# STORY-004: Two-Phase Ingestion Pipeline — Acceptance Criteria

> ACs for the pipeline collecting events from processors and broadcasting to observers.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Phase 1 Collects Events | Happy path |
| AC-002 | Phase 2 Broadcasts to Observers | Happy path |
| AC-003 | Observers Run After Processors Complete | Integration |
| AC-004 | No Events Means No Observer Phase | Edge case |
| AC-005 | Pipeline Returns Events | Happy path |
| AC-006 | Multiple Processors Emit Events | Integration |

---

### AC-001: Phase 1 Collects Events

**Given** two `IngestProcessor` plugins are registered
**When** the pipeline ingests a bundle
**Then** events from both processors are collected into a single flat list

---

### AC-002: Phase 2 Broadcasts to Observers

**Given** an `IngestObserver` is registered alongside an `IngestProcessor`
**When** the pipeline ingests a bundle
**Then** the observer's `on_ingest_complete` is called with the events from Phase 1

---

### AC-003: Observers Run After Processors Complete

**Given** a slow `IngestProcessor` and a fast `IngestObserver`
**When** the pipeline ingests a bundle
**Then** the observer does not receive events until all processors have finished

---

### AC-004: No Events Means No Observer Phase

**Given** an `IngestProcessor` that returns no events (e.g., all URIs filtered out)
**When** the pipeline ingests a bundle
**Then** observers are still called with an empty event list
**And** no error is raised

---

### AC-005: Pipeline Returns Events

**Given** processors that emit events
**When** `pipeline.ingest(uris)` completes
**Then** the returned bundle includes the collected `IngestionEvent` list

---

### AC-006: Multiple Processors Emit Events

**Given** Processor A emits 2 events and Processor B emits 3 events
**When** the pipeline completes Phase 1
**Then** the combined event list has 5 events
**And** events from both processors are present
