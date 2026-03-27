# STORY-002: Supported Media Types on IngestProcessor — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Default supported_media_types Is None | Happy path |
| AC-002 | Processor Declares Media Types | Happy path |
| AC-003 | Existing Processors Unaffected | Edge case |

---

### AC-001: Default supported_media_types Is None

**Given** an `IngestProcessor` subclass that does not override `supported_media_types`
**When** `supported_media_types` is accessed
**Then** it returns `None`

### AC-002: Processor Declares Media Types

**Given** an `IngestProcessor` subclass that overrides `supported_media_types` to return `["text/markdown", "text/plain"]`
**When** `supported_media_types` is accessed
**Then** it returns `["text/markdown", "text/plain"]`

### AC-003: Existing Processors Unaffected

**Given** an existing `IngestProcessor` subclass written before this change that does not define `supported_media_types`
**When** the processor is instantiated and used in the pipeline
**Then** it continues to function without error
**And** `supported_media_types` returns `None` (accept all)
