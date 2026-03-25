# STORY-005: Update Documentation — Acceptance Criteria

> ACs for ensuring all documentation reflects the three-interface model.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Plugin Developer Guide Updated | Happy path |
| AC-002 | System Overview Updated | Happy path |
| AC-003 | No References to IngestListener | Validation |

---

### AC-001: Plugin Developer Guide Updated

**Given** the plugin developer guide at `agent-os/context/architecture/plugin-developer-guide.md`
**When** it is read
**Then** it documents all three interfaces: `ToolProvider`, `IngestProcessor`, `IngestObserver`
**And** it includes code examples for each
**And** it explains when to use each interface

---

### AC-002: System Overview Updated

**Given** the system overview at `agent-os/context/architecture/system-overview.md`
**When** it is read
**Then** it references the two-phase ingestion pipeline
**And** it distinguishes between processors and observers

---

### AC-003: No References to IngestListener

**Given** the full codebase including docs, specs, and source
**When** searched for the string "IngestListener"
**Then** no occurrences are found (fully renamed)
