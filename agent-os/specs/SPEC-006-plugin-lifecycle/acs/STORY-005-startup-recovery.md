# STORY-005: Plugin Loader & Startup Recovery — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Enabled Plugins Loaded on Startup | Happy path |
| AC-002 | Disabled Plugins Not Loaded | Happy path |
| AC-003 | Failed Load Logged Not Fatal | Error |
| AC-004 | Event Filters Restored | Integration |
| AC-005 | Core Plugins Unaffected | Regression |

---

### AC-001: Enabled Plugins Loaded on Startup

**Given** the `registered_plugins` table has 2 enabled plugin records
**When** the server starts
**Then** both plugins are instantiated and registered with the PluginRegistry

### AC-002: Disabled Plugins Not Loaded

**Given** a plugin record with `enabled=0`
**When** the server starts
**Then** that plugin is not instantiated or registered

### AC-003: Failed Load Logged Not Fatal

**Given** a plugin record with an invalid `module_path`
**When** the server starts
**Then** a warning is logged about the failed load
**And** the server continues to start normally with remaining plugins

### AC-004: Event Filters Restored

**Given** a plugin was registered with an event_filter
**When** the server restarts and loads the plugin from the table
**Then** the observer's event_filter matches what was originally configured

### AC-005: Core Plugins Unaffected

**Given** core plugins are hardcoded in cli.py
**When** the startup recovery loads dynamic plugins
**Then** core plugins are still registered and functional
