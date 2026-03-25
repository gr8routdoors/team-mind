# Product Roadmap

## Phase 1: MVP (Core Information Architecture) — COMPLETE
- **Central Knowledge Gateway:** MCP server with plugin registration and tool routing. *(SPEC-001)*
- **Bundle Ingestion Pipeline:** Two-phase broadcast pipeline — processors write, observers react. *(SPEC-001, SPEC-003)*
- **Embedded Storage Engine:** SQLite with `sqlite-vec` and JSON1, plugin-scoped doctypes, indexed columns. *(SPEC-001, SPEC-002)*
- **Trivial Plugin Proof-of-Concept:** Markdown semantic processor with chunking, embedding, and search. *(SPEC-001)*
- **Plugin Data Contracts:** Doctype system with schemas, discovery tool, cross-plugin queries. *(SPEC-002)*
- **Plugin Developer Guide:** Documentation for building plugins — interfaces, storage modes, doctypes. *(SPEC-002, SPEC-003)*

## Phase 2: Intelligence & Weighting — IN PROGRESS
- **Usage-Based Ranking:** Cumulative moving average scoring with magnitude signals (-5 to +5). *(SPEC-004 — COMPLETE)*
- **Information Decay:** Plugin-declared decay half-life on doctypes, computed at query time. *(SPEC-004 — COMPLETE)*
- **Document Lifecycle:** In-place updates (`update_payload`) and wipe-and-replace (`delete_by_uri`). *(SPEC-004 — COMPLETE)*
- **Tombstoning:** Flag bad documents out of results without deletion, reversible. *(SPEC-004 — COMPLETE)*
- **Semantic Deduplication:** Prevent duplicate content during ingestion. *(SPEC-005 — NOT STARTED)*

## Phase 3: Scale & Enterprise
- **Database Migration:** Move from SQLite to self-hosted MongoDB (or similar) for robust vector and document storage at scale.
- **Validation Pipeline (Librarian):** Implement LLM-as-a-judge to detect conflicts and verify facts during transcript/meeting ingestion.
- **Access Control & RBAC:** Add security layers for different project access levels.
- **Team Integrations:** MS Teams bot for querying and contributing knowledge directly from chat.
- **Frontend UI:** Lightweight JavaScript UI for human browsing and management of the knowledge graph.
