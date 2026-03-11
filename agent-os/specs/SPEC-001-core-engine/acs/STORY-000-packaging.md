# STORY-000: Executable Packaging & Delivery — Acceptance Criteria

> ACs for packaging the MCP server as a shippable Python CLI using `uv`.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Valid Package Build | Happy path |
| AC-002 | CLI Entry Point Execution | Happy path |

---

## Acceptance Criteria

### AC-001: Valid Package Build

**Given** a properly structured `pyproject.toml`
**When** the user executes `uv build`
**Then** the project successfully compiles into a `.whl` (Wheel) and `.tar.gz` (Source) distribution
**And** no dependency resolution errors occur

---

### AC-002: CLI Entry Point Execution

**Given** the package is correctly installed (or executed via `uv run team-mind-mcp`)
**When** a user invokes the CLI entry point
**Then** the application triggers the main MCP server startup routine
**And** returns a successful exit code (or enters the listen loop)
