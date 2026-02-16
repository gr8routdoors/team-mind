# STORY-002: pyproject.toml + UV setup — Acceptance Criteria

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
**Then** core dependencies include: Click (for CLI interfaces on framework tools)
**And** dev dependencies include: pytest, ruff
**And** all dependencies specify version lower bounds (e.g., `click>=8.0`)
**And** `uv.lock` is committed to the repo for reproducible installs
**And** all dependencies resolve and install via `uv sync`

> **Note:** PyYAML and python-frontmatter are intentionally excluded. The LLM reads and writes YAML/frontmatter natively — Python tools handle deterministic operations (hashing, diffing, validating structure) that don't require YAML parsing. Additional dependencies should be added per-story as needed.

## AC-003: Tools directory structure

**Given** the `tools/` directory exists
**Then** it contains `__init__.py`
**And** scripts are importable as Python modules
**And** scripts are runnable via `uv run python -m tools.<script_name>` or `uv run <cli_command>`
