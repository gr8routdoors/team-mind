# STORY-002: Rename IngestListener to IngestProcessor — Acceptance Criteria

> ACs for renaming the interface and updating process_bundle() to return events.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | IngestProcessor ABC Exists | Happy path |
| AC-002 | IngestListener No Longer Importable | Validation |
| AC-003 | process_bundle Returns Events | Happy path |
| AC-004 | MarkdownPlugin Returns Events | Integration |
| AC-005 | Registry Tracks Processors | Happy path |
| AC-006 | Existing Tests Pass | Regression |

---

### AC-001: IngestProcessor ABC Exists

**Given** the `server.py` module
**When** `IngestProcessor` is imported
**Then** it is an abstract base class with `name` and `process_bundle` methods

---

### AC-002: IngestListener No Longer Importable

**Given** the `server.py` module
**When** an attempt is made to import `IngestListener`
**Then** an `ImportError` is raised

---

### AC-003: process_bundle Returns Events

**Given** a plugin implementing `IngestProcessor`
**When** `process_bundle(bundle)` is called
**Then** the return type is `list[IngestionEvent]`

---

### AC-004: MarkdownPlugin Returns Events

**Given** the `MarkdownPlugin` processes a bundle with 2 markdown files
**When** `process_bundle` completes
**Then** it returns `IngestionEvent` objects with `plugin="markdown_plugin"`, `doctype="markdown_chunk"`, and the correct URIs and doc IDs

---

### AC-005: Registry Tracks Processors

**Given** a plugin implementing `IngestProcessor` is registered
**When** `get_ingest_processors()` is called on the registry
**Then** the plugin appears in the returned list

---

### AC-006: Existing Tests Pass

**Given** the rename from IngestListener to IngestProcessor
**When** the full SPEC-001 and SPEC-002 test suites are executed
**Then** all tests pass
