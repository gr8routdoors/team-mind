# STORY-001: Semantic Type and Media Type Schema — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Documents Table Has semantic_type Column | Happy path |
| AC-002 | Documents Table Has media_type Column | Happy path |
| AC-003 | Index on semantic_type | Happy path |
| AC-004 | Migration Applies Cleanly to Existing Data | Edge case |

---

### AC-001: Documents Table Has semantic_type Column

**Given** a freshly migrated database
**When** the `documents` table schema is inspected
**Then** a `semantic_type` column exists with type `TEXT` and default value `''`

### AC-002: Documents Table Has media_type Column

**Given** a freshly migrated database
**When** the `documents` table schema is inspected
**Then** a `media_type` column exists with type `TEXT` and default value `''`

### AC-003: Index on semantic_type

**Given** a freshly migrated database
**When** the indexes on the `documents` table are listed
**Then** an index `idx_documents_semantic_type` exists on the `semantic_type` column

### AC-004: Migration Applies Cleanly to Existing Data

**Given** a database with pre-existing rows in the `documents` table
**When** the migration adding `semantic_type` and `media_type` is applied
**Then** all existing rows have `semantic_type = ''` and `media_type = ''`
**And** no data loss occurs on the existing columns
