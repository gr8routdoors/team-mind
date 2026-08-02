# ADR-011: Structured Ingestion Contracts

**Status:** Accepted
**Date:** 2026-08-02
**Spec:** SPEC-012 (Structured Ingestion Contracts)
**See also:** [ADR-007: Three-Type Model & Semantic Type Routing](ADR-007-semantic-type-routing.md), [ADR-004: Idempotent Ingestion](ADR-004-idempotent-ingestion.md), [ADR-006: Reliability Seeding](ADR-006-reliability-seeding.md), [ADR-009: Document Segments](ADR-009-document-segments.md), [ADR-010: Tenant Sharding](ADR-010-tenant-sharding.md), [Plugin Developer Guide](../plugin-developer-guide.md)

## Context

Team Mind has always ingested data one way: hand the pipeline a URI, and an `IngestProcessor` plugin fetches, parses, chunks, embeds, and writes it. This is the **raw** path — the framework delivers bytes and routes; the plugin does all the refinement.

Two gaps had accumulated:

1. **No push path for already-refined records.** The motivating case is the Service Profile Plugin (roadmap Phase 4): rather than build a plugin that clones a repo and derives a service profile inside the framework, we want an AI agent to produce the finished record *in its own harness* and push it here. That record is already refined — there is nothing for a processor to parse. It just needs to be validated and stored. There was no door for that.

2. **No schema enforcement anywhere.** `RecordTypeSpec.schema` existed but was an advisory dict validated by nothing. A plugin (or a future external caller) could write structurally garbage `metadata` and the platform would accept it. For an external push endpoint — where the caller is outside the framework's control — validation is not optional.

Most of the machinery a push endpoint needs already exists: storage (`save_payload`), reliability seeding (SPEC-007), observer subscription-by-`record_type` (SPEC-008 `EventFilter.record_types`), and idempotency (SPEC-004/005). This decision adds a **validated write endpoint** on top of them, plus the first real schema enforcement, and folds in one small adjacent capability (raw content supplied by value).

### The three types, kept precise

The framework already models three distinct type concepts (ADR-007 / SPEC-008). Earlier drafts of this work conflated the last two; this ADR is explicit that they are different:

| Type | Meaning | Example | Role on this path |
|------|---------|---------|-------------------|
| `media_type` | raw data format | `text/markdown`, `audio/wav` | only the raw-content story, **not** the push path |
| `semantic_type` | semantic identity of the *input* | `meeting`, `service_repo` | routes raw input to refining plugins; **not** used on the push path |
| `record_type` | the *refined output* record | `service_profile`, `markdown_chunk` | **the key for this spec** — the caller sends one directly |

`record_type` is **not** `semantic_type`. A `semantic_type` describes what raw input *means* and can fan out to many `record_type`s (a `meeting` → `meeting_metrics` + `architecture_strawman`) — but that fan-out is a raw-ingestion concern. On the structured-push path the caller has *already refined* to exactly one `record_type`, so routing is by `record_type` with no input-semantic fan-out to resolve. A pushed record has no input `semantic_type`, so pushed events carry `semantic_types=[]` (see below).

## Decision

Add `submit_structured` — an MCP tool for pushing a batch of pre-refined records straight into the catalog, each validated against its `record_type`'s JSON Schema at the boundary — and make schema validation universal and mandatory by routing **all** writes through one canonical, self-validating method.

### 1. JSON Schema is the IDL

Every record type's contract is expressed as a **JSON Schema**. The schema describes the `metadata` sub-document (the payload) 1:1 and nothing else.

**Protobuf and Pydantic were considered and rejected.** The deciding factor is **MongoDB portability**: the store is SQLite today and MongoDB at scale, and MongoDB validates documents natively with `$jsonSchema`. A record type's JSON Schema can be handed to the collection unchanged and enforced *at the store*, so the framework's validation and the database's validation are the same artifact. Protobuf would introduce a codegen/build step and a binary wire format with no JSON-native store enforcement; Pydantic would couple the contract to Python classes and, again, give the store nothing to enforce. JSON Schema is JSON-native end to end, expresses rich constraints in one library (`jsonschema`, the only validation dependency added), and needs no build step or codegen.

