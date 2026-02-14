# STORY-006: /contribute-upstream skill — Acceptance Criteria

## AC-001: Identify local modifications

**Given** the user has modified framework files (new skills, updated standards)
**When** the user runs `/contribute-upstream`
**Then** the skill compares local framework files to the manifest
**And** lists all modified, new, and deleted framework files

## AC-002: Package for contribution

**Given** the user selects which modifications to contribute
**When** the skill packages the contribution
**Then** it extracts the selected files into a clean format suitable for a PR against the upstream repo
**And** helps the user write a contribution summary describing what changed and why

## AC-003: Exclude project-specific content

**Given** the user runs `/contribute-upstream`
**Then** the skill never includes project-specific files (product docs, specs, sessions) in the contribution package
**And** warns the user if a selected file appears to contain project-specific content
