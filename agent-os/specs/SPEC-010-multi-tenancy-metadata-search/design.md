# SPEC-010: Multi-Tenancy & Metadata Search — Design

## Overview

Adds required `tenant_id` to all documents and metadata search filters to the query path. All changes are breaking (no backward compatibility required). The `semantic_search` tool becomes the single composable query surface for vector similarity, metadata filtering, tenant scoping, and weight ranking.

## Components

| Component | Type | Change |
|-----------|------|--------|
| documents table | Storage | **Extended** — `tenant_id TEXT NOT NULL` column, updated indexes. |
| StorageAdapter.save_payload | Storage | **Extended** — Required `tenant_id` parameter. |
| StorageAdapter.delete_by_uri | Storage | **Extended** — Scoped by `tenant_id`. |
| StorageAdapter.lookup_existing_docs | Storage | **Extended** — Scoped by `tenant_id`. |
| StorageAdapter.retrieve_by_vector_similarity | Storage | **Extended** — `tenant_ids` filter, `metadata_filters`, optional vector. |
| IngestionBundle | Data Model | **Extended** — `tenant_id: str` field (default `"default"`). |
| IngestionEvent | Data Model | **Extended** — `tenant_id: str` field. |
| IngestionPipeline | Event Loop | **Extended** — Propagates `tenant_id` to processors and events. |
| MarkdownPlugin | Plugin | **Updated** — Passes `tenant_id` to `save_payload`. |
| IngestionPlugin | Plugin | **Updated** — `tenant_id` parameter on `ingest_documents` tool. |
| semantic_search tool | Plugin (Markdown) | **Extended** — `tenant_ids` and `metadata_filters` parameters, optional `query`. |
| CLI | Entry Point | **Extended** — `--tenant-id` flag on ingest subcommand. |

## Data Model

### Schema changes

```sql
-- Add required tenant_id to documents
ALTER TABLE documents ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default';

-- Replace old composite index with tenant-aware version
DROP INDEX IF EXISTS idx_documents_uri_plugin_record_type;
CREATE INDEX idx_documents_uri_plugin_record_type_tenant
    ON documents(uri, plugin, record_type, tenant_id);

-- Tenant query index
CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
```

### Updated composite identity

The uniqueness/idempotency key changes from `(uri, plugin, record_type)` to `(uri, plugin, record_type, tenant_id)`. This means:
- The same URI can exist in different tenants without collision.
- `lookup_existing_docs` and `delete_by_uri` both require `tenant_id`.
- A document's tenant is immutable after creation (like its URI).

### StorageAdapter.save_payload extension

```python
def save_payload(
    self,
    uri: str,
    metadata: dict,
    vector: list[float],
    plugin: str,
    record_type: str,
    tenant_id: str,                          # NEW — required, no default
    decay_half_life_days: float | None = None,
    content_hash: str | None = None,
    plugin_version: str = "0.0.0",
    semantic_type: str = "",
    media_type: str = "",
    initial_score: float = 0.0,
) -> int:
```

`tenant_id` is required at the storage layer with no default. The MCP tool layer provides the `"default"` ergonomic default.

### StorageAdapter.delete_by_uri extension

```python
def delete_by_uri(
    self,
    uri: str,
    plugin: str,
    record_type: str,
    tenant_id: str,                          # NEW — required
) -> int:
```

### StorageAdapter.lookup_existing_docs extension

```python
def lookup_existing_docs(
    self,
    uri: str,
    plugin: str,
    record_type: str,
    tenant_id: str,                          # NEW — required
) -> list[dict]:
```

### IngestionBundle extension

```python
@dataclass
class IngestionBundle:
    uris: List[str]
    events: List[IngestionEvent] = field(default_factory=list)
    contexts: Dict[str, IngestionContext] = field(default_factory=dict)
    semantic_types: list[str] = field(default_factory=list)
    reliability_hint: float | None = None
    tenant_id: str = "default"               # NEW
```

