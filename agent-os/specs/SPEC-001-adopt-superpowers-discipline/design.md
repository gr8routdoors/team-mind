# SPEC-001: Adopt Superpowers Discipline Patterns — Design

## Overview

Integrate seven behavioral discipline patterns from the Superpowers framework into Lit SDLC. The changes touch existing skills (modifications), new skills (creation), and new standards (creation). All changes preserve Lit SDLC's existing architecture — no structural changes to the agent-os directory layout or spec/story model.

## Components

| Component | Type | Purpose |
|-----------|------|---------|
| Anti-rationalization sections | Skill modification | Prevent agents from skipping skills |
| verify-completion | New skill | Enforce evidence before completion claims |
| dispatch-subagents | New skill + prompts | Subagent-driven development workflow |
| Hard gates | Skill modification | Block premature progression |
| cso.md | New standard | Rules for writing skill descriptions |
| request-code-review | New skill | Dispatch code review subagents |
| receive-code-review | New skill | Handle review feedback correctly |
| git-worktrees.md | New standard | Branch isolation pattern |

## Data Flow

```
User request → Skill triggered → Anti-rationalization table read first →
  Hard gate check → Process steps → verify-completion before claiming done
```

For subagent workflows:
```
Spec/stories loaded → dispatch-subagents skill →
  Implementer subagent per story → spec-compliance review →
  code-quality review → story marked passing
```

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Rationalization tables placement | Before process, after process, separate file | Before process: agent reads them before starting work |
| Hard gate format | Markdown heading, HTML, custom syntax | `## HARD GATE` heading is simple and visible |
| SDD prompt templates | Inline in skill, separate files | Separate files: easier to maintain, same as Superpowers |
| CSO as tagged standard | Standard with [all] tag, guardrail entry | Standard: enables injection via /inject-standards |

---

## Execution Plan

Implementation tasks in recommended order:

### Task 1: Anti-rationalization sections (STORY-001)
- Add `## The Agent Will Rationalize` section to all 12 existing skills
- Place after overview/purpose, before process steps
- Each table: Rationalization | Why It's Wrong | What To Do Instead
- Tailor rationalizations to each skill's specific purpose

**Stories:** STORY-001

### Task 2: Verify-completion skill (STORY-002)
- Create `.claude/skills/agent-os/verify-completion/SKILL.md`
- Add guardrail GR-P03 to guardrails.md
- Core: identify → run → read → verify → claim

**Stories:** STORY-002

### Task 3: Dispatch-subagents skill (STORY-003)
- Create `.claude/skills/agent-os/dispatch-subagents/SKILL.md`
- Create `implementer-prompt.md`, `spec-reviewer-prompt.md`, `code-quality-reviewer-prompt.md`
- Adapt from Superpowers SDD to use Lit SDLC spec/story/AC system

**Stories:** STORY-003

### Task 4: Hard gates (STORY-004)
- Add `## HARD GATE` sections to shape-spec, derive-acs, generate-bdd-tests, continue-spec
- Each gate: clear blocking condition + what must happen first

**Stories:** STORY-004

### Task 5: CSO standard + audit (STORY-005)
- Create `agent-os/standards/cso.md`
- Update `agent-os/standards/index.yml`
- Audit and fix all 12 skill description fields

**Stories:** STORY-005

### Task 6: Code review skills (STORY-006)
- Create `.claude/skills/agent-os/request-code-review/SKILL.md`
- Create `.claude/skills/agent-os/receive-code-review/SKILL.md`

**Stories:** STORY-006

### Task 7: Git worktrees standard (STORY-007)
- Create `agent-os/standards/git-worktrees.md`
- Update `agent-os/standards/index.yml`
- Add cross-reference in `agent-os/standards/git.md`

**Stories:** STORY-007

### Task 8: Cross-cutting updates
- Update AGENTS.md with new skills
- Update guardrails.md with new guardrails
- Update gaps.md (GAP-001, GAP-006 status)
- Update specs/index.yml
