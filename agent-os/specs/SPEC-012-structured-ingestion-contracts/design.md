# SPEC-012: Structured Ingestion Contracts — Design

## Overview

This spec extends the ingestion boundary from **by-reference only** (`ingest_documents(uris)` — the pipeline fetches) to **by-value**: callers may submit the content itself. Two payload shapes share the door, distinguished by whether the content still needs *decoding* or is already a *record*:

1. **Inline raw content** — bytes + a declared `media_type`. The framework decodes/validates well-formedness, then hands the decoded content to a plugin that interprets it (chunk, embed, write). Same self-extract semantics as the URI path, minus the fetch.
2. **Structured record** — a finished record (JSON). The framework validates it against the target `record_type`'s **JSON Schema contract**, then hands the validated payload to a plugin that maps it to storage.

Both are gated at the pipeline boundary. Neither gate lives inside a plugin.

## The two gates

| Gate | Applies to | Mechanism | Owner |
|------|-----------|-----------|-------|
| **Format / well-formedness** ("bad-data bar") | inline raw content (and, later, fetched URIs) | decode bytes as the declared `media_type`; malformed → reject | framework (trivial decoders here; SPEC-013 generalizes) |
| **Record-schema conformance** | structured records | validate JSON payload against the record type's JSON Schema; invalid → reject | framework (this spec) |

## The decode-vs-interpret razor

The boundary between framework responsibility and plugin responsibility:

- **Decode / validate** — bytes+format → faithful structure; JSON record → schema-valid payload. Lossless, deterministic, no judgment. **→ framework.**
- **Interpret** — a structure → the records we store (chunking, which text to embed, fan-out to parent + segments, derived counts). A *choice* that varies per plugin. **→ plugin.**

## Interface Definition Language: JSON Schema

Record contracts are expressed in **JSON Schema**, validated with the `jsonschema` library.

- **JSON-native end to end.** Producers emit JSON, we validate JSON, we persist JSON in `documents.metadata` (so SPEC-010 `json_extract` search keeps working). No serialization/interchange conversion, no build step.
- **Rich constraints in one library.** `required`, types, `minimum/maximum`, `pattern`, `enum`, `minItems`, `oneOf` — natively, no second constraint layer.
- **MongoDB-portable enforcement.** JSON Schema is Mongo's native validator (`$jsonSchema`), so at scale the *same* contract can be pushed down to the collection as defense-in-depth. (Considered and rejected: Protobuf — typed/cross-language but not stored (we keep JSON for search), not enforceable by Mongo, and adds a toolchain + proto→JSON canonicalization. Pydantic — Python-bound.)
- **Single IDL, one validator behind the seam.** We do not build a multi-IDL registry. The `PayloadValidator` interface exists only so the IDL is not hardwired across the codebase; it ships exactly **one** implementation (`JsonSchemaValidator`).

## Components

| Component | Type | Change | Purpose |
|-----------|------|--------|---------|
| `submit_structured` MCP tool | Tool (new) | new | External door for structured-record submission. |
| `IngestionPlugin` | ToolProvider | modified | Hosts `submit_structured`; extends `ingest_documents` to accept inline content. |
| `IngestionPipeline` | Service | modified | New `ingest_structured(...)` entry; wires the two gates; by-value content path. |
| `PayloadValidator` | ABC (new) | new | The record-schema gate seam. One implementation. |
| `JsonSchemaValidator` | Validator (new) | new | Validates a JSON payload against the record type's JSON Schema; returns the validated payload. |
| Format/well-formedness check | Validator (new) | new | The "bad-data bar" for inline raw content (trivial decoders for now). |
| `RecordTypeSpec` | dataclass | modified | Opt-in `submittable`; when set, `schema` becomes the enforced JSON Schema. |
| `IngestProcessor` | ABC | modified | New `process_structured(submission)` hook; receives the validated payload. |
| `PluginRegistry` | Service | modified | Owner-uniqueness check for submittable record types; lookup by submittable record_type. |
| `StructuredSubmission` | dataclass (new) | new | Validated payload + envelope (record_type, uri, reliability_hint, tenant, semantic_types). |
| `MarkdownPlugin` | Processor | modified | Consumes framework-provided content instead of fetching. |
| `DoctypeDiscoveryPlugin` | ToolProvider | modified | Surfaces submittable record types + their JSON Schema via `list_record_types`. |

