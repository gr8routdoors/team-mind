"""
SPEC-008 / STORY-001: Semantic Type and Media Type Schema

NOTE: The registered_plugins table moved to TenantStorageManager / system.sqlite
per SPEC-010 / STORY-001. AC-005 and AC-006 updated accordingly.
"""

import os
import sqlite3
import sqlite_vec
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.tenant_manager import TenantStorageManager


def test_ac001_documents_table_has_semantic_type_column(tmp_path):
    """AC-001: Documents Table Has semantic_type Column"""
    db_path = tmp_path / "test.db"

    # Given a freshly migrated database
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # When the documents table schema is inspected
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = {
            row[1]: {"type": row[2], "default": row[4]} for row in cursor.fetchall()
        }

    # Then a semantic_type column exists with type TEXT and default value ''
    assert "semantic_type" in columns
    assert columns["semantic_type"]["type"] == "TEXT"
    assert columns["semantic_type"]["default"] == "''"

    adapter.close()


def test_ac002_documents_table_has_media_type_column(tmp_path):
    """AC-002: Documents Table Has media_type Column"""
    db_path = tmp_path / "test.db"

    # Given a freshly migrated database
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # When the documents table schema is inspected
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = {
            row[1]: {"type": row[2], "default": row[4]} for row in cursor.fetchall()
        }

    # Then a media_type column exists with type TEXT and default value ''
    assert "media_type" in columns
    assert columns["media_type"]["type"] == "TEXT"
    assert columns["media_type"]["default"] == "''"

    adapter.close()


def test_ac003_index_on_semantic_type(tmp_path):
    """AC-003: Index on semantic_type"""
    db_path = tmp_path / "test.db"

    # Given a freshly migrated database
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # When the indexes on the documents table are listed
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        index_names = [row[0] for row in cursor.fetchall()]

    # Then an index idx_documents_semantic_type exists on the semantic_type column
    assert "idx_documents_semantic_type" in index_names

    adapter.close()


def test_ac004_migration_applies_to_existing_data(tmp_path):
    """AC-004: Migration Applies Cleanly to Existing Data"""
    db_path = tmp_path / "test.db"

    # Given a database with pre-existing rows in the documents table
    # (simulate an older database without semantic_type / media_type columns)
    with sqlite3.connect(str(db_path)) as conn:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uri TEXT NOT NULL,
                plugin TEXT NOT NULL DEFAULT '',
                doctype TEXT NOT NULL DEFAULT '',
                metadata JSON,
                content_hash TEXT,
                plugin_version TEXT DEFAULT '0.0.0'
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_documents USING vec0(
                id INTEGER PRIMARY KEY,
                embedding float[768]
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS doc_weights (
                doc_id INTEGER PRIMARY KEY REFERENCES documents(id),
                usage_score REAL DEFAULT 0.0,
                signal_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                tombstoned INTEGER DEFAULT 0,
                decay_half_life_days REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registered_plugins (
                plugin_name TEXT PRIMARY KEY,
                plugin_type TEXT NOT NULL,
                module_path TEXT NOT NULL,
                config JSON,
                event_filter JSON,
                enabled INTEGER DEFAULT 1,
                registered_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        # Insert a pre-existing row
        conn.execute(
            "INSERT INTO documents (uri, plugin, doctype, plugin_version) VALUES (?, ?, ?, ?)",
            ("file:///existing/doc.md", "old_plugin", "old_doctype", "1.0.0"),
        )

    # When the migration adding semantic_type and media_type is applied
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Then all existing rows have semantic_type = '' and media_type = ''
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute(
            "SELECT uri, plugin, record_type, plugin_version, semantic_type, media_type FROM documents"
        )
        rows = cursor.fetchall()

    assert len(rows) == 1
    uri, plugin, record_type, plugin_version, semantic_type, media_type = rows[0]

    # And no data loss occurs on the existing columns
    assert uri == "file:///existing/doc.md"
    assert plugin == "old_plugin"
    assert record_type == "old_doctype"
    assert plugin_version == "1.0.0"

    # And new columns default to ''
    assert semantic_type == ""
    assert media_type == ""

    adapter.close()


def test_ac005_registered_plugins_has_semantic_types_and_supported_media_types_columns(
    tmp_path,
):
    """AC-005: registered_plugins table in system.sqlite has semantic_types and supported_media_types."""
    base = str(tmp_path / "mind")

    # Given a freshly initialized TenantStorageManager
    mgr = TenantStorageManager(base)
    mgr.initialize()
    mgr.close()

    # When the registered_plugins table schema in system.sqlite is inspected
    system_db = os.path.join(base, "system.sqlite")
    with sqlite3.connect(system_db) as conn:
        cursor = conn.execute("PRAGMA table_info(registered_plugins)")
        columns = {
            row[1]: {"type": row[2], "default": row[4]} for row in cursor.fetchall()
        }

    # Then semantic_types column exists with type JSON and no default (NULL)
    assert "semantic_types" in columns
    assert columns["semantic_types"]["type"] == "JSON"
    assert columns["semantic_types"]["default"] is None

    # And supported_media_types column exists with type JSON and no default (NULL)
    assert "supported_media_types" in columns
    assert columns["supported_media_types"]["type"] == "JSON"
    assert columns["supported_media_types"]["default"] is None


def test_ac006_registered_plugins_idempotent_in_system_sqlite(tmp_path):
    """AC-006: TenantStorageManager.initialize() is idempotent on an existing system.sqlite with registered_plugins data."""
    base = str(tmp_path / "mind")

    # Given a system.sqlite pre-created with a registered_plugins row
    os.makedirs(base, exist_ok=True)
    system_db = os.path.join(base, "system.sqlite")
    with sqlite3.connect(system_db) as conn:
        conn.execute("""
            CREATE TABLE registered_plugins (
                plugin_name TEXT PRIMARY KEY,
                plugin_type TEXT NOT NULL,
                module_path TEXT NOT NULL,
                config JSON,
                event_filter JSON,
                semantic_types JSON,
                supported_media_types JSON,
                enabled INTEGER DEFAULT 1,
                registered_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE tenants (
                tenant_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                metadata JSON
            )
        """)
        conn.execute(
            "INSERT INTO registered_plugins (plugin_name, plugin_type, module_path) VALUES (?, ?, ?)",
            ("my_plugin", "tool_provider", "my.module.Plugin"),
        )

    # When TenantStorageManager.initialize() is called on the existing DB
    mgr = TenantStorageManager(base)
    mgr.initialize()

    # Then the pre-existing row is still intact
    with sqlite3.connect(system_db) as conn:
        cursor = conn.execute(
            "SELECT plugin_name, plugin_type, module_path, semantic_types, supported_media_types "
            "FROM registered_plugins"
        )
        rows = cursor.fetchall()

    assert len(rows) == 1
    plugin_name, plugin_type, module_path, semantic_types, supported_media_types = rows[0]
    assert plugin_name == "my_plugin"
    assert plugin_type == "tool_provider"
    assert module_path == "my.module.Plugin"
    assert semantic_types is None
    assert supported_media_types is None

    mgr.close()
