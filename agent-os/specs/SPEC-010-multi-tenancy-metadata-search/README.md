# SPEC-010: Multi-Tenancy & Metadata Search

## Overview

Introduces required multi-tenancy via per-tenant SQLite database sharding and metadata search as a query-time filtering mechanism on the existing JSON metadata column. Each tenant gets its own database file; a global `system.sqlite` holds the plugin registry and tenant directory. The `semantic_search` tool becomes the single composable query surface for vector similarity, metadata filtering, tenant scoping, and weight ranking. Cross-tenant queries use scatter-gather across shards.

## Scope

**In scope:**
- `TenantStorageManager` class managing per-tenant SQLite databases, scatter-gather queries, and tenant lifecycle.
- `system.sqlite` with `registered_plugins` (moved from per-database) and `tenants` tables.
- Per-tenant `data.sqlite` files with `documents`, `vec_documents`, and `doc_weights` tables (no `tenant_id` column).
- `StorageAdapter` unchanged — operates on a single database, no tenant awareness.
- `tenant_id` threaded through `IngestionBundle`, `IngestionEvent`, and `IngestionPipeline.ingest()` for routing to the correct shard.
- Metadata search via `json_extract` filters on `retrieve_by_vector_similarity`.
- Optional vector query — pure metadata/weight-ranked retrieval when `target_vector` is `None`.
- `semantic_search` MCP tool extended with `tenant_ids` and `metadata_filters` parameters, `query` made optional.
- `ingest_documents` MCP tool extended with `tenant_id` parameter (defaults to `"default"`).
- `provide_feedback` MCP tool extended with required `tenant_id` parameter.
- CLI `--tenant-id` flag on ingest subcommand.
- Update all existing tests for tenant-aware pipeline routing.
- Update documentation.

**Out of scope:**
- Permission gating on cross-tenant queries (future work, noted in ADR-008).
- Parallel shard queries in scatter-gather (MVP is sequential).
- Generated column indexes for metadata hot paths (optimization, can be added later).
- Metadata search operators beyond equality (range, contains, etc. — future enhancement).
- Hash-based directory structure for extreme tenant counts (future optimization).

## Context

**References:**
- `agent-os/context/architecture/ADRs/ADR-008-multi-tenancy-metadata-search.md` — Original multi-tenancy rationale, amended by ADR-010.
- `agent-os/context/architecture/ADRs/ADR-010-tenant-sharding.md` — Tenant sharding decision and KNN correctness analysis.
- `agent-os/context/architecture/ADRs/ADR-003-relevance-weighting.md` — Weighting system that metadata search composes with.
- `agent-os/context/architecture/ADRs/ADR-007-semantic-type-routing.md` — Semantic type routing (structural field vs. metadata field boundary).

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Per-tenant SQLite sharding | Column filter vs file sharding vs bucket sharding | KNN post-filter is provably incorrect at 1K+ tenants. File sharding makes KNN correct by construction. See ADR-010. |
| Required tenancy with default tenant | Required vs optional | Eliminates null/empty ambiguity. Every document has an owner. `"default"` for single-tenant deployments. |
| Global system.sqlite | Per-database vs global plugin registry | Plugins are global — register once, available across all tenants. Tenant directory enables scatter-gather enumeration. |
| StorageAdapter unchanged | Add tenant params vs route externally | StorageAdapter operates on one database. Tenant routing is TenantStorageManager's concern. Clean separation. |
| Extend semantic_search | New tool vs extend existing | Preserves weighting, decay, composite scoring. One composable query surface. |
| Metadata equality filters | Equality-only vs rich operators | Simple, sufficient for current needs. Rich operators can be added later. |
| Sequential scatter-gather (MVP) | Sequential vs parallel | SQLite connections are single-threaded. Parallel is a future optimization. |
| No backward compatibility | Breaking changes vs migration | No deployed instances. Clean break is simpler than migration scaffolding. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | system.sqlite and TenantStorageManager | pending |
| STORY-002 | Per-Tenant Database Lifecycle | pending |
| STORY-003 | Ingestion Pipeline Routing | pending |
| STORY-004 | Metadata Search Filters | pending |
| STORY-005 | Optional Vector Query (Weight-Ranked Retrieval) | pending |
| STORY-006 | Cross-Tenant Scatter-Gather | pending |
| STORY-007 | MCP Tools and CLI | pending |
| STORY-008 | Update Existing Tests | pending |
| STORY-009 | Update Documentation | pending |
