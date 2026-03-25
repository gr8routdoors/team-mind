# STORY-002: Doc Weights Table & Ingestion Hook — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Table Created on Initialize | Happy path |
| AC-002 | Weight Row Auto-Created on Save | Happy path |
| AC-003 | Decay Half-Life Copied from Registry | Happy path |
| AC-004 | No Doctype Match Uses Null Decay | Edge case |
| AC-005 | Existing Databases Get Migration | Integration |

---

### AC-001: Table Created on Initialize

**Given** a fresh database
**When** `StorageAdapter.initialize()` is called
**Then** the `doc_weights` table exists with columns: `doc_id`, `usage_score`, `last_accessed`, `created_at`, `tombstoned`, `decay_half_life_days`

---

### AC-002: Weight Row Auto-Created on Save

**Given** an initialized StorageAdapter
**When** `save_payload` is called and creates a document
**Then** a corresponding row in `doc_weights` is created with `usage_score=0.0`, `tombstoned=0`, and `created_at` set

---

### AC-003: Decay Half-Life Copied from Registry

**Given** a StorageAdapter with a registry reference where a doctype declares `decay_half_life_days=30`
**When** `save_payload` is called with that doctype
**Then** the `doc_weights` row has `decay_half_life_days=30`

---

### AC-004: No Doctype Match Uses Null Decay

**Given** a `save_payload` call with a doctype not registered in any plugin
**When** the weight row is created
**Then** `decay_half_life_days` is NULL (no decay)

---

### AC-005: Existing Databases Get Migration

**Given** a database created before the weighting feature
**When** `StorageAdapter.initialize()` runs
**Then** the `doc_weights` table is created without error
**And** existing documents have no weight rows (lazy creation)
