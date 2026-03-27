# STORY-001: Reliability Hint on IngestionBundle — Acceptance Criteria

---

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Field Exists and Defaults to None | Happy path |
| AC-002 | Hint Propagates Through Bundle | Happy path |
| AC-003 | Hint Accessible in Processor | Integration |

---

### AC-001: Field Exists and Defaults to None
**Given** an `IngestionBundle` created without specifying `reliability_hint`
**When** `reliability_hint` is accessed
**Then** it is `None`

### AC-002: Hint Propagates Through Bundle
**Given** a bundle created with `reliability_hint=0.8`
**When** a processor receives the bundle
**Then** `bundle.reliability_hint` is `0.8`

### AC-003: Hint Accessible in Processor
**Given** a processor that reads `bundle.reliability_hint`
**When** the pipeline ingests with `reliability_hint=0.7`
**Then** the processor sees `0.7`