**No binary storage.** JSON Schema does not introduce a binary format. The only binary that has ever lived in the store — the embedding vector — remains the only one. Payloads are stored as JSON (`json.dumps` into the `metadata` column today, a nested sub-document in Mongo later).

### 2. `write_record` — the single canonical write path and validation choke point

Record writes go through **one** method — `team_mind_mcp.toolkit.write_record` — used by the framework on the push path and available to plugins on every other path (raw ingestion, future meta-plugins). It owns, in order:

1. **Validation (always)** — `validate_record(payload, spec.schema)`; on failure it raises `RecordValidationError` and **writes nothing**.
2. **Embedding** — if the record type declares an `embed_source`, the text at those field paths is concatenated and vectorized; otherwise the record is stored with no vector (metadata-only, still findable via SPEC-010 metadata search).
3. **content_hash** over the canonical payload.
4. **Reliability ladder** (SPEC-007) — `reliability_hint` → `spec.default_reliability` → `0.0`.
5. **Idempotency** (SPEC-004/005) — insert a new row, or update the existing one in place (preserving `doc_id` and its weight row), based on the `IngestionContext` / storage lookup.
6. **Write** — payload stored 1:1 as `metadata`; envelope fields on the row.

Because `write_record` is the *one* write path, **validation is universal and free**: every record — pushed externally *or* written by a plugin refining raw input — is validated against its record type's published schema, so no path can write garbage and the external endpoint carries no validation logic of its own. Validation lives *inside* the write method, not as a separate pipeline step and not as a multi-dialect validator registry — a single function against a single IDL.

### 3. Mandatory schema for every record type; `submittable` is exposure only

Every `record_type` **must** declare a non-empty JSON Schema. A registration guard (`PluginRegistry._guard_record_types`) rejects a missing/empty schema for *any* record type, and additionally, for `submittable` types, rejects a schema that declares envelope fields and rejects a second submittable declarer of the same name.

**Enforcement is mandatory — there is no opt-out.** We are pre-release with no published plugins, so there is no legacy to grandfather; and MongoDB's `$jsonSchema` will enforce at the store anyway, so enforcing at the framework now avoids a jarring change for future adopters. The existing MarkdownPlugin — the only plugin affected — is brought into compliance in-spec: `markdown_source` and `markdown_chunk` get real schemas, its `metadata` is reduced to payload-only (no envelope fields), and its writes go through `write_record` so they are validated like everything else.

`submittable` is a **separate axis**. It controls *only* whether external callers may push a record type via `submit_structured`. It does **not** gate validation: internal-only record types (`submittable=False`) are still validated on every plugin write. There is no `semantic_types` field on `RecordTypeSpec` — routing on the push path is purely by `record_type` name.

### 4. `metadata` is 1:1 with the payload; envelope vs. payload namespacing

There are two namespaces, and the contract owns only one of them:

- **Envelope** (framework-owned) — `uri`, `id`, `record_type`, `plugin`, `content_hash`, `plugin_version`, `semantic_type`, `media_type`, `parent_id` (plus vector and weights). These live on the *containing record* (columns today, Mongo top-level fields later) and are **not** part of the contract.
- **Payload** (contract-owned) — the JSON Schema's properties *are* the `metadata` keys, 1:1, `snake_case`. A schema property is the stored key; there is no aliasing layer.

Three rules follow: (1) `snake_case` payload keys; (2) 1:1, no aliasing; (3) **never flatten** — the payload stays nested under `metadata`. Rule 3 is load-bearing for **MongoDB portability**: nesting prevents envelope/`_id` collisions (`metadata.uri` is distinct from the envelope `uri`) and makes the SQLite→Mongo transition a pure query remap (`json_extract(metadata,'$.k')` → `{"metadata.k": ...}`). The registration guard enforces the envelope/payload split for submittable types by rejecting envelope-field declarations in the schema.

