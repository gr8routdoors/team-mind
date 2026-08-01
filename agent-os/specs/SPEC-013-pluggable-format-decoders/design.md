# SPEC-013: Pluggable Content Parsing / Format Decoders — Design

## Overview

Moves format decoding out of plugins and into a framework-owned subsystem. A `ContentDecoder` turns `(bytes, media_type)` into a **faithful, lossless** structure and asserts well-formedness; a `DecoderRegistry` routes all inbound content — inline (SPEC-012 by-value) or fetched (existing URI path) — through the matching decoder before a plugin sees it. Plugins become pure **interpreters** of decoded structures.

This spec generalizes the decode half of the SPEC-012 seam. It does not touch the record-schema gate (that is SPEC-012).

## The razor, restated for implementers

For any inbound content, work splits at exactly one line:

| Step | Example (markdown) | Example (JSON record) | Owner |
|------|--------------------|-----------------------|-------|
| **Decode** — bytes → faithful structure + well-formedness check | parse to block/AST structure | `json.loads` → dict | **framework (this spec)** |
| **Interpret** — structure → stored records | split blocks into chunks, pick embed text, parent+segments | map fields, choose embed text | **plugin** |

If a transformation involves a *choice* (how to chunk, what to summarize, which field to embed), it is interpret and stays in the plugin. If it is the deterministic, lossless recovery of the format's structure, it is decode and belongs in a decoder.

## Components

