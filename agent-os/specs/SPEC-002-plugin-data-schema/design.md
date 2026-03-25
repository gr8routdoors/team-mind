# SPEC-002: Plugin Data Schema & Doctype System — Design

## Overview

This spec introduces a **doctype** layer into Team Mind's plugin architecture. Doctypes are plugin-scoped document type declarations that serve as data contracts between plugins. Each plugin declares what types of documents it produces and what schema those documents follow. This enables cross-plugin data discovery, scoped queries, and a self-describing knowledge base that AI agents can introspect at runtime.

## Components

| Component | Type | Change |
|-----------|------|--------|
| DoctypeSpec | Data Model | **New** — Dataclass representing a document type declaration (name, description, schema). |
| ToolProvider / IngestListener | Plugin Interface | **Extended** — Optional `doctypes` property for plugins to declare their document types. |
| StorageAdapter | Abstraction | **Extended** — `plugin` and `doctype` columns, scoped query methods accepting filter lists. |
| PluginRegistry | Core Manager | **Extended** — Doctype catalog methods for discovery across all registered plugins. |
| DoctypeDiscoveryPlugin | Plugin | **New** — ToolProvider that exposes `list_doctypes` as an MCP tool. |
| MarkdownPlugin | Plugin | **Migrated** — Declares `markdown_chunk` doctype, passes plugin/doctype on save. |

## Data Model

### DoctypeSpec

```python
@dataclass
class DoctypeSpec:
    name: str                    # e.g., "markdown_chunk", "user_interest"
    description: str             # Human-readable purpose
    schema: dict                 # JSON Schema-style advisory schema for metadata fields
    plugin: str                  # Owning plugin name (set automatically on registration)
```

**Fully-qualified doctype name:** `{plugin}:{doctype}` — e.g., `markdown_plugin:markdown_chunk`.

### Storage Schema

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uri TEXT NOT NULL,
    plugin TEXT NOT NULL,         -- owning plugin name
    doctype TEXT NOT NULL,        -- document type within that plugin
    metadata JSON
);

CREATE INDEX idx_documents_plugin ON documents(plugin);
CREATE INDEX idx_documents_doctype ON documents(doctype);
CREATE INDEX idx_documents_plugin_doctype ON documents(plugin, doctype);
```

## Data Flow

### Ingestion (with doctypes)
1. Plugin receives a bundle via `process_bundle()`.
2. Plugin processes content and calls `storage.save_payload(uri, plugin, doctype, metadata, vector)`.
3. StorageAdapter writes the row with explicit `plugin` and `doctype` columns.

### Cross-plugin query
1. A ToolProvider plugin (e.g., TripPlanner) wants user interests.
2. It calls `storage.retrieve_by_vector_similarity(vector, doctypes=["user_interest"], plugins=["travel_preferences"])`.
3. StorageAdapter applies `WHERE plugin IN (...) AND doctype IN (...)` filters alongside KNN search.
4. Results come back scoped to the requested data.

### Discovery
1. AI client calls `list_doctypes` MCP tool (optionally filtered by plugin name).
2. DoctypeDiscoveryPlugin queries the PluginRegistry's doctype catalog.
3. Returns structured list of all doctypes with their schemas, grouped by plugin.

## API Contracts

### StorageAdapter (extended)

```python
def save_payload(
    self, uri: str, metadata: dict, vector: list[float],
    plugin: str, doctype: str
) -> int:

def retrieve_by_vector_similarity(
    self, target_vector: list[float], limit: int = 5,
    plugins: list[str] | None = None,
    doctypes: list[str] | None = None
) -> list[dict]:
```

### PluginRegistry (extended)

```python
def get_doctype_catalog(self) -> list[DoctypeSpec]:
    """All doctypes across all registered plugins."""

def get_doctypes_for_plugin(self, plugin_name: str) -> list[DoctypeSpec]:
    """What doctypes does a specific plugin declare?"""

def get_plugins_for_doctype(self, doctype_name: str) -> list[str]:
    """Which plugins produce a given doctype?"""
```

### MCP Tool

```
list_doctypes(plugin?: str) -> list[{plugin, name, description, schema}]
```

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Optional `doctypes` property | Required vs optional on interfaces | Backward-compatible — plugins that don't declare doctypes still work. The property defaults to an empty list. |
| `save_payload` signature change | New method vs extend existing | Extending the existing method (with `plugin`/`doctype` params) keeps one code path. Existing callers must be updated, which is acceptable given the small surface area. |

## Execution Plan

### Task 1: DoctypeSpec Model
- Define the `DoctypeSpec` dataclass.
- Add optional `doctypes` property to `ToolProvider` and `IngestListener` base classes.
- *Stories:* STORY-001

### Task 2: Storage Schema Evolution
- Add `plugin` and `doctype` columns to `documents` table.
- Add indexes for efficient filtering.
- Update `save_payload` signature.
- *Stories:* STORY-002

### Task 3: Scoped Queries
- Extend `retrieve_by_vector_similarity` to accept optional `plugins` and `doctypes` filter lists.
- Build SQL dynamically with `IN` clauses when filters are provided.
- *Stories:* STORY-003

### Task 4: Doctype Registry
- Add catalog methods to `PluginRegistry`.
- Collect doctypes from plugins on registration.
- *Stories:* STORY-004

### Task 5: Discovery MCP Tool
- Build `DoctypeDiscoveryPlugin` as a ToolProvider.
- Expose `list_doctypes` tool.
- *Stories:* STORY-005

### Task 6: Migrate Existing Plugins
- Update `MarkdownPlugin` to declare a `markdown_chunk` doctype and pass plugin/doctype on save.
- Update any other plugins that write to storage.
- *Stories:* STORY-006
