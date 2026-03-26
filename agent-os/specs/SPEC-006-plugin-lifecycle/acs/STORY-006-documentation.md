# STORY-006: Update Documentation — Acceptance Criteria

> ACs for ensuring all documentation reflects the plugin lifecycle management system, including the full array of plugin integration options.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Plugin Developer Guide — Registration Section | Happy path |
| AC-002 | Plugin Developer Guide — EventFilter Section | Happy path |
| AC-003 | Plugin Developer Guide — Integration Options Summary | Happy path |
| AC-004 | System Overview Updated | Happy path |
| AC-005 | ADR-002 Updated | Happy path |
| AC-006 | SPEC-003 Design Doc Updated | Happy path |
| AC-007 | Roadmap Updated | Happy path |
| AC-008 | README Updated | Happy path |
| AC-009 | No Stale References | Validation |

---

### AC-001: Plugin Developer Guide — Registration Section

**Given** the plugin developer guide "Registering Your Plugin" section
**When** it is read
**Then** it documents both approaches:
- Compile-time registration (hardcoded in `cli.py` — core plugins)
- Runtime registration via `register_plugin` MCP tool (dynamic plugins)
**And** explains that dynamic plugins persist across restarts

---

### AC-002: Plugin Developer Guide — EventFilter Section

**Given** the plugin developer guide IngestObserver section
**When** it is read
**Then** it documents the `event_filter` property with examples:
- No filter (fire hose — receives all events)
- Plugin filter only
- Doctype filter only
- Combined filter
**And** explains that the default is fire hose (backward compatible)

---

### AC-003: Plugin Developer Guide — Integration Options Summary

**Given** the plugin developer guide
**When** it is read
**Then** it includes a clear summary of all plugin integration options:
- Three interfaces (ToolProvider, IngestProcessor, IngestObserver)
- Two registration methods (compile-time, runtime)
- Two observation modes (fire hose, topic-based)
- Two storage modes (pointer, embedded)
- Idempotent ingestion (content hashing, plugin versioning, IngestionContext)
- Relevance weighting (decay policy, feedback signals)
**And** a developer can understand the full capability matrix from this one document

---

### AC-004: System Overview Updated

**Given** the system overview
**When** it is read
**Then** it mentions that plugins can be registered/unregistered at runtime
**And** distinguishes between core (bundled) plugins and dynamically loaded plugins

---

### AC-005: ADR-002 Updated

**Given** ADR-002 (Plugin Architecture)
**When** it is read
**Then** the PluginRegistry section mentions `unregister()`
**And** the Plugin Inventory includes LifecyclePlugin
**And** Key Files includes the lifecycle module and registered_plugins table

---

### AC-006: SPEC-003 Design Doc Updated

**Given** the SPEC-003 design doc (Ingestion Interface Split)
**When** it is read
**Then** the IngestObserver interface shows the optional `event_filter` property
**And** the Pipeline Flow section mentions filtered Phase 2 broadcast
**And** references SPEC-006 for details

---

### AC-007: Roadmap Updated

**Given** the product roadmap
**When** it is read
**Then** SPEC-006 appears in Phase 2 (or Phase 3 as appropriate)

---

### AC-008: README Updated

**Given** the README
**When** it is read
**Then** the Development Status section includes SPEC-006
**And** the architecture description notes that plugins can be added at runtime

---

### AC-009: No Stale References

**Given** the full documentation set
**When** searched for references to plugin registration
**Then** no document implies that plugins can only be registered at compile-time / startup
