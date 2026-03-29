# SPEC-010: Multi-Tenancy & Metadata Search — Design

## Overview

Introduces required multi-tenancy via per-tenant SQLite database sharding and metadata search filters on the query path. Each tenant gets its own database file; a global `system.sqlite` holds the plugin registry and tenant directory. The `semantic_search` tool becomes the single composable query surface for vector similarity, metadata filtering, tenant scoping, and weight ranking. Cross-tenant queries use scatter-gather across shards.

## Design Amendments (vs Original Spec)

| Amendment | Original | Revised |
|-----------|----------|---------|
| Tenant isolation mechanism | `tenant_id` column on `documents` | Per-tenant SQLite file sharding (ADR-010) |
| `tenant_id` on StorageAdapter methods | Required parameter on `save_payload`, `delete_by_uri`, `lookup_existing_docs` | Removed — `TenantStorageManager` routes to the correct database |
| `tenant_ids` on `retrieve_by_vector_similarity` | WHERE clause filter | Removed — cross-tenant uses scatter-gather |
| Composite identity key | `(uri, plugin, record_type, tenant_id)` | `(uri, plugin, record_type)` — tenant is the database |
| KNN over-fetch for tenant filters | Dynamic multiplier adjustment | Not needed — KNN operates within shard |
| `registered_plugins` table | Per-database | Global in `system.sqlite` |
| `IngestionPipeline.ingest()` | `tenant_id` as WHERE clause | `tenant_id` routes to shard via `TenantStorageManager` |

## Components

| Component | Type | Change |
|-----------|------|--------|
| TenantStorageManager | Storage | **New** — Manages per-tenant databases, scatter-gather, tenant lifecycle. |
| system.sqlite | Storage | **New** — Global database for `registered_plugins` and `tenants` tables. |
| Per-tenant data.sqlite | Storage | **New** — Per-tenant `documents`, `vec_documents`, `doc_weights`. |
| StorageAdapter | Storage | **Unchanged** — Operates on a single database. No `tenant_id` parameters. |
| StorageAdapter.retrieve_by_vector_similarity | Storage | **Extended** — `metadata_filters` parameter, optional `target_vector`. |
| IngestionBundle | Data Model | **Extended** — `tenant_id: str` field (default `"default"`) for routing. `storage: StorageAdapter` field injected by pipeline. |
| IngestionEvent | Data Model | **Extended** — `tenant_id: str` field for observer awareness. |
| IngestionPipeline.ingest | Event Loop | **Extended** — `tenant_id: str = "default"` parameter, routes to shard. |
| MarkdownPlugin | Plugin | **Unchanged** — Uses `bundle.storage` instead of `self.storage`. No constructor changes. |
| IngestionPlugin | Plugin | **Updated** — `tenant_id` parameter on `ingest_documents` tool. |
| semantic_search tool | Plugin (Markdown) | **Extended** — `tenant_ids` and `metadata_filters` parameters, optional `query`. |
| FeedbackPlugin | Plugin | **Updated** — Constructor takes `TenantStorageManager` instead of `StorageAdapter`. `call_tool` resolves adapter from `tenant_id` in tool arguments via `self.tenant_manager.get_adapter(arguments["tenant_id"])`. `provide_feedback` tool schema gains required `tenant_id`. |
| CLI | Entry Point | **Extended** — `--tenant-id` flag on ingest subcommand. |

## Data Model

### File layout

```
~/.team-mind/
  system.sqlite                     # Global: registered_plugins, tenants
  tenants/
    default/data.sqlite             # Default tenant
    user-123/data.sqlite            # Per-tenant data
    user-456/data.sqlite
```

### system.sqlite schema

```sql
-- Plugin registry (moved from per-database to global)
CREATE TABLE registered_plugins (
    plugin_name TEXT PRIMARY KEY,
    plugin_type TEXT NOT NULL,
    module_path TEXT NOT NULL,
    config JSON,
    event_filter JSON,
    semantic_types JSON,
    supported_media_types JSON,
    enabled INTEGER DEFAULT 1,
    registered_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Tenant directory
CREATE TABLE tenants (
    tenant_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata JSON
);
```

### Per-tenant data.sqlite schema

