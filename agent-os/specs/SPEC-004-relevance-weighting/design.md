# SPEC-004: Relevance Weighting System — Design

## Overview

Platform-managed relevance weighting that combines usage feedback signals with time-based decay to rank retrieval results beyond pure vector similarity. The spike (STORY-001) validates the technical approach before production implementation.

## Components

| Component | Type | Change |
|-----------|------|--------|
| doc_weights table | Storage | **New** — Separate table for usage scores, timestamps, tombstone flags. |
| DoctypeSpec | Data Model | **Extended** — Optional `decay_half_life_days` field. |
| StorageAdapter | Abstraction | **Extended** — Weight row creation on save, composite scoring on retrieval. |
| FeedbackPlugin | Plugin | **New** — ToolProvider exposing `provide_feedback` MCP tool. |
| PluginRegistry | Core Manager | **Unchanged** — FeedbackPlugin registers like any other ToolProvider. |

## Spike: STORY-001

The spike must answer three questions:

### Q1: Can sqlite-vec KNN compose with a scoring JOIN?

Test whether this query pattern works and performs:
```sql
SELECT d.id, d.uri, d.metadata, v.distance, w.usage_score,
       (v.distance - COALESCE(w.usage_score, 0) * 0.1) AS final_rank
FROM vec_documents v
JOIN documents d ON v.id = d.id
LEFT JOIN doc_weights w ON d.id = w.doc_id
WHERE v.embedding MATCH ? AND k = ?
ORDER BY final_rank
```

### Q2: What's the performance impact of the JOIN?

Benchmark with:
- 100, 1000, 10000 documents
- With and without the weights JOIN
- Measure query time delta

### Q3: If SQL-side scoring doesn't work, how does Python re-ranking perform?

Test the fallback: over-fetch from KNN, then re-rank in Python:
```python
raw_results = storage.retrieve_by_vector_similarity(vector, limit=limit * 4)
scored = [(r, compute_final_score(r)) for r in raw_results]
scored.sort(key=lambda x: x[1])
return scored[:limit]
```

### Spike deliverables:
- A standalone test file (`tests/spikes/test_weighted_scoring.py`) with benchmarks.
- A written recommendation in the spike results (update this design doc).
- Clear go/no-go for SQL-side scoring.

## Spike Results (STORY-001 — Completed)

### Findings

**SQL-side composite scoring works.** The `LEFT JOIN` on `doc_weights` with a composite `ORDER BY` composes correctly with sqlite-vec's `MATCH` operator. Tombstone filtering via `AND COALESCE(w.tombstoned, 0) = 0` also works within the same query.

**Both approaches produce identical results.** At 200 documents, the SQL and Python approaches returned 100% identical top-10 result sets, confirming functional equivalence.

**Weights change ordering.** Both approaches produce different rankings than pure vector distance, confirming that `usage_score` has a real effect on result ordering.

### Performance Benchmarks

| Scale | Baseline (KNN only) | SQL Composite | Python Re-rank |
|-------|---------------------|---------------|----------------|
| 100 docs | 0.58 ms | 0.82 ms (1.41x) | 0.79 ms (1.36x) |
| 1,000 docs | 1.00 ms | 1.09 ms (1.10x) | 1.08 ms (1.08x) |
| 10,000 docs | 9.59 ms | 9.95 ms (1.04x) | 9.82 ms (1.02x) |

Key observations:
- At small scale (100 docs), both approaches add ~40% overhead — negligible in absolute terms (< 1ms).
- At scale (10K docs), the overhead shrinks to **2-4%** — the KNN search dominates and the JOIN/re-rank cost is amortized.
- SQL and Python approaches perform nearly identically at all scales.

### Recommendation

**Go with SQL-side composite scoring (Approach 1).** It works, it's fast, and it keeps the scoring logic in one place (the query) rather than split across SQL + Python. The `LEFT JOIN` + `COALESCE` pattern handles missing weight rows cleanly, and tombstone filtering composes naturally with the existing `WHERE` clause.

The Python re-ranking approach is a viable fallback but offers no performance advantage and adds code complexity. Keep it as a documented alternative in case future sqlite-vec versions change the MATCH operator behavior.

**For STORY-005 implementation, use this query pattern:**
```sql
SELECT d.id, d.uri, d.plugin, d.doctype, d.metadata, v.distance,
       COALESCE(w.usage_score, 0.0) AS usage_score,
       (v.distance - COALESCE(w.usage_score, 0.0) * :weight_influence) AS final_rank
FROM vec_documents v
JOIN documents d ON v.id = d.id
LEFT JOIN doc_weights w ON d.id = w.doc_id
WHERE v.embedding MATCH ? AND k = ?
  AND COALESCE(w.tombstoned, 0) = 0
  [AND d.plugin IN (...)]
  [AND d.doctype IN (...)]
ORDER BY final_rank ASC
LIMIT ?
```

## Data Model

### doc_weights table

```sql
CREATE TABLE doc_weights (
    doc_id INTEGER PRIMARY KEY REFERENCES documents(id),
    usage_score REAL DEFAULT 0.0,
    last_accessed TEXT,
    created_at TEXT NOT NULL,
    tombstoned INTEGER DEFAULT 0,
    decay_half_life_days REAL
);

CREATE INDEX idx_doc_weights_tombstoned ON doc_weights(tombstoned);
```

### DoctypeSpec extension

```python
@dataclass
class DoctypeSpec:
    name: str
    description: str
    schema: dict = field(default_factory=dict)
    plugin: str = ""
    decay_half_life_days: float | None = None  # None = no decay
```

## Signal Model

| Signal | Value | Behavior |
|--------|-------|----------|
| Strong promote | +3 to +5 | Significantly boost usage_score |
| Soft positive | +1 | Mild boost |
| Soft negative | -1 | Mild demotion |
| Strong demote | -3 to -5 | Significantly lower usage_score |
| Tombstone | flag | Set tombstoned=1, excluded from all results |
| Un-tombstone | flag | Set tombstoned=0, document re-enters results |

## Composite Scoring Formula

```
effective_score = usage_score * decay_factor
decay_factor = 0.5 ^ (days_since_creation / decay_half_life_days)
    (if decay_half_life_days is NULL, decay_factor = 1.0)

final_rank = vector_distance - (effective_score * weight_influence)
```

Lower `final_rank` is better (closer match + higher weight). The `weight_influence` constant controls how much weight affects ranking relative to vector distance.

## MCP Tool

```
provide_feedback(doc_id: int, signal: int, reason?: str, tombstone?: bool)
```

- `signal`: integer from -5 to +5
- `reason`: optional freeform text for audit trail
- `tombstone`: if true, sets tombstoned flag regardless of signal value
- Returns confirmation with the new usage_score

## Execution Plan

### Task 1: Spike (MUST complete before Tasks 2-6)
- Build benchmark test file.
- Test all three scoring approaches.
- Write recommendation.
- *Stories:* STORY-001

### Task 2: Weights Table + DoctypeSpec Extension
- Create doc_weights table in StorageAdapter.initialize().
- Add decay_half_life_days to DoctypeSpec.
- Auto-create weight row on save_payload.
- *Stories:* STORY-002, STORY-004

### Task 3: Feedback Tool
- Build FeedbackPlugin.
- Expose provide_feedback MCP tool.
- Wire into CLI.
- *Stories:* STORY-003

### Task 4: Composite Scoring (approach from spike)
- Integrate into retrieve_by_vector_similarity.
- Exclude tombstoned documents.
- *Stories:* STORY-005, STORY-006
