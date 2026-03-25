# Coverage Matrix

## Story Coverage

| Story | Happy | Validation | Edge | Error | Integration |
|-------|-------|------------|------|-------|-------------|
| STORY-001 | AC-001, AC-002 | AC-004 | AC-003 | — | — |
| STORY-002 | AC-001, AC-004 | AC-003 | — | — | AC-002 |
| STORY-003 | AC-001, AC-002, AC-003, AC-004, AC-005 | — | AC-007, AC-008 | — | AC-006 |
| STORY-004 | AC-001, AC-002, AC-003, AC-004 | — | AC-005 | — | AC-006 |
| STORY-005 | AC-001, AC-002, AC-003, AC-004, AC-005 | AC-007 | AC-008 | — | AC-006 |
| STORY-006 | AC-001, AC-002, AC-003, AC-004 | — | — | — | AC-005, AC-006 |

## Summary

- Total stories: 6
- Total ACs: 32
- Coverage gaps: None — error paths are minimal since this is a schema/model layer; validation enforcement is deferred to the Librarian spec.
- Design principle: Every filter surface (StorageAdapter, PluginRegistry, MCP tools) accepts lists uniformly.