The existing `documents`, `vec_documents`, and `doc_weights` tables — **without** a `tenant_id` column. The database file IS the tenant scope. Composite identity key: `(uri, plugin, record_type)`.

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uri TEXT NOT NULL,
    plugin TEXT NOT NULL DEFAULT '',
    record_type TEXT NOT NULL DEFAULT '',
    metadata JSON,
    content_hash TEXT,
    plugin_version TEXT DEFAULT '0.0.0',
    semantic_type TEXT NOT NULL DEFAULT '',
    media_type TEXT NOT NULL DEFAULT ''
);

-- Indexes (same as current, no tenant_id)
CREATE INDEX idx_documents_plugin ON documents(plugin);
CREATE INDEX idx_documents_record_type ON documents(record_type);
CREATE INDEX idx_documents_plugin_record_type ON documents(plugin, record_type);
CREATE INDEX idx_documents_uri_plugin_record_type ON documents(uri, plugin, record_type);
CREATE INDEX idx_documents_semantic_type ON documents(semantic_type);

CREATE VIRTUAL TABLE vec_documents USING vec0(
    id INTEGER PRIMARY KEY,
    embedding float[768]
);

CREATE TABLE doc_weights (
    doc_id INTEGER PRIMARY KEY REFERENCES documents(id),
    usage_score REAL DEFAULT 0.0,
    signal_count INTEGER DEFAULT 0,
    last_accessed TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    tombstoned INTEGER DEFAULT 0,
    decay_half_life_days REAL
);

CREATE INDEX idx_doc_weights_tombstoned ON doc_weights(tombstoned);
```

### TenantStorageManager

```python
class TenantStorageManager:
    """Manages per-tenant SQLite databases and cross-tenant queries."""

    def __init__(self, base_path: str):
        self.base_path = base_path           # e.g., ~/.team-mind/
        self._adapters: dict[str, StorageAdapter] = {}
        self._system_conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        """Initialize system.sqlite and ensure default tenant exists."""

    def get_adapter(self, tenant_id: str) -> StorageAdapter:
        """Get or lazily create a StorageAdapter for a tenant.

        Opens the tenant's data.sqlite, initializes tables if new.
        Raises ValueError if tenant is not registered in system.sqlite.
        """

    def create_tenant(self, tenant_id: str, metadata: dict | None = None) -> None:
        """Register a new tenant in system.sqlite. Creates tenant directory
        and data.sqlite on first access (lazy)."""

    def list_tenants(self) -> list[dict]:
        """List all registered tenants from system.sqlite."""

    def query_across_tenants(
        self,
        tenant_ids: list[str] | None,
        query_fn: Callable[[StorageAdapter], list[dict]],
        limit: int,
        sort_key: str = "final_rank",
        sort_descending: bool = False,
    ) -> list[dict]:
        """Scatter-gather: run query_fn on each tenant shard, merge results.

        Runs each shard query sequentially (MVP). Results from all shards
        are collected, tenant_id injected into each result dict, sorted by
        sort_key, and trimmed to limit.

        When tenant_ids is None, queries all registered tenants.

        sort_descending:
          - False (default): ascending sort — correct for distance-based
            scores (final_rank) where lower is better.
          - True: descending sort — correct for weight-based scores
            (weight_rank) where higher is better.

        Callers (e.g., semantic_search) set sort_descending based on
        whether a vector query was used:
          - Vector query:     sort_key="final_rank", sort_descending=False
          - Non-vector query: sort_key="weight_rank", sort_descending=True
        """

    # --- Plugin registry (delegates to system.sqlite) ---

    def save_plugin_record(self, ...) -> None:
        """Save plugin record to system.sqlite."""

    def get_enabled_plugin_records(self) -> list[dict]:
        """Get enabled plugins from system.sqlite."""

    def disable_plugin_record(self, plugin_name: str) -> bool:
        """Disable a plugin in system.sqlite."""

    def delete_plugin_record(self, plugin_name: str) -> bool:
        """Delete a plugin from system.sqlite."""

    def close(self) -> None:
        """Close all tenant adapters and system connection."""
```

**Connection management:**
- Tenant databases are opened lazily on first `get_adapter` call.
- LRU eviction policy closes idle connections (configurable max, default 64).
- Default tenant auto-created on `initialize()`.

### How processors get the tenant-specific adapter

Processors (e.g., MarkdownPlugin) currently hold `self.storage: StorageAdapter` set at init time. With tenant sharding, a single plugin instance needs to write to different shards per-bundle.

**Mechanism: `IngestionBundle` carries the adapter.**

```python
@dataclass
class IngestionBundle:
    uris: list[str]
    semantic_types: list[str]
    tenant_id: str = "default"
    storage: StorageAdapter | None = None  # Injected by pipeline
    # ... existing fields ...
