# Directory Boundary Convention

> Defines which directories are framework-owned (replaced on upgrade) and which are project-owned (never touched).

---

## The Rule

Framework directories are wholly owned by upstream. The `/upgrade-lit` skill deletes and replaces them from the source repo. **Never put project-specific content in framework-owned files or directories** — it will be lost on upgrade.

Project directories are never touched by upgrade. All project-specific content — product docs, specs, session history, build commands, tech stack — lives here.

Rollback after upgrade is `git checkout` — the upgrade only runs on a clean working directory, so the previous commit preserves the pre-upgrade state.

---

## Framework-Owned

Replaced wholesale on `/upgrade-lit`. Do not put project content here.

| Path | Contains |
|------|----------|
| `AGENTS.md` | Generic boot loader — workflow, directory map, discovery pointers |
| `.claude/skills/agent-os/` | Framework skills (start-session, shape-spec, etc.) |
| `agent-os/standards/*.md` | Framework standards (root-level files only) |
| `agent-os/standards/code-style/` | Language-specific style guides (java.md, go.md) |
| `tools/` | Framework Python tools |
| `pyproject.toml` | Package config |
| `uv.lock` | Dependency lockfile |

---

## Project-Owned

Never touched by `/upgrade-lit`. All project customization goes here.

| Path | Contains |
|------|----------|
| `CLAUDE.md` | Claude Code configuration |
| `README.md` | Project README |
| `.claude/skills/{project}/` | Project-specific skills |
| `agent-os/standards/project/` | Project-specific standards (build commands, test commands, tech stack) |
| `agent-os/product/` | Mission, roadmap, domain docs |
| `agent-os/specs/` | Specifications and stories |
| `agent-os/context/` | Architecture, components, sessions |

---

## Project Standards

`agent-os/standards/project/` is the project-owned subdirectory within standards. It holds project-specific conventions that `/inject-standards` discovers alongside framework standards.

Common project standards:

| File | Purpose |
|------|---------|
| `project/build.md` | Build commands and prerequisites |
| `project/testing.md` | Test commands for each component |
| `project/tech-stack.md` | Approved technologies and infrastructure |

Add any project-specific conventions here. Framework standards may reference these files but must not inline their content.

---

## Guidance for Agents

- **Writing a project-specific standard?** Put it in `agent-os/standards/project/`.
- **Writing a project-specific skill?** Put it in `.claude/skills/{project}/`.
- **Need build commands or test commands?** Check `agent-os/standards/project/build.md` and `project/testing.md`.
- **Never modify framework files** with project-specific content. The next upgrade will overwrite your changes.

---

_Last updated: 2026-02-15_
