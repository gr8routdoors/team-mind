"""
STORY-002: SQLite Embedded Storage Engine
"""

import pytest
import sqlite3
from team_mind_mcp.storage import StorageAdapter


def test_sqlite_database_initialization(tmp_path):
    """
    AC-001: Database Initialization
    """
    db_path = tmp_path / "test.db"

    # Given a valid SQLite file path
    adapter = StorageAdapter(str(db_path))

    # When the StorageAdapter is initialized
    adapter.initialize()

    # Then it creates the necessary tables for documents, metadata, and vectors if they do not exist
    # And the connection pool is established
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        assert "documents" in tables

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' OR type='view';"
        )
        all_tables = [row[0] for row in cursor.fetchall()]
        assert "vec_documents" in all_tables

    adapter.close()


def test_sqlite_vector_extension_required(tmp_path, monkeypatch):
    """
    AC-002: Vector Extension Required
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))

    # Given an environment where sqlite-vec cannot be compiled or loaded
    # MOCK sqlite_vec.load to raise an ImportError
    import sqlite_vec

    def mock_load(conn):
        raise ImportError("sqlite-vec extension missing")

    monkeypatch.setattr(sqlite_vec, "load", mock_load)

    # When the StorageAdapter attempts to initialize
    with pytest.raises(RuntimeError) as exc_info:
        adapter.initialize()

    # Then it throws a clear initialization error stating the missing dependency
    assert "Missing dependency or failed to load sqlite-vec" in str(exc_info.value)
    # And gracefully exits before accepting connections
    assert adapter._conn is None


def test_sqlite_save_payload(tmp_path):
    """
    AC-003: Save Payload
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Given an active StorageAdapter
    # When a plugin attempts to insert a document with a 768-dimensional vector, an origin URI, and arbitrary JSON metadata
    test_vector = [0.1] * 768
    doc_id = adapter.save_payload(
        uri="file:///tmp/test.md",
        metadata={"author": "team-mind", "tags": ["test"]},
        vector=test_vector,
        plugin="test_plugin",
        record_type="test_type",
    )

    # Then the record is successfully committed to the database
    # And an internal document ID is returned
    assert doc_id > 0

    # Verify the document
    with adapter._conn:
        cursor = adapter._conn.execute(
            "SELECT uri, metadata FROM documents WHERE id = ?", (doc_id,)
        )
        row = cursor.fetchone()
        assert row[0] == "file:///tmp/test.md"
        assert "team-mind" in row[1]

    adapter.close()


def test_sqlite_retrieve_by_vector_similarity(tmp_path):
    """
    AC-004: Retrieve by Vector Similarity
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Given a populated vector table with known embeddings
    # Insert 3 test vectors
    v1 = [1.0] + [0.0] * 767  # Document 1: 1 at index 0
    v2 = [0.0, 1.0] + [0.0] * 766  # Document 2: 1 at index 1
    v3 = [-1.0] + [0.0] * 767  # Document 3: -1 at index 0 (furthest from v1)

    doc1 = adapter.save_payload("doc1", {"name": "doc1"}, v1, plugin="p", record_type="t")
    doc2 = adapter.save_payload("doc2", {"name": "doc2"}, v2, plugin="p", record_type="t")
    adapter.save_payload("doc3", {"name": "doc3"}, v3, plugin="p", record_type="t")

    # When a KNN semantic query is executed with a target vector and a limit=2
    # Search for v1
    results = adapter.retrieve_by_vector_similarity(target_vector=v1, limit=2)

    # Then exactly 2 (or fewer) results are returned
    assert len(results) == 2

    # And they are ordered descending by similarity score (ascending by distance)
    # The first result should be doc1 (distance 0.0)
    assert results[0]["id"] == doc1
    assert results[0]["uri"] == "doc1"

    # The second result should be doc2 (further than doc1, but closer than doc3)
    assert results[1]["id"] == doc2

    adapter.close()
