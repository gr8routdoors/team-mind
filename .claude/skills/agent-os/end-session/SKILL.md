---
name: end-session
description: Use before ending significant work or switching tasks
triggers:
  - "end session"
  - "done for today"
  - "wrapping up"
  - "save context"
  - "preserve context"
---

# End Session

Preserve context from the current session for future sessions. Run this before ending significant work.

## When to Use

- End of a working session
- After completing a milestone
- When switching to a different task
- Before a break where context might be lost

## The Agent Will Rationalize

Before following this process, be aware of these rationalizations that lead to skipping session end:

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "Nothing important happened this session" | You learned something. You made decisions. You discovered gotchas. All of it matters to the next session. | Document everything, even small insights. |
| "Session summaries are optional" | No. They're the bridge between sessions. Without them, context is lost and work repeats. | Create the summary; it takes 10 minutes and prevents hours of rework. |
| "I'll write the summary next time" | You won't. Memory decays fast. Details that are clear now will be vague in a week. | Write it immediately while details are fresh. |
| "The code changes speak for themselves" | Code doesn't explain *why* it was built that way. Decisions, trade-offs, and blockers live in summaries. | Document the narrative: what happened and why. |
| "We'll update the spec and call it done" | Specs capture what was planned. Sessions capture what actually happened. Both are needed. | Create the session summary AND update the spec. |

## Process

### Step 1: Gather Session Context

Review what happened in this session:
- What was the goal?
- What was accomplished?
- What decisions were made?
- What was learned?
- What's still open?

### Step 2: Create Session Summary

Create a new file:
```
agent-os/context/sessions/YYYY-MM-DD-{topic}.md
```

Use this template:

```markdown
# Session: {Brief Topic Description}

> Date: {YYYY-MM-DD} | Duration: ~{X}h | Participants: Devon, Claude

---

## Summary

{1-2 sentence summary of the session focus and outcome}

---

## Decisions Made

- **{Decision 1}**: {What we decided} — _{Why}_
- **{Decision 2}**: {What we decided} — _{Why}_

---

## Learnings & Context to Preserve

### Domain/Business
- {Insight about how the business domain works}

### Implementation
- {Discovery about how the code works}
- {Gotcha or quirk uncovered}

### Failures (GOTCHA Self-Healing)

| What Failed | Why | Lesson | Added to Guardrails? |
|-------------|-----|--------|---------------------|
| {Approach X} | {Reason} | {Don't do Y} | ✅ / ❌ |

---

## Artifacts Updated

| Artifact | Change |
|----------|--------|
| `{path/to/file}` | {What changed} |

---

## Open Questions & Next Steps

- [ ] {Question or action item}
- [ ] {Another item}

---

> **If you only remember one thing:**
> {The single most important insight from this session}

---

_Recorded by: Claude_
```

### Step 3: Update Related Artifacts

Based on what was learned, update other artifacts:

**Spec updated?**
- Update status if it changed
- Add to decisions.md if decisions were made
- Update plan.md if scope changed

**Gotcha discovered?**
- Add to `context/component-details/{component}/gotchas.md`

**Anti-pattern found?**
- Add to `standards/guardrails.md`

**Component behavior clarified?**
- Update `context/component-details/{component}/current-behavior.md`

### Step 4: Update Priorities (if needed)

If spec is complete or priorities shifted:
- Update `agent-os/product/roadmap.md`
- Move completed items, add new items

### Step 5: Confirm Context Preserved

Present summary to user:

```
## Session Context Preserved

### Session Summary
Created: `context/sessions/{filename}.md`

### Other Updates
- ✅ {Artifact 1} — {change}
- ✅ {Artifact 2} — {change}

### Key Takeaway
> {The one thing to remember}

### Next Session
To resume: Run `/continue-spec {feature}` or review `roadmap.md`
```

## Tips

- **Be specific** — Vague summaries aren't useful. Include concrete details.
- **Capture the "why"** — Decisions without rationale are hard to revisit
- **One key insight** — Force yourself to identify the most important thing
- **Link artifacts** — Reference specific files so future sessions can find them
- **Don't skip this** — Context loss is expensive. A few minutes now saves hours later.

## Unattended Mode

When running unattended, this skill is **required** at the end of every session.

Include additional detail:
- All assumptions made
- All decisions made (even small ones)
- Anything that felt uncertain
- Recommended next actions for Devon to review
