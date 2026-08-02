# SPEC-012: Structured Ingestion Contracts — Design

## Overview

Adds an external door for pushing a **pre-refined record** — a fully-formed instance of a declared `record_type` — directly into the catalog, validated against a schema at the boundary. The caller (an AI agent in its own harness, or a deterministic tool) has already done the refinement; the framework validates the payload, writes it, and emits an event so subscribed observers react. This is the platform's **first schema enforcement**: today `RecordTypeSpec.schema` is an advisory dict validated by nothing.

The scope is deliberately small because most of the machinery already exists — routing, storage, observer subscription-by-record_type, and reliability seeding are all in place. This spec adds a validated write endpoint on top of them.

## The three types (vocabulary — use precisely)

The framework already models three distinct types (SPEC-008 / ADR-007). They must not be conflated:

| Type | Meaning | Example | Role here |
|------|---------|---------|-----------|
| `media_type` | raw data format | `text/markdown`, `audio/wav` | relevant only to the raw-content story, not the push path |
| `semantic_type` | semantic identity of the *input* | `meeting`, `service_repo` | routes raw input to refining plugins; **not** used on the push path |
| `record_type` | the *refined output* record | `service_profile`, `meeting_metrics` | **the key for this spec** — the caller sends one directly |

One `semantic_type` can fan out to many `record_type`s (a `meeting` → `meeting_metrics` + `architecture_strawman`), but that fan-out is a *raw-ingestion* concern. On the **structured-push path the caller has already refined to one `record_type`**, so routing is by `record_type` — no input-semantic fan-out to resolve.

## Data Flow

```
caller → submit_structured(record_type, payload, uri, reliability_hint?, tenant_id?)
  → IngestionPlugin.call_tool
    → IngestionPipeline.ingest_structured
       1. spec = registry.get_submittable_spec(record_type)         # the one declarer, or error
       2. ctx = build IngestionContext(uri, record_type)           # SPEC-004/005 idempotency (insert vs update)
       3. doc_id = toolkit.write_record(                            # VALIDATES then writes (single choke point)
             storage, record_type, payload, uri, tenant, spec=spec,
             reliability_hint=reliability_hint, context=ctx)
             #  -> validate_record(payload, spec.schema)  # ALWAYS; REJECT on failure, nothing written
             #  -> embed (from embed_source) + content_hash + reliability ladder + idempotent save_payload
       4. emit IngestionEvent(record_type=..., doc_ids=[doc_id], semantic_types=spec.semantic_types)
       5. existing observer Phase 2 fires subscribers (EventFilter.record_types)  # UNCHANGED
```

No new subscription mechanism, no plugin write-hook, **no separate validation step** — validation lives inside `write_record`. Rejection is **strict and atomic**: a schema failure returns structured errors and writes nothing. `submit_structured` is a thin external caller of `write_record`; the pipeline logic above is nearly all of it.

## The canonical write path (plugin toolkit)

To prevent write-sprawl (the framework writing one way, plugins another), record writes go through **one** method in a plugin toolkit/SDK, used by the framework on this path and available to plugins on other paths (raw ingestion, future meta-plugins):

```python
# team_mind_mcp.toolkit (new)
def write_record(
    storage, record_type: str, payload: dict, uri: str, tenant_id: str,
    *, spec: RecordTypeSpec, reliability_hint: float | None = None,
    context: IngestionContext | None = None, parent_id: int | None = None,
) -> int:
    """Canonical record write. Owns, in order:
       - VALIDATION: validate_record(payload, spec.schema) ALWAYS; REJECT on failure (nothing written).
                     The single validation choke point — every record type declares a schema.
       - embedding: derive text from spec.embed_source (if declared) and embed; else no vector
       - content_hash over the payload
       - reliability seeding ladder: reliability_hint -> spec.default_reliability -> 0.0  (SPEC-007)
       - idempotency: insert vs update_payload based on `context`
       - save_payload(metadata=payload, ...)  # payload stored 1:1 as the metadata sub-document
    """
```

