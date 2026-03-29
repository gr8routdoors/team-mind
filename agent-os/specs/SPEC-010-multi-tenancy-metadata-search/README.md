# SPEC-010: Multi-Tenancy & Metadata Search

## Overview

Introduces required multi-tenancy via a `tenant_id` field on all documents, and metadata search as a query-time filtering mechanism on the existing JSON metadata column. These features address data isolation across users/organizations and structured retrieval beyond vector similarity.

## Scope

**In scope:**
- `tenant_id TEXT NOT NULL` column on the `documents` table with `"default"` as the standard default tenant.
- `tenant_id` threaded through `IngestionBundle`, `save_payload`, `delete_by_uri`, `lookup_existing_docs`, and `IngestionEvent`.
- Updated composite identity key: `(uri, plugin, record_type, tenant_id)`.
- `tenant_ids: list[str] | None` filter on `retrieve_by_vector_similarity`.
- Metadata search via `json_extract` filters on `retrieve_by_vector_similarity`.
- Optional vector query — pure metadata/weight-ranked retrieval when `query` is omitted.
- `semantic_search` MCP tool extended with `tenant_ids` and `metadata_filters` parameters.
- `ingest_documents` MCP tool and CLI extended with `tenant_id` parameter (defaults to `"default"`).
- KNN over-fetch multiplier adjustment for additional filter dimensions.
- Update all existing tests for required `tenant_id` parameter.
- Update documentation.

**Out of scope:**
- Permission gating on cross-tenant queries (future work, noted in ADR-008).
- Sub-document segments / sub-document weighting (future ADR, noted in ADR-008).
- Generated column indexes for metadata hot paths (optimization, can be added later).
- Metadata search operators beyond equality (range, contains, etc. — future enhancement).

## Context

**References:**
- `agent-os/context/architecture/ADRs/ADR-008-multi-tenancy-metadata-search.md` — Full design rationale.
- `agent-os/context/architecture/ADRs/ADR-003-relevance-weighting.md` — Weighting system that metadata search composes with.
- `agent-os/context/architecture/ADRs/ADR-007-semantic-type-routing.md` — Semantic type routing (structural field vs. metadata field boundary).

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Required tenant_id | Required vs optional | Eliminates null/empty ambiguity. Every document has an owner. No backward compat concern. |
| Default tenant = `"default"` | `"default"` vs `"global"` vs `""` | Clear, readable, no special semantics. Single-tenant deployments just use it. |
| Extend semantic_search | New tool vs extend existing | Preserves weighting, decay, composite scoring. One composable query surface. |
| Metadata equality filters | Equality-only vs rich operators | Simple, sufficient for current needs. Rich operators can be added later. |
| tenant_ids as list on query | Single vs list vs wildcard | List is the natural primitive. Omit = all tenants. Covers all use cases. |
| No backward compatibility | Breaking changes vs migration | No deployed instances. Clean break is simpler than migration scaffolding. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | Tenant ID Schema and Storage | pending |
| STORY-002 | Tenant-Scoped Idempotency | pending |
| STORY-003 | Tenant ID in Ingestion Pipeline | pending |
| STORY-004 | Tenant-Filtered Vector Search | pending |
| STORY-005 | Metadata Search Filters | pending |
| STORY-006 | Optional Vector Query (Weight-Ranked Retrieval) | pending |
| STORY-007 | MCP Tool and CLI Extensions | pending |
| STORY-008 | Update Existing Tests | pending |
| STORY-009 | Update Documentation | pending |
