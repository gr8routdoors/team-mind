# SPEC-001: Adopt Superpowers Discipline Patterns

## Overview

Adopt behavioral discipline patterns from the Superpowers framework to strengthen Lit SDLC's agent enforcement capabilities. Lit SDLC excels at structured knowledge (product context, standards, specs, session memory) but lacks mechanisms to prevent AI agents from cutting corners. This spec adds anti-rationalization engineering, verification enforcement, subagent-driven development, hard gates, CSO compliance, code review workflows, and git worktree isolation.

## Scope

**In scope:**
- Anti-rationalization sections in all existing skills
- New verify-completion skill
- New dispatch-subagents skill with prompt templates
- Hard gates in key workflow skills
- CSO (Claude Search Optimization) standard + skill description audit
- Code review skills (request + receive)
- Git worktrees standard

**Out of scope:**
- Rewriting existing skill logic
- Changing the spec/story data model
- Adding hook-based session initialization (Superpowers-specific)
- Plugin packaging system

## Context

**References:**
- `../../../superpowers/` — Superpowers framework (cloned repo)
- `../../../superpowers/skills/verification-before-completion/SKILL.md` — Verification pattern
- `../../../superpowers/skills/subagent-driven-development/SKILL.md` — SDD workflow
- `../../../superpowers/skills/test-driven-development/SKILL.md` — Anti-rationalization example

**Standards:**
- guardrails — Will be updated with new guardrails
- best-practices — YAGNI/TDD principles inform design
- testing — Verification enforcement touches testing
- bdd — ACs in Given/When/Then format

**Visuals:** None

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Add rationalization tables vs. inline warnings | Tables, inline prose, separate files | Tables are scannable and match Superpowers' proven pattern |
| Hard gate syntax | `## HARD GATE`, `## WARNING`, custom emoji | `## HARD GATE` with clear blocking language for maximum visibility |
| CSO as standard vs. guardrail | Standard file, guardrail entry, both | Standard file enables indexing and selective injection |
| Adapt SDD vs. copy directly | Direct copy, full adaptation, hybrid | Full adaptation to use Lit SDLC specs/stories instead of plan.md |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | Anti-rationalization sections in all skills | failing |
| STORY-002 | Verify-completion skill | failing |
| STORY-003 | Dispatch-subagents skill | failing |
| STORY-004 | Hard gates in workflow skills | failing |
| STORY-005 | CSO standard + description audit | failing |
| STORY-006 | Code review skills | failing |
| STORY-007 | Git worktrees standard | failing |