**Validation is universal, for free.** Because `write_record` is the one write path, *every* record — pushed externally via `submit_structured` **or** written by a plugin refining raw input — is validated against its record type's published schema. Every record type has an enforced schema, so no path can write garbage, and the external endpoint needs no validation logic of its own. Both the framework (push) and any plugin (raw/meta) call `write_record` — a single, evolvable, self-validating write contract.

**Enforcement is mandatory — no opt-out.** Every record type declares a JSON Schema and every write is validated. We are pre-release with no published plugins, so there is no legacy to grandfather; and MongoDB's `$jsonSchema` will enforce at the store anyway, so enforcing at the framework now avoids a jarring change for future adopters. Registration **rejects a record type with a missing or empty schema**. The existing MarkdownPlugin is brought into compliance as part of this spec (real schemas; `metadata` aligned to payload-only). `submittable` is a *separate* axis — it controls only external push exposure, not whether validation happens.

## Embedding on the push path

The record type declares an optional **embed source** — the field path(s) whose text is vectorized:

- `spec.embed_source` set → `write_record` embeds that text; the record is vector-searchable.
- `spec.embed_source` absent → no vector; the record is a metadata-only document, still findable via SPEC-010 metadata search.

This keeps the framework able to write directly (no plugin logic needed). Push→parent/segment fan-out is **out of scope for v1** — a pushed record is one stored record.

## API Contracts

### `submit_structured` (new MCP tool)

```jsonc
{
  "name": "submit_structured",
  "description": "Submit a pre-refined record for validated ingestion against its record type's JSON Schema.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "record_type":     { "type": "string", "description": "The refined record type being submitted (routing key)." },
      "payload":         { "type": "object", "description": "The record as JSON; validated against the record type's schema. Stored 1:1 as the metadata sub-document." },
      "uri":             { "type": "string", "description": "Identity key for idempotency / updates (required)." },
      "reliability_hint":{ "type": "number", "description": "Optional confidence seed (0.0–1.0); top rung of SPEC-007 reliability seeding." },
      "tenant_id":       { "type": "string", "description": "Tenant (default: 'default')." }
    },
    "required": ["record_type", "payload", "uri"]
  }
}
```

Single record per call (v1). On validation failure, structured `jsonschema` errors; nothing written.

### `RecordTypeSpec` (extended)

```python
@dataclass
class RecordTypeSpec:
    name: str
    description: str
    schema: dict = field(default_factory=dict)     # MANDATORY JSON Schema — enforced on every write
    plugin: str = ""
    decay_half_life_days: float | None = None
    default_reliability: float | None = None        # existing — middle rung of the reliability ladder
    submittable: bool = False                        # NEW — exposed to external submit_structured push (does NOT gate validation)
    embed_source: list[str] | None = None            # NEW — field path(s) to vectorize; None = metadata-only
```

`schema` is a **mandatory** JSON Schema, enforced on **every** write regardless of `submittable`. It describes the `metadata` sub-document (payload) only and must not declare envelope fields (`id`, `uri`, `plugin`, `content_hash`, `vector`, `tenant`). A registration guard rejects both envelope-field declarations **and** a missing/empty schema. `submittable` controls only whether external callers may push this record type via `submit_structured`; internal-only record types are still validated on every plugin write.

### Validator (new)

```python
def validate_record(payload: dict, schema: dict) -> list[str]:
    """Validate payload against a JSON Schema; return [] if valid, else structured error strings."""
```

A single function, called **inside `write_record`** — not a separate pipeline step and not a multi-dialect registry. (A `PayloadValidator` seam is unnecessary ceremony at this scope; JSON Schema is the IDL.)

## Raw content by-value (one story, folded in)

A small adjacent capability: let a caller supply raw bytes inline instead of a URL. `ingest_documents` items may carry `{uri, content, media_type}`; when `content` is present the pipeline uses it directly (no fetch), else it fetches as today. `media_type` is required when `content` is present. Everything downstream — decode, interpret, write — is unchanged and stays **in the plugin** (decoding uses standard Python libraries; there is no framework decoder). This is roughly a few lines threaded through the bundle, hence a story here rather than its own spec.

