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
| IngestionBundle | Data Model | **Extended** — `tenant_id: str` field (default `"default"`) for routing. |
| IngestionEvent | Data Model | **Extended** — `tenant_id: str` field for observer awareness. |
| IngestionPipeline.ingest | Event Loop | **Extended** — `tenant_id: str = "default"` parameter, routes to shard. |
| MarkdownPlugin | Plugin | **Unchanged** — Writes to whichever StorageAdapter the pipeline provides. |
| IngestionPlugin | Plugin | **Updated** — `tenant_id` parameter on `ingest_documents` tool. |
| semantic_search tool | Plugin (Markdown) | **Extended** — `tenant_ids` and `metadata_filters` parameters, optional `query`. |
| FeedbackPlugin | Plugin | **Updated** — `tenant_id` parameter on `provide_feedback` tool. |
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
        tenant_ids: list[str],
        query_fn: Callable[[StorageAdapter], list[dict]],
        limit: int,
        sort_key: str = "final_rank",
        sort_ascending: bool = True,
    ) -> list[dict]:
        """Scatter-gather: run query_fn on each tenant shard, merge results.

        Runs each shard query sequentially (MVP). Results from all shards
        are collected, sorted by sort_key, and trimmed to limit.
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

When `tenant_ids` is provided, MarkdownPlugin runs the query via `TenantStorageManager.query_across_tenants`. When omitted, queries all tenants. Results include `tenant_id` injected by the manager.

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

The pipeline uses `tenant_id` to get the correct `StorageAdapter` from `TenantStorageManager`, then passes that adapter to processors. Processors write to whatever adapter they receive — they don't know about tenants.

## Pipeline Flow

### Ingestion with tenant_id

```
1. Caller: ingest(uris, semantic_types=["travel_prefs"], tenant_id="user-123")
2. Pipeline gets adapter: tenant_manager.get_adapter("user-123")
3. IngestionBundle created with tenant_id="user-123"
4. Pipeline routes to processors by semantic type (unchanged)
5. For each URI, _build_contexts() uses the tenant's adapter:
   adapter.lookup_existing_docs(uri, plugin, record_type)  # no tenant_id param
6. Processor calls adapter.save_payload(...)                 # no tenant_id param
7. IngestionEvent emitted with tenant_id="user-123"
8. Observers receive event, can filter/react by tenant
```

### Query with tenant + metadata filters

```
1. Caller: semantic_search(
       query="hiking trails",
       tenant_ids=["user-123", "user-456"],
       metadata_filters={"activity_type": "outdoor"}
   )
2. MarkdownPlugin receives query, tenant_ids, metadata_filters
3. For each tenant_id, gets adapter from TenantStorageManager
4. Runs retrieve_by_vector_similarity on each shard:
   adapter.retrieve_by_vector_similarity(
       target_vector=embed("hiking trails"),
       limit=5,
       metadata_filters={"activity_type": "outdoor"}
   )
5. Each shard returns top-5 results (pure KNN + metadata post-filter)
6. Results merged across shards, re-sorted by final_rank, trimmed to limit=5
7. tenant_id injected into each result dict by TenantStorageManager
8. Return top-5 global results
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
- Add `tenant_id` to `IngestionBundle` and `IngestionEvent`.
- `IngestionPipeline.ingest()` gains `tenant_id: str = "default"` parameter.
- Pipeline resolves tenant to `StorageAdapter` via `TenantStorageManager`.
- Processors receive the tenant-specific adapter — no changes to processor interface.
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
- Merge results, re-sort by composite score, trim to limit.
- Inject `tenant_id` into result dicts.
- *Stories:* STORY-006

### Task 7: MCP Tools and CLI
- Update `semantic_search` tool: add `tenant_ids` and `metadata_filters`, make `query` optional. Route through `TenantStorageManager`.
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
