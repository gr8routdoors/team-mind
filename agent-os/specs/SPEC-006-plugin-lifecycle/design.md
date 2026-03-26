# SPEC-006: Plugin Lifecycle Management — Design

## Overview

This spec adds runtime plugin management: dynamic registration/unregistration, filtered event subscriptions, and persistent plugin state. The system transitions from a compile-time plugin roster to a managed lifecycle.

## Components

| Component | Type | Change |
|-----------|------|--------|
| EventFilter | Data Model | **New** — Optional filter for observer subscriptions. |
| IngestObserver | Plugin Interface | **Extended** — `event_filter` property (default None = fire hose). |
| IngestionPipeline | Event Loop | **Extended** — Phase 2 applies filters per observer. |
| registered_plugins | Storage | **New** — Table persisting dynamic plugin roster. |
| PluginRegistry | Core Manager | **Extended** — `unregister()` method, loader integration. |
| LifecyclePlugin | Plugin | **New** — MCP tools for register/unregister/list. |
| PluginLoader | Utility | **New** — Imports and instantiates plugins from module paths. |

## Data Model

### EventFilter

```python
@dataclass
class EventFilter:
    plugins: list[str] | None = None
    doctypes: list[str] | None = None
```

Matching semantics (same as all our other filters):
- `None` = no filter on this dimension (match all)
- `[]` = match nothing
- `["a", "b"]` = match if value in list
- Both set = intersection (must match both)

### registered_plugins table

```sql
CREATE TABLE registered_plugins (
    plugin_name TEXT PRIMARY KEY,
    plugin_type TEXT NOT NULL,
    module_path TEXT NOT NULL,
    config JSON,
    event_filter JSON,
    enabled INTEGER DEFAULT 1,
    registered_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### IngestObserver extension

```python
class IngestObserver(ABC):
    @property
    def event_filter(self) -> EventFilter | None:
        """Override to subscribe to specific event types. None = all events."""
        return None
```

## Data Flow

### Filtered Phase 2 Broadcast

```
Phase 2 (updated):
  for each observer:
    filter = observer.event_filter
    if filter is None:
      → pass ALL events to observer (fire hose)
    else:
      → filter events by plugin/doctype match
      → if any events match, call observer.on_ingest_complete(filtered_events)
      → if no events match, skip this observer entirely
```

### Dynamic Registration Flow

```
1. Admin calls register_plugin(module_path, config?, event_filter?)
2. LifecyclePlugin validates module_path is importable
3. LifecyclePlugin instantiates the plugin class
4. PluginRegistry.register(plugin) — tools, processor, observer all routed
5. Persisted to registered_plugins table
6. Plugin is now live — tools visible, ingestion active
```

### Startup Recovery Flow

```
1. Server starts, loads core plugins from cli.py (as today)
2. Reads registered_plugins WHERE enabled = 1
3. For each row:
   a. Import module_path
   b. Instantiate with config
   c. Set event_filter if present
   d. Register with PluginRegistry
   e. On failure: log warning, skip (don't block startup)
```

## API Contracts

### MCP Tools (LifecyclePlugin)

```
register_plugin(
    module_path: str,          # e.g., "my_plugins.travel.TravelPlugin"
    config?: dict,             # Plugin-specific config passed to constructor
    event_filter?: {           # Optional subscription filter
        plugins?: list[str],
        doctypes?: list[str]
    }
) -> {status, plugin_name, tools_registered}

unregister_plugin(
    plugin_name: str
) -> {status, tools_removed}

list_plugins() -> list[{
    name, plugin_type, module_path, enabled,
    event_filter, registered_at, tools
}]
```

### PluginRegistry (extended)

```python
def unregister(self, plugin_name: str) -> None:
    """Remove a plugin from all internal collections. Does not delete data."""
```

## Execution Plan

### Task 1: EventFilter + Filtered Broadcast
- Define EventFilter dataclass.
- Add event_filter property to IngestObserver.
- Update pipeline Phase 2 to apply filters.
- *Stories:* STORY-001, STORY-002

### Task 2: Persistence Table
- Create registered_plugins table in StorageAdapter.initialize().
- CRUD methods for plugin records.
- *Stories:* STORY-003

### Task 3: MCP Tools + Loader
- Build PluginLoader utility (import by module_path, instantiate).
- Build LifecyclePlugin with register/unregister/list tools.
- Integrate with persistence table.
- *Stories:* STORY-004

### Task 4: Startup Recovery
- Load enabled plugins from table on server boot.
- Graceful failure handling.
- *Stories:* STORY-005

### Task 5: Documentation
- Update plugin developer guide, ADR-002, system overview.
- *Stories:* STORY-006
