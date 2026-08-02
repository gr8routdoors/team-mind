# SPEC-012: Structured Ingestion Contracts — Design

## Overview

Adds an external door for pushing a **pre-refined record** — a fully-formed instance of a declared `record_type` — directly into the catalog, validated against a schema at the boundary. The caller (an AI agent in its own harness, or a deterministic tool) has already done the refinement; the framework validates the payload, writes it, and emits an event so subscribed observers react. This is the platform's **first schema enforcement**: today `RecordTypeSpec.schema` is an advisory dict validated by nothing.

The scope is deliberately small because most of the machinery already exists — routing, storage, observer subscription-by-record_type, and reliability seeding are all in place. This spec adds a validated write endpoint on top of them.

## The three types (vocabulary — use precisely)

The framework already models three distinct types (SPEC-008 / ADR-007). They must not be conflated:

| Type | Meaning | Example | Role here |
|------|---------|---------|-----------|
| `media_type` | raw data format | `text/markdown`, `audio/wav` | not used on this path (raw ingestion — future SPEC-013) |
| `semantic_type` | semantic identity of the *input* | `meeting`, `service_repo` | routes raw input to refining plugins; **not** used on the push path |
| `record_type` | the *refined output* record | `service_profile`, `meeting_metrics` | **the key for this spec** — the caller sends one directly |

One `semantic_type` can fan out to many `record_type`s (a `meeting` → `meeting_metrics` + `architecture_strawman`), but that fan-out is a *raw-ingestion* concern. On the **structured-push path the caller has already refined to one `record_type`**, so routing is by `record_type` — no input-semantic fan-out to resolve.

## Data Flow

```
caller → submit_structured(record_type, payload, uri, reliability_hint?, tenant_id?)
  → IngestionPlugin.call_tool
    → IngestionPipeline.ingest_structured
       1. spec = registry.get_submittable_spec(record_type)         # the one declarer, or error
       2. JsonSchemaValidator.validate(payload, spec.schema)        # REJECT on failure; nothing written
       3. ctx = build IngestionContext(uri, record_type)           # SPEC-004/005 idempotency (insert vs update)
       4. doc_id = toolkit.write_record(                            # the CANONICAL write path (see below)
             record_type, payload, uri, tenant,
             reliability_hint=reliability_hint, context=ctx)
       5. emit IngestionEvent(record_type=..., doc_ids=[doc_id], semantic_types=spec.semantic_types)
       6. existing observer Phase 2 fires subscribers (EventFilter.record_types)  # UNCHANGED
```

No new subscription mechanism, no plugin write-hook. Rejection is **strict and atomic** — a schema failure returns structured errors and writes nothing.

## The canonical write path (plugin toolkit)

To prevent write-sprawl (the framework writing one way, plugins another), record writes go through **one** method in a plugin toolkit/SDK, used by the framework on this path and available to plugins on other paths (raw ingestion, future meta-plugins):

```python
# team_mind_mcp.toolkit (new)
def write_record(
    storage, record_type: str, payload: dict, uri: str, tenant_id: str,
    *, reliability_hint: float | None = None, spec: RecordTypeSpec,
    context: IngestionContext | None = None, parent_id: int | None = None,
) -> int:
    """Canonical record write. Owns:
       - embedding: derive text from spec.embed_source (if declared) and embed; else no vector
       - content_hash over the payload
       - reliability seeding ladder: reliability_hint -> spec.default_reliability -> 0.0  (SPEC-007)
       - idempotency: insert vs update_payload based on `context`
       - save_payload(metadata=payload, ...)  # payload stored 1:1 as the metadata sub-document
    """
```

Both the framework (push) and any plugin (raw/meta) call `write_record` — a single, evolvable write contract. Existing plugins that call `save_payload` directly are migrated to it opportunistically (only MarkdownPlugin exists, and it stays on the raw path).

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
    schema: dict = field(default_factory=dict)     # advisory when not submittable; ENFORCED JSON Schema when submittable
    plugin: str = ""
    decay_half_life_days: float | None = None
    default_reliability: float | None = None        # existing — middle rung of the reliability ladder
    submittable: bool = False                        # NEW — opt-in structured push
    embed_source: list[str] | None = None            # NEW — field path(s) to vectorize; None = metadata-only
```

When `submittable`, `schema` is a JSON Schema enforced against the payload; it describes the `metadata` sub-document (payload) only and must not declare envelope fields (`id`, `uri`, `plugin`, `content_hash`, `vector`, `tenant`) — a registration guard rejects those.

### Validator (new)

```python
def validate_record(payload: dict, schema: dict) -> ValidationResult:
    """jsonschema.validate(payload, schema); collect structured errors."""
