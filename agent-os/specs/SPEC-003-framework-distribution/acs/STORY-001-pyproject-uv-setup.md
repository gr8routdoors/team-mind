# STORY-001: pyproject.toml + UV setup — Acceptance Criteria

## AC-001: Valid pyproject.toml

**Given** the lit-sdlc repository
**When** `pyproject.toml` is created at the repo root
**Then** it defines the project name, version, and Python version requirement (3.11+)
**And** it configures UV as the package manager
**And** it defines `tools/` as the package source
**And** `uv sync` succeeds without errors

## AC-002: Core dependencies

**Given** a valid `pyproject.toml`
**When** dependencies are defined
**Then** core dependencies include: PyYAML, python-frontmatter, Click
**And** dev dependencies include: pytest, ruff
**And** all dependencies resolve and install via `uv sync`

## AC-003: Tools directory structure

**Given** the `tools/` directory exists
**Then** it contains `__init__.py`
**And** scripts are importable as Python modules
**And** scripts are runnable via `uv run python -m tools.<script_name>` or `uv run <cli_command>`
