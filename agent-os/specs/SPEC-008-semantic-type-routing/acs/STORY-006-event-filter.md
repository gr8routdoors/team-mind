# STORY-006: EventFilter Semantic Type Support — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Filter Events by Semantic Type | Happy path |
| AC-002 | Combined with Other Filter Fields | Happy path |
| AC-003 | None semantic_types Matches All | Edge case |
| AC-004 | Empty List Matches No Events | Validation |

---

### AC-001: Filter Events by Semantic Type

**Given** an `EventFilter` with `semantic_types=["architecture_docs"]`
**When** events with semantic types `["architecture_docs", "meeting_notes", "architecture_docs"]` are filtered
**Then** only the two events with `semantic_type="architecture_docs"` pass through

### AC-002: Combined with Other Filter Fields

**Given** an `EventFilter` with `plugins=["markdown_plugin"]` and `semantic_types=["architecture_docs"]`
**When** events are filtered
**Then** only events matching both the plugin name and the semantic type pass through

### AC-003: None semantic_types Matches All

**Given** an `EventFilter` with `semantic_types=None`
**When** events with various semantic types are filtered
**Then** all events pass through regardless of their semantic type

### AC-004: Empty List Matches No Events

**Given** an `EventFilter` with `semantic_types=[]`
**When** events are filtered
**Then** no events pass through on the semantic_types criterion
