---
name: clean-install
description: Use when a cloned Lit SDLC repo needs to be reset for a new project
triggers:
  - "clean install"
  - "new project"
  - "reset project"
  - "start fresh"
  - "clean slate"
  - "initialize project"
---

# Clean Install

Reset a cloned Lit SDLC repository to a clean skeleton for a new project. Wipes all project-specific content while preserving the framework. Hands off to `/plan-product` for greenfield projects or `/onboard-project` for brownfield adoption.

## Important

- Read `@agent-os/standards/directory-boundary.md` before proceeding — it defines which paths are framework-owned vs project-owned
- **CLAUDE.md must NOT be modified** — it is a minimal pointer to AGENTS.md by design and should stay that way
- AGENTS.md is framework-owned and must NOT be modified — it discovers project context from known locations

## The Agent Will Rationalize

Before following this process, be aware of these rationalizations that lead to botched installs:

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "I'll just delete the files I see" | You'll miss hidden content, leave stale worktrees, or break directory structure. | Follow the full inventory and reset process. |
| "The existing content is mostly fine, I'll just edit it" | Leftover content from the source project bleeds into the new project's context. AI agents will pick up stale domain terms, old specs, and wrong architecture docs. | Wipe everything project-owned and start clean. |
| "I'll customize CLAUDE.md with project details" | CLAUDE.md is intentionally minimal — it points at AGENTS.md, which discovers context from standard locations. Putting content in CLAUDE.md creates a second source of truth. | Leave CLAUDE.md as-is. Put project context in `agent-os/product/` and `agent-os/standards/project/`. |
| "I should update AGENTS.md with project info" | AGENTS.md is framework-owned. It gets replaced on `/upgrade-lit`. Any project content there will be lost. | Never modify AGENTS.md. Project context lives in `agent-os/product/` and `agent-os/context/`. |
| "I can skip the confirmation, the user already said reset" | The user may not realize how much content exists. Showing the inventory builds trust and prevents surprises. | Always show what will be wiped and confirm before proceeding. |

## ⛔ HARD GATE

**DO NOT proceed without explicit user confirmation after showing the inventory.** The reset is destructive — all project-specific content is permanently wiped. The user must see what will be affected and confirm.

## Process

### Step 1: Inventory Project-Owned Content

Read `@agent-os/standards/directory-boundary.md` to confirm the framework/project boundary.

Scan all project-owned paths and categorize what exists:

```
Project-owned paths to reset:
────────────────────────────────────────────
agent-os/product/          — Mission, roadmap, domain docs
agent-os/specs/            — Specifications and stories
agent-os/context/          — Architecture, components, sessions
agent-os/standards/project/ — Project-specific standards
README.md                  — Project README
```

For each path, count files and note any non-trivial content (files larger than a placeholder/template).

