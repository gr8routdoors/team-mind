# STORY-004: Two-Phase Pipeline Provides Context — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Bundle Contains Contexts | Happy path |
| AC-002 | Context Generated Per URI | Happy path |
| AC-003 | Multiple Processors Get Independent Contexts | Integration |
| AC-004 | No Existing Docs Means Fresh Context | Edge case |

---

### AC-001: Bundle Contains Contexts

**Given** the pipeline processes a bundle with URIs
**When** the bundle is passed to processors
**Then** `bundle.contexts` is a dict mapping URI strings to `IngestionContext` objects

### AC-002: Context Generated Per URI

**Given** a bundle with 3 URIs, one previously ingested and two new
**When** the pipeline builds contexts
**Then** the previously-ingested URI has `is_update=True` and the new ones have `is_update=False`

### AC-003: Multiple Processors Get Independent Contexts

**Given** two processors registered, one has previously ingested a URI and the other has not
**When** contexts are generated
**Then** each processor's context reflects its own history (not the other processor's)

### AC-004: No Existing Docs Means Fresh Context

**Given** no documents exist in the database
**When** the pipeline ingests any URI
**Then** all contexts have `is_update=False`
