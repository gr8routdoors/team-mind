# ADR-009: Document Segments — Explicit Parent-Child Hierarchy

**Status:** Accepted
**Date:** 2026-03-29
**Spec:** SPEC-011 (Document Segments)
**See also:** [ADR-003: Relevance Weighting](ADR-003-relevance-weighting.md), [ADR-008: Multi-Tenancy & Metadata Search](ADR-008-multi-tenancy-metadata-search.md), [Plugin Developer Guide](../plugin-developer-guide.md)

## Context

Two independent plugins have converged on the same pattern: splitting a logical document into multiple independently-weighted rows in the `documents` table.

1. **MarkdownPlugin** splits a source file into paragraph-level chunks. Each paragraph gets its own row, vector embedding, and weight. The reason is retrieval precision — embedding an entire 50-paragraph document produces a diluted vector that weakly matches any specific query. Paragraph-level embeddings produce stronger matches for targeted searches.

2. **Travel plugin** (in development) stores each user preference as its own row. The reason is weighting granularity — if all of a user's sports preferences were one document, downvoting the Bears would drag down the Bulls. Independent rows allow independent weighting.

Both plugins end up with multiple rows sharing the same URI, with no formal relationship between them. The MarkdownPlugin's chunks are orphaned siblings — you can't navigate from one chunk to its source file's other chunks without URI-based queries. The travel plugin would face the same problem.

### The micro-document pattern

ADR-003 established that "the unit of weighting is the row" and that "plugins that want finer-grained weighting chunk smaller during ingestion." This is correct, and it leads to what we've called the **micro-document pattern** — storing one independently-ratable knowledge atom per row.

ADR-008 acknowledged this pattern as intentional and introduced metadata search to make it viable (reconstituting logical groupings at query time via metadata filters). But metadata-based grouping is a plugin convention, not a framework concept. Every plugin invents its own way to tie atoms back to their logical parent.

### What's missing

The framework has no concept of "these rows belong together." Specifically:

- **No parent-child relationship.** You can't ask "what document does this chunk come from?" or "what are all the chunks in this document?" without knowing the plugin's URI conventions.
- **No parent-level context.** A search result returns a chunk with no way to navigate to its siblings or understand its broader context.
- **No aggregate scoring.** You can't ask "what's the overall value of this user's sports preference profile?" without manually querying and averaging across rows.
- **Each plugin reinvents grouping.** MarkdownPlugin uses shared URIs. The travel plugin would use metadata fields. A code plugin might use file paths. No consistency.

## Decision

We introduce a formal **parent-child relationship** on the `documents` table via a `parent_id` column. This makes the existing micro-document pattern explicit without adding a second table or changing the fundamental storage model.

### 1. Schema: `parent_id` on `documents`

```sql
ALTER TABLE documents ADD COLUMN parent_id INTEGER REFERENCES documents(id);
CREATE INDEX idx_documents_parent_id ON documents(parent_id);
```

- `parent_id = NULL` — This is a root document (either a standalone document or a parent with children).
- `parent_id = <id>` — This is a segment (child) of the referenced document.

**Why not a separate `segments` table:** A segment needs everything a document already has — URI, metadata, vector, weight, semantic_type. A separate table would duplicate the entire schema. Using `parent_id` on the same table means all existing query machinery (vector search, metadata filters, weight joins, tenant scoping) works on segments without modification.

### 2. Parent Documents — Containers, Not Searchable Units

A parent document is a row that serves as a logical container:

- Has its own URI, semantic_type, record_type, metadata. (Tenant scoping is structural — the database file IS the tenant, per ADR-010.)
- **Has no vector embedding** — it is not a searchable unit in KNN.
- **Has no `doc_weights` row** — its effective score is derived from its children (see below).
- Stores document-level metadata (e.g., `{"profile_type": "sports", "user_name": "Alice"}` for a travel profile, or `{"source_file": "architecture.md", "last_modified": "2026-03-29"}` for a markdown file).

Since the parent has no vector, it will never appear in vector search results. It exists for grouping, context, and aggregate scoring.

### 3. Segments — The Searchable, Ratable Atoms

A segment is a row with `parent_id` pointing to its parent:

