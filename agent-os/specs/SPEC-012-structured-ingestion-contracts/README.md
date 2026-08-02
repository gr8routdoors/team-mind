# SPEC-012: Structured Ingestion Contracts

## Overview

Adds an external door — `submit_structured` — for pushing a **pre-refined record** (a fully-formed instance of a declared `record_type`) directly into the catalog, **validated against a JSON Schema** at the boundary. The caller (an AI agent in its own harness, or a deterministic tool) has already done the refinement; the framework validates, writes, and emits an event so subscribed observers react. This is the platform's **first schema enforcement** — today `RecordTypeSpec.schema` is an advisory dict validated by nothing.

The scope is intentionally small: routing, storage, observer subscription-by-`record_type`, and reliability seeding **already exist**. This spec adds a validated write endpoint on top of them.

## The three types (used precisely)

The framework already models three distinct types (SPEC-008 / ADR-007); earlier drafts conflated the last two, which this spec corrects:

- **`media_type`** — raw data format (`text/markdown`, `audio/wav`). *Not used on this path.*
- **`semantic_type`** — semantic identity of the *input* (`meeting`); routes raw input to refining plugins, and can fan out to many outputs. *Not used on this path.*
- **`record_type`** — the *refined output* record (`service_profile`). **The key for this spec** — the caller sends one directly, already refined, so routing is by `record_type` with no input-semantic fan-out to resolve.

## Motivation

The driver is the **Service Profile Plugin** (Phase 4): rather than build a plugin that clones a repo and derives a service profile, we let an AI agent produce the finished record in its own harness and push it here — validated and confidence-tiered. Keeps agents *out* of the framework, and is the primitive Meta-Plugins later build on.

## Scope

**In scope:**

- **`submit_structured(record_type, payload, uri, reliability_hint?, tenant_id?)`** MCP tool — validated push of one pre-refined record.
- **Opt-in enforcement per record type**: `RecordTypeSpec.submittable` makes its `schema` (a JSON Schema) the enforced caller contract. The schema describes the **payload = `metadata` sub-document** only; envelope fields are rejected by a registration guard.
- **Framework writes** the validated record via a **canonical `write_record` toolkit method** shared by the framework and plugins (prevents write-sprawl). It owns embedding (from a declared `embed_source`), content-hash, the reliability ladder, and idempotency.
- **`metadata` 1:1 with the payload**; envelope fields (`uri`, `id`, …) live on the containing record. JSON Schema is MongoDB-portable (`$jsonSchema`) for enforcement at scale.
- **Reliability seeding passthrough** (SPEC-007): `reliability_hint` is the top rung of the three-layer ladder, seeding `usage_score` so high-confidence facts rank up immediately.
- **Notify subscribers via the existing observer layer** — emit `IngestionEvent(record_type=…)`; `EventFilter.record_types` already fires the right observers. No new subscription mechanism.
- **Idempotency** via `IngestionContext` (SPEC-004/005), keyed on `uri`.
- **Registration**: one submittable **declarer** per `record_type`; discovery surfaces submittable types + schemas via `list_record_types`.
- **Dependency**: add `jsonschema` (currently zero validation deps); no build step.

**Out of scope:**

- **Raw content by-value ingestion** (pushing bytes inline instead of a URI) → **deferred SPEC-013**.
- **Framework-owned decoding / an intermediate format / a decode library** → **not built.** Decoding stays in plugins using standard Python libraries.
- **A plugin write-hook (`process_structured`)** → replaced by framework-writes + the shared `write_record` toolkit.
- **Push → parent/segment fan-out** → a pushed record is one stored record (v1).
- **Curation / validation-gate semantics** (the Curator) and **Meta-Plugin authoring** → separate milestones.

## Context

**References:**

- `src/team_mind_mcp/ingestion.py` — `IngestionPipeline` (adds `ingest_structured`), Phase 2 observer dispatch (already fires by `record_type`, `ingestion.py:233`).
- `src/team_mind_mcp/storage.py` — `save_payload` / `update_payload` (the write the toolkit wraps); `doc_weights` (reliability seeding).
- `src/team_mind_mcp/server.py` — `RecordTypeSpec` (gains `submittable`, `embed_source`), `EventFilter.record_types` (existing subscription), `PluginRegistry` (declarer uniqueness).
- `src/team_mind_mcp/discovery.py` — `list_record_types` (surfaces submittable schemas).
- SPEC-007 (reliability seeding), SPEC-008 / ADR-007 (three-type model), SPEC-004/005 (idempotency), SPEC-010 (metadata search), SPEC-011 (segments).
- Roadmap Phase 3 "Structured Ingestion Contracts"; Phase 4 "Service Profile Plugin(s)".

**Standards:**

- `testing`, `bdd` (deferred to the AC/BDD pass), `code-style/python`.
- Proposed **ADR-011: Structured Ingestion Contracts** — JSON Schema IDL; framework write + toolkit; `metadata` 1:1; the three-type clarification; field-naming/Mongo portability.

**Visuals:** None.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Scope = structured push only | one spec vs. push + raw + decoders | Routing/storage/observers/seeding already exist; the milestone is a validated write endpoint. Raw by-value → deferred SPEC-013; framework decoding → killed. |
| **JSON Schema as the IDL** | Protobuf vs. Pydantic vs. JSON Schema | JSON-native end to end; rich constraints in one lib; Mongo-native `$jsonSchema` at scale. |
| **Framework writes; plugins share `write_record`** | plugin `process_structured` hook vs. framework write + toolkit | A pushed record is already refined. One canonical write method (framework + plugins) prevents sprawl and stays evolvable. |
| Declarative `embed_source` | plugin embed hook vs. declared source | Lets the framework write directly; common case covered; complex embedding is future. |
| Route by `record_type` | `semantic_type` vs. `record_type` | The caller sends the refined output; `semantic_type` fan-out is a raw-path concern. |
| `metadata` 1:1 with payload | spread vs. sub-document | Contract = payload = `metadata`; envelope on the record; clean Mongo shape; renames are storage-breaking. |
| `uri` required (identity) | optional/hash-derived vs. required | Reuses SPEC-004/005 idempotency; enables updates. |
| Keep `reliability_hint` | drop vs. keep | Thin SPEC-007 passthrough; enables the confidence-tiering the Service Profile needs. |
| Reuse existing observers | new subscription vs. existing | `EventFilter.record_types` already fires subscribers on write. |

## Stories

> Stories, acceptance criteria, and BDD scaffolding are **deferred** to a follow-up pass. A provisional breakdown is in `design.md` → Execution Plan.

## Relationship to SPEC-013

Independent. **SPEC-013 (deferred)** covers *raw* content by-value ingestion (bytes inline instead of a URI, routed by `semantic_type`, decoded by plugins). This spec covers *refined-record* push only. Neither depends on the other.
