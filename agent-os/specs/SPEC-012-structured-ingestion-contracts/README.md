# SPEC-012: Structured Ingestion Contracts

## Overview

Adds a **by-value ingestion boundary** so external producers — AI agents in their own harness, or deterministic tools — can push content *directly* into the pipeline instead of only handing us a URI to fetch. Two payload shapes travel through the same door: **inline raw content** (bytes the framework decodes, then a plugin interprets) and a **pre-structured record** (a finished output record the framework validates against its schema, then a plugin stores). This introduces the platform's **first schema enforcement**: today `RecordTypeSpec.schema` is advisory and output-only, and the ingestion boundary accepts nothing but URIs.

## The organizing idea

The axis this spec introduces is **content by value vs. content by reference**. Today ingestion is by reference only (`ingest_documents(uris)` — the pipeline fetches). Payload-vs-URI is a *storage-optimization* concern (don't become the enterprise mega-bucket), already reflected at the storage layer where `save_payload(uri, metadata, ...)` persists a structured record. What is missing is an **external door** to submit content by value. This spec opens that door with a validation gate in front of it.

On the by-value side there are two payload types, and they map cleanly onto **two validation gates** (both framework-owned, both at the pipeline boundary — never re-implemented per plugin):

| Payload type | What the caller sends | Gate | Then |
|--------------|-----------------------|------|------|
| Inline raw content | bytes + a declared `media_type` | **Format / well-formedness** ("is this actually the format you claimed?") | plugin interprets → embed → write |
| Structured record | a finished output record | **Record-schema conformance** (validate against `RecordTypeSpec.schema`) | plugin maps → embed → write |

The razor separating framework work from plugin work is **decode vs. interpret**: the framework does the lossless, deterministic part (decode bytes into a faithful structure; validate a record against its schema); the plugin does the lossy, judgment part (chunking, picking embedding text, fanning out to parent + segments). See SPEC-013, which generalizes the decode side into a pluggable subsystem.

## Motivation

The first concrete driver is the **Service Profile Plugin** (Phase 4). A service profile — outgoing dependencies, service calls, data shapes — is a canonical record we store. We could build a plugin that clones a Java repo and derives it deterministically. Or we let an **AI agent** (better at inferring real consumers and intent) produce that record in *its own* harness and hand us the finished output. This spec is the submission mechanism for exactly that — and it keeps AI agents *out* of our framework (they stay in the caller's harness). It is also the primitive that Meta-Plugins (internal re-ingestion) will later build on.

## Scope

**In scope:**

- New **`submit_structured`** MCP tool — method-clear by name — accepting a pre-structured record: `record_type`, `payload`, and optional `uri` (identity key), `semantic_types`, `reliability_hint`, `tenant_id`.
- **By-value inline content** on the raw/extract path: content supplied directly (`content` + declared `media_type`), with `uri` as the identity key. If `content` is absent, the pipeline fetches the URI as today. (Inline content *forces* decode into the framework — a plugin cannot fetch a URI that was never given.)
- A **pluggable validator seam** at the pipeline boundary — a `ValidatorRegistry` keyed by format/dialect — hosting the two gates above. Ships a **JSON Schema** validator for structured records and the trivial decoders for the formats we have (JSON, text). No per-plugin validation.
- **Enforcement of `RecordTypeSpec.schema`**, **opt-in per record type**: a record type declares itself *submittable*, and its schema then defines the caller-supplied contract. System-managed fields (`id`, embedding `vector`, `plugin` owner, `content_hash`, `tenant`, weight row) are **never** part of that contract.
- A new processor hook — **`process_structured(submission)`** — receiving the *validated* payload. The plugin owns interpretation, embedding, and the write (`save_payload`), including any parent/segment fan-out.
- **Registration-time uniqueness**: exactly one structured-owner per submittable `record_type`, enforced with a collision error (mirrors the existing tool-collision check).
- **Routing by `record_type`** — the semantic "what am I ingesting" key.
- **MarkdownPlugin migration**: stop self-fetching content; receive content from the framework; keep chunk/embed/write.
- **Discovery**: expose submittable record types and their input schemas through the existing `list_record_types` surface so agents know exactly what to send.

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
- Proposed **ADR-011: Structured Ingestion Contracts** — to record the input≡output-at-metadata-level reframe and the two-gate validation model.

**Visuals:** None.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Separate `submit_structured` tool | New tool vs. a `mode` flag on `ingest_documents` | The two paths differ in routing key, plugin behavior, and failure semantics. The tool name *is* the method clarity; keeps the existing URI path untouched. |
| Validate against the **output** schema | Distinct input-schema artifact vs. reuse `RecordTypeSpec.schema` | The agent hands us the *finished output record*. Input and output are the same thing at the `metadata` level; a parallel input-schema type is an architectural smell. |
| Exclude system-managed fields from the contract | Full-row schema vs. caller-fields-only | Caller supplies semantic content; framework/plugin still stamp `vector`, `plugin`, `content_hash`, `tenant`, weight. Input ≡ output only at the `metadata` level. |
| Validation at the pipeline boundary | Per-tool / per-plugin vs. pipeline-level | Single enforcement point, DRY, plugins never re-validate — the original design goal. |
| Pluggable validator registry | Hardcoded JSON Schema vs. registry | Different formats/dialects need different validators; the registry is the seam SPEC-013 grows into. |
| Opt-in schema enforcement | Global enforcement vs. per-record-type opt-in | Existing schemas are advisory and include derived/owner fields; flipping global enforcement on would reject valid internal writes. |
| Plugin does write + embed | Framework writes via `save_payload` vs. plugin `process_structured` | Embedding is a projection choice (what text to vectorize, how to fan out) — same decode-vs-interpret razor. Belongs with the plugin. |
| Route by `record_type`, single owner | Explicit contract name vs. record_type; multi-owner vs. single | `record_type` is the semantic "what am I ingesting" key. A submittable record type needs one unambiguous handoff target; enforced at registration. |
| Include inline-by-value in this spec | Structured-record only vs. both payload types | Inline raw content is the *same door* and shares the validator seam; it also *forces* decode into the framework, which SPEC-013 then generalizes. Splitting it out would be an artificial seam. |

## Stories

> Stories, acceptance criteria, and BDD scaffolding are intentionally **deferred** to a follow-up shaping pass (per session decision — capture design first). A provisional breakdown lives in `design.md` → Execution Plan. `stories.yml` will be created then.

## Relationship to SPEC-013

SPEC-012 ships the **seam** (framework-owned decode + validate at the boundary) plus the trivial decoders it needs. **SPEC-013** generalizes the decode half into a first-class, pluggable `ContentDecoder` subsystem and migrates format parsing out of plugins. SPEC-013 depends on this spec's seam; this spec does not depend on SPEC-013.
