# SPEC-005: Idempotent Ingestion with Content Hashing

## Overview

Makes ingestion aware of previously-ingested content by providing plugins with structured context about each URI: whether it's been seen before, whether the content has changed, what plugin version originally processed it, and the IDs of existing rows. Plugins use this context to make intelligent decisions — skip unchanged content, re-process with a new plugin version, or wipe and replace stale data.

## Scope

**In scope:**
- `content_hash` column on the `documents` table (SHA-256 of content at ingestion time).
- `plugin_version` column on the `documents` table (set by the ingesting plugin).
- `version` property on `IngestProcessor` interface (optional, defaults to `"0.0.0"`).
- `IngestionContext` dataclass passed to processors alongside each URI during ingestion.
- URI lookup at ingest time: detect existing rows for the same URI + plugin + doctype.
- Content hash comparison: flag whether content has changed since last ingestion.
- Plugin version comparison: flag whether the processing plugin version has changed.
- Update MarkdownPlugin to skip unchanged content (idempotent optimization).

**Out of scope:**
- Semantic similarity-based deduplication (different URIs with similar content).
- Automatic migration of old-version documents (plugins decide their own migration strategy).
- Content hash enforcement (hash is computed and stored, not validated on read).

## Context

**References:**
- `agent-os/context/architecture/ADRs/ADR-003-relevance-weighting.md` — Weighting system that benefits from stable document IDs across re-ingestion.
- `agent-os/specs/SPEC-004-relevance-weighting/` — `update_payload` and `delete_by_uri` provide the primitives plugins use to act on the context.
- `agent-os/context/architecture/plugin-developer-guide.md` — Must be updated with ingestion context docs.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Platform provides context, plugins decide | Platform auto-dedup vs platform-provides-context | Different plugins have different idempotency needs. A deterministic parser can skip; a non-deterministic analyzer may re-process. Let plugins choose. |
| SHA-256 content hash | MD5 vs SHA-256 vs xxHash | SHA-256 is standard, collision-resistant, and fast enough for our scale. Not a security hash — just content identity. |
| Plugin version on document row | Version in metadata vs dedicated column | Dedicated column enables efficient queries ("find all docs from plugin v1.x") without JSON parsing. |
| Version as string | Semver vs integer vs string | String is the most flexible. Plugins can use semver, date-based, or any format. Platform doesn't parse it — just stores and compares. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | Content Hash & Plugin Version Columns | pending |
| STORY-002 | Plugin Version Property | pending |
| STORY-003 | IngestionContext & URI Lookup | pending |
| STORY-004 | Two-Phase Pipeline Provides Context | pending |
| STORY-005 | MarkdownPlugin Idempotent Optimization | pending |
| STORY-006 | Update Documentation | pending |
