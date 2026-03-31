# SPEC-012: Search Query Enhancements — Design

**Status:** in_design
**Created:** 2026-03-31

## Problem Statement

Two gaps exist in Team Mind's search layer after SPEC-010 (Multi-Tenancy & Metadata Search) shipped:

### Gap 1: No Semantic Type Filtering on Search (Priority)

The `semantic_type` column exists on the `documents` table (added in SPEC-008) and is indexed (`idx_documents_semantic_type`). It is populated at ingestion time via the ingestion pipeline's semantic type routing. However, **neither `retrieve_by_vector_similarity` nor `retrieve_by_weight` accepts `semantic_types` as a query parameter**.

This means callers cannot scope a search to "show me only architecture_docs" or "only meeting_transcripts" — even within a single tenant. This is a core framework gap: the data is there, the index is there, but the query path doesn't use it.

### Gap 2: DocumentRetrievalPlugin Not Wired for Cross-Tenant Queries

`FeedbackPlugin` was converted from `StorageAdapter` to `TenantStorageManager` in SPEC-010 (STORY-007). `DocumentRetrievalPlugin` was not — it still holds a single `StorageAdapter` in its constructor:

```python
class DocumentRetrievalPlugin(ToolProvider):
    def __init__(self, storage: StorageAdapter):
        self.storage = storage
```

This means the `retrieve_documents` and `get_full_document` MCP tools cannot:
- Accept `tenant_ids` to scope or scatter-gather across tenants
- Accept `semantic_types` to filter by semantic type
- Return results with `tenant_id` injected (the consistent result format established in SPEC-010)

The infrastructure exists (`TenantStorageManager.query_across_tenants`), but the MCP tool layer doesn't use it.

---

## Design

### 1. Semantic Type Filter on StorageAdapter

Add `semantic_types: list[str] | None` parameter to both retrieval methods:

```python
def retrieve_by_vector_similarity(
    self,
    target_vector: list[float],
    limit: int = 5,
    plugins: list[str] | None = None,
    record_types: list[str] | None = None,
    metadata_filters: dict[str, str] | None = None,
    semantic_types: list[str] | None = None,        # NEW
) -> list[dict]:

def retrieve_by_weight(
    self,
    limit: int = 5,
    plugins: list[str] | None = None,
    record_types: list[str] | None = None,
    metadata_filters: dict[str, str] | None = None,
    semantic_types: list[str] | None = None,        # NEW
) -> list[dict]:
```

#### Comma-Joined Semantic Type Matching

Per ADR-007, `documents.semantic_type` stores a **comma-joined string** for documents with multiple semantic types (e.g., `"architecture_docs,booking_service"`). A simple `IN (...)` clause won't match these multi-type values.

**Approach: INSTR-based matching.** For each requested semantic type, generate:

```sql
(d.semantic_type = ? OR INSTR(d.semantic_type, ?) > 0)
```

Combined with OR semantics across the list (ANY-match — same as EventFilter):

```sql
-- semantic_types=["architecture_docs", "meeting_transcripts"]
AND (
    (d.semantic_type = 'architecture_docs' OR INSTR(d.semantic_type, 'architecture_docs') > 0)
    OR
    (d.semantic_type = 'meeting_transcripts' OR INSTR(d.semantic_type, 'meeting_transcripts') > 0)
)
```

**Why INSTR over LIKE:** `INSTR` is more precise. `LIKE '%arch%'` would false-match `"search_docs"`. `INSTR(col, 'architecture_docs')` matches the exact substring. Since semantic type names are human-chosen identifiers (no commas in names), substring matching on comma-joined values is safe.

**Why not normalize to a join table:** The comma-joined storage was an intentional design decision in ADR-007 to keep the schema simple. A join table would be a schema migration and would complicate the KNN pipeline (additional JOIN in the already-constrained sqlite-vec query). The INSTR approach works within the existing schema.

#### Empty-List Short-Circuit

Consistent with `plugins` and `record_types`:

```python
if semantic_types is not None and len(semantic_types) == 0:
    return []
```

#### Over-Fetch Adjustment

Semantic type filtering is a post-KNN filter (same as plugin/record_type/metadata). The existing `KNN_OVERFETCH_MULTIPLIER = 4` applies — `has_filters` already checks for any active filter:

```python
has_filters = (
    plugins is not None
    or record_types is not None
    or bool(metadata_filters)
    or semantic_types is not None    # ADD THIS
)
```

#### Return Value Enhancement

Both methods should include `semantic_type` in the returned dict alongside existing fields (`id`, `uri`, `plugin`, `record_type`, `metadata`, etc.):

```python
{
    "id": 42,
    "uri": "file:///docs/arch.md",
    "plugin": "markdown_plugin",
    "record_type": "markdown_chunk",
    "semantic_type": "architecture_docs",    # NEW in results
    "metadata": {...},
    "final_rank": 0.23,
    ...
}
```

This is additive — no breaking change to existing result consumers.

### 2. DocumentRetrievalPlugin Cross-Tenant Conversion

Convert `DocumentRetrievalPlugin` from `StorageAdapter` to `TenantStorageManager`, following the same pattern as `FeedbackPlugin`:

```python
class DocumentRetrievalPlugin(ToolProvider):
    def __init__(self, tenant_manager: TenantStorageManager):
        self.tenant_manager = tenant_manager
```

