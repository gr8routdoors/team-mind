# STORY-004: /create-pr skill — Acceptance Criteria

## AC-001: Conventional commit format for PR title

**Given** the user runs `/create-pr`
**When** the skill prepares the PR title
**Then** it uses conventional commit format: `<type>(<scope>): <description>`
**And** if there is exactly one commit on the branch (compared to the base branch), it uses that commit's first line (subject) as the PR title
**And** if there are multiple commits, it reads the commit messages to determine the appropriate type and scope:
  - If all commits have the same type and scope, use that for the PR title with a summary description
  - If commits have different types, use the most common type or ask the user which to use
  - If commits have different scopes, use the broadest applicable scope or ask the user
**And** it presents the proposed PR title to the user for review before creating the PR

## AC-002: PR description follows git.md standard

**Given** the user runs `/create-pr`
**When** the skill prepares the PR description
**Then** if there is exactly one commit on the branch, it uses the commit body (everything after the first line) as the starting point for the PR description
**And** if there are multiple commits, it synthesizes a description from the commit messages
**And** it ensures the description includes the sections specified in `git.md`:
  - **Summary** (or **What**) — Brief description of the change
  - **Test plan** (or **Testing**) — How it was tested (or "Manual verification" if not automated)
**And** it includes the standard Claude Code footer: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
**And** it presents the description to the user for review before creating the PR

## AC-003: Use `gh pr create` for PR creation

**Given** the user runs `/create-pr` and approves the title and description
**When** the skill creates the PR
**Then** it uses `gh pr create --title "<title>" --body "<description>"`
**And** it returns the PR URL to the user
**And** if `gh` is not installed or authenticated, it provides clear error message and instructions

## AC-004: CSO-compliant skill description

**Given** the skill file exists at `.claude/skills/agent-os/create-pr/SKILL.md`
**When** an agent reads the frontmatter
**Then** the `description` field states ONLY the triggering condition (when to use the skill)
**And** it does NOT summarize the workflow or list the steps
**And** it includes appropriate trigger phrases like "create pr", "make pr", "open pull request"

## AC-005: Anti-rationalization table

**Given** the skill file exists
**When** an agent is tempted to skip a step
**Then** the skill includes an anti-rationalization table with common excuses and why they're wrong
**And** includes entries for: "The commit message is good enough for the PR title" (No — git.md requires conventional format), "The user can edit the PR after creation" (No — get it right the first time), "Just use the branch name as the title" (No — conventional commits required)
