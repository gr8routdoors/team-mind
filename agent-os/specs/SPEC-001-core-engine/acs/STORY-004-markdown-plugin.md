# STORY-004: Markdown Vector Plugin — Acceptance Criteria

> ACs for the trivial Markdown plugin that vectorizes semantic data and stores Source Pointers (URIs).

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Markdown Semantic Ingestion | Happy path |
| AC-002 | Tool Registration | Integration |
| AC-003 | Skips Non-Markdown Resources | Validation |

---

## Acceptance Criteria

### AC-001: Markdown Semantic Ingestion

**Given** the `MarkdownPlugin` is active
**When** it receives a `.process_bundle()` event containing a `.md` resource
**Then** it chunks the text and requests embeddings for each chunk
**And** it stores the embeddings along with the Source Pointer (URI) in the `StorageAdapter`

---

### AC-002: Tool Registration

**Given** the `MCPGateway` and `PluginRegistry` are online
**When** the `MarkdownPlugin` initializes
**Then** it successfully registers the `semantic_search` tool
**And** it is visible to MCP clients

---

### AC-003: Skips Non-Markdown Resources

**Given** a bundle containing `image.png` and `notes.md`
**When** the `MarkdownPlugin` processes the bundle
**Then** it successfully parses `notes.md`
**And** it silently ignores `image.png` without throwing an error
