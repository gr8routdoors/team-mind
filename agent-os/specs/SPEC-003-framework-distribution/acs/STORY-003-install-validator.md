# STORY-003: Install validation script — Acceptance Criteria

## AC-001: Detect missing skill directories

**Given** `.claude/skills/agent-os/commit/` directory is missing
**When** `tools/validate_install.py` is run
**Then** it reports the missing skill directory

## AC-002: Detect missing AGENTS.md sections

**Given** AGENTS.md exists but is missing the operating profile section
**When** `tools/validate_install.py` is run
**Then** it reports the missing section

## AC-003: Validate directory structure

**Given** the `agent-os/` directory structure is complete
**When** `tools/validate_install.py` is run
**Then** it verifies: product/, standards/, specs/, context/ directories exist
**And** standards/index.yml exists
**And** specs/index.yml exists

## AC-004: Clean validation pass

**Given** a properly installed Lit SDLC project
**When** `tools/validate_install.py` is run
**Then** it exits with code 0 and reports "Installation valid"
