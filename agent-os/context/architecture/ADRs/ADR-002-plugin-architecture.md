# ADR-002: Broadcast Plugin Architecture with Dual Interfaces

**Status:** Accepted
**Date:** 2026-03-10 (retroactive — originally designed in SPEC-001)
**Spec:** SPEC-001 (Core Information Architecture, MVP)

## Context

Team Mind needs an extensible architecture where new capabilities (code parsing, metrics extraction, transcript processing) can be added without modifying the core system. The MCP server must expose tools from multiple independent domains, and the ingestion pipeline must allow multiple processors to extract different kinds of value from the same source material.

The key tension: a single markdown file might need semantic vectorization (for search), structural extraction (for code understanding), and metrics analysis (for quality tracking) — all from different processors. The architecture must support this without those processors knowing about each other.

## Decision

We adopt a **broadcast plugin architecture** with two decoupled interfaces and a central registry.

### 1. Two Plugin Interfaces

Plugins implement one or both of two abstract base classes:

- **`ToolProvider`** — Exposes MCP tools to connected AI clients. Defines `get_tools()` (returns tool definitions) and `call_tool(name, arguments)` (executes a tool). This is the retrieval/query side.

- **`IngestListener`** — Receives ingestion events. Defines `process_bundle(bundle)` which is called when new documents arrive. This is the write/processing side.

Plugins can implement either interface independently or both together:

| Pattern | Example | Use Case |
|---------|---------|----------|
| ToolProvider only | `DocumentRetrievalPlugin`, `IngestionPlugin` | Exposes query/action tools without processing ingestion events |
| IngestListener only | *(future)* Metrics collector | Processes documents silently without exposing tools |
| Both | `MarkdownPlugin` | Ingests documents AND exposes search tools |

This was refined in STORY-009 (Decouple Plugin Interfaces). The original design had a single `Plugin` base class, but this forced tool-only plugins to carry unused ingestion methods and vice versa.

### 2. PluginRegistry as Central Router

The `PluginRegistry` manages all plugin lifecycle:

- **Registration:** `register(plugin)` inspects the plugin via `isinstance` checks and routes it to the appropriate internal collections (`_tool_providers` for ToolProviders, `_ingest_listeners` for IngestListeners). Dual-interface plugins are registered in both.
- **Tool routing:** Maps tool names to their owning provider. Enforces uniqueness — no two plugins can register the same tool name.
- **Broadcast:** Exposes `get_ingest_listeners()` for the ingestion pipeline to iterate and broadcast bundles.

### 3. Broadcast Ingestion (Fan-Out)

When documents are ingested:

1. `IngestionPipeline` receives a list of URIs.
2. `ResourceResolver` expands directories, validates schemes (`file://`, `http://`, `https://`).
3. An `IngestionBundle` (list of resolved URIs) is created.
4. The bundle is broadcast to **all** registered `IngestListener` plugins via `asyncio.gather` (concurrent fan-out).
5. Each plugin independently decides which URIs are relevant (e.g., MarkdownPlugin filters for `.md` files) and processes them.

Plugins are responsible for their own filtering. The pipeline doesn't pre-sort or route based on file type — it simply broadcasts everything to everyone.

### 4. Dual-Mode Storage: Pointers and Embedded Content

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

### 5. MCP Gateway as Thin Router

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

### 4. Single Plugin base class (original design, superseded)

One `Plugin` ABC with both `get_tools()` and `process_bundle()` methods.

**Rejected (in STORY-009) because:**
- Tool-only plugins (IngestionPlugin, DocumentRetrievalPlugin) had to carry no-op `process_bundle` methods.
- Listener-only plugins would carry no-op `get_tools` methods.
- Dual interfaces via multiple inheritance is cleaner and more Pythonic — `isinstance` checks handle routing naturally.

### 5. Pre-sorted routing (pipeline routes by file type)

The ingestion pipeline inspects file extensions and only sends `.md` files to MarkdownPlugin, `.py` files to a code plugin, etc.

**Rejected because:**
- The pipeline would need to know about every plugin's preferences — tight coupling.
- Some plugins may want to process the same file type differently (e.g., a markdown file could be both vectorized and fact-extracted).
- Letting plugins self-filter is simpler and more extensible.

## Consequences

### Positive

- **Independent extensibility.** Adding a new plugin (e.g., code AST parser) requires zero changes to the core system — just implement the interface and register it.
- **Concurrent ingestion.** `asyncio.gather` processes bundles in parallel across all listeners. No plugin blocks another.
- **Flexible composition.** The dual-interface pattern (ToolProvider + IngestListener) lets plugins be exactly what they need to be — no unused interface baggage.
- **Client-side orchestration.** AI agents see all tools and choose their own query strategy. No server-side LLM required for retrieval orchestration.
- **Minimal infrastructure.** Single-process SQLite + in-process broadcast. No external brokers, no microservices.

### Negative

- **Broadcast inefficiency.** Every bundle goes to every listener, even if only one cares. At small scale (few plugins) this is negligible. At large scale, a topic-based routing layer may be needed.
- **No inter-plugin communication.** Plugins can't directly call each other. They share a `StorageAdapter` but can't invoke each other's tools. *(Partially addressed by SPEC-002's doctype system enabling cross-plugin data queries.)*
- **Single-process bottleneck.** The `asyncio.gather` fan-out is concurrent but not parallel (GIL-bound). CPU-intensive plugins (e.g., real embedding generation) will need offloading. Acceptable for MVP.
- **Tool name collisions.** The registry enforces global uniqueness of tool names. As the plugin ecosystem grows, naming conventions may be needed.

### Neutral

- The Librarian (Phase 2) will sit between broadcast and commit, adding a validation gate without changing the plugin interfaces.
- Storage is currently SQLite but the `StorageAdapter` abstraction allows migration to MongoDB (Phase 3) without plugin changes.

## Current Plugin Inventory

| Plugin | Interfaces | Tools | Purpose |
|--------|-----------|-------|---------|
| `MarkdownPlugin` | ToolProvider + IngestListener | `semantic_search` | Vectorizes markdown chunks, exposes semantic search |
| `DocumentRetrievalPlugin` | ToolProvider | `get_full_document` | Fetches full document content from URI pointers |
| `IngestionPlugin` | ToolProvider | `ingest_documents` | Exposes ingestion pipeline as an MCP tool for live use |

## Key Files

| File | Role |
|------|------|
| `src/team_mind_mcp/server.py` | `ToolProvider`, `IngestListener` ABCs, `PluginRegistry`, `MCPGateway` |
| `src/team_mind_mcp/ingestion.py` | `IngestionPipeline`, `IngestionBundle`, `ResourceResolver` |
| `src/team_mind_mcp/storage.py` | `StorageAdapter` (SQLite + sqlite-vec) |
| `src/team_mind_mcp/markdown.py` | `MarkdownPlugin` (dual interface) |
| `src/team_mind_mcp/retrieval.py` | `DocumentRetrievalPlugin` (tool only) |
| `src/team_mind_mcp/ingestion_plugin.py` | `IngestionPlugin` (tool only) |
| `src/team_mind_mcp/cli.py` | CLI entry point, wires everything together |
