# STORY-001: Minimal AGENTS.md redesign — Acceptance Criteria

## AC-001: Generic boot loader content

**Given** the current AGENTS.md contains project-specific content (product details, team conventions, etc.)
**When** AGENTS.md is redesigned
**Then** it contains only framework-owned content: workflow description, directory structure map, skill discovery instructions, and "run /start-session"
**And** all project-specific content is removed (not relocated — it already lives in `agent-os/product/`)
**And** AGENTS.md is fully replaceable by `/upgrade-lit` without losing project context

## AC-002: Project context discovery

**Given** an agent reads the redesigned AGENTS.md
**When** it needs project-specific context (mission, roadmap, domain terminology, etc.)
**Then** AGENTS.md points to `agent-os/product/` as the location for project context
**And** the agent can discover project-specific skills from `.claude/skills/{project}/`
**And** no project context is inlined in AGENTS.md

## AC-003: Existing skills still work

**Given** AGENTS.md has been redesigned
**When** existing skills are invoked (e.g., /start-session, /shape-spec, /commit)
**Then** they continue to function correctly
**And** any skill that reads AGENTS.md can still find the information it needs (workflow, directory structure)
