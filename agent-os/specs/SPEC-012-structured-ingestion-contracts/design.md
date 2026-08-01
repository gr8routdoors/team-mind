# SPEC-012: Structured Ingestion Contracts — Design

## Overview

This spec extends the ingestion boundary from **by-reference only** (`ingest_documents(uris)` — the pipeline fetches) to **by-value**: callers may submit the content itself. Two payload shapes share the door, distinguished by whether the content still needs *decoding* or is already a *record*:

1. **Inline raw content** — bytes + a declared `media_type`. The framework decodes/validates well-formedness, then hands the decoded content to a plugin that interprets it (chunk, embed, write). Same self-extract semantics as the URI path, minus the fetch.
2. **Structured record** — a finished output record. The framework validates it against the target `record_type`'s schema, then hands the validated payload to a plugin that maps it to storage.

Both are gated at the pipeline boundary by a **pluggable validator seam**. Neither gate lives inside a plugin.

## The decode-vs-interpret razor

The boundary between framework responsibility and plugin responsibility is a single principle:

- **Decode** — bytes + declared format → a *faithful* structure (lossless, deterministic, no judgment). `json.loads` for a JSON record; text/identity for markdown; later, markdown→AST, XML→tree, etc. Also the natural home of the format well-formedness gate. **→ framework.**
- **Interpret** — a structure → the records we store (chunking strategy, which text to embed, fan-out to parent + segments, derived counts). A *choice* that varies per plugin and record type. **→ plugin.**

This spec establishes the decode seam and the two trivial decoders it needs (JSON, text). SPEC-013 grows the decoder catalog.

## Components

| Component | Type | Change | Purpose |
|-----------|------|--------|---------|
| `submit_structured` MCP tool | Tool (new) | new | External door for structured-record submission. |
| `IngestionPlugin` | ToolProvider | modified | Hosts `submit_structured`; extends `ingest_documents` to accept inline content. |
| `IngestionPipeline` | Service | modified | New `ingest_structured(...)` entry; wires the validator seam; by-value content path. |
| `ValidatorRegistry` | Service (new) | new | Framework-owned registry of validators keyed by format/dialect. |
| `RecordSchemaValidator` (JSON Schema) | Validator (new) | new | Validates a structured payload against `RecordTypeSpec.schema`. |
| Format/well-formedness check | Validator (new) | new | The "bad-data bar" for inline raw content (trivial decoders for now). |
| `RecordTypeSpec` | dataclass | modified | Opt-in enforcement: `submittable` flag; schema becomes the caller contract when set. |
| `IngestProcessor` | ABC | modified | New `process_structured(submission)` hook; receives validated payloads. |
| `PluginRegistry` | Service | modified | Owner-uniqueness check for submittable record types; lookup by submittable record_type. |
| `StructuredSubmission` | dataclass (new) | new | Validated, normalized payload + envelope (record_type, uri, reliability_hint, tenant, semantic_types). |
| `MarkdownPlugin` | Processor | modified | Consumes framework-provided content instead of fetching. |
| `DoctypeDiscoveryPlugin` | ToolProvider | modified | Surfaces submittable record types + input schemas via `list_record_types`. |

## Data Flow

### Structured-record path (the primary new capability)

```
caller → submit_structured(record_type, payload, uri?, ...)
  → IngestionPlugin.call_tool
    → IngestionPipeline.ingest_structured
       1. registry.get_submittable_owner(record_type)      # exactly one, or error
       2. spec = owner.record_type_spec(record_type)       # must be submittable
       3. validator = ValidatorRegistry.for(spec)          # by schema dialect
       4. result = validator.validate(payload, spec.schema) # REJECT on failure — never reaches plugin
       5. submission = StructuredSubmission(record_type, result.normalized, uri, reliability_hint, tenant, ...)
       6. events = await owner.process_structured(submission) # plugin embeds + writes (save_payload)
       7. observers react (Phase 2, unchanged)
```

Rejection is **strict and atomic**: a schema failure returns structured errors to the caller and writes nothing. (Contrast the URI path, which is best-effort/no-op.) This strictness is the point — it is the platform's first schema enforcement.

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

## API Contracts

### `submit_structured` (new MCP tool)

```jsonc
{
  "name": "submit_structured",
  "description": "Submit a pre-structured record for validated ingestion against a record type's schema.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "record_type":     { "type": "string", "description": "Target submittable record type (the routing key)." },
      "payload":         { "type": ["object", "array"], "description": "The pre-structured record(s), validated against the record type's schema." },
      "uri":             { "type": "string", "description": "Optional identity key for idempotency / updates." },
      "semantic_types":  { "type": "array", "items": { "type": "string" }, "description": "Optional; forwarded to observers." },
      "reliability_hint":{ "type": "number", "description": "Optional reliability seed (0.0–1.0)." },
      "tenant_id":       { "type": "string", "description": "Tenant to ingest into (default: 'default')." }
    },
    "required": ["record_type", "payload"]
  }
}
```

**Result:** on success, a summary of what was queued/written (record_type, count, doc ids where available). On validation failure, a structured error listing the offending fields/paths — the caller can correct and resubmit. Nothing is written on failure.

### `ingest_documents` (extended, backward-compatible)

The flat `uris: [string]` form keeps working. A richer item form is added so callers may supply content by value:

```jsonc
{
  "documents": [
    { "uri": "file:///docs/a.md" },                                  // by reference (fetched) — unchanged behavior
    { "uri": "mem://note/42", "content": "# Title\n...", "media_type": "text/markdown" }  // by value (decoded)
  ]
}
```

`media_type` is **required** when `content` is present (no file extension to sniff). `uri` remains required as the identity key.

### `RecordTypeSpec` (extended)

