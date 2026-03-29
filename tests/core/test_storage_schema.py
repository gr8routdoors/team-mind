"""
SPEC-002 / STORY-002: Storage Schema Evolution
"""

import sqlite3
import pytest
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


def test_save_payload_requires_plugin_and_doctype(tmp_path):
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


def test_saved_record_contains_plugin_and_doctype(tmp_path):
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