## Reliability seeding (SPEC-007 passthrough)

`reliability_hint` is the top of the existing three-layer ladder, resolved in `write_record`:

1. `reliability_hint` (caller) → 2. `spec.default_reliability` → 3. `0.0` (platform).

The resolved value is `save_payload(initial_score=...)`, seeding `doc_weights.usage_score`, which feeds ranking (`WEIGHT_INFLUENCE`). Effect: a high-confidence pushed fact ranks up immediately. No new machinery — a passthrough to SPEC-007.

## Storage & Serialization — `metadata` is 1:1 with the payload

- **Envelope fields** — `uri`, `id`, `record_type`, `plugin`, `content_hash`, `plugin_version`, `semantic_type`, `media_type`, `parent_id` (+ vector, weights) — live on the **containing record** (columns today, Mongo top-level fields later).
- **`metadata`** is the **sub-document**, stored **1:1 with the validated payload** (`json.dumps` into the `metadata` column; a nested sub-document in Mongo).

A record type's **JSON Schema describes exactly the `metadata` sub-document**. At Mongo scale `$jsonSchema` can enforce it directly. No storage-schema change; the only binary in the store remains the embedding vector.

## Field Naming & Namespacing

Two namespaces; the contract owns only the payload.

- **Envelope** (framework-owned): record-level fields above — not in the contract.
- **Payload** (contract-owned): JSON Schema properties = `metadata` keys, 1:1, `snake_case`.

Rules: (1) `snake_case` payload keys; (2) 1:1, no aliasing — a schema property *is* the stored key; (3) never flatten — keep payload nested under `metadata`. Rule 3 prevents envelope/`_id` collisions (`metadata.uri` ≠ envelope `uri`) and makes SQLite→Mongo a query remap (`json_extract(metadata,'$.k')` → `{"metadata.k": ...}`). **Consequence:** we store/query by name, so payload **renames are storage-breaking** (adds are safe). Mongo `_id` mapping is an envelope/migration decision, IDL-independent.

## Registration & routing

- A record type is **submittable** iff `RecordTypeSpec.submittable` is `True`. Its declaring plugin is the single **declarer**.
- `PluginRegistry.register` enforces **one submittable declarer per record_type** (raises `ValueError`; mirrors the tool-collision check at `server.py:134`).
- Non-submittable record types are unaffected and may still be produced by multiple plugins.
- `submit_structured` routes `record_type → its declarer's spec → validate → write`. Subscribers are notified by the existing observer layer (`EventFilter.record_types`).

## Data model changes

**None.** Uses the existing `documents.metadata` + vector + weight rows via `save_payload`.

## Dependencies

`pyproject.toml` gains `jsonschema` (currently zero validation deps). No build step, no codegen.

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Scope = one spec (push + raw-content story) | multiple specs vs. one | Routing/storage/observers/seeding already exist; the milestone is a validated write endpoint plus a small raw-by-value story. Framework decoding → rejected. |
| JSON Schema IDL | Protobuf vs. Pydantic vs. JSON Schema | JSON-native end to end; rich constraints in one lib; Mongo-native `$jsonSchema`. |
| Framework writes; plugins share the write method | plugin `process_structured` hook vs. framework write + toolkit | A pushed record is already refined; the framework writes it. One canonical `write_record` (framework + plugins) prevents write-sprawl. |
| Validation lives inside `write_record` | validate in the endpoint vs. in the write method | Single choke point → external push AND plugin writes both validated against the published schema for free; the endpoint carries no validation logic. |
| **Validation is mandatory — no opt-out** | opt-in per record type vs. mandatory | Pre-release, so no legacy to grandfather; Mongo `$jsonSchema` will enforce at the store anyway. Every record type must declare a schema; MarkdownPlugin is made compliant here. `submittable` no longer gates validation (external-exposure only). |
| Raw content by-value = one story here | separate SPEC-013 vs. a story in this spec | Inline bytes vs. a URL is a few lines on the existing raw path; it doesn't earn a spec. SPEC-013 retired. |
| Declarative `embed_source` | plugin embed hook vs. declared source | Lets the framework write directly; covers the common case; complex embedding is future. |
| Route by `record_type` | `semantic_type` vs. `record_type` | The caller sends the refined output; `semantic_type` fan-out is a raw-path concern. |
| `metadata` 1:1 with payload | spread vs. sub-document | Contract = payload = `metadata`; envelope on the record; clean Mongo shape. |
| `uri` required (identity) | optional/hash-derived vs. required | Reuses SPEC-004/005 idempotency; enables updates; motivating case has a natural identity. |
| No `semantic_types` param on the tool | keep vs. drop | Not routing here; observer labels come from the declarer's `semantic_type`. |
| Keep `reliability_hint` | drop vs. keep | Thin passthrough to SPEC-007; enables confidence-tiering the Service Profile needs. |
| Single submittable declarer per record_type | multi vs. single | Unambiguous schema/write owner; caught at registration. |

