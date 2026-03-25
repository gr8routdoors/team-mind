# STORY-001: IngestionEvent Data Model — Acceptance Criteria

> ACs for the structured event that processors emit after writing documents.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Event Fields | Happy path |
| AC-002 | Event Serializable | Validation |
| AC-003 | Empty Doc IDs Allowed | Edge case |

---

### AC-001: Event Fields

**Given** the `IngestionEvent` dataclass is defined
**When** an instance is created with `plugin`, `doctype`, `uris`, and `doc_ids`
**Then** all four fields are accessible and match the values provided

---

### AC-002: Event Serializable

**Given** an `IngestionEvent` with populated fields
**When** it is converted to a dict
**Then** all fields are present and can be serialized to JSON

---

### AC-003: Empty Doc IDs Allowed

**Given** a processor that filters out all URIs (nothing to ingest)
**When** it creates an `IngestionEvent` with empty `uris` and `doc_ids`
**Then** the event is valid with empty lists
