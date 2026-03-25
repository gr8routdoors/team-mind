# STORY-006: Tombstone Support — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Tombstoned Excluded from Search | Happy path |
| AC-002 | Tombstone via Feedback Tool | Happy path |
| AC-003 | Un-Tombstone Restores Document | Happy path |
| AC-004 | Tombstoned Row Still in Database | Validation |

---

### AC-001: Tombstoned Excluded from Search

**Given** a document with `tombstoned=1`
**When** `retrieve_by_vector_similarity` is called
**Then** the document does not appear in results

---

### AC-002: Tombstone via Feedback Tool

**Given** a document
**When** `provide_feedback(doc_id, signal=0, tombstone=true)` is called
**Then** `doc_weights.tombstoned` is set to `1`

---

### AC-003: Un-Tombstone Restores Document

**Given** a tombstoned document
**When** `provide_feedback(doc_id, signal=0, tombstone=false)` is called
**Then** `doc_weights.tombstoned` is set to `0`
**And** the document reappears in search results

---

### AC-004: Tombstoned Row Still in Database

**Given** a tombstoned document
**When** the `documents` and `doc_weights` tables are queried directly
**Then** both rows still exist (not deleted)
