# STORY-007: MCP Tool and CLI Semantic Type Parameter — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | MCP Tool Accepts semantic_types Parameter | Happy path |
| AC-002 | CLI Accepts Repeatable --semantic-type Flag | Happy path |
| AC-003 | Parameter Propagates to Pipeline | Integration |
| AC-004 | CLI Config File Provides Default Semantic Types | Happy path |
| AC-005 | Missing Config File Uses Built-In Defaults | Edge case |

---

### AC-001: MCP Tool Accepts semantic_types Parameter

**Given** the `ingest_documents` MCP tool
**When** called with `semantic_types=["architecture_docs", "meeting_notes"]` alongside URIs
**Then** the tool accepts the parameter without error
**And** the resulting bundle has `semantic_types=["architecture_docs", "meeting_notes"]`

### AC-002: CLI Accepts Repeatable --semantic-type Flag

**Given** the ingestion CLI command
**When** invoked with `--semantic-type architecture_docs --semantic-type meeting_notes`
**Then** the flags are parsed and accepted without error
**And** the resulting bundle has `semantic_types=["architecture_docs", "meeting_notes"]`

### AC-003: Parameter Propagates to Pipeline

**Given** an MCP tool call or CLI invocation with `semantic_types=["meeting_notes"]`
**When** the ingestion pipeline is invoked
**Then** the resulting `IngestionBundle` has `semantic_types=["meeting_notes"]`

### AC-004: CLI Config File Provides Default Semantic Types

**Given** a `~/.team-mind.toml` file containing:
```toml
[markdown_plugin]
semantic_types = ["*"]
```
**When** the CLI start or ingest command runs
**Then** `markdown_plugin` is registered in the registry with `semantic_types=["*"]`
**And** no `--semantic-type` flag is required for markdown ingestion to function

### AC-005: Missing Config File Uses Built-In Defaults

**Given** no `~/.team-mind.toml` file exists
**When** the CLI start or ingest command runs
**Then** `markdown_plugin` is registered with `semantic_types=["*"]` by default
**And** markdown file ingestion functions out of the box without additional configuration
