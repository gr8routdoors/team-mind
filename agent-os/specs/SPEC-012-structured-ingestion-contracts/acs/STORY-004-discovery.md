# STORY-004: Discovery of submittable contracts — Acceptance Criteria

> Callers can discover which record types they may push, and their schemas.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Submittable record type exposes its schema | Happy path |
| AC-002 | Submittable flag distinguishes pushable types | Business rule |
| AC-003 | Existing plugin/record filters still work | Integration |

---

## Acceptance Criteria

### AC-001: Submittable record type exposes its schema

**Given** a submittable record type `service_profile` with a JSON Schema
**When** `list_record_types` is called
**Then** the result includes `service_profile` with its `schema`
**And** its owning `plugin` and `description`.

---

### AC-002: Submittable flag distinguishes pushable types

**Given** one submittable record type and one non-submittable record type are registered
**When** `list_record_types` is called
**Then** both are listed
**And** each entry indicates whether it is `submittable`
**And** a caller can therefore tell which types `submit_structured` will accept.

---

### AC-003: Existing plugin/record filters still work

**Given** record types from multiple plugins
**When** `list_record_types` is called with a `plugins` filter
**Then** only that plugin's record types are returned
**And** the same holds for a `record_types` name filter (existing behavior preserved).