**Consequence:** because we store and query by name, payload-field **renames are storage-breaking** (a rename orphans existing rows and stored queries) while additive fields are safe. Mongo `_id` mapping is an envelope/migration concern, independent of the IDL.

### 5. `submit_structured` — batch endpoint semantics

`submit_structured(records[], tenant_id?)` takes a batch, matching `ingest_documents`' array shape. Each item is `{record_type, payload, uri, reliability_hint?}`. Two semantics are fixed:

- **Strict per record, best-effort across the batch.** Each record is validated and written independently through `write_record`. An invalid record returns its structured `jsonschema` errors and writes nothing; a valid sibling still lands. There is **no all-or-nothing rollback** — a failing record never unwrites one that already persisted. This matches `ingest_documents`' best-effort nature and is more useful than failing a 500-record batch on one bad row.
- **An empty `records` list is an error.** At least one record is required (parity with `ingest_documents`); nothing is written.

The response is a per-record result list: `{uri, record_type, status: "written", doc_id}` on success, or `{..., status: "error", errors: [...]}` for a not-submittable or schema-invalid record. A single record is a one-element list.

`submit_structured` is a thin external caller of `write_record`: the pipeline entry (`IngestionPipeline.ingest_structured`) resolves the submittable spec per record, builds an idempotency context, calls `write_record`, collects an event, and after the loop broadcasts events to observers. The endpoint itself carries no validation or write logic.

### 6. Reliability seeding passthrough; observers fire by `record_type`

`reliability_hint` is a thin passthrough to the existing SPEC-007 ladder — it is the top rung (`reliability_hint` → `spec.default_reliability` → `0.0`), resolved inside `write_record` and seeded into `doc_weights.usage_score`. Effect: a high-confidence pushed fact ranks up immediately. No new machinery.

Subscribers are notified through the **existing** observer layer. After the batch loop, `ingest_structured` emits an `IngestionEvent(record_type=…, doc_ids=[…], semantic_types=[])` per written record and reuses the same Phase-2 broadcast as the raw path, so `EventFilter.record_types` fires the right observers. Pushed events carry `semantic_types=[]` — a pushed record has no input `semantic_type` — so observers filter these by `record_type` (or plugin). No new subscription mechanism. (If a semantic label on pushed events is ever wanted, that is a `RecordTypeSpec`-shape change, out of scope here.)

### 7. Raw content by value (folded-in story)

A small adjacent capability rides along: `ingest_documents` items may now be supplied by value. An item may carry `{uri, content, media_type}` — when `content` is present the pipeline uses it directly (no fetch), and `media_type` is required (an inline URI carries no extension to infer from); the `uri` remains the identity key. When `content` is absent the item is fetched by reference as before. Inline content is threaded through the bundle to processors; **decoding stays in the plugin**, using standard Python libraries.

### 8. What was rejected: framework-owned decoding / a universal IR

A framework-owned decoder subsystem — a decode library or intermediate representation the framework would produce for plugins — was **considered and rejected, not built.** There is no universal intermediate representation (JSON is a dict, XML is a tree, markdown is an AST); a framework decoder is therefore either a valueless wrapper over an existing library or a smuggled-in intermediate format that every plugin would have to un-convert. Decode *and* interpret both stay in plugins, using standard Python libraries. The framework only delivers bytes (by reference or by value) and routes. This is why the by-value capability is *one story*, not its own subsystem — and why the retired SPEC-013's two ideas resolved here: raw-content-by-value became this story, and the decoder subsystem was rejected outright.

## Alternatives Considered

### 1. Validate in the endpoint, not in the write method

Put validation logic in `submit_structured` itself.

**Rejected because:**
- It would validate only the push path; a plugin writing its own refined output could still write garbage.
- A single choke point inside `write_record` validates external push *and* every plugin write for free, and keeps the endpoint a thin caller with no logic to drift out of sync.

### 2. Opt-in validation per record type

Let a record type declare whether it wants validation.

