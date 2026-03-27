# STORY-001: EventFilter Data Model — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | EventFilter Fields | Happy path |
| AC-002 | Default event_filter Is None | Happy path |
| AC-003 | Observer Declares Filter | Happy path |
| AC-004 | None Means Fire Hose | Edge case |

---

### AC-001: EventFilter Fields

**Given** an `EventFilter` instance
**When** created with `plugins=["java_plugin"]` and `doctypes=["code_signature"]`
**Then** both fields are accessible and match

### AC-002: Default event_filter Is None

**Given** an `IngestObserver` that does not override `event_filter`
**When** `event_filter` is accessed
**Then** it returns `None`

### AC-003: Observer Declares Filter

**Given** an observer that overrides `event_filter` to return an `EventFilter`
**When** `event_filter` is accessed
**Then** the returned `EventFilter` has the declared plugins and/or doctypes

### AC-004: None Means Fire Hose

**Given** an `EventFilter` with `plugins=None` and `doctypes=None`
**When** used to filter a list of events
**Then** all events pass through (equivalent to no filter)
