# STORY-008: Live MCP Ingestion Tool

## Acceptance Criteria

### AC-001: Plugin Instantiation
- Given the `IngestionPlugin` is registered with the Core Engine
- When queried for available tools
- Then an `ingest_documents` tool is surfaced with the required JSON schema parameters

### AC-002: Successful Execution Broadcast
- Given a valid URI target is provided to the tool parameters
- When the `ingest_documents` tool is called
- Then the `IngestionPipeline` dispatches the URIs to all listeners and returns a successful response message

### AC-003: Graceful Error Handling
- Given a malformed URI or non-existent file path
- When the tool is asked to ingest the dead endpoints
- Then the underlying errors (like `FileNotFoundError`) are gracefully caught
- And the MCP Tool response returns standard TextContent alerting the client of the specific failure, instead of silently crashing the stdio transport
