# ADR-003: Platform-Managed Relevance Weighting with Plugin-Controlled Decay

**Status:** Accepted (spike validated SQL-side composite scoring — see SPEC-004 STORY-001)
**Date:** 2026-03-25
**Spec:** SPEC-004 (Relevance Weighting System)
**See also:** [Plugin Developer Guide](../plugin-developer-guide.md), [ADR-001: Record Types](ADR-001-plugin-scoped-record-types.md), [ADR-009: Document Segments](ADR-009-document-segments.md) — formalizes the "unit of weighting is the row" insight with explicit parent-child hierarchy and aggregate parent scoring

## Context

Team Mind stores knowledge that varies dramatically in quality and relevance over time. Meeting notes from last month may be stale. A code signature from a year ago may still be perfectly valid. An AI agent's search results today should surface the most valuable information, not just the most semantically similar.

The roadmap identifies three intelligence mechanisms: usage-based ranking, information decay, and semantic deduplication. This ADR addresses the first two — how information gains or loses value over time.

### Key design tension

Weighting could be implemented per-plugin (each plugin builds its own scoring) or in the platform (one system for all plugins). Per-plugin weighting forces every plugin author to reinvent scoring logic. Platform weighting risks being too rigid for diverse doctypes (code vs. meeting notes vs. user preferences all age differently).

### Granularity insight

Our `documents` table already stores data at the **chunk** level, not the source-file level. When MarkdownPlugin ingests a file, it creates one row per paragraph. The retrieval unit is the row. Therefore, **the unit of weighting is the row** — which is already the right granularity for scoring. Plugins that want finer-grained weighting chunk smaller during ingestion; plugins that want coarser weighting chunk larger. The weighting system doesn't need to solve sub-row granularity.

## Decision

Relevance weighting is a **platform concern** managed by the core engine. Plugins influence it through two channels: **usage signals** (feedback from AI agents and humans) and **decay policy** (declared per-doctype).

### 1. Weighted Signal Model (not binary +1/-1)

Feedback signals carry a magnitude, not just a direction:

| Signal Type | Range | Example |
|-------------|-------|---------|
| Soft positive | +1 | AI used this result and it contributed to the response |
| Strong promote | +3 to +5 | Human explicitly marks as high-value or canonical |
| Soft negative | -1 | AI retrieved this but didn't use it |
| Strong demote | -3 to -5 | Human marks as outdated or low-quality |
| Tombstone | flag | "This is wrong — exclude from all future results" |

Tombstoning does not delete the row (preserves audit trail) but effectively removes it from search results via a boolean flag.

AI agents provide feedback via a `provide_feedback(doc_id, signal, reason?)` MCP tool. The platform records the signal and updates the weight. Plugins don't implement this — it's a core tool that works across all doctypes.

**Score accumulation uses cumulative moving average, not simple addition.** Each new signal is averaged proportionally into the existing score:

```
new_count = old_count + 1
new_score = old_score + (signal - old_score) / new_count
```

This naturally bounds `usage_score` to the signal range [-5, +5] without artificial clamping. A document with 5000 ratings of +5 followed by one -5 ends up at ≈ 4.998 — the single outlier has proportionally minimal impact. The `doc_weights` table tracks `signal_count` to maintain the running average.

### 2. Decay Policy via DoctypeSpec

Plugins declare how their data ages by extending DoctypeSpec:

```python
DoctypeSpec(
    name="meeting_notes",
    decay_half_life_days=30,    # loses half its boost every 30 days
    ...
)

DoctypeSpec(
    name="code_signature",
    decay_half_life_days=None,  # no decay — code doesn't age
    ...
)

DoctypeSpec(
    name="user_preference",
    decay_half_life_days=90,    # preferences shift slowly
    ...
)
```

The platform applies the decay math at query time. The plugin just declares the policy.

### 3. Separate Weights Table

Weights live in their own table, not on the `documents` row:

```sql
CREATE TABLE doc_weights (
    doc_id INTEGER PRIMARY KEY REFERENCES documents(id),
    usage_score REAL DEFAULT 0.0,
    last_accessed TEXT,              -- ISO timestamp
    created_at TEXT NOT NULL,        -- ISO timestamp
    tombstoned INTEGER DEFAULT 0,   -- boolean flag
    decay_half_life_days REAL       -- copied from doctype at creation, nullable
);
```

**Why a separate table:**
- Decouples weighting from document storage — plugins that don't care about weights aren't affected.
- Enables weight operations (feedback, decay recalculation) without touching the documents table.
- Can be indexed and queried independently.
- Weight rows are created lazily (on first feedback or at ingestion time).

