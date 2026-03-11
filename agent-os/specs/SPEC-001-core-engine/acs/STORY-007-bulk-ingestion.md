# STORY-007: Bulk CLI Ingestion Subcommand

## Acceptance Criteria

### AC-001: Offline Command Routing
- Given the `team-mind-mcp` CLI
- When the `ingest` subcommand is invoked
- Then the MCP gateway stdio server is NOT started, preventing background process hangs

### AC-002: Recursive Directory Resolution
- Given the user calls `ingest ./docs` (where `docs` is an existing directory)
- When the `--recursive` flag is present (the default)
- Then all valid nested files inside the directory are properly converted to explicit `file://` URIs and batched into the Ingestion Pipeline

### AC-003: Remote URI Pass-through
- Given the user provides an explicit `http://` or `https://` target
- When the targets are dispatched
- Then remote URIs bypass local directory checks and are forwarded safely into the ingestion bundle
