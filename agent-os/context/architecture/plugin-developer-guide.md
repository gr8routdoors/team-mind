# Plugin Developer Guide

> How to build plugins for Team Mind. This is the starting point for anyone extending the system.

## What You Control

When you build a plugin, you own:

1. **Your doctypes** — You declare what types of documents your plugin produces (e.g., `user_interest`, `trip_review`, `code_signature`). These are namespaced to your plugin automatically (`your_plugin:your_doctype`), so you'll never collide with other plugins.

2. **Your metadata schema** — The `metadata` JSON column is yours. Store whatever structure you need per document — free-form fields, nested objects, arrays. You declare an advisory schema so other plugins can understand your data, but it's your design.

3. **Your storage mode per document** — For each document you ingest, you choose:
   - **Pointer mode**: Store a URI reference. The content lives externally (file, URL, API) and is fetched live on demand. Best for stable, long-lived sources.
   - **Embedded mode**: Store the full content directly in the `metadata` JSON under a `local_payload` key. Best for ephemeral content, user input, or anything without a stable external URL.
   - You can mix both modes freely within the same doctype.

4. **Your MCP tools** — You define what tools AI agents can call and what those tools do. Tools are your plugin's public API.

5. **Your ingestion logic** — You decide which URIs from a bundle are relevant, how to process them, how to chunk/transform content, and what to store.

6. **Your observation reactions** — You decide what to do when other plugins finish ingesting (auditing, notifications, cross-plugin triggers).

## What the Platform Provides

You don't build these — they're shared infrastructure:

- **The `documents` table** — A shared table with columns: `id`, `uri`, `plugin`, `doctype`, `metadata` (JSON). Your plugin writes rows tagged with your plugin name and doctype. Other plugins can read your data by querying your doctype.
- **The `vec_documents` table** — Vector embeddings linked to document rows. Used for semantic (KNN) search.
- **The `PluginRegistry`** — Handles registration, tool routing, and doctype catalog. You register; it routes.
- **The `IngestionPipeline`** — Two-phase pipeline: broadcasts bundles to processors (Phase 1), then notifies observers with structured events (Phase 2).
- **Cross-plugin queries** — Any plugin can query by `plugins` and/or `doctypes` lists. If your data is useful to others, they can discover it via `list_doctypes` and query it via `semantic_search`.

## Plugin Interfaces

There are three interfaces. Pick any combination depending on what your plugin does:

| Interface | Role | When to use |
|-----------|------|-------------|
| **ToolProvider** | Expose tools to AI clients | You want AI agents to call your plugin's functionality |
| **IngestProcessor** | Do ingestion work (parse, chunk, store) | You want to process raw URIs and write documents to storage |
| **IngestObserver** | React to completed ingestion | You want to know when other plugins have finished ingesting (audit, notify, trigger) |

Common combinations:

| Pattern | Example | Use Case |
|---------|---------|----------|
| ToolProvider only | `DocumentRetrievalPlugin` | Query/action tools, no ingestion |
| IngestProcessor only | *(future)* Metrics collector | Silently processes documents |
| IngestObserver only | *(future)* Audit plugin | Reacts when ingestion completes |
| ToolProvider + IngestProcessor | `MarkdownPlugin` | Ingests AND exposes search tools |
| ToolProvider + IngestObserver | *(future)* Dashboard plugin | Tools AND reacts to ingestion |

### ToolProvider — Expose tools to AI clients

```python
from team_mind_mcp.server import ToolProvider, DoctypeSpec
from mcp.types import Tool, TextContent

class MyPlugin(ToolProvider):
    @property
    def name(self) -> str:
        return "my_plugin"

    @property
    def doctypes(self) -> list[DoctypeSpec]:
        return [
            DoctypeSpec(
                name="my_data_type",
                description="What this document type represents.",
                schema={
                    "field_a": {"type": "string", "description": "..."},
                    "field_b": {"type": "integer", "description": "..."},
                }
            )
        ]

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="my_tool",
                description="What this tool does.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            )
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name == "my_tool":
            # Your logic here
            return [TextContent(type="text", text="result")]
        raise ValueError(f"Unknown tool: {name}")
```

### IngestProcessor — Process incoming documents

Processors receive raw URIs, do the heavy lifting (parsing, chunking, embedding), write to storage, and return `IngestionEvent` objects describing what they wrote.

