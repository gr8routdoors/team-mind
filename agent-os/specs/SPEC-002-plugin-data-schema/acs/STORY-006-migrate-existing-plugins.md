# STORY-006: Migrate Existing Plugins to Doctypes — Acceptance Criteria

> ACs for updating MarkdownPlugin and other storage-writing plugins to use formal doctypes.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | MarkdownPlugin Declares Doctype | Happy path |
| AC-002 | MarkdownPlugin Passes Plugin and Doctype on Save | Happy path |
| AC-003 | Semantic Search Filters by Doctype | Integration |
| AC-004 | Existing Tests Continue to Pass | Regression |

---

## Acceptance Criteria

### AC-001: MarkdownPlugin Declares Doctype

**Given** the `MarkdownPlugin` class
**When** its `doctypes` property is accessed
**Then** it returns a list containing a `DoctypeSpec` with `name="markdown_chunk"`
**And** the spec includes a description and schema describing the chunk metadata

---

### AC-002: MarkdownPlugin Passes Plugin and Doctype on Save

**Given** the `MarkdownPlugin` is processing a markdown bundle
**When** it calls `storage.save_payload`
**Then** it passes `plugin="markdown_plugin"` and `doctype="markdown_chunk"` as arguments

---

### AC-003: Semantic Search Filters by Doctype

**Given** the knowledge base contains documents from multiple plugins and doctypes
**When** `semantic_search` is called via the MarkdownPlugin
**Then** results include the `plugin` and `doctype` fields in the response metadata
**And** consumers can distinguish document types in the results

---

### AC-004: Existing Tests Continue to Pass

**Given** the changes to MarkdownPlugin and StorageAdapter
**When** the full SPEC-001 test suite is executed
**Then** all existing tests pass without modification or with minimal backward-compatible updates
