# STORY-005: Pipeline Semantic Type Routing — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Routes to Processors Registered for Semantic Type | Happy path |
| AC-002 | Filters URIs by Processor Media Types | Happy path |
| AC-003 | Empty semantic_types Routes to Wildcard Processors Only | Edge case |
| AC-004 | Multiple Processors for Same Semantic Type | Happy path |
| AC-005 | No Matching Processors Returns Empty Results | Edge case |
| AC-006 | Wildcard Processor Receives All Bundles | Happy path |

---

### AC-001: Routes to Processors Registered for Semantic Type

**Given** processor A registered for `semantic_types=["architecture_docs"]` and processor B registered for `semantic_types=["meeting_notes"]`
**When** a bundle with `semantic_types=["architecture_docs"]` is ingested
**Then** only processor A receives the bundle

### AC-002: Filters URIs by Processor Media Types

**Given** a processor with `supported_media_types=["text/markdown"]`
**When** a bundle containing `["doc.md", "image.png", "notes.txt"]` is routed to this processor
**Then** only `"doc.md"` is included in the filtered bundle passed to the processor

### AC-003: Empty semantic_types Routes to Wildcard Processors Only

**Given** processor A registered for `semantic_types=["architecture_docs"]`
**And** processor B registered for `semantic_types=["*"]` (wildcard)
**When** a bundle with `semantic_types=[]` is ingested
**Then** only processor B (wildcard) receives the bundle
**And** processor A does not receive the bundle

### AC-004: Multiple Processors for Same Semantic Type

**Given** processors A and B both registered for `semantic_types=["architecture_docs"]`
**When** a bundle with `semantic_types=["architecture_docs"]` is ingested
**Then** both processor A and processor B receive the bundle

### AC-005: No Matching Processors Returns Empty Results

**Given** no processors registered for `"unknown_type"`
**When** a bundle with `semantic_types=["unknown_type"]` is ingested
**Then** the pipeline completes without error
**And** no events are produced

### AC-006: Wildcard Processor Receives All Bundles

**Given** a processor registered for `semantic_types=["*"]`
**When** a bundle with `semantic_types=["architecture_docs"]` is ingested
**Then** the wildcard processor receives the bundle alongside any specifically-registered processors
