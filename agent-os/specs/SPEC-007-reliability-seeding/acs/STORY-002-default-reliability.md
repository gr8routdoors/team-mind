# STORY-002: Default Reliability on RecordTypeSpec — Acceptance Criteria

---

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Field Defaults to None | Happy path |
| AC-002 | Plugin Declares Default | Happy path |
| AC-003 | Backward Compatible | Edge case |

---

### AC-001: Field Defaults to None
**Given** a `RecordTypeSpec` without `default_reliability`
**When** the field is accessed
**Then** it is `None`

### AC-002: Plugin Declares Default
**Given** a `RecordTypeSpec(name="code_sig", default_reliability=0.9)`
**When** the field is accessed
**Then** it is `0.9`

### AC-003: Backward Compatible
**Given** existing plugins that don't set `default_reliability` on their record types
**When** registered
**Then** no error occurs and `default_reliability` is `None`