## Data Flow

### Structured-record path (the primary new capability)

```
caller → submit_structured(record_type, payload, uri, ...)
  → IngestionPlugin.call_tool
    → IngestionPipeline.ingest_structured
       1. owner = registry.get_submittable_owner(record_type)     # exactly one, or error
       2. spec  = owner.record_type_spec(record_type)             # must be submittable
       3. result = JsonSchemaValidator.validate(payload, spec.schema)
             jsonschema.validate(payload, spec.schema)            # types/required/ranges/enums/...
          # failure → REJECT with structured errors; nothing written
       4. ctx = build IngestionContext(uri, plugin, record_type)  # SPEC-004/005 idempotency (skip/update/replace)
       5. submission = StructuredSubmission(record_type, payload, uri, reliability_hint, tenant, context=ctx, ...)
       6. events = await owner.process_structured(submission)     # plugin embeds + writes (save_payload(metadata=payload))
       7. observers react (Phase 2, unchanged)
```

Rejection is **strict and atomic**: a validation failure returns structured errors and writes nothing. (Contrast the URI path, which is best-effort/no-op.) This strictness is the point — the platform's first schema enforcement.

### Inline-raw path (by-value extract)

```
caller → ingest_documents(documents=[{uri, content, media_type}], ...)
  → IngestionPipeline.ingest
     for each item:
       if content present:
         decode/validate well-formedness against media_type   # bad-data bar; REJECT if malformed
         provide decoded content to matching processors        # no fetch
       else:
         resolve + fetch URI as today
     → processor.process_bundle (interprets, embeds, writes)   # unchanged plugin contract
```

`uri` is the identity key for idempotency/updates (`lookup_existing_docs` keys on it), whether content is inline or fetched.

## Storage & Serialization — `metadata` is 1:1 with the payload

The record persists through the existing `save_payload` path. The key model, confirmed:

- **Envelope fields** — `uri`, `id`, `record_type`, `plugin`, `content_hash`, `plugin_version`, `semantic_type`, `media_type`, `parent_id` (+ vector, weights) — live on the **containing record**: columns on `documents` today, top-level fields on the Mongo document later.
- **`metadata`** is the **sub-document**, and it is **1:1 with the submitted payload** — the validated JSON goes in verbatim (SQLite: `json.dumps` into the `metadata` column; Mongo: a nested `metadata` sub-document).

So a submittable record type's **JSON Schema describes exactly the `metadata` sub-document** — the caller payload — and nothing else. Envelope fields are supplied out-of-band (`uri` on the call, `record_type` via routing, `id`/`plugin`/`content_hash` system-generated) and are never in the contract.

At Mongo scale this is directly enforceable: `$jsonSchema` can validate the `metadata` sub-document with the same contract. No storage-schema change is required for this spec; the only binary in the store remains the embedding vector (`vec_documents.embedding`), which is orthogonal — the plugin still chooses which validated fields to embed.

## Field Naming & Namespacing

Two field-name namespaces; the contract owns only one.

- **Envelope** (framework-owned): the record-level fields above. Not described by the contract.
- **Payload** (contract-owned): the JSON Schema's properties = the `metadata` sub-document keys, 1:1.

**Rules:**

1. **`snake_case` by convention** for payload keys (matches envelope/column style and `json_extract` predicates).
2. **1:1, no aliasing** — a schema property name *is* the stored `metadata` key.
3. **Never flatten the payload — keep it nested under `metadata`.** In Mongo, mirror the shape (top-level envelope + nested `metadata`). `json_extract(metadata,'$.k')` → `{"metadata.k": ...}` is a mechanical remap. A payload field named `uri` is fine (`metadata.uri` ≠ envelope `uri`) and stays clear of Mongo's reserved `_id`. Flattening is the only thing that would create collisions — so we don't.

**Consequence to accept:** we store and query **by name**, so payload field **names are durable contract**. Adding fields is safe; **renaming a payload field is a storage-breaking change** requiring migration.

**MongoDB migration** (forward note): the nested-`metadata` shape is deliberately Mongo-portable. Envelope columns become top-level document fields (snake_case ports as-is); the one special case is Mongo's reserved **`_id`** — at migration we decide `id`→`_id` or keep a separate numeric `id`. An envelope/migration decision, independent of the IDL.

## API Contracts

### `submit_structured` (new MCP tool)

