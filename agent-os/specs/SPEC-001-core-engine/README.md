# SPEC-001: Core Information Architecture (MVP)

## Overview

The Core Information Architecture establishes the foundational "Team Mind" knowledge base. It builds an extensible MCP Server gateway, an event-driven resource bundle ingestion pipeline, an embedded SQLite storage abstraction for vectors and documents, and a foundational Markdown plugin that powers semantic search and full-document context retrieval for AI tooling.

## Scope

**In scope:**
- Base Python MCP Server allowing client connections.
- Plugin registration and tool-routing system.
- Bundle-based broadcast ingestion loop.
- Abstract storage layer backed natively by SQLite (with `sqlite-vec` + JSON).
- A basic Markdown semantic plugin that provides fast vector search.
- A dedicated Document Retrieval plugin that resolves and fetches live file content from Pointers (URIs).

**Out of scope:**
- The Librarian validation pipeline (reserved for SPEC-002).
- Native MS Teams / Chat integrations (reserved for future specs).
- Complex domain plugins like AST parsers or Metric aggregators.
- Enterprise MongoDB migration.

## Context

**References:**
- `agent-os/context/architecture/system-overview.md` — Explains the broadcast pipeline and pluggable model.
- `agent-os/product/mission.md` — The guiding philosophy of token-optimized, precision retrieval.

**Standards:**
- Python code conventions (to be established/injected).
- Testing — TDD principles with BDD acceptance criteria.

**Visuals:**
- None for this core backend spec.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Embedded SQLite | SQLite vs Flat Files vs MongoDB | Zero-deployment friction for MVP, yet full support for vectors `sqlite-vec` and JSON document storage, avoiding flat-file brittleness. |
| Dedicated Retrieval Plugin | Unified vs Dedicated Plugin | Separating vector search (MarkdownPlugin) from content fetching (DocumentRetrievalPlugin) ensures we can cleanly handle URIs/Pointers without bloating domain-specific parsing plugins. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | MCP Gateway & Plugin Registry | in_requirements |
| STORY-002 | SQLite Embedded Storage Engine | in_requirements |
| STORY-003 | URI-based Bundle Ingestion Loop | in_requirements |
| STORY-004 | Markdown Vector Plugin | in_requirements |
| STORY-005 | Document Retrieval Plugin | in_requirements |
