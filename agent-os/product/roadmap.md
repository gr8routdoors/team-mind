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

- **Reliability Seeding:** Three-layer initial quality scoring (ingest hint, plugin default, plugin override). Replaces the original inline Librarian concept — see ADR-006. *(SPEC-007 — IN DESIGN)*
- **Background Conflict Detection:** External reaper process using LLM inference to detect contradictions across documents. Runs asynchronously post-ingestion. *(Future — see ADR-006)*
- **Semantic Deduplication:** Detect near-duplicate content across different URIs using vector similarity thresholds. *(Future)*
- **Meta-Plugins / Chained Processing:** Observer-triggered secondary ingestion enabling complex processing pipelines (e.g., dependency audit across code + POM output). *(Future — see ADR-007)*

## Phase 4: Scale & Enterprise

- **Database Migration:** Move from SQLite to self-hosted MongoDB (or similar) for robust vector and document storage at scale.
- **Access Control & RBAC:** Add security layers for different project access levels.
- **Team Integrations:** MS Teams bot for querying and contributing knowledge directly from chat.
- **Frontend UI:** Lightweight JavaScript UI for human browsing and management of the knowledge graph.
