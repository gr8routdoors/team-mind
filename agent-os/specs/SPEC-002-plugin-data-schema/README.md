# SPEC-002: Plugin Data Schema & Doctype System

## Overview

The Plugin Data Schema spec introduces a formal **doctype** system that lets plugins declare the types of documents they produce, complete with schemas. This enables cross-plugin data discovery and querying while maintaining strict plugin ownership of data. Doctypes are plugin-scoped (namespaced as `plugin_name:doctype_name`) to prevent collisions at scale.

## Scope

**In scope:**
- `DoctypeSpec` model for declaring document types with schemas.
- `doctypes` property on plugin interfaces (opt-in).
- Storage schema evolution: `plugin` and `doctype` as first-class indexed columns on the `documents` table.
- Scoped query methods on `StorageAdapter` — filter by plugin(s) and/or doctype(s).
- Doctype catalog on `PluginRegistry` for runtime discovery.
- MCP tool (`list_doctypes`) exposing the catalog to connected AI clients.
- Migration of existing plugins (MarkdownPlugin, etc.) to declare doctypes.

**Out of scope:**
- Schema enforcement/validation on write (advisory schemas only for this spec).
- Cross-instance doctype federation.
- Doctype versioning or evolution strategy.
- Access control (RBAC) on doctype queries.

## Context

**References:**
- `agent-os/specs/SPEC-001-core-engine/` — Establishes the plugin system, StorageAdapter, and MCP gateway this spec extends.
- `agent-os/context/architecture/system-overview.md` — Plugin architecture and broadcast pipeline.
- `agent-os/product/mission.md` — Token-optimized precision retrieval philosophy.

**Standards:**
- Python code conventions per `agent-os/standards/code-style/python.md`.
- BDD acceptance criteria with inline pytest.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Plugin-scoped doctypes | Global shared names vs plugin-scoped namespacing | If you're querying another plugin's data, you already know it exists. Namespacing (`plugin:doctype`) eliminates collision risk at scale without losing discoverability. |
| Advisory schemas (not enforced) | Enforce on write vs advisory-only | Enforcing schemas adds complexity and rigidity. Advisory schemas let consumers understand the shape without blocking producers. Enforcement can be layered on later via the Librarian (Phase 2). |
| Multi-value query filters | Single plugin/doctype vs list filters | `IN` clauses on indexed columns are efficient in SQLite. Letting callers pass lists avoids N separate queries and N KNN searches. |
| Shared documents table | Separate tables per plugin vs shared table with columns | A shared table with indexed `plugin`/`doctype` columns enables cross-plugin queries naturally. Separate tables would require UNION queries and complicate the storage API. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | Doctype Specification Model | pending |
| STORY-002 | Storage Schema Evolution | pending |
| STORY-003 | Scoped Storage Queries | pending |
| STORY-004 | Doctype Registry & Catalog | pending |
| STORY-005 | Doctype Discovery MCP Tool | pending |
| STORY-006 | Migrate Existing Plugins to Doctypes | pending |
