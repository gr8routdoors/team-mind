---
name: shape-spec
description: Use when starting significant new work that needs requirements, design, and stories — run in plan mode
triggers:
  - "shape spec"
  - "new spec"
  - "new feature"
  - "create spec"
  - "plan feature"
---

# Shape Spec

Gather context and structure planning for significant work. **Run this skill while in plan mode.**

## Important Guidelines

- **Always use AskUserQuestion tool** when asking the user anything
- **Offer suggestions** — Present options the user can confirm, adjust, or correct
- **Keep it lightweight** — This is shaping, not exhaustive documentation

## The Agent Will Rationalize

Before following this process, be aware of these rationalizations that lead to skipping spec creation:

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "This is too simple to need a spec" | Simple features have the most unexamined assumptions. Simplicity is why you skip design, and why bugs ship. | Run the process. Simple features shape fast. |
| "I already know what to build" | You know what you *think* to build. Shaping surfaces what you missed. | Let the process confirm or correct your understanding. |
| "The user described it clearly enough" | Users describe outcomes, not implementation. Gaps between intent and design cause rework. | Shape the spec to bridge intent and implementation. |
| "Writing a spec will slow us down" | Rework from unclear requirements takes 3-10x longer than shaping. | Invest 15 minutes now to save hours of rework. |
| "I can figure out the design while coding" | Designing while coding is expensive. You refactor endlessly because you never thought it through. | Invest in shaping before implementation starts. |

## HARD GATE

⛔ **DO NOT write any implementation code, create any files outside the spec folder, or scaffold any project structure** until the spec's design.md is created and the user has explicitly approved it.

Shaping is for planning, not building. If you feel the urge to "just start coding," that's the rationalization this gate prevents. Design approval first, always.

## Prerequisites

This skill **must be run in plan mode**.

**Before proceeding, check if you are currently in plan mode.**

If NOT in plan mode, **stop immediately** and tell the user:

```
Shape-spec must be run in plan mode. Please enter plan mode first, then run /shape-spec again.
```

Do not proceed with any steps below until confirmed to be in plan mode.

## Process

### Step 1: Clarify What We're Building

Use AskUserQuestion to understand the scope:

```
What are we building? Please describe the feature or change.

(Be as specific as you like — I'll ask follow-up questions if needed)
```

Based on their response, ask 1-2 clarifying questions if the scope is unclear. Examples:
- "Is this a new feature or a change to existing functionality?"
- "What's the expected outcome when this is done?"
- "Are there any constraints or requirements I should know about?"

### Step 2: Gather Visuals

Use AskUserQuestion:

```
Do you have any visuals to reference?

- Mockups or wireframes
- Screenshots of similar features
- Examples from other apps

(Paste images, share file paths, or say "none")
```

If visuals are provided, note them for inclusion in the spec folder.

### Step 3: Identify Reference Implementations

Use AskUserQuestion:

```
Is there similar code in this codebase I should reference?

Examples:
- "The comments feature is similar to what we're building"
- "Look at how src/features/notifications/ handles real-time updates"
- "No existing references"

(Point me to files, folders, or features to study)
```

If references are provided, read and analyze them to inform the plan.

### Step 4: Check Product Context

Check if `agent-os/product/` exists and contains files.

If it exists, read key files (like `mission.md`, `roadmap.md`) and use AskUserQuestion:

```
I found product context in agent-os/product/. Should this feature align with any specific product goals or constraints?

Key points from your product docs:
- [summarize relevant points]

(Confirm alignment or note any adjustments)
```

If no product folder exists, skip this step.

### Step 5: Surface Relevant Standards

Read `agent-os/standards/index.yml` to identify relevant standards based on the feature being built.

Use AskUserQuestion to confirm:

```
Based on what we're building, these standards may apply:

1. **code-style/java** — Java conventions
2. **testing** — TDD principles and coverage
3. **bdd** — Acceptance criteria and BDD test patterns

Should I reference these in the spec? (yes / adjust: remove X, add Y)
```

Note the confirmed standards for inclusion in the README.md.

