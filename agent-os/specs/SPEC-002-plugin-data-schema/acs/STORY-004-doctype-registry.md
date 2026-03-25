# STORY-004: Doctype Registry & Catalog — Acceptance Criteria

> ACs for extending PluginRegistry with doctype catalog and discovery methods.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Catalog Collects Doctypes on Registration | Happy path |
| AC-002 | Get All Doctypes | Happy path |
| AC-003 | Get Doctypes for Plugin | Happy path |
| AC-004 | Get Plugins for Doctype | Happy path |
| AC-005 | Plugin with No Doctypes | Edge case |
| AC-006 | Doctype Specs Include Plugin Name | Integration |

---

## Acceptance Criteria

### AC-001: Catalog Collects Doctypes on Registration

**Given** a plugin that declares two doctypes
**When** the plugin is registered with the `PluginRegistry`
**Then** both doctypes appear in the registry's internal catalog
**And** each doctype's `plugin` field is set to the registering plugin's name

---

### AC-002: Get All Doctypes

**Given** three plugins are registered, declaring a total of five doctypes
**When** `get_doctype_catalog()` is called
**Then** all five `DoctypeSpec` instances are returned

---

### AC-003: Get Doctypes for Plugin

**Given** `"plugin_a"` declares `["type_x", "type_y"]` and `"plugin_b"` declares `["type_z"]`
**When** `get_doctypes_for_plugin("plugin_a")` is called
**Then** exactly `["type_x", "type_y"]` are returned

---

### AC-004: Get Plugins for Doctype

**Given** `"plugin_a"` and `"plugin_b"` both declare a doctype named `"common_type"`
**When** `get_plugins_for_doctype("common_type")` is called
**Then** both `"plugin_a"` and `"plugin_b"` are returned

---

### AC-005: Plugin with No Doctypes

**Given** a plugin that does not override the `doctypes` property
**When** it is registered with the `PluginRegistry`
**Then** the catalog is not modified
**And** no error is raised

---

### AC-006: Doctype Specs Include Plugin Name

**Given** a plugin named `"my_plugin"` declares a doctype `"my_type"`
**When** the doctype is retrieved from the catalog
**Then** the `DoctypeSpec.plugin` field equals `"my_plugin"`
