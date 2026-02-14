# SPEC-003: Framework Distribution

## Overview

Make Lit SDLC easy to install, upgrade, and adopt in both greenfield and brownfield projects. This spec covers the Python tooling foundation, framework/project boundary management, upgrade and contribution workflows, the /clean-install and /onboard-project skills, and a getting started guide.

## Scope

**In scope:**
- Python tooling foundation (pyproject.toml, UV, tools/ directory, validator scripts)
- Framework vs. project boundary manifest
- /upgrade skill and upgrade Python tooling
- /contribute-upstream skill
- Version tagging
- Minimal AGENTS.md redesign (boot loader)
- /clean-install skill (reset, setup wizard, validation)
- /onboard-project skill (content ingestion, quality assessment, transformation, feature mapping, gap analysis)
- Getting started guide

**Out of scope:**
- Autonomous orchestrator (Phase 5)
- Enterprise integrations (Confluence, Jira, Teams — Phase 5)
- Automated skill testing framework (backlog)

## Context

**References:**
- `AGENTS.md` — Current format to be redesigned
- `agent-os/standards/index.yml` — To be validated by Python tooling
- `agent-os/context/architecture/autonomous-agents-plan-original.md` — Session frontmatter parser feeds into Phase 5

**Standards:**
- guardrails — Anti-patterns and unattended mode rules
- cso — Skill description rules
- git — Commit and branch conventions
- best-practices — SOLID, YAGNI principles

**Visuals:** None

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| UV for package management | UV vs pip vs poetry vs pdm | UV is fast, modern, and already in use at the maintainer's work projects |
| tools/ directory convention | tools/ vs scripts/ vs src/ | tools/ clearly signals "framework utilities" vs application code |
| Framework manifest for boundary | Manifest file vs directory convention vs git submodule | Manifest is explicit and machine-enforceable; directory convention is implicit and fragile; submodule adds git complexity |
| /clean-install as skill (not script) | Skill vs bash script vs Python CLI | Skill enables interactive conversation (language selection, project structure); delegates deterministic file ops to Python tooling |
| Content ingestion via copy/paste | API integration vs copy/paste vs file upload | API integration is impractical (too many tools); copy/paste + file upload covers 90% of cases without external dependencies |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | pyproject.toml + UV setup | failing |
| STORY-002 | Standards index validator | failing |
| STORY-003 | Install validation script | failing |
| STORY-004 | Framework/project boundary manifest | failing |
| STORY-005 | /upgrade skill + upgrade tooling | failing |
| STORY-006 | /contribute-upstream skill | failing |
| STORY-007 | Version tagging | failing |
| STORY-008 | Minimal AGENTS.md redesign | failing |
| STORY-009 | /clean-install skill | failing |
| STORY-010 | /onboard-project skill | failing |
| STORY-011 | Getting started guide | failing |