```python
@dataclass
class RecordTypeSpec:
    name: str
    description: str
    schema: dict = field(default_factory=dict)   # advisory OUTPUT description; also the caller contract when submittable
    plugin: str = ""
    decay_half_life_days: float | None = None
    default_reliability: float | None = None
    submittable: bool = False                     # NEW — opt-in structured ingestion
    schema_dialect: str = "json_schema"           # NEW — selects the validator (SPEC-013 grows this set)
```

When `submittable` is `True`, `schema` is treated as the **enforced caller contract** at the boundary and must exclude system-managed fields (`id`, `vector`, `plugin`, `content_hash`, `tenant`, weight). When `False` (default), behavior is exactly as today — advisory, unenforced.

### `IngestProcessor` (extended)

```python
async def process_structured(self, submission: "StructuredSubmission") -> list["IngestionEvent"]:
    """Receive a validated, normalized structured payload and write it.
    The pipeline has already validated `submission.payload` against the record type's schema.
    The plugin chooses embedding text, performs any parent/segment fan-out, and calls save_payload.
    Default: raise NotImplementedError (a processor opts in by overriding)."""
```

### `StructuredSubmission` (new)

```python
@dataclass
class StructuredSubmission:
    record_type: str
    payload: dict | list          # validated + normalized
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
    normalized: dict | list | None = None   # coerced/canonical payload when ok
    errors: list[str] = field(default_factory=list)

class PayloadValidator(ABC):
    @property
    @abstractmethod
    def dialect(self) -> str: ...            # e.g. "json_schema"
    @abstractmethod
    def validate(self, payload, schema) -> ValidationResult: ...

class ValidatorRegistry:
    def register(self, validator: PayloadValidator) -> None: ...
    def for_dialect(self, dialect: str) -> PayloadValidator: ...   # raises on unknown dialect
```

Ships one implementation: `JsonSchemaValidator(dialect="json_schema")`. Additional dialects (e.g. Pydantic) and the format-decoder side are grown in SPEC-013. *(Open question for the AC pass: ship a Pydantic validator here or defer to 013.)*

## Registration & routing

- A record type is **submittable** iff its `RecordTypeSpec.submittable` is `True`.
- `PluginRegistry.register` enforces **one submittable owner per record type name**; a second raises `ValueError` (mirrors the tool-collision check at `server.py:134`).
- Non-submittable record types are unaffected and may still be produced by multiple plugins (the output side is unchanged).
- `submit_structured` routes `record_type → the single submittable owner → process_structured`.

## Data model changes

**None.** Structured records are stored through the existing `save_payload` path (`documents.metadata` JSON blob + vector + weight row). This spec adds a validated *entry* to that capability, not new tables or columns.

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Reuse `save_payload`, no schema changes | New structured store vs. existing | Structured records already live in `documents.metadata`; only the boundary is missing. |
| Strict, atomic rejection on the structured path | Best-effort vs. strict | This is the *enforcement* milestone; partial writes of invalid records defeat the purpose. |
| `media_type` required for inline content | Sniff vs. require | No file extension to infer from; requiring it also feeds the format gate. |
| Normalized payload returned from validators | Boolean vs. normalized | Plugins receive canonical data instead of re-parsing; enables coercion. |
| Opt-in `submittable` | Global enforcement vs. opt-in | Protects existing advisory schemas (which carry derived/owner fields) from breaking. |
| Single submittable owner per record type | Multi-owner vs. single | Structured push needs one unambiguous handoff; caught at registration, not submission. |

## Backward compatibility

- `ingest_documents(uris=[...])` is unchanged.
- `RecordTypeSpec` gains optional fields defaulting to today's behavior (`submittable=False`).
- `IngestProcessor.process_structured` defaults to `NotImplementedError`; existing processors are unaffected until they opt in.
- No schema migration.

---

## Execution Plan

Provisional task breakdown (stories/ACs to be finalized in the follow-up pass).

### Task 1: Validator seam
- `PayloadValidator` ABC, `ValidationResult`, `ValidatorRegistry`.
- `JsonSchemaValidator` implementation.
- Registry wired into the pipeline; unknown-dialect error.

### Task 2: RecordTypeSpec enforcement (opt-in)
- Add `submittable`, `schema_dialect`.
- Registry: submittable-owner uniqueness check; `get_submittable_owner(record_type)`.
- Discovery: surface submittable record types + schemas in `list_record_types`.

### Task 3: `process_structured` + `StructuredSubmission`
- Add the processor hook (default `NotImplementedError`).
- `StructuredSubmission` dataclass; tenant-adapter resolution reuse.

### Task 4: `submit_structured` tool + pipeline entry
- `IngestionPipeline.ingest_structured(...)` (validate → build submission → dispatch → observers).
- `submit_structured` tool on `IngestionPlugin`; strict error surfacing.

### Task 5: Inline-by-value content on the extract path
- Extend `ingest_documents` item shape (`{uri, content?, media_type?}`), backward-compatible.
- Pipeline: use provided content when present; format well-formedness gate; fetch fallback.
- `ResourceResolver` / bundle plumbing to carry inline content + declared media type.

### Task 6: MarkdownPlugin migration
- Receive framework-provided content instead of fetching (`urllib` removed from the hot path).
- Keep chunk/embed/write; verify parity with SPEC-011 parent/segment behavior.

### Task 7: Documentation
- Update plugin developer guide (submittable record types, `process_structured`, inline content).
- Update system overview + ingestion diagrams.
- Author proposed **ADR-011** (structured ingestion contracts; input≡output-at-metadata; two-gate model).

### Task 8: Reference structured plugin (test/example)
- A minimal submittable plugin exercising `submit_structured` end-to-end (validation pass + reject), independent of the Service Profile work.