### 4. Composite Scoring at Query Time

When `retrieve_by_vector_similarity` runs, the platform computes:

```
final_rank = f(vector_distance, usage_score, age_decay)
```

Where:
- `vector_distance` = raw KNN similarity (what we have today)
- `usage_score` = accumulated feedback signals
- `age_decay` = `usage_score * (0.5 ^ (days_since_creation / half_life))` if decay is configured

**Open question (spike required):** Whether this can be computed in SQL via a JOIN with `doc_weights`, or whether it requires Python post-processing after the KNN fetch. sqlite-vec's `MATCH` operator may not compose with arbitrary scoring JOINs. The spike (SPEC-004, STORY-001) will validate this.

### 5. Feedback MCP Tool

A new core tool, not plugin-specific:

```
provide_feedback(doc_id: int, signal: int, reason?: str)
```

- `signal` ranges from -5 to +5 (0 is not meaningful)
- `reason` is optional freeform text (useful for audit/debugging)
- Tombstoning is a special case: `provide_feedback(doc_id, signal=0, tombstone=true)`

## Alternatives Considered

### 1. Per-plugin weighting

Each plugin implements its own scoring and decay logic.

**Rejected because:**
- Every plugin author reinvents the same scoring math.
- No cross-plugin consistency — results from different plugins would have incomparable scores.
- The feedback tool would need to route signals to the correct plugin.

### 2. Weight on the documents row

Add `usage_score`, `last_accessed`, etc. directly to the `documents` table.

**Rejected because:**
- Bloats the documents table with columns many plugins don't use.
- Weight updates (frequent) would contend with document inserts (also frequent).
- Harder to evolve the weighting schema independently of the document schema.

### 3. Binary +1/-1 signals only

Simple up/down voting like Reddit or Stack Overflow.

**Rejected because:**
- Can't distinguish "slightly useful" from "this is the canonical answer."
- Can't express "this is actively harmful — remove it."
- The installed-instance model (teams own their knowledge base) makes stronger signals safe — there's no adversarial voting concern.

### 3b. Additive accumulation with clamping

Sum all signals directly (`score += signal`) and clamp to a range like [-50, +50].

**Rejected because:**
- Unfair to outliers: 5000 signals of +5 then one -5 drops the score to 45 — the single negative voice has disproportionate impact.
- Cumulative moving average is fairer: the same scenario gives ≈ 4.998, and naturally bounds to [-5, +5] without artificial clamping.

### 4. Delete instead of tombstone

Remove bad documents entirely.

**Rejected because:**
- Loses audit trail — you can't explain why something disappeared.
- Can't undo a mistaken deletion without re-ingesting.
- Tombstoning is reversible (flip the flag) while deletion is not.

## Consequences

### Positive

- **Zero plugin work for basic weighting.** Every plugin gets usage-based ranking for free via the platform.
- **Doctype-aware decay.** Code doesn't age like meeting notes — plugins declare this once in their DoctypeSpec.
- **Rich signal model.** The magnitude-based feedback captures more nuance than binary voting.
- **Clean separation.** Weights table is independent of documents — can evolve or be dropped without migration risk.
- **Audit-friendly.** Tombstoned documents are still in the database; feedback signals with optional reasons provide an audit trail.

### Negative

- **Scoring composability risk.** sqlite-vec may not support efficient composite scoring in SQL. Spike required to validate. Worst case: Python-side re-ranking after KNN fetch (functional but less efficient).
- **Weight staleness.** If decay is computed at query time, old weights don't need periodic recalculation — but if an admin wants to see "what's the current effective score of document X?" they need to compute it on the fly.
- **Lazy weight creation.** Documents without feedback signals have no row in `doc_weights`. Query logic must handle this (LEFT JOIN or COALESCE).

### Neutral

- The `provide_feedback` tool adds one more tool to the MCP catalog. Lightweight.
- DoctypeSpec gains one optional field (`decay_half_life_days`). Backward compatible.
- **SPEC-011 (Document Segments):** The insight that "the unit of weighting is the row" established here is now formalized by ADR-009. Segments (child rows) each have their own `doc_weights` entry and are independently rated. Parent documents have no weight row — their effective score is computed at query time as the average of their non-tombstoned children's scores. This extends the decay and feedback model without changing it: all weight operations still target individual rows. See [ADR-009: Document Segments](ADR-009-document-segments.md).
