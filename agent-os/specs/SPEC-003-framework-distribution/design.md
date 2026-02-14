# SPEC-003: Framework Distribution — Design

## Overview

A layered approach: Python tooling provides the executable foundation, the framework manifest defines the boundary between framework and project files, upgrade/contribution workflows build on the manifest, and the install/onboard skills provide the user-facing adoption experience.

## Components

| Component | Type | Purpose |
|-----------|------|---------|
| `pyproject.toml` | Config | UV package management, project metadata |
| `tools/` | Python package | Framework utility scripts |
| `tools/validate_standards.py` | Script | Validate standards index integrity |
| `tools/validate_install.py` | Script | Verify directory structure and completeness |
| `tools/parse_session.py` | Script | Parse session summaries with YAML frontmatter |
| `tools/upgrade.py` | Script | Diff framework files against upstream, generate report |
| `framework-manifest.yml` | Config | Lists all framework-owned files with version hashes |
| `/upgrade` skill | Skill | Interactive upgrade from upstream |
| `/contribute-upstream` skill | Skill | Extract and package local enhancements for upstream PR |
| `/clean-install` skill | Skill | Reset repo to clean skeleton, guided setup |
| `/onboard-project` skill | Skill | Brownfield content ingestion and structuring |
| Getting started guide | Doc | User-facing walkthrough |

## Data Flow

### Install flow
```
User clones repo → /clean-install → Python tools reset files → setup wizard → /onboard-project or /plan-product
```

### Upgrade flow
```
/upgrade → tools/upgrade.py fetches upstream manifest → diff against local → present changes → apply or walk through conflicts
```

### Contribution flow
```
/contribute-upstream → compare local framework files to manifest → identify modifications → extract into PR-ready format
```

## Framework Manifest Structure

```yaml
# framework-manifest.yml
version: "2.1.0"
files:
  ".claude/skills/agent-os/commit/SKILL.md":
    hash: "sha256:abc123..."
    type: skill
  "agent-os/standards/guardrails.md":
    hash: "sha256:def456..."
    type: standard
  "tools/validate_standards.py":
    hash: "sha256:ghi789..."
    type: tool
  # ... all framework-owned files

project_files:
  # These are NOT framework-owned (never overwritten by upgrade)
  - "AGENTS.md"
  - "agent-os/product/**"
  - "agent-os/specs/**"
  - "agent-os/context/sessions/**"
  - "agent-os/context/component-details/**"
```

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Hash-based change detection | Hash vs timestamp vs git diff | Hash is deterministic and works regardless of git history |
| Glob patterns for project files | Explicit list vs glob patterns | Globs are maintainable; explicit lists break as projects grow |
| /onboard-project as single skill | Single skill vs multiple skills per content type | Single skill with internal phases keeps the user experience simple |

---

## Execution Plan

### Task 1: Python tooling foundation
- Create `pyproject.toml` with UV configuration
- Create `tools/__init__.py` and package structure
- Add core dependencies (PyYAML, python-frontmatter, Click)
- Add dev dependencies (pytest, ruff)

**Stories:** STORY-001

### Task 2: Validator scripts
- Create `tools/validate_standards.py`
- Create `tools/validate_install.py`
- Create `tools/parse_session.py`
- Add pytest tests for each

**Stories:** STORY-002, STORY-003

### Task 3: Framework boundary
- Design and create `framework-manifest.yml`
- Create `tools/manifest.py` for manifest operations (generate, compare, diff)
- Document the boundary convention

**Stories:** STORY-004

### Task 4: Upgrade and contribution
- Create `/upgrade` skill with CSO-compliant description
- Create `tools/upgrade.py` for deterministic diff/apply
- Create `/contribute-upstream` skill
- Implement version tagging convention

**Stories:** STORY-005, STORY-006, STORY-007

### Task 5: AGENTS.md redesign
- Strip framework documentation from AGENTS.md
- Reduce to boot loader: project description, directory structure, "run /start-session", project config, profile setting
- Document the new format

**Stories:** STORY-008

### Task 6: /clean-install skill
- Create skill that delegates file operations to Python tools
- Interactive setup wizard (languages, project structure, git workflow, profile)
- Greenfield vs brownfield fork
- Install validation via tools/validate_install.py

**Stories:** STORY-009

### Task 7: /onboard-project skill
- Content ingestion workflow (copy/paste, file upload, URL)
- Content quality assessment and scorecard
- Guided content transformation into Lit SDLC artifacts
- Existing feature mapping to retroactive specs
- Gap analysis after onboarding

**Stories:** STORY-010

### Task 8: Getting started guide
- Write user-facing walkthrough
- Cover install, first session, common workflows
- Link to relevant skills and docs

**Stories:** STORY-011
