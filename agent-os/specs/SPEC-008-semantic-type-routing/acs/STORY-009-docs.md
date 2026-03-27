# STORY-009: Update Documentation — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Plugin Developer Guide — Three-Type Model | Happy path |
| AC-002 | Plugin Developer Guide — Registration and Activation | Happy path |
| AC-003 | Plugin Developer Guide — Integration Options Summary | Happy path |
| AC-004 | System Overview Updated | Happy path |
| AC-005 | ADR-002 Updated | Happy path |
| AC-006 | Roadmap Updated | Happy path |
| AC-007 | README Updated | Happy path |
| AC-008 | No Stale Type References | Validation |

---

### AC-001: Plugin Developer Guide — Three-Type Model

**Given** the plugin developer guide
**When** it is read
**Then** it documents the three-type model: semantic type (input meaning), media type (encoding), record type (output)
**And** it explains that semantic type is the routing key, media type is the parsing hint, and record type is what plugins produce
**And** it includes examples showing how one semantic type can arrive in different media types

---

### AC-002: Plugin Developer Guide — Registration and Activation

**Given** the plugin developer guide
**When** it is read
**Then** it documents the available-vs-enabled model (no semantic types = no processing)
**And** it explains how to declare `supported_media_types` on IngestProcessor
**And** it explains how to associate semantic types at registration time (both compile-time and runtime)
**And** it documents that `*` is explicit opt-in for wildcard processing
**And** it documents that semantic types can be updated without plugin reinstall

---

### AC-003: Plugin Developer Guide — Integration Options Summary

**Given** the plugin developer guide Integration Options Summary table
**When** it is read
**Then** it includes the semantic type routing and media type capability rows
**And** it reflects the available-vs-enabled activation model

---

### AC-004: System Overview Updated

**Given** the system overview
**When** it is read
**Then** it describes the three-type model
**And** it explains semantic-type-based routing in the pipeline section
**And** it mentions the available-vs-enabled plugin activation model

---

### AC-005: ADR-002 Updated

**Given** ADR-002 (Plugin Architecture)
**When** it is read
**Then** the PluginRegistry section references semantic type associations on registration
**And** the broadcast ingestion section notes the transition from broadcast to semantic routing
**And** it links to ADR-007 for the full routing design

---

### AC-006: Roadmap Updated

**Given** the roadmap
**When** it is read
**Then** SPEC-008 status is reflected accurately

---

### AC-007: README Updated

**Given** the README
**When** it is read
**Then** the Development Status section includes SPEC-008

---

### AC-008: No Stale Type References

**Given** the full documentation set (plugin developer guide, system overview, ADR-002, README)
**When** searched for descriptions of the ingestion routing model
**Then** no document describes pure broadcast-and-self-filter as the current behavior without noting the transition to semantic type routing
