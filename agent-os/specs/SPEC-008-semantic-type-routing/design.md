# SPEC-008: Semantic Type Routing — Design

## Overview

Phase A of ADR-007. Adds semantic type and media type as first-class concepts. Introduces semantic-type-based routing to the pipeline. All changes are additive — no renames.

## Design Amendments (vs Original Spec)

| Amendment | Original | Revised |
|-----------|----------|---------|
| Semantic type cardinality | `semantic_type: str \| None` (singular) | `semantic_types: list[str]` (plural) |
| No-semantic-type behavior | Broadcast to all | Wildcard-only (`["*"]` processors) |
| Semantic type at entry points | Optional | Required (with config default fallback) |
| Media type filtering scope | When semantic type specified | Always |
| CLI config | Not specced | `~/.team-mind.toml` (TOML); default: MarkdownPlugin = `["*"]` |

## Components

| Component | Type | Change |
|-----------|------|--------|
| documents table | Storage | **Extended** — `semantic_type`, `media_type` columns. |
| IngestProcessor | Interface | **Extended** — `supported_media_types` property. |
| registered_plugins table | Storage | **Extended** — `semantic_types`, `supported_media_types` columns. |
| IngestionBundle | Data Model | **Extended** — `semantic_types: list[str]` field. |
| IngestionEvent | Data Model | **Extended** — `semantic_types: list[str]` field. |
| EventFilter | Data Model | **Extended** — `semantic_types: list[str] \| None` field. |
| IngestionPipeline | Event Loop | **Extended** — Routes by semantic type, filters URIs by media type. |
| IngestionPlugin | Plugin | **Extended** — `semantic_types` parameter on `ingest_documents`. |
| MarkdownPlugin | Plugin | **Updated** — Declares media types, stores semantic_type/media_type. |
| LifecyclePlugin | Plugin | **Extended** — `semantic_types` and `supported_media_types` in registration. |
| CLI | Entry Point | **Extended** — `--semantic-type` flag (repeatable), TOML config loading. |
| media_types.py | New Module | `MEDIA_TYPE_MAP`, `get_media_type()`, `filter_uris_by_media_type()`. |

## Data Model

### Schema additions

```sql
ALTER TABLE documents ADD COLUMN semantic_type TEXT DEFAULT '';
ALTER TABLE documents ADD COLUMN media_type TEXT DEFAULT '';
CREATE INDEX idx_documents_semantic_type ON documents(semantic_type);

ALTER TABLE registered_plugins ADD COLUMN semantic_types JSON;
ALTER TABLE registered_plugins ADD COLUMN supported_media_types JSON;
```

Note: `documents.semantic_type` stores a comma-joined string when multiple types are present
(e.g., `"architecture_docs,booking_service"`). Default `''` for legacy rows.

### IngestProcessor extension

```python
class IngestProcessor(ABC):
    @property
    def supported_media_types(self) -> list[str] | None:
        """Media types this plugin can parse. None = accept all (backward compat)."""
        return None
```

### IngestionBundle extension

```python
@dataclass
class IngestionBundle:
    uris: List[str]
    events: List[IngestionEvent] = field(default_factory=list)
    contexts: Dict[str, IngestionContext] = field(default_factory=dict)
    semantic_types: list[str] = field(default_factory=list)        # NEW — plural
```

### IngestionEvent extension

```python
@dataclass
class IngestionEvent:
    plugin: str
    doctype: str
    uris: list[str] = field(default_factory=list)
    doc_ids: list[int] = field(default_factory=list)
    semantic_types: list[str] = field(default_factory=list)        # NEW — plural, at end
```

### EventFilter extension

```python
@dataclass
class EventFilter:
    plugins: list[str] | None = None
    doctypes: list[str] | None = None
    semantic_types: list[str] | None = None                        # NEW
```

## Routing Logic

### When semantic_types is non-empty

```
1. Caller: ingest(uris, semantic_types=["architecture_docs"])
2. Pipeline finds processors registered for "architecture_docs"
   (also includes processors with semantic_types=["*"])
3. For each matched processor:
   a. Filter URIs by processor's supported_media_types
   b. Build IngestionContext per filtered URI
   c. Call process_bundle with filtered bundle
4. Collect events, broadcast to observers (with semantic_types filter support)
```

### When semantic_types is empty or None

```
1. Caller: ingest(uris)  # no semantic_types
2. Pipeline only routes to processors with semantic_types=["*"] (wildcard)
3. If no wildcard processors, no processing occurs
4. This is intentional: no semantic type = no routing target (except wildcards)
```

There is no broadcast-to-all fallback. Unspecified semantic types = wildcard-only.

### Plugin activation model

```
Available (registered, no semantic types) → does NOT process content
Enabled (registered, has semantic types)  → processes matching content
Wildcard (semantic_types=["*"])           → processes all content (explicit opt-in)
```

`PluginRegistry.register()` accepts optional `semantic_types`:
```python
registry.register(plugin, semantic_types=["architecture_docs"])  # enabled for this type
registry.register(plugin)                                         # available only
registry.register(plugin, semantic_types=["*"])                   # processes everything
```

### Media type detection (new module: media_types.py)

```python
MEDIA_TYPE_MAP = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".json": "application/json",
    ".java": "text/x-java",
    ".py": "text/x-python",
    ".xml": "application/xml",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    ".csv": "text/csv",
    # extensible
}
```

Media type filtering applies in ALL pipeline modes (with or without semantic types).

## CLI Config (~/.team-mind.toml)

Format (TOML, Python 3.11+ stdlib `tomllib`):

```toml
[markdown_plugin]
semantic_types = ["*"]

# Example with specific types:
# [markdown_plugin]
# semantic_types = ["architecture_docs", "meeting_notes"]
```

**Default behavior** (no config file): MarkdownPlugin registered with `semantic_types=["*"]`.
This ensures backward-compatible out-of-the-box markdown ingestion without manual setup.

`pyproject.toml` requires Python >= 3.11 to use stdlib `tomllib` with no extra dependencies.

## Execution Plan

### Task 1: Schema + Media Types Module
- Add columns to documents and registered_plugins.
- Create media_types.py module.
- *Stories:* STORY-001

### Task 2: Interface Extensions
- Add `supported_media_types` to IngestProcessor.
- Add `semantic_types` to IngestionBundle and IngestionEvent.
- Add `semantic_types` to EventFilter.
- *Stories:* STORY-002, STORY-004, STORY-006

### Task 3: Registration
- Semantic types and media types stored in registered_plugins.
- PluginRegistry.register() accepts semantic_types.
- LifecyclePlugin accepts these on registration.
- load_persisted_plugins reloads semantic_types from DB.
- *Stories:* STORY-003

### Task 4: Pipeline Routing
- Route by semantic_types when specified.
- Filter URIs by media type within matched plugins.
- Wildcard fallback when no semantic_types.
- *Stories:* STORY-005

### Task 5: MCP + CLI
- ingest_documents accepts semantic_types (list[str]).
- CLI accepts repeatable --semantic-type flag.
- load_cli_config() reads ~/.team-mind.toml.
- *Stories:* STORY-007

### Task 6: MarkdownPlugin
- Declare supported_media_types=["text/markdown", "text/plain"].
- Store semantic_type (comma-joined) and media_type on save.
- Remove hardcoded .md extension check.
- *Stories:* STORY-008

### Task 7: Documentation
- Plugin developer guide, system overview, ADR-002.
- *Stories:* STORY-009
