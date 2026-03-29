# STORY-004: Semantic Types on IngestionBundle and IngestionEvent — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | IngestionBundle Has semantic_types Field | Happy path |
| AC-002 | IngestionEvent Has semantic_types Field | Happy path |
| AC-003 | Semantic Types Propagate from Bundle to Event | Integration |
| AC-004 | Default semantic_types Is Empty List on Both | Edge case |

---

### AC-001: IngestionBundle Has semantic_types Field

**Given** an `IngestionBundle` constructed with `semantic_types=["architecture_docs", "meeting_notes"]`
**When** `semantic_types` is accessed
**Then** it returns `["architecture_docs", "meeting_notes"]`

### AC-002: IngestionEvent Has semantic_types Field

**Given** an `IngestionEvent` constructed with `semantic_types=["architecture_docs"]`
**When** `semantic_types` is accessed
**Then** it returns `["architecture_docs"]`

### AC-003: Semantic Types Propagate from Bundle to Event

**Given** an `IngestionBundle` with `semantic_types=["meeting_notes", "design_specs"]`
**When** a processor creates an `IngestionEvent` from this bundle
**Then** the event's `semantic_types` is `["meeting_notes", "design_specs"]`

### AC-004: Default semantic_types Is Empty List on Both

**Given** an `IngestionBundle` created without specifying `semantic_types`
**When** `semantic_types` is accessed on the bundle
**Then** it returns `[]`
**And** given an `IngestionEvent` created without specifying `semantic_types`, it also returns `[]`
