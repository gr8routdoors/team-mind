# STORY-007: MCP Tool and CLI Semantic Type Parameter — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | MCP Tool Accepts semantic_type Parameter | Happy path |
| AC-002 | CLI Accepts --semantic-type Flag | Happy path |
| AC-003 | Parameter Propagates to Pipeline | Integration |

---

### AC-001: MCP Tool Accepts semantic_type Parameter

**Given** the `ingest_documents` MCP tool
**When** called with `semantic_type="architecture_docs"` alongside URIs
**Then** the tool accepts the parameter without error

### AC-002: CLI Accepts --semantic-type Flag

**Given** the ingestion CLI command
**When** invoked with `--semantic-type architecture_docs`
**Then** the flag is parsed and accepted without error

### AC-003: Parameter Propagates to Pipeline

**Given** an MCP tool call or CLI invocation with `semantic_type="meeting_notes"`
**When** the ingestion pipeline is invoked
**Then** the resulting `IngestionBundle` has `semantic_type="meeting_notes"`
