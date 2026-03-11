# STORY-009: Decouple Plugin Interfaces

## Acceptance Criteria

### AC-001: Tool Providers Subclass
- Given a plugin designed solely for exposing MCP tools (like the Base Ingestion Plugin)
- When inheriting from `ToolProvider`
- Then the plugin can be registered into the registry and map specifically to `get_tools` loops without causing attribute errors for ingestion lists

### AC-002: Ingestion Listeners Subclass
- Given a plugin strictly dedicated to document chunking and persistence
- When inheriting from `IngestListener`
- Then the plugin executes cleanly inside the `process_bundle` broadcast arrays

### AC-003: Dual Capabilities
- Given a complex feature that both exposes capabilities to clients AND listens for broad system events (like `MarkdownPlugin`)
- When the plugin inherits from BOTH the `ToolProvider` and `IngestListener` classes
- Then the registry intelligently places the single plugin into both active loops simultaneously during `register()`
