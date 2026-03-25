# STORY-003: Scoped Storage Queries — Acceptance Criteria

> ACs for extending vector similarity search with plugin and doctype filter lists.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Unfiltered Search Returns All | Happy path |
| AC-002 | Filter by Single Doctype | Happy path |
| AC-003 | Filter by Multiple Doctypes | Happy path |
| AC-004 | Filter by Single Plugin | Happy path |
| AC-005 | Filter by Multiple Plugins | Happy path |
| AC-006 | Combined Plugin and Doctype Filter | Integration |
| AC-007 | Empty Filter List Returns Nothing | Edge case |
| AC-008 | Post-Filter Behavior with KNN Limit | Edge case |

---

## Acceptance Criteria

### AC-001: Unfiltered Search Returns All

**Given** documents from multiple plugins and doctypes exist in storage
**When** `retrieve_by_vector_similarity` is called with no `plugins` or `doctypes` filters
**Then** results include documents from all plugins and doctypes
**And** results are ordered by vector similarity

---

### AC-002: Filter by Single Doctype

**Given** documents with doctypes `"type_a"` and `"type_b"` exist
**When** `retrieve_by_vector_similarity` is called with `doctypes=["type_a"]`
**Then** only documents with `doctype = "type_a"` are returned

---

### AC-003: Filter by Multiple Doctypes

**Given** documents with doctypes `"type_a"`, `"type_b"`, and `"type_c"` exist
**When** `retrieve_by_vector_similarity` is called with `doctypes=["type_a", "type_b"]`
**Then** only documents with `doctype` in `("type_a", "type_b")` are returned
**And** documents with `doctype = "type_c"` are excluded

---

### AC-004: Filter by Single Plugin

**Given** documents from plugins `"plugin_x"` and `"plugin_y"` exist
**When** `retrieve_by_vector_similarity` is called with `plugins=["plugin_x"]`
**Then** only documents from `plugin = "plugin_x"` are returned

---

### AC-005: Filter by Multiple Plugins

**Given** documents from plugins `"plugin_x"`, `"plugin_y"`, and `"plugin_z"` exist
**When** `retrieve_by_vector_similarity` is called with `plugins=["plugin_x", "plugin_y"]`
**Then** only documents from those two plugins are returned

---

### AC-006: Combined Plugin and Doctype Filter

**Given** documents across multiple plugins and doctypes exist
**When** `retrieve_by_vector_similarity` is called with `plugins=["plugin_x"]` and `doctypes=["type_a"]`
**Then** only documents matching BOTH `plugin = "plugin_x"` AND `doctype = "type_a"` are returned

---

### AC-007: Empty Filter List Returns Nothing

**Given** documents exist in storage
**When** `retrieve_by_vector_similarity` is called with `doctypes=[]` (empty list)
**Then** no results are returned
**And** no error is raised

---

### AC-008: Post-Filter Behavior with KNN Limit

**Given** 10 documents exist: 5 with `doctype="type_a"` and 5 with `doctype="type_b"`
**When** `retrieve_by_vector_similarity` is called with `limit=5` and `doctypes=["type_a"]`
**Then** results contain only `doctype="type_a"` documents
**And** the result count may be fewer than `limit` due to post-filter KNN behavior

> **Implementation note:** sqlite-vec performs KNN search *before* JOIN/WHERE filters.
> The query over-fetches by a configurable multiplier to compensate, but `limit` is a
> maximum, not a guarantee, when filters are applied.
