# ADR-002: Plugin Architecture with Three Interfaces

**Status:** Accepted
**Date:** 2026-03-10 (retroactive — originally designed in SPEC-001, updated 2026-03-25, updated 2026-03-29 for SPEC-008, updated 2026-03-30 for SPEC-010)
**Spec:** SPEC-001 (Core Information Architecture, MVP), SPEC-003 (Ingestion Interface Split), SPEC-008 (Semantic Type Routing), SPEC-010 (Multi-Tenancy & Metadata Search)
**See also:** [Plugin Developer Guide](../plugin-developer-guide.md) — practical guide for building plugins; [ADR-007: Three-Type Model](ADR-007-semantic-type-routing.md) — semantic type routing and the three-type model; [ADR-008: Multi-Tenancy & Metadata Search](ADR-008-multi-tenancy-metadata-search.md) — tenancy model, metadata search; [ADR-010: Tenant Sharding](ADR-010-tenant-sharding.md) — file-level sharding, TenantStorageManager, scatter-gather; [ADR-009: Document Segments](ADR-009-document-segments.md) — parent-child hierarchy formalizing the plugin chunking pattern introduced here

## Context

Team Mind needs an extensible architecture where new capabilities (code parsing, metrics extraction, transcript processing) can be added without modifying the core system. The MCP server must expose tools from multiple independent domains, and the ingestion pipeline must allow multiple processors to extract different kinds of value from the same source material.

The key tension: a single markdown file might need semantic vectorization (for search), structural extraction (for code understanding), and metrics analysis (for quality tracking) — all from different processors. The architecture must support this without those processors knowing about each other.

Additionally, some plugins need to **react** to completed ingestion rather than participate in it. For example, an audit plugin may want to know when a Java code plugin has finished indexing new source files — not to process the raw URIs itself, but to take action based on what was ingested. This requires separating "do ingestion work" from "observe ingestion events."

## Decision

We adopt a **broadcast plugin architecture** with three decoupled interfaces and a central registry.

### 1. Three Plugin Interfaces

Plugins implement one or more of three abstract base classes:

- **`ToolProvider`** — Exposes MCP tools to connected AI clients. Defines `get_tools()` (returns tool definitions) and `call_tool(name, arguments)` (executes a tool). This is the retrieval/query side.

- **`IngestProcessor`** — Does the actual ingestion work. Defines `process_bundle(bundle)` which receives raw URIs and writes documents to storage. Called **during** ingestion, in parallel with other processors. This is the write/processing side.

- **`IngestObserver`** — Reacts to completed ingestion. Defines `on_ingest_complete(events)` which receives a list of `IngestionEvent` objects describing what was just written. Called **after** all processors finish. This is the event/reaction side.

Plugins can implement any combination of interfaces:

| Pattern | Example | Use Case |
|---------|---------|----------|
| ToolProvider only | `DocumentRetrievalPlugin`, `IngestionPlugin`, `DoctypeDiscoveryPlugin` | Exposes query/action tools without participating in ingestion |
| IngestProcessor only | *(future)* Silent metrics collector | Processes documents during ingestion without exposing tools |
| IngestObserver only | *(future)* Audit plugin, notification plugin | Reacts to completed ingestion events without processing or exposing tools |
| ToolProvider + IngestProcessor | `MarkdownPlugin` | Ingests documents AND exposes search tools |
| ToolProvider + IngestObserver | *(future)* Dashboard plugin | Exposes tools AND reacts to ingestion events |
| IngestProcessor + IngestObserver | *(future)* Chained processor | Processes documents and also observes what others ingested |

**Why three interfaces instead of two:**

The original design (SPEC-001) used a single `IngestListener` interface for both processing and observing. This conflated two fundamentally different roles:
- **Processors** receive raw URIs and do the heavy lifting (parsing, chunking, embedding, storing).
- **Observers** receive structured events describing what was already stored and take secondary actions (auditing, notifications, cross-plugin triggers).

Keeping them as one interface would mean an audit plugin receives raw URIs it doesn't care about, and would need to re-query the database to understand what just happened. Splitting them gives each interface exactly the information it needs.

### 2. IngestionEvent — The Observer's Contract

When an `IngestProcessor` finishes writing documents, the pipeline collects structured events:

```python
@dataclass
class IngestionEvent:
    plugin: str          # Which processor wrote the data
    record_type: str     # What record type was written
    uris: list[str]      # Which source URIs were processed
    doc_ids: list[int]   # IDs of the document rows created
```

