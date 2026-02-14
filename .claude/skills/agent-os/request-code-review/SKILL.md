---
name: request-code-review
description: Use after completing implementation work, before merging or marking stories complete
triggers:
  - "request review"
  - "code review"
  - "review my code"
  - "get feedback"
---

# Request Code Review

Dispatch a code review subagent to catch issues before they cascade.

## The Agent Will Rationalize

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "This change is too simple to review" | Simple changes break complex systems. Reviews catch what you missed. | Request the review. Simple changes review fast. |
| "I already reviewed my own code" | Self-review is biased. You see what you intended, not what you wrote. | Self-review is step 1. External review is step 2. |
| "Reviews slow down delivery" | Bugs in production slow down delivery more. Reviews catch bugs early. | Invest 10 minutes now to save hours of debugging. |
| "I'll review at the end" | Issues compound. Late review means late rework. | Review after each story, not after all stories. |

## When to Request

**Mandatory:**
- After completing a story in a spec
- Before merging to main branch
- Before marking a spec complete

**Recommended:**
- When stuck (fresh perspective helps)
- After fixing a complex bug
- Before refactoring

## Process

### Step 1: Identify Review Scope

Determine what code to review:
- Which story was just completed?
- What files were changed?
- What are the relevant ACs?

### Step 2: Two-Stage Review

Code review happens in two stages. **Order matters — do not skip or reorder.**

**Stage 1: Spec Compliance**
- Did the implementation match the story's ACs?
- Is anything missing?
- Is anything extra (YAGNI)?
- Use `dispatch-subagents/spec-reviewer-prompt.md` template

**Stage 2: Code Quality** (only after spec compliance passes)
- Is the code clean and maintainable?
- Are tests comprehensive?
- Are errors handled properly?
- Use `dispatch-subagents/code-quality-reviewer-prompt.md` template

### Step 3: Act on Feedback

| Severity | Action |
|----------|--------|
| Critical | Fix immediately before proceeding |
| Important | Fix before marking story complete |
| Minor | Note for follow-up, OK to proceed |

### Step 4: Verify Fixes

After fixing reviewer issues:
- Run verification (tests, build)
- Request re-review if changes were significant

## Tips

- **Review early, review often** — Don't accumulate unreviewed work
- **Push back if wrong** — Reviewers can be incorrect. Use technical reasoning.
- **Don't be performative** — Skip "great point!" Just fix the issue.
