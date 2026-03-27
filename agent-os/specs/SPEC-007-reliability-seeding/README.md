# SPEC-007: Reliability Seeding

## Overview

Enables documents to be seeded with an initial reliability score at ingestion time. Three layers contribute: an ingest hint from the caller (always present on the bundle), a plugin default (declared on DoctypeSpec), and a plugin override (decided at process time). The plugin always has the last word, but always has the ingest hint available to inform its decision.

## Scope

**In scope:**
- `reliability_hint` on `IngestionBundle` — optional float passed by the ingestion caller.
- `default_reliability` on `DoctypeSpec` — optional float declared by plugins.
- `initial_score` parameter on `save_payload` — seeds `usage_score` in `doc_weights`.
- Update `IngestionPipeline.ingest()` to accept and propagate `reliability_hint`.
- Update `ingest_documents` MCP tool to accept `reliability_hint`.
- Update CLI `ingest` subcommand to accept `--reliability` flag.
- Update MarkdownPlugin to use reliability seeding.
- Update documentation.

**Out of scope:**
- Background conflict detection (separate future spec).
- Automatic reliability inference from content analysis.
- Per-chunk reliability (reliability is per-document/save operation).

## Context

**References:**
- `agent-os/context/architecture/ADRs/ADR-006-reliability-seeding.md` — Design rationale, Librarian retirement.
- `agent-os/specs/SPEC-004-relevance-weighting/` — `usage_score` and `doc_weights` this builds on.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Three-layer seeding | Single source vs three layers | Different actors have different knowledge. The caller knows the source, the plugin knows the domain, the plugin decides the final value. |
| Seed into usage_score | Separate field vs seed existing | Reliability and usage scoring serve the same ranking purpose. One field, different starting points. |
| Hint always on bundle | Optional vs always | Plugins should always be able to inspect the hint, even if they ignore it. None means "no hint provided." |
| Plugin has last word | Platform overrides vs plugin overrides | Plugin has the most domain knowledge. Platform provides the hint, plugin decides. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | Reliability Hint on IngestionBundle | pending |
| STORY-002 | Default Reliability on DoctypeSpec | pending |
| STORY-003 | Initial Score on save_payload | pending |
| STORY-004 | Pipeline and MCP Tool Propagation | pending |
| STORY-005 | MarkdownPlugin Reliability Integration | pending |
| STORY-006 | Update Documentation | pending |