Observers receive a list of these events — one per (plugin, record_type) combination — so they know exactly what changed without re-querying storage.

### 3. Two-Phase Ingestion Pipeline

The ingestion pipeline now runs in two phases:

```
Phase 1: Processing (parallel)
  URIs → IngestionBundle → broadcast to all IngestProcessors via asyncio.gather
  → Each processor writes its record types, returns IngestionEvents

Phase 2: Observation (parallel, after Phase 1 completes)
  Collected IngestionEvents → broadcast to all IngestObservers via asyncio.gather
  → Each observer reacts to the events it cares about
```

Phase 2 only runs after Phase 1 fully completes. Observers are guaranteed to see the final state of what was written.

### 4. PluginRegistry as Central Router

The `PluginRegistry` manages all plugin lifecycle:

- **Registration:** `register(plugin, semantic_types=None)` inspects the plugin via `isinstance` checks and routes it to the appropriate internal collections (`_tool_providers`, `_ingest_processors`, `_ingest_observers`). Multi-interface plugins are registered in all applicable collections. The optional `semantic_types` list controls which ingestion traffic the processor receives — a processor with no semantic types is available but idle.
- **Semantic type routing:** The registry maps semantic types to registered processors. `get_ingest_processors(semantic_types)` returns only the processors enabled for those types (plus wildcard processors). See [ADR-007](ADR-007-semantic-type-routing.md) for the full routing model.
- **Tool routing:** Maps tool names to their owning provider. Enforces uniqueness — no two plugins can register the same tool name.
- **Unregistration:** `unregister(plugin_name)` removes a plugin from all internal collections — tools, processors, observers, record types, semantic type associations. Does not delete the plugin's data.
- **Observer broadcast:** Exposes `get_ingest_observers()` for Phase 2 of the ingestion pipeline. Observers still receive events via broadcast (filtered by EventFilter, which now supports `semantic_types`).

### 5. Semantic Type Routing (replaces broadcast fan-out, SPEC-008)

When documents are ingested:

1. `IngestionPipeline` receives a list of URIs and `semantic_types` (e.g., `["architecture_docs"]`).
2. `ResourceResolver` expands directories, validates schemes (`file://`, `http://`, `https://`).
3. An `IngestionBundle` (list of resolved URIs + semantic types) is created.
4. **Phase 1:** The pipeline queries the registry for processors registered for those semantic types. The bundle is routed only to matching processors via `asyncio.gather`. Within the routed set, each processor further filters by its declared `supported_media_types`. Each processor returns `IngestionEvent` objects (now including `semantic_types`) describing what it wrote.
5. **Phase 2:** The collected events are broadcast to all registered `IngestObserver` plugins via `asyncio.gather`. Observers filter by their `EventFilter` (which now supports `semantic_types` filtering).

This replaces the previous model where the bundle was broadcast to all processors and each plugin self-filtered. See [ADR-007](ADR-007-semantic-type-routing.md) for rationale and alternatives considered.

### 6. Dual-Mode Storage: Pointers and Embedded Content

The storage layer supports **two modes** for document content, and they can coexist in the same table:

**Mode A: Pointer-based (URI reference)**
- The `documents` table stores the URI as a pointer to the original source.
- When an AI agent needs the full document, `DocumentRetrievalPlugin` resolves and fetches it live from the URI (local file via `file://`, remote via `http://`/`https://`).
- Best for: long-lived documents with a stable source location (files on disk, web pages, Confluence docs).
- Advantage: prevents storage bloat at scale — the database holds semantic indexes and metadata, not copies of every document.

**Mode B: Embedded content (stored in metadata)**
- The full document content is stored directly in the `metadata` JSON column under a `local_payload` key.
- When `DocumentRetrievalPlugin` resolves a document, it checks for `local_payload` **first** — if present, it returns the embedded content immediately without any network or filesystem access.
- Best for: ephemeral content without a stable URI (uploaded text, chat transcripts, user-provided notes, API responses), or situations where the original source may disappear.
- Advantage: fully self-contained — the database is the source of truth, not dependent on external availability.

**How retrieval works (in order):**
1. `DocumentRetrievalPlugin` looks up the URI in the `documents` table.
2. If the matching row's metadata contains `local_payload` → return it directly (Mode B).
3. Otherwise → resolve the URI and fetch content live from the source (Mode A).
4. If the live source is unreachable → return an error indicating the document is no longer available.

Plugins choose which mode to use per-document at ingestion time. A single knowledge base can contain a mix of pointer-based and embedded documents. This is not an either/or architectural choice — both modes are first-class.

