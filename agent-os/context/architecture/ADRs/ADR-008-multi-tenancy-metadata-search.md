# ADR-008: Required Multi-Tenancy and Metadata Search

**Status:** Accepted (amended by [ADR-010: Tenant Sharding](ADR-010-tenant-sharding.md) — tenancy implemented via file-level sharding, not a column)
**Date:** 2026-03-29
**Spec:** SPEC-010 (Multi-Tenancy & Metadata Search)
**See also:** [ADR-003: Relevance Weighting](ADR-003-relevance-weighting.md), [ADR-007: Semantic Type Routing](ADR-007-semantic-type-routing.md), [ADR-010: Tenant Sharding](ADR-010-tenant-sharding.md)

## Context

While developing a travel plugin that aggregates user interest profiles, a fundamental design gap emerged: Team Mind has no mechanism to isolate data by owner. The travel plugin serves multiple users, each with their own preferences (sports teams, destinations, activities). The only way to keep user data separate today is to encode the user ID into the URI — e.g., `sports-interest/user-123/nfl/bears`.

This works for basic isolation but creates three problems:

1. **URI conflation.** The URI was designed to represent *where content comes from* (a file, a URL, a virtual resource). Encoding ownership into the URI conflates resource identity with data ownership. The same conceptual resource (NFL Bears interest) can't exist at a clean URI across multiple users.

2. **No cross-owner queries.** There's no way to ask "what sports interests exist across all users?" without fragile URI prefix matching. The storage layer has no indexed ownership dimension to query against.

3. **Metadata is write-only.** The `documents.metadata` JSON column stores rich structured data (interest categories, leagues, destinations, price ranges), but no query path filters on it. `retrieve_by_vector_similarity` — the only real search — never touches metadata. So metadata is returned *after* retrieval but can't *guide* retrieval.

These issues compound: without tenant isolation, ownership goes into URIs. Without metadata search, domain-specific attributes can't be queried. The result is that URIs become overloaded as the sole axis of identity, hierarchy, and filtering — a role they weren't designed for.

### The micro-document pattern

A related tension emerged from ADR-003's design: weighting operates at the document (row) level. If a user's "sports preferences" are stored as one document, downvoting the Bears would drag down all their sports preferences. This forces applications toward a **micro-document pattern** — one independently-ratable fact per row.

With metadata search and tenant isolation, this pattern becomes viable: logical groupings can be reconstituted at query time via metadata filters ("give me all of user-123's sports preferences"), while individual facts retain independent weighting. The "document" in Team Mind is effectively a **knowledge unit**, not a file or page.

We acknowledge this pattern will increase row counts. Tenant-based sharding is a natural mitigation, and cross-tenant queries being slower is an acceptable trade-off since they are inherently more expensive operations.

### No backward compatibility constraints

Team Mind has not been deployed externally. All usage is internal dogfooding. This ADR does not need to preserve backward compatibility — we can make breaking changes to the schema, API, and plugin contract.

## Decision

We introduce **required multi-tenancy** via a `tenant_id` field on all documents, and **metadata search** as a query-time filtering mechanism on the existing JSON metadata column. Both capabilities are added to the existing `semantic_search` tool rather than introducing new tools.

### 1. Required `tenant_id` with Default Tenant

Every document belongs to exactly one tenant. `tenant_id` is a required, non-null field on the `documents` table.

```sql
ALTER TABLE documents ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default';
```

**Design rules:**
- `tenant_id` is always required at the storage layer — no null, no empty string.
- The MCP tool layer defaults to `"default"` for ergonomics — callers that don't care about tenancy get a sensible default without special code paths.
- The default tenant `"default"` is a regular tenant — no special semantics, no special code paths. Single-tenant deployments just use it and never think about it.
- The composite identity key becomes `(uri, plugin, record_type, tenant_id)` — the same URI can exist in different tenants without collision.

**Why required, not optional:**
- Eliminates null/empty-string ambiguity. Every document has an owner, always.
- No "unscoped" mode that means something subtly different from scoped queries.
- Applications that don't need multi-tenancy pass `"default"` (or let the tool layer do it) and pay no complexity cost.
- Bakes tenancy into the data model from day one rather than retrofitting it later with edge cases around pre-tenancy data.

**Threading:** `tenant_id` flows through the full stack:
- `IngestionBundle` gains `tenant_id: str` (set by caller, defaults to `"default"`)
- `save_payload()` requires `tenant_id` parameter
- `delete_by_uri()` scopes by `tenant_id`
- `lookup_existing_docs()` scopes by `tenant_id`
- `retrieve_by_vector_similarity()` accepts `tenant_ids: list[str] | None` for query-time filtering
- `IngestionEvent` carries `tenant_id` for observer awareness

### 2. Metadata Search via `json_extract`

The existing `metadata` JSON column becomes queryable at search time through optional filter parameters.

