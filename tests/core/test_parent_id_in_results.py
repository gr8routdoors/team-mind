"""
SPEC-011 / STORY-004: Parent ID in Search Results

Verifies that both retrieve_by_vector_similarity and retrieve_by_weight
include a parent_id key in result dicts, with correct semantics:
- None for standalone documents (no parent)
- integer parent ID for segment documents (with a parent)
"""

import pytest
from team_mind_mcp.storage import StorageAdapter


DUMMY_VECTOR = [0.1] * 768
DIFFERENT_VECTOR = [0.2] * 768


@pytest.fixture
def adapter(tmp_path):
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    yield storage
    storage.close()


# --- retrieve_by_vector_similarity ---


def test_ac001_vector_similarity_standalone_has_parent_id_none(adapter):
    """
    AC-001: retrieve_by_vector_similarity result dict includes parent_id key.
    For a standalone document (no parent), value is None.
    """
    # Given a standalone document with no parent
    adapter.save_payload(
        uri="file:///docs/standalone.md",
        metadata={"title": "standalone"},
        vector=DUMMY_VECTOR,
        plugin="markdown",
        record_type="chunk",
    )

    # When retrieving by vector similarity
    results = adapter.retrieve_by_vector_similarity(target_vector=DUMMY_VECTOR, limit=5)

    # Then result includes parent_id key with value None
    assert len(results) == 1
    result = results[0]
    assert "parent_id" in result
    assert result["parent_id"] is None


def test_ac001_vector_similarity_segment_has_correct_parent_id(adapter):
    """
    AC-001: retrieve_by_vector_similarity result dict includes parent_id key.
    For a segment document (with a parent), value is the parent's integer ID.
    """
    # Given a parent document and a segment that references it
    parent_id = adapter.save_parent(
        uri="file:///docs/spec.md",
        plugin="markdown",
        record_type="document",
    )
    child_id = adapter.save_payload(
        uri="file:///docs/spec.md#chunk1",
        metadata={"title": "chunk 1"},
        vector=DUMMY_VECTOR,
        plugin="markdown",
        record_type="chunk",
        parent_id=parent_id,
    )

    # When retrieving by vector similarity
    results = adapter.retrieve_by_vector_similarity(target_vector=DUMMY_VECTOR, limit=5)

    # Then result includes parent_id equal to the parent's ID
    assert len(results) == 1
    result = results[0]
    assert result["id"] == child_id
    assert "parent_id" in result
    assert result["parent_id"] == parent_id
    assert isinstance(result["parent_id"], int)


def test_ac001_vector_similarity_mixed_docs_correct_parent_ids(adapter):
    """
    AC-001: When both standalone and segment documents exist, each result
    carries the correct parent_id value.
    """
    # Given a parent document, a segment, and a standalone document
    parent_id = adapter.save_parent(
        uri="file:///docs/big.md",
        plugin="markdown",
        record_type="document",
    )
    segment_id = adapter.save_payload(
        uri="file:///docs/big.md#s1",
        metadata={"title": "segment"},
        vector=DUMMY_VECTOR,
        plugin="markdown",
        record_type="chunk",
        parent_id=parent_id,
    )
    standalone_id = adapter.save_payload(
        uri="file:///docs/small.md",
        metadata={"title": "standalone"},
        vector=DIFFERENT_VECTOR,
        plugin="markdown",
        record_type="chunk",
    )

    # When retrieving both
    results = adapter.retrieve_by_vector_similarity(target_vector=DUMMY_VECTOR, limit=5)

    # Then each result has the correct parent_id
    result_by_id = {r["id"]: r for r in results}
    assert result_by_id[segment_id]["parent_id"] == parent_id
    assert result_by_id[standalone_id]["parent_id"] is None


# --- retrieve_by_weight ---


def test_ac002_weight_standalone_has_parent_id_none(adapter):
    """
    AC-002: retrieve_by_weight result dict includes parent_id key.
    For a standalone document (no parent), value is None.
    """
    # Given a standalone document with a weight entry
    adapter.save_payload(
        uri="file:///docs/standalone.md",
        metadata={"title": "standalone"},
        vector=DUMMY_VECTOR,
        plugin="markdown",
        record_type="chunk",
        initial_score=1.0,
    )

    # When retrieving by weight
    results = adapter.retrieve_by_weight(limit=5)

    # Then result includes parent_id key with value None
    assert len(results) == 1
    result = results[0]
    assert "parent_id" in result
    assert result["parent_id"] is None


def test_ac002_weight_segment_has_correct_parent_id(adapter):
    """
    AC-002: retrieve_by_weight result dict includes parent_id key.
    For a segment document (with a parent), value is the parent's integer ID.
    """
    # Given a parent document and a segment that references it
    parent_id = adapter.save_parent(
        uri="file:///docs/spec.md",
        plugin="markdown",
        record_type="document",
    )
    child_id = adapter.save_payload(
        uri="file:///docs/spec.md#chunk1",
        metadata={"title": "chunk 1"},
        vector=DUMMY_VECTOR,
        plugin="markdown",
        record_type="chunk",
        parent_id=parent_id,
        initial_score=2.0,
    )

    # When retrieving by weight
    results = adapter.retrieve_by_weight(limit=5)

    # Then the segment result carries the correct parent_id
    result_by_id = {r["id"]: r for r in results}
    assert child_id in result_by_id
    segment_result = result_by_id[child_id]
    assert "parent_id" in segment_result
    assert segment_result["parent_id"] == parent_id
    assert isinstance(segment_result["parent_id"], int)


