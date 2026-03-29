# ADR-010: Tenant Sharding at the SQLite File Level

**Status:** Accepted
**Date:** 2026-03-29
**Spec:** SPEC-010 (Multi-Tenancy & Metadata Search)
**See also:** [ADR-008: Multi-Tenancy & Metadata Search](ADR-008-multi-tenancy-metadata-search.md), [ADR-003: Relevance Weighting](ADR-003-relevance-weighting.md)

## Context

ADR-008 established that Team Mind needs required multi-tenancy and metadata search. The original design placed a `tenant_id` column on the `documents` table and used WHERE clauses to filter by tenant at query time. During design review, we discovered this approach has a fundamental correctness problem with vector search at scale.

### The KNN post-filter problem

sqlite-vec's `MATCH` operator performs KNN (K-Nearest Neighbors) on the **entire** vector index before any WHERE clauses are applied. The query flow is:

1. KNN returns the K nearest vectors globally from `vec_documents`
2. The outer query JOINs with `documents` and applies WHERE filters (tenant, metadata, plugin, etc.)
3. Rows that don't match filters are discarded

When a tenant's data is a small fraction of the total dataset, most KNN candidates are discarded. To compensate, the system over-fetches — requesting more candidates than needed — but this is fundamentally a heuristic. Analysis of scaling scenarios revealed it breaks at moderate scale:

| Scenario | Selectivity | KNN k=20, expected matches | Works? |
|----------|------------|---------------------------|--------|
| 10 tenants, 10K docs each | 10% | 2.0 | Marginal |
| 1K tenants, 1K docs each | 0.1% | 0.02 | **No** |
| 1M tenants, 100 docs each (travel app) | 0.0001% | 0.000002 | **No** |

No static over-fetch multiplier can solve this. A retry loop with exponential backoff (Option B) hits the same wall — at 0.0001% selectivity, you'd need to scan half the vector index before finding 5 matches, defeating the purpose of KNN entirely.

A pre-filter-then-rerank approach (Option C) works for small candidate sets but breaks in the opposite direction — when the pre-filtered set is large (e.g., "all NFL fans across 1M users" = 5M candidates), application-side vector distance computation becomes too expensive.

### The insight: shard at the database level

If each tenant's data lives in its own SQLite file, KNN operates on **exactly the right dataset** by construction. There's nothing to filter out — every vector in the index belongs to the target tenant. The correctness problem vanishes.

Within a tenant's shard, metadata filters (`json_extract`) are the only post-filter. Since per-tenant data is orders of magnitude smaller than the global dataset, the existing 4x over-fetch constant handles metadata filtering adequately. The extreme selectivity scenarios that break global KNN simply don't exist at per-tenant scale.

## Decision

We shard tenant data at the SQLite file level. Each tenant gets its own database file containing `documents`, `vec_documents`, and `doc_weights`. Global system state (plugin registry, tenant directory) lives in a separate `system.sqlite` file.

### 1. File Layout

```
~/.team-mind/
  system.sqlite                     # Global: registered_plugins, tenants
  tenants/
    default/data.sqlite             # Default tenant
    user-123/data.sqlite            # Per-tenant data
    user-456/data.sqlite
```

### 2. Global Database (`system.sqlite`)

Contains data that is shared across all tenants:

```sql
-- Existing table, moved from per-tenant to global
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

-- New table: tenant directory
CREATE TABLE tenants (
    tenant_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata JSON
);
```

The `tenants` table provides:
- **Enumeration:** "What tenants exist?" for cross-tenant query discovery and scatter-gather.
- **Validation:** Pipeline can verify a tenant exists before writing.
- **Lifecycle:** A place to track creation time and metadata (display name, owner, etc.). Soft-delete and archival can be added later.

### 3. Per-Tenant Database (`data.sqlite`)