**Filter model:**
```python
# Simple equality filters on metadata paths
metadata_filters = {
    "interest_category": "sports",
    "league": "nfl"
}
# Translates to:
# WHERE json_extract(metadata, '$.interest_category') = 'sports'
#   AND json_extract(metadata, '$.league') = 'nfl'
```

**Integration with existing search:**
- `semantic_search` gains an optional `metadata_filters: dict` parameter.
- Metadata filters are applied as additional WHERE clauses alongside existing `plugin` and `record_type` filters.
- When metadata filters are present, the KNN over-fetch multiplier increases to compensate for additional post-filtering.
- Vector query (`query` parameter) becomes optional — when omitted, results are ranked by weight/decay score alone (pure metadata query). This enables structured retrieval without requiring semantic similarity.

**Why extend `semantic_search` rather than a new tool:**
- A separate tool would bypass weighting, decay, and composite scoring. These are valuable even for metadata-filtered queries.
- Keeping one tool avoids fragmenting the query surface. The parameters compose naturally: vector similarity + metadata filters + tenant scoping + weight ranking.
- Pure metadata queries (no vector) are just a degenerate case where one parameter is omitted.

### 3. Cross-Tenant Query Model

Queries accept a list of tenant IDs, not a single value:

```python
# Search within one tenant
semantic_search(query="hiking trails", tenant_ids=["user-123"])

# Search across specific tenants
semantic_search(query="hiking trails", tenant_ids=["user-123", "user-456"])

# Search across all tenants (omit parameter)
semantic_search(query="hiking trails")
```

**Design rules:**
- `tenant_ids` is optional on search. When omitted, all tenants are searched.
- When provided, only documents in the listed tenants are returned.
- This is a query-time concern — no data copying or cross-tenant writes.
- Permission gating on which tenants a caller can query is a future concern. We note it here but do not solve it in this spec.

### 4. Structural Fields vs. Metadata Fields

With metadata becoming searchable, it's important to clarify what belongs as a first-class column vs. what belongs in metadata:

| | First-class columns | Metadata fields |
|---|---|---|
| **Purpose** | Framework routing, identity, and system behavior | Domain-specific attributes for query-time filtering |
| **When used** | Ingestion-time routing + query-time filtering | Query-time filtering only |
| **Who controls** | Framework / pipeline | Plugins / domain logic |
| **Examples** | `tenant_id`, `plugin`, `record_type`, `semantic_type`, `media_type` | `interest_category`, `league`, `destination`, `price_range` |
| **Indexed** | Dedicated B-tree indexes | `json_extract` (potentially generated column indexes for hot paths) |

**The rule:** If the framework/pipeline needs it to make routing or identity decisions, it's a column. If only consumers need it at query time, it's metadata.

`semantic_type` retains its column because it drives ingestion-time routing — the pipeline uses it to match documents to processors *before* they're stored. Metadata search is a query-time mechanism and cannot serve this role.

### 5. Schema Changes

```sql
-- Required tenant_id on all documents
ALTER TABLE documents ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default';

-- Updated composite identity index
DROP INDEX IF EXISTS idx_documents_uri_plugin_record_type;
CREATE INDEX idx_documents_uri_plugin_record_type_tenant
    ON documents(uri, plugin, record_type, tenant_id);

-- Tenant query index
CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
```

### 6. Future Consideration: Sub-Document Segments

The micro-document pattern (one ratable fact per row) works today but may create scaling pressure. A future evolution could introduce a formal `segments` table — documents as logical containers with independently weighted segments inside them. This would formalize the parent-child relationship that already exists implicitly (MarkdownPlugin creates multiple rows per source file).

**We defer this to a future ADR.** The micro-document pattern is sufficient for current use cases, and metadata search makes reconstituting logical groupings viable. If two or more plugins independently need sub-document weighting, that signals the pattern is real and worth formalizing. Early indicators from the travel plugin and markdown chunking suggest this is likely — but we want to design it deliberately rather than prematurely.

## Design Amendment: Tenant Sharding (ADR-010)

During design review of the implementation approach, analysis of KNN behavior at scale revealed that a `tenant_id` column with post-filter WHERE clauses is provably incorrect for multi-tenant vector search. sqlite-vec performs KNN globally before applying WHERE clauses, so at 1K+ tenants the vast majority of KNN candidates are discarded and too few results are returned.

**ADR-010** replaces the column-based approach with **file-level sharding**: each tenant gets its own SQLite database. KNN operates within a tenant's shard by construction — no post-filtering needed.

The following decisions from ADR-008 are **amended**:

