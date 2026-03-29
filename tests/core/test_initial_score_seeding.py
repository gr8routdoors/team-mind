"""
SPEC-007 / STORY-003: Initial Score on save_payload

Tests that save_payload accepts an optional initial_score parameter and seeds
usage_score in doc_weights to that value, while leaving signal_count at 0.
"""

import pytest
from team_mind_mcp.storage import StorageAdapter


@pytest.fixture
def storage(tmp_path):
    """In-memory-style storage using a temp SQLite db."""
    db_path = tmp_path / "test_initial_score.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()
    yield adapter
    adapter.close()


def _get_doc_weights(adapter: StorageAdapter, doc_id: int) -> dict:
    """Helper to fetch raw doc_weights row for a given doc_id."""
    row = adapter._conn.execute(
        "SELECT usage_score, signal_count FROM doc_weights WHERE doc_id = ?",
        (doc_id,),
    ).fetchone()
    return {"usage_score": row[0], "signal_count": row[1]}


BASE_VEC = [0.1] * 768


# AC-001: Default Initial Score Is Zero
def test_default_initial_score_is_zero(storage):
    """
    AC-001: Default Initial Score Is Zero

    Given save_payload called without initial_score
    When the doc_weights row is inspected
    Then usage_score is 0.0
    """
    # Given
    # When
    doc_id = storage.save_payload(
        "uri://doc1", {}, BASE_VEC, plugin="p", record_type="t"
    )

    # Then
    weights = _get_doc_weights(storage, doc_id)
    assert weights["usage_score"] == 0.0, (
        f"Expected usage_score=0.0, got {weights['usage_score']}"
    )


# AC-002: Custom Initial Score Seeds usage_score
def test_custom_initial_score_seeds_usage_score(storage):
    """
    AC-002: Custom Initial Score Seeds usage_score

    Given save_payload called with initial_score=0.8
    When the doc_weights row is inspected
    Then usage_score is 0.8
    """
    # Given / When
    doc_id = storage.save_payload(
        "uri://doc2", {}, BASE_VEC, plugin="p", record_type="t", initial_score=0.8
    )

    # Then
    weights = _get_doc_weights(storage, doc_id)
    assert weights["usage_score"] == pytest.approx(0.8), (
        f"Expected usage_score=0.8, got {weights['usage_score']}"
    )


# AC-003: Signal Count Stays Zero
def test_signal_count_stays_zero_with_initial_score(storage):
    """
    AC-003: Signal Count Stays Zero

    Given save_payload called with initial_score=0.8
    When the doc_weights row is inspected
    Then signal_count is 0 (initial score is not a feedback signal)
    """
    # Given / When
    doc_id = storage.save_payload(
        "uri://doc3", {}, BASE_VEC, plugin="p", record_type="t", initial_score=0.8
    )

    # Then
    weights = _get_doc_weights(storage, doc_id)
    assert weights["signal_count"] == 0, (
        f"Expected signal_count=0, got {weights['signal_count']}"
    )


# AC-004: Higher Initial Score Ranks Higher
def test_higher_initial_score_ranks_higher(storage):
    """
    AC-004: Higher Initial Score Ranks Higher

    Given two documents with identical vectors, one with initial_score=0.9 and one with initial_score=0.1
    When retrieve_by_vector_similarity is called
    Then the document with initial_score=0.9 ranks higher
    """
    # Given — identical vectors, different initial scores
    identical_vec = [0.5] * 768

    doc_low = storage.save_payload(
        "uri://low", {}, identical_vec, plugin="p", record_type="t", initial_score=0.1
    )
    doc_high = storage.save_payload(
        "uri://high", {}, identical_vec, plugin="p", record_type="t", initial_score=0.9
    )

    # When
    results = storage.retrieve_by_vector_similarity(identical_vec, limit=10)

    # Then
    result_ids = [r["id"] for r in results]
    assert doc_high in result_ids, "High-score document not returned"
    assert doc_low in result_ids, "Low-score document not returned"

    high_idx = result_ids.index(doc_high)
    low_idx = result_ids.index(doc_low)
    assert high_idx < low_idx, (
        f"Document with initial_score=0.9 (idx={high_idx}) should rank above "
        f"document with initial_score=0.1 (idx={low_idx})"
    )
