# SPEC-003: Ingestion Interface Split (Processor + Observer)

## Overview

Splits the single `IngestListener` interface into two distinct interfaces: `IngestProcessor` (does ingestion work) and `IngestObserver` (reacts to completed ingestion). Introduces `IngestionEvent` as the structured data contract between processors and observers, and updates the pipeline to run in two phases.

## Scope

**In scope:**
- Rename `IngestListener` → `IngestProcessor` across all code and docs.
- Define new `IngestObserver` interface with `on_ingest_complete(events)`.
- Define `IngestionEvent` dataclass (plugin, doctype, uris, doc_ids).
- Update `IngestProcessor.process_bundle()` to return `list[IngestionEvent]`.
- Update `IngestionPipeline` to run two-phase ingestion (process → observe).
- Update `PluginRegistry` to track observers separately from processors.
- Update all existing plugins, tests, and documentation.

**Out of scope:**
- Filtering/routing events to specific observers (all observers get all events).
- Async event queuing or persistence of events.
- Observer error handling policy (fail-open for now).

## Context

**References:**
- `agent-os/context/architecture/ADRs/ADR-002-plugin-architecture.md` — Updated to reflect three interfaces.
- `agent-os/specs/SPEC-001-core-engine/` — Original IngestListener design.
- `agent-os/context/architecture/plugin-developer-guide.md` — Must be updated.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Rename IngestListener → IngestProcessor | Keep old name vs rename | "Listener" implies passive observation. "Processor" accurately describes the active role of parsing, chunking, and storing. |
| Separate observer interface | Single interface vs split | Processors and observers need fundamentally different inputs (raw URIs vs structured events). Splitting gives each exactly what it needs. |
| Two-phase pipeline | Interleaved vs sequential | Observers must see the final committed state. Running observation after all processing completes provides this guarantee. |
| IngestionEvent as return value | Return events vs emit via callback | Returning events from `process_bundle()` is simpler and testable. The pipeline collects and forwards them. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | IngestionEvent Data Model | pending |
| STORY-002 | Rename IngestListener to IngestProcessor | pending |
| STORY-003 | IngestObserver Interface | pending |
| STORY-004 | Two-Phase Ingestion Pipeline | pending |
| STORY-005 | Update Documentation | pending |
