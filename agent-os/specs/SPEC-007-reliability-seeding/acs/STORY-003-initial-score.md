# STORY-003: Initial Score on save_payload — Acceptance Criteria

---

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Default Initial Score Is Zero | Happy path |
| AC-002 | Custom Initial Score Seeds usage_score | Happy path |
| AC-003 | Signal Count Stays Zero | Validation |
| AC-004 | Higher Initial Score Ranks Higher | Integration |

---

### AC-001: Default Initial Score Is Zero
**Given** `save_payload` called without `initial_score`
**When** the doc_weights row is inspected
**Then** `usage_score` is `0.0`

### AC-002: Custom Initial Score Seeds usage_score
**Given** `save_payload` called with `initial_score=0.8`
**When** the doc_weights row is inspected
**Then** `usage_score` is `0.8`

### AC-003: Signal Count Stays Zero
**Given** `save_payload` called with `initial_score=0.8`
**When** the doc_weights row is inspected
**Then** `signal_count` is `0` (initial score is not a feedback signal)

### AC-004: Higher Initial Score Ranks Higher
**Given** two documents with identical vectors, one with `initial_score=0.9` and one with `initial_score=0.1`
**When** `retrieve_by_vector_similarity` is called
**Then** the document with `initial_score=0.9` ranks higher
