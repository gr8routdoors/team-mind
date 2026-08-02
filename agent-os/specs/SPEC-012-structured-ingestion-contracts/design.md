# SPEC-012: Structured Ingestion Contracts — Design

## Overview

This spec extends the ingestion boundary from **by-reference only** (`ingest_documents(uris)` — the pipeline fetches) to **by-value**: callers may submit the content itself. Two payload shapes share the door, distinguished by whether the content still needs *decoding* or is already a *record*:

1. **Inline raw content** — bytes + a declared `media_type`. The framework decodes/validates well-formedness, then hands the decoded content to a plugin that interprets it (chunk, embed, write). Same self-extract semantics as the URI path, minus the fetch.
2. **Structured record** — a finished output record. The framework validates it against the target `record_type`'s **protobuf contract**, then hands the validated, normalized payload to a plugin that maps it to storage.

Both are gated at the pipeline boundary. Neither gate lives inside a plugin.

## The two gates

| Gate | Applies to | Mechanism | Owner |
|------|-----------|-----------|-------|
| **Format / well-formedness** ("bad-data bar") | inline raw content (and, later, fetched URIs) | decode bytes as the declared `media_type`; malformed → reject | framework (trivial decoders here; SPEC-013 generalizes) |
| **Record-schema conformance** | structured records | parse JSON→proto message + `protovalidate` constraints; invalid → reject | framework (this spec) |

## The decode-vs-interpret razor

The boundary between framework responsibility and plugin responsibility:

- **Decode / validate** — bytes+format → faithful structure; JSON record → validated proto message. Lossless, deterministic, no judgment. **→ framework.**
- **Interpret** — a structure → the records we store (chunking, which text to embed, fan-out to parent + segments, derived counts). A *choice* that varies per plugin. **→ plugin.**

## Interface Definition Language: Protobuf

The framework's record contracts are expressed in **protobuf** (proto3), with **protovalidate** (buf's CEL-based constraint layer) for field-level rules. Rationale and trade-offs are in the Decisions table; the essential properties:

- **Typed, cross-language, service-shaped** — contracts are portable artifacts, not Python- or JSON-only. Aligns with the Phase-4 Service Profile / service-catalog direction.
- **Single IDL, one validator behind the seam.** We do **not** build a multi-IDL registry. The `PayloadValidator` interface exists so the IDL is not hardwired across the codebase, but it ships exactly **one** implementation (proto + protovalidate). "Single IDL now, not painted into a corner."
- **Proto is a validation/interchange layer, not the storage format.** See *Storage & Serialization*.
- **The `.proto` carries the whole contract** — message shape (types) *and* `protovalidate` CEL constraints (required, ranges, lengths, patterns) as field options. Bare parsing stays fast; CEL checks fire only on annotated fields.

## Components

| Component | Type | Change | Purpose |
|-----------|------|--------|---------|
| `submit_structured` MCP tool | Tool (new) | new | External door for structured-record submission. |
| `IngestionPlugin` | ToolProvider | modified | Hosts `submit_structured`; extends `ingest_documents` to accept inline content. |
| `IngestionPipeline` | Service | modified | New `ingest_structured(...)` entry; wires the two gates; by-value content path. |
| `PayloadValidator` | ABC (new) | new | The record-schema gate seam. One implementation. |
| `ProtoRecordValidator` | Validator (new) | new | Parses JSON→proto message, runs `protovalidate`, returns the normalized dict. |
| Format/well-formedness check | Validator (new) | new | The "bad-data bar" for inline raw content (trivial decoders for now). |
| `RecordTypeSpec` | dataclass | modified | Opt-in `submittable`; references the proto message that defines the input contract. |
| `IngestProcessor` | ABC | modified | New `process_structured(submission)` hook; receives validated, normalized payloads. |
| `PluginRegistry` | Service | modified | Owner-uniqueness check for submittable record types; lookup by submittable record_type. |
| `StructuredSubmission` | dataclass (new) | new | Normalized payload (proto-JSON dict) + envelope (record_type, uri, reliability_hint, tenant, semantic_types). |
| `MarkdownPlugin` | Processor | modified | Consumes framework-provided content instead of fetching. |
| `DoctypeDiscoveryPlugin` | ToolProvider | modified | Surfaces submittable record types + their proto contract via `list_record_types`. |

## Data Flow

### Structured-record path (the primary new capability)

