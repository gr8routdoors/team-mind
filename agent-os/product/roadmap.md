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
- **Structured Ingestion Contracts:** A declared, validated *inbound* schema that lets external providers — AI agents or deterministic tools — push **pre-structured facts** into the ingestion pipeline, distinct from raw-URI processing where the plugin self-extracts. Plugins declare an input contract; the pipeline validates provider-supplied payloads against it at the ingestion boundary. This is the platform's **first schema enforcement** — today `RecordTypeSpec.schema` is advisory and output-only, and the pipeline only accepts raw URIs. Foundational primitive: it is the mechanism both Meta-Plugins (internal re-ingestion) and external agent-populated plugins use to submit structured data. **Boundary:** this milestone covers the *input path only* — internal observer-driven chaining stays with Meta-Plugins. *(SPEC-012 — NEXT)*
- **LLM Background Reaper:** Async post-ingestion process that scans for near-duplicate content across different URIs and cross-document contradictions — semantic deduplication (same fact, different URI) and conflict detection (contradicting facts). This is the surviving form of the mission's "validation gate" differentiator (the inline Librarian was retired in ADR-006 in favor of background detection). **Independent capability — "not blocked by anything" (ADR-006); it depends on no other Phase 3 item and could be sequenced before or after them.** Service Profile edge-reconciliation is one *application* of it, not a dependency. Expect it to be a **capstone item, built 2nd or 3rd in M3**, and to take several iterations to dial in.
  - *Direction (to settle at spec time):* **Trigger vs. execution are split** — an `IngestObserver` (SPEC-006 `EventFilter`) *enqueues* candidates on ingestion; a **separate async worker** runs the KNN + LLM analysis out-of-band (never inline; keeps the server LLM-free), with a periodic sweep as backstop. **It proposes, it does not silently dispose:** its ceiling of autonomous action is a *reversible* tombstone; **hard deletes are always human-gated**; high-reliability/"golden" docs are never auto-touched; confidence-tiered (high-confidence dups may auto-tombstone, contradictions escalate to human review). **v1 auto-deletes nothing** — detect + propose + human dispositions; auto-tombstone is a later iteration once precision is proven on real data. Paired with **Curation Audit & Review** (below) as its disposition surface.
  *(Future — see ADR-006)*
- **Curation Audit & Review:** Human-in-the-loop surface for automated/agent-driven curation. A moderation queue of proposed actions (approve/reject), a "recently tombstoned" report with one-click **restore** (un-tombstone is already reversible), and a provenance/audit trail — what acted, why, with what confidence, from what source — for every automated mutation. **Generalized beyond the Reaper:** Service Profile agent inferences and any future auto-curation feed the same review layer. **Coupled to the Reaper** (it is the Reaper's disposition half) — the two are sequenced together, not independently. *(Future)*
- **Meta-Plugins / Chained Processing:** Observer-triggered secondary ingestion enabling complex processing pipelines (e.g., dependency audit across code + POM output). Builds on Structured Ingestion Contracts as its submission mechanism. First concrete driver: agent synthesis of Service Profiles (Phase 4). *(Future — see ADR-007)*

## Phase 4: Scale & Integrations

- **Service Profile Plugin(s):** A machine-readable service catalog living inside Team Mind — per service: dependencies (internal + external), schemas/data shapes, **provides/consumes** integration contracts, and persisted data. Hybrid population: deterministic extractors (POM/`package.json`/OpenAPI/`.proto`/migrations) self-extract ground-truth facts; an AI agent supplies **inferred** facts (real consumers, intent) via Structured Ingestion Contracts. Stored as parent (service) + segments (facets) with reliability tiering — deterministic facts high/no-decay, inferred facts lower/decaying. Starts as a single plugin with snap-in per-language extractors; graduates to a per-language plugin family. **Depends on SPEC-012; drives Meta-Plugins (agent synthesis); provides the Reaper an application (edge reconciliation) — not a dependency in either direction.**
- **Database Migration:** Move from SQLite to self-hosted MongoDB (or similar) for robust vector and document storage at scale.
- **Access Control & RBAC:** Add security layers for different project access levels.
- **MS Teams Integration:** Bot for querying and contributing knowledge directly from chat.
- **Additional Tooling Integrations:** Other workspace and developer tool integrations as the platform matures.
- **Frontend UI:** Lightweight JavaScript UI for human browsing and management of the knowledge graph.