#### Updated Tool Schema: `retrieve_documents`

```python
Tool(
    name="retrieve_documents",
    description="Search stored documents across tenants...",
    inputSchema={
        "type": "object",
        "properties": {
            "query_text": {
                "type": "string",
                "description": "Search query (required for vector mode).",
            },
            "query_mode": {
                "type": "string",
                "enum": ["vector", "weight"],
                "description": "...",
            },
            "metadata_filters": {
                "type": "object",
                "description": "Filter by metadata key-value pairs (AND semantics).",
            },
            "semantic_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by semantic types (ANY-match semantics).",
            },
            "tenant_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tenant shards to search (default: all tenants).",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results (default 10).",
            },
        },
        "required": [],
    },
)
```

#### Query Routing

All queries route through `query_across_tenants` for consistent result format:

```python
async def _retrieve_documents(self, arguments: dict) -> list[TextContent]:
    query_mode = arguments.get("query_mode", "vector")
    query_text = arguments.get("query_text")
    limit = int(arguments.get("limit", 5))
    metadata_filters = arguments.get("metadata_filters") or None
    semantic_types = arguments.get("semantic_types") or None
    tenant_ids = arguments.get("tenant_ids") or None

    if query_mode == "weight":
        def query_fn(adapter):
            return adapter.retrieve_by_weight(
                limit=limit,
                metadata_filters=metadata_filters,
                semantic_types=semantic_types,
            )
        results = self.tenant_manager.query_across_tenants(
            query_fn=query_fn,
            sort_key="weight_rank",
            sort_descending=True,
            tenant_ids=tenant_ids,
        )
    else:
        if not query_text:
            raise ValueError("query_text is required for vector mode")
        vector = _embed(query_text)
        def query_fn(adapter):
            return adapter.retrieve_by_vector_similarity(
                vector,
                limit=limit,
                metadata_filters=metadata_filters,
                semantic_types=semantic_types,
            )
        results = self.tenant_manager.query_across_tenants(
            query_fn=query_fn,
            sort_key="final_rank",
            sort_descending=False,
            tenant_ids=tenant_ids,
        )

    return [TextContent(type="text", text=json.dumps(results[:limit]))]
```

**Note:** `query_across_tenants` fetches `limit` per shard, then we trim the merged result to `limit`. This is the same pattern used by `semantic_search`.

#### Updated Tool: `get_full_document`

`get_full_document` also needs tenant awareness:

```python
Tool(
    name="get_full_document",
    inputSchema={
        "type": "object",
        "properties": {
            "uri": {"type": "string", "description": "The URI pointer"},
            "tenant_id": {
                "type": "string",
                "description": "Tenant to search in (default: 'default').",
            },
        },
        "required": ["uri"],
    },
)
```

The implementation resolves the adapter via `self.tenant_manager.get_adapter(tenant_id)`.

### 3. CLI and Existing Tool Updates

#### `semantic_search` Tool

The existing `semantic_search` MCP tool (in `cli.py` or wherever it's registered) should also gain the `semantic_types` parameter, forwarded through `query_across_tenants` to the storage adapter.

### 4. Documentation Updates

After features are implemented:

- **Plugin Developer Guide:** Add "Querying by Semantic Type" section explaining that semantic types set at ingestion time are available as query-time filters. Show examples of filtering by semantic type in both vector and weight modes.
- **System Overview / README:** Update the architecture description to mention semantic type filtering as a query capability (not just an ingestion routing mechanism).
- **ADR-007 Cross-Reference:** Add a note to ADR-007 that semantic type filtering on queries was added in SPEC-012, closing the loop on the three-type model (semantic types now used at both ingestion-time routing AND query-time filtering).

---

## Edge Cases

### Empty Semantic Type

Documents ingested before SPEC-008 (or without semantic types specified) have `semantic_type = ''` (empty string). The filter should **not** match these documents unless the caller explicitly requests `""`. This is natural behavior — `INSTR('', 'architecture_docs')` returns 0.

### Wildcard Semantic Type

No wildcard support on the query side. Omitting `semantic_types` (None) means "don't filter by semantic type" — return all documents regardless of semantic type. This is consistent with `plugins=None` and `record_types=None`.

### Cross-Tenant with Semantic Types

Both filters compose naturally. `tenant_ids=["team-a", "team-b"]` with `semantic_types=["architecture_docs"]` runs the semantic-type-filtered query on each shard, then merges.

### Parent Documents (Segments)

Parent documents have `semantic_type` set (inherited from the bundle). Segments inherit the parent's semantic type at write time (via `save_payload`). Filtering by semantic type naturally includes both parents and segments. Since parent documents are metadata-only (no embedding), they won't appear in vector search results but will appear in weight-ranked results — consistent with existing behavior.

---

## Non-Goals

- **Full-text search on semantic type names.** We don't need fuzzy matching or partial semantic type search. Exact match (or exact substring in comma-joined values) is sufficient.
- **Semantic type CRUD via MCP tools.** Managing semantic types is an admin/registration concern, not a query concern.
- **Parallel scatter-gather.** Sequential shard queries remain the MVP approach (per SPEC-010 design).
- **EventFilter changes.** EventFilter already supports `semantic_types` (added in SPEC-008). No changes needed.
