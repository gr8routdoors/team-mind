# STORY-005: /upgrade skill + upgrade tooling — Acceptance Criteria

## AC-001: Detect upstream changes

**Given** the upstream Lit SDLC repo has new or modified framework files
**When** the user runs `/upgrade`
**Then** the skill fetches the upstream manifest
**And** compares it to the local manifest
**And** presents a summary: new files, modified files, removed files

## AC-002: Clean upgrade (no local modifications)

**Given** no local framework files have been modified (all hashes match local manifest)
**And** upstream has new or updated files
**When** the user confirms the upgrade
**Then** the skill applies changes automatically
**And** updates the local manifest to match upstream
**And** reports what was changed

## AC-003: Conflict handling (local modifications)

**Given** a local framework file has been modified AND upstream has a different version
**When** the upgrade encounters this conflict
**Then** the skill presents both versions to the user
**And** asks the user to choose: keep local, take upstream, or merge manually
**And** does not silently overwrite local modifications

## AC-004: Upgrade Python tooling

**Given** `tools/upgrade.py` is invoked
**Then** it performs the deterministic operations: fetch manifest, compare hashes, generate diff report
**And** returns structured data that the skill uses for the interactive conversation
