# SPEC-009: Record Type Rename (doctype → record_type)

## Overview

Phase B of ADR-007. A purely mechanical rename — `doctype` becomes `record_type` throughout the codebase, completing the three-type model introduced in SPEC-008 Phase A. No new functionality; the concept is unchanged. This rename clarifies the role of this type: it is what the plugin *produced and stored*, not the input type or encoding.

## Scope

**In scope:**
- Rename `DoctypeSpec` → `RecordTypeSpec` (class and all imports).
- Rename `IngestProcessor.doctypes` property → `record_types`.
- Rename `IngestionEvent.doctype` field → `record_type`.
- Rename `EventFilter.doctypes` field → `record_types`.
- Rename `PluginRegistry` internal state and methods (`get_doctype_catalog`, `get_doctypes_for_plugin`, `get_plugins_for_doctype`).
- Rename `documents.doctype` SQL column → `record_type` (with index updates).
- Rename all `StorageAdapter` method parameters (`doctype` → `record_type`, `doctypes` → `record_types`).
- Rename `discovery.py` MCP tool `list_doctypes` → `list_record_types`.
- Update `lifecycle.py` EventFilter handling (`doctypes` → `record_types`).
- Update `MarkdownPlugin` (`DoctypeSpec` usage, `doctype=` kwargs).
- Update all tests.
- Update all documentation.

**Out of scope:**
- Any new functionality.
- Changes to `registered_plugins` table (already uses `semantic_types` / `supported_media_types`, no doctype column).
- Changes to the `SPEC-002` spec files (archived, describes the original doctype system as designed — leave as historical record).

## Context

**References:**
- `agent-os/context/architecture/ADRs/ADR-007-semantic-type-routing.md` — Section 4 defines the rename rationale.
- `agent-os/specs/SPEC-008-semantic-type-routing/` — Phase A, now complete. This is Phase B.

## Decisions

| Decision | Rationale |
|----------|-----------|
| `ALTER TABLE RENAME COLUMN` (SQLite 3.25+) | Runtime is SQLite 3.45.1 — no workaround needed. Simple, clean. |
| No backward-compat alias | No deployed instances. Clean rename, no deprecation shim needed. |
| `doctypes` → `record_types` (plural) | Follows established convention from Phase A: list fields are plural. |
| `DoctypeSpec` → `RecordTypeSpec` | The spec describes what the plugin *recorded*, not the input. |
| `list_doctypes` MCP tool → `list_record_types` | Public MCP tool name must match new terminology. |

## Stories

See `stories.yml` for current status.

| ID | Story | Scope |
|----|-------|-------|
| STORY-001 | Core Types and Interfaces | `DoctypeSpec→RecordTypeSpec`, `IngestionEvent.doctype→record_type`, `EventFilter.doctypes→record_types`, `IngestProcessor.doctypes→record_types`, `PluginRegistry` internals |
| STORY-002 | Storage Layer | SQL `documents.doctype→record_type`, index rename, all `StorageAdapter` method params |
| STORY-003 | MCP Tools and Lifecycle | `discovery.py` tool rename, `lifecycle.py` EventFilter, `PluginRegistry` public methods |
| STORY-004 | MarkdownPlugin | `DoctypeSpec→RecordTypeSpec`, `doctype=` kwargs to `record_type=` |
| STORY-005 | Documentation | ADRs, plugin guides, system overview, roadmap, README |
