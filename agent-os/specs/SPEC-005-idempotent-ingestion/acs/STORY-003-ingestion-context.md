# STORY-003: IngestionContext Data Model — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Context Fields | Happy path |
| AC-002 | New URI Context | Happy path |
| AC-003 | Unchanged Content Context | Happy path |
| AC-004 | Changed Content Context | Happy path |
| AC-005 | Version Changed Context | Happy path |

---

### AC-001: Context Fields

**Given** an IngestionContext instance
**When** fields are accessed
**Then** `uri`, `is_update`, `content_changed`, `plugin_version_changed`, `previous_doc_ids`, `previous_content_hash`, and `previous_plugin_version` are all present

### AC-002: New URI Context

**Given** a URI that has never been ingested
**When** context is generated
**Then** `is_update=False`, `content_changed=None`, `plugin_version_changed=False`, `previous_doc_ids=[]`

### AC-003: Unchanged Content Context

**Given** a URI that was previously ingested with hash `"abc"` and the current content hashes to `"abc"`
**When** context is generated
**Then** `is_update=True`, `content_changed=False`

### AC-004: Changed Content Context

**Given** a URI that was previously ingested with hash `"abc"` and the current content hashes to `"def"`
**When** context is generated
**Then** `is_update=True`, `content_changed=True`

### AC-005: Version Changed Context

**Given** a URI previously ingested with plugin version `"1.0.0"` and the current plugin version is `"2.0.0"`
**When** context is generated
**Then** `plugin_version_changed=True`, `previous_plugin_version="1.0.0"`
