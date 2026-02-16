# SPEC-003: Framework Tooling & Upgrade — Design

## Overview

Four changes that make Lit SDLC maintainable: a generic AGENTS.md, Python tooling, a formalized directory boundary, and a nuke-and-replace upgrade skill. The key insight is that framework files and project files are separated by directory — upgrade replaces framework directories wholesale rather than diffing individual files.

## Components

| Component | Type | Purpose |
|-----------|------|---------|
| `AGENTS.md` | Config | Generic boot loader — framework workflow, directory map, pointer to project config |
| `pyproject.toml` | Config | UV package management, project metadata |
| `tools/` | Python package | Framework utility scripts (CLI via Click) |
| `/upgrade` skill | Skill (SKILL.md) | Replace framework directories from upstream |

## Directory Boundary

The framework/project boundary is defined by directory location, not by a manifest or metadata:

```
Framework-owned (replaced on upgrade):
  .claude/skills/agent-os/       ← framework skills
  agent-os/standards/            ← framework standards
  tools/                         ← framework Python tools
  AGENTS.md                      ← generic boot loader
  pyproject.toml                 ← package config
  uv.lock                        ← dependency lockfile

Project-owned (never touched by upgrade):
  .claude/skills/{project}/      ← project-specific skills
  agent-os/product/              ← mission, roadmap, domain docs
  agent-os/specs/                ← project specs and stories
  agent-os/context/              ← sessions, component details
  README.md                      ← project README
```

This convention means:
- **Custom skills go in `.claude/skills/{project}/`**, not in `agent-os/`
- **Project-specific standards** (if any) go in a project-owned location, not in `agent-os/standards/`
- Upgrade can safely nuke framework directories because project files are never there

## Data Flow

### Upgrade flow
```
/upgrade → confirm with user → git commit current state → delete framework directories → copy from upstream → uv sync → report what changed
```

### AGENTS.md discovery
```
Agent reads AGENTS.md → sees directory structure → reads project config from agent-os/product/ → discovers project skills from .claude/skills/{project}/ → ready to work
```

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Directory boundary over manifest | Directory convention vs manifest file vs git submodule | Directory separation makes ownership obvious by location; no metadata to maintain |
| Nuke-and-replace upgrade | Nuke-and-replace vs diff-and-merge vs three-way merge | Framework directories are wholly owned by upstream. Nuke-and-replace is simple, eliminates stale files after refactors, and has zero merge complexity. Rollback is `git checkout`. |
| AGENTS.md as framework file | Framework-owned vs project-owned | Generic AGENTS.md can be upgraded like any other framework file. Project config is discovered from known locations, not inlined in AGENTS.md. |
| Pre-upgrade commit | Auto-commit vs manual commit vs no commit | Auto-commit before upgrade ensures `git checkout` is a clean rollback path. User confirms before proceeding. |

---

## Execution Plan

### Task 1: AGENTS.md redesign
- Strip all project-specific content from AGENTS.md
- Keep: framework workflow description, directory structure map, skill discovery instructions, "run /start-session"
- Add: pointer to `agent-os/product/` for project context
- Add: pointer to `.claude/skills/{project}/` for project-specific skills
- Document the new format so downstream projects know what to customize where

**Stories:** STORY-001

### Task 2: Python tooling foundation
- Create `pyproject.toml` with UV configuration
- Create `tools/__init__.py` and package structure
- Add core dependency: Click (CLI interfaces for framework tools)
- Add dev dependencies (pytest, ruff)
- Commit `uv.lock` for reproducible installs

**Stories:** STORY-002

### Task 3: Directory boundary convention
- Document the framework-owned vs project-owned directory convention
- Ensure existing directory structure matches the convention
- Add convention to AGENTS.md directory map
- Verify no project files live in framework directories and vice versa

**Stories:** STORY-003

### Task 4: /upgrade skill
- Create `.claude/skills/agent-os/upgrade/SKILL.md`
- CSO-compliant description, anti-rationalization table
- Process: show current vs upstream version → confirm with user → auto-commit current state → delete framework directories → copy from upstream repo → run `uv sync` → report changes → suggest reviewing diff with `git diff HEAD~1`
- User can opt out of any directory (e.g., keep local standards)
- If custom files detected in framework directories, warn before deleting

**Stories:** STORY-004

---

## Future Work (Deferred)

The following were originally part of this spec and are deferred to a future spec:

- **Framework manifest** — Hash-based file tracking for validation and contribution workflows
- **Validator scripts** — `validate_standards.py`, `validate_install.py`, `parse_session.py`
- **`/contribute-upstream` skill** — Package local enhancements for upstream PR
- **Version tagging** — Semantic versioning, changelog generation
- **`/clean-install` skill** — Fresh adoption experience for new projects
- **`/onboard-project` skill** — Brownfield content ingestion
- **Getting started guide** — User-facing walkthrough
