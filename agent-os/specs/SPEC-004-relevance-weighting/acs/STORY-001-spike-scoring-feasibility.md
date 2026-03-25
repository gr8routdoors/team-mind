# STORY-001: Spike — sqlite-vec Composite Scoring Feasibility

> ACs for the technical spike validating whether weighted scoring can compose with sqlite-vec KNN queries.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | SQL-Side Composite Scoring Test | Spike |
| AC-002 | Python Re-Ranking Fallback Test | Spike |
| AC-003 | Performance Benchmark | Spike |
| AC-004 | Written Recommendation | Spike |

---

## Acceptance Criteria

### AC-001: SQL-Side Composite Scoring Test

**Given** a populated database with documents, vectors, and a `doc_weights` table
**When** a KNN query is executed with a LEFT JOIN on `doc_weights` and a composite ORDER BY
**Then** the spike records whether the query succeeds, returns correct results, and whether the ordering reflects the composite score (not just vector distance)

---

### AC-002: Python Re-Ranking Fallback Test

**Given** the same populated database
**When** a standard KNN query is executed with over-fetch (limit * 4), then results are re-ranked in Python using `usage_score` and `decay`
**Then** the spike records that this approach produces correctly weighted results
**And** documents are ordered by the composite score

---

### AC-003: Performance Benchmark

**Given** databases with 100, 1000, and 10000 documents
**When** both approaches (SQL-side and Python re-rank) are benchmarked
**Then** the spike records query times for each approach at each scale
**And** includes a comparison table in the results

---

### AC-004: Written Recommendation

**Given** the results from AC-001 through AC-003
**When** the spike is complete
**Then** a written recommendation exists in the design doc
**And** it includes a clear go/no-go for SQL-side scoring
**And** it specifies the recommended approach for STORY-005
