# SPEC-003: Framework Tooling & Upgrade — Coverage Matrix

## Story → AC Coverage

| Story | ACs | Happy Path | Edge Cases | Integration |
|-------|-----|------------|------------|-------------|
| STORY-001: AGENTS.md redesign | 3 | AC-001 (generic content) | AC-002 (discovery) | AC-003 (existing skills still work) |
| STORY-002: pyproject.toml + UV | 3 | AC-001 (valid config) | — | AC-002 (deps + lockfile), AC-003 (directory structure) |
| STORY-003: Directory boundary | 3 | AC-001 (documented) | AC-002 (violations found) | AC-003 (AGENTS.md map updated) |
| STORY-004: /upgrade skill | 5 | AC-003 (nuke-and-replace) | AC-002 (custom file detection), AC-005 (upstream config) | AC-001 (pre-upgrade safety), AC-004 (post-upgrade report) |

## Cross-cutting Concerns

| Concern | Covered By |
|---------|------------|
| CSO-compliant skill descriptions | STORY-004 (/upgrade skill) |
| Anti-rationalization tables | STORY-004 (/upgrade skill) |
| Framework/project boundary respected | STORY-003 (convention), STORY-004 AC-003 (upgrade respects boundary) |
| Rollback safety | STORY-004 AC-001 (pre-upgrade commit), AC-004 (rollback instructions) |
