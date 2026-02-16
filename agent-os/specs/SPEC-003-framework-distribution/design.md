# SPEC-003: Framework Tooling & Upgrade — Design

## Overview

Three changes that make Lit SDLC maintainable: a generic AGENTS.md, a formalized directory boundary, and a nuke-and-replace upgrade skill. The key insight is that framework files and project files are separated by directory — upgrade replaces framework directories wholesale rather than diffing individual files.

## Components

| Component | Type | Purpose |
|-----------|------|---------|
| `AGENTS.md` | Config | Generic boot loader — framework workflow, directory map, pointer to project config |
| `/upgrade-lit` skill | Skill (SKILL.md) | Replace framework directories from upstream |

## Directory Boundary

The framework/project boundary is defined by directory location, not by a manifest or metadata:

```
Framework-owned (replaced on upgrade):
  .claude/skills/agent-os/       ← framework skills
  agent-os/standards/*.md        ← framework standards (root-level files)
  agent-os/standards/code-style/ ← framework language guides
  AGENTS.md                      ← generic boot loader

Project-owned (never touched by upgrade):
  .claude/skills/{project}/      ← project-specific skills
  agent-os/standards/project/    ← project-specific standards (build commands, tech stack, etc.)
  agent-os/product/              ← mission, roadmap, domain docs
  agent-os/specs/                ← project specs and stories
  agent-os/context/              ← sessions, component details
  README.md                      ← project README
```

This convention means:
- **Custom skills go in `.claude/skills/{project}/`**, not in `.claude/skills/agent-os/`
- **Project-specific standards go in `agent-os/standards/project/`**, not in root-level standards files. This includes build commands, test commands, tech stack, and any other project-specific conventions.
- Framework standards files (root-level `.md` files in `agent-os/standards/`) are templates that may reference project standards but must not contain project-specific content themselves.
- Upgrade can safely replace framework directories because project files are never there.

## Data Flow

### Upgrade flow
```
/upgrade-lit → check for uncommitted changes (abort if dirty) → shallow clone upstream to temp dir → scan for custom files → show what will be replaced → confirm with user → delete framework paths → copy from temp dir → merge index.yml → clean up temp dir → report what changed
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
| Abort if dirty | Auto-commit vs abort-if-dirty vs no check | Abort if uncommitted changes exist. Auto-committing user work risks damage; aborting is safe and the user can commit or stash themselves. Rollback after upgrade is `git checkout` on the upgrade commit. |
| Project standards in `standards/project/` | Subdirectory vs separate top-level dir vs inline in framework files | Keeps all standards co-located for `/inject-standards` discovery. Subdirectory is project-owned and excluded from upgrade. Framework template files must not contain project content — it gets nuked on upgrade. |
| `index.yml` merge on upgrade | Nuke-and-replace vs split into two files vs merge by `project_owned` flag | Single index file with `project_owned: true` flag on project entries. Upgrade replaces framework entries and preserves project entries. Avoids split-file complexity; users add standards the same way framework does. |

---

## Execution Plan

### Task 1: AGENTS.md redesign
- Strip all project-specific content from AGENTS.md
- Keep: framework workflow description, directory structure map, skill discovery instructions, "run /start-session"
- Add: pointer to `agent-os/product/` for project context
- Add: pointer to `.claude/skills/{project}/` for project-specific skills
- Document the new format so downstream projects know what to customize where

**Stories:** STORY-001

### Task 2: Directory boundary convention
- Create `agent-os/standards/directory-boundary.md` documenting the convention
- Create `agent-os/standards/project/` as the project-owned standards directory
- Relocate project-specific placeholder content (build commands, test commands, tech stack) from framework files into `standards/project/`
- Clean framework files: replace inlined project sections with pointers to `standards/project/`
- Update AGENTS.md directory map to include `standards/project/` as project-owned
- Update `standards/index.yml` with new entries
- Verify no project-specific content remains in framework-owned files

**Stories:** STORY-002

### Task 3: /upgrade-lit skill
- Create `.claude/skills/agent-os/upgrade-lit/SKILL.md`
- CSO-compliant description, anti-rationalization table
- Process: check for uncommitted changes (abort if dirty) → show what will be replaced → confirm with user → delete framework directories → copy from upstream repo → report changes → suggest reviewing diff with `git diff HEAD~1`
- If custom files detected in framework directories, warn before deleting

**Stories:** STORY-003

---

## Future Work (Deferred)

The following were originally part of this spec and are deferred to a future spec:

- **Python tooling foundation** — `pyproject.toml`, UV, `tools/` directory, Click CLI. Deferred until first Python tool is needed (YAGNI). When added, `/upgrade-lit` will be updated to handle these paths.
- **Framework manifest** — Hash-based file tracking for validation and contribution workflows
- **Validator scripts** — `validate_standards.py`, `validate_install.py`, `parse_session.py`
- **`/contribute-upstream` skill** — Package local enhancements for upstream PR
- **Version tagging** — Semantic versioning, changelog generation
- **`/clean-install` skill** — Fresh adoption experience for new projects
- **`/onboard-project` skill** — Brownfield content ingestion
- **Getting started guide** — User-facing walkthrough