| Original Decision | Amended To | Rationale |
|---|---|---|
| `tenant_id TEXT NOT NULL` column on `documents` | **Removed.** The database file IS the tenant scope. | No column needed when data is physically separated. |
| Composite key `(uri, plugin, record_type, tenant_id)` | **Reverts to `(uri, plugin, record_type)`.** | Tenant scoping is file-level, not key-level. |
| `tenant_id` on `save_payload`, `delete_by_uri`, `lookup_existing_docs` | **Removed from StorageAdapter signatures.** `TenantStorageManager` routes to the correct database. | StorageAdapter operates on one database and doesn't know about tenants. |
| `tenant_ids` filter on `retrieve_by_vector_similarity` | **Removed.** Cross-tenant queries use scatter-gather across databases. | KNN within a shard is always correct; cross-shard is merge-and-sort. |
| KNN over-fetch multiplier adjustment for tenant filters | **No longer needed.** Existing 4x constant is adequate at per-tenant data scale. | The extreme selectivity problem doesn't exist within a shard. |

The following decisions from ADR-008 are **unchanged**:

- Required tenancy with default tenant `"default"` — still true, just structural rather than a column.
- `IngestionBundle` and `IngestionEvent` carry `tenant_id` — for pipeline routing and observer awareness.
- `semantic_search` accepts `tenant_ids` parameter — scatter-gather is transparent to callers.
- `ingest_documents` accepts `tenant_id` parameter — routes to the correct shard.
- Metadata search via `json_extract` — unchanged, operates within a shard.
- Structural fields vs. metadata fields boundary — unchanged.

See [ADR-010](ADR-010-tenant-sharding.md) for full rationale.

## Alternatives Considered

### 1. Optional `tenant_id` with empty-string default

Make `tenant_id` optional, defaulting to `""` for non-tenant-aware callers.

**Rejected because:**
- Creates ambiguity: does `""` mean "no tenant", "default tenant", or "global scope"?
- Forces every query path to handle both tenanted and un-tenanted documents.
- Since there's no deployed data, there's no reason to accept this complexity.

### 2. Separate metadata query tool

Create a new `query_documents` MCP tool for metadata-only queries.

**Rejected because:**
- Loses weighting, decay, and composite scoring. These are valuable even for structured queries.
- Fragments the query surface — callers would need to choose between two tools.
- A single tool with composable parameters is simpler and more powerful.

### 3. Dedicated metadata columns instead of JSON search

Add columns like `category TEXT`, `subcategory TEXT` for commonly filtered fields.

**Rejected because:**
- The set of filterable metadata fields is unbounded and plugin-specific. Travel plugins filter on `league` and `destination`; code plugins might filter on `language` and `framework`.
- Adding columns for every domain-specific attribute doesn't scale.
- SQLite's `json_extract` is efficient for this pattern, and generated column indexes can optimize hot paths if needed.

### 4. Encode tenant in URI (current workaround)

Continue using URI path segments for tenant isolation.

**Rejected because:**
- Conflates resource identity with ownership.
- Makes cross-tenant queries impossible without URI pattern matching.
- Forces every plugin to embed and parse tenant IDs from URI conventions.

### 5. Sub-document weighting (segments) now

Introduce a formal segments table to solve the micro-document pattern alongside tenancy.

**Deferred because:**
- Adds significant complexity to the storage layer and plugin contract.
- The micro-document pattern is workable with metadata search for reconstituting groupings.
- Better to validate the need with real usage before committing to the abstraction.
- Documented as a future consideration in this ADR and will be revisited once more plugins exercise the pattern.

## Consequences

### Positive

- **Clean data isolation.** Every document belongs to a tenant. No ambiguity, no special cases.
- **Cross-tenant queries.** Search across specific tenants or all tenants with a single parameter.
- **Metadata-driven retrieval.** Domain-specific attributes become first-class query filters without schema changes per plugin.
- **URI clarity.** URIs return to representing resource identity, not ownership. `sports-interest/nfl/bears` is the resource; `tenant_id="user-123"` is the owner.
- **Composable queries.** Vector similarity, metadata filters, tenant scoping, and weight ranking compose in a single tool call.
- **Micro-document viability.** Metadata search makes the micro-document pattern practical by enabling logical grouping at query time.

### Negative

- **Every caller must specify tenant_id.** Even single-tenant deployments pass `"default"` (though the MCP tool layer defaults this). This is a trade-off for API clarity.
- **KNN over-fetch increases.** More filters (metadata + tenant) mean more candidates are discarded post-KNN. The over-fetch multiplier must increase to compensate, using more memory during queries.
- **json_extract performance.** Without generated column indexes, metadata filtering scans JSON blobs. Acceptable for current scale; may need optimization at higher volumes.
- **Micro-document row explosion.** Applications that store fine-grained facts will generate more rows. Tenant-based sharding mitigates this, but cross-tenant aggregation queries will be slower.

### Neutral

- The `IngestionBundle` gains one required field (`tenant_id`). Simple to thread through.
- Existing tests will need updates for the new required parameter. Since there's no backward compatibility concern, this is mechanical.
- Permission gating on cross-tenant queries is noted as future work but not addressed here.