def test_ac002_weight_mixed_docs_correct_parent_ids(adapter):
    """
    AC-002: When both standalone and segment documents exist, each result
    carries the correct parent_id value.
    """
    # Given a parent document, a segment, and a standalone document
    parent_id = adapter.save_parent(
        uri="file:///docs/big.md",
        plugin="markdown",
        record_type="document",
    )
    segment_id = adapter.save_payload(
        uri="file:///docs/big.md#s1",
        metadata={"title": "segment"},
        vector=DUMMY_VECTOR,
        plugin="markdown",
        record_type="chunk",
        parent_id=parent_id,
        initial_score=1.0,
    )
    standalone_id = adapter.save_payload(
        uri="file:///docs/small.md",
        metadata={"title": "standalone"},
        vector=DIFFERENT_VECTOR,
        plugin="markdown",
        record_type="chunk",
        initial_score=1.0,
    )

    # When retrieving by weight
    results = adapter.retrieve_by_weight(limit=5)

    # Then each result has the correct parent_id
    result_by_id = {r["id"]: r for r in results}
    assert result_by_id[segment_id]["parent_id"] == parent_id
    assert result_by_id[standalone_id]["parent_id"] is None


# --- AC-003: parent_id appended at END (index integrity check) ---


def test_ac003_vector_similarity_existing_fields_still_correct(adapter):
    """
    AC-003 / AC-004: Adding parent_id at the end must not shift existing row
    indices. All existing fields must still map to correct values.
    """
    # Given a document with known metadata and a weight entry
    doc_id = adapter.save_payload(
        uri="file:///docs/doc.md",
        metadata={"title": "test doc"},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="chunk",
        initial_score=3.0,
    )

    # When retrieving by vector similarity
    results = adapter.retrieve_by_vector_similarity(target_vector=DUMMY_VECTOR, limit=5)

    # Then all existing fields are still correct (no index corruption)
    assert len(results) == 1
    result = results[0]
    assert result["id"] == doc_id
    assert result["uri"] == "file:///docs/doc.md"
    assert result["plugin"] == "test_plugin"
    assert result["record_type"] == "chunk"
    assert result["metadata"] == {"title": "test doc"}
    assert isinstance(result["score"], float)
    assert result["usage_score"] == pytest.approx(3.0)
    assert isinstance(result["final_rank"], float)
    assert "parent_id" in result


def test_ac003_weight_existing_fields_still_correct(adapter):
    """
    AC-003 / AC-004: Adding parent_id at the end must not shift existing row
    indices for retrieve_by_weight. All existing fields must still be correct.
    """
    # Given a document with known metadata and a weight entry
    doc_id = adapter.save_payload(
        uri="file:///docs/doc.md",
        metadata={"title": "test doc"},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="chunk",
        initial_score=2.5,
    )

    # When retrieving by weight
    results = adapter.retrieve_by_weight(limit=5)

    # Then all existing fields are still correct (no index corruption)
    assert len(results) == 1
    result = results[0]
    assert result["id"] == doc_id
    assert result["uri"] == "file:///docs/doc.md"
    assert result["plugin"] == "test_plugin"
    assert result["record_type"] == "chunk"
    assert result["metadata"] == {"title": "test doc"}
    assert result["usage_score"] == pytest.approx(2.5)
    assert isinstance(result["weight_rank"], float)
    assert "parent_id" in result


# --- AC-004: parent documents do not appear in results ---


def test_ac004_parent_document_weight_result_has_parent_id_none(adapter):
    """
    AC-004: A parent document (created via save_parent) has parent_id=NULL in
    the documents table, so its result dict should have parent_id=None.
    retrieve_by_weight uses a LEFT JOIN so parent docs without weight rows may
    still appear — but when they do, parent_id must be None (they have no parent
    themselves).
    """
    # Given only a parent document (no segment)
    parent_doc_id = adapter.save_parent(
        uri="file:///docs/parent.md",
        plugin="markdown",
        record_type="document",
    )

    # When retrieving by weight
    results = adapter.retrieve_by_weight(limit=5)

    # Then if the parent document appears, its own parent_id is None
    result_by_id = {r["id"]: r for r in results}
    if parent_doc_id in result_by_id:
        assert result_by_id[parent_doc_id]["parent_id"] is None


def test_ac004_parent_document_does_not_appear_in_vector_results(adapter):
    """
    AC-004: Parent documents have no vec_documents entry, so they never appear
    in retrieve_by_vector_similarity results.
    """
    # Given only a parent document (no segment)
    adapter.save_parent(
        uri="file:///docs/parent.md",
        plugin="markdown",
        record_type="document",
    )

    # When retrieving by vector similarity
    results = adapter.retrieve_by_vector_similarity(target_vector=DUMMY_VECTOR, limit=5)

    # Then no results are returned (parent has no vector)
    assert results == []
