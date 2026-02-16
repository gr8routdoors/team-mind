# SPEC-003: Framework Tooling & Upgrade

## Overview

Make AGENTS.md a generic boot loader, formalize the framework-vs-project directory boundary, build an upgrade skill that replaces framework files from upstream, and create a minimal PR creation skill that enforces conventional commit format. These four changes make Lit SDLC maintainable for projects that are already using it.

## Scope

**In scope:**
- Minimal AGENTS.md redesign (generic boot loader, project content discovered not inlined)
- Framework/project directory boundary convention (formalized and documented)
- `/upgrade-lit` skill (nuke-and-replace framework directories from upstream)
- `/create-pr` skill (minimal PR creation with conventional commit titles)

**Out of scope (deferred to future spec):**
- Python tooling foundation (pyproject.toml, UV, tools/ directory) — deferred until first Python tool is needed (YAGNI)
- Framework manifest with file hashes (not needed for nuke-and-replace upgrade)
- Validator scripts (standards index, install validation)
- `/contribute-upstream` skill
- Version tagging and changelog
- `/clean-install` skill (fresh adoption experience)
- `/onboard-project` skill (brownfield content ingestion)
- Getting started guide

## Context

**References:**
- `AGENTS.md` — Current format to be redesigned as generic boot loader
- `.claude/skills/agent-os/` — Framework-owned skills directory
- `.claude/skills/{project}/` — Project-owned skills directory (convention)
- `agent-os/standards/` — Framework-owned standards
- `agent-os/standards/project/` — Project-owned standards (build commands, tech stack, etc.)
- `agent-os/product/` — Project-owned content (never touched by upgrade)
- `agent-os/specs/` — Project-owned specs (never touched by upgrade)

**Standards:**
- guardrails — Anti-patterns and unattended mode rules
- cso — Skill description rules
- git — Commit and branch conventions
- best-practices — SOLID, YAGNI principles

**Visuals:** None

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Directory boundary over manifest | Directory convention vs manifest file vs git submodule | Directory separation makes framework files obvious by location; upgrade becomes nuke-and-replace with no diffing or merge logic needed |
| Nuke-and-replace upgrade | Nuke-and-replace vs diff-and-merge vs manifest-based three-way merge | Framework directories are wholly owned by upstream — no project files live there. Nuke-and-replace is simple, eliminates stale files after refactors, and avoids all merge complexity. Rollback is just `git checkout`. |
| AGENTS.md as generic boot loader | Generic vs project-specific | Generic AGENTS.md is a framework file that can be upgraded like any other. Project-specific config lives in a known location that AGENTS.md points to. |
| Project standards in `standards/project/` | Subdirectory vs separate top-level dir vs inline in framework files | Keeps all standards co-located for `/inject-standards` discovery. Project-owned subdirectory excluded from upgrade. Framework files must not contain project content. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | Minimal AGENTS.md redesign | passing |
| STORY-002 | Framework/project directory boundary | passing |
| STORY-003 | /upgrade-lit skill | passing |
| STORY-004 | /create-pr skill | passing |
