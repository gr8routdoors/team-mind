# STORY-002: Storage Layer

## Acceptance Criteria

### AC-001: SQL column renamed with PRAGMA guard
- `StorageAdapter.initialize()` checks `PRAGMA table_info(documents)` for the column name.
- If `doctype` column exists: `ALTER TABLE documents RENAME COLUMN doctype TO record_type`.
- Migration runs once on existing databases; fresh databases use `record_type` from creation.
- `CREATE TABLE documents` statement uses `record_type TEXT NOT NULL DEFAULT ''`.

### AC-002: Old indexes dropped, new indexes created
- After column rename: `DROP INDEX IF EXISTS idx_documents_doctype`, `idx_documents_plugin_doctype`, `idx_documents_uri_plugin_doctype`.
- New indexes created: `idx_documents_record_type`, `idx_documents_plugin_record_type`, `idx_documents_uri_plugin_record_type`.
- New indexes use `CREATE INDEX IF NOT EXISTS` — safe to run on both fresh and migrated databases.

### AC-003: save_payload parameter renamed
- `save_payload(uri, metadata, vector, plugin, doctype, ...)` → `record_type` parameter.
- SQL `INSERT` statement uses `record_type` column.
- All callers (MarkdownPlugin, tests) updated to `record_type=...`.

### AC-004: delete_by_uri parameter renamed
- `delete_by_uri(uri, plugin, doctype)` → `record_type` parameter.
- SQL `WHERE doctype = ?` → `WHERE record_type = ?`.
- All callers updated.

### AC-005: lookup_existing_docs parameter renamed
- `lookup_existing_docs(uri, plugin_name, doctype)` → `record_type` parameter.
- SQL `WHERE uri = ? AND plugin = ? AND doctype = ?` → `record_type`.
- All callers in `ingestion.py` updated.

### AC-006: retrieve_by_vector_similarity parameter renamed
- `retrieve_by_vector_similarity(..., doctypes=None)` → `record_types=None`.
- SQL filter clause `d.doctype IN (...)` → `d.record_type IN (...)`.
- SELECT column alias `d.doctype` → `d.record_type` in result row.
- Result dict key `"doctype"` → `"record_type"`.

### AC-007: Tests pass
- `test_storage_schema.py` verifies the column is named `record_type` in fresh databases.
- `test_plugin_migration.py` (or equivalent) verifies the rename migration runs on existing databases.
- All storage-dependent tests pass with no regressions.
