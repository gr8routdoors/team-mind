# STORY-004: MarkdownPlugin

## Acceptance Criteria

### AC-001: Import updated
- `from team_mind_mcp.server import ..., DoctypeSpec` → `RecordTypeSpec`.

### AC-002: doctypes property renamed
- `MarkdownPlugin.doctypes` property renamed to `record_types`.
- Returns `list[RecordTypeSpec]` (was `list[DoctypeSpec]`).
- `DoctypeSpec(name="markdown_chunk", ...)` → `RecordTypeSpec(name="markdown_chunk", ...)`.

### AC-003: save_payload calls updated
- All `self.storage.save_payload(..., doctype="markdown_chunk", ...)` calls → `record_type="markdown_chunk"`.

### AC-004: delete_by_uri calls updated
- `self.storage.delete_by_uri(uri, plugin=self.name, doctype="markdown_chunk")` → `record_type="markdown_chunk"`.

### AC-005: process_bundle local variable updated
- Any local variable named `doctype_names` in `process_bundle` → `record_type_names` (if applicable).

### AC-006: IngestionEvent updated
- `IngestionEvent(plugin=self.name, doctype="markdown_chunk", ...)` → `record_type="markdown_chunk"`.

### AC-007: Tests pass
- `test_markdown_plugin.py` updated to use `record_type` field names.
- `test_markdown_semantic.py` updated to use `record_type` field names.
- All MarkdownPlugin tests pass with no regressions.
