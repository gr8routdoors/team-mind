# STORY-006: Migrate Existing Plugins to Doctypes — Acceptance Criteria

> ACs for updating MarkdownPlugin and other storage-writing plugins to use formal doctypes, and ensuring MCP tools surface multi-value filtering.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | MarkdownPlugin Declares Doctype | Happy path |
| AC-002 | MarkdownPlugin Passes Plugin and Doctype on Save | Happy path |
| AC-003 | Semantic Search Accepts Plugin and Doctype Filters | Happy path |
| AC-004 | Semantic Search Multi-Value Filters | Happy path |
| AC-005 | Response Metadata Includes Plugin and Doctype | Integration |
| AC-006 | Existing Tests Continue to Pass | Regression |

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

### AC-003: Semantic Search Accepts Plugin and Doctype Filters

**Given** the `semantic_search` MCP tool
**When** called with optional `plugins` and/or `doctypes` list parameters
**Then** results are scoped to only documents matching the provided filters
**And** omitting the parameters returns results across all plugins and doctypes

---

### AC-004: Semantic Search Multi-Value Filters

**Given** documents from plugins `"plugin_a"` and `"plugin_b"` with doctypes `"type_x"` and `"type_y"`
**When** `semantic_search` is called with `plugins=["plugin_a", "plugin_b"]` and `doctypes=["type_x"]`
**Then** results include documents from both plugins but only with `doctype = "type_x"`

---

### AC-005: Response Metadata Includes Plugin and Doctype

**Given** documents stored with explicit plugin and doctype fields
**When** `semantic_search` returns results
**Then** each result includes `plugin` and `doctype` in its metadata
**And** consumers can distinguish document types in the results

---

### AC-006: Existing Tests Continue to Pass

**Given** the changes to MarkdownPlugin and StorageAdapter
**When** the full SPEC-001 test suite is executed
**Then** all existing tests pass without modification or with minimal backward-compatible updates
