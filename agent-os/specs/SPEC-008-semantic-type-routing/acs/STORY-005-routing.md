# STORY-005: Pipeline Semantic Type Routing — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Routes to Processors Registered for Semantic Type | Happy path |
| AC-002 | Filters URIs by Processor Media Types | Happy path |
| AC-003 | Broadcast Fallback When No Semantic Type | Edge case |
| AC-004 | Multiple Processors for Same Semantic Type | Happy path |
| AC-005 | No Matching Processors Returns Empty Results | Edge case |

---

### AC-001: Routes to Processors Registered for Semantic Type

**Given** processor A registered for `semantic_types=["architecture_docs"]` and processor B registered for `semantic_types=["meeting_notes"]`
**When** a bundle with `semantic_type="architecture_docs"` is ingested
**Then** only processor A receives the bundle

### AC-002: Filters URIs by Processor Media Types

**Given** a processor with `supported_media_types=["text/markdown"]`
**When** a bundle containing `["doc.md", "image.png", "notes.txt"]` is routed to this processor
**Then** only `"doc.md"` is included in the filtered bundle passed to the processor

### AC-003: Broadcast Fallback When No Semantic Type

**Given** processors A and B registered with various semantic types
**When** a bundle with `semantic_type=None` is ingested
**Then** all processors receive the bundle (broadcast behavior, backward compatible)

### AC-004: Multiple Processors for Same Semantic Type

**Given** processors A and B both registered for `semantic_types=["architecture_docs"]`
**When** a bundle with `semantic_type="architecture_docs"` is ingested
**Then** both processor A and processor B receive the bundle

### AC-005: No Matching Processors Returns Empty Results

**Given** no processors registered for `semantic_types=["unknown_type"]`
**When** a bundle with `semantic_type="unknown_type"` is ingested
**Then** the pipeline completes without error
**And** no events are produced
