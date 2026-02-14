# STORY-007: Version tagging — Acceptance Criteria

## AC-001: Semantic versioning

**Given** a new release of Lit SDLC is prepared
**When** a version tag is created
**Then** it follows semantic versioning (MAJOR.MINOR.PATCH)
**And** the version is recorded in framework-manifest.yml
**And** the version is recorded in pyproject.toml

## AC-002: Version display in /upgrade

**Given** a project has Lit SDLC installed
**When** `/upgrade` is run
**Then** the skill displays the current installed version and the latest available version
**And** shows a changelog summary of what changed between versions
