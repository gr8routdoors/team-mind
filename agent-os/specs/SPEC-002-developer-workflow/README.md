# SPEC-002: Developer Workflow

## Overview

Build the skills that complete the implementation pipeline: structured git commits and PR creation from Lit SDLC artifacts. These skills close the gap between "verification passes" and "work is shipped."

## Scope

**In scope:**
- `/commit` skill — context-aware conventional commits from Lit SDLC context
- `/ship-pr` skill — PR assembly from spec/story/AC artifacts

**Out of scope:**
- Operating profiles (see `future-profiles.md` for vision)
- Auto-merge behavior (future, requires CI integration)
- GitHub Actions or CI/CD integration
- Pipeline integration (automatic `/commit` after `/verify-completion`) — future work

## Context

**References:**
- `agent-os/standards/git.md` — Conventional commit format, branch naming
- `agent-os/standards/git-worktrees.md` — Branch isolation patterns

**Standards:**
- guardrails — Anti-patterns and unattended mode rules
- cso — Skill description rules
- git — Commit and branch conventions
- best-practices — SOLID, YAGNI principles

**Visuals:** None

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| /commit as standalone skill | Standalone vs embedded in /ship-pr | Standalone is usable for personal repos without PRs; /ship-pr calls /commit when needed |
| Commit message from Lit SDLC context | From context vs manual vs template | Context-aware messages are the whole point — spec/story/changes inform the message automatically |
| Profile behavior deferred | Now vs later | Profiles are an enhancement layer; /commit and /ship-pr work fully without them. See `future-profiles.md`. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | /commit skill | passing |
| STORY-002 | /ship-pr skill | failing |
