# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## Our Standards

Standards are stored in `agent-os/standards/` and indexed in `agent-os/standards/index.yml`.

### Loading Standards

Use the `/inject-standards` skill to load relevant standards for your current task. This reads `agent-os/standards/index.yml` and injects applicable conventions.

### Key Standards Files

| File | Purpose |
|------|---------|
| `standards/index.yml` | Index of all standards with tags |
| `standards/guardrails.md` | What NOT to do — anti-patterns and lessons learned |
| `standards/code-style.md` | Code conventions and patterns |
| `standards/testing.md` | Testing requirements and patterns |

### Standards vs Skills

- **Standards** = Declarative conventions ("API responses use this format")
- **Skills** = Procedural workflows ("How to create a feature spec")
- Skills can reference standards for best of both worlds

## Workflow

Workflows are implemented as skills in `.claude/skills/agent-os/`. Each skill is a directory containing a `SKILL.md` file with YAML frontmatter for metadata and triggers.

### Getting Started

**First time on this project?**
- Terminal: Run `./scripts/init.sh` to verify environment
- LLM session: Run `/bootstrap` to learn about Agent OS

**Returning?**
- Run `/start-session` at the beginning of every session

### Operating Mode

Before starting work, determine your mode:
- **Interactive**: Devon is present — ask questions, iterate, move fast
- **Unattended**: Working autonomously — be conservative, document everything, flag decisions

For unattended work, review `standards/guardrails.md` — Unattended Mode section (GR-U01–U06).

### Workflow by Phase

| Phase | Skill | When to Use |
|-------|-------|-------------|
| Session Start | `/start-session` | **Always run first** — loads priorities, context, spec status |
| First Time | `/bootstrap` | New agent onboarding — learn Agent OS |
| Product Strategy | `/plan-product` | Roadmap, priorities, strategic planning |
| Shaping | `/shape-spec` | New feature or significant change (creates spec) |
| Acceptance Criteria | `/derive-acs` | Generate ACs from requirements (standalone) |
| BDD Tests | `/generate-bdd-tests` | Transform ACs into test scaffolding |
| Continuing Work | `/continue-spec` | Resume work on existing spec |
| Investigation | `/investigate` | Bugs, performance, understanding behavior |
| End of Session | `/end-session` | Context preservation, session summary |

Before implementation, run `/inject-standards` to load applicable conventions.

### Quick Start for New Sessions

1. **Run `/start-session`** — This orients you to current priorities and active work
2. Pick the appropriate workflow skill based on the task
3. At session end, run `/end-session` to preserve context

## Repository Overview

This is the Agent OS framework — a structured approach for AI-assisted software development. Agent OS provides workflows, standards, and context management for effective collaboration between AI agents and developers.

**Architecture**: Adaptable to your project's architecture. Commonly used with microservices, monoliths, and hybrid systems.

## Planning Artifacts

All planning artifacts live in `agent-os/`:

### Product (`agent-os/product/`)

| Path | Purpose |
|------|---------|
| `product/mission.md` | Mission, vision, objectives, technical direction |
| `product/roadmap.md` | Current focus, feature roadmap, blocked items, ideas, completed |
| `product/domain/` | Domain knowledge (business concepts, rules, terminology) |
| `product/capabilities/` | Service capability documentation |

### Context (`agent-os/context/`)

| Path | Purpose |
|------|---------|
| `context/architecture/` | System architecture docs and ADRs |
| `context/component-details/` | Per-component implementation knowledge |
| `context/sessions/` | Session summaries with learnings |

### Specifications (`agent-os/specs/`)

| Path | Purpose |
|------|---------|
| `specs/index.yml` | Master index of all specs with status |
| `specs/SPEC-{NNN}-{slug}/` | Individual spec folders |
| `specs/_archive/` | Completed or abandoned specs |

**Spec Structure:**
```
SPEC-001-feature-name/
├── README.md      # Scope, context, decisions, references
├── design.md      # Architecture + execution plan
├── stories.yml    # Story status (failing/passing)
└── acs/           # Acceptance criteria per story
    ├── STORY-001-{name}.md
    └── coverage-matrix.md
```

**Spec Statuses:** `in_requirements` → `in_design` → `in_progress` → `complete` → `archived`

**Story Rules:** Agents can only modify story `status` field — cannot add/remove stories (prevents scope creep)

### Skills (`.claude/skills/agent-os/`)

Each skill is a directory with a `SKILL.md` file:

| Skill | Purpose |
|-------|---------|
| `start-session/` | **Run first** — Session startup ritual, loads context |
| `bootstrap/` | New agent onboarding — learn Agent OS framework |
| `shape-spec/` | Create new spec (requirements → design → stories → ACs) |
| `continue-spec/` | Resume work on existing spec |
| `derive-acs/` | Generate acceptance criteria from requirements |
| `generate-bdd-tests/` | Transform ACs into BDD test scaffolding (Go/Java) |
| `investigate/` | Investigate bugs, performance, or behavior |
| `end-session/` | Context preservation at session end |
| `plan-product/` | Strategic product planning |
| `inject-standards/` | Load relevant standards for current task |
| `discover-standards/` | Extract standards from codebase patterns |
| `index-standards/` | Rebuild standards index

## Project Structure

_Configure this section for your project's structure. Example:_

- `services/`: Backend microservices
  - `core-service/`: Main business logic service
  - `data-service/`: Database operations
  - `api-gateway/`: API routing and aggregation
- `ux/`: Frontend applications
  - `admin-ui/`: Administrative interface
  - `client-app/`: Customer-facing application

## Common Development Commands

### Building Services

// TODO: Add commands here for building your components

### Testing
// TODO: Add commands here for testing your components

## Key Architecture Patterns

// TODO: Describe your architecture patterns here

## Development Environment Setup

### Quick Setup

// TODO: Add quick dev enviornment setup here

### Prerequisites

// TODO: Add setup prerequisites here


## Testing Patterns

// TODO: Add testing patterns here