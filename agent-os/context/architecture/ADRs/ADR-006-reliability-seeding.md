# ADR-006: Retire Inline Librarian, Adopt Reliability Seeding + Background Conflict Detection

**Status:** Accepted
**Date:** 2026-03-27
**Supersedes:** Original Librarian concept from system-overview.md and roadmap.md
**See also:** [ADR-003: Relevance Weighting](ADR-003-relevance-weighting.md), [Plugin Developer Guide](../plugin-developer-guide.md)

## Context

The original roadmap envisioned a "Librarian" as an inline LLM-as-a-judge validation gate that sits between ingestion and commit, evaluating new content against existing "Golden" documents for conflicts and quality.

Since then, we've built several capabilities that address the Librarian's original motivations:

| Original Librarian concern | What we built |
|---------------------------|---------------|
| Duplicate content detection | URI-based idempotent ingestion with content hashing (SPEC-005) |
| Stale content persistence | Tombstoning, decay, and feedback signals (SPEC-004) |
| Update detection | IngestionContext with content_changed and plugin_version_changed (SPEC-005) |
| Post-ingestion quality signals | Cumulative moving average feedback tool (SPEC-004) |

What remains unaddressed:
1. **Initial quality/reliability seeding** — not all documents should start at the same score. A CTO's architecture doc vs. a random meeting note should have different initial reliability.
2. **Cross-document conflict detection** — "this new document says X but an existing trusted document says Y."

## Decision

We retire the Librarian as a single inline gatekeeper and replace it with two purpose-built mechanisms:

### 1. Reliability Seeding (inline, during ingestion)

Documents can be seeded with an initial reliability score at ingestion time through three layers:

**Layer 1: Ingest hint (always present)**
The caller who triggers ingestion provides a `reliability_hint` that travels with the bundle. This is metadata about the source — "this came from the architecture repo" (high) vs. "this came from a Slack export" (low).

```python
await pipeline.ingest(uris, reliability_hint=0.8)
```

**Layer 2: Plugin default (declared on DoctypeSpec)**
Plugins declare a default reliability for their doctypes:

```python
DoctypeSpec(
    name="code_signature",
    default_reliability=0.9,   # Code is inherently reliable
)
DoctypeSpec(
    name="meeting_notes",
    default_reliability=0.5,   # Transcripts are medium reliability
)
```

**Layer 3: Plugin override (at process time)**
The plugin sees both the ingest hint and its own default, then decides the final seed value. The plugin always has the last word.

```python
async def process_bundle(self, bundle):
    hint = bundle.reliability_hint  # From caller
    default = self.doctypes[0].default_reliability  # From doctype

    # Plugin decides: use hint, use default, or compute its own
    final_reliability = hint if hint is not None else default

    storage.save_payload(..., initial_score=final_reliability)
```

The `initial_score` seeds the `usage_score` in `doc_weights` at ingestion time. Documents with higher initial reliability rank higher in search results from the start, before any feedback signals arrive.

### 2. Background Conflict Detection (external, not inline)

Cross-document contradiction detection runs as a **separate background process**, not inline in the ingestion pipeline. It:

- Periodically scans for recently ingested/updated documents
- Cross-references them against existing trusted documents using LLM inference
- Flags contradictions for human review or auto-tombstones with low confidence
- Can be implemented as an `IngestObserver` that queues work for background analysis, or as a standalone cron process

This is deferred to a future spec. It does not block the core engine or any current Phase 3 work.

## Alternatives Considered

### 1. Keep the inline Librarian as designed

Run LLM inference on every ingestion to validate content before commit.

**Rejected because:**
- Adds LLM latency to every ingest operation — non-starter at scale.
- Non-deterministic — LLM judgments vary across runs.
- The most common cases (dedup, staleness, update detection) are already solved deterministically.
- Conflict detection is better suited for batch processing where latency isn't a concern.

### 2. Global reliability scoring in the platform (not plugin-controlled)

The platform assigns reliability scores based on URI patterns or source metadata, without plugin input.

**Rejected because:**
- The platform doesn't know enough about the content to assign reliability. Is a `.md` file an architecture doc or rough notes? Only the plugin or the caller knows.
- Plugins that parse code can assert high reliability from domain knowledge. The platform can't.

### 3. Reliability as a separate table (like doc_weights)

Create a `doc_reliability` table separate from `doc_weights`.

**Rejected because:**
- Reliability and usage scoring serve the same purpose — influencing search ranking. Keeping them in one `usage_score` field (seeded at different starting points) is simpler and composes naturally with the existing composite scoring formula.
- A separate table would require a separate JOIN in the query, adding complexity for no functional benefit.

## Consequences

### Positive

- **No inline LLM dependency.** Ingestion remains deterministic and fast.
- **Fair initial ranking.** High-authority content ranks higher from the start, before any feedback arrives.
- **Plugin autonomy.** Plugins decide their own reliability based on domain knowledge and ingest hints.
- **Ingest hint always available.** Even plugins that don't care about reliability get the hint — they can ignore it or use it.
- **Background conflict detection deferred cleanly.** It's a separate concern with separate infrastructure needs. Not blocked by anything.

### Negative

- **Reliability is honor-system.** Plugins self-report reliability. A misconfigured plugin could seed artificially high scores. Mitigated by the feedback system correcting scores over time.
- **No pre-commit validation.** Bad content enters the knowledge base immediately. It must be corrected after the fact via feedback/tombstone. For most use cases this is acceptable; for regulated environments it may not be.

### Neutral

- The roadmap's "Librarian" item is replaced by "Reliability Seeding" (SPEC-007) and "Conflict Detection" (future spec, Phase 3).
- The `usage_score` field in `doc_weights` now has dual purpose: initial reliability seed + accumulated feedback. The math works the same — higher score = higher ranking.
