# STORY-001: /commit skill — Acceptance Criteria

## AC-001: Context-aware commit message from spec work

**Given** the agent has completed work on STORY-002 of SPEC-002
**And** there are staged or unstaged changes in the working tree
**When** the agent runs `/commit`
**Then** the skill reads the active spec and story context
**And** builds a conventional commit message (e.g., `feat(ship-pr): add PR assembly from spec artifacts`)
**And** the commit body references the spec and story (e.g., `SPEC-002 / STORY-002`)
**And** presents the message for human review before committing

## AC-002: Context-aware commit message for ad hoc work

**Given** the agent has made changes outside of any spec (e.g., framework improvements, README updates)
**And** there are staged or unstaged changes
**When** the agent runs `/commit`
**Then** the skill infers the commit type and scope from the changed files
**And** builds a conventional commit message (e.g., `docs: update README with new skills table`)
**And** presents the message for human review before committing

## AC-003: Selective staging

**Given** the working tree has multiple unstaged changes across several files
**When** the agent runs `/commit`
**Then** the skill presents a summary of all changed files
**And** allows the user to confirm or adjust which files to stage
**And** respects `.gitignore`
**And** flags any potentially sensitive files (`.env`, credentials, API keys) and refuses to stage them

## AC-004: Atomic commit enforcement

**Given** the working tree contains changes spanning multiple logical units (e.g., a bug fix and a new feature)
**When** the agent runs `/commit`
**Then** the skill identifies the distinct logical units
**And** suggests splitting into multiple commits
**And** walks the user through staging and committing each unit separately

## AC-005: Conventional commit format compliance

**Given** the agent runs `/commit`
**When** the commit message is generated
**Then** the message follows the format defined in `git.md` standards
**And** uses appropriate type prefix (feat, fix, docs, chore, refactor, test, etc.)
**And** includes scope when identifiable
**And** keeps the subject line under 72 characters
