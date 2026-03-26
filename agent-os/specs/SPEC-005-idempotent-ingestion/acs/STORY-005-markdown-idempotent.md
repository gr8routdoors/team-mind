# STORY-005: MarkdownPlugin Idempotent Optimization — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Skips Unchanged Content | Happy path |
| AC-002 | Replaces Changed Content | Happy path |
| AC-003 | Re-processes on Version Change | Happy path |
| AC-004 | Fresh Ingest Works Normally | Regression |

---

### AC-001: Skips Unchanged Content

**Given** a markdown file that was previously ingested with the same content and plugin version
**When** `process_bundle` is called again for the same URI
**Then** no new documents are created and no existing documents are modified
**And** the returned IngestionEvent list is empty (no-op)

### AC-002: Replaces Changed Content

**Given** a markdown file that was previously ingested but the content has since changed
**When** `process_bundle` is called for the same URI
**Then** old chunks are deleted via `delete_by_uri`
**And** new chunks are inserted with the updated content and a new content hash

### AC-003: Re-processes on Version Change

**Given** a markdown file previously ingested by plugin version `"1.0.0"` with unchanged content
**When** `process_bundle` is called and the plugin is now version `"1.1.0"`
**Then** old chunks are deleted and new chunks are inserted
**And** the new rows have `plugin_version="1.1.0"`

### AC-004: Fresh Ingest Works Normally

**Given** a markdown file that has never been ingested
**When** `process_bundle` is called
**Then** chunks are created normally with content_hash and plugin_version set
**And** the behavior is identical to pre-SPEC-005 ingestion