```

The pipeline injects the tenant-specific adapter into the bundle before passing it to processors:

```python
# In IngestionPipeline.ingest():
adapter = self.tenant_manager.get_adapter(tenant_id)
bundle.storage = adapter

# Processor uses bundle.storage for all storage operations:
class MarkdownPlugin(IngestProcessor):
    def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        storage = bundle.storage  # Tenant-specific adapter
        storage.save_payload(uri=..., metadata=..., vector=..., ...)
```

**Why bundle, not constructor:**
- A single plugin instance is registered once but processes bundles for many tenants.
- Changing constructors would require re-instantiating plugins per tenant or injecting TenantStorageManager into every plugin.
- The bundle is the natural per-invocation context — it already carries URIs, semantic_types, and tenant_id.
- **No changes to the processor interface or constructor.** Processors just read `bundle.storage` instead of `self.storage`.

**Migration:** Existing processors that use `self.storage` need a one-line change to use `bundle.storage`. Since there's no backward compatibility concern, this is mechanical.

### Tenant auto-creation on ingestion

`TenantStorageManager.get_adapter(tenant_id)` raises `ValueError` for unregistered tenants when called directly — this is correct for raw programmatic use where an unknown tenant likely indicates a bug.

However, the **ingestion pipeline auto-creates unknown tenants** to support zero-friction use:

```python
# In IngestionPipeline.ingest():
try:
    adapter = self.tenant_manager.get_adapter(tenant_id)
except ValueError:
    self.tenant_manager.create_tenant(tenant_id)
    adapter = self.tenant_manager.get_adapter(tenant_id)
```

**The rule:**
- `get_adapter()` alone: strict — raises for unknown tenants. Callers must explicitly create tenants first.
- `IngestionPipeline.ingest()`: auto-creates — passing `tenant_id="user-123"` just works. The pipeline handles registration transparently.
- `semantic_search` with unknown tenant_id: returns empty results (shard doesn't exist). No error — querying a nonexistent tenant is not an error condition.

This means a caller can do `ingest(uris, tenant_id="user-123")` without pre-registering "user-123". The pipeline creates the tenant entry in `system.sqlite` and initializes the shard on first use.

### StorageAdapter changes

`StorageAdapter` is **unchanged** in its method signatures — no `tenant_id` parameter anywhere. It continues to operate on a single database file.

The only change: `StorageAdapter.initialize()` no longer creates the `registered_plugins` table. Plugin registry is managed by `TenantStorageManager` on `system.sqlite`.

## Query Model

### retrieve_by_vector_similarity — metadata filters and optional vector

`StorageAdapter.retrieve_by_vector_similarity` gains metadata filters and optional vector. No tenant parameters — it operates within one shard.

```python
def retrieve_by_vector_similarity(
    self,
    target_vector: list[float] | None = None,  # CHANGED — now optional
    limit: int = 5,
    plugins: list[str] | None = None,
    record_types: list[str] | None = None,
    metadata_filters: dict[str, str] | None = None,  # NEW
) -> list[dict]:
```

**Metadata filtering:** Each entry in `metadata_filters` becomes a WHERE clause:
```sql
AND json_extract(d.metadata, '$.interest_category') = ?
AND json_extract(d.metadata, '$.league') = ?
```

**Optional vector:** When `target_vector` is `None`, skip the KNN step entirely. Query documents directly from the `documents` table, ranked by composite weight score:

```sql
SELECT d.id, d.uri, d.plugin, d.record_type, d.metadata,
       COALESCE(w.usage_score, 0.0) AS usage_score,
       (COALESCE(w.usage_score, 0.0)
        * CASE
            WHEN w.decay_half_life_days IS NOT NULL
                 AND w.decay_half_life_days > 0
            THEN POWER(0.5,
                 (JULIANDAY('now') - JULIANDAY(COALESCE(w.created_at, datetime('now'))))
                 / w.decay_half_life_days)
            ELSE 1.0
          END
       ) AS weight_rank
FROM documents d
LEFT JOIN doc_weights w ON d.id = w.doc_id
WHERE COALESCE(w.tombstoned, 0) = 0
  AND json_extract(d.metadata, '$.interest_category') = ?
