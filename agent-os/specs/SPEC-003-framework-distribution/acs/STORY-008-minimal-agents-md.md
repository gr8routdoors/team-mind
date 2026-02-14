# STORY-008: Minimal AGENTS.md redesign — Acceptance Criteria

## AC-001: Boot loader format

**Given** AGENTS.md is redesigned
**Then** it contains only: a one-paragraph project description, the Lit SDLC directory structure overview, the startup instruction ("run /start-session first, or /bootstrap if new"), project-specific configuration sections (tech stack, build commands, project structure), and the operating profile setting
**And** it does NOT contain framework documentation (workflow tables, skill descriptions, discipline enforcement explanations, standards references)

## AC-002: TODO markers for project config

**Given** AGENTS.md is in its clean-install state
**Then** project-specific sections are marked with `// TODO:` placeholders
**And** each placeholder includes a brief instruction of what to fill in

## AC-003: Framework docs accessible via skills

**Given** framework documentation has been removed from AGENTS.md
**Then** all removed information is still accessible via the appropriate skill or standard
**And** `/start-session` loads the context that AGENTS.md previously provided
**And** no framework knowledge is lost — it's just relocated to where it belongs