```
caller → submit_structured(record_type, payload_json, uri?, ...)
  → IngestionPlugin.call_tool
    → IngestionPipeline.ingest_structured
       1. owner = registry.get_submittable_owner(record_type)     # exactly one, or error
       2. spec  = owner.record_type_spec(record_type)             # must be submittable
       3. validator = PayloadValidator (ProtoRecordValidator)
       4. result = validator.validate(payload_json, spec)
             a. json_format.ParseDict(payload_json, spec.message(), ignore_unknown_fields=False)  # type gate
             b. protovalidate.validate(msg)                                                       # constraint gate
             c. normalized = json_format.MessageToDict(msg, preserving_proto_field_name=True)     # canonical dict
          # any failure → REJECT with structured errors; nothing written
       5. submission = StructuredSubmission(record_type, normalized, uri, reliability_hint, tenant, ...)
       6. events = await owner.process_structured(submission)      # plugin embeds + writes (save_payload(metadata=normalized))
       7. observers react (Phase 2, unchanged)
```

Rejection is **strict and atomic**: a validation failure returns structured errors to the caller and writes nothing. (Contrast the URI path, which is best-effort/no-op.) This strictness is the point — the platform's first schema enforcement.

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

`uri` remains the identity key for idempotency/updates (`lookup_existing_docs` keys on it), whether content is inline or fetched.

## Storage & Serialization

**Proto validates at the door; JSON persists to disk.** The record lands in the existing `documents.metadata` column as JSON text via the current `save_payload` path (`json.dumps` internally). We store the **normalized proto-JSON dict** (`MessageToDict` output), not the raw incoming JSON — so what persists is exactly the validated contract shape (defaults applied, unknown fields stripped, types canonicalized).

Why JSON and not binary proto: metadata search (SPEC-010) runs `json_extract(d.metadata, '$.key')` against JSON text (`storage.py:602,698`). Storing the binary message would forfeit that capability. The only binary in the store is the **embedding vector** (`vec_documents.embedding`, packed `float[768]`), which is orthogonal — the plugin still chooses which validated fields to embed. **No storage-schema change is required for the IDL decision.**

Proto's JSON serialization is *not* a performance optimization (it is slower than plain `json.dumps`); its value here is a **normalized, validated, canonical** record. The conversion cost is negligible against embedding + SQLite IO.

**Canonicalization pins** (proto3 JSON mapping) — the stored shape must be predictable because we query it by path:

- `preserving_proto_field_name=True` — keep `snake_case` keys (default emits `camelCase`, which would break every `$.snake_key` predicate).
- **int64/uint64 → JSON string** in canonical mapping — metadata-search predicates on 64-bit fields compare against strings. Known and documented, not a bug.
- **enums → names** by default — deliberate and stable.

## Field Naming & Namespacing

There are **two** field-name namespaces; proto owns only one.

- **Envelope fields** (framework-owned): `uri`, `record_type`, `plugin`, `content_hash`, `plugin_version`, `semantic_type`, `media_type`, `parent_id`, `id` — plus vector and weights. Columns on `documents`. Proto does **not** describe these.
- **Payload fields** (contract-owned): the record's semantic fields, sourced from the proto message. They live **inside** the `metadata` namespace.

**Three rules:**

1. **Pin proto JSON to `snake_case`** (`preserving_proto_field_name=True`) — payload keys match envelope style and existing predicates.
2. **1:1, no aliasing** — the proto field name *is* the stored key. No proto-name→storage-name translation table; proto field *numbers* provide the underlying versioning safety net.
3. **Never flatten the payload — keep it nested under `metadata`.** In Mongo, mirror the shape: a top-level document with envelope fields plus a nested `metadata` sub-document. `json_extract(metadata,'$.k')` → `{"metadata.k": ...}` is a near-mechanical remap.

Rule 3 **dissolves collisions**: a payload field named `uri` is fine (`metadata.uri` ≠ envelope `uri`), and payload stays clear of Mongo's reserved `_id`. Flattening is the only thing that would create envelope/`_id` collisions — so we don't.

**Consequence to accept:** because we store and query **by name** (a JSON projection), payload field **names are part of our durable contract**, not just proto field numbers. In pure proto a rename is wire-compatible if the number is stable; for us a rename changes the stored `metadata` key and old documents keep the old key. **Adding fields is safe; renaming a payload field is a storage-breaking change requiring migration.**

**MongoDB migration** (forward note): the nested-`metadata` shape is deliberately Mongo-portable. Envelope columns become top-level document fields (snake_case ports as-is); the one special case is Mongo's reserved **`_id`** — at migration we decide `id`→`_id` (Mongo owns identity) or keep a separate numeric `id`. That's an envelope/migration decision, independent of the proto IDL.

## API Contracts

### `submit_structured` (new MCP tool)

