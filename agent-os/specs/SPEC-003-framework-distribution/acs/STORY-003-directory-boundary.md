# STORY-003: Framework/project directory boundary — Acceptance Criteria

## AC-001: Convention documented

**Given** the framework uses a directory-based boundary between framework and project files
**When** the convention is formalized
**Then** a document exists (in AGENTS.md directory map or a dedicated reference) that lists:
- Framework-owned directories (replaced on upgrade): `.claude/skills/agent-os/`, `agent-os/standards/`, `tools/`, `AGENTS.md`, `pyproject.toml`, `uv.lock`
- Project-owned directories (never touched by upgrade): `.claude/skills/{project}/`, `agent-os/product/`, `agent-os/specs/`, `agent-os/context/`, `README.md`
**And** the document explains the rule: custom content goes in project-owned directories, never in framework-owned directories

## AC-002: Existing structure matches convention

**Given** the documented directory boundary convention
**When** the current repo structure is checked
**Then** no project-specific files exist in framework-owned directories
**And** no framework-generic files exist in project-owned directories
**And** if any violations are found, they are relocated as part of this story

## AC-003: AGENTS.md directory map updated

**Given** AGENTS.md has been redesigned (STORY-001)
**When** the directory boundary is formalized
**Then** AGENTS.md includes the boundary convention in its directory structure map
**And** the map clearly marks which directories are framework-owned vs project-owned
