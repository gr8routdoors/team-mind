"""
SPEC-011 / STORY-002: Save Parent Storage Method
"""

import json
import pytest
from team_mind_mcp.storage import StorageAdapter


@pytest.fixture
def adapter(tmp_path):
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    yield storage
    storage.close()


def test_save_parent_inserts_row_and_returns_int_id(adapter):
    """
    AC-001: save_parent(uri, plugin, record_type) inserts a row into documents
    and returns the integer doc ID.
    """
    # Given an initialized StorageAdapter
    # When save_parent is called with required fields
    doc_id = adapter.save_parent(
        uri="file:///docs/spec.md",
        plugin="markdown",
        record_type="document",
    )

    # Then an integer ID is returned
    assert isinstance(doc_id, int)
    assert doc_id > 0

    # And a row exists in documents
    row = adapter._conn.execute(
        "SELECT id, uri, plugin, record_type FROM documents WHERE id = ?",
        (doc_id,),
    ).fetchone()
    assert row is not None
    assert row[1] == "file:///docs/spec.md"
    assert row[2] == "markdown"
    assert row[3] == "document"


def test_save_parent_returned_id_matches_inserted_row(adapter):
    """
    AC-002: The returned ID matches the row inserted (verify by looking up by ID).
    """
    # Given an initialized StorageAdapter
    # When two parent documents are saved
    id_a = adapter.save_parent(
        uri="file:///docs/a.md", plugin="markdown", record_type="document"
    )
    id_b = adapter.save_parent(
        uri="file:///docs/b.md", plugin="markdown", record_type="document"
    )

    # Then each returned ID resolves to its own row
    row_a = adapter._conn.execute(
        "SELECT uri FROM documents WHERE id = ?", (id_a,)
    ).fetchone()
    row_b = adapter._conn.execute(
        "SELECT uri FROM documents WHERE id = ?", (id_b,)
    ).fetchone()

    assert row_a[0] == "file:///docs/a.md"
    assert row_b[0] == "file:///docs/b.md"
    assert id_a != id_b


def test_save_parent_has_no_vec_documents_entry(adapter):
    """
    AC-003: The parent row has NO corresponding entry in vec_documents.
    """
    # Given an initialized StorageAdapter
    # When save_parent is called
    doc_id = adapter.save_parent(
        uri="file:///docs/spec.md",
        plugin="markdown",
        record_type="document",
    )

    # Then no entry exists in vec_documents for the returned ID
    row = adapter._conn.execute(
        "SELECT id FROM vec_documents WHERE id = ?", (doc_id,)
    ).fetchone()
    assert row is None


def test_save_parent_has_no_doc_weights_entry(adapter):
    """
    AC-004: The parent row has NO corresponding entry in doc_weights.
    """
    # Given an initialized StorageAdapter
    # When save_parent is called
    doc_id = adapter.save_parent(
        uri="file:///docs/spec.md",
        plugin="markdown",
        record_type="document",
    )

    # Then no entry exists in doc_weights for the returned ID
    row = adapter._conn.execute(
        "SELECT doc_id FROM doc_weights WHERE doc_id = ?", (doc_id,)
    ).fetchone()
    assert row is None


def test_save_parent_optional_fields_stored_when_provided(adapter):
    """
    AC-005 (provided): Optional fields are stored on the row when provided.
    """
    # Given an initialized StorageAdapter
    # When save_parent is called with all optional fields
    doc_id = adapter.save_parent(
        uri="file:///docs/spec.md",
        plugin="markdown",
        record_type="document",
        metadata={"author": "alice", "version": 2},
        content_hash="abc123",
        plugin_version="1.2.3",
        semantic_type="article",
        media_type="text/markdown",
    )

    # Then the row has the provided values
    row = adapter._conn.execute(
        "SELECT metadata, content_hash, plugin_version, semantic_type, media_type FROM documents WHERE id = ?",
        (doc_id,),
    ).fetchone()

    assert json.loads(row[0]) == {"author": "alice", "version": 2}
    assert row[1] == "abc123"
    assert row[2] == "1.2.3"
    assert row[3] == "article"
    assert row[4] == "text/markdown"


def test_save_parent_optional_fields_use_defaults_when_omitted(adapter):
    """
    AC-005 (omitted): When optional fields are omitted, sensible defaults are used.
    """
    # Given an initialized StorageAdapter
    # When save_parent is called with only required fields
    doc_id = adapter.save_parent(
        uri="file:///docs/spec.md",
        plugin="markdown",
        record_type="document",
    )

    # Then defaults are stored: metadata=None, plugin_version="0.0.0",
    # semantic_type="", media_type=""
    row = adapter._conn.execute(
        "SELECT metadata, content_hash, plugin_version, semantic_type, media_type FROM documents WHERE id = ?",
        (doc_id,),
    ).fetchone()

    assert row[0] is None  # metadata defaults to None
    assert row[1] is None  # content_hash defaults to None
    assert row[2] == "0.0.0"  # plugin_version default
    assert row[3] == ""  # semantic_type default
    assert row[4] == ""  # media_type default


def test_save_parent_row_has_null_parent_id(adapter):
    """
    AC-006: The inserted row has parent_id = NULL (it is itself a root, not a child).
    """
    # Given an initialized StorageAdapter
    # When save_parent is called
    doc_id = adapter.save_parent(
        uri="file:///docs/spec.md",
        plugin="markdown",
        record_type="document",
    )

    # Then the row's parent_id is NULL
    row = adapter._conn.execute(
        "SELECT parent_id FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()

    assert row[0] is None
