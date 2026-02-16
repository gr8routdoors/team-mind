# STORY-004: /upgrade skill — Acceptance Criteria

## AC-001: Pre-upgrade safety

**Given** the user runs `/upgrade`
**When** the skill starts
**Then** it shows the current framework state (list of framework directories that will be replaced)
**And** checks for uncommitted changes and prompts the user to commit or stash first
**And** auto-commits the current state with a message like `chore: pre-upgrade snapshot` so `git checkout` is a clean rollback path
**And** the user must confirm before any files are modified

## AC-002: Custom file detection

**Given** the user runs `/upgrade`
**When** the skill scans framework directories before replacing
**Then** it identifies any files that don't appear in the upstream version of those directories
**And** warns the user: "These files exist in framework directories but aren't in upstream — they will be deleted"
**And** gives the user the option to move them to a project-owned location before proceeding

## AC-003: Nuke-and-replace execution

**Given** the user confirms the upgrade
**When** the skill executes
**Then** it deletes the contents of framework-owned directories (`.claude/skills/agent-os/`, `agent-os/standards/`, `tools/`)
**And** copies the latest versions from the upstream repository
**And** replaces `AGENTS.md`, `pyproject.toml`, and `uv.lock`
**And** runs `uv sync` to install any new or changed dependencies
**And** does NOT touch any project-owned directories

## AC-004: Post-upgrade report

**Given** the upgrade has completed
**When** the skill presents results
**Then** it shows a summary: files added, files removed, files changed
**And** suggests the user review the diff with `git diff HEAD~1`
**And** reminds the user they can roll back with `git checkout HEAD~1 -- .` if needed

## AC-005: Upstream source configuration

**Given** the user runs `/upgrade`
**When** the skill needs to fetch upstream files
**Then** it reads the upstream repo URL from a known location (e.g., a setting in the project config or a default GitHub URL)
**And** fetches files from the default branch (e.g., `main`)
**And** the user can override the branch or tag if needed
