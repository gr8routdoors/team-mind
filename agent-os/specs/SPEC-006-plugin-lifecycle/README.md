# SPEC-006: Plugin Lifecycle Management

## Overview

Transforms Team Mind's plugin system from a compile-time module registry to a runtime-managed plugin architecture. Adds dynamic plugin registration/unregistration, filtered event subscriptions (topic-based or fire hose), and persistent plugin state that survives restarts.

## Scope

**In scope:**
- `EventFilter` data model for topic-based event subscriptions on `IngestObserver`.
- Filtered Phase 2 broadcast: observers only receive events matching their filter (or all events if no filter).
- `registered_plugins` table for persisting dynamically-registered plugins, configs, and event filters.
- Dynamic `register_plugin` / `unregister_plugin` MCP tools for runtime management.
- Plugin loader: instantiate plugins from a `module_path` at runtime.
- Startup loader: read `registered_plugins` on boot and restore the roster.
- Update plugin developer guide and architecture docs.

**Out of scope:**
- File system plugin discovery (scanning a `plugins/` directory) — deferred to future spec.
- Plugin sandboxing or dependency isolation.
- Plugin marketplace or distribution mechanism.
- Hot-reloading (updating a plugin's code without unregister/re-register).

## Context

**References:**
- `agent-os/context/architecture/ADRs/ADR-005-plugin-lifecycle.md` — Design rationale.
- `agent-os/context/architecture/ADRs/ADR-002-plugin-architecture.md` — Original plugin architecture.
- `agent-os/specs/SPEC-003-ingestion-interface-split/` — Observer interface this builds on.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Opt-in event filtering | Mandatory vs opt-in | Backward compatible — existing observers get fire hose by default. |
| Database persistence | DB vs config file | Single source of truth — DB is already our persistence layer. |
| Module path loading | Path vs scanning vs entry points | Simplest to implement, uses Python's import system. Scanning layered on later. |
| Core plugins stay hardcoded | All dynamic vs hybrid | Core plugins (Markdown, Retrieval, etc.) are always needed. No reason to make them dynamic. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | EventFilter Data Model | pending |
| STORY-002 | Filtered Observer Broadcast | pending |
| STORY-003 | Plugin State Persistence Table | pending |
| STORY-004 | Dynamic Registration MCP Tools | pending |
| STORY-005 | Plugin Loader & Startup Recovery | pending |
| STORY-006 | Update Documentation | pending |
