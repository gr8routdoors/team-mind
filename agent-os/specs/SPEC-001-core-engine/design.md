# SPEC-001: Core Information Architecture (MVP) — Design

## Overview

This MVP establishes the "Core Engine" backend in Python. It centers around a pluggable architecture where the MCP server handles external connectivity, the Ingestion Engine handles broadcasting files/urls as "Bundles", the Storage Layer manages SQLite connections, and individual Plugins register specialized tools and handle domain-specific data extraction.

## Components

| Component | Type | Purpose |
|-----------|------|---------|
| MCPGateway | Server Interface | Normalizes tools and handles AI client connections via the MCP Protocol. |
| PluginRegistry | Core Manager | Registers available plugins and routes incoming ingestion bundles to them. |
| StorageAdapter | Abstraction | Manages the connection pool and schemas for SQLite (`sqlite-vec` + JSON1). |
| IngestionPipeline | Event Loop | Monitors for new URIs/inputs, packages them as Bundles, and broadcasts them. |
| ResourceResolver | Utility | Fetches content from a URI (local file, http, etc.) on demand to prevent storage bloat. |
| MarkdownPlugin | Plugin | Parses `.md` files, generates embeddings, stores the Source Pointer, and registers `semantic_search`. |
| DocumentRetrievalPlugin | Plugin | Dedicated to fetching full source context from either the DB or the live URI pointer. Registers `get_full_document`. |

## Data Flow

### Ingestion Flow
1. User or script submits a list of one or more URIs (file paths, web URLs, etc.).
2. `IngestionPipeline` creates a single `ResourceBundle` object containing the underlying URIs.
3. `IngestionPipeline` passes the bundle to the `PluginRegistry`.
4. `PluginRegistry` iterates through all active plugins (e.g., `MarkdownPlugin`), broadcasting the `.process_bundle(bundle)` event.
5. `MarkdownPlugin` uses a `ResourceResolver` to fetch the markdown text for relevant URIs, chunks it, and creates vectors.
6. `MarkdownPlugin` calls `StorageAdapter` to insert the vector embeddings and the Source Pointers (URIs).

### Retrieval Flow
1. AI Client calls `mcp_call("semantic_search", {"query": "how do I configure AWS"})`.
2. `MCPGateway` routes the tool call down to the registered `MarkdownPlugin`.
3. `MarkdownPlugin` vectorizes the query and calls `StorageAdapter` to perform an ANN query in SQLite.
4. `MarkdownPlugin` returns summarized snippets with their associated URIs to the AI Client.
5. AI Client determines it needs the full context, so it calls `mcp_call("get_full_document", {"uri": "file:///path/to/docs.md"})`.
6. `MCPGateway` routes to `DocumentRetrievalPlugin`, which uses the `ResourceResolver` to fetch the real-time contents from the remote/local URI (or embedded DB if flagged for local storage) and returns it.

## API Contracts

**MCP Tools (Exposed by MarkdownPlugin):**
- `semantic_search(query: str, limit: int = 5) -> List[SearchResult]`
- `get_full_document(document_id: str) -> str`

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Deferring "Librarian" | Build now vs Phase 2 | Ensure the base deterministic SQLite, Vector, and MCP loop works perfectly before mixing in non-deterministic LLM-as-a-judge validation logic. |

---

## Execution Plan

Implementation tasks in recommended order:

### Task 1: Setup Storage Layer
- Scaffold SQLite connection management.
- Ensure extensions (`sqlite-vec`, JSON capability) function correctly.
- *Stories:* STORY-002

### Task 2: Core MCP Gateway & Extensibility
- Build Plugin interface/contract.
- Scaffold the `mcp` Python server and expose registered dummy tools.
- *Stories:* STORY-001

### Task 3: Bundle Broadcast Ingestion
- Implement the loop that accepts paths, creates Bundles, and alerts Plugins.
- *Stories:* STORY-003

### Task 4: Markdown Vector Plugin
- Implement Markdown parsing and embedding generation.
- Hook into Storage Adapter for saving vectors and pointers.
- Expose the semantic search tool.
- *Stories:* STORY-004

### Task 5: Document Retrieval Plugin
- Implement the dedicated retrieval plugin.
- Setup `ResourceResolver` to abstract fetching from DB vs local file vs network URI.
- Expose the full document fetch tool.
- *Stories:* STORY-005
