# STORY-002: /ship-pr skill — Acceptance Criteria

## AC-001: PR assembly from Lit SDLC artifacts

**Given** the agent has completed and verified work on a story
**When** the agent runs `/ship-pr`
**Then** the skill builds a PR title from the spec name and story name
**And** the PR description includes: spec overview (from README.md), story scope, acceptance criteria summary, verification evidence, files changed summary
**And** the description links to the spec, story, and AC files in the repo

## AC-002: Uncommitted changes handling

**Given** there are uncommitted changes in the working tree
**When** the agent runs `/ship-pr`
**Then** the skill calls `/commit` first to stage and commit changes
**And** then proceeds with PR creation using the resulting commit(s)

## AC-003: Git hygiene

**Given** the agent runs `/ship-pr`
**When** preparing the branch for PR
**Then** the skill ensures the branch is clean (no uncommitted changes after /commit)
**And** organizes commits per `git.md` standards
**And** handles rebasing against the target branch if needed
**And** respects `git-worktrees.md` if worktrees are in use

## AC-004: PR linkage to spec artifacts

**Given** a PR is created by `/ship-pr`
**Then** the PR description includes markdown links to the spec README, story in stories.yml, and relevant AC files
**And** optionally updates `stories.yml` to note the PR is open