Each tenant's database contains the existing schema **without** a `tenant_id` column — the file IS the tenant scope:

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uri TEXT NOT NULL,
    plugin TEXT NOT NULL DEFAULT '',
    record_type TEXT NOT NULL DEFAULT '',
    parent_id INTEGER REFERENCES documents(id),
    metadata JSON,
    content_hash TEXT,
    plugin_version TEXT DEFAULT '0.0.0',
    semantic_type TEXT NOT NULL DEFAULT '',
    media_type TEXT NOT NULL DEFAULT ''
);

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
```

The composite identity key remains `(uri, plugin, record_type)` — unchanged from the pre-tenancy design. Tenant scoping is structural (file-level), not a query filter.

### 4. `TenantStorageManager`

A new class manages per-tenant database lifecycle and cross-tenant operations:

```python
class TenantStorageManager:
    """Manages per-tenant SQLite databases and cross-tenant queries."""

    def __init__(self, base_path: str):
        self.base_path = base_path           # e.g., ~/.team-mind/
        self._adapters: dict[str, StorageAdapter] = {}
        self._system_db: sqlite3.Connection   # system.sqlite

    def get_adapter(self, tenant_id: str) -> StorageAdapter:
        """Get or lazily create a StorageAdapter for a tenant."""

    def create_tenant(self, tenant_id: str, metadata: dict | None = None) -> None:
        """Register a new tenant in system.sqlite, create its data directory."""

    def list_tenants(self) -> list[dict]:
        """List all registered tenants."""

    def query_across_tenants(
        self,
        tenant_ids: list[str],
        query_fn: Callable[[StorageAdapter], list[dict]],
        limit: int,
        sort_key: str = "final_rank",
    ) -> list[dict]:
        """Scatter-gather: run query_fn on each tenant shard, merge results."""
```

**Connection management:**
- Tenant databases are opened lazily on first access.
- An LRU eviction policy closes idle connections to bound memory usage.
- The default tenant (`"default"`) is auto-created on first startup if it doesn't exist.

### 5. Single-Tenant Query (Common Case)

```python
# 1. Pipeline/tool resolves tenant_id to a StorageAdapter
adapter = tenant_manager.get_adapter("user-123")

