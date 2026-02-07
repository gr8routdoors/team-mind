---
name: derive-acs
description: Generate acceptance criteria from requirements and architectural design
triggers:
  - "derive acs"
  - "generate acs"
  - "create acceptance criteria"
  - "write acs"
---

# Derive ACs

Generate acceptance criteria from requirements and architectural design.

## Prerequisites

Before running this skill:
1. Spec exists with requirements in `specs/SPEC-{NNN}-{slug}/README.md`
2. Architectural design documented in `specs/SPEC-{NNN}-{slug}/design.md`
3. Stories defined in `specs/SPEC-{NNN}-{slug}/stories.yml`

If these don't exist, run `/shape-spec` first.

## Process

### Step 1: Load Context

Read the following to understand the feature:

```
specs/SPEC-{NNN}-{slug}/README.md     # Requirements, scope, context
specs/SPEC-{NNN}-{slug}/design.md     # Architectural approach
specs/SPEC-{NNN}-{slug}/stories.yml   # Stories to derive ACs for
product/domain/                        # Business rules, terminology
standards/bdd.md                       # AC format and coverage patterns
```

Summarize key requirements and stories to the user for confirmation.

### Step 2: Map Stories to Coverage

For each story in stories.yml, identify the coverage needed. Use AskUserQuestion:

```
Based on the stories, I'll generate ACs with this coverage:

STORY-001: {name}
- Happy path scenarios
- Edge cases (boundaries, nulls)

STORY-002: {name}
- Happy path scenarios
- Validation rules
- Error conditions

STORY-003: {name}
- Happy path scenarios
- Business rules
- Integration scenarios

Does this coverage plan look right? (Adjust / Confirm)
```

### Step 3: Generate ACs for Each Story

For each story, generate ACs using coverage patterns.

**Coverage Checklist** (apply as relevant to each story):
- [ ] Happy path — Primary success scenario
- [ ] Validation — Invalid inputs
- [ ] Business rules — Rule violations
- [ ] Edge cases — Boundaries, nulls, empty
- [ ] Error conditions — Downstream failures
- [ ] Integration — Cross-component interactions

**AC Format**:
```markdown
### AC-{NNN}: {Title}

**Given** {initial context}
**And** {additional context if needed}
**When** {action taken}
**Then** {expected outcome}
**And** {additional outcomes if needed}
```

### Step 4: Create AC Files

Create `specs/SPEC-{NNN}-{slug}/acs/` directory with one file per story:

```
specs/SPEC-{NNN}-{slug}/acs/
├── STORY-001-{name}.md
├── STORY-002-{name}.md
├── STORY-003-{name}.md
└── coverage-matrix.md
```

**File Template**:
```markdown
# STORY-{NNN}: {Story Name} — Acceptance Criteria

> ACs for {brief description from stories.yml}

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | {title} | Happy path |
| AC-002 | {title} | Validation |
| AC-003 | {title} | Edge case |

---

## Acceptance Criteria

### AC-001: {Title}

**Given** ...
**When** ...
**Then** ...

---

### AC-002: {Title}

**Given** ...
**When** ...
**Then** ...
```

### Step 5: Build Coverage Matrix

Create traceability from stories to ACs:

```markdown
# Coverage Matrix

## Story Coverage

| Story | Happy | Validation | Edge | Error | Integration |
|-------|-------|------------|------|-------|-------------|
| STORY-001 | AC-001, AC-002 | — | AC-003 | — | — |
| STORY-002 | AC-001 | AC-002, AC-003 | AC-004 | AC-005 | — |
| STORY-003 | AC-001 | — | — | — | AC-002, AC-003 |

## Summary

- Total stories: 3
- Total ACs: 15
- Coverage gaps: None
```

Save as `specs/SPEC-{NNN}-{slug}/acs/coverage-matrix.md`.

### Step 6: Review with User

Present generated ACs for review:

```
## Generated ACs for SPEC-{NNN}

### STORY-001: {name} ({N} ACs)
- AC-001: {title} — Happy path
- AC-002: {title} — Happy path
- AC-003: {title} — Edge case

### STORY-002: {name} ({N} ACs)
- AC-001: {title} — Happy path
- AC-002: {title} — Validation
...

### Coverage Summary
- Total ACs: {count}
- Stories covered: {count}/{total}
- Gaps: {list any uncovered areas}

Ready to save these ACs? (Save / Adjust / Add more)
```

### Step 7: Save and Summarize

After user approval:
1. Write AC files to `specs/SPEC-{NNN}-{slug}/acs/`
2. Write coverage matrix
3. Summarize what was created

```
## ACs Created

| File | ACs | Coverage Types |
|------|-----|----------------|
| STORY-001-batch-loading.md | 5 | Happy, Edge |
| STORY-002-cache-invalidation.md | 6 | Happy, Validation, Error |
| STORY-003-fallback.md | 4 | Happy, Edge, Integration |
| coverage-matrix.md | — | Traceability |

**Total:** 15 ACs covering 3 stories

Next: Run `/generate-bdd-tests` to create test scaffolding
```

## Tips

- **Be specific** — Avoid vague terms like "properly", "correctly", "appropriate"
- **One behavior per AC** — If an AC tests multiple things, split it
- **Include data** — Use concrete values (not "some value")
- **Think like a tester** — What would break this? What edge cases exist?
- **Reference domain** — Check `product/domain/` for business rules to test
- **Match story scope** — ACs should align with story boundaries
