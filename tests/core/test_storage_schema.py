"""
SPEC-002 / STORY-002: Storage Schema Evolution
"""

import sqlite3
import pytest
import sqlite_vec
from team_mind_mcp.storage import StorageAdapter


def test_new_columns_on_fresh_database(tmp_path):
    """
    AC-001: New Columns on Fresh Database
    """
    db_path = tmp_path / "test.db"

    # Given no existing database file
    adapter = StorageAdapter(str(db_path))

    # When the StorageAdapter is initialized
    adapter.initialize()

    # Then the documents table includes plugin TEXT NOT NULL and record_type TEXT NOT NULL columns
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

    assert "plugin" in columns
    assert "record_type" in columns
    # And the table creation succeeds without error (implicit)
    adapter.close()


def test_indexes_created(tmp_path):
    """
    AC-002: Indexes Created
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Given a freshly initialized StorageAdapter
    # When the table schema is inspected
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        index_names = [row[0] for row in cursor.fetchall()]

    # Then indexes exist on plugin, record_type, and the composite (plugin, record_type)
    assert "idx_documents_plugin" in index_names
    assert "idx_documents_record_type" in index_names
    assert "idx_documents_plugin_record_type" in index_names
    adapter.close()


def test_save_payload_requires_plugin_and_record_type(tmp_path):
    """
    AC-003: Save Payload Requires Plugin and record_type
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Given an initialized StorageAdapter
    # When save_payload is called without plugin or record_type arguments
    # Then a TypeError is raised (missing required arguments)
    with pytest.raises(TypeError):
        adapter.save_payload(
            uri="file:///tmp/test.md", metadata={"test": True}, vector=[0.0] * 768
        )
    adapter.close()


def test_saved_record_contains_plugin_and_record_type(tmp_path):
    """
    AC-004: Saved Record Contains Plugin and record_type
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Given an initialized StorageAdapter
    # When save_payload is called with plugin="test_plugin" and record_type="test_type"
    doc_id = adapter.save_payload(
        uri="file:///tmp/test.md",
        metadata={"key": "value"},
        vector=[0.1] * 768,
        plugin="test_plugin",
        record_type="test_type",
    )

    # Then the saved row in the documents table has the correct values
    with adapter._conn:
        cursor = adapter._conn.execute(
            "SELECT plugin, record_type FROM documents WHERE id = ?", (doc_id,)
        )
        row = cursor.fetchone()

    assert row[0] == "test_plugin"
    assert row[1] == "test_type"
    adapter.close()


# --- SPEC-011 STORY-001: parent_id schema and index ---


def test_parent_id_column_on_fresh_database(tmp_path):
    """
    AC-001: Fresh initialize() creates documents table with parent_id INTEGER defaulting to NULL.
    """
    db_path = tmp_path / "test.db"

    # Given no existing database
    adapter = StorageAdapter(str(db_path))

    # When the StorageAdapter is initialized
    adapter.initialize()

    # Then the documents table has a parent_id column
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = {row[1]: row for row in cursor.fetchall()}

    assert "parent_id" in columns
    # Column type is INTEGER
    assert columns["parent_id"][2].upper() == "INTEGER"
    # Column is nullable (not NOT NULL)
    assert columns["parent_id"][3] == 0
    # Default value is NULL (dflt_value field is None)
    assert columns["parent_id"][4] is None

    adapter.close()


def test_parent_id_migration_on_existing_database(tmp_path):
    """
    AC-002: Existing database without parent_id gets the column added on initialize() — no error,
    column is nullable, existing rows keep parent_id = NULL.
    """
    db_path = tmp_path / "test.db"

    # Given an existing database without parent_id (simulating a pre-migration DB)
    with sqlite3.connect(str(db_path)) as conn:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uri TEXT NOT NULL,
                plugin TEXT NOT NULL DEFAULT '',
                record_type TEXT NOT NULL DEFAULT '',
                metadata JSON,
                content_hash TEXT,
                plugin_version TEXT DEFAULT '0.0.0',
                semantic_type TEXT NOT NULL DEFAULT '',
                media_type TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute(
            "INSERT INTO documents (uri, plugin, record_type) VALUES (?, ?, ?)",
            ("file:///existing.md", "test_plugin", "doc"),
        )
        conn.commit()

    # When initialize() is called on the existing database
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()  # must not raise

    # Then parent_id column exists and is nullable
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = {row[1]: row for row in cursor.fetchall()}

    assert "parent_id" in columns
    assert columns["parent_id"][3] == 0  # not NOT NULL

    # And existing rows have parent_id = NULL
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("SELECT parent_id FROM documents")
        rows = cursor.fetchall()

    assert len(rows) == 1
    assert rows[0][0] is None

    adapter.close()


def test_parent_id_index_exists_after_initialization(tmp_path):
    """
    AC-003: idx_documents_parent_id index exists on documents(parent_id) after initialization.
    """
    db_path = tmp_path / "test.db"

    # Given a freshly initialized StorageAdapter
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # When indexes are inspected
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        index_names = [row[0] for row in cursor.fetchall()]

    # Then the parent_id index is present
    assert "idx_documents_parent_id" in index_names

    adapter.close()
