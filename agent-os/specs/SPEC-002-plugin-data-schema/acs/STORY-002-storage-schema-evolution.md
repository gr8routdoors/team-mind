# STORY-002: Storage Schema Evolution — Acceptance Criteria

> ACs for adding `plugin` and `doctype` columns to the documents table with proper indexing.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | New Columns on Fresh Database | Happy path |
| AC-002 | Indexes Created | Happy path |
| AC-003 | Save Payload Requires Plugin and Doctype | Validation |
| AC-004 | Saved Record Contains Plugin and Doctype | Happy path |

---

## Acceptance Criteria

### AC-001: New Columns on Fresh Database

**Given** no existing database file
**When** the `StorageAdapter` is initialized
**Then** the `documents` table includes `plugin TEXT NOT NULL` and `doctype TEXT NOT NULL` columns
**And** the table creation succeeds without error

---

### AC-002: Indexes Created

**Given** a freshly initialized `StorageAdapter`
**When** the table schema is inspected
**Then** indexes exist on `plugin`, `doctype`, and the composite `(plugin, doctype)`

---

### AC-003: Save Payload Requires Plugin and Doctype

**Given** an initialized `StorageAdapter`
**When** `save_payload` is called without `plugin` or `doctype` arguments
**Then** a `TypeError` is raised (missing required arguments)

---

### AC-004: Saved Record Contains Plugin and Doctype

**Given** an initialized `StorageAdapter`
**When** `save_payload` is called with `plugin="test_plugin"` and `doctype="test_type"`
**Then** the saved row in the `documents` table has `plugin = "test_plugin"` and `doctype = "test_type"`