```python
from team_mind_mcp.server import IngestProcessor, DoctypeSpec
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.ingestion import IngestionBundle, IngestionEvent

class MyIngestionPlugin(IngestProcessor):
    def __init__(self, storage: StorageAdapter):
        self.storage = storage

    @property
    def name(self) -> str:
        return "my_ingestion_plugin"

    @property
    def doctypes(self) -> list[DoctypeSpec]:
        return [
            DoctypeSpec(
                name="processed_item",
                description="An item extracted during ingestion.",
                schema={"content": {"type": "string"}}
            )
        ]

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        doc_ids = []
        processed_uris = []

        for uri in bundle.uris:
            if not self._is_relevant(uri):
                continue

            processed_uris.append(uri)
            content = self._fetch_and_process(uri)
            vector = self._generate_embedding(content)

            # Pointer mode: store URI reference, fetch content on demand
            doc_id = self.storage.save_payload(
                uri=uri,
                metadata={"summary": content[:200]},
                vector=vector,
                plugin=self.name,
                doctype="processed_item"
            )
            doc_ids.append(doc_id)

            # OR Embedded mode: store full content in metadata
            doc_id = self.storage.save_payload(
                uri=uri,
                metadata={"local_payload": content, "summary": content[:200]},
                vector=vector,
                plugin=self.name,
                doctype="processed_item"
            )
            doc_ids.append(doc_id)

        # Return events describing what you wrote
        if processed_uris:
            return [IngestionEvent(
                plugin=self.name,
                doctype="processed_item",
                uris=processed_uris,
                doc_ids=doc_ids
            )]
        return []
```

### IngestObserver — React to completed ingestion

Observers don't process raw URIs. They receive structured `IngestionEvent` objects **after** all processors have finished, describing what was written. Use this for auditing, notifications, cross-plugin triggers, or any reaction to "something was just ingested."

```python
from team_mind_mcp.server import IngestObserver
from team_mind_mcp.ingestion import IngestionEvent

class AuditPlugin(IngestObserver):
    @property
    def name(self) -> str:
        return "audit_plugin"

    async def on_ingest_complete(self, events: list[IngestionEvent]) -> None:
        for event in events:
            if event.plugin == "java_plugin" and event.doctype == "code_signature":
                # Java code was updated — trigger compliance audit
                await self._run_audit(event.uris, event.doc_ids)
```

**What's in an IngestionEvent:**
```python
@dataclass
class IngestionEvent:
    plugin: str          # Which processor wrote the data
    doctype: str         # What doctype was written
    uris: list[str]      # Which source URIs were processed
    doc_ids: list[int]   # IDs of the document rows created
```

### Combining interfaces

```python
# Ingest AND expose tools (like MarkdownPlugin)
class MyFullPlugin(ToolProvider, IngestProcessor):
    # Implement: name, doctypes, get_tools, call_tool, process_bundle
    ...

# Tools AND react to ingestion
class MyDashboard(ToolProvider, IngestObserver):
    # Implement: name, get_tools, call_tool, on_ingest_complete
    ...
```

## The Two-Phase Ingestion Pipeline

When documents are ingested, the pipeline runs in two phases:

```
Phase 1 — Processing (parallel):
  Raw URIs → IngestionBundle → broadcast to all IngestProcessors
  → Each processor writes documents, returns IngestionEvents

Phase 2 — Observation (parallel, after Phase 1 completes):
  Collected IngestionEvents → broadcast to all IngestObservers
  → Each observer reacts to what was written
```

**Key guarantee:** Observers never run until all processors have finished. When your observer receives events, the data is committed and queryable.

## Storage: How Your Data Lives in the Database

The `documents` table is shared, but your data is yours:

```
┌──────────────────────────────────────────────────────────────────┐
│                        documents table                           │
├────┬──────────────────┬───────────────────┬───────────┬──────────┤
│ id │ uri              │ plugin            │ doctype   │ metadata │
├────┼──────────────────┼───────────────────┼───────────┼──────────┤
│  1 │ file:///doc.md   │ markdown_plugin   │ md_chunk  │ {chunk…} │
│  2 │ file:///doc.md   │ markdown_plugin   │ md_chunk  │ {chunk…} │
│  3 │ user://input     │ travel_plugin     │ interest  │ {local…} │
│  4 │ https://dest.com │ travel_plugin     │ dest_info │ {name…}  │
│  5 │ file:///code.py  │ ast_plugin        │ signature │ {func…}  │
└────┴──────────────────┴───────────────────┴───────────┴──────────┘

 Your plugin's rows are scoped by the `plugin` and `doctype` columns.
 Other plugins can query your data by doctype, but you own it.
```

