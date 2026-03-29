# STORY-001: Core Types and Interfaces

## Acceptance Criteria

### AC-001: DoctypeSpec renamed to RecordTypeSpec
- `class DoctypeSpec` in `server.py` is renamed to `RecordTypeSpec`.
- All imports of `DoctypeSpec` across the codebase are updated to `RecordTypeSpec`.
- All instantiations `DoctypeSpec(...)` are replaced with `RecordTypeSpec(...)`.

### AC-002: IngestProcessor.doctypes renamed to record_types
- The `doctypes` abstract property on `IngestProcessor` is renamed to `record_types`.
- Return type annotation is updated to `List[RecordTypeSpec]`.
- All implementations of the property (e.g., in `MarkdownPlugin`, test plugins) are renamed.

### AC-003: IngestionEvent.doctype renamed to record_type
- `IngestionEvent.doctype: str` field is renamed to `record_type: str`.
- All `IngestionEvent(plugin=..., doctype=...)` calls are updated to `record_type=...`.
- The EventFilter check in `ingestion.py` (`e.doctype in ef.doctypes`) is updated to `e.record_type in ef.record_types`.

### AC-004: EventFilter.doctypes renamed to record_types
- `EventFilter.doctypes: list[str] | None` is renamed to `record_types`.
- All `EventFilter(doctypes=...)` instantiations are updated to `record_types=...`.

### AC-005: PluginRegistry internal state updated
- `PluginRegistry._doctype_catalog` is renamed to `_record_type_catalog`.
- `PluginRegistry._doctypes_by_plugin` is renamed to `_record_types_by_plugin`.
- All internal references within `register()`, `unregister()`, and iteration loops are updated.

### AC-006: Tests pass
- All existing tests continue to pass after the rename.
- Test files that create `IngestionEvent` or `EventFilter` objects are updated to use the new field names.
- Test files that import or use `DoctypeSpec` are updated to `RecordTypeSpec`.
