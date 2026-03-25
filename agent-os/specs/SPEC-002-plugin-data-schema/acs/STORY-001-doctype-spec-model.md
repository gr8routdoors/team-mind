# STORY-001: Doctype Specification Model — Acceptance Criteria

> ACs for defining the DoctypeSpec dataclass and extending plugin interfaces with an optional `doctypes` property.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | DoctypeSpec Dataclass Fields | Happy path |
| AC-002 | Plugin Declares Doctypes | Happy path |
| AC-003 | Doctypes Property Defaults Empty | Edge case |
| AC-004 | Schema Is Advisory Dict | Validation |

---

## Acceptance Criteria

### AC-001: DoctypeSpec Dataclass Fields

**Given** the `DoctypeSpec` dataclass is defined
**When** a new instance is created with `name`, `description`, and `schema`
**Then** all three fields are accessible on the instance
**And** the fields match the values provided at construction

---

### AC-002: Plugin Declares Doctypes

**Given** a plugin that implements `ToolProvider` or `IngestListener`
**When** the plugin overrides the `doctypes` property
**Then** it returns a list of `DoctypeSpec` instances
**And** each spec has a non-empty `name` and `description`

---

### AC-003: Doctypes Property Defaults Empty

**Given** a plugin that does NOT override the `doctypes` property
**When** the `doctypes` property is accessed
**Then** it returns an empty list
**And** no error is raised

---

### AC-004: Schema Is Advisory Dict

**Given** a `DoctypeSpec` with a `schema` containing JSON Schema-style field definitions
**When** the schema is accessed
**Then** it is a plain `dict` with string keys
**And** it can be serialized to JSON without error