**Key points:**
- The `plugin` column is always set to your plugin's `name` property. This is automatic ownership.
- The `doctype` column is whatever you declared in your `doctypes` property. One plugin can have multiple doctypes.
- The `metadata` column is a JSON blob — you define its shape. Your doctype's `schema` tells others what to expect, but it's not enforced (advisory only).
- The `uri` column identifies the source. For embedded content, it can be any identifier you choose (e.g., `user://preferences/hiking`).

## Querying Data (Yours or Other Plugins')

```python
# Query your own data
results = storage.retrieve_by_vector_similarity(
    vector, limit=10,
    plugins=["my_plugin"],
    doctypes=["my_data_type"]
)

# Query another plugin's data (cross-plugin)
results = storage.retrieve_by_vector_similarity(
    vector, limit=10,
    plugins=["travel_plugin"],
    doctypes=["interest", "dest_info"]
)

# Query across all plugins (no filters)
results = storage.retrieve_by_vector_similarity(vector, limit=10)
```

All filter parameters accept **lists**, so you can query multiple plugins and doctypes in a single call.

## Registering Your Plugin

There are two ways to register plugins:

### Compile-time registration (core plugins)

Core plugins are registered in `cli.py` at server startup:

```python
my_plugin = MyPlugin(storage)
gateway.registry.register(my_plugin)
```

### Runtime registration (dynamic plugins)

Plugins can be registered at runtime via the `register_plugin` MCP tool — no server restart needed:

```json
// AI agent or admin calls:
register_plugin(module_path="my_plugins.travel.TravelPlugin", config={...})
```

Dynamically registered plugins:
- Are persisted to the `registered_plugins` table — they survive restarts
- Can be unregistered via `unregister_plugin(plugin_name)`
- Can be listed via `list_plugins()`

### What happens on registration:
- Your tools are added to the MCP tool catalog (visible to AI clients).
- Your doctypes are added to the doctype catalog (discoverable via `list_doctypes`).
- If you implement `IngestProcessor`, you start receiving bundles during ingestion.
- If you implement `IngestObserver`, you start receiving events after ingestion completes.

### Event subscriptions for observers

By default, observers receive **all** ingestion events (fire hose). To subscribe to specific events only, override the `event_filter` property:

```python
from team_mind_mcp.server import IngestObserver, EventFilter

class AuditPlugin(IngestObserver):
    @property
    def event_filter(self) -> EventFilter | None:
        # Only care about Java code changes
        return EventFilter(
            plugins=["java_plugin"],
            doctypes=["code_signature"]
        )

    async def on_ingest_complete(self, events):
        # Only receives java_plugin:code_signature events
        for event in events:
            await self._run_audit(event.uris)
```

| Pattern | event_filter returns | What the observer receives |
|---------|---------------------|--------------------------|
| Fire hose | `None` (default) | Every event from every processor |
| Plugin filter | `EventFilter(plugins=["java_plugin"])` | Only events from that plugin |
| Doctype filter | `EventFilter(doctypes=["code_signature"])` | Only events with that doctype |
| Combined | `EventFilter(plugins=[...], doctypes=[...])` | Events matching both |

## Integration Options Summary

Team Mind plugins support a wide array of integration patterns:

| Capability | Options |
|-----------|---------|
| **Interfaces** | `ToolProvider`, `IngestProcessor`, `IngestObserver` — any combination |
| **Registration** | Compile-time (hardcoded in cli.py) or runtime (via `register_plugin` MCP tool) |
| **Observation mode** | Fire hose (all events) or topic-based (filtered by plugin/doctype) |
| **Storage mode** | Pointer (URI reference) or embedded (`local_payload` in metadata) |
| **Idempotent ingestion** | Content hashing, plugin versioning, `IngestionContext` per URI |
| **Relevance weighting** | Decay policy per doctype, feedback signals, tombstoning |
| **Document updates** | In-place (`update_payload`) or wipe-and-replace (`delete_by_uri`) |

## Relevance Weighting (Platform-Managed)

The platform automatically manages relevance weighting for all plugins. You don't implement scoring — the platform does it for you. Your documents gain or lose value based on AI/human feedback and time-based decay.

### What you get for free

- **Usage-based ranking**: When an AI agent or human calls `provide_feedback(doc_id, signal)`, the platform updates the document's score. Higher-scored documents rank higher in search results.
- **Composite scoring**: Search results are ranked by `final_rank = vector_distance - (usage_score * weight_influence * decay_factor)`, not just vector distance alone.
- **Tombstoning**: Bad documents can be flagged out of all search results without being deleted.