### 7. MCP Gateway as Thin Router

The `MCPGateway` is deliberately thin:

- Wraps the official `mcp.server.Server` instance.
- Registers two handlers: `list_tools` (aggregates from all providers) and `call_tool` (routes to the correct provider).
- No business logic, no orchestration — the gateway just multiplexes.
- AI clients (Claude, Cursor, custom agents) do their own orchestration over the exposed tools.

## Alternatives Considered

### 1. Monolithic processor with configuration

A single ingestion engine configured with a list of file types and processing rules.

**Rejected because:**
- Every new domain (code, metrics, transcripts) would require modifying the core engine.
- No separation of concerns — parsing logic, storage logic, and tool definitions would all live in one place.
- Testing becomes a combinatorial nightmare.

### 2. Pipeline-style (linear chain) processing

Each plugin processes documents in sequence, passing results to the next.

**Rejected because:**
- Plugins extracting different dimensions of value (semantics vs. structure vs. metrics) are independent, not sequential.
- A linear chain implies ordering dependencies that don't exist.
- Failure in one plugin would block downstream plugins.

### 3. Message queue / event bus (Kafka, RabbitMQ)

External message broker for decoupling producers and consumers.

**Rejected because:**
- Massive infrastructure overhead for an MVP that runs as a single process.
- The in-process `asyncio.gather` broadcast achieves the same fan-out with zero deployment cost.
- Can be introduced later if Team Mind scales to multi-process / distributed.

### 4. Single Plugin base class (original design, superseded in SPEC-001)

One `Plugin` ABC with both `get_tools()` and `process_bundle()` methods.

**Rejected (in STORY-009) because:**
- Tool-only plugins had to carry no-op `process_bundle` methods.
- Listener-only plugins would carry no-op `get_tools` methods.
- Multiple interfaces via multiple inheritance is cleaner and more Pythonic.

### 5. Pre-sorted routing by file type (partially superseded in SPEC-008)

The ingestion pipeline inspects file extensions and only sends `.md` files to MarkdownPlugin, `.py` files to a code plugin, etc.

**Originally rejected** (tight coupling, plugins wanting to share file types). **SPEC-008 adopts semantic-type-based routing** — routing is not by file extension but by the semantic meaning of the data, configured at registration time. Media type filtering (file extension / MIME type) is still applied per-plugin as a secondary filter within a routed bundle, but routing itself is semantic. See [ADR-007](ADR-007-semantic-type-routing.md).

### 6. Single IngestListener for both processing and observing (original design, superseded in SPEC-003)

One `IngestListener` interface that receives bundles and is used for both active processing and passive observation.

**Rejected because:**
- Conflates two fundamentally different roles: "do ingestion work" vs. "react to completed ingestion."
- Observers would receive raw URIs they don't care about and would need to re-query storage to understand what happened.
- Processors and observers need different inputs: processors need raw URIs, observers need structured events (plugin, record_type, doc IDs).
- Two-phase pipeline (process then observe) provides ordering guarantees that a single-phase broadcast cannot.

## Consequences

### Positive

- **Independent extensibility.** Adding a new plugin requires zero changes to the core system — just implement the interface(s) and register.
- **Concurrent ingestion.** `asyncio.gather` processes bundles in parallel across all processors. No plugin blocks another.
- **Flexible composition.** The three-interface pattern lets plugins be exactly what they need to be — no unused interface baggage.
- **Reactive observers.** Plugins can react to completed ingestion with full context (what was written, by whom, which record types) without re-querying.
- **Client-side orchestration.** AI agents see all tools and choose their own query strategy. No server-side LLM required.
- **Minimal infrastructure.** Single-process SQLite + in-process broadcast. No external brokers, no microservices.

### Negative

- **Routing complexity.** SPEC-008 replaces broadcast-to-all with semantic-type-based routing. The pipeline must look up semantic type registrations, match media types, and build the routed processor list. More logic, more tests needed.
- **No inter-plugin communication.** Plugins can't directly call each other. They share a `StorageAdapter` but can't invoke each other's tools. *(Partially addressed by SPEC-002's record type system enabling cross-plugin data queries.)*
- **Single-process bottleneck.** The `asyncio.gather` fan-out is concurrent but not parallel (GIL-bound). CPU-intensive plugins will need offloading.
- **Tool name collisions.** The registry enforces global uniqueness of tool names. Naming conventions may be needed at scale.
- **Caller must know semantic types.** The ingestion caller specifies what the data means — additional burden but also clarity about intent.

