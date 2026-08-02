# SPEC-012: Structured Ingestion Contracts

## Overview

Adds a **by-value ingestion boundary** so external producers — AI agents in their own harness, or deterministic tools — can push content *directly* into the pipeline instead of only handing us a URI to fetch. Two payload shapes travel through the same door: **inline raw content** (bytes the framework decodes, then a plugin interprets) and a **pre-structured record** (a finished output record the framework validates against a **protobuf contract**, then a plugin stores). This introduces the platform's **first schema enforcement**: today `RecordTypeSpec.schema` is an advisory, output-only dict validated by nothing, and the ingestion boundary accepts nothing but URIs.

The record contract IDL is **protobuf** (proto3) with **protovalidate** (CEL) for field constraints — typed, cross-language, and service-shaped from day one. Proto is a validation/interchange layer, not the storage format: records persist as canonical JSON in `documents.metadata` (so SPEC-010 metadata search keeps working). See `design.md` for the full IDL, storage, and field-naming treatment.

## The organizing idea

The axis this spec introduces is **content by value vs. content by reference**. Today ingestion is by reference only (`ingest_documents(uris)` — the pipeline fetches). Payload-vs-URI is a *storage-optimization* concern (don't become the enterprise mega-bucket), already reflected at the storage layer where `save_payload(uri, metadata, ...)` persists a structured record. What is missing is an **external door** to submit content by value. This spec opens that door with a validation gate in front of it.

On the by-value side there are two payload types, and they map cleanly onto **two validation gates** (both framework-owned, both at the pipeline boundary — never re-implemented per plugin):

| Payload type | What the caller sends | Gate | Then |
|--------------|-----------------------|------|------|
| Inline raw content | bytes + a declared `media_type` | **Format / well-formedness** ("is this actually the format you claimed?") | plugin interprets → embed → write |
| Structured record | a finished output record (JSON) | **Record-schema conformance** (parse into the record type's proto message + `protovalidate` constraints) | plugin maps → embed → write |

The razor separating framework work from plugin work is **decode vs. interpret**: the framework does the lossless, deterministic part (decode bytes into a faithful structure; validate a record against its proto contract and normalize it); the plugin does the lossy, judgment part (chunking, picking embedding text, fanning out to parent + segments). See SPEC-013, which generalizes the decode side into a pluggable subsystem.

## Motivation

The first concrete driver is the **Service Profile Plugin** (Phase 4). A service profile — outgoing dependencies, service calls, data shapes — is a canonical record we store. We could build a plugin that clones a Java repo and derives it deterministically. Or we let an **AI agent** (better at inferring real consumers and intent) produce that record in *its own* harness and hand us the finished output. This spec is the submission mechanism for exactly that — and it keeps AI agents *out* of our framework (they stay in the caller's harness). It is also the primitive that Meta-Plugins (internal re-ingestion) will later build on.

## Scope

**In scope:**

- New **`submit_structured`** MCP tool — method-clear by name — accepting a pre-structured record: `record_type`, `payload`, and optional `uri` (identity key), `semantic_types`, `reliability_hint`, `tenant_id`.
- **By-value inline content** on the raw/extract path: content supplied directly (`content` + declared `media_type`), with `uri` as the identity key. If `content` is absent, the pipeline fetches the URI as today. (Inline content *forces* decode into the framework — a plugin cannot fetch a URI that was never given.)
- A **record-schema validator behind a `PayloadValidator` seam** — one implementation, `ProtoRecordValidator` (parse JSON→proto message → `protovalidate` → normalized dict). Single IDL, not a multi-dialect registry; the seam only keeps the IDL from being hardwired. Plus the trivial format decoders for inline content (JSON, text). No per-plugin validation.
- **Opt-in structured ingestion per record type**: a record type declares itself *submittable* and references a **proto message** whose `.proto` (with `protovalidate` options) is the enforced caller contract. The message describes **payload** fields only; system-managed/envelope fields (`id`, `vector`, `plugin`, `content_hash`, `uri`, `tenant`, weight) are **never** part of it (a registration guard rejects a contract that declares them).
- **Field naming & namespacing**: payload keys come from the proto message, pinned `snake_case` (`preserving_proto_field_name=True`), stored 1:1 under the `metadata` namespace — never flattened. This isolates the proto-owned payload namespace from framework-owned envelope fields and keeps the SQLite→MongoDB migration a query-syntax remap. Payload field *renames* are storage-breaking (adds are safe).
- A new processor hook — **`process_structured(submission)`** — receiving the *validated* payload. The plugin owns interpretation, embedding, and the write (`save_payload`), including any parent/segment fan-out.
- **Registration-time uniqueness**: exactly one structured-owner per submittable `record_type`, enforced with a collision error (mirrors the existing tool-collision check).
- **Routing by `record_type`** — the semantic "what am I ingesting" key.
- **MarkdownPlugin migration**: stop self-fetching content; receive content from the framework; keep chunk/embed/write.
- **Discovery**: expose submittable record types and their proto contract (`.proto`/descriptor) through the existing `list_record_types` surface so agents know exactly what to send.
- **Dependencies**: add `protobuf` + `protovalidate` and a `.proto` build step (the codebase currently has zero validation deps) — the accepted ergonomic cost of the proto IDL.

**Out of scope:**

- The **rich multi-format decoder library** (markdown→AST, XML, YAML, protobuf, PDF). This spec ships the *seam* and trivial decoders only; **SPEC-013** generalizes it. New formats are onboarded per-need, not pre-built.
- **Internal observer-driven chaining / Meta-Plugins.** Roadmap boundary: this milestone is the **input path only**.
- **Bringing AI agents inside the framework.** Producers stay in their own harness.
- **Curation / validation-gate semantics** (the Curator). A structured submission that passes schema validation is accepted; catalog coherence is a separate, later milestone.
- Non-record-level validation such as cross-record referential integrity ("does this dependency reference a known service?"). The schema gate is structural; referential checks are future work.

## Context

**References:**

- `src/team_mind_mcp/ingestion_plugin.py` — current `ingest_documents` tool; the URI-only boundary this spec extends.
- `src/team_mind_mcp/ingestion.py` — `IngestionPipeline`, `IngestionBundle`, `ResourceResolver`; where the by-value path and validator seam attach.
- `src/team_mind_mcp/storage.py` — `save_payload(uri, metadata, vector, plugin, record_type, ...)`; proves structured records are already stored, just not accepted at the boundary.
- `src/team_mind_mcp/server.py` — `RecordTypeSpec` (gains opt-in enforcement), `IngestProcessor` (gains `process_structured`), `PluginRegistry` (owner-uniqueness check).
- `src/team_mind_mcp/markdown.py` — the one real processor; migrated to receive content instead of fetching.
- `src/team_mind_mcp/discovery.py` — `list_record_types`; extended to surface submittable contracts.
- `src/team_mind_mcp/media_types.py` — media-type resolution; the format gate reuses/extends it.
- `agent-os/specs/SPEC-013-pluggable-format-decoders/` — the decode subsystem this spec seeds.
- Roadmap Phase 3, "Structured Ingestion Contracts"; Phase 4 "Service Profile Plugin(s)" (the driving consumer).

**Standards:**

- `testing` — TDD principles and coverage.
- `bdd` — AC format and coverage patterns (deferred to the AC/BDD pass).
- `code-style/python` — Python conventions.
- Proposed **ADR-011: Structured Ingestion Contracts** — records the protobuf IDL + protovalidate choice, the input≡output-at-metadata reframe, the two-gate model, and the field-naming/namespacing + Mongo-portability rules.

**Visuals:** None.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Separate `submit_structured` tool | New tool vs. a `mode` flag on `ingest_documents` | The two paths differ in routing key, plugin behavior, and failure semantics. The tool name *is* the method clarity; keeps the existing URI path untouched. |
| **Protobuf as the single IDL** | JSON Schema vs. Pydantic vs. Protobuf | Typed, cross-language, service-shaped from day one; aligns with the Phase-4 Service Profile direction. Pydantic is Python-bound; JSON Schema is JSON-only and taxes us over time. |
| **protovalidate for constraints** | proto-types only vs. + CEL | proto3 enforces types/shape, not required/ranges/patterns; protovalidate closes the gap and only fires on annotated fields. |
| **Proto validates, JSON persists** | store binary proto vs. store JSON | Binary would forfeit `json_extract` metadata search (SPEC-010). Proto's value here is normalization, not speed. |
| **snake_case + 1:1 names + nested `metadata`** | camelCase / flattened / aliased | Predictable query shape; no envelope/`_id` collisions; SQLite↔Mongo is a query remap, not a reshape. Payload renames are storage-breaking. |
| Validate against the record's contract | Distinct input-schema artifact vs. the record's proto | The agent hands us the *finished record*. Input ≡ output at the `metadata` level; a parallel input-schema type is an architectural smell. |
| Exclude system-managed fields from the contract | Full-row schema vs. payload-only | Caller supplies payload; framework/plugin still stamp `vector`, `plugin`, `content_hash`, `uri`, `tenant`, weight. Registration guard enforces it. |
| Validation at the pipeline boundary | Per-tool / per-plugin vs. pipeline-level | Single enforcement point, DRY, plugins never re-validate — the original design goal. |
| Opt-in `submittable` | Global enforcement vs. per-record-type opt-in | Existing advisory schemas include derived/owner fields; global enforcement would reject valid internal writes. |
| Plugin does write + embed | Framework writes via `save_payload` vs. plugin `process_structured` | Embedding is a projection choice (what text to vectorize, how to fan out) — same decode-vs-interpret razor. Belongs with the plugin. |
| Route by `record_type`, single owner | Explicit contract name vs. record_type; multi-owner vs. single | `record_type` is the semantic "what am I ingesting" key. A submittable record type needs one unambiguous handoff target; enforced at registration. |
| Include inline-by-value in this spec | Structured-record only vs. both payload types | Inline raw content is the *same door* and shares the validator seam; it also *forces* decode into the framework, which SPEC-013 then generalizes. Splitting it out would be an artificial seam. |

## Stories

> Stories, acceptance criteria, and BDD scaffolding are intentionally **deferred** to a follow-up shaping pass (per session decision — capture design first). A provisional breakdown lives in `design.md` → Execution Plan. `stories.yml` will be created then.

## Relationship to SPEC-013

SPEC-012 ships the **seam** (framework-owned decode + validate at the boundary) plus the trivial decoders it needs. **SPEC-013** generalizes the decode half into a first-class, pluggable `ContentDecoder` subsystem and migrates format parsing out of plugins. SPEC-013 depends on this spec's seam; this spec does not depend on SPEC-013.
