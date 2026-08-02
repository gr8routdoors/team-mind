# SPEC-013: Raw Content By-Value Ingestion

> **Status: DEFERRED / future.** Captured to preserve the design decision, not scheduled. This replaces the earlier "Pluggable Content Parsing / Format Decoders" draft, whose framework-owned-decoding premise was **rejected** — see *Superseded design* below.

## Overview

Lets a caller submit **raw content by value** — the bytes themselves plus a declared `media_type` — instead of only a URI the pipeline fetches. It is a small delta over today's raw/extract path: the framework delivers the provided bytes to the plugins that handle that input (routed by `semantic_type`), and **the plugin decodes and refines them exactly as it does for fetched URIs**. Decoding stays entirely in plugins, using standard Python libraries.

This is the *raw* counterpart to SPEC-012's *refined-record* push, and it is intentionally separate: SPEC-012 handles already-refined records; this handles raw input the plugin must still interpret.

## The three types (context)

- **`media_type`** — the format of the raw bytes (`text/markdown`, `audio/wav`); required when content is supplied inline (no extension to sniff).
- **`semantic_type`** — the input's semantic identity (`meeting`); the routing key that can fan the input out to multiple refining plugins.
- **`record_type`** — each plugin's refined output; unchanged.

## Scope (when scheduled)

**In scope:**

- By-value delivery on the raw path: `ingest_documents` items may carry `{uri, content, media_type}`; when `content` is present the pipeline uses it directly (no fetch), else it fetches as today. `uri` remains the identity key.
- A light **well-formedness bar**: if the receiving plugin's decoder rejects the bytes as the declared `media_type`, the item is rejected — but this lives in the plugin's decode, not a framework stage.
- Routing by `semantic_type` to the matching plugins (existing SPEC-008 machinery).

**Out of scope (explicitly rejected — see below):**

- **Framework-owned decoding / an intermediate representation / a shared decoder library.** Decoding is the plugin's job with off-the-shelf libraries.
- Anything on the refined-record push path (SPEC-012).

## Superseded design (why the decoder subsystem was dropped)

The earlier draft proposed a framework-owned `ContentDecoder`/`DecoderRegistry` that turned bytes into a canonical structure for plugins to consume. It was rejected for two reasons:

1. **No universal IR.** JSON is a dict, XML a tree, markdown an AST — there is no faithful union. A framework "decoded structure" is really a per-format shape every consumer must couple to, reintroducing the intermediate format we were trying to avoid.
2. **Low value.** A framework "markdown decoder" is either a thin wrapper over an existing library (no value) or it smuggles that intermediate format back in. Formats are easy enough to decode in-plugin with standard Python libraries, so the dedup win does not justify the coupling — especially with a single existing plugin.

The durable principle stands: **decode (bytes → structure) and interpret (structure → refined record) both live in the plugin; the framework only delivers bytes and routes.**

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Separate, deferred spec | fold into SPEC-012 vs. its own spec | SPEC-012 is refined-record push; raw by-value is a distinct, smaller, not-yet-needed capability. |
| No framework decoding | framework decode-stage / shared library vs. in-plugin | No universal IR; wrappers add no value and risk an accidental intermediate format. |
| Decode + interpret both in-plugin | split decode to framework vs. keep together | The value razor: interpretation is per-plugin; decode of easy formats is cheap in-plugin. |

## Stories

> Not scheduled. No stories/ACs until this spec is picked up.

## Relationship to SPEC-012

Independent. SPEC-012 (active) = validated push of *refined records* by `record_type`. This spec (deferred) = delivery of *raw content* by value, routed by `semantic_type`, decoded in-plugin.
