# SPEC-003: Ingestion Interface Split — Design

## Overview

This spec splits `IngestListener` into `IngestProcessor` and `IngestObserver`, introduces `IngestionEvent`, and updates the pipeline to two-phase execution.

## Components

| Component | Type | Change |
|-----------|------|--------|
| IngestionEvent | Data Model | **New** — Structured event describing what a processor wrote. |
| IngestProcessor | Plugin Interface | **Renamed** from IngestListener. `process_bundle()` now returns `list[IngestionEvent]`. |
| IngestObserver | Plugin Interface | **New** — ABC with `on_ingest_complete(events)` for post-ingestion reactions. |
| PluginRegistry | Core Manager | **Extended** — Tracks `_ingest_observers` separately from `_ingest_processors`. |
| IngestionPipeline | Event Loop | **Extended** — Two-phase: process (collect events) → observe (broadcast events). |
| MarkdownPlugin | Plugin | **Migrated** — Implements IngestProcessor (renamed), returns IngestionEvents. |
| Plugin Developer Guide | Documentation | **Updated** — Describes all three interfaces. |

## Data Model

### IngestionEvent

```python
@dataclass
class IngestionEvent:
    plugin: str          # Which processor wrote the data
    doctype: str         # What doctype was written
    uris: list[str]      # Which source URIs were processed
    doc_ids: list[int]   # IDs of the document rows created
```

## Interface Changes

### IngestProcessor (renamed from IngestListener)

```python
class IngestProcessor(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def doctypes(self) -> list[DoctypeSpec]:
        return []

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        return []
```

### IngestObserver (new)

```python
class IngestObserver(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def event_filter(self) -> EventFilter | None:
        """Optional: filter which events this observer receives. None = all events (fire hose).
        See SPEC-006 for EventFilter details and filtered broadcast implementation."""
        return None

    async def on_ingest_complete(self, events: list[IngestionEvent]) -> None:
        pass
```

## Pipeline Flow

```
Phase 1 — Processing:
  IngestionBundle → broadcast to IngestProcessors (asyncio.gather)
  → each returns list[IngestionEvent]
  → pipeline flattens all events into one list

Phase 2 — Observation (filtered, per observer):
  for each IngestObserver:
    if event_filter is None → all events broadcast (fire hose)
    else → filter events by plugin/doctype, broadcast only matching
  → filtered events broadcast via asyncio.gather
  → each observer reacts to events it cares about
```

## Execution Plan

### Task 1: IngestionEvent
- Define dataclass in `ingestion.py`.
- *Stories:* STORY-001

### Task 2: Rename IngestListener → IngestProcessor
- Rename ABC in `server.py`.
- Update `process_bundle()` return type to `list[IngestionEvent]`.
- Update PluginRegistry internal collections.
- Update MarkdownPlugin to return events.
- Update all existing tests.
- *Stories:* STORY-002

### Task 3: IngestObserver Interface
- Define ABC in `server.py`.
- Add observer tracking to PluginRegistry.
- *Stories:* STORY-003

### Task 4: Two-Phase Pipeline
- Update `IngestionPipeline.ingest()` to collect events from Phase 1.
- Add Phase 2: broadcast events to observers.
- *Stories:* STORY-004

### Task 5: Documentation
- Update plugin developer guide, system overview, ADR-001, README.
- *Stories:* STORY-005
