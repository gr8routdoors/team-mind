# STORY-004: Framework/project boundary manifest — Acceptance Criteria

## AC-001: Manifest lists all framework files

**Given** the framework-manifest.yml is generated
**Then** it includes every framework-owned file (skills, standards, tools, core config)
**And** each entry has a sha256 hash of the file contents
**And** each entry has a type (skill, standard, tool, config)

## AC-002: Manifest excludes project files

**Given** the framework-manifest.yml is generated
**Then** it does NOT include project-specific files (product docs, specs, sessions, component-details)
**And** it defines glob patterns for project file paths that should never be overwritten

## AC-003: Manifest diff detection

**Given** a local framework file has been modified (hash differs from manifest)
**When** `tools/manifest.py diff` is run
**Then** it reports which files have been locally modified
**And** which files match the manifest (unchanged)

## AC-004: Manifest generation

**Given** a developer runs `tools/manifest.py generate`
**Then** a new framework-manifest.yml is created from the current state of all framework files
**And** the version field is set from the current git tag or a provided argument
