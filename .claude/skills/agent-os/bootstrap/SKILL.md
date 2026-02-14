---
name: bootstrap
description: Use when an agent is new to this project or returning after a long gap
triggers:
  - "first time"
  - "new to project"
  - "how does this work"
  - "onboard"
---

# Bootstrap

**Run this skill when starting work on this project for the first time.** This teaches you about Agent OS and how this development environment works.

## Purpose

This skill onboards a new agent to:
- Understand the Agent OS framework
- Know where to find what
- Learn the workflow and conventions
- Get oriented to current work (via /start-session)

## When to Use

- First time working on this project
- After a long gap (context may have evolved)
- When unsure how the project is organized

## The Agent Will Rationalize

Before following this process, be aware of these rationalizations that lead to skipping onboarding:

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "I already know how frameworks work" | You don't know *this* framework. Every project has unique conventions. Assuming familiarity causes mistakes. | Go through the full bootstrap to learn this project's specifics. |
| "I can figure it out as I work" | No. You'll make mistakes because you don't understand the structure. | Invest 30 minutes learning the framework to prevent missteps. |
| "The code is self-explanatory" | It's not. Code shows *what* was built. Frameworks show *how* to extend it. | Learn the framework so you work *with* it, not against it. |
| "I don't need to understand the workflow" | The workflow is the contract. Breaking it causes problems for future sessions. | Understand the workflow so you operate consistently with the framework. |
| "I'll skip bootstrap and run /start-session instead" | /start-session assumes you know the framework. Bootstrap teaches the framework first. | Run bootstrap first, then /start-session. |

## Process

### Step 1: Understand Agent OS

Read `AGENTS.md` at the repository root:

```
Agent OS loaded. Key concepts:

- **Standards** — Conventions in `agent-os/standards/`, indexed by `index.yml`
- **Skills** — Workflows in `.claude/skills/agent-os/`
- **Product** — Mission, roadmap, priorities in `agent-os/product/`
- **Context** — Architecture, component details, sessions in `agent-os/context/`
- **Specs** — Feature specifications in `agent-os/specs/`
```

### Step 2: Learn the Standards System

Read `agent-os/standards/index.yml`:

```
Standards available:

| Standard | Tags | Purpose |
|----------|------|---------|
| guardrails | all | What NOT to do |
| code-style | coding, reviewing | Code conventions |
| testing | coding, testing | TDD and coverage |
| bdd | testing, planning | BDD and AC patterns |
| ... | ... | ... |
```

Note: Use `/inject-standards` to load relevant standards for any task.

### Step 3: Learn the Workflow

Understand the development lifecycle:

```
Workflow Phases:
────────────────────────────────────────────────────────
1. Product Strategy   → /plan-product
2. Shaping           → /shape-spec (creates spec)
3. Design & Stories  → Part of /shape-spec
4. ACs & BDD Tests   → /derive-acs, /generate-bdd-tests
5. Implementation    → Write code to pass BDD tests
6. Verification      → Run tests, verify stories
7. Session End       → /end-session
────────────────────────────────────────────────────────

Session Start: Always run /start-session first!
```

### Step 4: Understand Spec Structure

```
Spec Lifecycle:
────────────────────────────────────────────────────────
Status: in_requirements → in_design → in_progress → complete → archived

Spec Folder:
  SPEC-{NNN}-{slug}/
  ├── README.md      # Scope, context, decisions
  ├── design.md      # Architecture + execution plan
  ├── stories.yml    # Story status (failing/passing)
  └── acs/           # Acceptance criteria per story
      ├── STORY-001-{name}.md
      └── coverage-matrix.md

Key Rule: Agents can only modify story STATUS, not add/remove stories
────────────────────────────────────────────────────────
```

### Step 5: Know the Key Paths

```
Quick Reference:
────────────────────────────────────────────────────────
AGENTS.md                          # Start here
agent-os/
├── product/
│   ├── mission.md                 # Mission, vision, objectives, technical direction
│   └── roadmap.md                 # Current focus, roadmap, blocked, ideas, completed
├── standards/
│   ├── index.yml                  # Standards index
│   └── guardrails.md              # What NOT to do
├── context/
│   ├── sessions/                  # Session summaries
│   └── component-details/         # Implementation knowledge
└── specs/
    ├── index.yml                  # Spec index
    └── SPEC-{NNN}-{slug}/         # Individual specs
────────────────────────────────────────────────────────
```

### Step 6: Run Start Session

Now that you understand the framework, run `/start-session` to:
- Load current priorities
- Check recent session context
- Review active specs and stories
- Determine operating mode

```
Bootstrap complete! Running /start-session to get current context...
```

**Proceed to run `/start-session` now.**

## Tips

- **AGENTS.md is your guide** — When in doubt, re-read it
- **Standards prevent mistakes** — Load them before coding
- **Specs are the source of truth** — Don't deviate without updating the spec
- **Stories track progress** — Update status as you complete work
- **Sessions preserve context** — Run /end-session before stopping
