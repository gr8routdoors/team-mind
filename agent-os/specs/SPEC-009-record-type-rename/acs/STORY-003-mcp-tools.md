# STORY-003: MCP Tools and Lifecycle

## Acceptance Criteria

### AC-001: PluginRegistry public methods renamed
- `get_doctype_catalog()` → `get_record_type_catalog()`.
- `get_doctypes_for_plugin(plugin_name)` → `get_record_types_for_plugin(plugin_name)`.
- `get_plugins_for_doctype(doctype_name)` → `get_plugins_for_record_type(record_type_name)`.
- All callers (discovery.py, tests) updated.

### AC-002: discovery.py MCP tool renamed
- Tool name `"list_doctypes"` → `"list_record_types"`.
- Tool description updated to use "record type" terminology.
- Input schema parameter `"doctypes"` → `"record_types"`.
- `if name != "list_record_types"` guard updated.
- `arguments.get("record_types")` updated.
- `get_record_type_catalog()` call updated.

### AC-003: lifecycle.py apply_event_filter updated
- `EventFilter(doctypes=event_filter_json.get("doctypes"))` → `record_types=event_filter_json.get("record_types")`.

### AC-004: lifecycle.py _list() display dict updated
- `"doctypes": ef.doctypes` → `"record_types": ef.record_types` in the event filter display dict.

### AC-005: lifecycle.py register_plugin schema updated
- Any description strings in the register_plugin tool schema that reference "doctypes" or "doctype" are updated to "record types" or "record_type".

### AC-006: Tests pass
- `test_discovery_plugin.py` verifies the `list_record_types` tool is exposed (not `list_doctypes`).
- `test_plugin_lifecycle.py` verifies the EventFilter display dict uses `record_types`.
- All lifecycle tests pass with no regressions.
