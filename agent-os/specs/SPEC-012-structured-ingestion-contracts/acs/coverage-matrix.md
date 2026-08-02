# SPEC-012 — Coverage Matrix

Traceability from stories to acceptance criteria and coverage types.

## Story Coverage

| Story | Happy | Validation | Business rule | Edge | Integration |
|-------|-------|------------|---------------|------|-------------|
| STORY-001 Mandatory schema & guards | AC-001 | AC-002, AC-003 | AC-004 | AC-005, AC-006 | — |
| STORY-002 write_record toolkit | AC-001 | AC-002 | AC-004, AC-005, AC-006 | AC-003, AC-009 | AC-007, AC-008 |
| STORY-003 submit_structured endpoint | AC-001 | AC-004 | AC-002 | AC-005, AC-007 | AC-003, AC-006 |
| STORY-004 Discovery | AC-001 | — | AC-002 | — | AC-003 |
| STORY-005 MarkdownPlugin compliance | AC-001 | AC-004 | AC-002 | — | AC-003 |
| STORY-006 Raw content by-value | AC-001 | AC-002 | AC-005 | AC-003 | AC-004 |
| STORY-007 Documentation & ADR-011 | — (no BDD) | — | — | — | — |

## Summary

- Total stories: 7 (6 BDD-testable, 1 documentation)
- Total ACs: 33
  - STORY-001: 6 · STORY-002: 9 · STORY-003: 7 · STORY-004: 3 · STORY-005: 4 · STORY-006: 5
- Coverage gaps: none for the testable stories. STORY-007 is documentation-only (verified by review, not BDD).

## Cross-cutting guarantees (asserted across stories)

- **No unvalidated write path** — every write goes through `write_record` (STORY-002 AC-002; STORY-005 AC-003).
- **metadata 1:1 with payload; envelope isolation** — STORY-002 AC-001/AC-009; STORY-005 AC-002.
- **Idempotency on `uri`** — STORY-002 AC-007/AC-008; STORY-003 AC-006; STORY-006 AC-004.
- **Reliability ladder (SPEC-007)** — STORY-002 AC-004/AC-005/AC-006.
