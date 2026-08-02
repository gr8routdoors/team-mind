# SPEC-013: Pluggable Content Parsing / Format Decoders

## Overview

Generalizes the **decode seam** seeded by SPEC-012 into a first-class, pluggable **content-parsing subsystem**. Format decoding moves *out of plugins* and into a framework-owned `DecoderRegistry`: each decoder turns bytes + a declared `media_type` into a *faithful, lossless* structure and validates well-formedness (the shared "bad-data bar"). Plugins stop bundling their own parsers and instead receive a trusted structure to **interpret**. New formats onboard by registering a decoder — no big-bang parser library, no core rewrite.

## The organizing principle

One razor governs the whole subsystem — the same one SPEC-012 introduced:

- **Decode** (this spec, framework): bytes + declared format → a faithful structure. Lossless, deterministic, no judgment. `json.loads`, markdown→AST, XML→tree, YAML, CSV.
- **Interpret** (stays in plugins): structure → stored records. Chunking, choosing embedding text, fan-out to parent + segments, derived fields. A *choice* that varies per plugin.

Centralizing **decode** is a real win for plugin developers: no plugin re-implements a JSON or markdown parser, and a single format is parsed **once** for many consumers (e.g. a "summary" plugin and a "word-count" plugin both walk the same markdown structure). Centralizing **interpret** would be a mistake — it would force a lossy canonical that becomes a coupling and evolution bottleneck. The razor keeps the line in the right place.

## Why this is its own spec

SPEC-012 ships the *seam* plus the two trivial decoders it needs (JSON, text). It deliberately does **not** build a library of real parsers. SPEC-013 is where that library — and the ergonomics of registering, discovering, and evolving decoders — gets designed and populated. The split is on a **principle** (seam vs. catalog / decode-vs-interpret), not on cost. In fact the migration cost is tiny: there is exactly one real processor today (`MarkdownPlugin`), plus a test double.

## Scope

**In scope:**

- A `ContentDecoder` interface: a declared `media_type` it handles, a `decode(bytes) -> DecodedContent` producing a faithful structure, and well-formedness validation (the format gate).
- A framework-owned `DecoderRegistry` keyed by `media_type`; the pipeline routes inline **and** fetched content through the matching decoder *before* handing it to a plugin.
- A **per-format canonical representation policy**: each format has its own faithful structure; there is **no universal IR**. Raw bytes remain available to plugins for anything a decoder does not surface.
- Real decoders beyond the trivial pair, onboarded per actual need: **markdown → block/AST structure** (migrating MarkdownPlugin's current inline parsing), and the next formats driven by real consumers (YAML, XML, CSV as they arrive).
- Migration of `MarkdownPlugin` (and any later processors) to consume decoded structure instead of parsing raw bytes.
- The **format well-formedness gate** as the shared "bad-data bar" for *both* ingestion paths (inline raw content and fetched URIs) — reject a supposed markdown/JSON/XML document that is not actually well-formed, before any plugin sees it.
- Discovery of supported formats (which `media_type`s the platform can decode).

**Out of scope:**

- **Interpretive / lossy transformations** — chunking, summarization, symbol extraction, embedding-text selection. These stay in plugins by principle.
- **Speculative decoders** for formats with no driving use case. Built per-need; the registry makes each addition cheap.
- The **structured-record push path** and its schema gate — that is SPEC-012. (This spec is the *format* gate; SPEC-012 owns the *record-schema* gate.)
- A universal intermediate representation across all formats. Explicitly rejected (JSON is a dict, XML a tree, protobuf a typed message — no faithful union exists).

## Context

**References:**

- `agent-os/specs/SPEC-012-structured-ingestion-contracts/design.md` — the decode seam this spec generalizes, the decode-vs-interpret razor, and the sibling record-schema gate (protobuf + protovalidate) that stays in SPEC-012.
- `src/team_mind_mcp/media_types.py` — media-type resolution; decoders key off the same media types.
- `src/team_mind_mcp/markdown.py` — the parsing this spec pulls into a decoder; MarkdownPlugin becomes an *interpreter* of decoded blocks.
- `src/team_mind_mcp/ingestion.py` — pipeline content path where decoders attach.
- Roadmap Phase 3 — "Structured Ingestion Contracts" (its enabling sibling) and the Service Profile / Meta-Plugin consumers downstream.

**Standards:**

- `testing` — TDD principles and coverage.
- `bdd` — AC format and coverage patterns (deferred to the AC/BDD pass).
- `code-style/python` — Python conventions.
- Proposed **ADR-012: Pluggable Content Decoders** — recording the decode-vs-interpret razor, the no-universal-IR decision, and the grow-per-format policy.

**Visuals:** None.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Split principle = decode vs. interpret | Blast-radius/cost vs. conceptual boundary | Cost is a heuristic, not a principle — and it is near-zero here (one plugin). Decode-vs-interpret is the durable line. |
| Framework owns decode | Per-plugin parsing vs. shared registry | Dedup (no repeated JSON/markdown parsers), parse-once-many-consumers, and a uniform ingestion door. Also *forced* by inline-by-value: a plugin cannot fetch a URI it was never given. |
| No universal IR | One canonical structure vs. per-format | There is no faithful union across JSON/XML/protobuf; a forced canonical is lossy and becomes a coupling bottleneck. |
| Raw always available to plugins | Decoded-only vs. decoded + raw | A plugin needing a field the decoder dropped must not be blocked on the framework. |
| Grow the catalog per format | Big-bang parser library vs. per-need | The next real format drives the next decoder; the registry makes each addition cheap; avoids speculative surface. |
| Interpret stays in plugins | Centralize chunking/extraction vs. keep in plugin | Interpretation is a per-plugin choice; centralizing it recreates the bottleneck the razor avoids. |

## Stories

> Stories, acceptance criteria, and BDD scaffolding are intentionally **deferred** to a follow-up shaping pass. A provisional breakdown lives in `design.md` → Execution Plan. `stories.yml` will be created then.

## Relationship to SPEC-012

**Depends on SPEC-012.** SPEC-012 establishes the seam (framework-owned decode + validate at the boundary) and the trivial decoders. SPEC-013 turns the decode half into the `ContentDecoder` / `DecoderRegistry` subsystem, migrates real parsing out of plugins, and makes the format gate the shared bad-data bar. The two gates stay cleanly divided: **SPEC-013 = format well-formedness; SPEC-012 = record-schema conformance.**
