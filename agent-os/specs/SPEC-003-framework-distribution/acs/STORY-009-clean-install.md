# STORY-009: /clean-install skill — Acceptance Criteria

## AC-001: Reset project-specific content

**Given** the user clones the full Lit SDLC repo (with roadmap, SPEC-001, etc.)
**When** the user runs `/clean-install`
**Then** product docs (mission, roadmap, domain) are reset to empty templates
**And** all specs are removed from specs/ (and index.yml reset)
**And** session history is cleared
**And** AGENTS.md project-specific sections are reset to `// TODO:` markers
**And** framework files (skills, standards, tools) are preserved untouched

## AC-002: Interactive setup wizard

**Given** the reset is complete
**When** the setup wizard runs
**Then** it asks: project languages (removes irrelevant language-specific standards)
**And** asks: project structure (populates AGENTS.md structure section)
**And** asks: git workflow (configures git standards)
**And** asks: team size and review process (sets operating profile)

## AC-003: Greenfield vs brownfield fork

**Given** the setup wizard is complete
**When** the skill asks "Do you have existing documentation to import?"
**Then** if yes, it hands off to `/onboard-project`
**And** if no, it hands off to `/plan-product`

## AC-004: Install validation

**Given** `/clean-install` has completed
**Then** it runs `tools/validate_install.py` to verify the result
**And** reports any issues found
**And** confirms successful installation if all checks pass
