# STORY-002: Canonical validated write path (write_record toolkit) — Acceptance Criteria

> The single write method validates, embeds, seeds reliability, and writes idempotently.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Valid payload is written with vector and metadata 1:1 | Happy path |
| AC-002 | Invalid payload writes nothing | Validation |
| AC-003 | No embed_source ⇒ metadata-only, no vector | Edge case |
| AC-004 | reliability_hint wins the ladder | Business rule |
| AC-005 | default_reliability used when no hint | Business rule |
| AC-006 | Platform default 0.0 when neither given | Business rule |
| AC-007 | First write inserts | Integration |
| AC-008 | Re-write with changed payload updates in place | Integration |
| AC-009 | Payload key `uri` stays namespaced under metadata | Edge case |

---

## Acceptance Criteria

### AC-001: Valid payload is written with vector and metadata 1:1

**Given** a record type with a schema and `embed_source = ["summary"]`
**When** `write_record` is called with a payload that satisfies the schema
**Then** a document is stored whose `metadata` equals the payload exactly (1:1)
**And** a vector embedding is computed from the `summary` field
**And** a weight row is created
**And** the new `doc_id` is returned.

---

### AC-002: Invalid payload writes nothing

**Given** a record type whose schema requires field `name`
**When** `write_record` is called with a payload missing `name`
**Then** the call raises/returns a validation error listing `name`
**And** no row is written to `documents`, `vec_documents`, or `doc_weights`.

---

### AC-003: No embed_source ⇒ metadata-only, no vector

**Given** a record type with a valid schema and `embed_source = None`
**When** `write_record` writes a valid payload
**Then** a `documents` row and `metadata` are stored
**And** no `vec_documents` row is created
**And** the record is still retrievable via metadata search (`json_extract`).

---

### AC-004: reliability_hint wins the ladder

**Given** a record type with `default_reliability = 0.5`
**When** `write_record` writes with `reliability_hint = 0.8`
**Then** the record's `usage_score` is seeded to `0.8`.

---

### AC-005: default_reliability used when no hint

**Given** a record type with `default_reliability = 0.5`
**When** `write_record` writes with `reliability_hint = None`
**Then** the record's `usage_score` is seeded to `0.5`.

---

### AC-006: Platform default 0.0 when neither given

**Given** a record type with `default_reliability = None`
**When** `write_record` writes with `reliability_hint = None`
**Then** the record's `usage_score` is seeded to `0.0`.

---

### AC-007: First write inserts

**Given** no existing document for `(uri, plugin, record_type)`
**When** `write_record` writes a valid payload
**Then** a new document is inserted with a fresh `doc_id`.

---

### AC-008: Re-write with changed payload updates in place

**Given** an existing document for the same `uri` and `record_type` with content hash H1
**When** `write_record` writes a valid payload with a different content hash H2
**Then** the existing document is updated in place (metadata and vector replaced)
**And** its `doc_id` and weight row are preserved (not duplicated).

---

### AC-009: Payload key `uri` stays namespaced under metadata

**Given** a schema that permits a payload property literally named `uri`
**When** `write_record` writes a payload containing `uri = "x"`
**Then** the value is stored at `metadata.uri`
**And** it does not overwrite or collide with the envelope `uri` column.
