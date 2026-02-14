# SPEC-002: Developer Workflow — Design

## Overview

Two new skills (/commit, /ship-pr) that complete the development pipeline. They are standalone tools invoked explicitly by the developer or agent — not wired into the mainline SDLC pipeline.

## Components

| Component | Type | Purpose |
|-----------|------|---------|
| `/commit` skill | Skill (SKILL.md) | Context-aware git commit creation |
| `/ship-pr` skill | Skill (SKILL.md) | PR creation from Lit SDLC artifacts |

## Data Flow

1. Agent completes work on a story
2. Developer (or agent) runs `/commit` — reads active spec/story context, stages changes, builds conventional commit message, presents for approval, stamps commit
3. (If team repo) Developer runs `/ship-pr` — reads commit messages + spec artifacts, assembles PR description, creates PR or presents for approval

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Commit message always presented for review | Always review vs auto-commit option | Default to review for safety; auto-commit may be enabled by future operating profiles |
| /ship-pr depends on /commit | Integrated vs independent | /ship-pr calls /commit first if uncommitted changes exist; avoids duplicate logic |
| Not wired into mainline pipeline | Automatic after /verify-completion vs explicit invocation | Committing and shipping are deliberate actions; automatic coupling is too opinionated for diverse workflows |

---

## Execution Plan

### Task 1: /commit skill
- Create `.claude/skills/agent-os/commit/SKILL.md`
- CSO-compliant description (triggering conditions only)
- Anti-rationalization table
- Process: detect changes → read spec/story context → build conventional commit message → selective staging → present for review → commit
- Follow git.md standards for commit format

**Stories:** STORY-001

### Task 2: /ship-pr skill
- Create `.claude/skills/agent-os/ship-pr/SKILL.md`
- CSO-compliant description
- Anti-rationalization table
- Process: check for uncommitted changes (call /commit if needed) → read spec/story/ACs → build PR title and description → git hygiene → create PR
- Link PR to spec artifacts

**Stories:** STORY-002

---

## Future: Operating Profiles

See `future-profiles.md` for how operating profiles (full/team/lean) will layer additional behavior on top of these skills. Both `/commit` and `/ship-pr` are designed to work fully without profiles.