# 2. Pure KNN within this tenant's database — no tenant filter needed
results = adapter.retrieve_by_vector_similarity(
    target_vector=embed("hiking trails"),
    limit=5,
    metadata_filters={"activity_type": "outdoor"},
)
```

KNN searches only the target tenant's `vec_documents`. No over-fetch gymnastics. Metadata filters are the only post-filter, operating on a dataset that's orders of magnitude smaller than the global total.

### 6. Cross-Tenant Query (Scatter-Gather)

```python
# Search across specific tenants
results = tenant_manager.query_across_tenants(
    tenant_ids=["user-123", "user-456"],
    query_fn=lambda adapter: adapter.retrieve_by_vector_similarity(
        target_vector=embed("hiking trails"),
        limit=5,
        metadata_filters={"activity_type": "outdoor"},
    ),
    limit=5,
)
```

Each shard query runs independently. Results are merged, re-sorted by composite score, and trimmed to the requested limit. Scatter-gather runs the shard queries sequentially in the MVP (SQLite connections are single-threaded); parallel execution across shards is a future optimization.

### 7. Impact on `StorageAdapter`

`StorageAdapter` **loses** the `tenant_id` parameter on all methods. It operates on a single database file and doesn't know about tenants — that's `TenantStorageManager`'s concern.

- `save_payload(uri, metadata, vector, plugin, record_type, ...)` — no `tenant_id`
- `delete_by_uri(uri, plugin, record_type)` — no `tenant_id`
- `lookup_existing_docs(uri, plugin, record_type)` — no `tenant_id`
- `retrieve_by_vector_similarity(target_vector, limit, ...)` — no `tenant_ids`

The composite identity key stays at `(uri, plugin, record_type)`. Tenant isolation is at the file level, not the query level.

### 8. Impact on Pipeline and Data Models

`IngestionBundle` and `IngestionEvent` **retain** `tenant_id`:
- The pipeline uses `tenant_id` from the bundle to route to the correct shard via `TenantStorageManager.get_adapter(tenant_id)`.
- The event carries `tenant_id` so observers know which tenant was affected.
- `IngestionPipeline.ingest()` retains `tenant_id: str = "default"` — it routes, not filters.

### 9. Impact on MCP Tools

- `ingest_documents` retains `tenant_id` parameter (default `"default"`). Routes to the correct shard.
- `semantic_search` retains `tenant_ids` parameter. When provided, triggers scatter-gather. When omitted, searches all tenants.
- `provide_feedback(doc_id, signal)` needs `tenant_id` to know which shard contains the document. Added as parameter.

### 10. `registered_plugins` Migration

The `registered_plugins` table moves from per-database to `system.sqlite`. Plugins are global — you register MarkdownPlugin once, and it's available across all tenants. The `StorageAdapter.initialize()` method no longer creates this table; `TenantStorageManager` handles it during system initialization.

## Alternatives Considered

### 1. `tenant_id` column with KNN over-fetch heuristics (original ADR-008 approach)

Add `tenant_id` to the `documents` table, use over-fetch multipliers on KNN.

**Rejected because:**
- Provably incorrect at moderate scale (1K+ tenants). No static multiplier compensates for extreme selectivity.
- Retry loops degrade to full vector index scans when selectivity is very high.
- Creates a false sense of correctness — works in testing, fails in production.

### 2. Pre-filter then application-side reranking

Pre-filter candidate IDs by tenant/metadata, fetch their vectors, compute distances in Python.

**Rejected as a standalone strategy because:**
- Works well for small candidate sets but breaks on large ones (5M+ candidates for broad cross-tenant queries).
- Requires loading vectors into application memory — doesn't scale.
- However, this approach is effectively what happens within a shard when the shard is small, which is the common case.

### 3. Hybrid approach (pre-filter for small sets, KNN for large sets)

Estimate candidate count, choose strategy dynamically.

**Rejected because:**
- The estimation step adds latency and complexity.
- Two code paths means two sets of bugs.
- Sharding eliminates the need for the decision entirely — KNN within a shard is always correct.

### 4. Bucket sharding (hash tenant_id into N fixed buckets)

Group multiple tenants into a fixed number of SQLite files (e.g., 256 buckets).

**Rejected because:**
- Partially reintroduces the within-shard filtering problem. 1M tenants / 256 buckets = ~4K tenants per bucket, and KNN within a bucket still suffers from tenant selectivity.
- Adds complexity (hash routing) without fully solving the problem.
- Per-tenant sharding is simpler and correct. If file count becomes an operational issue, bucket sharding can be introduced as a future optimization with a migration path.

### 5. Separate vector tables per tenant within a single database

Create `vec_tenant_<id>` virtual tables dynamically.

**Rejected because:**
- Dynamic DDL in the hot path (creating tables per tenant) is fragile.
- Naming conventions and table management add complexity.
- SQLite's `sqlite_master` grows with every table, impacting startup time.
- Separate files are operationally simpler and provide natural I/O isolation.

## Consequences

### Positive

- **Correct by construction.** KNN within a shard searches exactly the right data. No over-fetch heuristics, no retry loops, no false matches.
- **Natural isolation.** Tenants literally cannot see each other's data without explicit scatter-gather. No accidental data leakage through query bugs.
- **Independent scaling.** Hot tenants get their own I/O. A large tenant's database doesn't slow down queries for small tenants.
- **Simpler `StorageAdapter`.** No `tenant_id` parameter on any method. The adapter operates on one database — clean and focused.
- **Metadata filtering works at shard scale.** The existing 4x over-fetch constant handles metadata filters on per-tenant data sizes (100s to 10Ks of rows).
- **Future-ready.** Per-tenant files can be moved to different storage backends, archived, or backed up independently.

### Negative

- **Cross-tenant queries are slower.** Scatter-gather across N shards means N sequential queries (in MVP). Parallel execution can mitigate but adds complexity.
- **Connection management overhead.** Many SQLite files means many potential connections. LRU eviction bounds this but adds a management layer.
- **Schema migrations across shards.** Adding a column or index must be applied to every tenant database. Requires a migration runner that iterates over all shards.
- **File system pressure at extreme scale.** 1M tenants = 1M directories/files. Manageable with hash-based directory structure (e.g., `tenants/ab/abcd1234/data.sqlite`), but requires planning.
- **`provide_feedback` needs tenant context.** The caller must know which tenant a document belongs to when providing feedback. The `doc_id` alone is not globally unique — it's unique within a shard.

### Neutral

- `IngestionBundle` and `IngestionEvent` still carry `tenant_id` — for routing and observer awareness.
- The `semantic_search` MCP tool still accepts `tenant_ids` — the scatter-gather is transparent to the caller.
- Single-tenant deployments just use the `default` shard and never think about sharding.
