# STORY-001: MCP Gateway & Plugin Registry — Acceptance Criteria

> ACs for establishing the base Python MCP server and the generic interface for plugins to register tools.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Server Initialized | Happy path |
| AC-002 | Plugin Registration | Integration |
| AC-003 | Rejects Unregistered Tools | Error condition |

---

## Acceptance Criteria

### AC-001: Server Initialized

**Given** the core server is configured with default settings
**When** the server process is started
**Then** it successfully binds to an stdio or SSE transport
**And** it responds to MCP `initialize` handshakes

---

### AC-002: Plugin Registration

**Given** a valid mock plugin that exposes a `test_tool`
**When** the plugin is added to the `PluginRegistry`
**And** the MCP client requests the list of available tools
**Then** the `test_tool` is returned in the tools list with its description and schema

---

### AC-003: Rejects Unregistered Tools

**Given** the MCP server is running with only `test_tool` registered
**When** an AI client attempts to call `unknown_tool`
**Then** the server returns a standard MCP Error response indicating the tool does not exist
**And** the server does not crash
