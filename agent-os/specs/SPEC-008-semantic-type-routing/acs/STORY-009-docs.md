# STORY-009: Update Documentation — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Plugin Developer Guide Updated | Happy path |
| AC-002 | System Overview Updated | Happy path |
| AC-003 | ADR-002 Updated with Semantic Type References | Happy path |

---

### AC-001: Plugin Developer Guide Updated

**Given** the plugin developer guide
**When** inspected after this story is complete
**Then** it documents how to declare `supported_media_types` on an `IngestProcessor`
**And** it documents how to register `semantic_types` for a plugin
**And** it includes an example of a plugin using semantic type routing

### AC-002: System Overview Updated

**Given** the system overview documentation
**When** inspected after this story is complete
**Then** it describes the three-type model (semantic type, media type, record type)
**And** it explains the semantic-type-based routing behavior in the pipeline

### AC-003: ADR-002 Updated with Semantic Type References

**Given** ADR-002 (or the relevant architecture decision record)
**When** inspected after this story is complete
**Then** it references the semantic type and media type additions
**And** it links to ADR-007 for the full design rationale
