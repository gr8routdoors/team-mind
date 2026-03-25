# STORY-003: IngestObserver Interface — Acceptance Criteria

> ACs for the new observer interface that reacts to completed ingestion.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | IngestObserver ABC Exists | Happy path |
| AC-002 | Observer Receives Events | Happy path |
| AC-003 | Observer Registered in Registry | Happy path |
| AC-004 | Observer Default No-Op | Edge case |
| AC-005 | Multiple Observers | Integration |

---

### AC-001: IngestObserver ABC Exists

**Given** the `server.py` module
**When** `IngestObserver` is imported
**Then** it is an abstract base class with `name` and `on_ingest_complete` methods

---

### AC-002: Observer Receives Events

**Given** a mock `IngestObserver` is registered
**When** `on_ingest_complete(events)` is called with a list of `IngestionEvent` objects
**Then** the observer receives the full list of events

---

### AC-003: Observer Registered in Registry

**Given** a plugin implementing `IngestObserver` is registered
**When** `get_ingest_observers()` is called on the registry
**Then** the plugin appears in the returned list

---

### AC-004: Observer Default No-Op

**Given** a plugin that implements `IngestObserver` without overriding `on_ingest_complete`
**When** `on_ingest_complete(events)` is called
**Then** it completes without error (default no-op)

---

### AC-005: Multiple Observers

**Given** two `IngestObserver` plugins are registered
**When** events are broadcast to observers
**Then** both observers receive the same list of events
