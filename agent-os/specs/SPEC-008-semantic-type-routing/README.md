# SPEC-008: Semantic Type Routing (Phase A — Additive)

## Overview

Introduces the three-type model (semantic type, media type, record type) and semantic-type-based routing to the ingestion pipeline. This is Phase A — all additive changes, no renames. Phase B (rename doctype → record_type) was completed as SPEC-009.

## Scope

**In scope:**
- `semantic_type` and `media_type` columns on the `documents` table.
- `semantic_type` field on `IngestionBundle` (set by caller, propagated to plugins).
- `semantic_type` field on `IngestionEvent` (set by processor, propagated to observers).
- `semantic_types` field on `EventFilter` (observers can filter by semantic type).
- `supported_media_types` property on `IngestProcessor` (declares parsing capabilities).
- `semantic_types` and `supported_media_types` columns on `registered_plugins` table.
- Registration-time semantic type configuration (updateable without plugin reinstall).
- Pipeline routes to plugins registered for the bundle's semantic type.
- Pipeline filters URIs within a bundle by plugin's supported media types.
- `ingest_documents` MCP tool and CLI accept `semantic_type` parameter.
- Update MarkdownPlugin with `supported_media_types` and semantic type awareness.
- Update documentation.

**Out of scope:**
- Rename doctype → record_type (Phase B, completed in SPEC-009).
- Meta-plugins / chained processing (future roadmap item).
- Auto-detection of semantic type from content (caller must specify).

## Context

**References:**
- `agent-os/context/architecture/ADRs/ADR-007-semantic-type-routing.md` — Full design rationale.
- `agent-os/context/architecture/ADRs/ADR-006-reliability-seeding.md` — Reliability seeding interacts with semantic type context.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Additive first, rename later | All-at-once vs phased | Isolates new functionality from mechanical refactor. Reduces risk. |
| Semantic type on bundle, not per-URI | Per-URI vs per-bundle | A bundle represents a single ingestion request with one semantic context. Individual URIs within may have different media types but share semantic type. |
| Media type auto-detected from extension | Explicit only vs auto-detect | File extensions are a reliable heuristic. Explicit hint can override. |
| Fallback to broadcast when no semantic type | Require semantic type vs optional | Backward compatible — existing code that doesn't specify semantic_type gets broadcast behavior. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | Semantic Type and Media Type Schema | pending |
| STORY-002 | Supported Media Types on IngestProcessor | pending |
| STORY-003 | Semantic Types on Plugin Registration | pending |
| STORY-004 | Semantic Type on IngestionBundle and IngestionEvent | pending |
| STORY-005 | Pipeline Semantic Type Routing | pending |
| STORY-006 | EventFilter Semantic Type Support | pending |
| STORY-007 | MCP Tool and CLI Semantic Type Parameter | pending |
| STORY-008 | MarkdownPlugin Media Type and Semantic Type Awareness | pending |
| STORY-009 | Update Documentation | pending |
