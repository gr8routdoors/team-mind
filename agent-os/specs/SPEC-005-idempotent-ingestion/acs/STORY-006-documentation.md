# STORY-006: Update Documentation — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Plugin Developer Guide Updated | Happy path |
| AC-002 | Decision Matrix Documented | Happy path |
| AC-003 | Version Property Documented | Happy path |

---

### AC-001: Plugin Developer Guide Updated

**Given** the plugin developer guide
**When** it is read
**Then** it documents IngestionContext, content hashing, and how to use context in process_bundle

### AC-002: Decision Matrix Documented

**Given** the plugin developer guide
**When** it is read
**Then** it includes the decision matrix (is_update × content_changed × version_changed → typical action)

### AC-003: Version Property Documented

**Given** the plugin developer guide
**When** it is read
**Then** it documents the `version` property on IngestProcessor and explains when/why to use it