```jsonc
{
  "name": "submit_structured",
  "description": "Submit a pre-structured record for validated ingestion against a record type's JSON Schema.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "record_type":     { "type": "string", "description": "Target submittable record type (the routing key)." },
      "payload":         { "type": "object", "description": "The record as JSON; validated against the record type's JSON Schema. Becomes the metadata sub-document 1:1." },
      "uri":             { "type": "string", "description": "Identity key for idempotency / updates (required)." },
      "semantic_types":  { "type": "array", "items": { "type": "string" }, "description": "Optional; forwarded to observers (not routing)." },
      "reliability_hint":{ "type": "number", "description": "Optional reliability seed (0.0–1.0)." },
      "tenant_id":       { "type": "string", "description": "Tenant to ingest into (default: 'default')." }
    },
    "required": ["record_type", "payload", "uri"]
  }
}
```

**Result:** on success, a summary (record_type, doc id(s)). On validation failure, structured errors listing offending fields/paths (from `jsonschema`). Nothing written on failure. *(Single record per call in v1; batching is a possible additive extension — decision #2.)*

### `ingest_documents` (extended, backward-compatible)

The flat `uris: [string]` form keeps working. A richer item form is added so callers may supply content by value:

```jsonc
{
  "documents": [
    { "uri": "file:///docs/a.md" },                                              // by reference (fetched) — unchanged
    { "uri": "mem://note/42", "content": "# Title\n...", "media_type": "text/markdown" }  // by value (decoded)
  ]
}
```

`media_type` is **required** when `content` is present (no extension to sniff). `uri` is the identity key. (Unified `ingest_documents` per decision #1 — by-ref and by-value-raw are the same extract method.)

### `RecordTypeSpec` (extended)

```python
@dataclass
class RecordTypeSpec:
    name: str
    description: str
    schema: dict = field(default_factory=dict)   # advisory when not submittable; ENFORCED JSON Schema when submittable
    plugin: str = ""
    decay_half_life_days: float | None = None
    default_reliability: float | None = None
    submittable: bool = False                     # NEW — opt-in structured ingestion
```

When `submittable` is `True`, `schema` is a JSON Schema enforced against the submitted payload; it describes the `metadata` sub-document (payload) only and must not declare envelope fields (`id`, `uri`, `plugin`, `content_hash`, `vector`, `tenant`) — a registration guard rejects those. When `False` (default), `schema` is advisory and unenforced, exactly as today.

### `IngestProcessor` (extended)

```python
async def process_structured(self, submission: "StructuredSubmission") -> list["IngestionEvent"]:
    """Receive a validated payload and write it. The pipeline has already validated
    `submission.payload` against the record type's JSON Schema and built an IngestionContext.
    The payload IS the metadata sub-document (1:1). The plugin chooses embedding text,
    performs any parent/segment fan-out, and calls save_payload(metadata=submission.payload, ...).
    Default: raise NotImplementedError (a processor opts in by overriding)."""
```

### `StructuredSubmission` (new)

```python
@dataclass
class StructuredSubmission:
    record_type: str
    payload: dict                 # validated; stored 1:1 as the metadata sub-document
    uri: str
    reliability_hint: float | None = None
    tenant_id: str = "default"
    semantic_types: list[str] = field(default_factory=list)
    context: "IngestionContext | None" = None   # SPEC-004/005 idempotency
    storage: "StorageAdapter | None" = None      # tenant-resolved adapter
```

### Validator seam (new)

```python
@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)

class PayloadValidator(ABC):
    @abstractmethod
    def validate(self, payload: dict, schema: dict) -> ValidationResult: ...

class JsonSchemaValidator(PayloadValidator):
    """jsonschema.validate(payload, schema); collects structured errors."""
```

One implementation ships. The seam keeps the IDL from being hardwired without inviting a multi-IDL pile-up.

## Registration & routing

- A record type is **submittable** iff `RecordTypeSpec.submittable` is `True`.
- `PluginRegistry.register` enforces **one submittable owner per record type name** (raises `ValueError`; mirrors the tool-collision check at `server.py:134`).
- Non-submittable record types are unaffected and may still be produced by multiple plugins.
- `submit_structured` routes `record_type → the single submittable owner → process_structured`.

## Data model changes

**None.** Structured records use the existing `save_payload` path (`documents.metadata` JSON + vector + weight row).

## Dependencies

`pyproject.toml` gains `jsonschema` (the codebase currently declares zero validation dependencies). No build step, no codegen.

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| **JSON Schema as the IDL** | Protobuf vs. Pydantic vs. JSON Schema | JSON-native end to end; rich constraints in one lib; Mongo-native `$jsonSchema` enforcement at scale. Proto isn't stored (we keep JSON for search), isn't Mongo-enforceable, and adds a toolchain; Pydantic is Python-bound. |
| **`metadata` is 1:1 with the payload** | payload spread across envelope vs. a single sub-document | Contract = payload = `metadata`; envelope fields live on the record. Clean SQLite columns / Mongo top-level + nested `metadata`. |
| **Enforce `RecordTypeSpec.schema` when submittable** | separate input-schema artifact vs. the record's schema | Input ≡ output at the `metadata` level; reuse the existing field, opt-in. |
| **Payload renames are storage-breaking** | — | We store/query by name; adds are safe, renames need migration. |
| Separate `submit_structured` tool | mode flag vs. new tool | Different routing/behavior/failure semantics; the name is the method clarity. |
| Exclude envelope fields from the contract | full-record schema vs. payload-only | Envelope is system-managed; a registration guard enforces it. |
| Strict, atomic rejection | best-effort vs. strict | This is the enforcement milestone. |
| Opt-in `submittable` | global vs. opt-in | Existing advisory schemas carry derived/owner fields; global enforcement would reject valid internal writes. |
| Single submittable owner per record type | multi-owner vs. single | Structured push needs one unambiguous handoff; caught at registration. |
| Plugin does write + embed | framework writes vs. plugin `process_structured` | Embedding is a projection choice — the decode-vs-interpret razor. |
| `uri` required (identity) | optional/hash-derived vs. required | Reuses SPEC-004/005 idempotency; enables update semantics; motivating case has a natural identity. |

## Backward compatibility

- `ingest_documents(uris=[...])` is unchanged.
- `RecordTypeSpec` gains `submittable` (default `False`); today's behavior preserved.
- `IngestProcessor.process_structured` defaults to `NotImplementedError`; existing processors unaffected until they opt in.
- No schema migration.

---

## Execution Plan

Provisional task breakdown (stories/ACs to be finalized in the follow-up pass).

### Task 1: Validator seam
- Add `jsonschema`; `PayloadValidator` ABC, `ValidationResult`, `JsonSchemaValidator`.
- Structured error surfacing from `jsonschema`.

### Task 2: RecordTypeSpec enforcement (opt-in)
- Add `submittable`; enforce `schema` as JSON Schema when set.
- Registry: submittable-owner uniqueness; `get_submittable_owner(record_type)`.
- Registration guard: reject a submittable `schema` that declares envelope field names.
- Discovery: surface submittable record types + their JSON Schema in `list_record_types`.

### Task 3: `process_structured` + `StructuredSubmission`
- Add the processor hook (default `NotImplementedError`).
- `StructuredSubmission` dataclass; IngestionContext (SPEC-004/005) built for structured submissions; tenant-adapter resolution reuse.

### Task 4: `submit_structured` tool + pipeline entry
- `IngestionPipeline.ingest_structured(...)` (validate → context → submission → dispatch → observers).
- `submit_structured` tool on `IngestionPlugin`; strict error surfacing.

### Task 5: Inline-by-value content on the extract path
- Extend `ingest_documents` item shape (`{uri, content?, media_type?}`), backward-compatible.
- Pipeline: use provided content when present; format well-formedness gate; fetch fallback.
- `ResourceResolver` / bundle plumbing to carry inline content + declared media type.

### Task 6: MarkdownPlugin migration
- Receive framework-provided content instead of fetching (`urllib` removed from the hot path).
- Keep chunk/embed/write; verify parity with SPEC-011 parent/segment behavior.

### Task 7: Documentation
- Update plugin developer guide (submittable record types, JSON Schema contracts, `process_structured`, inline content, field-naming rules, metadata 1:1).
- Update system overview + ingestion diagrams.
- Author proposed **ADR-011** (structured ingestion contracts; JSON Schema IDL; input≡output-at-metadata; two-gate model; metadata-1:1 + field-naming + Mongo portability).

### Task 8: Reference structured plugin (test/example)
- A minimal submittable plugin with a JSON Schema contract exercising `submit_structured` end-to-end (validation pass + reject), independent of the Service Profile work.
