# STORY-003: submit_structured endpoint and ingest_structured pipeline — Acceptance Criteria

> Batch push: strict per record, best-effort across the batch, with events for observers.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Batch of valid records is written | Happy path |
| AC-002 | One invalid record does not sink the batch | Business rule |
| AC-003 | Observers fire on submitted record_type | Integration |
| AC-004 | Non-submittable record_type is rejected | Validation |
| AC-005 | Single-record list behaves as one write | Edge case |
| AC-006 | Re-submitting same uri updates, not duplicates | Integration |
| AC-007 | Empty batch is rejected | Edge case |

---

## Acceptance Criteria

### AC-001: Batch of valid records is written

**Given** two records of submittable types, each valid against its schema
**When** `submit_structured` is called with both in `records`
**Then** both are written via `write_record`
**And** the response contains two per-record results, each with a `doc_id`.

---

### AC-002: One invalid record does not sink the batch

**Given** a batch of three records where the second fails schema validation
**When** `submit_structured` is called
**Then** records 1 and 3 are written
**And** the response reports record 2's validation errors
**And** records 1 and 3 are not rolled back (strict per record, best-effort across the batch).

---

### AC-003: Observers fire on submitted record_type

**Given** an observer whose `EventFilter.record_types = ["service_profile"]`
**When** a valid `service_profile` record is submitted
**Then** the observer's `on_ingest_complete` is called with an `IngestionEvent` for `service_profile`
**And** an observer filtered to a different record type is not called.

---

### AC-004: Non-submittable record_type is rejected

**Given** a record whose `record_type` has no submittable declarer
**When** it is submitted
**Then** that record's result is an error indicating the type is not submittable
**And** nothing is written for it.

---

### AC-005: Single-record list behaves as one write

**Given** a `records` list with exactly one valid record
**When** `submit_structured` is called
**Then** one document is written
**And** the response contains exactly one per-record result.

---

### AC-006: Re-submitting same uri updates, not duplicates

**Given** a record with `uri = "service://payments"` already ingested
**When** the same `uri`/`record_type` is submitted again with a changed payload
**Then** the existing document is updated in place
**And** no duplicate document is created.

---

### AC-007: Empty batch is rejected

**Given** a `records` list that is empty
**When** `submit_structured` is called
**Then** the call returns a clear error stating at least one record is required
**And** nothing is written (parity with `ingest_documents` requiring at least one URI).