ORDER BY weight_rank DESC
LIMIT ?
```

**KNN over-fetch:** The existing `KNN_OVERFETCH_MULTIPLIER = 4` constant handles metadata filtering at per-tenant data scale. No dynamic adjustment needed — within a shard, metadata selectivity is manageable.

### Query composition matrix

| Vector | Metadata | Behavior |
|--------|----------|----------|
| yes | omitted | Current behavior — KNN within shard. |
| yes | set | KNN within shard + metadata post-filter. |
| no | set | Pure metadata query within shard, ranked by weight. |
| no | omitted | All non-tombstoned documents in shard, ranked by weight. |

Tenant scoping is orthogonal — the caller chooses which shard(s) to query via `TenantStorageManager`.

### semantic_search MCP tool

```python
{
    "name": "semantic_search",
    "inputSchema": {
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query text. Optional — omit for pure metadata/weight-ranked retrieval."
            },
            "limit": {"type": "integer", "default": 5},
            "plugins": {"type": "array", "items": {"type": "string"}},
            "record_types": {"type": "array", "items": {"type": "string"}},
            "tenant_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tenant IDs to search within. Omit to search all tenants."
            },
            "metadata_filters": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Equality filters on metadata fields."
            }
        },
        "required": []
    }
}
```

`semantic_search` **always** routes through `TenantStorageManager.query_across_tenants` — even for a single tenant. This ensures consistent result format: every result dict includes `tenant_id`, regardless of how many tenants were queried. When `tenant_ids` is omitted, queries all registered tenants.

### ingest_documents MCP tool

```python
{
    "name": "ingest_documents",
    "inputSchema": {
        "properties": {
            "uris": {"type": "array", "items": {"type": "string"}},
            "semantic_types": {"type": "array", "items": {"type": "string"}},
            "reliability_hint": {"type": "number"},
            "tenant_id": {
                "type": "string",
                "default": "default",
                "description": "Tenant ID for data isolation. Defaults to 'default'."
            }
        },
        "required": ["uris"]
    }
}
```

### provide_feedback MCP tool

```python
{
    "name": "provide_feedback",
    "inputSchema": {
        "properties": {
            "doc_id": {"type": "integer"},
            "signal": {"type": "integer"},
            "reason": {"type": "string"},
            "tombstone": {"type": "boolean"},
            "tenant_id": {
                "type": "string",
                "default": "default",
                "description": "Tenant that owns the document."
            }
        },
        "required": ["doc_id", "signal", "tenant_id"]
    }
}
```

`tenant_id` is required on `provide_feedback` because `doc_id` is only unique within a shard.

### CLI extension

```
team-mind ingest --tenant-id user-123 --semantic-type travel_preferences /path/to/data
```

`--tenant-id` defaults to `"default"` when not specified.

### IngestionPipeline.ingest

```python
async def ingest(
    self,
    uris: List[str],
    semantic_types: list[str] | None = None,
    reliability_hint: float | None = None,
    tenant_id: str = "default",
) -> IngestionBundle | None:
```

The pipeline uses `tenant_id` to get the correct `StorageAdapter` from `TenantStorageManager` (auto-creating the tenant if unregistered), injects it into `bundle.storage`, then passes the bundle to processors. Processors use `bundle.storage` — they don't know about tenants.

## Pipeline Flow

### Ingestion with tenant_id

```
1. Caller: ingest(uris, semantic_types=["travel_prefs"], tenant_id="user-123")
2. Pipeline auto-creates tenant if unregistered:
   tenant_manager.create_tenant("user-123")  # idempotent if exists
3. Pipeline gets adapter: tenant_manager.get_adapter("user-123")
4. IngestionBundle created with tenant_id="user-123", storage=adapter
5. Pipeline routes to processors by semantic type (unchanged)
6. For each URI, _build_contexts() uses bundle.storage:
   bundle.storage.lookup_existing_docs(uri, plugin, record_type)
7. Processor uses bundle.storage for writes:
   bundle.storage.save_payload(uri=..., metadata=..., vector=...)
8. IngestionEvent emitted with tenant_id="user-123"
9. Observers receive event, can filter/react by tenant
```

### Query with tenant + metadata filters

```
1. Caller: semantic_search(
       query="hiking trails",
       tenant_ids=["user-123", "user-456"],
       metadata_filters={"activity_type": "outdoor"}
   )
2. semantic_search ALWAYS routes through query_across_tenants
   (even for single tenant — ensures consistent result format)
