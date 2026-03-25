# ADR-001: Plugin-Scoped Doctypes as Cross-Plugin Data Contracts

**Status:** Accepted
**Date:** 2026-03-25
**Spec:** SPEC-002 (Plugin Data Schema & Doctype System)
**See also:** [Plugin Developer Guide](../plugin-developer-guide.md) — practical guide for building plugins

## Context

Team Mind's plugin architecture (SPEC-001) established a system where plugins can ingest documents and expose MCP tools. However, the data model has no formal concept of document types. All documents go into a single `documents` table with a freeform `metadata` JSON blob — the only type signal is an ad-hoc `"plugin"` key buried in that JSON.

This creates three problems:

1. **No cross-plugin data access.** A tool-only plugin (e.g., a trip planner) cannot meaningfully query data produced by an ingestion plugin (e.g., travel preferences) because there's no way to scope queries to specific data types.

2. **No data discovery.** An AI agent connected to the MCP server has no way to ask "what kinds of data exist in this knowledge base?" — it can only do blind semantic searches.

3. **No data contracts.** Plugins that want to consume another plugin's data have no way to understand the shape of that data without reading the source code.

The immediate trigger was designing a travel agent plugin that needs to store user interests, destination profiles, and trip history as distinct document types — then have separate tool plugins query across those types.

## Decision

We introduce **doctypes** — plugin-scoped document type declarations that serve as data contracts between plugins.

### Core design:

1. **`DoctypeSpec` dataclass** — Each plugin declares the document types it produces via a `doctypes` property, including a name, description, and advisory JSON schema.

2. **Plugin-scoped namespacing** — Doctypes are namespaced as `{plugin}:{doctype}` (e.g., `markdown_plugin:markdown_chunk`). There are no global/shared doctype names.

3. **First-class storage columns** — `plugin` and `doctype` become indexed columns on the `documents` table (promoted from buried-in-metadata to queryable columns).

4. **List-based filtering everywhere** — Every surface that accepts a plugin or doctype filter accepts a `list[str]`. This applies uniformly from `StorageAdapter.retrieve_by_vector_similarity()` through `PluginRegistry` catalog methods to MCP tools (`semantic_search`, `list_doctypes`). Single-value filtering is just a list of one.

5. **Discovery MCP tool** — A `list_doctypes` tool exposes the doctype catalog to connected AI clients, enabling self-describing knowledge bases.

6. **Advisory schemas** — Doctype schemas describe the expected shape of metadata but are not enforced on write. Enforcement is deferred to the Librarian pipeline (Phase 2).

## Alternatives Considered

### 1. Separate tables per plugin

Each plugin would own its own SQLite table(s).

**Rejected because:**
- Cross-plugin queries would require `UNION` across unknown table names.
- The StorageAdapter API would become plugin-aware (leaky abstraction).
- Adding a new plugin would mean DDL changes, not just data.

### 2. Global/shared doctype names (no plugin namespacing)

Any plugin could emit documents with doctype `"user_interest"` and consumers would query by doctype alone.

**Rejected because:**
- At scale, uncoordinated teams would collide on names.
- If you're querying another plugin's data, you already know that plugin exists — so namespacing costs nothing.
- Plugin-scoped names make ownership unambiguous.

### 3. Enforced schemas on write

Validate metadata against the declared JSON schema before saving.

**Rejected for now because:**
- Adds rigidity during a phase where schemas are still evolving.
- The Librarian (Phase 2) is the natural place for validation — it already sits in the ingestion pipeline as a quality gate.
- Advisory schemas give consumers enough to work with without blocking producers.

### 4. Single-value filters on MCP tools (pass one plugin or doctype)

MCP tools would accept a single string filter, not lists.

**Rejected because:**
- Forces N round-trips for N-value queries.
- Inconsistent with the StorageAdapter layer (which benefits from `IN` clauses).
- A list of one is a perfectly good single-value filter — no reason to have two APIs.

## Consequences

### Positive

- **Cross-plugin data access** becomes a first-class capability. Tool plugins can query by doctype across all plugins without coupling to specific implementations.
- **Self-describing knowledge base.** AI agents can call `list_doctypes` to discover what data exists and adapt their queries accordingly.
- **Clean ownership model.** Every document row has an explicit owner (`plugin` column). No ambiguity about who produced what.
- **Efficient queries.** Indexed `plugin`/`doctype` columns with `IN` clauses are fast in SQLite. Composite index on `(plugin, doctype)` covers the common combined filter case.
- **Backward compatible.** The `doctypes` property is optional — existing plugins that don't declare doctypes continue to work.

### Negative

- **Breaking change to `save_payload`.** The signature gains required `plugin` and `doctype` parameters. All existing callers (MarkdownPlugin) must be updated. Mitigated by the small surface area (currently one plugin writes to storage).
- **Advisory schemas may mislead.** Consumers might assume metadata matches the declared schema when it doesn't. Mitigated by documenting schemas as advisory and planning enforcement for Phase 2.
- **Schema evolution not addressed.** If a plugin changes its doctype schema across versions, existing documents don't match the new schema. Deferred — this is a versioning problem for a future ADR.

### Neutral

- No migration needed for existing databases in production — there are none yet (pre-release).
- The `DoctypeDiscoveryPlugin` adds one more plugin to the registry, but it's lightweight (catalog lookup only, no storage).

## Implementation

See SPEC-002 for full stories and acceptance criteria. Key files affected:

| File | Change |
|------|--------|
| `server.py` | `DoctypeSpec` dataclass, `doctypes` property on base classes, catalog methods on `PluginRegistry` |
| `storage.py` | `plugin`/`doctype` columns, indexes, updated `save_payload` and `retrieve_by_vector_similarity` signatures |
| `markdown.py` | Declare `markdown_chunk` doctype, pass plugin/doctype on save, accept filters on `semantic_search` |
| New: `discovery.py` | `DoctypeDiscoveryPlugin` exposing `list_doctypes` MCP tool |
