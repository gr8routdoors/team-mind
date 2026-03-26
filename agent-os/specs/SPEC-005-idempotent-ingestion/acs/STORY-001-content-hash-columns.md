# STORY-001: Content Hash & Plugin Version Columns — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Columns Exist on Fresh DB | Happy path |
| AC-002 | save_payload Stores Hash and Version | Happy path |
| AC-003 | lookup_existing_docs Returns Matches | Happy path |
| AC-004 | lookup_existing_docs Returns Empty for No Match | Edge case |
| AC-005 | Migration Adds Columns to Existing DB | Integration |
| AC-006 | Composite Index Created | Happy path |

---

### AC-001: Columns Exist on Fresh DB

**Given** a freshly initialized StorageAdapter
**When** the documents table schema is inspected
**Then** `content_hash TEXT` and `plugin_version TEXT` columns exist

### AC-002: save_payload Stores Hash and Version

**Given** an initialized StorageAdapter
**When** `save_payload` is called with `content_hash="abc123"` and `plugin_version="1.0.0"`
**Then** the saved row has those values in the corresponding columns

### AC-003: lookup_existing_docs Returns Matches

**Given** two documents with URI `"file:///doc.md"`, plugin `"p"`, doctype `"t"`
**When** `lookup_existing_docs("file:///doc.md", "p", "t")` is called
**Then** it returns a list of dicts with `id`, `content_hash`, and `plugin_version` for both docs

### AC-004: lookup_existing_docs Returns Empty for No Match

**Given** no documents matching the URI+plugin+doctype
**When** `lookup_existing_docs` is called
**Then** an empty list is returned

### AC-005: Migration Adds Columns to Existing DB

**Given** a database created before this feature (no content_hash/plugin_version columns)
**When** `StorageAdapter.initialize()` runs
**Then** both columns are added via ALTER TABLE without error

### AC-006: Composite Index Created

**Given** a freshly initialized StorageAdapter
**When** indexes are inspected
**Then** an index on `(uri, plugin, doctype)` exists for efficient URI lookups
