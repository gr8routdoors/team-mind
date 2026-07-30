# Future Work

_Parking lot for ideas that are out of scope for current phases._

## Service Profile Plugin

A plugin that builds and serves a structured, machine-readable profile of a
service — effectively a service catalog / contract registry living inside Team
Mind. A profile captures:

- **Dependencies:** internal service dependencies and external dependencies
  (third-party APIs, infra, libraries).
- **Schemas / data shapes:** the data structures the service uses.
- **Integration contracts:** what the service **provides** vs **consumes**
  (its inbound/outbound contracts).
- **Persisted data:** what the service stores in its own datastore.

**Open architectural question — population strategy.** Some of this is amenable
to deterministic extraction (parsing POM/package.json/OpenAPI specs/DB
migrations, i.e. the ingestion-tooling pattern already in the codebase), but
much of it — intent, "what contract does this really provide," inferring
consumers — needs an AI agent to synthesize. Likely a **hybrid**: deterministic
extractors feed an agent that assembles the profile. This overlaps directly
with the Phase 3 LLM Background Reaper (agent-driven background work, ADR-006)
and Meta-Plugins / Chained Processing (ADR-007) — Service Profile may be the
concrete use case that motivates building those.

## Kubernetes / Horizontal Scale

Run Team Mind on a Kubernetes cluster to scale ingestion and serving of data
independently. Forcing function for the Phase 4 "Database Migration" decision:
the current per-tenant SQLite sharding model (SPEC-010) is embedded and
single-node, so a distributed runtime pushes the storage question (shared
network-attached shards vs. a move to MongoDB/similar) to the front. Reframes
Phase 4 as "distributed runtime + storage story," not just a DB swap.

## Confluence Integration

Ingest from and (optionally) render query results back out to Confluence — the
enterprise leans on it heavily. Not yet scoped. The architecture already
anticipates it: the Resource/URI abstraction lists `confluence://` as an
example scheme (system-overview.md) and ADR-002 names Confluence docs as a
target for the source-backed plugin storage mode. A Confluence ingestion plugin
would slot into the existing plugin model; bidirectional (write-back) rendering
is a larger, separate capability.
