# ADR-005: Dynamic Plugin Lifecycle with Persistent State and Filtered Event Subscriptions

**Status:** Accepted
**Date:** 2026-03-26
**Spec:** SPEC-006 (Plugin Lifecycle Management)
**See also:** [ADR-002: Plugin Architecture](ADR-002-plugin-architecture.md), [Plugin Developer Guide](../plugin-developer-guide.md)

## Context

Team Mind's plugin system currently requires all plugins to be hardcoded in `cli.py` and registered at startup. There is no way to add, remove, or reconfigure plugins without restarting the server. Observers receive every ingestion event regardless of relevance. Nothing about the plugin roster or subscription preferences survives a restart.

This creates three limitations:

1. **No runtime extensibility.** Adding a new plugin requires code changes and a server restart. This defeats the purpose of a plugin architecture — it's effectively a module architecture.
2. **Fire hose only.** Every `IngestObserver` receives every `IngestionEvent`. At enterprise scale with many plugins and frequent ingestion, observers waste cycles filtering events they don't care about.
3. **No state persistence.** A power cycle loses all dynamically-registered plugins and their configurations. Enterprise deployments need the system to come back up in the same state it was in.

## Decision

We introduce a **plugin lifecycle management system** with three capabilities: dynamic registration, filtered event subscriptions, and persistent state.

### 1. Dynamic Plugin Registration at Runtime

Plugins can be registered and unregistered while the MCP server is running via:
- A `register_plugin` MCP tool (for AI agents and admin clients)
- A `PluginRegistry.register()` / `unregister()` API (for programmatic use)

Unregistering a plugin:
- Removes its tools from the MCP tool catalog
- Removes it from the processor and observer broadcast lists
- Does NOT delete its data from the database — documents and weights persist

Registration requires the plugin to be loadable — either already imported in the Python environment or discoverable via a plugin path/entry point mechanism.

### 2. Filtered Event Subscriptions (Topic-Based + Fire Hose)

Observers can optionally declare which events they care about:

```python
class AuditPlugin(IngestObserver):
    @property
    def event_filter(self) -> EventFilter | None:
        """Return None for fire hose (all events). Return EventFilter to subscribe to specific topics."""
        return EventFilter(
            plugins=["java_plugin"],
            doctypes=["code_signature"]
        )
```

**Key design: opt-in filtering, not mandatory.**
- `event_filter` returns `None` (the default) → observer gets every event (fire hose)
- `event_filter` returns an `EventFilter` → observer only gets matching events

This is backward compatible — existing observers that don't override `event_filter` continue to receive everything.

The pipeline applies filters during Phase 2 broadcast:
```python
for observer in registry.get_ingest_observers():
    filtered_events = apply_filter(observer.event_filter, all_events)
    if filtered_events:
        await observer.on_ingest_complete(filtered_events)
```

### 3. Plugin State Persistence

A `registered_plugins` table stores the plugin roster and configuration:

```sql
CREATE TABLE registered_plugins (
    plugin_name TEXT PRIMARY KEY,
    plugin_type TEXT NOT NULL,           -- 'tool_provider', 'ingest_processor', 'ingest_observer', or combinations
    module_path TEXT NOT NULL,           -- Python import path for the plugin class
    config JSON,                         -- Plugin-specific configuration
    event_filter JSON,                   -- Serialized EventFilter (null = fire hose)
    enabled INTEGER DEFAULT 1,           -- Soft enable/disable without unregistering
    registered_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

On startup, the system:
1. Loads hardcoded "core" plugins (MarkdownPlugin, RetrievalPlugin, etc.) as today
2. Reads `registered_plugins` table for dynamically-registered plugins
3. Imports and instantiates each one
4. Registers them with the `PluginRegistry`

This means the system comes back up in the same state after a restart.

### 4. EventFilter Data Model

```python
@dataclass
class EventFilter:
    plugins: list[str] | None = None    # Filter by source plugin names
    doctypes: list[str] | None = None   # Filter by doctype names
```

- Both `None` = fire hose (match everything)
- One set = filter on that dimension
- Both set = intersection (must match both)

Same semantics as our existing query filters — consistent across the system.

## Alternatives Considered

### 1. Configuration file instead of database persistence

Store the plugin roster in a YAML/JSON config file.

**Rejected because:**
- Config files require filesystem access patterns that may vary across deployment environments.
- The database is already our single persistence layer — adding a config file introduces a second source of truth.
- SQL queries make it easy to inspect and manage registered plugins.

### 2. Mandatory event filtering (no fire hose option)

Require every observer to declare an `EventFilter`.

**Rejected because:**
- Breaks backward compatibility — every existing observer would need changes.
- Some observers legitimately need all events (e.g., a logging/audit observer).
- Opt-in filtering is simpler and covers both use cases.

### 3. External plugin discovery via file system scanning

Automatically discover plugins by scanning a `plugins/` directory.

**Deferred (not rejected):** This is valuable for enterprise deployments but adds complexity around class loading, dependency isolation, and security. The `module_path` approach in the persistence table is a stepping stone — it uses Python's import system, which is well-understood. File system scanning can be layered on later.

## Consequences

### Positive

- **True plugin architecture.** Plugins can be added at runtime without server restart.
- **Efficient at scale.** Observers only process events they care about.
- **Persistent state.** Power cycle doesn't lose plugin configuration.
- **Backward compatible.** Existing hardcoded plugins and fire-hose observers work unchanged.

### Negative

- **Dynamic loading complexity.** Importing plugins by module path at runtime introduces potential for import errors, missing dependencies, and class loading issues. Mitigated by validation on registration.
- **Unregister edge cases.** Unregistering a plugin while it's mid-ingestion requires careful handling. Simplest approach: queue the unregister for after the current ingestion cycle completes.
- **State divergence risk.** If someone edits the `registered_plugins` table directly, the runtime state and persisted state may diverge. Mitigated by always using the API/tools, not raw SQL.

### Neutral

- Core plugins (Markdown, Retrieval, Ingestion, Discovery, Feedback) remain hardcoded in `cli.py`. The persistence table is for dynamically-added plugins only.
- The `EventFilter` model mirrors the existing filter patterns in `StorageAdapter` and `DoctypeDiscoveryPlugin` — consistent API design.
