# Team Mind

Team Mind is a collaborative AI knowledge engine built on the Model Context Protocol (MCP). It provides a persistent, decentralized "brain" that allows AI agents and development teams to share context, ingest documents, and execute semantic searches.

## Architecture & Data Flow

At its core, Team Mind operates as an extensible MCP Server. The architecture separates the communication layer from the storage and ingestion mechanisms, allowing for flexible plugin-based capabilities.

```mermaid
graph TD
    %% AI Clients
    Claude((Claude Desktop / AI Client))

    %% Core Engine
    subgraph Core Engine [Team Mind MCP Server]
        Gateway[MCP Gateway]
        Registry[Plugin Registry]
        Pipeline[Ingestion Pipeline]
        
        %% Plugins
        subgraph Plugins
            IngestPlugin(Ingestion Plugin)
            RetrievePlugin(Retrieval Plugin)
            MarkdownPlugin(Markdown Plugin)
        end
        
        %% Storage
        DB[(SQLite + sqlite-vec)]
    end

    %% Connections
    Claude <-->|stdio / MCP Protocol| Gateway
    Gateway --> Registry
    Registry --> IngestPlugin
    Registry --> RetrievePlugin
    Registry --> MarkdownPlugin
    
    IngestPlugin -->|Triggers| Pipeline
    Pipeline -->|Broadcasts IngestionBundle| MarkdownPlugin
    
    MarkdownPlugin -->|Stores chunks & vectors| DB
    RetrievePlugin -->|Fetches full docs| DB
```

### Core Components

- **MCP Gateway**: Handles the standard MCP protocol lifecycle and routing between the connected AI client (e.g., Claude) and the internal registry.
- **Plugin Registry**: Manages registered tools (`ToolProvider`), ingestion processors (`IngestProcessor`), and ingestion observers (`IngestObserver`).
- **Ingestion Pipeline**: A two-phase event-driven loop that resolves URIs, broadcasts bundles to processors (Phase 1), then notifies observers with structured events (Phase 2).
- **Storage Adapter**: An embedded SQLite database utilizing the `sqlite-vec` extension for high-performance semantic vector search and `json1` for metadata.

## Usage

Team Mind is built with `uv` and exposes a unified CLI entry point.

### Starting the Server

To start the MCP Server and connect it to a client:

```bash
# Starts the stdio server (defaults to ~/.team-mind/database.sqlite)
uv run team-mind-mcp start

# Override the database location
uv run team-mind-mcp --db-path ./my-project-brain.sqlite start
```

### Offline Bulk Ingestion

You can seamlessly pre-load the database with context from local files, entire directories, or remote URIs using the `ingest` subcommand without starting the server:

```bash
# Ingest diverse targets simultaneously
uv run team-mind-mcp ingest ./docs/ https://example.com/api.md ./notes.txt
```

### Live Agent Ingestion

When the server is running, connected AI agents have access to the `ingest_documents` tool. This allows them to dynamically pull in web links or local file paths during a conversation, expanding their context dynamically!

## Building Plugins

Want to extend Team Mind with a new plugin? See the **[Plugin Developer Guide](agent-os/context/architecture/plugin-developer-guide.md)** — it covers what you own (doctypes, metadata schemas, storage modes, tools), what the platform provides, and includes runnable code examples.

## Development Status

- **Phase 1: Core Engine** - **COMPLETE**
  - SPEC-001: MCP Gateway, SQLite storage, ingestion pipeline, Markdown plugin, CLI
  - SPEC-002: Doctype system, plugin-scoped namespacing, scoped queries, discovery tool
  - SPEC-003: IngestProcessor/IngestObserver split, two-phase pipeline, IngestionEvent
- **Phase 2: Intelligence & Weighting** - **IN PROGRESS**
  - SPEC-004: Usage-based ranking (cumulative average), information decay, tombstoning, doc updates — **COMPLETE**
  - SPEC-005: Idempotent ingestion (content hashing, plugin versioning, IngestionContext) — **COMPLETE**
  - SPEC-006: Plugin lifecycle management (dynamic registration, filtered subscriptions, persistence) — *In design*

---

> **Note:** This project uses [Lit SDLC](https://github.com/buildermethods/lit-sdlc) for structured AI-assisted development. See `AGENTS.md` for the internal workflow.
