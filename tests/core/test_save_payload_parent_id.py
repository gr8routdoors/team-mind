"""
SPEC-011 / STORY-003: Parent ID on Save Payload
"""

import pytest
from team_mind_mcp.storage import StorageAdapter


DUMMY_VECTOR = [0.1] * 768


@pytest.fixture
def adapter(tmp_path):
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    yield storage
    storage.close()


def test_ac001_save_payload_without_parent_id_behaves_as_before(adapter):
    """
    AC-001: When parent_id is omitted (default None), save_payload behaves
    identically to the current behavior.
    """
    # Given an initialized StorageAdapter
    # When save_payload is called without parent_id
    doc_id = adapter.save_payload(
        uri="file:///docs/chunk1.md",
        metadata={"title": "chunk 1"},
        vector=DUMMY_VECTOR,
        plugin="markdown",
        record_type="chunk",
    )

    # Then an integer ID is returned
    assert isinstance(doc_id, int)
    assert doc_id > 0

    # And the row exists with parent_id = NULL
    row = adapter._conn.execute(
        "SELECT id, parent_id FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    assert row is not None
    assert row[1] is None


def test_ac001_save_payload_with_explicit_none_behaves_as_before(adapter):
    """
    AC-001: When parent_id=None is passed explicitly, behavior is unchanged.
    """
    # Given an initialized StorageAdapter
    # When save_payload is called with parent_id=None explicitly
    doc_id = adapter.save_payload(
        uri="file:///docs/chunk2.md",
        metadata={"title": "chunk 2"},
        vector=DUMMY_VECTOR,
        plugin="markdown",
        record_type="chunk",
        parent_id=None,
    )

    # Then the row is inserted normally
    assert isinstance(doc_id, int)
    assert doc_id > 0

    row = adapter._conn.execute(
        "SELECT parent_id FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    assert row[0] is None


def test_ac002_save_payload_raises_value_error_when_parent_not_found(adapter):
    """
    AC-002: When parent_id is provided but no document with that ID exists,
    save_payload raises ValueError.
    """
    # Given an initialized StorageAdapter with no parent document
    nonexistent_parent_id = 9999

    # When save_payload is called with a parent_id that does not exist
    # Then a ValueError is raised
    with pytest.raises(ValueError):
        adapter.save_payload(
            uri="file:///docs/chunk.md",
            metadata={"title": "orphan chunk"},
            vector=DUMMY_VECTOR,
            plugin="markdown",
            record_type="chunk",
            parent_id=nonexistent_parent_id,
        )


def test_ac003_save_payload_stores_parent_id_when_parent_exists(adapter):
    """
    AC-003: When parent_id is provided and the parent document exists,
    the inserted row stores the parent_id value.
    """
    # Given a parent document created via save_parent
    parent_id = adapter.save_parent(
        uri="file:///docs/spec.md",
        plugin="markdown",
        record_type="document",
    )

    # When save_payload is called with the valid parent_id
    child_id = adapter.save_payload(
        uri="file:///docs/spec.md#chunk1",
        metadata={"title": "chunk 1"},
        vector=DUMMY_VECTOR,
        plugin="markdown",
        record_type="chunk",
        parent_id=parent_id,
    )

    # Then the inserted row has parent_id set to the parent document ID
    row = adapter._conn.execute(
        "SELECT parent_id FROM documents WHERE id = ?", (child_id,)
    ).fetchone()
    assert row is not None
    assert row[0] == parent_id


def test_ac004_save_payload_null_parent_id_when_none(adapter):
    """
    AC-004: When parent_id is None, the inserted row has parent_id = NULL
    (backward compatibility — existing behavior unchanged).
    """
    # Given an initialized StorageAdapter
    # When save_payload is called without parent_id
    doc_id = adapter.save_payload(
        uri="file:///docs/standalone.md",
        metadata={"title": "standalone"},
        vector=DUMMY_VECTOR,
        plugin="markdown",
        record_type="chunk",
    )

    # Then the inserted row has parent_id = NULL
    row = adapter._conn.execute(
        "SELECT parent_id FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    assert row is not None
    assert row[0] is None
