# SPEC-008: Semantic Type Routing — Design

## Overview

Phase A of ADR-007. Adds semantic type and media type as first-class concepts. Introduces semantic-type-based routing to the pipeline. All changes are additive — no renames.

## Components

| Component | Type | Change |
|-----------|------|--------|
| documents table | Storage | **Extended** — `semantic_type`, `media_type` columns. |
| IngestProcessor | Interface | **Extended** — `supported_media_types` property. |
| registered_plugins table | Storage | **Extended** — `semantic_types`, `supported_media_types` columns. |
| IngestionBundle | Data Model | **Extended** — `semantic_type` field. |
| IngestionEvent | Data Model | **Extended** — `semantic_type` field. |
| EventFilter | Data Model | **Extended** — `semantic_types` field. |
| IngestionPipeline | Event Loop | **Extended** — Routes by semantic type, filters URIs by media type. |
| IngestionPlugin | Plugin | **Extended** — `semantic_type` parameter on `ingest_documents`. |
| MarkdownPlugin | Plugin | **Updated** — Declares media types, stores semantic_type/media_type. |
| LifecyclePlugin | Plugin | **Extended** — `semantic_types` and `supported_media_types` in registration. |

## Data Model

### Schema additions

```sql
ALTER TABLE documents ADD COLUMN semantic_type TEXT DEFAULT '';
ALTER TABLE documents ADD COLUMN media_type TEXT DEFAULT '';
CREATE INDEX idx_documents_semantic_type ON documents(semantic_type);

ALTER TABLE registered_plugins ADD COLUMN semantic_types JSON;
ALTER TABLE registered_plugins ADD COLUMN supported_media_types JSON;
```

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
    events: List[IngestionEvent]
    contexts: Dict[str, IngestionContext]
    reliability_hint: float | None = None
    semantic_type: str | None = None        # NEW
```

### IngestionEvent extension

```python
@dataclass
class IngestionEvent:
    plugin: str
    doctype: str
    semantic_type: str = ""                  # NEW
    uris: list[str]
    doc_ids: list[int]
```

### EventFilter extension

```python
@dataclass
class EventFilter:
    plugins: list[str] | None = None
    doctypes: list[str] | None = None
    semantic_types: list[str] | None = None  # NEW
```

## Routing Logic

### When semantic_type is specified

```
1. Caller: ingest(uris, semantic_type="architecture_docs")
2. Pipeline finds processors registered for "architecture_docs"
3. For each matched processor:
   a. Filter URIs by processor's supported_media_types
   b. Build IngestionContext per filtered URI
   c. Call process_bundle with filtered bundle
4. Collect events, broadcast to observers (with semantic_type filter support)
```

### When semantic_type is NOT specified

```
1. Caller: ingest(uris)  # no semantic_type
2. Pipeline only routes to processors with semantic_types=["*"] (wildcard)
3. If no wildcard processors, no processing occurs
4. This is intentional: no semantic type = no routing target
```

Note: This is a breaking change from the previous broadcast-to-all behavior.
Plugins must be explicitly associated with semantic types (or wildcard `*`) to
receive bundles. See ADR-007 "Available vs Enabled" for rationale.

### Plugin activation model

```
Available (registered, no semantic types) → does NOT process content
Enabled (registered, has semantic types)  → processes matching content
Wildcard (semantic_types=["*"])           → processes all content (explicit opt-in)
```

`PluginRegistry.register()` accepts optional `semantic_types`:
```python
registry.register(plugin, semantic_types=["architecture_docs"])  # enabled for this type
registry.register(plugin)  # available only, no processing until configured
registry.register(plugin, semantic_types=["*"])  # processes everything
```

### Media type detection

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

## Execution Plan

### Task 1: Schema + Data Model
- Add columns to documents and registered_plugins.
- Add fields to IngestionBundle, IngestionEvent, EventFilter.
- Add supported_media_types to IngestProcessor.
- *Stories:* STORY-001, STORY-002, STORY-004, STORY-006

### Task 2: Registration
- Semantic types and media types stored in registered_plugins.
- LifecyclePlugin accepts these on registration.
- Updateable via re-registration.
- *Stories:* STORY-003

### Task 3: Pipeline Routing
- Route by semantic type when specified.
- Filter URIs by media type within matched plugins.
- Broadcast fallback when no semantic type.
- *Stories:* STORY-005

### Task 4: MCP + CLI
- ingest_documents accepts semantic_type.
- CLI accepts --semantic-type flag.
- *Stories:* STORY-007

### Task 5: MarkdownPlugin
- Declare supported_media_types=["text/markdown", "text/plain"].
- Store semantic_type and media_type on save.
- *Stories:* STORY-008

### Task 6: Documentation
- Plugin developer guide, system overview, ADR-002.
- *Stories:* STORY-009