- Has its own URI (can match the parent's or be unique).
- Has its own metadata (segment-level attributes).
- Has its own vector embedding — this is what KNN searches match against.
- Has its own `doc_weights` row — this is what gets independently rated.

Segments are the unit of retrieval and the unit of weighting. This formalizes what plugins already do.

### 4. Parent Scoring as Child Aggregate

A parent's effective score is **computed at query time** as the average of its non-tombstoned children's scores:

```sql
SELECT p.id, p.uri, p.metadata,
       AVG(w.usage_score) AS aggregate_score,
       COUNT(s.id) AS segment_count
FROM documents p
JOIN documents s ON s.parent_id = p.id
JOIN doc_weights w ON s.id = w.doc_id
WHERE p.id = ?
  AND COALESCE(w.tombstoned, 0) = 0
GROUP BY p.id
```

**Why computed, not stored:**
- Always consistent — no sync problem between parent score and child updates.
- No additional write overhead on feedback signals (updating a child's weight doesn't cascade to the parent row).
- Parents don't need a `doc_weights` row, simplifying the model.

**Why average, not sum or max:**
- Average reflects the overall quality of the collection. A parent with 10 highly-rated segments and 2 poorly-rated ones still scores well overall.
- Sum would bias toward parents with more segments (larger documents score higher just for being larger).
- Max would ignore the overall quality distribution.
- A parent with all tombstoned children effectively has no score — it's empty.

### 5. Search Results Include Parent Context

Search results (from `retrieve_by_vector_similarity`) gain a `parent_id` field:

```json
{
  "id": 57,
  "uri": "user://user-123/sports/nfl-bears",
  "parent_id": 42,
  "metadata": {"league": "nfl", "team": "bears"},
  "usage_score": 3.2,
  "final_rank": 0.45
}
```

Note: `tenant_id` is not in StorageAdapter results — it operates within a single per-tenant database (per ADR-010). `TenantStorageManager` injects `tenant_id` during scatter-gather.

When `parent_id` is non-null, the client knows this result is a segment and can look up its parent and siblings for broader context.

### 6. Discoverability: Get Document with Segments

A new storage method enables navigation from a segment to its full context:

```python
def get_document_with_segments(self, doc_id: int) -> dict:
    """Return a document with its child segments and aggregate score.

    If doc_id is a parent: returns parent metadata + all child segments.
    If doc_id is a segment: returns parent metadata + all sibling segments.
    If doc_id is standalone (no parent, no children): returns just the document.
    """
```

This is the discoverability path: "I found this segment in search — what else is in its parent?" A single call returns the full context without the client needing to know the plugin's grouping conventions.

### 7. Ingestion: Creating Parents and Segments

Plugins create parent-child relationships during ingestion:

```python
# Create parent first, then segments
# (StorageAdapter has no tenant_id parameter — it operates on a per-tenant
# database routed by TenantStorageManager, per ADR-010)
parent_id = storage.save_parent(
    uri="user://user-123/sports-preferences",
    plugin="travel_plugin",
    record_type="interest_profile",
    metadata={"profile_type": "sports"},
    semantic_type="travel_preferences",
)

for interest in user_interests:
    storage.save_payload(
        uri=f"user://user-123/sports/{interest['team']}",
        parent_id=parent_id,           # Links to parent
        plugin="travel_plugin",
        record_type="sport_interest",
        metadata={"league": interest["league"], "team": interest["team"]},
        vector=embed(f"{interest['league']} {interest['team']} fan"),
        ...
    )
```

**`save_parent`** is a new lightweight storage method that creates a document row without a vector or weight. It validates that the referenced tenant exists and returns the `doc_id` for child segments to reference.

**Backward compatibility:** `parent_id` defaults to `NULL`. Existing plugins that don't use segments continue to work identically — their rows are standalone documents with no parent. No code changes required for existing plugins.

### 8. Idempotent Ingestion with Segments

`delete_by_uri` gains awareness of parent-child relationships:

- When deleting a parent document, all its child segments (and their vectors and weights) are also deleted.
- When deleting a specific segment, only that segment is removed — the parent and siblings are unaffected.
- The idempotency key remains `(uri, plugin, record_type)` — tenant scoping is structural (per-tenant database file, per ADR-010).

For MarkdownPlugin's wipe-and-replace pattern: deleting by the source file's URI removes the parent and all paragraph segments, then re-ingestion creates a new parent with new segments.

### 9. What Segments Do and Don't Solve

**What segments solve:**
- **Discoverability.** Framework-level navigation from segment to parent and siblings.
- **Grouping semantics.** Parent document provides context (URI, metadata) for its children. No plugin-invented conventions.
- **Aggregate scoring.** "What's the overall value of this profile?" is a framework query, not plugin logic.
- **Consistency.** Every plugin uses the same parent-child mechanism. Clients can navigate any plugin's data uniformly.

**What segments don't solve:**
- **Row count.** You still have one row per ratable knowledge atom. Segments may add one more row (the parent) per logical document.
- **The atom-per-row reality.** Vector search is inherently atom-level. The unit of embedding, retrieval, and weighting remains the row.
- **Storage reduction.** The micro-document pattern remains at the storage level — segments make it structured, not eliminated.

Segments are a **structural improvement** (explicit hierarchy, framework-level grouping, aggregate scoring) not a **storage reduction**. The honest statement is: the micro-document pattern is the right architecture for a vector-search + per-item-weighting system, and segments make it first-class rather than ad-hoc.

## Alternatives Considered

### 1. Separate `segments` table

Create a dedicated table for segments with its own schema.

**Rejected because:**
- A segment needs the same fields as a document (URI, metadata, vector, weight).
- Duplicating the schema means duplicating all query logic — vector search, metadata filters, weight joins.
- A `parent_id` column on the existing table achieves the same relationship with zero duplication.

### 2. JSON path weighting on parent documents

Store all segments as nested JSON within a single parent document and weight individual JSON paths.

**Rejected because:**
- `json_extract` per-row is a full scan — no index can help for dynamic paths.
- Vector search requires per-atom embeddings, which would still need separate rows or a secondary structure.
- Weight updates via `json_set` re-serialize the entire JSON blob — O(document size) per feedback signal.
- The segment-per-row approach uses indexed columns for weights and native KNN for vectors — both O(1) or O(log n).

### 3. Stored parent weights (materialized aggregate)

Store the parent's aggregate score in a `doc_weights` row, updated on every child weight change.

**Rejected because:**
- Every feedback signal on a child would trigger a cascading update to the parent's weight.
- Creates write amplification and potential consistency issues under concurrent feedback.
- Computed-at-query-time is simpler, always consistent, and the SQL aggregate is fast (small number of children per parent).

### 4. Parent documents with their own vector embeddings

Give parent documents a summary or composite vector for inclusion in KNN search.

**Deferred because:**
- Generating a meaningful parent vector (summary embedding, centroid of children) adds complexity to the ingestion contract.
- It's unclear what the parent vector should represent — the summary of all children? The metadata? The title?
- Starting without parent vectors keeps the model clean: search returns segments, navigation reveals parents.
- Can be added later as an optional feature if parent-level search proves valuable.

### 5. Don't formalize segments — keep it as a plugin convention

Let plugins continue using shared URIs, metadata fields, or naming conventions to group related documents.

**Rejected because:**
- Two plugins already independently need this pattern (MarkdownPlugin + travel plugin).
- Without framework support, every plugin invents its own grouping convention.
- Clients can't navigate between related documents without understanding each plugin's conventions.
- Aggregate scoring would require per-plugin query logic.

## Consequences

### Positive

- **Framework-level grouping.** Every plugin's parent-child relationships are expressed the same way and navigable the same way.
- **Discoverability.** "I found this segment — show me its context" is a single framework call.
- **Aggregate scoring.** Parent-level quality assessment computed from children's weights — no plugin logic needed.
- **Backward compatible.** `parent_id = NULL` is the default. Existing plugins and data are unaffected.
- **No new tables.** One column addition to `documents`, one new index. Minimal schema complexity.
- **Composes with SPEC-010.** Tenant scoping + metadata filters + segments work together naturally: "show me all segments of type `sport_interest` for tenant `user-123` where `league = nfl`."

### Negative

- **Parent rows have no vector.** Parents are invisible to KNN search by design. If a use case needs parent-level search, a composite vector feature would need to be added later.
- **Cascade deletes add complexity.** `delete_by_uri` on a parent must also delete children. The storage layer needs to handle this correctly.
- **One more row per logical document.** Parents are additional rows that don't participate in search. Marginal storage cost, but non-zero.
- **Plugin contract expansion.** Plugins that want to use segments need to learn `save_parent` + `parent_id` on `save_payload`. Not required — purely opt-in.

### Neutral

- The `doc_weights` table is unchanged. Only segments (children) have weight rows. Parents derive their score at query time.
- The `vec_documents` table is unchanged. Only segments have vector embeddings.
- ADR-003's statement that "the unit of weighting is the row" remains true. Segments formalize this, they don't change it.
- MarkdownPlugin's paragraph chunking becomes an explicit parent-child relationship. The behavior is the same, just formally structured.