### Neutral

- The inline Librarian concept has been retired (ADR-006). Reliability is addressed via Reliability Seeding (SPEC-007) and a future background conflict detection reaper.
- Storage is currently SQLite but the `StorageAdapter` abstraction allows migration without plugin changes.
- **SPEC-010 (Multi-Tenancy):** The `registered_plugins` table moved from per-tenant `StorageAdapter` to `system.sqlite` (managed by `TenantStorageManager`). Plugins are registered globally once. `IngestProcessor` plugins no longer hold a `storage` reference — the pipeline injects `bundle.storage` at call time, pointing to the correct per-tenant `StorageAdapter`. Plugins are completely tenant-unaware by design. See [ADR-008](ADR-008-multi-tenancy-metadata-search.md) and [ADR-010](ADR-010-tenant-sharding.md).
- **SPEC-011 (Document Segments):** The plugin chunking pattern introduced here (splitting a source into multiple rows via `process_bundle`) is now formally structured with a `parent_id` column on `documents`. Plugins that chunk content use `save_parent` + `parent_id` on `save_payload` to create an explicit parent-child hierarchy. Backward compatible — existing plugins are unchanged. See [ADR-009: Document Segments](ADR-009-document-segments.md).

## Current Plugin Inventory

| Plugin | Interfaces | Tools | Purpose |
|--------|-----------|-------|---------|
| `MarkdownPlugin` | ToolProvider + IngestProcessor | `semantic_search` | Vectorizes markdown chunks, exposes semantic search |
| `DocumentRetrievalPlugin` | ToolProvider | `get_full_document`, `retrieve_documents` | Fetches full document content from URI pointers; weight-ranked retrieval |
| `IngestionPlugin` | ToolProvider | `ingest_documents` | Exposes ingestion pipeline as an MCP tool; routes to correct tenant shard |
| `DoctypeDiscoveryPlugin` | ToolProvider | `list_record_types` | Exposes record type catalog for AI client discovery |
| `FeedbackPlugin` | ToolProvider | `provide_feedback` | Relevance feedback signals for weighting; requires `tenant_id` (shard-scoped `doc_id`) |
| `LifecyclePlugin` | ToolProvider | `register_plugin`, `unregister_plugin`, `list_plugins` | Runtime plugin management; operates on `system.sqlite` |
| `TenantPlugin` | ToolProvider | `register_tenant`, `list_tenants` | Tenant lifecycle management via `TenantStorageManager` |

## Key Files

| File | Role |
|------|------|
| `src/team_mind_mcp/server.py` | `ToolProvider`, `IngestProcessor`, `IngestObserver`, `EventFilter` ABCs, `RecordTypeSpec`, `PluginRegistry`, `MCPGateway` |
| `src/team_mind_mcp/ingestion.py` | `IngestionPipeline`, `IngestionBundle`, `IngestionEvent`, `IngestionContext`, `ResourceResolver` |
| `src/team_mind_mcp/storage.py` | `StorageAdapter` (per-tenant SQLite + sqlite-vec); no `tenant_id` parameters — operates on one database |
| `src/team_mind_mcp/tenant_manager.py` | `TenantStorageManager` — per-tenant database lifecycle, `system.sqlite`, LRU adapter cache, scatter-gather |
| `src/team_mind_mcp/lifecycle.py` | `LifecyclePlugin`, `PluginLoader`, `load_persisted_plugins`; operates on `system.sqlite` via `TenantStorageManager` |
| `src/team_mind_mcp/markdown.py` | `MarkdownPlugin` (ToolProvider + IngestProcessor); uses `bundle.storage` in `process_bundle` |
| `src/team_mind_mcp/retrieval.py` | `DocumentRetrievalPlugin` (ToolProvider only) |
| `src/team_mind_mcp/ingestion_plugin.py` | `IngestionPlugin` (ToolProvider only); passes `tenant_id` to pipeline |
| `src/team_mind_mcp/discovery.py` | `DoctypeDiscoveryPlugin` (ToolProvider only) |
| `src/team_mind_mcp/feedback.py` | `FeedbackPlugin` (ToolProvider only); accepts `tenant_id`, resolves adapter via `TenantStorageManager` |
| `src/team_mind_mcp/tenant_plugin.py` | `TenantPlugin` (ToolProvider only); `register_tenant`, `list_tenants` |
| `src/team_mind_mcp/cli.py` | CLI entry point, wires everything together; uses `TenantStorageManager` exclusively |
