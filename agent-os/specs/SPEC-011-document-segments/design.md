# SPEC-011: Document Segments — Design

## Overview

Adds a `parent_id` column to the `documents` table, enabling formal parent-child relationships. Parent documents are metadata containers with no vector or weight. Segments are searchable, ratable children. MarkdownPlugin is updated to use this pattern. Documentation is updated across the project.

## Design Amendments (vs Original Spec)

| Amendment | Original | Revised |
|-----------|----------|---------|
| `tenant_id` on StorageAdapter methods | Required parameter on `save_parent`, `save_payload`, `delete_by_uri` | Removed — `TenantStorageManager` routes to the correct database (per ADR-010) |
| Idempotency key | `(uri, plugin, record_type, tenant_id)` | `(uri, plugin, record_type)` — tenant is the database |
| `delete_by_id` | Not present | **New** — Surgical single-document delete, cascades automatically for parents |
| `delete_by_uri` cascade | Explicit cascade flag considered | Always cascades for parents — no flag needed |

## Components

| Component | Type | Change |
|-----------|------|--------|
| documents table | Storage | **Extended** — `parent_id INTEGER` column, new index. |
| StorageAdapter.save_parent | Storage | **New** — Creates parent document (no vector, no weight). |
| StorageAdapter.save_payload | Storage | **Extended** — Optional `parent_id` parameter. |
| StorageAdapter.retrieve_by_vector_similarity | Storage | **Extended** — `parent_id` in result dicts. |
| StorageAdapter.get_document_with_segments | Storage | **New** — Navigate parent/sibling relationships. |
| StorageAdapter.get_parent_aggregate_score | Storage | **New** — Computed AVG of children's scores. |
| StorageAdapter.delete_by_uri | Storage | **Extended** — Cascade delete children when deleting parent. |
| StorageAdapter.delete_by_id | Storage | **New** — Delete a single document by ID, cascade if parent. |
| MarkdownPlugin | Plugin | **Updated** — Creates parent per source file, segments per paragraph. |
| Plugin Developer Guide | Docs | **Updated** — Segment patterns, examples, fix stale references. |
| System Overview | Docs | **Updated** — Segment model, development status. |
| README.md | Docs | **Updated** — Development status. |
| ADR-002, ADR-003 | Docs | **Updated** — Cross-references to ADR-009. |

## Data Model

### Schema changes

```sql
-- Add parent_id to documents (nullable — NULL means root/standalone)
ALTER TABLE documents ADD COLUMN parent_id INTEGER REFERENCES documents(id);

-- Index for efficient child lookups
CREATE INDEX idx_documents_parent_id ON documents(parent_id);
```

### Document types by `parent_id` value

