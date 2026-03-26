# STORY-003: Plugin State Persistence Table — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Table Created on Initialize | Happy path |
| AC-002 | Save Plugin Record | Happy path |
| AC-003 | Retrieve Enabled Plugins | Happy path |
| AC-004 | Disable Plugin | Happy path |
| AC-005 | Delete Plugin Record | Happy path |
| AC-006 | Event Filter Serialized as JSON | Validation |

---

### AC-001: Table Created on Initialize

**Given** a freshly initialized StorageAdapter
**When** the database schema is inspected
**Then** the `registered_plugins` table exists with all required columns

### AC-002: Save Plugin Record

**Given** an initialized StorageAdapter
**When** a plugin record is saved with name, type, module_path, config, and event_filter
**Then** the row is persisted and retrievable

### AC-003: Retrieve Enabled Plugins

**Given** 3 plugin records: 2 enabled, 1 disabled
**When** enabled plugins are queried
**Then** only the 2 enabled records are returned

### AC-004: Disable Plugin

**Given** an enabled plugin record
**When** it is disabled (set enabled=0)
**Then** it no longer appears in enabled plugin queries
**And** the row still exists in the table

### AC-005: Delete Plugin Record

**Given** a plugin record
**When** it is deleted
**Then** it no longer appears in any query

### AC-006: Event Filter Serialized as JSON

**Given** a plugin with `event_filter = EventFilter(plugins=["a"], doctypes=["b"])`
**When** saved and retrieved
**Then** the event_filter is correctly round-tripped through JSON serialization