### Step 6: Generate Spec ID and Folder

Read `agent-os/specs/index.yml` to determine the next spec ID.

Create a folder name using this format:
```
SPEC-{NNN}-{slug}/
```

Where:
- NNN is the next sequential spec number (zero-padded to 3 digits)
- Slug is derived from the feature description (lowercase, hyphens, max 40 chars)

Example: `SPEC-001-user-authentication/`

**Note:** If `agent-os/specs/` doesn't exist, create it along with `index.yml`.

### Step 7: Architectural Design

Before defining acceptance criteria, create a lightweight architectural design document.

Use AskUserQuestion:

```
Before we define acceptance criteria, let's capture the architectural approach.

Key questions:
1. What are the main components/services involved?
2. Are there new API endpoints, data models, or integrations?
3. Are there any performance or scalability considerations?

(Describe the high-level approach, or I can propose one based on reference implementations)
```

Based on their input (or your analysis of references), draft `design.md` covering:
- **Components** — What gets built/modified
- **Data flow** — How data moves through the system
- **API contracts** — New or modified endpoints (if applicable)
- **Data model changes** — Schema changes (if applicable)
- **Integration points** — External systems or services
- **Trade-offs** — Key decisions and their rationale
- **Execution plan** — The implementation tasks

### Step 8: Define Stories

Based on requirements and design, break the spec into discrete stories.

Use AskUserQuestion:

```
Based on our requirements, I've identified these stories:

1. STORY-001: [Story name] — [Brief description]
2. STORY-002: [Story name] — [Brief description]
3. STORY-003: [Story name] — [Brief description]

Does this breakdown look right? (yes / adjust)
```

Each story should be:
- Independently deliverable
- Testable via BDD
- Small enough to complete in a focused session

### Step 9: Derive Acceptance Criteria

With requirements, design, and stories in place, derive acceptance criteria.

Use AskUserQuestion:

```
I'll now derive acceptance criteria for each story.

The ACs will cover:
- Happy path scenarios for each capability
- Edge cases and error handling
- Integration scenarios (if applicable)

Should I proceed with AC derivation? (yes / focus on specific stories: [list])
```

If confirmed, follow the `/derive-acs` workflow to:
1. Generate ACs using Given/When/Then format
2. Create `acs/` directory with AC files named `STORY-{NNN}-{slug}.md`
3. Build coverage matrix

Present the AC summary to the user for review before finalizing.

### Step 10: Verification Planning

Before finalizing, establish how completion will be verified.

Use AskUserQuestion:

```
How should we verify this spec is complete?

Suggested verification:
- [ ] All BDD tests pass
- [ ] Manual smoke test of [key scenario]
- [ ] Code review approved
- [ ] [Any additional criteria]

(Confirm or adjust verification criteria)
```

Add verification criteria to the stories.yml file.

### Step 11: Save Spec Documentation

Present the final structure to the user:

```
Ready to save spec documentation:

agent-os/specs/SPEC-{NNN}-{slug}/
├── README.md      # Scope, context, decisions, references, standards
├── design.md      # Architecture + execution plan
├── stories.yml    # Story status tracking
└── acs/
    ├── STORY-001-{name}.md
    ├── STORY-002-{name}.md
    └── coverage-matrix.md

I'll also update agent-os/specs/index.yml with this spec.

Ready to save? (yes / adjust)
```

### Step 12: Ready for Execution

After saving, present next steps:

```
Spec saved! Next steps:

1. Run `/generate-bdd-tests` to create test scaffolding from ACs
2. Implementation tasks are in design.md → Execution Plan
3. Update stories.yml as stories are completed
4. Run verification steps before marking spec complete

Ready to generate BDD tests? (yes / later)
```

## Output Structure

The spec folder will contain:

```
agent-os/specs/SPEC-{NNN}-{slug}/
├── README.md          # The spec (scope, context, decisions, references)
├── design.md          # Architecture + execution plan
├── stories.yml        # Story status tracking with verification
├── acs/               # Acceptance criteria
│   ├── STORY-001-{name}.md
│   ├── STORY-002-{name}.md
│   └── coverage-matrix.md
└── visuals/           # Mockups, screenshots (if any)
```

