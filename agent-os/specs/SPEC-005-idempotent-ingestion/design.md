# SPEC-005: Idempotent Ingestion — Design

## Overview

This spec makes ingestion context-aware by providing processors with information about previously-ingested content for each URI. The platform computes content hashes, performs URI lookups, and passes structured `IngestionContext` to processors so they can make intelligent re-ingestion decisions.

## Components

| Component | Type | Change |
|-----------|------|--------|
| documents table | Storage | **Extended** — `content_hash` and `plugin_version` columns. |
| IngestProcessor | Plugin Interface | **Extended** — Optional `version` property. `process_bundle` receives `IngestionContext` per URI. |
| IngestionContext | Data Model | **New** — Per-URI context: is_update, content_changed, plugin_version_changed, previous_doc_ids. |
| IngestionPipeline | Event Loop | **Extended** — URI lookup and hash comparison before broadcasting to processors. |
| StorageAdapter | Abstraction | **Extended** — `save_payload` accepts `content_hash` and `plugin_version`. Lookup method for existing docs by URI. |
| MarkdownPlugin | Plugin | **Updated** — Uses context to skip unchanged content. |

## Data Model

### Schema additions

```sql
ALTER TABLE documents ADD COLUMN content_hash TEXT;
ALTER TABLE documents ADD COLUMN plugin_version TEXT DEFAULT '0.0.0';

CREATE INDEX idx_documents_uri_plugin_doctype ON documents(uri, plugin, doctype);
```

### IngestionContext

```python
@dataclass
class IngestionContext:
    uri: str
    is_update: bool                     # True if URI+plugin+doctype already exists
    content_changed: bool | None        # True/False/None (None = no prior hash to compare)
    plugin_version_changed: bool        # True if current plugin version != stored version
    previous_doc_ids: list[int]         # IDs of existing rows for this URI+plugin+doctype
    previous_content_hash: str | None   # Hash from the most recent prior ingestion
    previous_plugin_version: str | None # Version from the most recent prior ingestion
```

### IngestProcessor version property

```python
class IngestProcessor(ABC):
    @property
    def version(self) -> str:
        """Plugin version. Override to declare. Used for version-aware re-ingestion."""
        return "0.0.0"
```

## Data Flow

### Ingestion with context

```
1. Pipeline receives URIs
2. ResourceResolver expands and validates URIs
3. For each URI, pipeline queries StorageAdapter:
   - "Do docs exist for this URI + each registered processor's plugin+doctype?"
   - If yes: fetch content_hash and plugin_version from existing rows
4. Pipeline computes content hash for each URI's current content
5. Pipeline builds IngestionContext per (URI, processor) pair
6. Phase 1: Broadcast bundle + contexts to processors
   - Processor receives: bundle.uris AND bundle.contexts[uri]
   - Processor decides: skip, re-process, wipe-replace, or surgical update
7. Phase 2: Broadcast events to observers (unchanged)
```

### Plugin decision matrix

| is_update | content_changed | version_changed | Typical action |
|-----------|----------------|-----------------|----------------|
| false | N/A | N/A | Fresh insert (new content) |
| true | false | false | Skip (nothing changed) |
| true | true | false | Wipe and replace (content updated) |
| true | false | true | Re-process (plugin logic changed) |
| true | true | true | Wipe and replace (both changed) |

## API Changes

### StorageAdapter

```python
def save_payload(
    self, uri, metadata, vector, plugin, doctype,
    decay_half_life_days=None,
    content_hash: str | None = None,
    plugin_version: str = "0.0.0",
) -> int:

def lookup_existing_docs(
    self, uri: str, plugin: str, doctype: str
) -> list[dict]:
    """Returns existing doc info: [{id, content_hash, plugin_version}, ...]"""
```

### IngestionBundle (extended)

```python
@dataclass
class IngestionBundle:
    uris: list[str]
    events: list[IngestionEvent] = field(default_factory=list)
    contexts: dict[str, IngestionContext] = field(default_factory=dict)
```

## Execution Plan

### Task 1: Schema & Storage
- Add `content_hash` and `plugin_version` columns to documents table (with migration).
- Update `save_payload` to accept and store both.
- Add `lookup_existing_docs` method.
- *Stories:* STORY-001

### Task 2: Plugin Version Property
- Add optional `version` property to `IngestProcessor`.
- Default to `"0.0.0"`.
- *Stories:* STORY-002

### Task 3: IngestionContext
- Define dataclass.
- Build context generation logic (URI lookup + hash comparison).
- *Stories:* STORY-003

### Task 4: Pipeline Integration
- Update `IngestionPipeline.ingest()` to build contexts before Phase 1.
- Attach contexts to the bundle.
- *Stories:* STORY-004

### Task 5: MarkdownPlugin Optimization
- Use context to skip unchanged content.
- Pass content_hash and version on save.
- *Stories:* STORY-005

### Task 6: Documentation
- Update plugin developer guide with ingestion context, decision matrix, version property.
- *Stories:* STORY-006