### IngestionEvent extension

```python
@dataclass
class IngestionEvent:
    plugin: str
    record_type: str
    uris: list[str] = field(default_factory=list)
    doc_ids: list[int] = field(default_factory=list)
    semantic_types: list[str] = field(default_factory=list)
    tenant_id: str = "default"               # NEW
```

## Query Model

### retrieve_by_vector_similarity extension

```python
def retrieve_by_vector_similarity(
    self,
    target_vector: list[float] | None = None,  # CHANGED — now optional
    limit: int = 5,
    plugins: list[str] | None = None,
    record_types: list[str] | None = None,
    tenant_ids: list[str] | None = None,        # NEW
    metadata_filters: dict[str, str] | None = None,  # NEW
) -> list[dict]:
```

**Behavior changes:**

1. **Tenant filtering:** When `tenant_ids` is provided, only documents in those tenants are returned. When `None`, all tenants are searched.

2. **Metadata filtering:** Each entry in `metadata_filters` becomes a WHERE clause:
   ```sql
   AND json_extract(d.metadata, '$.interest_category') = ?
   AND json_extract(d.metadata, '$.league') = ?
   ```

3. **Optional vector:** When `target_vector` is `None`, skip the KNN step entirely. Query documents directly from the `documents` table with metadata/tenant/plugin/record_type filters, ranked by composite weight score (usage_score adjusted by decay). This enables pure structured retrieval.

4. **Over-fetch adjustment:** When metadata filters or tenant filters are present alongside a vector query, the over-fetch multiplier increases to account for additional post-KNN filtering. Suggested: `KNN_OVERFETCH_MULTIPLIER = 4` baseline, `+2` per active filter dimension (tenant, metadata).

### Query composition matrix

| Vector | Tenant | Metadata | Behavior |
|--------|--------|----------|----------|
| yes | omitted | omitted | Current behavior — KNN across all documents. |
| yes | set | omitted | KNN filtered to specific tenants. |
| yes | omitted | set | KNN filtered by metadata fields. |
| yes | set | set | KNN filtered by tenant and metadata. |
| no | set | omitted | All documents in tenant(s), ranked by weight. |
| no | omitted | set | All documents matching metadata, ranked by weight. |
| no | set | set | Documents matching tenant + metadata, ranked by weight. |
| no | omitted | omitted | All non-tombstoned documents, ranked by weight. |

### Non-vector query path

When `target_vector` is `None`, the query bypasses `vec_documents` entirely:

```sql
SELECT d.id, d.uri, d.plugin, d.record_type, d.metadata, d.tenant_id,
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
  AND d.tenant_id IN (?, ?)                              -- tenant filter
  AND json_extract(d.metadata, '$.interest_category') = ? -- metadata filter
ORDER BY weight_rank DESC
LIMIT ?
```

Results are ranked by weight (highest first) rather than vector distance (lowest first), since there's no distance metric to minimize.

### semantic_search MCP tool extension

```python
# Tool schema additions:
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
                "description": "Equality filters on metadata fields. Keys are field names, values are expected values."
            }
        },
        "required": []  # query is no longer required
    }
}
```

### ingest_documents MCP tool extension

```python
# Tool schema additions:
{
    "name": "ingest_documents",
    "inputSchema": {
        "properties": {
            # ... existing properties ...
            "tenant_id": {
                "type": "string",
                "default": "default",
                "description": "Tenant ID for data isolation. Defaults to 'default'."
            }
        }
    }
}
```

### CLI extension

```
team-mind ingest --tenant-id user-123 --semantic-type travel_preferences /path/to/data
```

`--tenant-id` defaults to `"default"` when not specified.

## Pipeline Flow

### Ingestion with tenant_id

