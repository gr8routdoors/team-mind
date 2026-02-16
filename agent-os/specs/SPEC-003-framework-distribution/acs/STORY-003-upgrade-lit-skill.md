# STORY-003: /upgrade-lit skill — Acceptance Criteria

## AC-001: Pre-upgrade safety

**Given** the user runs `/upgrade-lit`
**When** the skill starts
**Then** it checks for uncommitted changes in the working directory
**And** if uncommitted changes exist, it warns the user and aborts — the user must commit or stash before upgrading
**And** if the working directory is clean, it shows the list of framework directories that will be replaced
**And** the user must confirm before any files are modified

## AC-002: Custom file detection

**Given** the user runs `/upgrade-lit`
**When** the skill scans framework directories before replacing
**Then** it identifies any files that don't appear in the upstream version of those directories
**And** warns the user: "These files exist in framework directories but aren't in upstream — they will be deleted"
**And** gives the user the option to move them to a project-owned location before proceeding

## AC-003: Nuke-and-replace execution

**Given** the user confirms the upgrade
**When** the skill executes
**Then** it replaces framework-owned paths from upstream:
- `.claude/skills/agent-os/` — deleted and replaced
- `agent-os/standards/*.md` — root-level files deleted and replaced
- `agent-os/standards/code-style/` — deleted and replaced
- `agent-os/standards/index.yml` — merged (see below)
- `AGENTS.md` — replaced
**And** it does NOT touch project-owned paths:
- `agent-os/standards/project/` — preserved
- `.claude/skills/{project}/` — preserved
- `agent-os/product/`, `agent-os/specs/`, `agent-os/context/` — preserved
- `CLAUDE.md`, `README.md` — preserved
**And** for `index.yml`, it merges rather than replaces:
- Framework entries (no `project_owned` flag) are replaced with upstream versions
- Project entries (`project_owned: true`) are preserved from the local file
- New framework entries from upstream are added

> **Note:** Python tooling paths (`tools/`, `pyproject.toml`, `uv.lock`, `uv sync`) are out of scope for this story. They will be addressed in STORY-004 (Python tooling) and the upgrade skill updated accordingly.

## AC-004: Post-upgrade report

**Given** the upgrade has completed
**When** the skill presents results
**Then** it shows a summary: files added, files removed, files changed
**And** suggests the user review the diff with `git diff HEAD~1`
**And** reminds the user they can roll back with `git checkout HEAD~1 -- .` if needed

## AC-005: Upstream source configuration

**Given** the user runs `/upgrade-lit`
**When** the skill needs to fetch upstream files
**Then** it reads the Lit SDLC upstream repo URL from a default configured in the skill (can be overridden by the user)
**And** performs a shallow clone (`git clone --depth 1`) to a temp directory to get the latest framework files
**And** fetches from the default branch (`main`), which the user can override
**And** cleans up the temp directory after the upgrade completes
