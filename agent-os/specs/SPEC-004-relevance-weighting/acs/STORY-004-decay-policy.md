# STORY-004: Decay Policy on DoctypeSpec — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Field Exists and Defaults to None | Happy path |
| AC-002 | Plugin Declares Decay | Happy path |
| AC-003 | Backward Compatible | Edge case |

---

### AC-001: Field Exists and Defaults to None

**Given** a `DoctypeSpec` created without specifying `decay_half_life_days`
**When** the field is accessed
**Then** it is `None`

---

### AC-002: Plugin Declares Decay

**Given** a plugin declares `DoctypeSpec(name="notes", decay_half_life_days=30)`
**When** the doctype is registered
**Then** the catalog entry has `decay_half_life_days=30`

---

### AC-003: Backward Compatible

**Given** existing plugins that don't specify `decay_half_life_days`
**When** they are registered
**Then** no error occurs and their doctypes have `decay_half_life_days=None`