```jsonc
{
  "name": "submit_structured",
  "description": "Submit a pre-structured record for validated ingestion against a record type's protobuf contract.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "record_type":     { "type": "string", "description": "Target submittable record type (the routing key)." },
      "payload":         { "type": "object", "description": "The record as JSON; validated against the record type's proto contract." },
      "uri":             { "type": "string", "description": "Optional identity key for idempotency / updates." },
      "semantic_types":  { "type": "array", "items": { "type": "string" }, "description": "Optional; forwarded to observers (not routing)." },
      "reliability_hint":{ "type": "number", "description": "Optional reliability seed (0.0–1.0)." },
      "tenant_id":       { "type": "string", "description": "Tenant to ingest into (default: 'default')." }
    },
    "required": ["record_type", "payload"]
  }
}
```

**Result:** on success, a summary (record_type, count, doc ids where available). On validation failure, structured errors listing the offending fields/paths (from `protovalidate`/`ParseDict`) — the caller corrects and resubmits. Nothing is written on failure. *(Single record per call in v1; batching is a possible additive extension — see open design forks.)*

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

`media_type` is **required** when `content` is present (no file extension to sniff). `uri` remains the identity key. *(Whether inline-raw stays on `ingest_documents` or becomes its own tool is an open fork.)*

### `RecordTypeSpec` (extended)

```python
@dataclass
class RecordTypeSpec:
    name: str
    description: str
    schema: dict = field(default_factory=dict)          # advisory (legacy / non-submittable types); unchanged
    plugin: str = ""
    decay_half_life_days: float | None = None
    default_reliability: float | None = None
    submittable: bool = False                            # NEW — opt-in structured ingestion
    message: "type | None" = None                        # NEW — the proto message type defining the input contract
```

When `submittable` is `True`, `message` is the proto message whose `.proto` (with `protovalidate` options) is the enforced caller contract. The message describes **payload** fields only; it must not declare envelope/system-managed fields (`id`, `vector`, `plugin`, `content_hash`, `uri`, `tenant`). When `submittable` is `False` (default), behavior is exactly as today — advisory `schema`, unenforced.

### `IngestProcessor` (extended)

```python
async def process_structured(self, submission: "StructuredSubmission") -> list["IngestionEvent"]:
    """Receive a validated, normalized structured payload and write it.
    The pipeline has already parsed+validated the payload against the record type's proto contract.
    `submission.payload` is the canonical proto-JSON dict (snake_case keys).
    The plugin chooses embedding text, performs any parent/segment fan-out, and calls save_payload.
    Default: raise NotImplementedError (a processor opts in by overriding)."""
```

### `StructuredSubmission` (new)

```python
@dataclass
class StructuredSubmission:
    record_type: str
    payload: dict                 # normalized proto-JSON (snake_case), ready for save_payload(metadata=...)
    uri: str | None = None
    reliability_hint: float | None = None
    tenant_id: str = "default"
    semantic_types: list[str] = field(default_factory=list)
    storage: "StorageAdapter | None" = None   # tenant-resolved adapter, as with IngestionBundle
```

### Validator seam (new)

```python
@dataclass
class ValidationResult:
    ok: bool
    normalized: dict | None = None          # canonical proto-JSON dict when ok
    errors: list[str] = field(default_factory=list)

class PayloadValidator(ABC):
    @abstractmethod
    def validate(self, payload: dict, spec: "RecordTypeSpec") -> ValidationResult: ...

class ProtoRecordValidator(PayloadValidator):
    """ParseDict → protovalidate → MessageToDict(preserving_proto_field_name=True)."""
```

One implementation ships. The seam keeps the IDL from being hardwired without inviting a multi-IDL pile-up.

## Registration & routing

- A record type is **submittable** iff `RecordTypeSpec.submittable` is `True` (and carries a `message`).
- `PluginRegistry.register` enforces **one submittable owner per record type name**; a second raises `ValueError` (mirrors the tool-collision check at `server.py:134`).
- Non-submittable record types are unaffected and may still be produced by multiple plugins (output side unchanged).
- `submit_structured` routes `record_type → the single submittable owner → process_structured`.

## Data model changes

**None.** Structured records are stored through the existing `save_payload` path (`documents.metadata` JSON blob + vector + weight row). This spec adds a validated *entry* to that capability, not new tables or columns.

## Dependencies

