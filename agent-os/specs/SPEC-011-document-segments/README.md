# SPEC-011: Document Segments

## Overview

Introduces a formal parent-child relationship on the `documents` table via a `parent_id` column. Parent documents serve as logical containers with metadata but no vector embedding. Segments (children) are the searchable, independently-weighted atoms. This formalizes the micro-document pattern already used by MarkdownPlugin and needed by the travel plugin.

## Scope

**In scope:**
- `parent_id INTEGER REFERENCES documents(id)` column on the `documents` table.
- `save_parent()` storage method for creating parent documents (no vector, no weight).
- `parent_id` parameter on `save_payload()` for linking segments to parents.
- `parent_id` included in search results from `retrieve_by_vector_similarity`.
- `get_document_with_segments()` storage method for parent/sibling navigation.
- Aggregate parent scoring computed at query time (AVG of children's usage_score).
- Cascade delete: `delete_by_uri` on a parent also deletes child segments.
- `delete_by_id()` for surgical single-document deletion (cascades automatically for parents).
- URI convention for segments (parent URI + segment-specific suffix).
- MarkdownPlugin updated to create parent documents per source file, with paragraph chunks as segments.
- Update plugin developer guide with segment patterns and examples.
- Update system overview, README, and relevant ADRs with cross-references.
- Correct stale `doctype`/`DoctypeSpec` references in existing documentation to `record_type`/`RecordTypeSpec`.

**Out of scope:**
- Parent-level vector embeddings (composite/summary vectors) — deferred, may add later.
- Nested segments (segments of segments) — one level of hierarchy only.
- Segment-aware EventFilter on observers — future enhancement.
- Permission gating on parent/segment access — future, tied to SPEC-010 tenant permissions.

## Context

**References:**
- `agent-os/context/architecture/ADRs/ADR-009-document-segments.md` — Full design rationale.
- `agent-os/context/architecture/ADRs/ADR-003-relevance-weighting.md` — "The unit of weighting is the row" — segments formalize this.
- `agent-os/context/architecture/ADRs/ADR-008-multi-tenancy-metadata-search.md` — Multi-tenancy and metadata search compose with segments.
- `agent-os/specs/SPEC-010-multi-tenancy-metadata-search/design.md` — tenant_id threading that segments must respect.

## Decisions

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| `parent_id` on `documents` table | Separate `segments` table vs column | Segments need the same fields as documents. One table avoids schema duplication. |
| No parent vector | Vector vs no vector on parents | Parents are containers, not searchable units. KNN matches segments. |
| Computed parent score | Stored vs computed aggregate | Computed is always consistent, no cascade writes on feedback. |
| AVG for aggregate | AVG vs SUM vs MAX | AVG reflects overall quality without bias toward larger collections. |
| One level of hierarchy | Single vs multi-level | Sufficient for current use cases. Multi-level adds complexity with unclear value. |
| Backward compatible | Breaking vs opt-in | `parent_id = NULL` default means existing plugins are unaffected. |

## Stories

See `stories.yml` for current status.

| ID | Story | Status |
|----|-------|--------|
| STORY-001 | Parent ID Schema and Index | pending |
| STORY-002 | Save Parent Storage Method | pending |
| STORY-003 | Parent ID on Save Payload | pending |
| STORY-004 | Parent ID in Search Results | pending |
| STORY-005 | Get Document with Segments | pending |
| STORY-006 | Aggregate Parent Scoring | pending |
| STORY-007 | Delete Operations (Cascade + delete_by_id) | pending |
| STORY-008 | MarkdownPlugin Segment Migration | pending |
| STORY-009 | Update Documentation, Diagrams, and Fix Stale References | pending |
