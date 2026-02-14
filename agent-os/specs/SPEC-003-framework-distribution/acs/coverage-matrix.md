# SPEC-003: Framework Distribution — Coverage Matrix

## Story → AC Coverage

| Story | ACs | Happy Path | Edge Cases | Integration |
|-------|-----|------------|------------|-------------|
| STORY-001: pyproject.toml + UV | 3 | AC-001 | — | AC-002 (deps), AC-003 (structure) |
| STORY-002: Standards validator | 4 | AC-004 | AC-001 (missing), AC-002 (orphan), AC-003 (tags) | — |
| STORY-003: Install validator | 4 | AC-004 | AC-001 (missing skill), AC-002 (missing section) | AC-003 (structure) |
| STORY-004: Framework manifest | 4 | AC-001, AC-004 | AC-002 (exclusions) | AC-003 (diff) |
| STORY-005: /upgrade skill | 4 | AC-002 | AC-003 (conflicts) | AC-001 (detection), AC-004 (tooling) |
| STORY-006: /contribute-upstream | 3 | AC-001, AC-002 | AC-003 (exclusion) | — |
| STORY-007: Version tagging | 2 | AC-001 | — | AC-002 (upgrade display) |
| STORY-008: Minimal AGENTS.md | 3 | AC-001 | AC-002 (TODO markers) | AC-003 (no knowledge loss) |
| STORY-009: /clean-install | 4 | AC-001, AC-002 | — | AC-003 (fork), AC-004 (validation) |
| STORY-010: /onboard-project | 5 | AC-001, AC-003 | AC-002 (quality), AC-004 (features) | AC-005 (gap analysis) |
| STORY-011: Getting started guide | 2 | AC-001 | — | AC-002 (links) |

## Cross-cutting Concerns

| Concern | Covered By |
|---------|------------|
| CSO-compliant skill descriptions | All new skills |
| Anti-rationalization tables | All new skills |
| Python tools testable with pytest | STORY-001 AC-003, all tool stories |
| Framework/project boundary respected | STORY-004, STORY-005 AC-003, STORY-006 AC-003, STORY-009 AC-001 |
