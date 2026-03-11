# Product Roadmap

## Phase 1: MVP (Core Information Architecture)
- **Central Knowledge Gateway:** Build the core Model Context Protocol (MCP) server shell, establishing the plugin registration and tool-routing system.
- **Bundle Ingestion Pipeline:** Implement the broadcast event loop where "Bundles" of "Resources" (files, URLs) are passed to plugins for processing.
- **Embedded Storage Engine:** Set up abstract interfaces backed by an embedded database (like SQLite with `sqlite-vec` and JSON1 extensions) to provide immediate Vector and Document storage without dev-ops overhead.
- **Trivial Plugin Proof-of-Concept:** Build one simple initial plugin (e.g., a basic Markdown semantic processor) to prove out the end-to-end ingestion, storage, and retrieval flows.

## Phase 2: Intelligence & Weighting
- **Usage-Based Ranking:** Implement utility scoring (+1/-1 feedback loops from AI/user usage).
- **Information Decay:** Add time-based decay algorithms so unused information naturally falls in relevance.
- **Semantic Deduplication:** Prevent duplicate notes during ingestion.

## Phase 3: Scale & Enterprise
- **Database Migration:** Move from local/flat-file storage to self-hosted MongoDB (or similar) for robust vector and document storage at scale.
- **Validation Pipeline (Librarian):** Implement LLM-as-a-judge to detect conflicts and verify facts during transcript/meeting ingestion.
- **Access Control & RBAC:** Add security layers for different project access levels.
- **Team Integrations:** MS Teams bot for querying and contributing knowledge directly from chat.
- **Frontend UI:** Lightweight JavaScript UI for human browsing and management of the knowledge graph.
