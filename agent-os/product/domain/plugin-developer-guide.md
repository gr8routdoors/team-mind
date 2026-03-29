# Plugin Developer Guide (Product Domain)

> High-level overview of the plugin model. For full implementation details, see the [Plugin Developer Guide](../../context/architecture/plugin-developer-guide.md) in the architecture docs.

## Overview

Team Mind is extended through plugins. A plugin is a Python class that implements one or more of the three plugin interfaces and registers with the platform at startup or runtime.

## Three-Type Model (SPEC-008)

Every piece of data in Team Mind is described by three distinct type concepts:

| Type | What it answers | Example |
|------|----------------|---------|
| **Semantic type** | "What does this data *mean*?" | `architecture_docs`, `travel_profile`, `payment_service` |
| **Media type** | "How is this data *encoded*?" | `text/markdown`, `application/json`, `text/x-java` |
| **Record type** | "What did the plugin *produce*?" | `markdown_chunk`, `code_signature`, `user_interest` |

- **Semantic type** is set by the ingestion caller. It describes the domain meaning of the content.
- **Media type** is detected automatically (or hinted) from file extension or content.
- **Record type** (previously called `doctype`) is declared by the plugin — it's what the plugin writes to storage.

These three concepts are independent: one semantic type can arrive in multiple media types, one semantic type can yield multiple record types, and one media type can carry multiple semantic types.

## Available vs Enabled: Activation Model

A registered plugin can be in one of two operational states:

| State | Has semantic types? | Processes content? |
|-------|--------------------|--------------------|
| **Available** | No | No — idle |
| **Enabled** | Yes (specific or `["*"]`) | Yes, for matching types |

**No semantic types = no processing.** Registering a plugin makes it available (its MCP tools are active, its record types are discoverable), but it does not process ingestion until an admin associates semantic types with it.

`["*"]` is the wildcard: the plugin processes all semantic types it has media type capability for. It must be explicitly configured — it is not the default.

This model ensures that newly installed plugins don't silently process all historical data. Activation is a deliberate, admin-controlled action.

## Plugin Interfaces

Plugins implement one or more of three abstract interfaces:

| Interface | Role | Use when |
|-----------|------|----------|
| **ToolProvider** | Expose MCP tools to AI clients | Your plugin answers queries or performs actions |
| **IngestProcessor** | Process raw URIs during ingestion | Your plugin parses, chunks, or embeds content |
| **IngestObserver** | React to completed ingestion events | Your plugin audits, notifies, or triggers secondary actions |

Plugins can implement any combination. A plugin that only exposes tools (e.g., a retrieval plugin) never participates in ingestion. A plugin that only processes never exposes tools. Most full-featured plugins implement both `ToolProvider` and `IngestProcessor`.

## Registration with Semantic Types

Processors must have semantic types assigned to receive ingestion traffic:

```python
# At compile time (cli.py):
gateway.registry.register(markdown_plugin, semantic_types=["architecture_docs", "meeting_transcripts"])

# At runtime via MCP tool:
register_plugin(
    module_path="my_plugins.java.JavaPlugin",
    semantic_types=["payment_service", "backend_services"]
)

# Wildcard — process all semantic types this plugin can handle:
register_plugin(
    module_path="team_mind_mcp.markdown.MarkdownPlugin",
    semantic_types=["*"]
)
```

Semantic type associations can be updated at runtime without reinstalling the plugin.

## Integration Patterns

| Pattern | Interfaces | Use case |
|---------|------------|----------|
| Observer | `IngestObserver` | Audit, notify, or trigger secondary actions on completed ingestion |
| Processor | `IngestProcessor` | Transform URIs into stored records |
| Tool provider | `ToolProvider` | Expose query/action tools to AI agents |
| Full plugin | `ToolProvider` + `IngestProcessor` | Ingest content AND expose search/query tools |

For implementation details, code examples, storage modes, relevance weighting, and idempotent ingestion patterns, see the full [Plugin Developer Guide](../../context/architecture/plugin-developer-guide.md).
