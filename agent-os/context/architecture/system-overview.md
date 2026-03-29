# System Architecture Overview

> **Building a plugin?** Start with the [Plugin Developer Guide](plugin-developer-guide.md) — it covers what you own, what the platform provides, and how to build with both storage modes.

## Design Philosophy

The core philosophy of "Team Mind" is to provide an intelligent, token-optimized, and highly extensible enterprise knowledge base. Moving beyond traditional "dumb" RAG (Retrieval-Augmented Generation) which relies solely on text chunking and semantic fuzziness, this system embraces a **Structured, Pluggable Architecture**. 

It prioritizes:
1. **Token Optimization & Precision:** Giving AI agents exactly the structural information they need (e.g., AST signatures) rather than raw, noisy files.
2. **Deterministic Retrieval:** Allowing agents to invoke explicit tools for specific data types instead of relying on unpredictable semantic search for everything.
3. **Rich, Multipronged Ingestion:** A single source file or resource can be processed by multiple specialized plugins to extract diverse layers of value (semantics, metrics, structural graphs).

## Project Structure & Architecture

The system is decomposed into three primary layers:

### 1. The Gateway Layer (MCP Server)
The universal entry point for the system is a **Model Context Protocol (MCP) Server**.
- It acts as the Host/Router that registers tools exposed by the underlying plugins.
- It normalizes the interface so that any MCP-compliant client (Claude, Cursor, custom agents) can seamlessly interact with the enterprise knowledge base.
- **Dynamic plugin management:** Plugins can be registered and unregistered at runtime via `register_plugin` / `unregister_plugin` MCP tools, without restarting the server. Core plugins (Markdown, Retrieval, etc.) are bundled; additional plugins are loaded dynamically from Python module paths and persisted across restarts.
- For non-MCP human interfaces (like MS Teams bots), a lightweight "Router API" (potentially backed by a fast LLM) will act as an intermediary client to query the MCP server on the human's behalf.

### 2. The Ingestion Pipeline (Semantic Routing & Validation)
Ingestion is treated as a systemic, multi-stage event rather than a simple database write.
- **Resource Bundles & URIs:** The system abstracts incoming data as "Resources" identified by URIs (e.g., `file://`, `https://`, `confluence://`), not just local files. A "Bundle" contains one or more of these Resources.
- **Dual-Mode Storage (Pointers + Embedded Content):** Each document row supports two retrieval modes. **Pointer mode:** the row stores a URI reference; when an AI requests the full document, a Resolver fetches it live from the source (`file://`, `https://`, etc.). This prevents data duplication at enterprise scale. **Embedded mode:** the full content is stored directly in the row's `metadata` JSON under `local_payload`; retrieval is instantaneous with no external dependency. Plugins choose per-document which mode to use at ingestion time — both are first-class, and a single knowledge base freely mixes them. Embedded mode is essential for ephemeral content (uploaded text, chat transcripts, API responses) that has no stable external URI.
- **Semantic Type Routing (SPEC-008):** Processors are no longer broadcast to unconditionally. The ingestion caller specifies `semantic_types` (e.g., `["architecture_docs"]`), and the pipeline routes the bundle only to `IngestProcessor` plugins registered for those types. Within a routed bundle, plugins additionally filter by their declared media type capabilities — a MarkdownPlugin only receives `.md` files even when routing is via `["*"]`. See the [Three-Type Model](#three-type-model) section below.
- **Phase 1 — Processing:** When a Bundle is ingested, the pipeline routes it to matching `IngestProcessor` plugins in parallel. Each processor parses the bundle, extracts domain-specific value (e.g., parsing code ASTs, vectorizing text, extracting facts), writes to storage, and returns structured `IngestionEvent` objects describing what was written.
- **Phase 2 — Observation:** After all processors complete, the collected `IngestionEvent` objects are broadcast to all registered `IngestObserver` plugins. Observers react to completed ingestion — auditing, notifications, cross-plugin triggers — without processing raw URIs. Observers are guaranteed to see the final committed state. EventFilter now supports `semantic_types` filtering.
- **Reliability Seeding (SPEC-007 — implemented):** The original inline Librarian concept has been retired (ADR-006). Reliability is addressed via three-layer score seeding at ingestion time: (1) caller-supplied `reliability_hint` passed through `ingest_documents` or `--reliability` CLI flag; (2) plugin-declared `RecordTypeSpec.default_reliability`; (3) platform default of `0.0`. Plugins resolve these layers in `process_bundle` and pass the result as `initial_score` to `save_payload`, which seeds `usage_score` in `doc_weights`.
- **Future: Background Conflict Detection:** An asynchronous background reaper will scan for near-duplicate content across different URIs and cross-document contradictions (semantic deduplication + contradiction detection). *(Future — see ADR-006)*

### 3. The Plugin Architecture (Renderers/Processors)
Plugins are specialized engines that handle both the ingestion parsing of resources and the registration of retrieval tools to the MCP Server.
- **Example Plugins:**
  - *Markdown/Text Plugin:* Handles semantic vectorization and keyword search. (Registers tool: `search_knowledge_base`)
  - *Document Retrieval Plugin:* Dedicated plugin for fetching raw content. Can retrieve from local DB storage or live URIs. (Registers tool: `get_full_document`)
  - *AST/Code Plugin:* Parses code into structural relationships. (Registers tools: `get_class_signature`, `get_method`)
  - *Metrics Plugin:* Analyzes code churn or complexity during ingestion. (Registers tool: `get_file_metrics`)

## Three-Type Model

SPEC-008 (ADR-007) introduces three distinct type concepts for all data in the system:

| Type | What it answers | Set by | Example |
|------|----------------|--------|---------|
| **Semantic type** | "What does this data *mean*?" | Ingestion caller | `architecture_docs`, `payment_service` |
| **Media type** | "How is this data *encoded*?" | Plugin / auto-detected | `text/markdown`, `text/x-java` |
| **Record type** | "What did the plugin *produce*?" | Plugin, at write time | `markdown_chunk`, `code_signature` |

Record type replaced the earlier `doctype` field (renamed in SPEC-009).

### Activation Model

Registered plugins exist in one of two operational states:

- **Available:** Plugin is registered, its tools are active and discoverable — but it has no semantic type associations, so it receives no ingestion traffic.
- **Enabled:** Plugin has one or more semantic types configured (`["architecture_docs"]` or `["*"]` for wildcard). It processes ingestion bundles for those types, subject to its media type capabilities.

This model ensures that newly installed plugins don't silently process all content. Activation requires an explicit admin action — associating semantic types with the plugin at registration time or via `update_plugin_semantic_types`.

## Key Architectural Decisions

1. **Client-Side Orchestration:** The MCP Server does not need a heavy internal orchestrating LLM for retrieval. It exposes all plugin tools to the AI client, allowing the client (Claude/Cursor) to orchestrate its own deterministic tool calls.
2. **Reliability Seeding (replaces Librarian):** Rather than a synchronous inline Librarian gatekeeper, reliability is seeded at ingestion time via a three-layer model (caller hint → plugin default → 0.0). High-quality sources rank higher immediately; the platform's scoring system handles refinement over time via feedback signals.
3. **Embedded Relational/Document Storage (MVP):** Phase 1 skips flat files and avoids massive MongoDB deployments by utilizing an embedded database (e.g., SQLite with JSON/Vector extensions, or DuckDB). Modern SQLite provides native JSON document views (`JSONB`), allowing us to store and query arbitrary plugin metadata/documents just like MongoDB, alongside vector embeddings, entirely in process.
