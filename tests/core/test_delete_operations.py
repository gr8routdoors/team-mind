"""
SPEC-011 / STORY-007: Delete Operations (Cascade + delete_by_id)
"""

import pytest
from team_mind_mcp.storage import StorageAdapter


VECTOR_DIM = 768


def make_vector(val: float = 0.1) -> list[float]:
    return [val] * VECTOR_DIM


@pytest.fixture
def adapter(tmp_path):
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    yield storage
    storage.close()


def _doc_exists(adapter: StorageAdapter, doc_id: int) -> bool:
    assert adapter._conn is not None
    row = adapter._conn.execute(
        "SELECT id FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    return row is not None


def _vec_exists(adapter: StorageAdapter, doc_id: int) -> bool:
    assert adapter._conn is not None
    row = adapter._conn.execute(
        "SELECT id FROM vec_documents WHERE id = ?", (doc_id,)
    ).fetchone()
    return row is not None


def _weight_exists(adapter: StorageAdapter, doc_id: int) -> bool:
    assert adapter._conn is not None
    row = adapter._conn.execute(
        "SELECT doc_id FROM doc_weights WHERE doc_id = ?", (doc_id,)
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# AC-001: delete_by_uri with a parent document cascades to children
# ---------------------------------------------------------------------------


def test_delete_by_uri_parent_cascades_to_children(adapter):
    """
    AC-001: delete_by_uri with a URI matching a parent document deletes the
    parent AND all its child segments (weights, vectors, document rows).
    Returns total count (parent + children).
    """
    # Given a parent document with two child segments
    parent_id = adapter.save_parent(
        uri="file:///docs/readme.md",
        plugin="markdown",
        record_type="document",
    )
    child1_id = adapter.save_payload(
        uri="file:///docs/readme.md",
        metadata={"chunk": 1},
        vector=make_vector(0.1),
        plugin="markdown",
        record_type="segment",
        parent_id=parent_id,
    )
    child2_id = adapter.save_payload(
        uri="file:///docs/readme.md",
        metadata={"chunk": 2},
        vector=make_vector(0.2),
        plugin="markdown",
        record_type="segment",
        parent_id=parent_id,
    )

    # When delete_by_uri is called with the parent's URI/plugin/record_type
    count = adapter.delete_by_uri(
        uri="file:///docs/readme.md",
        plugin="markdown",
        record_type="document",
    )

    # Then the total deleted count is 1 (parent) + 2 (children) = 3
    assert count == 3

    # And the parent row is gone
    assert not _doc_exists(adapter, parent_id)

    # And both children rows are gone
    assert not _doc_exists(adapter, child1_id)
    assert not _doc_exists(adapter, child2_id)

    # And children weights and vectors are gone
    assert not _weight_exists(adapter, child1_id)
    assert not _weight_exists(adapter, child2_id)
    assert not _vec_exists(adapter, child1_id)
    assert not _vec_exists(adapter, child2_id)


# ---------------------------------------------------------------------------
# AC-002: delete_by_uri with a URI matching a segment directly
# ---------------------------------------------------------------------------


def test_delete_by_uri_segment_deletes_only_that_segment(adapter):
    """
    AC-002: delete_by_uri with a URI matching a segment directly (no children
    of its own) deletes only that segment. Returns count of 1.
    """
    # Given a standalone segment (no parent_id, no children)
    seg_id = adapter.save_payload(
        uri="file:///docs/note.md#para1",
        metadata={"chunk": 1},
        vector=make_vector(0.1),
        plugin="markdown",
        record_type="segment",
    )

    # When delete_by_uri is called on that segment's URI
    count = adapter.delete_by_uri(
        uri="file:///docs/note.md#para1",
        plugin="markdown",
        record_type="segment",
    )

    # Then count is 1
    assert count == 1

    # And the segment row is gone
    assert not _doc_exists(adapter, seg_id)
    assert not _weight_exists(adapter, seg_id)
    assert not _vec_exists(adapter, seg_id)


# ---------------------------------------------------------------------------
# AC-003: delete_by_uri with a standalone document behaves as before
# ---------------------------------------------------------------------------


def test_delete_by_uri_standalone_document_deletes_just_that_document(adapter):
    """
    AC-003: delete_by_uri with a URI matching a standalone document behaves
    identically to before — deletes just that document. Returns count of 1.
    """
    # Given a standalone document (no parent_id, no children)
    doc_id = adapter.save_payload(
        uri="file:///docs/standalone.md",
        metadata={"title": "Standalone"},
        vector=make_vector(0.5),
        plugin="markdown",
        record_type="document",
    )

    # When delete_by_uri is called
    count = adapter.delete_by_uri(
        uri="file:///docs/standalone.md",
        plugin="markdown",
        record_type="document",
    )

    # Then count is 1
    assert count == 1

    # And the document is gone
    assert not _doc_exists(adapter, doc_id)
    assert not _weight_exists(adapter, doc_id)
    assert not _vec_exists(adapter, doc_id)


# ---------------------------------------------------------------------------
# AC-004: delete_by_id on a parent cascades to all children
# ---------------------------------------------------------------------------


def test_delete_by_id_parent_cascades_all_children(adapter):
    """
    AC-004: delete_by_id(doc_id) when called on a parent cascades: deletes all
    children's weights, vectors, and rows, then the parent. Returns total count.
    """
    # Given a parent with three children
    parent_id = adapter.save_parent(
        uri="file:///docs/guide.md",
        plugin="markdown",
        record_type="document",
    )
    child_ids = []
    for i in range(3):
        cid = adapter.save_payload(
            uri="file:///docs/guide.md",
            metadata={"chunk": i},
            vector=make_vector(i * 0.1),
            plugin="markdown",
            record_type="segment",
            parent_id=parent_id,
        )
        child_ids.append(cid)

    # When delete_by_id is called on the parent
    count = adapter.delete_by_id(parent_id)

    # Then total count = 1 parent + 3 children = 4
    assert count == 4

    # And parent is gone
    assert not _doc_exists(adapter, parent_id)

    # And all children are gone (docs, weights, vectors)
    for cid in child_ids:
        assert not _doc_exists(adapter, cid)
        assert not _weight_exists(adapter, cid)
        assert not _vec_exists(adapter, cid)


# ---------------------------------------------------------------------------
# AC-005: delete_by_id on a segment deletes only that segment
# ---------------------------------------------------------------------------


def test_delete_by_id_segment_deletes_only_that_segment(adapter):
    """
    AC-005: delete_by_id(doc_id) when called on a segment deletes only that
    segment. Parent and siblings are unaffected.
    """
    # Given a parent with two children
    parent_id = adapter.save_parent(
        uri="file:///docs/faq.md",
        plugin="markdown",
        record_type="document",
    )
    seg1_id = adapter.save_payload(
        uri="file:///docs/faq.md",
        metadata={"chunk": 1},
        vector=make_vector(0.1),
        plugin="markdown",
        record_type="segment",
        parent_id=parent_id,
    )
    seg2_id = adapter.save_payload(
        uri="file:///docs/faq.md",
        metadata={"chunk": 2},
        vector=make_vector(0.2),
        plugin="markdown",
        record_type="segment",
        parent_id=parent_id,
    )

    # When delete_by_id is called on seg1
    count = adapter.delete_by_id(seg1_id)

    # Then count is 1
    assert count == 1

    # And seg1 is gone
    assert not _doc_exists(adapter, seg1_id)
    assert not _weight_exists(adapter, seg1_id)
    assert not _vec_exists(adapter, seg1_id)

    # And parent is unaffected
    assert _doc_exists(adapter, parent_id)

    # And sibling seg2 is unaffected
    assert _doc_exists(adapter, seg2_id)
    assert _weight_exists(adapter, seg2_id)
    assert _vec_exists(adapter, seg2_id)


# ---------------------------------------------------------------------------
# AC-006: delete_by_id on a standalone document deletes just that document
# ---------------------------------------------------------------------------


def test_delete_by_id_standalone_deletes_just_that_document(adapter):
    """
    AC-006: delete_by_id(doc_id) when called on a standalone document deletes
    just that document.
    """
    # Given a standalone document (no parent, no children)
    doc_id = adapter.save_payload(
        uri="file:///docs/solo.md",
        metadata={"title": "Solo"},
        vector=make_vector(0.3),
        plugin="markdown",
        record_type="document",
    )

    # When delete_by_id is called
    count = adapter.delete_by_id(doc_id)

    # Then count is 1
    assert count == 1

    # And the document is gone
    assert not _doc_exists(adapter, doc_id)
    assert not _weight_exists(adapter, doc_id)
    assert not _vec_exists(adapter, doc_id)


# ---------------------------------------------------------------------------
# AC-007: delete_by_id returns total count of deleted documents
# ---------------------------------------------------------------------------


def test_delete_by_id_returns_correct_total_count(adapter):
    """
    AC-007: delete_by_id returns the total count of deleted documents
    (1 for segment/standalone, 1 + N children for parent).
    """
    # Given a parent with 5 children
    parent_id = adapter.save_parent(
        uri="file:///docs/big.md",
        plugin="markdown",
        record_type="document",
    )
    for i in range(5):
        adapter.save_payload(
            uri="file:///docs/big.md",
            metadata={"chunk": i},
            vector=make_vector(i * 0.05),
            plugin="markdown",
            record_type="segment",
            parent_id=parent_id,
        )

    # When delete_by_id is called on the parent
    count = adapter.delete_by_id(parent_id)

    # Then count is 6 (1 parent + 5 children)
    assert count == 6

    # Given a standalone document
    solo_id = adapter.save_payload(
        uri="file:///docs/solo2.md",
        metadata={},
        vector=make_vector(0.9),
        plugin="markdown",
        record_type="document",
    )

    # When delete_by_id is called on the standalone
    solo_count = adapter.delete_by_id(solo_id)

    # Then count is 1
    assert solo_count == 1


# ---------------------------------------------------------------------------
# AC-008: delete_by_id returns 0 when doc_id does not exist
# ---------------------------------------------------------------------------


def test_delete_by_id_returns_zero_for_nonexistent_doc(adapter):
    """
    AC-008: delete_by_id returns 0 and does nothing when doc_id does not exist.
    """
    # Given a doc_id that does not exist in the database
    nonexistent_id = 99999

    # When delete_by_id is called
    count = adapter.delete_by_id(nonexistent_id)

    # Then count is 0
    assert count == 0