## Compatibility

- `ingest_documents(uris=[...])` unchanged (plus the folded-in inline-content story).
- `RecordTypeSpec` gains `submittable`/`embed_source`, and `schema` becomes mandatory-and-enforced. There is **no external legacy** (pre-release), so mandatory validation is not a breaking change for adopters.
- **MarkdownPlugin is migrated in-spec** to a compliant, enforced schema (`metadata` reduced to payload-only; envelope fields removed from `metadata`). This is the only existing plugin affected.
- No storage-schema migration; the raw/extract path is otherwise unchanged.

---

## Execution Plan

Provisional (stories/ACs to follow).

### Task 1: Validator + mandatory schema declaration
- Add `jsonschema`; `validate_record`.
- `RecordTypeSpec`: `schema` mandatory + `submittable` + `embed_source`.
- Registration guard: reject a missing/empty schema **and** a schema that declares envelope fields; single submittable-declarer uniqueness.
- Registry: `get_submittable_spec(record_type)`.

### Task 2: Canonical write path (toolkit) — with built-in validation
- `toolkit.write_record(...)` — **validation first** (`validate_record` against the enforced schema; reject on failure), then embedding (from `embed_source`), content_hash, reliability ladder (SPEC-007), idempotency (SPEC-004/005), `save_payload`/`update_payload`.
- `validate_record(payload, schema)` via `jsonschema`.

### Task 3: `submit_structured` tool + pipeline entry
- `IngestionPipeline.ingest_structured(...)` (validate → context → write → emit event).
- `submit_structured` on `IngestionPlugin`; strict error surfacing.
- Confirm existing observer Phase 2 fires by `record_type`.

### Task 4: Discovery
- Surface submittable record types + their JSON Schema in `list_record_types`.

### Task 5: Reference submittable plugin (test/example)
- A minimal plugin declaring a submittable record type + JSON Schema, exercising `submit_structured` end-to-end (pass + reject), independent of the Service Profile work.

### Task 6: MarkdownPlugin compliance
- Give `markdown_source` / `markdown_chunk` real, enforced JSON Schemas; remove envelope fields (e.g. `plugin`) from `metadata`.
- Route its writes through `write_record` so they are validated like everything else; verify SPEC-011 parent/segment parity.

### Task 7: Raw content by-value (folded-in story)
- Extend the `ingest_documents` item shape to `{uri, content?, media_type?}`; use inline `content` when present (no fetch), require `media_type` with it, keep `uri` as identity.
- Thread inline content through the bundle so plugins receive it; decoding stays in-plugin.

### Task 8: Documentation
- Plugin developer guide (submittable record types, `write_record` toolkit, embed_source, metadata 1:1, field-naming, the three-type vocabulary).
- System overview + ingestion diagrams; fix `record_type`/`semantic_type` conflation.
- Author proposed **ADR-011** (structured ingestion contracts; JSON Schema IDL; framework write + toolkit; metadata 1:1; three-type clarification).
