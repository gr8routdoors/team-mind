# System Architecture Overview

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
- For non-MCP human interfaces (like MS Teams bots), a lightweight "Router API" (potentially backed by a fast LLM) will act as an intermediary client to query the MCP server on the human's behalf.

### 2. The Ingestion Pipeline (Bundle Broadcast & Validation)
Ingestion is treated as a systemic, multi-stage event rather than a simple database write.
- **Resource Bundles & URIs:** The system abstracts incoming data as "Resources" identified by URIs (e.g., `file://`, `https://`, `confluence://`), not just local files. A "Bundle" contains one or more of these Resources.
- **Dual-Mode Storage (Pointers + Embedded Content):** Each document row supports two retrieval modes. **Pointer mode:** the row stores a URI reference; when an AI requests the full document, a Resolver fetches it live from the source (`file://`, `https://`, etc.). This prevents data duplication at enterprise scale. **Embedded mode:** the full content is stored directly in the row's `metadata` JSON under `local_payload`; retrieval is instantaneous with no external dependency. Plugins choose per-document which mode to use at ingestion time — both are first-class, and a single knowledge base freely mixes them. Embedded mode is essential for ephemeral content (uploaded text, chat transcripts, API responses) that has no stable external URI.
- **Stage A: Broadcast Processing:** When a Bundle is ingested, the Core Engine broadcasts it to all registered plugins. Each plugin parses the bundle and extracts its domain-specific value (e.g., parsing code ASTs, vectorizing text, extracting facts). These extracted records are held in a `PENDING` state.
- **Stage B: The Librarian (Validation Post-Processor):** Because validation requires understanding the semantic *meaning* of the parsed data, the Librarian operates *after* the plugins have done the heavy lifting. The Librarian evaluates the new `PENDING` facts and vectors against the current "Golden" state of the database. If a new fact contradicts established architecture, it halts the commit and flags the bundle for human review. If it passes, the records are committed to the primary active index.

### 3. The Plugin Architecture (Renderers/Processors)
Plugins are specialized engines that handle both the ingestion parsing of resources and the registration of retrieval tools to the MCP Server.
- **Example Plugins:**
  - *Markdown/Text Plugin:* Handles semantic vectorization and keyword search. (Registers tool: `search_knowledge_base`)
  - *Document Retrieval Plugin:* Dedicated plugin for fetching raw content. Can retrieve from local DB storage or live URIs. (Registers tool: `get_full_document`)
  - *AST/Code Plugin:* Parses code into structural relationships. (Registers tools: `get_class_signature`, `get_method`)
  - *Metrics Plugin:* Analyzes code churn or complexity during ingestion. (Registers tool: `get_file_metrics`)

## Key Architectural Decisions

1. **Client-Side Orchestration:** The MCP Server does not need a heavy internal orchestrating LLM for retrieval. It exposes all plugin tools to the AI client, allowing the client (Claude/Cursor) to orchestrate its own deterministic tool calls.
2. **Post-Processing Validation:** The Librarian acts as a gatekeeper *after* initial parsing but *before* final commit. This solves the "Catch-22" of needing semantic understanding to validate a file.
3. **Embedded Relational/Document Storage (MVP):** Phase 1 skips flat files and avoids massive MongoDB deployments by utilizing an embedded database (e.g., SQLite with JSON/Vector extensions, or DuckDB). Modern SQLite provides native JSON document views (`JSONB`), allowing us to store and query arbitrary plugin metadata/documents just like MongoDB, alongside vector embeddings, entirely in process.