**Explicitly note:** CLAUDE.md will NOT be modified (it's a minimal pointer to AGENTS.md by design).

### Step 2: Check for Worktrees

Scan for `.claude/worktrees/` directory:

```bash
ls -d .claude/worktrees/*/ 2>/dev/null
```

If worktrees exist, note them in the inventory — their project-specific content will also be reset.

### Step 3: Present Inventory and Confirm

Present the full inventory to the user using AskUserQuestion:

```
## Clean Install — Content to Reset

**Will be WIPED and replaced with blank templates:**
- agent-os/product/ — [N files] (mission, roadmap, domain docs)
- agent-os/specs/ — [N specs with M total stories]
- agent-os/context/ — [N files] (architecture, sessions, component details)
- agent-os/standards/project/ — [N files] (build, testing, tech-stack)
- README.md — current project README
[If worktrees exist:]
- .claude/worktrees/ — [N worktrees] with project content

**Will NOT be touched:**
- CLAUDE.md (minimal pointer to AGENTS.md — stays as-is)
- AGENTS.md (framework-owned)
- .claude/skills/agent-os/ (framework skills)
- agent-os/standards/*.md (framework standards)
- agent-os/standards/code-style/ (framework code-style guides)

Proceed with the reset?
```

If the user declines, stop here.

### Step 4: Reset Product Layer

Replace all files in `agent-os/product/` with blank templates:

#### agent-os/product/mission.md
```markdown
# Product Mission

## Problem

<!-- What problem does this product solve? -->

## Target Users

<!-- Who uses this product? -->

## Solution

<!-- High-level description of the solution -->

## Key Differentiators

<!-- What makes this product unique? -->
```

#### agent-os/product/roadmap.md
```markdown
# Product Roadmap

## Current Focus

_No phases defined yet. Run `/plan-product` to begin._

## Backlog / Ideas

<!-- Add initial ideas here -->
```

#### agent-os/product/future-work.md
```markdown
# Future Work

_Parking lot for ideas that are out of scope for current phases._
```

#### Domain files

For each file in `agent-os/product/domain/`:
- If it's a `.md` file, replace contents with a single-line header and HTML comment placeholder
- If it's a non-markdown file (e.g., `.docx`, `.pdf`), replace contents with the text `[archived — previous project content]`
- Preserve `.gitkeep` files as-is

Standard domain templates to create/overwrite:

**agent-os/product/domain/terminology.md:**
```markdown
# Domain Terminology

> Project-specific vocabulary. Define terms here so all agents use consistent language.

---

| Term | Definition |
|------|-----------|
<!-- Add domain terms as the project develops -->
```

**agent-os/product/domain/business-rules.md:**
```markdown
# Business Rules

> Non-negotiable constraints and rules governing how this product operates.

---

<!-- Define business rules as requirements are gathered -->
```

### Step 5: Reset Specs Layer

#### agent-os/specs/index.yml
Replace with empty index:
```yaml
# agent-os/specs/index.yml
# Master index of all specs with status
#
# Statuses:
#   in_requirements - Gathering requirements, shaping scope
#   in_design       - Architectural design phase
#   in_progress     - Implementation underway
#   complete        - All stories pass verification
#   archived        - No longer active (completed or abandoned)

specs: {}

# Next spec number: 001
```

#### Existing spec directories
For each `SPEC-*` directory under `agent-os/specs/`:
- Replace every file's contents with: `# [ARCHIVED — Previous project content, no longer active]`
- This handles environments where file deletion is not permitted (e.g., sandboxed mounts)

**Note on deletion:** Attempt `rm -rf` on spec directories first. If deletion fails (permission denied), fall back to overwriting each file with the archive marker. Either approach is valid — the index.yml is the source of truth and it references no specs.

### Step 6: Reset Context Layer

#### agent-os/context/architecture/system-overview.md
Replace with blank template:
```markdown
# System Architecture Overview

## Design Philosophy

<!-- Describe the architectural approach for this project -->

## Project Structure

<!-- Document the directory layout and key components -->

## Key Architectural Decisions

<!-- Record decisions as they're made -->
```

#### Other context files
- For any `.md` files in `agent-os/context/architecture/ADRs/`: replace with archive marker
- For any `.md` files in `agent-os/context/component-details/`: replace with archive marker
- For any `.md` files in `agent-os/context/sessions/`: replace with archive marker
- Preserve `.gitkeep` files as-is

#### agent-os/gaps.md (if it exists)
Replace with:
```markdown
# Known Gaps

_No gaps identified yet._
```

### Step 7: Reset Project Standards

Replace project-specific standards with blank templates:

#### agent-os/standards/project/build.md
```markdown
# Build Commands & Prerequisites

> Project-specific build commands and environment setup.
> This file is project-owned and not replaced on `/upgrade-lit`.

---

## Prerequisites

<!-- List required tools and setup steps -->

## Build Commands

<!-- Add build commands for each component -->

---

_Last updated: [today's date]_
```

#### agent-os/standards/project/tech-stack.md
```markdown
# Tech Stack

> Approved technologies and infrastructure for this project.
> This file is project-owned and not replaced on `/upgrade-lit`.

---

## Languages & Frameworks

| Layer | Technology | Notes |
|-------|-----------|-------|
<!-- Add your tech stack -->

## Tooling

| Tool | Purpose | Notes |
|------|---------|-------|
<!-- Add development tools -->

---

_Last updated: [today's date]_
```

#### agent-os/standards/project/testing.md
```markdown
# Test Commands

> Project-specific test commands and testing approach.
> This file is project-owned and not replaced on `/upgrade-lit`.

---

## Testing Strategy

<!-- Define your testing approach -->

## Running Tests

<!-- Add test commands for each component -->

---

_Last updated: [today's date]_
```

### Step 8: Reset README.md

Replace with minimal project README:

```markdown
# [Project Name]

<!-- Brief project description -->

## Development

This project uses [Lit SDLC](https://github.com/buildermethods/lit-sdlc) for structured AI-assisted development. See [AGENTS.md](AGENTS.md) for the development workflow.

### Quick Start

<!-- Add setup and run instructions -->

## Project Structure

<!-- Document the directory layout -->
```

**Note:** Use the project name from the repository directory name (or ask the user if unclear).

### Step 9: Reset Worktrees (if they exist)

For each worktree directory under `.claude/worktrees/`:
- Attempt `rm -rf` first
- If deletion fails, overwrite every file with: `# [ARCHIVED — Previous project worktree content]`

### Step 10: Post-Reset Report

Present the results:

```
## Clean Install Complete

**Reset:**
- ✓ Product layer (mission, roadmap, domain docs) — blank templates
- ✓ Specs — index cleared, [N] old spec directories archived
- ✓ Context — architecture, sessions, component details cleared
- ✓ Project standards — blank templates (build, testing, tech-stack)
- ✓ README.md — minimal template
[If worktrees existed:]
- ✓ Worktrees — [N] worktrees cleared

**Untouched:**
- CLAUDE.md (pointer to AGENTS.md)
- AGENTS.md (framework boot loader)
- Framework skills (.claude/skills/agent-os/)
- Framework standards (agent-os/standards/*.md)

**Next steps:**
- Run `/plan-product` to define your mission, roadmap, and tech stack
- Or manually populate agent-os/product/ files
```

Use AskUserQuestion to ask if the user wants to proceed directly to `/plan-product`.

## Tips

- **The index.yml is the source of truth** — Old spec directories that can't be deleted are harmless as long as index.yml doesn't reference them
- **CLAUDE.md stays minimal** — Resist the urge to add project info there. It's a pointer file. Project context lives in `agent-os/product/`
- **Domain templates are intentionally sparse** — `/plan-product` will fill them in interactively
- **Run `/start-session` after clean install** — It will correctly report a blank slate, confirming the reset worked
