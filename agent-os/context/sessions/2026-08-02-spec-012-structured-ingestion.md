# Session: SPEC-012 Structured Ingestion Contracts — shape → implement → complete

> Date: 2026-08-02 | Participants: Devon, Claude

---

## Summary

Shaped SPEC-012 (Structured Ingestion Contracts) from scratch through several architectural pivots, wrote the full spec/design/ACs, then implemented all 7 stories via subagent dispatch with two-stage review. Spec is **complete** — 490 tests green, all stories passed independent spec + quality review, plus a final integration review.

---

## Decisions Made (the journey matters — we changed our minds a few times)

- **Scope collapsed to "a validated write endpoint."** Initial straw-man (two-gate validator seam, framework decoders, `process_structured` hook, inline-raw path, a separate SPEC-013) was over-built. Most machinery already existed (routing, storage, observer subscription-by-`record_type`, reliability seeding). Final scope: one validated write path + a thin MCP tool. — _We repeatedly "hallucinated" building things the framework already had._
- **Three-type model clarified (the crux).** `media_type` (raw format) vs `semantic_type` (input identity, e.g. `meeting`) vs `record_type` (refined output). We had been conflating `record_type` with `semantic_type`. This is the SPEC-008/ADR-007 model — not new. Push routes by `record_type`; `semantic_type` fan-out (one input → many outputs) is a raw-path concern via existing routing. — _This unblocked the whole design._
- **IDL = JSON Schema** (Protobuf and Pydantic considered and rejected). Deciding factor: MongoDB validates natively with `$jsonSchema`; we store records as JSON (not binary) so `json_extract` metadata search keeps working. Pydantic is Python-bound; proto adds a toolchain and isn't Mongo-enforceable. We flip-flopped (proto for a while) before Devon's Mongo research settled it. — _Proto's wins (binary/codegen) were things we don't use._
- **Single canonical `write_record` toolkit = the validation choke point.** Framework AND plugins call it, so every write is validated against the record type's schema. Prevents write-sprawl and makes validation universal & free. — _Devon's key insight._
- **Mandatory schema, no opt-out.** Every record type declares a JSON Schema; `write_record` always validates. We're pre-release (no legacy), and Mongo will enforce anyway. `submittable` is a *separate* axis = external-push exposure only. — _"Allowing unvalidated writes because one plugin predates the concept is how a data store rots."_
- **`metadata` is 1:1 with the payload.** Envelope fields (`uri`,`id`,`plugin`,`content_hash`,`vector`,`tenant`) live on the record; payload lives nested under `metadata` (never flattened) → no envelope/`_id` collisions, mechanical SQLite→Mongo remap. Payload-field renames are storage-breaking.
- **Batch endpoint** matching `ingest_documents` (array): strict per record, best-effort across the batch, empty batch is an error.
- **Framework-owned decoding rejected.** No universal IR; decoders would be valueless wrappers or a smuggled intermediate format. Decode + interpret both stay in plugins. Raw-content-by-value folded in as one story; SPEC-013 retired.

---

## Learnings & Context to Preserve

### Implementation
- **The single-write-path invariant**: every `documents` write goes through `write_record` EXCEPT the deliberate SPEC-011 parent (no vector/weight → `save_parent`, but preceded by `validate_record`). Grep confirms no other bypass.
- `write_record` gained 3 optional envelope params (`semantic_type`/`media_type`/`plugin_version`) so raw-path plugins (markdown) stamp them; defaults preserve the push path.
- New storage primitive `save_metadata_record` / `update_metadata` for metadata-only (no-vector) records — existing `save_payload` always writes a vector; `save_parent` writes neither weight nor vector.
- Embedding + hashing extracted to `embedding.py`; `markdown.py` re-exports old names.
- `RecordTypeSpec` has NO `semantic_types` field — pushed `IngestionEvent`s carry `semantic_types=[]`. Do not invent one.

### Process
- Ran dispatch-subagents sequentially (dependency chain 001→002→003; 001→004; 001+002→005; 006 independent) to avoid parallel subagents racing on the shared working tree/branch.
- Mobile app truncates long assistant messages — keep replies concise.

---

## Artifacts Updated

| Artifact | Change |
|----------|--------|
| `agent-os/specs/SPEC-012-*/` | Full spec: README, design, stories.yml, 6 AC files, coverage-matrix |
| `src/team_mind_mcp/toolkit.py` | NEW — `write_record`, `validate_record` |
| `src/team_mind_mcp/embedding.py` | NEW — shared `mock_embed`, `content_hash` |
| `src/team_mind_mcp/server.py` | `RecordTypeSpec.submittable/embed_source`, `_guard_record_types`, `get_submittable_spec` |
| `src/team_mind_mcp/ingestion.py` / `ingestion_plugin.py` | `ingest_structured`, `submit_structured`, inline `documents[]` content |
| `src/team_mind_mcp/storage.py` | `save_metadata_record`, `update_metadata`, `content_hash` on update |
| `src/team_mind_mcp/markdown.py` | Compliant schemas, writes via `write_record`, inline-content branch |
| `src/team_mind_mcp/discovery.py` | `submittable` flag in `list_record_types` |
| `agent-os/context/architecture/ADRs/ADR-011-*.md` | NEW decision record |
| `plugin-developer-guide.md` / `system-overview.md` | Updated; guide migrated off direct `save_payload` |
| `agent-os/specs/index.yml` | SPEC-012 → complete; SPEC-013 removed |

---

## Open Questions & Next Steps

- [ ] Devon to review the full PR (`claude/structured-ingest-api-j6tq0c`) in detail; bring back any issues.
- [ ] Minor tracked follow-ups (in `stories.yml` `known_followups`): guard edge cases (intra-batch duplicate-submittable; errors not naming plugin); `ingest_structured` best-effort catches only `RecordValidationError`; vestigial `write_record` `tenant_id`; markdown transient-spec `.plugin` mutation; raw-by-value AC-002 whole-call rejection.
- [ ] Next roadmap item after this: Phase 3 remaining (Curator/Reaper are future) or Phase 4 Service Profile Plugin (the driving consumer of SPEC-012).

---

> **If you only remember one thing:**
> `write_record` is the single validated write path — every record write goes through it (schema-validated), the only exception being the SPEC-011 parent container. Never teach or add a `save_payload` path that bypasses it.

---

_Recorded by: Claude_
