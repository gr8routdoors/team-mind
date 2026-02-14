---
name: start-session
description: Use at the beginning of every new working session
triggers:
  - "starting work"
  - "new session"
  - "begin session"
  - "what should I work on"
---

# Start Session

**Run this skill at the beginning of every new session.** This orients you to the current state of the project before any work begins.

## Purpose

This skill prevents:
- Working on outdated priorities
- Missing context from previous sessions
- Duplicating completed work
- Losing track of in-progress stories

## The Agent Will Rationalize

Before following this process, be aware of these rationalizations that lead to skipping session startup:

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "Nothing has changed since yesterday" | Context decays. Priorities shift, specs are updated, failures are discovered. | Load context to verify state hasn't changed. |
| "I remember what we're working on" | You don't. Memory is unreliable. Priorities in your head contradict priorities in the roadmap. | Load the roadmap and recent sessions to confirm. |
| "Starting up takes too long" | Startup takes 5 minutes. False starts from missing context take hours. | Run the process; it pays for itself immediately. |
| "I'll just look at the spec" | Specs are static. They don't capture blockers, learnings, or decisions made after spec creation. | Load the spec AND recent sessions for complete picture. |
| "We didn't make decisions in the last session worth reviewing" | Even small decisions compound. Skipping this means you'll remake decisions. | Load sessions to see all reasoning and avoid repetition. |

## Process

### Step 1: Load Priorities

Read `agent-os/product/roadmap.md`:

```
Current priorities loaded:

1. [Priority 1] — [Status]
2. [Priority 2] — [Status]
3. [Priority 3] — [Status]
```

If the file doesn't exist, note this and continue.

### Step 2: Check Recent Sessions

Read the most recent files in `agent-os/context/sessions/` (up to 3):

```
Recent session context:

- [Date]: [Summary of session focus and outcomes]
- [Date]: [Summary of session focus and outcomes]
```

Pay attention to:
- Decisions made
- Blockers encountered
- Work left incomplete
- Questions raised

If no session files exist, note this and continue.

### Step 3: Review Active Specs

Read `agent-os/specs/index.yml` to see all active specs:

```
Active specs:

| Spec | Status | Stories | Complete |
|------|--------|---------|----------|
| SPEC-001: [Name] | in_progress | 3 | 1 |
| SPEC-002: [Name] | in_design | 2 | 0 |
```

For any spec that is `in_progress`, also read its `stories.yml` to see story-level status:

```
SPEC-001 Stories:
- STORY-001: [Name] — passing ✓
- STORY-002: [Name] — failing
- STORY-003: [Name] — failing
```

### Step 4: Check Operating Mode

Determine the operating mode for this session:

```
Operating mode check:

Are you (Devon) actively present in this session?
- Interactive: You're here — I'll ask questions, iterate quickly
- Unattended: Working autonomously — I'll be conservative, document everything
```

If unattended, remind yourself of the guardrails in `standards/guardrails.md` (GR-U01–U06).

### Step 5: Present Orientation Summary

Summarize what you've learned:

```
Session Orientation Complete
============================

**Current Focus:** [Top priority from roadmap.md]

**Recent Context:**
- [Key point from recent sessions]
- [Key point from recent sessions]

**Active Work:**
- SPEC-001: [Name] — [X/Y stories complete]
  - Next: STORY-002 [Name]

**Mode:** Interactive / Unattended

**Ready to proceed.** What would you like to work on?
```

## Quick Reference Paths

| Artifact | Path |
|----------|------|
| Roadmap | `agent-os/product/roadmap.md` |
| Sessions | `agent-os/context/sessions/` |
| Specs Index | `agent-os/specs/index.yml` |
| Guardrails | `agent-os/standards/guardrails.md` |
| Standards Index | `agent-os/standards/index.yml` |

## Tips

- **Always run this first** — Even if you think you know what to do, context may have changed
- **Note discrepancies** — If priorities don't match recent session work, flag it
- **Don't skip steps** — Each step builds your understanding
- **Ask if unclear** — If priorities conflict or context is confusing, ask before proceeding