| Component | Type | Change | Purpose |
|-----------|------|--------|---------|
| `ContentDecoder` | ABC (new) | new | Declares a handled `media_type`; `decode(bytes) -> DecodedContent`; well-formedness validation. |
| `DecoderRegistry` | Service (new) | new | Maps `media_type → ContentDecoder`; routes content pre-plugin; raises/《rejects》on unknown or malformed. |
| `DecodedContent` | dataclass (new) | new | Faithful structure + retained raw bytes + resolved `media_type`. |
| `JsonDecoder` | Decoder (new) | new | `application/json` → dict/list (promoted from SPEC-012's trivial decoder). |
| `TextDecoder` | Decoder (new) | new | `text/plain`, `text/markdown` (identity/UTF-8) — the pre-AST baseline. |
| `MarkdownDecoder` | Decoder (new) | new | `text/markdown` → block/AST structure; absorbs MarkdownPlugin's current parsing. |
| `IngestionPipeline` | Service | modified | Route inline + fetched content through `DecoderRegistry`; the format gate lives here. |
| `MarkdownPlugin` | Processor | modified | Consumes `DecodedContent` blocks; keeps only interpretation (chunk/embed/write). |
| `DoctypeDiscoveryPlugin` / discovery | ToolProvider | modified | Report which `media_type`s are decodable. |

## Data Flow

```
inbound content (inline bytes OR fetched URI bytes) + media_type
  → DecoderRegistry.for(media_type)          # unknown media_type → reject (bad-data bar)
  → decoder.decode(bytes) -> DecodedContent  # malformed for the declared format → reject (bad-data bar)
  → provide DecodedContent (faithful structure + raw) to matching processors
  → processor interprets: chunk / choose embed text / fan out / write   # unchanged plugin responsibility
```

The format gate is now a single choke point serving **both** ingestion paths. It replaces per-plugin, ad-hoc parsing and the implicit "assume it's valid" behavior of the current URI path.

## Interfaces

### `ContentDecoder` (new)

```python
@dataclass
class DecodedContent:
    media_type: str
    structure: object          # faithful, per-format (dict for JSON, block list/AST for markdown, ...)
    raw: bytes                 # always retained — plugins may reach past the decoder

class ContentDecoder(ABC):
    @property
    @abstractmethod
    def media_type(self) -> str: ...          # or a list, for aliases

    @abstractmethod
    def decode(self, raw: bytes) -> DecodedContent: ...
        # Must raise a well-defined DecodeError on malformed input (the bad-data bar).
```

### `DecoderRegistry` (new)

```python
class DecoderRegistry:
    def register(self, decoder: ContentDecoder) -> None: ...
    def for_media_type(self, media_type: str) -> ContentDecoder: ...   # raises on unknown
    def supported(self) -> list[str]: ...                              # for discovery
```

### Canonical representation policy

- **Per-format, faithful, lossless.** No universal IR. JSON → `dict/list`; markdown → an ordered block/AST structure; XML → a tree; etc.
- **Raw retained.** `DecodedContent.raw` is always present so a plugin needing something the decoder did not surface is never blocked on the framework.
- **Decode is judgment-free.** Anything requiring a choice (chunk boundaries, summaries) is *interpret* and does not belong in a decoder.

## Migration: MarkdownPlugin

**Before (today):** the plugin fetches the URI, reads bytes, splits into paragraph chunks, embeds each, writes parent + segments — parsing and interpretation entangled inside the plugin.

**After:** the pipeline decodes markdown into a block structure via `MarkdownDecoder`. The plugin receives `DecodedContent`, applies its **chunking choice** to the blocks, chooses embedding text, and writes parent + segments (SPEC-011 behavior preserved). Parsing leaves the plugin; interpretation stays.

This is the reference migration that proves the razor and the registry. Any future processor follows the same shape: *decode is done for you; you interpret.*

## Trade-offs & Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| `media_type` as the registry key | Custom format ids vs. media types | Reuses the existing `media_types` vocabulary and the caller-declared `media_type` from SPEC-012's inline path. |
| Retain raw bytes on `DecodedContent` | Decoded-only vs. decoded + raw | Prevents the decoder's canonical from becoming a lossy bottleneck. |
| Decoders raise on malformed input | Return optional vs. raise | Malformed = the bad-data bar; a raised `DecodeError` maps directly to a boundary rejection. |
| One decoder per media type | Chain vs. single | Simplicity; aliases handled by a decoder declaring multiple media types. Chaining/transcoding is future, if ever. |
| Grow catalog per format | Ship many decoders now vs. per-need | Avoids speculative parsers; each addition is a small, isolated registration. |

## Backward compatibility

- The URI path continues to work; it simply gains a decode step (and, for the first time, a well-formedness gate). Content that previously "worked" because a plugin tolerated it should be checked against the new gate during migration.
- Plugins that have not migrated keep their current `process_bundle` contract until moved to the decoded-content shape; migration is per-plugin (only MarkdownPlugin exists today).

---

## Execution Plan

Provisional task breakdown (stories/ACs to be finalized in the follow-up pass). Sequenced **after** SPEC-012.

### Task 1: Decoder subsystem
- `ContentDecoder` ABC, `DecodedContent`, `DecoderRegistry`.
- Promote SPEC-012's trivial JSON/text decoders into `JsonDecoder` / `TextDecoder`.
- Unknown-media-type rejection; `DecodeError` → boundary rejection mapping.

### Task 2: Pipeline integration (the shared format gate)
- Route inline (SPEC-012) and fetched content through `DecoderRegistry` before processor dispatch.
- Single well-formedness gate for both paths.
- Thread `DecodedContent` into the processor-facing bundle/context.

### Task 3: MarkdownDecoder + MarkdownPlugin migration
- `MarkdownDecoder`: markdown → ordered block/AST structure.
- MarkdownPlugin consumes `DecodedContent`; retains chunking/embedding/write; SPEC-011 parent/segment parity verified.

### Task 4: Discovery
- Report decodable `media_type`s through the discovery surface.

### Task 5: Documentation + ADR
- Plugin developer guide: "decode is done for you; you interpret"; how to register a decoder.
- System overview + ingestion diagrams updated for the decode choke point.
- Author proposed **ADR-012** (pluggable content decoders; decode-vs-interpret; no universal IR; grow-per-format).

### Task 6 (per-need, not committed): next-format decoders
- Add YAML / XML / CSV decoders only when a real consumer drives them. Left explicit so it is chosen, not assumed.
