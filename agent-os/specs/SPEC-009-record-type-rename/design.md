# SPEC-009: Record Type Rename — Design

## Overview

Purely mechanical rename completing the three-type model from ADR-007. No new behavior is introduced. Every `doctype` identifier becomes `record_type` (singular) or `record_types` (plural list fields).

## Rename Map

### Python identifiers

| Old | New | Location |
|-----|-----|----------|
| `DoctypeSpec` | `RecordTypeSpec` | `server.py`, all importers |
| `IngestProcessor.doctypes` | `IngestProcessor.record_types` | `server.py` ABC |
| `IngestionEvent.doctype` | `IngestionEvent.record_type` | `ingestion.py` |
| `EventFilter.doctypes` | `EventFilter.record_types` | `server.py` |
| `PluginRegistry._doctype_catalog` | `PluginRegistry._record_type_catalog` | `server.py` |
| `PluginRegistry._doctypes_by_plugin` | `PluginRegistry._record_types_by_plugin` | `server.py` |
| `PluginRegistry.get_doctype_catalog()` | `PluginRegistry.get_record_type_catalog()` | `server.py` |
| `PluginRegistry.get_doctypes_for_plugin()` | `PluginRegistry.get_record_types_for_plugin()` | `server.py` |
| `PluginRegistry.get_plugins_for_doctype()` | `PluginRegistry.get_plugins_for_record_type()` | `server.py` |
| `save_payload(doctype=...)` | `save_payload(record_type=...)` | `storage.py` |
| `delete_by_uri(doctype=...)` | `delete_by_uri(record_type=...)` | `storage.py` |
| `lookup_existing_docs(doctype=...)` | `lookup_existing_docs(record_type=...)` | `storage.py` |
| `retrieve_by_vector_similarity(doctypes=...)` | `retrieve_by_vector_similarity(record_types=...)` | `storage.py` |
| `list_doctypes` (MCP tool name) | `list_record_types` | `discovery.py` |
| `arguments.get("doctypes")` | `arguments.get("record_types")` | `discovery.py`, `lifecycle.py` |
| `"doctypes"` (EventFilter display key) | `"record_types"` | `lifecycle.py` |
| `doctype="markdown_chunk"` | `record_type="markdown_chunk"` | `markdown.py` |
| `MarkdownPlugin.doctypes` property | `MarkdownPlugin.record_types` property | `markdown.py` |
| `ingestion.py` local `doctype_names` | `record_type_names` | `ingestion.py` |
| `ingestion.py` EventFilter check `e.doctype` | `e.record_type` | `ingestion.py` |

### SQL

```sql
-- In StorageAdapter.initialize() migration block:
ALTER TABLE documents RENAME COLUMN doctype TO record_type;

DROP INDEX IF EXISTS idx_documents_doctype;
DROP INDEX IF EXISTS idx_documents_plugin_doctype;
DROP INDEX IF EXISTS idx_documents_uri_plugin_doctype;

CREATE INDEX IF NOT EXISTS idx_documents_record_type ON documents(record_type);
CREATE INDEX IF NOT EXISTS idx_documents_plugin_record_type ON documents(plugin, record_type);
CREATE INDEX IF NOT EXISTS idx_documents_uri_plugin_record_type ON documents(uri, plugin, record_type);
```

**Migration guard** — Use PRAGMA to check for the old column name before renaming:

```python
existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(documents)")}
if "doctype" in existing_columns:
    conn.execute("ALTER TABLE documents RENAME COLUMN doctype TO record_type")
    conn.execute("DROP INDEX IF EXISTS idx_documents_doctype")
    conn.execute("DROP INDEX IF EXISTS idx_documents_plugin_doctype")
    conn.execute("DROP INDEX IF EXISTS idx_documents_uri_plugin_doctype")
```

The new indexes are created with `CREATE INDEX IF NOT EXISTS` so they run safely on both fresh and migrated databases.

## Updated Data Models

### RecordTypeSpec (renamed from DoctypeSpec)

```python
@dataclass
class RecordTypeSpec:
    name: str
    plugin: str
    schema: dict
    description: str = ""
    decay_half_life_days: float | None = None
```

### IngestProcessor (updated property)

```python
class IngestProcessor(ABC):
    @property
    @abstractmethod
    def record_types(self) -> List[RecordTypeSpec]:
        """Record types this processor writes. Each has a name, schema, decay config."""
        ...
```

### IngestionEvent (updated field)

```python
@dataclass
class IngestionEvent:
    plugin: str
    record_type: str                                 # renamed from doctype
    uris: list[str] = field(default_factory=list)
    doc_ids: list[int] = field(default_factory=list)
    semantic_types: list[str] = field(default_factory=list)
```

### EventFilter (updated field)

```python
@dataclass
class EventFilter:
    plugins: list[str] | None = None
    record_types: list[str] | None = None            # renamed from doctypes
    semantic_types: list[str] | None = None
```

## MCP Tool: list_record_types (renamed from list_doctypes)

`discovery.py` exposes a single MCP tool. The tool name and parameter change:

```python
Tool(
    name="list_record_types",           # was: list_doctypes
    description="...",
    inputSchema={
        "type": "object",
        "properties": {
            "plugins": {...},
            "record_types": {...},      # was: doctypes
        }
    }
)
```

The `if name != "list_record_types"` guard and `arguments.get("record_types")` follow.

## lifecycle.py EventFilter

Two places to update:

```python
# apply_event_filter():
EventFilter(
    plugins=event_filter_json.get("plugins"),
    record_types=event_filter_json.get("record_types"),   # was: doctypes
    semantic_types=event_filter_json.get("semantic_types"),
)

# _list() display dict:
"record_types": ef.record_types,   # was: "doctypes": ef.doctypes
```

The `register_plugin` tool schema description string also references "doctypes" — update to "record types".

## Test updates

Every test that uses:
- `IngestionEvent(plugin=..., doctype=...)` → `record_type=...`
- `EventFilter(doctypes=...)` → `record_types=...`
- `save_payload(..., doctype=...)` → `record_type=...`
- `delete_by_uri(..., doctype=...)` → `record_type=...`
- `DoctypeSpec(...)` → `RecordTypeSpec(...)`
- `list_doctypes` tool name → `list_record_types`

Files expected to need updates:
- `tests/core/test_ingestion_bundle_event.py`
- `tests/core/test_event_filter.py`
- `tests/core/test_event_filter_semantic.py`
- `tests/core/test_pipeline_routing.py`
- `tests/core/test_mcp_cli_semantic.py`
- `tests/core/test_doctype_model.py`
- `tests/core/test_doctype_registry.py`
- `tests/core/test_idempotent_ingestion.py`
- `tests/core/test_markdown_plugin.py`
- `tests/core/test_markdown_semantic.py`
- `tests/core/test_semantic_type_registration.py`
- `tests/core/test_two_phase_pipeline.py`
- `tests/core/test_storage_schema.py`
- `tests/core/test_composite_scoring.py`
- `tests/core/test_doc_weights.py`
- `tests/core/test_retrieval_plugin.py`
- `tests/spikes/test_weighted_scoring.py`
