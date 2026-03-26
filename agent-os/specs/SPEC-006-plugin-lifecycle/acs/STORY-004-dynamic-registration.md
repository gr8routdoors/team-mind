# STORY-004: Dynamic Registration MCP Tools — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Tools Registered | Happy path |
| AC-002 | Register Plugin Successfully | Happy path |
| AC-003 | Registered Plugin Tools Visible | Integration |
| AC-004 | Unregister Plugin Removes Tools | Happy path |
| AC-005 | List Plugins Returns Roster | Happy path |
| AC-006 | Invalid Module Path Errors | Error |
| AC-007 | Duplicate Registration Errors | Error |

---

### AC-001: Tools Registered

**Given** the LifecyclePlugin is registered
**When** MCP tools are listed
**Then** `register_plugin`, `unregister_plugin`, and `list_plugins` appear

### AC-002: Register Plugin Successfully

**Given** a valid module_path pointing to a plugin class
**When** `register_plugin(module_path)` is called
**Then** the plugin is instantiated, registered, and persisted
**And** the response includes the plugin name and tools registered

### AC-003: Registered Plugin Tools Visible

**Given** a plugin registered via `register_plugin`
**When** MCP tools are listed
**Then** the dynamically registered plugin's tools appear alongside core plugins

### AC-004: Unregister Plugin Removes Tools

**Given** a dynamically registered plugin
**When** `unregister_plugin(plugin_name)` is called
**Then** the plugin's tools are removed from the MCP catalog
**And** the plugin is marked as disabled in the persistence table

### AC-005: List Plugins Returns Roster

**Given** core plugins and dynamically registered plugins
**When** `list_plugins()` is called
**Then** all plugins are returned with their name, type, enabled status, and tools

### AC-006: Invalid Module Path Errors

**Given** a module_path that cannot be imported
**When** `register_plugin(module_path)` is called
**Then** a clear error is returned indicating the module could not be loaded

### AC-007: Duplicate Registration Errors

**Given** a plugin that is already registered
**When** `register_plugin` is called with the same name
**Then** an error is returned indicating the plugin is already registered
