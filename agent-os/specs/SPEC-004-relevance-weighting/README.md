# SPEC-004: Relevance Weighting System

## Overview

Adds platform-managed relevance weighting to Team Mind's retrieval system. Documents gain or lose value based on usage feedback and time-based decay. The platform handles all scoring math; plugins influence it by declaring decay policies on their doctypes and receiving weighted results automatically.

## Scope

**In scope:**
- Technical spike: validate sqlite-vec composite scoring feasibility.
- `doc_weights` table with usage_score, timestamps, tombstone flag, and decay half-life.
- Weighted signal model (+5 to -5 magnitude, plus tombstone).
- `provide_feedback` MCP tool for AI agents and humans.
- Decay policy via `decay_half_life_days` on DoctypeSpec.
- Composite scoring integration into `retrieve_by_vector_similarity`.
- Weight creation during ingestion (auto-populated from doctype decay policy).

**Out of scope:**
- Semantic deduplication (separate spec).
- Feedback analytics / dashboards.
- Multi-dimensional weighting (e.g., separate scores for accuracy vs. relevance).
- Periodic background decay recalculation (decay is computed at query time).

## Context

**References:**
- `agent-os/context/architecture/ADRs/ADR-003-relevance-weighting.md` — Design rationale, signal model, alternatives.
- `agent-os/product/roadmap.md` — Phase 2: Intelligence & Weighting.
- `agent-os/product/mission.md` — Usage-Based Reliability as key differentiator.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Spike first | Build directly vs spike | sqlite-vec composite scoring is the make-or-break risk. Must validate before writing production code. |
| Platform-managed weights | Platform vs per-plugin | Every plugin gets weighting for free. Consistent scoring across doctypes. |
| Magnitude signals (-5 to +5) | Binary ±1 vs magnitude | Captures nuance: "slightly useful" vs "canonical" vs "harmful." Safe in installed-instance model. |
| Separate weights table | On documents row vs separate table | Clean separation, independent evolution, no bloat on documents table. |
| Tombstone over delete | Delete vs flag | Preserves audit trail, is reversible, doesn't require re-ingestion to undo. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | Spike: sqlite-vec Composite Scoring Feasibility | pending |
| STORY-002 | Doc Weights Table & Ingestion Hook | pending |
| STORY-003 | Provide Feedback MCP Tool | pending |
| STORY-004 | Decay Policy on DoctypeSpec | pending |
| STORY-005 | Composite Scoring in Retrieval | pending |
| STORY-006 | Tombstone Support | pending |

**Note:** Stories 002-006 are provisional. The spike (STORY-001) may reveal constraints that change the approach — particularly around whether scoring happens in SQL or Python. The remaining stories will be refined after the spike completes.