```
1. Caller: ingest(uris, semantic_types=["travel_prefs"], tenant_id="user-123")
2. IngestionBundle created with tenant_id="user-123"
3. Pipeline routes to processors by semantic type (unchanged)
4. For each URI, _build_contexts() calls:
   lookup_existing_docs(uri, plugin, record_type, tenant_id="user-123")
5. Processor calls save_payload(..., tenant_id="user-123")
6. IngestionEvent emitted with tenant_id="user-123"
7. Observers receive event, can filter/react by tenant
```

### Query with tenant + metadata filters

```
1. Caller: semantic_search(
       query="hiking trails",
       tenant_ids=["user-123", "user-456"],
       metadata_filters={"activity_type": "outdoor"}
   )
2. MarkdownPlugin embeds query text → target_vector
3. Calls retrieve_by_vector_similarity(
       target_vector=...,
       tenant_ids=["user-123", "user-456"],
       metadata_filters={"activity_type": "outdoor"}
   )
4. KNN fetches candidates (over-fetched to account for filters)
5. Post-filter: tenant_id IN list, json_extract matches
6. Composite scoring: distance - (usage_score * weight * decay)
7. Return top-k results with tenant_id in each result dict
```

## Execution Plan

### Task 1: Schema and Storage Layer
- Add `tenant_id` column to `documents` table.
- Update indexes (drop old composite, create tenant-aware composite + tenant index).
- Update `save_payload` with required `tenant_id`.
- Update `delete_by_uri` with required `tenant_id`.
- Update `lookup_existing_docs` with required `tenant_id`.
- Handle database migration for existing databases.
- *Stories:* STORY-001

### Task 2: Tenant-Scoped Idempotency
- Update `_build_contexts` in `IngestionPipeline` to pass `tenant_id`.
- Verify idempotent ingestion works correctly with tenant scoping.
- Same URI + different tenant = separate documents.
- Same URI + same tenant = idempotent update.
- *Stories:* STORY-002

### Task 3: Ingestion Pipeline Threading
- Add `tenant_id` to `IngestionBundle`.
- Add `tenant_id` to `IngestionEvent`.
- Pipeline propagates `tenant_id` from bundle to processors to events.
- MarkdownPlugin passes `tenant_id` through to `save_payload`.
- *Stories:* STORY-003

### Task 4: Tenant-Filtered Vector Search
- Add `tenant_ids` parameter to `retrieve_by_vector_similarity`.
- Add `d.tenant_id IN (...)` WHERE clause when `tenant_ids` is provided.
- Adjust over-fetch multiplier when tenant filter is active.
- Include `tenant_id` in result dicts.
- *Stories:* STORY-004

### Task 5: Metadata Search Filters
- Add `metadata_filters` parameter to `retrieve_by_vector_similarity`.
- Generate `json_extract(d.metadata, '$.key') = ?` clauses for each filter.
- Adjust over-fetch multiplier when metadata filters are active.
- *Stories:* STORY-005

### Task 6: Optional Vector Query
- Make `target_vector` optional in `retrieve_by_vector_similarity`.
- When `None`, query `documents` table directly (no `vec_documents` join).
- Rank by composite weight score (usage_score * decay) descending.
- *Stories:* STORY-006

### Task 7: MCP Tools and CLI
- Update `semantic_search` tool with `tenant_ids` and `metadata_filters` params, make `query` optional.
- Update `ingest_documents` tool with `tenant_id` param (default `"default"`).
- Update CLI with `--tenant-id` flag.
- *Stories:* STORY-007

### Task 8: Update Existing Tests
- All existing tests must pass with `tenant_id` threaded through.
- Update test helpers/fixtures to include `tenant_id`.
- Add focused tests for tenant isolation (same URI, different tenants).
- *Stories:* STORY-008

### Task 9: Documentation
- Update system overview with multi-tenancy model.
- Update plugin developer guide with `tenant_id` requirements.
- Update ADR-002 with cross-references.
- Update roadmap with SPEC-010 status.
- *Stories:* STORY-009
