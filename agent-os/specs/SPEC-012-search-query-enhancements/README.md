# SPEC-012: Search Query Enhancements

**Status:** in_design
**Created:** 2026-03-31
**Stories:** 8

## Summary

Closes two core gaps in Team Mind's search layer:

1. **Semantic type filtering on search queries** (priority) -- the `semantic_type` column exists and is indexed on `documents`, but neither `retrieve_by_vector_similarity` nor `retrieve_by_weight` accept it as a query-time filter. Callers cannot scope searches to "architecture_docs" or "meeting_transcripts" without resorting to metadata workarounds.

2. **DocumentRetrievalPlugin cross-tenant wiring** -- `DocumentRetrievalPlugin` holds a single `StorageAdapter` and cannot perform cross-tenant scatter-gather queries. `FeedbackPlugin` was already converted to hold `TenantStorageManager`; `DocumentRetrievalPlugin` needs the same treatment, exposing `tenant_ids` and `semantic_types` as tool arguments.

3. **Documentation updates** -- plugin developer guide, system overview, and ADR cross-references updated to reflect these new query capabilities.

## Key Design Decisions

- Semantic type filter follows the same pattern as `plugins` and `record_types`: a `semantic_types: list[str] | None` parameter, `IN (...)` SQL clause, empty-list short-circuit.
- `documents.semantic_type` stores comma-joined values for multi-type documents. The filter uses `INSTR()` matching (not exact `IN`) to handle comma-joined strings.
- `DocumentRetrievalPlugin` constructor changes from `StorageAdapter` to `TenantStorageManager`, mirroring the `FeedbackPlugin` pattern from SPEC-010.
- `retrieve_documents` MCP tool gains `tenant_ids` and `semantic_types` parameters.
- All queries route through `query_across_tenants` for consistent tenant_id-injected results.

## References

- [Design Document](design.md)
- [Stories](stories.yml)
- [SPEC-010: Multi-Tenancy & Metadata Search](../SPEC-010-multi-tenancy-metadata-search/README.md)
- [ADR-007: Semantic Type Routing](../../context/architecture/ADRs/ADR-007-semantic-type-routing.md)
- [ADR-008: Multi-Tenancy via SQLite Sharding](../../context/architecture/ADRs/ADR-008-multi-tenancy-sharding.md)