```

A single function — no multi-dialect registry. (A `PayloadValidator` seam is unnecessary ceremony at this scope; JSON Schema is the IDL.)

## Reliability seeding (SPEC-007 passthrough)

`reliability_hint` is the top of the existing three-layer ladder, resolved in `write_record`:

1. `reliability_hint` (caller) → 2. `spec.default_reliability` → 3. `0.0` (platform).

The resolved value is `save_payload(initial_score=...)`, seeding `doc_weights.usage_score`, which feeds ranking (`WEIGHT_INFLUENCE`). Effect: a high-confidence pushed fact ranks up immediately. No new machinery — a passthrough to SPEC-007.

## Storage & Serialization — `metadata` is 1:1 with the payload

- **Envelope fields** — `uri`, `id`, `record_type`, `plugin`, `content_hash`, `plugin_version`, `semantic_type`, `media_type`, `parent_id` (+ vector, weights) — live on the **containing record** (columns today, Mongo top-level fields later).
- **`metadata`** is the **sub-document**, stored **1:1 with the validated payload** (`json.dumps` into the `metadata` column; a nested sub-document in Mongo).

A submittable record type's **JSON Schema describes exactly the `metadata` sub-document**. At Mongo scale `$jsonSchema` can enforce it directly. No storage-schema change; the only binary in the store remains the embedding vector.

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
| Scope = structured push only | one spec vs. push + raw + decoders | Routing/storage/observers/seeding already exist; the milestone is a validated write endpoint. Raw by-value → deferred SPEC-013; framework decoding → killed. |
| JSON Schema IDL | Protobuf vs. Pydantic vs. JSON Schema | JSON-native end to end; rich constraints in one lib; Mongo-native `$jsonSchema`. |
| Framework writes; plugins share the write method | plugin `process_structured` hook vs. framework write + toolkit | A pushed record is already refined; the framework writes it. One canonical `write_record` (framework + plugins) prevents write-sprawl. |
| Declarative `embed_source` | plugin embed hook vs. declared source | Lets the framework write directly; covers the common case; complex embedding is future. |
| Route by `record_type` | `semantic_type` vs. `record_type` | The caller sends the refined output; `semantic_type` fan-out is a raw-path concern. |
| `metadata` 1:1 with payload | spread vs. sub-document | Contract = payload = `metadata`; envelope on the record; clean Mongo shape. |
| `uri` required (identity) | optional/hash-derived vs. required | Reuses SPEC-004/005 idempotency; enables updates; motivating case has a natural identity. |
| No `semantic_types` param on the tool | keep vs. drop | Not routing here; observer labels come from the declarer's `semantic_type`. |
| Keep `reliability_hint` | drop vs. keep | Thin passthrough to SPEC-007; enables confidence-tiering the Service Profile needs. |
| Single submittable declarer per record_type | multi vs. single | Unambiguous schema/write owner; caught at registration. |

## Backward compatibility

- `ingest_documents(uris=[...])` unchanged.
- `RecordTypeSpec` gains optional fields (`submittable=False`, `embed_source=None`); today's behavior preserved.
- No schema migration; no changes to the raw/extract path.

---

## Execution Plan

Provisional (stories/ACs to follow).

### Task 1: Validator + submittable declaration
- Add `jsonschema`; `validate_record`.
- `RecordTypeSpec.submittable` + `embed_source`; registration guard (no envelope fields in a submittable schema).
- Registry: `get_submittable_spec(record_type)` + single-declarer uniqueness.

### Task 2: Canonical write path (toolkit)
- `toolkit.write_record(...)` — embedding (from `embed_source`), content_hash, reliability ladder (SPEC-007), idempotency (SPEC-004/005), `save_payload`/`update_payload`.

### Task 3: `submit_structured` tool + pipeline entry
- `IngestionPipeline.ingest_structured(...)` (validate → context → write → emit event).
- `submit_structured` on `IngestionPlugin`; strict error surfacing.
- Confirm existing observer Phase 2 fires by `record_type`.

### Task 4: Discovery
- Surface submittable record types + their JSON Schema in `list_record_types`.

### Task 5: Reference submittable plugin (test/example)
- A minimal plugin declaring a submittable record type + JSON Schema, exercising `submit_structured` end-to-end (pass + reject), independent of the Service Profile work.

### Task 6: Documentation
- Plugin developer guide (submittable record types, `write_record` toolkit, embed_source, metadata 1:1, field-naming, the three-type vocabulary).
- System overview + ingestion diagrams; fix `record_type`/`semantic_type` conflation.
- Author proposed **ADR-011** (structured ingestion contracts; JSON Schema IDL; framework write + toolkit; metadata 1:1; three-type clarification).
