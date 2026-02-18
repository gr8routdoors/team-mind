# AGENTS.md

> This file is framework-owned and replaced on `/upgrade-lit`.
> Project-specific context lives in `agent-os/product/` — not here.

## Getting Started

**ALWAYS run `/start-session` first.** No exceptions. This loads priorities, recent context, and active specs before any work begins.

If `/start-session` finds no framework content (no roadmap, no specs, no sessions), run `/bootstrap` to set up the project.

**When asked to build or implement a spec**, read and follow the `/dispatch-subagents` skill once you've finished running /start-session. Do NOT implement stories yourself — dispatch subagents per story with two-stage review.

## Workflow

| Phase | Skill | When to Use |
|-------|-------|-------------|
| Session Start | `/start-session` | **ALWAYS run first** — loads priorities, context, spec status |
| Implementation | `/dispatch-subagents` | **Build/implement a spec** — dispatch subagents per story |
| Product Strategy | `/plan-product` | Roadmap, priorities, strategic planning |
| Shaping | `/shape-spec` | New feature or significant change (creates spec) |
| Acceptance Criteria | `/derive-acs` | Generate ACs from requirements (standalone) |
| BDD Tests | `/generate-bdd-tests` | Transform ACs into test scaffolding |
| Code Review | `/request-code-review` | Two-stage review (spec compliance + code quality) |
| Review Feedback | `/receive-code-review` | Handle review feedback with technical rigor |
| Continuing Work | `/continue-spec` | Resume work on existing spec |
| Investigation | `/investigate` | Bugs, performance, understanding behavior |
| Standards | `/inject-standards` | Load applicable conventions before implementation |
| Verification | `/verify-completion` | **Before ANY completion claim** — evidence before assertions |
| Onboarding | `/bootstrap` | New project with no framework content |
| End of Session | `/end-session` | Context preservation, session summary |

## Directory Structure

```
Framework-owned (replaced on /upgrade-lit):
  AGENTS.md                          # This file
  .claude/skills/agent-os/           # Framework skills
  agent-os/standards/*.md            # Framework standards (root-level files)
  agent-os/standards/code-style/     # Language-specific guides

Project-owned (never touched by /upgrade-lit):
  CLAUDE.md                          # Claude Code configuration
  README.md                          # Project README
  .claude/skills/{project}/          # Project-specific skills
  agent-os/standards/project/        # Project-specific standards
  agent-os/product/                  # Mission, roadmap, domain docs
  agent-os/specs/                    # Specifications and stories
  agent-os/context/                  # Architecture, components, sessions
```

## Project Context

Project-specific information is discovered from these locations:

| What | Where |
|------|-------|
| Mission & roadmap | `agent-os/product/` |
| Domain knowledge | `agent-os/product/domain/` |
| Architecture & decisions | `agent-os/context/architecture/` |
| Component details | `agent-os/context/component-details/` |
| Active specs | `agent-os/specs/index.yml` |
| Session history | `agent-os/context/sessions/` |
| Build commands & prerequisites | `agent-os/standards/project/build.md` |
| Test commands | `agent-os/standards/project/testing.md` |
| Tech stack | `agent-os/standards/project/tech-stack.md` |
| Directory boundary convention | `agent-os/standards/directory-boundary.md` |

## Skill Discovery

Framework skills live in `.claude/skills/agent-os/`. Project-specific skills live in `.claude/skills/{project}/`. Each skill directory contains a `SKILL.md` with instructions and triggers.