### What you control: Decay policy

Declare `decay_half_life_days` on your DoctypeSpec to control how fast your data's boost decays over time:

```python
DoctypeSpec(
    name="meeting_notes",
    description="Notes from team meetings.",
    decay_half_life_days=30,     # Loses half its boost every 30 days
)

DoctypeSpec(
    name="code_signature",
    description="Function signatures from source code.",
    decay_half_life_days=None,   # No decay — code doesn't age
)
```

- `None` (default) = no decay. Usage score stays at full value forever.
- A number = half-life in days. After that many days, the effective score is halved.

### How scoring works

| What | Who does it | How |
|------|-------------|-----|
| Feedback signals | AI agents / humans via `provide_feedback` MCP tool | `signal` from -5 (strongly demote) to +5 (strongly promote) |
| Score accumulation | Platform | Signals are **averaged**: each new signal is folded into the running average proportionally |
| Decay | Platform, at query time | `effective_score = usage_score * 0.5^(days_old / half_life)` |
| Tombstone | AI agents / humans via `provide_feedback(tombstone=true)` | Document excluded from all search results, reversible |

### What if you don't care about weighting?

Don't set `decay_half_life_days`. Don't call `provide_feedback`. Your documents get `usage_score=0.0`, `decay_factor=1.0`, and results are ranked by **pure vector distance** — identical to a system with no weighting at all.

### The `doc_weights` table

Each document gets one row in `doc_weights` (auto-created when the document is saved):

```
doc_weights
├── doc_id          → FK to documents
├── usage_score     → Running average of feedback signals (starts at 0.0)
├── signal_count    → Number of signals received (for averaging math)
├── created_at      → When the doc was ingested
├── last_accessed   → Last feedback timestamp
├── tombstoned      → 0 or 1
└── decay_half_life_days → Copied from DoctypeSpec (nullable)
```

There is **one row per document**, not one row per feedback event. The running average is maintained via `signal_count` — no compaction or aggregation needed at scale.

### Idempotent ingestion (content hashing & plugin versioning)

When the pipeline broadcasts a bundle, it provides an `IngestionContext` for each URI in `bundle.contexts[uri]`. This tells your processor whether the URI has been ingested before, whether the content changed, and whether your plugin version has changed:

```python
async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
    for uri in bundle.uris:
        ctx = bundle.contexts.get(uri)

        if ctx and ctx.is_update:
            # We've seen this URI before
            current_hash = hashlib.sha256(content.encode()).hexdigest()

            if ctx.previous_content_hash == current_hash and not ctx.plugin_version_changed:
                continue  # Nothing changed — skip

            # Content or version changed — wipe and re-ingest
            self.storage.delete_by_uri(uri, plugin=self.name, doctype="my_type")

        # Process and save with hash + version
        doc_id = self.storage.save_payload(
            uri, metadata, vector,
            plugin=self.name, doctype="my_type",
            content_hash=current_hash, plugin_version=self.version,
        )
```

**Plugin decision matrix:**

| is_update | content_changed | version_changed | Typical action |
|-----------|----------------|-----------------|----------------|
| false | N/A | N/A | Fresh insert |
| true | false | false | Skip (nothing changed) |
| true | true | false | Wipe and replace |
| true | false | true | Re-process (plugin logic changed) |
| true | true | true | Wipe and replace |

**Declaring your plugin version:**

```python
class MyPlugin(IngestProcessor):
    @property
    def version(self) -> str:
        return "1.0.0"  # Bump when your processing logic changes
```

Default is `"0.0.0"`. The platform stores this with every document so future versions of your plugin can detect docs processed by older logic.

### Updating and replacing documents

The platform provides two methods for keeping data current:

**Update a specific chunk in place** (preserves its weight):
```python
# Plugin knows the doc_id of the chunk it wants to update
storage.update_payload(
    doc_id=42,
    metadata={"chunk": "updated content", "version": 2},
    vector=new_embedding
)
# uri, plugin, doctype, and usage_score are all preserved
```

**Wipe and re-ingest a whole document** (fresh start):
```python
# Delete all old chunks for this URI, then re-ingest
deleted = storage.delete_by_uri(
    uri="file:///doc.md",
    plugin=self.name,
    doctype="markdown_chunk"
)
# Now insert new chunks — they start with usage_score=0.0
for chunk in new_chunks:
    storage.save_payload(uri, chunk_meta, vector, plugin=self.name, doctype="markdown_chunk")
```

