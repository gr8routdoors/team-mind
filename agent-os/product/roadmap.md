# Product Roadmap

## Phase 1: Core Information Architecture — COMPLETE

- **Central Knowledge Gateway:** MCP server with plugin registration and tool routing. *(SPEC-001)*
- **Bundle Ingestion Pipeline:** Two-phase pipeline — processors write, observers react. *(SPEC-001, SPEC-003)*
- **Embedded Storage Engine:** SQLite with `sqlite-vec` and JSON1, plugin-scoped record types, indexed columns. *(SPEC-001, SPEC-002)*
- **Trivial Plugin Proof-of-Concept:** Markdown semantic processor with chunking, embedding, and search. *(SPEC-001)*
- **Plugin Data Contracts:** Record type system with schemas, discovery tool, cross-plugin queries. *(SPEC-002)*
- **Plugin Developer Guide:** Documentation for building plugins — interfaces, storage modes, record types. *(SPEC-002, SPEC-003)*

## Phase 2: Intelligence & Weighting — COMPLETE

- **Usage-Based Ranking:** Cumulative moving average scoring with magnitude signals (-5 to +5). *(SPEC-004)*
- **Information Decay:** Plugin-declared decay half-life on record types, computed at query time. *(SPEC-004)*
- **Document Lifecycle:** In-place updates (`update_payload`) and wipe-and-replace (`delete_by_uri`). *(SPEC-004)*
- **Tombstoning:** Flag bad documents out of results without deletion, reversible. *(SPEC-004)*
- **Idempotent Ingestion:** Content hashing, plugin versioning, and IngestionContext for smart re-ingestion decisions. *(SPEC-005)*
- **Plugin Lifecycle Management:** Dynamic registration/unregistration at runtime, filtered event subscriptions (topic-based + fire hose), persistent plugin state. *(SPEC-006)*
- **Semantic Type Routing:** Three-type model (semantic type, media type, record type), registration-time routing, available vs enabled activation model. *(SPEC-008)*
- **Record Type Rename:** Renamed `doctype` → `record_type` throughout codebase — column, indexes, APIs, tests, and docs. *(SPEC-009)*

## Phase 3: Reliability & Extensibility — IN PROGRESS

- **Reliability Seeding:** Three-layer initial quality scoring — ingest hint (from caller), plugin-declared default on `RecordTypeSpec`, platform default (0.0). Seeds `usage_score` at ingestion time so high-quality sources rank higher immediately. Replaces the original inline Librarian concept (ADR-006). *(SPEC-007 — COMPLETE)*
- **Multi-Tenancy & Metadata Search:** Per-tenant SQLite file sharding via `TenantStorageManager`. Each tenant gets its own `data.sqlite` shard — KNN operates on exactly the right dataset by construction. Scatter-gather cross-tenant queries. Metadata search via `json_extract` equality filters on the existing `metadata` column. Optional vector query (weight-ranked retrieval when query is omitted). Plugin developer guide updated: plugins are tenant-unaware, use `bundle.storage`. *(SPEC-010 — COMPLETE)*
- **Document Segments:** Formal parent-child hierarchy on the `documents` table via `parent_id` column. Parents are metadata containers (no vector, no weight). Segments are searchable, ratable children. Aggregate parent scoring computed at query time (AVG of children). Cascade delete for parents, surgical `delete_by_id` for segments. URI convention for segment naming. Segment ordering guaranteed by insertion order (`ORDER BY id`). MarkdownPlugin migrated to parent-child model. *(SPEC-011 — COMPLETE)*
- **LLM Background Reaper:** Async post-ingestion process that scans for near-duplicate content across different URIs and cross-document contradictions. Covers both semantic deduplication (same fact, different URI) and conflict detection (contradicting facts). *(Future — see ADR-006)*
- **Meta-Plugins / Chained Processing:** Observer-triggered secondary ingestion enabling complex processing pipelines (e.g., dependency audit across code + POM output). *(Future — see ADR-007)*

## Phase 4: Scale & Integrations

- **Database Migration:** Move from SQLite to self-hosted MongoDB (or similar) for robust vector and document storage at scale.
- **Access Control & RBAC:** Add security layers for different project access levels.
- **MS Teams Integration:** Bot for querying and contributing knowledge directly from chat.
- **Additional Tooling Integrations:** Other workspace and developer tool integrations as the platform matures.
- **Frontend UI:** Lightweight JavaScript UI for human browsing and management of the knowledge graph.
