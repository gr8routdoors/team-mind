# STORY-005: Documentation and Spec Cleanup

## Acceptance Criteria

### AC-001: ADR-007 updated
- All references to `doctype` as an identifier are updated to `record_type`.
- The three-type table correctly shows "Record type (was doctype)" with no ambiguity.
- Section 4 "Record Type (renamed from Doctype)" is updated to past tense: rename is complete.

### AC-002: ADR-002 updated
- `DoctypeSpec` references updated to `RecordTypeSpec`.
- Any doctype-related method names updated to match the new names.

### AC-003: Plugin developer guides updated
- Both `agent-os/product/domain/plugin-developer-guide.md` and `agent-os/context/architecture/plugin-developer-guide.md` updated:
  - `DoctypeSpec` → `RecordTypeSpec` in code examples.
  - `plugin.doctypes` → `plugin.record_types` in code examples.
  - `doctype=` kwargs → `record_type=` in storage examples.
  - `list_doctypes` tool → `list_record_types` where mentioned.
  - Conceptual descriptions use "record type" terminology consistently.

### AC-004: System overview updated
- `agent-os/context/architecture/system-overview.md` uses "record type" not "doctype".

### AC-005: Roadmap updated
- SPEC-009 marked in progress / complete as appropriate.
- "Phase B: Rename doctype → record_type" item updated to reflect completion.

### AC-006: README updated
- SPEC-009 entry in development status section.

### AC-007: SPEC-008 README.md out-of-scope note updated
- The line "Rename doctype → record_type (Phase B, separate spec)" updated to note that Phase B is SPEC-009.

### AC-008: No remaining stale doctype references in docs
- No documentation files use `doctype` as a current identifier (historical context in ADR-007 "Context" section is acceptable).