`pyproject.toml` gains `protobuf` and `protovalidate` (the codebase currently declares **zero** validation dependencies). A proto build step is introduced — `.proto` files compiled to Python via `grpcio-tools`/`protoc` (or `buf`) — plus the generated modules' placement in the package. This is the ergonomic cost of the proto IDL, accepted deliberately.

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| **Protobuf as the single IDL** | JSON Schema vs. Pydantic vs. Protobuf | Typed, cross-language, service-shaped from day one; aligns with the Service Profile direction. Pydantic is Python-bound; JSON Schema is JSON-only. |
| **protovalidate for constraints** | proto-types only vs. + CEL constraints | proto3 alone enforces types/shape, not required/ranges/patterns. protovalidate closes the gap; CEL fires only on annotated fields. |
| **Proto validates, JSON persists** | store binary proto vs. store JSON | Binary would forfeit `json_extract` metadata search (SPEC-010). JSON keeps search; proto's win here is normalization, not speed. |
| **Store the normalized (MessageToDict) form** | store raw incoming JSON vs. normalized | Persists exactly the validated contract shape; defaults applied, unknowns stripped. |
| **snake_case pin + 1:1 names + nested `metadata`** | camelCase / flattened / aliased | Predictable query shape; no envelope/`_id` collisions; SQLite↔Mongo is a query-syntax remap, not a reshape. |
| **Payload renames are storage-breaking** | rely on proto number-compat vs. name-durable | We store/query by name, so names are durable contract; adds are safe, renames need migration. |
| Separate `submit_structured` tool | mode flag vs. new tool | Different routing key, plugin behavior, failure semantics; the name is the method clarity. |
| Validate against the record type's contract | distinct input-schema artifact vs. the record's proto | The agent hands us the finished record; input≡output at the `metadata` level. |
| Strict, atomic rejection | best-effort vs. strict | This is the enforcement milestone; partial writes of invalid records defeat it. |
| Opt-in `submittable` | global enforcement vs. opt-in | Protects existing advisory schemas (which carry derived/owner fields) from breaking. |
| Single submittable owner per record type | multi-owner vs. single | Structured push needs one unambiguous handoff; caught at registration. |
| Plugin does write + embed | framework writes vs. plugin `process_structured` | Embedding is a projection choice — same decode-vs-interpret razor. |

## Backward compatibility

- `ingest_documents(uris=[...])` is unchanged.
- `RecordTypeSpec` gains optional fields defaulting to today's behavior (`submittable=False`, `message=None`).
- `IngestProcessor.process_structured` defaults to `NotImplementedError`; existing processors are unaffected until they opt in.
- No schema migration.

---

## Execution Plan

Provisional task breakdown (stories/ACs to be finalized in the follow-up pass).

### Task 1: Proto toolchain + validator seam
- Add `protobuf` + `protovalidate`; introduce the `.proto` build step (generated modules in-package).
- `PayloadValidator` ABC, `ValidationResult`, `ProtoRecordValidator` (ParseDict → protovalidate → MessageToDict).
- Canonicalization pins (`preserving_proto_field_name`); structured error surfacing.

### Task 2: RecordTypeSpec enforcement (opt-in)
- Add `submittable`, `message`.
- Registry: submittable-owner uniqueness; `get_submittable_owner(record_type)`.
- Registration guard: reject a submittable `message` that declares envelope/system field names.
- Discovery: surface submittable record types + their proto contract (`.proto`/descriptor) in `list_record_types`.

### Task 3: `process_structured` + `StructuredSubmission`
- Add the processor hook (default `NotImplementedError`).
- `StructuredSubmission` dataclass; tenant-adapter resolution reuse.

### Task 4: `submit_structured` tool + pipeline entry
- `IngestionPipeline.ingest_structured(...)` (validate → normalize → build submission → dispatch → observers).
- `submit_structured` tool on `IngestionPlugin`; strict error surfacing.

### Task 5: Inline-by-value content on the extract path
- Extend `ingest_documents` item shape (`{uri, content?, media_type?}`), backward-compatible.
- Pipeline: use provided content when present; format well-formedness gate; fetch fallback.
- `ResourceResolver` / bundle plumbing to carry inline content + declared media type.

### Task 6: MarkdownPlugin migration
- Receive framework-provided content instead of fetching (`urllib` removed from the hot path).
- Keep chunk/embed/write; verify parity with SPEC-011 parent/segment behavior.

### Task 7: Documentation
- Update plugin developer guide (submittable record types, proto contracts, `process_structured`, inline content, field-naming rules).
- Update system overview + ingestion diagrams.
- Author proposed **ADR-011** (structured ingestion contracts; protobuf IDL + protovalidate; input≡output-at-metadata; two-gate model; field-naming/namespacing + Mongo portability).

### Task 8: Reference structured plugin (test/example)
- A minimal submittable plugin with a `.proto` contract exercising `submit_structured` end-to-end (validation pass + reject), independent of the Service Profile work.