3. query_across_tenants iterates shards for ["user-123", "user-456"]:
   For each shard, runs:
     adapter.retrieve_by_vector_similarity(
         target_vector=embed("hiking trails"),
         limit=5,
         metadata_filters={"activity_type": "outdoor"}
     )
4. Each shard returns top-5 results (KNN + metadata post-filter)
5. query_across_tenants injects tenant_id into each result dict
6. Results merged, re-sorted by final_rank (ascending), trimmed to limit=5
7. Return top-5 global results

Note on sort direction:
  - Vector queries:     sort_key="final_rank", sort_descending=False
    (lower final_rank = closer match = better)
  - Non-vector queries: sort_key="weight_rank", sort_descending=True
    (higher weight = more relevant = better)
  semantic_search sets the correct sort direction based on whether
  a query string was provided.
```

## Execution Plan

### Task 1: system.sqlite and TenantStorageManager
- Create `TenantStorageManager` class.
- Initialize `system.sqlite` with `registered_plugins` and `tenants` tables.
- Implement `create_tenant`, `list_tenants`, `get_adapter`.
- Lazy connection management with LRU eviction.
- Auto-create default tenant on initialization.
- Migrate plugin registry methods from `StorageAdapter` to `TenantStorageManager`.
- *Stories:* STORY-001

### Task 2: Per-Tenant Database Lifecycle
- `get_adapter` creates tenant directory and `data.sqlite` on first access.
- `StorageAdapter.initialize()` no longer creates `registered_plugins` table.
- Per-tenant schema identical to current minus `registered_plugins`.
- *Stories:* STORY-002

### Task 3: Ingestion Pipeline Routing
- Add `tenant_id` and `storage` fields to `IngestionBundle`. Add `tenant_id` to `IngestionEvent`.
- `IngestionPipeline.ingest()` gains `tenant_id: str = "default"` parameter.
- Pipeline auto-creates unregistered tenants on ingestion (try/create/retry pattern).
- Pipeline injects tenant-specific `StorageAdapter` into `bundle.storage`.
- Processors use `bundle.storage` instead of `self.storage` — no constructor changes.
- *Stories:* STORY-003

### Task 4: Metadata Search Filters
- Add `metadata_filters` parameter to `retrieve_by_vector_similarity`.
- Generate `json_extract(d.metadata, '$.key') = ?` clauses for each filter.
- Over-fetch multiplier unchanged (4x constant adequate at shard scale).
- *Stories:* STORY-004

### Task 5: Optional Vector Query (Weight-Ranked Retrieval)
- Make `target_vector` optional in `retrieve_by_vector_similarity`.
- When `None`, query `documents` table directly (no `vec_documents` join).
- Rank by composite weight score descending.
- *Stories:* STORY-005

### Task 6: Cross-Tenant Scatter-Gather
- Implement `TenantStorageManager.query_across_tenants`.
- Sequential shard queries (MVP).
- Inject `tenant_id` into each result dict.
- Merge results, re-sort by `sort_key` with correct direction (`sort_descending`), trim to limit.
- `tenant_ids=None` queries all registered tenants.
- *Stories:* STORY-006

### Task 7: MCP Tools and CLI
- Update `semantic_search` tool: add `tenant_ids` and `metadata_filters`, make `query` optional. **Always** route through `query_across_tenants` (even for single tenant) for consistent result format. Set `sort_descending` based on whether vector query was used.
- Update `ingest_documents` tool: add `tenant_id` (default `"default"`).
- Update `provide_feedback` tool: add required `tenant_id`.
- Update CLI: add `--tenant-id` flag.
- *Stories:* STORY-007

### Task 8: Update Existing Tests
- Update tests to use `TenantStorageManager` where needed.
- Add tests for tenant isolation (same URI in different shards).
- Add tests for scatter-gather across tenants.
- Add tests for metadata filters and optional vector query.
- *Stories:* STORY-008

### Task 9: Documentation and Diagrams
- Update system overview with sharding model and TenantStorageManager.
- Add mermaid diagrams to system overview and/or design docs:
  - Tenant sharding file layout (system.sqlite + per-tenant data.sqlite).
  - Scatter-gather query flow (single-tenant vs cross-tenant).
  - TenantStorageManager component relationships (manager → adapters → databases).
- Update plugin developer guide (plugins don't know about tenants).
- Update repo README: development status for SPEC-010, update architecture diagram to show multi-tenancy layer.
- Update ADR-002 with cross-references.
- Update roadmap with SPEC-010 status.
- *Stories:* STORY-009