## specs/index.yml Content

The master index tracks all specs:

```yaml
# agent-os/specs/index.yml
# Master index of all specs with status

specs:
  SPEC-001:
    name: User Authentication
    status: in_progress    # in_requirements | in_design | in_progress | complete | archived
    created: 2026-02-04
    stories: 3
    stories_complete: 1

  SPEC-002:
    name: Order Processing Rewrite
    status: in_requirements
    created: 2026-02-05
    stories: 0
    stories_complete: 0
```

**Statuses:**
- `in_requirements` — Gathering requirements, shaping scope
- `in_design` — Architectural design phase
- `in_progress` — Implementation underway
- `complete` — All stories pass verification
- `archived` — No longer active (completed or abandoned)

## README.md Content

The README.md consolidates scope, context, and decisions:

```markdown
# SPEC-{NNN}: {Spec Name}

## Overview

[What we're building and why — 2-3 sentences]

## Scope

**In scope:**
- [What's included]

**Out of scope:**
- [What's explicitly excluded]

## Context

**References:**
- `src/auth/legacy/` — Similar authentication pattern
- `src/cache/` — Session caching approach

**Standards:**
- code-style/java — Java conventions
- testing — TDD principles
- bdd — AC format and coverage patterns

**Visuals:**
- [Links to mockups if any, or "None"]

## Decisions

| Decision | Options Considered | Rationale | ADR |
|----------|-------------------|-----------|-----|
| Use Redis for cache | Redis vs EhCache | Distributed invalidation needed | ADR-012 |
| Batch size of 100 | 50, 100, 200 | Balance between latency and throughput | — |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | OAuth2 token validation | passing |
| STORY-002 | Session management | failing |
| STORY-003 | Role-based access control | failing |
```

## design.md Content

The design.md captures architecture AND execution plan:

```markdown
# SPEC-{NNN}: {Spec Name} — Design

## Overview

[Brief description of the architectural approach]

## Components

| Component | Type | Purpose |
|-----------|------|---------|
| TokenValidator | Service | Validates OAuth2 tokens |
| SessionCache | Repository | Redis-backed session storage |

## Data Flow

[Diagram and narrative explanation]

## API Contracts

[Input/output specifications]

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Batch size of 100 | 50, 100, 200 | Balance latency vs throughput |

---

## Execution Plan

Implementation tasks in recommended order:

### Task 1: [Task name]
- [Subtask]
- [Subtask]

**Stories:** STORY-001

### Task 2: [Task name]
...
```

## stories.yml Content

The stories.yml tracks individual story status:

```yaml
# Stories for SPEC-{NNN}
# Agents may only modify 'status' and 'verified_by' fields

stories:
  STORY-001:
    name: OAuth2 token validation
    description: Validate tokens against identity provider
    status: passing        # failing | passing
    verified_by: null      # or "2026-02-04 BDD test suite"

  STORY-002:
    name: Session management
    description: Handle session creation, refresh, and expiry
    status: failing
    verified_by: null

verification:
  criteria:
    - All BDD tests pass
    - Manual smoke test of authentication flow
    - Code review approved
  completed: false
  completed_date: null
```

**Status rules:**
- Agents can ONLY modify `status` and `verified_by` fields
- Stories cannot be added/removed by agents (prevents scope creep)
- `verified_by` should note how/when verification occurred

## Tips

- **Keep shaping fast** — Don't over-document. Capture enough to start, refine as you build.
- **Visuals are optional** — Not every feature needs mockups.
- **Standards guide, not dictate** — They inform the plan but aren't always mandatory.
- **Specs are discoverable** — Months later, someone can find this spec and understand what was built and why.
- **Design informs ACs** — The architectural design helps identify integration scenarios and edge cases.
- **Stories enable parallelism** — Well-defined stories can be worked on independently.
- **Verification prevents false completion** — Don't mark stories passing without running actual verification.
- **Tests drive code** — Implementation works toward passing the generated BDD tests (TDD-style).
