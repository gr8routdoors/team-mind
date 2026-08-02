# STORY-005: MarkdownPlugin compliance — Acceptance Criteria

> The existing plugin is brought under mandatory validation without losing SPEC-011 behavior.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Markdown ingestion still yields parent + segments | Happy path / regression |
| AC-002 | Chunk metadata is payload-only (no envelope fields) | Business rule |
| AC-003 | Markdown writes go through validation | Integration |
| AC-004 | Markdown record types declare non-empty schemas | Validation |

---

## Acceptance Criteria

### AC-001: Markdown ingestion still yields parent + segments

**Given** a markdown file ingested via the raw path
**When** MarkdownPlugin processes it
**Then** one `markdown_source` parent document is written
**And** one `markdown_chunk` segment is written per paragraph, linked by `parent_id` (SPEC-011 parity preserved).

---

### AC-002: Chunk metadata is payload-only (no envelope fields)

**Given** the migrated `markdown_chunk` record type
**When** a chunk is written
**Then** its `metadata` contains only payload fields (e.g. the chunk text)
**And** it does not contain envelope fields such as `plugin`.

---

### AC-003: Markdown writes go through validation

**Given** MarkdownPlugin writes via `write_record`
**When** a chunk payload would violate the `markdown_chunk` schema
**Then** the write is rejected by the same validation path as any other record
**And** no unvalidated write path exists for the plugin.

---

### AC-004: Markdown record types declare non-empty schemas

**Given** MarkdownPlugin registers `markdown_source` and `markdown_chunk`
**When** the plugin is registered
**Then** registration succeeds because both declare non-empty JSON Schemas
**And** it would fail STORY-001's guard if either schema were missing.
