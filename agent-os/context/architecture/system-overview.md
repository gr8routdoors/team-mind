# System Architecture Overview

## Design Philosophy

Lit SDLC is a **file-based, zero-dependency framework** that lives entirely inside your repository. No runtime, no server, no database. The framework consists of markdown files, YAML configuration, and convention-based directory structure that AI agents read and follow.

## The Four Layers

### 1. Product Layer (`agent-os/product/`)

The "why" — product vision, priorities, and domain knowledge.

| File | Purpose |
|------|---------|
| `mission.md` | Problem, target users, solution, differentiators |
| `roadmap.md` | Current focus, phased feature list, blocked items |
| `domain/terminology.md` | Business vocabulary and concept definitions |
| `domain/business-rules.md` | Non-negotiable constraints and operational rules |

### 2. Standards Layer (`agent-os/standards/`)

The "what" — declarative conventions agents must follow. Each standard is a markdown file indexed in `index.yml` with tags for selective injection.

### 3. Skills Layer (`.claude/skills/agent-os/`)

The "how" — procedural workflows executed step by step. Each skill has YAML frontmatter, anti-rationalization tables, optional hard gates, and process steps.

### 4. Context Layer (`agent-os/context/`)

The "what happened" — accumulated knowledge from past work: architecture docs, component details, session summaries.

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| File-based, no runtime | Zero dependencies. Works with any AI tool that reads files. |
| Standards separate from skills | Standards update independently. Prevents bloat. |
| Tagged index for standards | Agents load only relevant standards, preserving context window. |
| Session summaries in markdown | Human-readable, version-controlled, searchable. |
| Stories locked to agents | Agents modify status only. Prevents scope creep. |
| Two-stage code review | Catches different problem classes: spec drift vs. code quality. |
| Anti-rationalization by design | Agents skip good practices under pressure. Explicit counters prevent this. |
