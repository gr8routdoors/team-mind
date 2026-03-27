# STORY-008: MarkdownPlugin Media Type and Semantic Type Awareness — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Declares Supported Media Types | Happy path |
| AC-002 | Stores semantic_type on Document | Happy path |
| AC-003 | Stores media_type on Document | Happy path |
| AC-004 | Removes Hardcoded .md Extension Check | Refactor |

---

### AC-001: Declares Supported Media Types

**Given** the `MarkdownPlugin` processor
**When** `supported_media_types` is accessed
**Then** it returns `["text/markdown", "text/plain"]`

### AC-002: Stores semantic_type on Document

**Given** a bundle with `semantic_type="architecture_docs"` routed to the MarkdownPlugin
**When** the plugin processes and saves a document
**Then** the document row has `semantic_type="architecture_docs"`

### AC-003: Stores media_type on Document

**Given** a URI `"design.md"` processed by the MarkdownPlugin
**When** the document is saved
**Then** the document row has `media_type="text/markdown"`

### AC-004: Removes Hardcoded .md Extension Check

**Given** the MarkdownPlugin processor code
**When** routing is handled by semantic type and media type filtering
**Then** there is no hardcoded `.md` extension check in the plugin's processing logic
**And** URI filtering is delegated to the pipeline's media type mechanism