| `parent_id` | Has children? | Type | Vector? | Weight? |
|-------------|---------------|------|---------|---------|
| NULL | No | Standalone document (today's behavior) | Yes | Yes |
| NULL | Yes | Parent document | No | No (computed) |
| Non-null | — | Segment (child) | Yes | Yes |

### StorageAdapter.save_parent

```python
def save_parent(
    self,
    uri: str,
    plugin: str,
    record_type: str,
    metadata: dict | None = None,
    content_hash: str | None = None,
    plugin_version: str = "0.0.0",
    semantic_type: str = "",
    media_type: str = "",
) -> int:
    """Create a parent document — no vector embedding, no weight row.

    Returns the document ID for child segments to reference via parent_id.
    """
```

No `tenant_id` parameter — `StorageAdapter` operates on a single per-tenant database (per ADR-010). Tenant routing is handled by `TenantStorageManager`.

Implementation:
- INSERT into `documents` with all provided fields and `parent_id = NULL`.
- Do NOT insert into `vec_documents` (no vector).
- Do NOT insert into `doc_weights` (no weight — score is derived from children).
- Return the `id`.

### StorageAdapter.save_payload extension

```python
def save_payload(
    self,
    uri: str,
    metadata: dict,
    vector: list[float],
    plugin: str,
    record_type: str,
    parent_id: int | None = None,          # NEW — optional link to parent
    decay_half_life_days: float | None = None,
    content_hash: str | None = None,
    plugin_version: str = "0.0.0",
    semantic_type: str = "",
    media_type: str = "",
    initial_score: float = 0.0,
) -> int:
```

When `parent_id` is provided:
- Validate that the referenced parent document exists (SELECT by id).
- Raise `ValueError` if parent doesn't exist.
- Store `parent_id` on the inserted document row.

When `parent_id` is `None` (default):
- Behavior is identical to today — standalone document.

### StorageAdapter.retrieve_by_vector_similarity extension

Results gain `parent_id`:

```python
# In the SELECT clause, add:
# d.parent_id

# In the result dict:
{
    "id": row[0],
    "uri": row[1],
    "plugin": row[2],
    "record_type": row[3],
    "metadata": json.loads(row[4]) if row[4] else {},
    "parent_id": row[N],              # NEW — None for standalone/parent, int for segment
    "score": ...,
    "usage_score": ...,
    "final_rank": ...,
}
```

Parent documents (no vector) will never appear in KNN results. Only segments and standalone documents appear.

Note: `tenant_id` is not in the result dict from `StorageAdapter` — it operates within one shard. `TenantStorageManager.query_across_tenants` injects `tenant_id` into results during scatter-gather (see SPEC-010).

### StorageAdapter.get_document_with_segments

```python
def get_document_with_segments(self, doc_id: int) -> dict:
    """Return a document with its parent context and sibling segments.

    Behavior:
    - If doc_id is a parent (has children, no parent_id):
      Returns parent metadata + all non-tombstoned child segments with scores.
    - If doc_id is a segment (has parent_id):
      Returns parent metadata + all non-tombstoned sibling segments with scores.
    - If doc_id is standalone (no parent, no children):
      Returns just the document with an empty segments list.

    Returns:
        {
            "parent": {
                "id": 42,
                "uri": "user://user-123/sports-preferences",
                "plugin": "travel_plugin",
                "record_type": "interest_profile",
                "metadata": {"profile_type": "sports"},
                "aggregate_score": 2.8,
                "segment_count": 5,
            },
            "segments": [
                {
                    "id": 57,
                    "uri": "user://user-123/sports/nfl-bears",
                    "record_type": "sport_interest",
                    "metadata": {"league": "nfl", "team": "bears"},
                    "usage_score": 3.2,
                },
                ...
            ]
        }
    """
```

Implementation:
1. Fetch the document row for `doc_id`.
2. If it has `parent_id` → use `parent_id` as the root. Otherwise, `doc_id` is the root.
3. Fetch all children of the root: `SELECT ... FROM documents WHERE parent_id = ?`.
4. Join with `doc_weights` for scores, exclude tombstoned.
5. Compute aggregate score: `AVG(usage_score)` over non-tombstoned children.
6. Return structured dict.

### StorageAdapter.get_parent_aggregate_score

```python
def get_parent_aggregate_score(self, parent_id: int) -> dict:
    """Compute aggregate score for a parent from its children's weights.

    Returns:
        {
            "parent_id": 42,
            "aggregate_score": 2.8,
            "segment_count": 5,
            "min_score": -1.0,
            "max_score": 4.5,
        }
    """
```

SQL:
```sql
SELECT
    COUNT(s.id) AS segment_count,
    AVG(w.usage_score) AS aggregate_score,
    MIN(w.usage_score) AS min_score,
    MAX(w.usage_score) AS max_score
FROM documents s
JOIN doc_weights w ON s.id = w.doc_id
WHERE s.parent_id = ?
  AND COALESCE(w.tombstoned, 0) = 0
```

Returns `aggregate_score = None` and `segment_count = 0` if the parent has no non-tombstoned children.

### StorageAdapter.delete_by_uri extension — cascade delete

```python
def delete_by_uri(
    self,
    uri: str,
    plugin: str,
    record_type: str,
) -> int:
```

No `tenant_id` parameter — `StorageAdapter` operates on a single per-tenant database (per ADR-010).

Updated behavior:
1. Find matching documents (unchanged query).
2. For each matching document, check if it has children: `SELECT id FROM documents WHERE parent_id = ?`.
3. If children exist, collect all child IDs.
4. Delete weights, vectors, and document rows for both the parent and all children.
5. Return total count of deleted documents (parent + children).

This ensures wipe-and-replace ingestion patterns (like MarkdownPlugin's) cleanly remove the entire parent-child tree before re-ingestion.

### StorageAdapter.delete_by_id — surgical single-document delete

```python
def delete_by_id(self, doc_id: int) -> int:
    """Delete a single document by ID.

    If the document is a parent (has children), cascades: deletes all
    children's weights, vectors, and document rows, then deletes the parent.

    If the document is a segment (has parent_id), deletes only that segment.
    The parent and sibling segments are unaffected.

    If the document is standalone (no parent, no children), deletes it.

    Returns the total count of deleted documents.
    """
```

Implementation:
1. Fetch the document row for `doc_id`.
2. Check if it has children: `SELECT id FROM documents WHERE parent_id = ?`.
3. If children exist (parent): collect all child IDs, delete their weights, vectors, and rows, then delete the parent's row.
4. If no children: delete just this document's weight, vector, and row.
5. Return total count.

**No cascade flag.** A parent always cascades — there's no scenario where you'd delete a parent and leave orphaned children. A segment is always surgical — deleting one child doesn't affect siblings or the parent.

## URI Convention for Segments

Parent and segment URIs follow a convention that makes relationships discoverable without relying solely on `parent_id`:

- **Parent URI:** The logical resource identifier (e.g., `file:///path/to/doc.md`, `user://user-123/sports-preferences`).
- **Segment URI:** The parent URI with a segment-specific suffix (e.g., `file:///path/to/doc.md#chunk-0`, `user://user-123/sports/nfl-bears`).

This is a **convention, not a constraint**. The framework does not enforce URI structure — `parent_id` is the authoritative relationship. But following this convention makes URIs human-readable and enables URI-based queries to find related documents when `parent_id` is not available (e.g., in logs or debugging).

Plugins choose their own suffix scheme. MarkdownPlugin uses `#chunk-N` (zero-indexed). The travel plugin uses hierarchical path segments. The only rule: segment URIs should be derivable from or related to their parent's URI.

## MarkdownPlugin Migration

### Current behavior (pre-segments)

```python
# Creates N orphaned rows per source file, all sharing the same URI
for chunk in chunks:
    storage.save_payload(
        uri=uri,                    # Same URI for all chunks
        metadata={"chunk": chunk},
        vector=embed(chunk),
        plugin="markdown_plugin",
        record_type="markdown_chunk",
        ...
    )
```

### New behavior (with segments)

```python
# Create parent document for the source file
parent_id = storage.save_parent(
    uri=uri,
    plugin=self.name,
    record_type="markdown_source",      # New record type for parent
    metadata={"source_uri": uri, "chunk_count": len(chunks)},
    content_hash=current_hash,
    plugin_version=self.version,
    semantic_type=semantic_type,
    media_type=media_type,
)

# Create segment per paragraph chunk
for i, chunk in enumerate(chunks):
    storage.save_payload(
        uri=f"{uri}#chunk-{i}",         # URI convention: parent URI + segment suffix
        metadata={"chunk": chunk, "plugin": self.name},
        vector=embed(chunk),
        plugin=self.name,
        record_type="markdown_chunk",
        parent_id=parent_id,            # Link to parent
        content_hash=current_hash,
        plugin_version=self.version,
        semantic_type=semantic_type,
        media_type=media_type,
        initial_score=initial_score,
    )
```

**Changes to MarkdownPlugin:**
- New `record_types` entry: `RecordTypeSpec(name="markdown_source", ...)` for parent documents.
- `process_bundle` creates a parent first, then segments.
- `delete_by_uri` cascade handles cleanup — no change needed in the plugin's wipe-and-replace logic.

## Ingestion Pipeline Impact

### Pipeline context building

`_build_contexts` in `IngestionPipeline` is unchanged. The idempotency key is still `(uri, plugin, record_type)` — tenant scoping is structural (per-tenant database file, per ADR-010). Parent documents and their segments can have different record types (e.g., `markdown_source` vs. `markdown_chunk`), so they get separate contexts.

### IngestionEvent

No changes to `IngestionEvent` structure. The event reports `doc_ids` which may include both parent IDs and segment IDs. Observers that need to distinguish can query the document to check `parent_id`.

## Documentation Updates (STORY-009)

### Documents requiring updates

| Document | Updates needed |
|----------|---------------|
| **Plugin Developer Guide** | Add "Working with Segments" section. Update "Chunks are a plugin concept" to describe segments as the framework-level formalization. Fix stale `doctype`/`DoctypeSpec` references → `record_type`/`RecordTypeSpec` throughout code examples. Add ADR-008, ADR-009, SPEC-010, SPEC-011 to reference table. |
| **System Overview** | Add segments to architecture description. Update development status (SPEC-006 through SPEC-011). Add segment model to Three-Type Model section or as a new section. |
| **README.md** | Update development status section. SPEC-006 → complete. SPEC-007 → complete. SPEC-008 → complete. SPEC-009 → complete. Add SPEC-010 and SPEC-011. |
| **ADR-002** | Add cross-reference to ADR-009 in "See also" and "Neutral" consequences. Note that segments formalize the plugin chunking pattern. |
| **ADR-003** | Add cross-reference to ADR-009 in "See also". Note in "Neutral" consequences that segments formalize the "unit of weighting is the row" principle with explicit parent-child hierarchy. |

### Stale references to fix

The following documents contain stale `doctype`/`DoctypeSpec` references that should have been updated in SPEC-009 (record type rename):

| Document | Stale references |
|----------|-----------------|
| **Plugin Developer Guide** | `DoctypeSpec` in code examples (should be `RecordTypeSpec`). `doctypes` property (should be `record_types`). `doctype` parameter in `save_payload`/`delete_by_uri` examples (should be `record_type`). `list_doctypes` tool reference (should be `list_record_types`). `doctype` in table diagrams. Multiple `doctype` references in observer examples. |
| **ADR-002** | `IngestionEvent.doctype` in observer examples (may be partially updated). |

These are corrected as part of STORY-009 alongside the new segment documentation.

## Execution Plan

### Task 1: Schema
- Add `parent_id` column to `documents` table.
- Add `idx_documents_parent_id` index.
- Handle migration for existing databases.
- *Stories:* STORY-001

### Task 2: Save Parent
- Implement `save_parent()` on StorageAdapter.
- Creates document row, no vector, no weight.
- Returns doc_id.
- *Stories:* STORY-002

### Task 3: Parent ID on Save Payload
- Add optional `parent_id` parameter to `save_payload()`.
- Validate parent exists when provided.
- Store `parent_id` on document row.
- *Stories:* STORY-003

### Task 4: Search Results
- Add `parent_id` to result dicts from `retrieve_by_vector_similarity`.
- Add `d.parent_id` to SELECT clause.
- *Stories:* STORY-004

### Task 5: Get Document with Segments
- Implement `get_document_with_segments()`.
- Handles parent, segment, and standalone cases.
- Includes aggregate scoring.
- *Stories:* STORY-005

### Task 6: Aggregate Parent Scoring
- Implement `get_parent_aggregate_score()`.
- AVG of non-tombstoned children's usage_score.
- Returns count, min, max alongside aggregate.
- *Stories:* STORY-006

### Task 7: Delete Operations
- Update `delete_by_uri` to cascade delete children when a parent is matched.
- Implement `delete_by_id` for surgical single-document deletion with automatic parent cascade.
- Find children via `parent_id` lookup.
- Delete weights, vectors, document rows for parent + children (when applicable).
- *Stories:* STORY-007

### Task 8: MarkdownPlugin Migration
- Add `markdown_source` record type for parent documents.
- Update `process_bundle` to create parent + segments.
- Update wipe-and-replace logic (cascade delete handles this).
- Update existing MarkdownPlugin tests.
- *Stories:* STORY-008

### Task 9: Documentation, Diagrams, and Stale Reference Fixes
- Update plugin developer guide (segments section + stale reference fixes).
- Add mermaid diagrams to system overview and/or design docs:
  - Parent-child document hierarchy (parent → segments, standalone).
  - Ingestion flow with segments (save_parent → save_payload with parent_id).
  - Segment navigation flow (get_document_with_segments).
- Update system overview (segments model, development status).
- Update README (development status).
- Add cross-references to ADR-002, ADR-003.
- *Stories:* STORY-009
