"""
SPEC-004 / STORY-002: Doc Weights Table & Ingestion Hook
SPEC-004 / STORY-004: Decay Policy on RecordTypeSpec
"""

import sqlite3
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.server import RecordTypeSpec


def test_weights_table_created_on_initialize(tmp_path):
    """
    STORY-002 / AC-001: Table Created on Initialize
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Then the doc_weights table exists with the expected columns
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("PRAGMA table_info(doc_weights)")
        columns = {row[1] for row in cursor.fetchall()}

    assert "doc_id" in columns
    assert "usage_score" in columns
    assert "last_accessed" in columns
    assert "created_at" in columns
    assert "tombstoned" in columns
    assert "decay_half_life_days" in columns
    adapter.close()


def test_weight_row_auto_created_on_save(tmp_path):
    """
    STORY-002 / AC-002: Weight Row Auto-Created on Save
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    doc_id = adapter.save_payload(
        uri="file:///test.md",
        metadata={"test": True},
        vector=[0.1] * 768,
        plugin="test_plugin",
        doctype="test_type",
    )

    # Then a corresponding row in doc_weights exists
    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT usage_score, tombstoned, created_at FROM doc_weights WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == 0.0  # usage_score default
    assert row[1] == 0  # tombstoned default
    assert row[2] is not None  # created_at set
    adapter.close()


def test_decay_half_life_copied_on_save(tmp_path):
    """
    STORY-002 / AC-003: Decay Half-Life Copied from Registry
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    doc_id = adapter.save_payload(
        uri="file:///test.md",
        metadata={},
        vector=[0.1] * 768,
        plugin="test_plugin",
        doctype="notes",
        decay_half_life_days=30.0,
    )

    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT decay_half_life_days FROM doc_weights WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()

    assert row[0] == 30.0
    adapter.close()


def test_no_decay_uses_null(tmp_path):
    """
    STORY-002 / AC-004: No Doctype Match Uses Null Decay
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    doc_id = adapter.save_payload(
        uri="file:///test.md",
        metadata={},
        vector=[0.1] * 768,
        plugin="test_plugin",
        doctype="unknown_type",
    )

    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT decay_half_life_days FROM doc_weights WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()

    assert row[0] is None
    adapter.close()


def test_existing_databases_get_migration(tmp_path):
    """
    STORY-002 / AC-005: Existing Databases Get Migration
    """
    db_path = tmp_path / "test.db"

    # Create a database with the old schema (no doc_weights)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uri TEXT NOT NULL,
            plugin TEXT NOT NULL DEFAULT '',
            doctype TEXT NOT NULL DEFAULT '',
            metadata JSON
        )
    """)
    conn.execute(
        "INSERT INTO documents (uri, plugin, doctype) VALUES ('old', 'p', 'd')"
    )
    conn.commit()
    conn.close()

    # When StorageAdapter.initialize() runs
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Then doc_weights table is created without error
    with sqlite3.connect(str(db_path)) as conn2:
        cursor = conn2.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='doc_weights'"
        )
        assert cursor.fetchone() is not None

    # And existing documents have no weight rows (lazy creation)
    with adapter._conn:
        count = adapter._conn.execute("SELECT COUNT(*) FROM doc_weights").fetchone()[0]
    assert count == 0
    adapter.close()


# STORY-004 tests


def test_doctype_spec_decay_defaults_none():
    """
    STORY-004 / AC-001: Field Exists and Defaults to None
    """
    spec = RecordTypeSpec(name="test", description="test")
    assert spec.decay_half_life_days is None


def test_doctype_spec_decay_declared():
    """
    STORY-004 / AC-002: Plugin Declares Decay
    """
    spec = RecordTypeSpec(
        name="notes", description="Meeting notes", decay_half_life_days=30
    )
    assert spec.decay_half_life_days == 30


def test_doctype_spec_backward_compatible():
    """
    STORY-004 / AC-003: Backward Compatible
    """
    # Existing plugins that don't specify decay_half_life_days
    spec = RecordTypeSpec(
        name="chunk",
        description="A text chunk",
        schema={"text": {"type": "string"}},
    )
    assert spec.decay_half_life_days is None
