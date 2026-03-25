# STORY-005: Composite Scoring in Retrieval — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Weighted Results Differ from Unweighted | Happy path |
| AC-002 | No Weights Equals Baseline | Edge case |
| AC-003 | Decay Reduces Effective Score Over Time | Happy path |
| AC-004 | No Decay Means Full Score | Edge case |
| AC-005 | Plugin and Doctype Filters Still Work | Integration |

---

### AC-001: Weighted Results Differ from Unweighted

**Given** documents with varying `usage_score` values
**When** `retrieve_by_vector_similarity` is called
**Then** the result ordering reflects the composite score, not just vector distance

---

### AC-002: No Weights Equals Baseline

**Given** documents with no feedback (all `usage_score=0.0`, no decay)
**When** `retrieve_by_vector_similarity` is called
**Then** results are ordered identically to pure vector distance

---

### AC-003: Decay Reduces Effective Score Over Time

**Given** a document with `usage_score=5.0` and `decay_half_life_days=30`, created 30 days ago
**When** the composite score is computed
**Then** the effective score is approximately `5.0 * 0.5 = 2.5`

---

### AC-004: No Decay Means Full Score

**Given** a document with `usage_score=5.0` and `decay_half_life_days=NULL`
**When** the composite score is computed
**Then** the effective score is `5.0` regardless of age

---

### AC-005: Plugin and Doctype Filters Still Work

**Given** documents with weights across multiple plugins and doctypes
**When** `retrieve_by_vector_similarity` is called with `plugins` and `doctypes` filters
**Then** filtering works correctly alongside composite scoring