`delete_by_uri` is scoped to your plugin and doctype — it won't touch another plugin's data for the same URI. Deletion removes the document, vector, and weight rows together.

**Which to use:** If your chunks have stable identities (e.g., a user preference by ID), use `update_payload`. If the document's structure changes on update (paragraphs added/removed), use wipe-and-replace.

### Score averaging (not additive)

Scores use a **cumulative moving average**, not simple addition. Each new signal is averaged into the existing score proportionally:

```
new_count = old_count + 1
new_score = old_score + (signal - old_score) / new_count
```

This means:
- After 100 signals of +5, the average is 5.0
- One person comes along and gives -5 → average becomes ≈ 4.9 (barely moves)
- The score naturally stays bounded to [-5, +5] (the signal range) with no artificial clamping
- Every signal gets proportional weight — early signals and late signals are treated fairly

The `doc_weights` table tracks `signal_count` alongside `usage_score` to maintain the running average.

### URIs for embedded content

When storing content in embedded mode (`local_payload`), the URI is just a **string identifier** — it doesn't need to point to a real file or URL. Use any scheme that makes sense for your data:

```python
# These are all valid URIs for embedded content:
"user://preferences/hiking"
"chat://session-123/msg-5"
"virtual://generated-summary-42"
"api://weather/2026-03-25"
```

The URI serves as a logical identifier for `delete_by_uri` and `get_full_document` lookups regardless of storage mode.

### Chunks are a plugin concept, not a core concept

The platform has no concept of "chunks." Every row in the `documents` table is just a document — the platform doesn't know or care whether a row represents a whole file, a paragraph, a sentence, or a function signature. If your plugin splits a source file into 10 chunks, that's 10 document rows. If another plugin stores one row per file, that's fine too. The platform treats all rows identically.

## Discovery: How Others Find Your Data

AI clients can call the `list_doctypes` MCP tool to discover what's available:

```json
// list_doctypes(plugins=["travel_plugin"])
[
  {
    "plugin": "travel_plugin",
    "name": "interest",
    "description": "A user's stated travel interest or preference.",
    "schema": {"category": {"type": "string"}, "sentiment": {"type": "string"}}
  },
  {
    "plugin": "travel_plugin",
    "name": "dest_info",
    "description": "Information about a travel destination.",
    "schema": {"name": {"type": "string"}, "region": {"type": "string"}}
  }
]
```

This makes the knowledge base self-describing. An AI agent can ask "what data exists?" and adapt its queries.

## Reference

| Document | What it covers |
|----------|---------------|
| [ADR-002: Plugin Architecture](ADRs/ADR-002-plugin-architecture.md) | Three interfaces, two-phase pipeline, dual-mode storage, design rationale |
| [ADR-001: Plugin-Scoped Doctypes](ADRs/ADR-001-plugin-scoped-doctypes.md) | Doctype namespacing, cross-plugin queries, schema contracts |
| [SPEC-001: Core Engine](../../specs/SPEC-001-core-engine/design.md) | MCP gateway, storage adapter, ingestion pipeline internals |
| [SPEC-002: Plugin Data Schema](../../specs/SPEC-002-plugin-data-schema/design.md) | DoctypeSpec model, scoped queries, discovery tool |
| [SPEC-003: Ingestion Interface Split](../../specs/SPEC-003-ingestion-interface-split/design.md) | IngestProcessor/IngestObserver split, IngestionEvent, two-phase pipeline |
| [ADR-003: Relevance Weighting](ADRs/ADR-003-relevance-weighting.md) | Scoring model, decay policy, tombstoning, signal design |
| [SPEC-004: Relevance Weighting](../../specs/SPEC-004-relevance-weighting/design.md) | doc_weights table, feedback tool, composite scoring, spike results |
| [ADR-004: Idempotent Ingestion](ADRs/ADR-004-idempotent-ingestion.md) | Content hashing, plugin versioning, IngestionContext, decision matrix |
| [SPEC-005: Idempotent Ingestion](../../specs/SPEC-005-idempotent-ingestion/design.md) | Schema changes, pipeline integration, MarkdownPlugin optimization |
| [ADR-005: Plugin Lifecycle](ADRs/ADR-005-plugin-lifecycle.md) | Dynamic registration, event subscriptions, persistent state |
| [SPEC-006: Plugin Lifecycle](../../specs/SPEC-006-plugin-lifecycle/design.md) | EventFilter, persistence table, MCP tools, startup recovery |
| [System Overview](system-overview.md) | High-level architecture and design philosophy |
