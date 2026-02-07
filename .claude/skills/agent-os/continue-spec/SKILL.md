---
name: continue-spec
description: Resume work on an existing specification - loads context and identifies next steps
triggers:
  - "continue spec"
  - "resume spec"
  - "pick up where"
  - "continue working on"
---

# Continue Spec

Resume work on an existing specification.

## Process

### Step 1: Identify the Spec

If the user specified a spec name, search for it:
```
agent-os/specs/SPEC-{NNN}-{slug}/
```

If unclear, list available specs and use AskUserQuestion:
```
I found these specs in agent-os/specs/:

1. SPEC-001-user-authentication (Status: in_progress)
2. SPEC-002-data-export (Status: in_design)
3. ...

Which spec should we continue working on?
```

### Step 2: Load Spec Context

Read the spec folder contents:
- `README.md` — Scope, context, decisions
- `design.md` — Architecture + execution plan
- `stories.yml` — Story status tracking
- `acs/` — Acceptance criteria files

### Step 3: Check Spec Status

Look at the status in `specs/index.yml`:

| Status | Next Action |
|--------|-------------|
| `in_requirements` | Continue shaping — refine requirements, add details |
| `in_design` | Complete architectural design, define stories |
| `in_progress` | Continue implementation from where we left off |
| `complete` | Verify Definition of Done, consider archiving |

### Step 4: Load Related Context

Check for related session summaries:
```
agent-os/context/sessions/*{spec-topic}*
```

Read any relevant sessions to understand:
- Previous decisions and their rationale
- Learnings or gotchas discovered
- Open questions that were flagged

### Step 5: Check Component Context

If the spec involves a specific component (e.g., some-service):
```
agent-os/context/component-details/{component}/
```

Read:
- `current-behavior.md` — How it works today
- `gotchas.md` — Known issues to avoid

### Step 6: Summarize and Confirm

Present a summary to the user:

```
## Resuming: SPEC-{NNN} — {Name}

**Status:** {current status}
**Stories:** {X/Y passing}

### Where We Left Off
{Summary of current state based on spec and sessions}

### Stories Status
- STORY-001: {name} — passing ✓
- STORY-002: {name} — failing
- STORY-003: {name} — failing

### Open Questions
- {Any unresolved questions from spec or sessions}

### Suggested Next Steps
1. {Based on status and context}
2. {Next logical action}

Ready to continue?
```

### Step 7: Proceed Based on Status

**If in_requirements:**
- Continue refining the spec
- Address open questions
- Update README.md with new decisions

**If in_design:**
- Complete architectural design
- Define stories and ACs
- Prepare for implementation

**If in_progress:**
- Review what's been completed
- Identify next failing story
- Continue building toward passing tests

## Tips

- **Don't start from scratch** — Always check for existing context first
- **Update as you go** — Keep spec status and session summaries current
- **Flag blockers** — If you discover something blocking progress, document it
- **Preserve decisions** — Add to README.md when making significant choices
