# STORY-002: Plugin Version Property — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Default Version Is 0.0.0 | Happy path |
| AC-002 | Plugin Declares Custom Version | Happy path |
| AC-003 | Version Stored on Ingestion | Integration |

---

### AC-001: Default Version Is 0.0.0

**Given** an IngestProcessor that does not override the `version` property
**When** `version` is accessed
**Then** it returns `"0.0.0"`

### AC-002: Plugin Declares Custom Version

**Given** a plugin that overrides `version` to return `"2.1.0"`
**When** `version` is accessed
**Then** it returns `"2.1.0"`

### AC-003: Version Stored on Ingestion

**Given** MarkdownPlugin declares a version
**When** it processes a bundle and saves documents
**Then** the saved rows have `plugin_version` matching the plugin's version
