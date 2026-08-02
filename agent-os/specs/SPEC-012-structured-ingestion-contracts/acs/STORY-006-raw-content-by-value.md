# STORY-006: Raw content by-value ingestion — Acceptance Criteria

> A caller may supply raw bytes inline instead of a URL; decoding stays in the plugin.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Inline content is processed without a fetch | Happy path |
| AC-002 | Content without media_type is rejected | Validation |
| AC-003 | Mixed batch of URI and inline items | Edge case |
| AC-004 | uri remains the identity key for inline content | Integration |
| AC-005 | media_type filtering still applies to inline content | Business rule |

---

## Acceptance Criteria

### AC-001: Inline content is processed without a fetch

**Given** an `ingest_documents` item `{uri, content, media_type: "text/markdown"}` whose `uri` is not fetchable
**When** ingestion runs
**Then** the provided `content` is handed to the matching processor with no fetch attempted
**And** a document is written from that content.

---

### AC-002: Content without media_type is rejected

**Given** an `ingest_documents` item with `content` present but no `media_type`
**When** ingestion runs
**Then** the item is rejected with an error requiring `media_type`
**And** nothing is written for that item.

---

### AC-003: Mixed batch of URI and inline items

**Given** a batch with one URI-only item and one inline `{uri, content, media_type}` item
**When** ingestion runs
**Then** the URI-only item is fetched as today
**And** the inline item uses the provided content
**And** both are processed.

---

### AC-004: uri remains the identity key for inline content

**Given** an inline-content item ingested under `uri = "mem://note/42"`
**When** the same `uri` is ingested again with different `content`
**Then** idempotency keys on `uri` (the existing document is updated, not duplicated).

---

### AC-005: media_type filtering still applies to inline content

**Given** inline content with `media_type = "text/markdown"`
**When** ingestion routes it
**Then** only processors whose `supported_media_types` include `text/markdown` receive it
**And** a processor restricted to other media types does not.
