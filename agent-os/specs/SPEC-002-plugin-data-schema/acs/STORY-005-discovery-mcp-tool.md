# STORY-005: Doctype Discovery MCP Tool — Acceptance Criteria

> ACs for the DoctypeDiscoveryPlugin that exposes `list_doctypes` as an MCP tool.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Tool Registered | Happy path |
| AC-002 | Returns All Doctypes | Happy path |
| AC-003 | Filter by Plugin | Happy path |
| AC-004 | Response Structure | Validation |
| AC-005 | No Doctypes Registered | Edge case |

---

## Acceptance Criteria

### AC-001: Tool Registered

**Given** the `DoctypeDiscoveryPlugin` is registered with the `PluginRegistry`
**When** an MCP client requests the list of available tools
**Then** `list_doctypes` appears in the tools list
**And** it includes a description and input schema

---

### AC-002: Returns All Doctypes

**Given** multiple plugins have been registered with various doctypes
**When** `list_doctypes` is called with no arguments
**Then** the response includes every doctype from every registered plugin

---

### AC-003: Filter by Plugin

**Given** plugins `"alpha"` and `"beta"` are registered with doctypes
**When** `list_doctypes` is called with `plugin="alpha"`
**Then** only doctypes from `"alpha"` are returned
**And** doctypes from `"beta"` are excluded

---

### AC-004: Response Structure

**Given** a plugin declares a doctype with name, description, and schema
**When** `list_doctypes` is called
**Then** each entry in the response includes `plugin`, `name`, `description`, and `schema` fields
**And** the response is valid JSON

---

### AC-005: No Doctypes Registered

**Given** no plugins have declared any doctypes
**When** `list_doctypes` is called
**Then** an empty list is returned
**And** no error is raised
