# SPEC-002: Developer Workflow — Coverage Matrix

## Story → AC Coverage

| Story | ACs | Happy Path | Edge Cases | Integration |
|-------|-----|------------|------------|-------------|
| STORY-001: /commit skill | 5 | AC-001, AC-002 | AC-003 (sensitive files), AC-004 (multi-unit) | AC-005 (git.md compliance) |
| STORY-002: /ship-pr skill | 4 | AC-001 | AC-002 (uncommitted changes) | AC-003 (git hygiene), AC-004 (linkage) |

## Cross-cutting Concerns

| Concern | Covered By |
|---------|------------|
| CSO-compliant skill descriptions | All new skills (STORY-001, STORY-002) |
| Anti-rationalization tables | All new skills (STORY-001, STORY-002) |
| Conventional commit compliance | STORY-001 AC-005 |
| Git standards compliance | STORY-001 AC-005, STORY-002 AC-003 |

## Future (Not in Scope)

Operating profiles (full/team/lean) will layer additional behavior on these skills. See `future-profiles.md`.