**Rejected because:**
- We are pre-release — there is no legacy to grandfather — and MongoDB's `$jsonSchema` will enforce at the store regardless, so an opt-out would be a fiction the store overrides later.
- Universal enforcement is simpler to reason about: every record type has a schema, every write is checked. `submittable` remains a separate, orthogonal axis (external exposure only).

### 3. Protobuf or Pydantic as the contract language

Use Protobuf (with codegen) or Pydantic models as the record-type IDL.

**Rejected because:**
- Neither is natively enforceable by the target store. MongoDB validates with `$jsonSchema`; JSON Schema is the same artifact at the framework and at the store.
- Protobuf adds a codegen/build step and a binary wire format; Pydantic couples the contract to Python classes. JSON Schema is JSON-native end to end, needs no build step, and expresses rich constraints in one library.

### 4. A plugin write-hook (`process_structured`)

Give plugins a hook to receive and write pushed records.

**Rejected because:**
- A pushed record is already refined — there is nothing for a plugin to do but write it, which the framework can do directly via a declared `embed_source`.
- Framework-writes + the shared `write_record` toolkit prevents write-sprawl (the framework writing one way, plugins another) and keeps one evolvable, self-validating write contract.

### 5. All-or-nothing batch semantics

Roll back the whole batch if any record fails validation.

**Rejected because:**
- One bad row failing a 500-record batch is hostile and un-`ingest_documents`-like. Strict *per record* (an invalid record writes nothing and returns its errors) with best-effort *across* the batch is more useful and matches the existing raw endpoint.

### 6. Framework-owned decoder / intermediate representation

Build a decode library or IR the framework hands to plugins.

**Rejected because:**
- There is no universal IR across formats; the wrapper is either valueless or a smuggled-in format. Decode and interpret stay in plugins using standard libraries. (See Decision §8.)

## Consequences

### Positive

- **First real schema enforcement.** `RecordTypeSpec.schema` goes from advisory to enforced on every write, for every record type, via one choke point.
- **A validated external door.** `submit_structured` lets AI agents and deterministic tools push finished records without living inside the framework — the primitive the Service Profile Plugin and later Meta-Plugins build on.
- **No write-sprawl.** Framework and plugins share one canonical `write_record`; validation, embedding, hashing, seeding, and idempotency are implemented once.
- **MongoDB-ready by construction.** Payloads nest under `metadata`, schemas are `$jsonSchema`-portable, and the SQLite→Mongo move is a query remap, not a reshape.
- **Reuses existing layers.** Reliability seeding (SPEC-007), observer subscription (SPEC-008), idempotency (SPEC-004/005), and segments (SPEC-011) all compose unchanged.
- **No data-model change.** Uses the existing `documents.metadata` + vector + weight rows.

### Negative

- **Payload renames are storage-breaking.** Because we store and query by name (no aliasing), renaming a payload field orphans existing rows and stored queries. Additive changes are safe; renames need a migration.
- **A new dependency.** `jsonschema` is added (previously zero validation deps). No build step, but one more package.
- **Mandatory schemas are a hard requirement.** Every record type must ship a valid, non-empty schema or registration fails. Pre-release this is the right forcing function, but it is a real constraint on plugin authors.
- **Declarative `embed_source` covers only the common case.** The framework can embed from declared field paths; a record type needing complex/derived embeddings is not served on the push path (future work).

### Neutral

- **`submittable` is orthogonal to validation.** Making a record type non-submittable hides it from external push but changes nothing about how it is validated or written.
- **Pushed events carry `semantic_types=[]`.** Observers filter pushed records by `record_type` (or plugin); this is a consequence of routing by `record_type`, not a limitation to work around.
- **Push → parent/segment fan-out is out of scope for v1.** A pushed record is one stored record. The SPEC-011 parent/segment machinery is unchanged and still available to plugins on the raw path.
- **The raw path is otherwise unchanged.** By-value content is a few lines threaded through the existing bundle; by-reference ingestion behaves exactly as before.
