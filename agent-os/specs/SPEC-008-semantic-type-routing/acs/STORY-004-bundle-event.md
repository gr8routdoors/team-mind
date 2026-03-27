# STORY-004: Semantic Type on IngestionBundle and IngestionEvent — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | IngestionBundle Has semantic_type Field | Happy path |
| AC-002 | IngestionEvent Has semantic_type Field | Happy path |
| AC-003 | Semantic Type Propagates from Bundle to Event | Integration |
| AC-004 | Default semantic_type Is None on Bundle and Empty on Event | Edge case |

---

### AC-001: IngestionBundle Has semantic_type Field

**Given** an `IngestionBundle` constructed with `semantic_type="architecture_docs"`
**When** `semantic_type` is accessed
**Then** it returns `"architecture_docs"`

### AC-002: IngestionEvent Has semantic_type Field

**Given** an `IngestionEvent` constructed with `semantic_type="architecture_docs"`
**When** `semantic_type` is accessed
**Then** it returns `"architecture_docs"`

### AC-003: Semantic Type Propagates from Bundle to Event

**Given** an `IngestionBundle` with `semantic_type="meeting_notes"`
**When** a processor creates an `IngestionEvent` from this bundle
**Then** the event's `semantic_type` is `"meeting_notes"`

### AC-004: Default semantic_type Is None on Bundle and Empty on Event

**Given** an `IngestionBundle` created without specifying `semantic_type`
**When** `semantic_type` is accessed on the bundle
**Then** it returns `None`
**And** given an `IngestionEvent` created without specifying `semantic_type`, it defaults to `""`
