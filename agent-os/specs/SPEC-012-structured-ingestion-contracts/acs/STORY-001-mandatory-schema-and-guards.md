# STORY-001: Mandatory schema and registration guards — Acceptance Criteria

> Every record type must declare a schema; registration rejects invalid or conflicting declarations.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Valid submittable record type registers | Happy path |
| AC-002 | Missing/empty schema is rejected | Validation |
| AC-003 | Envelope field in schema is rejected | Validation |
| AC-004 | Duplicate submittable declarer is rejected | Business rule |
| AC-005 | Multiple non-submittable producers allowed | Edge case |
| AC-006 | embed_source is optional | Edge case |

---

## Acceptance Criteria

### AC-001: Valid submittable record type registers

**Given** a plugin declares a record type `service_profile` with a non-empty JSON Schema and `submittable = True`
**When** the plugin is registered
**Then** registration succeeds
**And** `service_profile` is retrievable via `get_submittable_spec("service_profile")`.

---

### AC-002: Missing/empty schema is rejected

**Given** a plugin declares a record type whose `schema` is an empty dict `{}`
**When** the plugin is registered
**Then** registration raises an error
**And** the error identifies the record type as missing a required schema
**And** the plugin is not registered.

---

### AC-003: Envelope field in schema is rejected

**Given** a submittable record type whose JSON Schema declares a property named `uri` (an envelope field)
**When** the plugin is registered
**Then** registration raises an error naming the disallowed envelope field
**And** the same holds for `id`, `plugin`, `content_hash`, `vector`, and `tenant`.

---

### AC-004: Duplicate submittable declarer is rejected

**Given** record type `service_profile` is already registered as submittable by plugin A
**When** plugin B registers the same record type name as submittable
**Then** registration raises a collision error
**And** plugin A remains the sole declarer.

---

### AC-005: Multiple non-submittable producers allowed

**Given** two plugins each produce a record type named `note` with `submittable = False`
**When** both plugins are registered
**Then** both registrations succeed
**And** both appear as producers of `note` (the single-declarer rule applies only to submittable types).

---

### AC-006: embed_source is optional

**Given** a submittable record type with a valid schema and `embed_source = None`
**When** the plugin is registered
**Then** registration succeeds
**And** records of that type will be stored without a vector (metadata-only).
