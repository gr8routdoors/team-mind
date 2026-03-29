"""
Tests for score averaging, document updates, and document deletion.
"""

import json
import pytest
from team_mind_mcp.storage import StorageAdapter


# --- Score averaging (cumulative moving average) ---


def test_score_averages_toward_signal_value(tmp_path):
    """Repeated +5 signals converge the average to 5.0."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    doc_id = adapter.save_payload("uri", {}, [0.1] * 768, plugin="p", record_type="t")

    for _ in range(20):
        adapter.update_weight(doc_id, signal=5)

    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT usage_score, signal_count FROM doc_weights WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()

    assert row[1] == 20  # signal_count
    assert abs(row[0] - 5.0) < 0.01  # converges to 5.0
    adapter.close()


def test_negative_signals_average_correctly(tmp_path):
    """Repeated -5 signals converge the average to -5.0."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    doc_id = adapter.save_payload("uri", {}, [0.1] * 768, plugin="p", record_type="t")

    for _ in range(20):
        adapter.update_weight(doc_id, signal=-5)

    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT usage_score, signal_count FROM doc_weights WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()

    assert row[1] == 20
    assert abs(row[0] - (-5.0)) < 0.01  # converges to -5.0
    adapter.close()


def test_single_outlier_barely_moves_average(tmp_path):
    """100 signals of +5, then one -5 — average stays near 5.0."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    doc_id = adapter.save_payload("uri", {}, [0.1] * 768, plugin="p", record_type="t")

    for _ in range(100):
        adapter.update_weight(doc_id, signal=5)

    # One outlier
    result = adapter.update_weight(doc_id, signal=-5)

    # Average should be (5.0 * 100 + (-5)) / 101 ≈ 4.9
    assert result["signal_count"] == 101
    assert result["usage_score"] > 4.8
    assert result["usage_score"] < 5.0
    adapter.close()


def test_mixed_signals_average(tmp_path):
    """Mixed signals produce a reasonable average."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    doc_id = adapter.save_payload("uri", {}, [0.1] * 768, plugin="p", record_type="t")

    # 3 signals of +5, 2 signals of -3 → expected avg = (15 + -6) / 5 = 1.8
    for _ in range(3):
        adapter.update_weight(doc_id, signal=5)
    for _ in range(2):
        result = adapter.update_weight(doc_id, signal=-3)

    assert result["signal_count"] == 5
    assert abs(result["usage_score"] - 1.8) < 0.01
    adapter.close()


# --- update_payload ---


def test_update_payload_changes_metadata_and_vector(tmp_path):
    """update_payload updates metadata and vector in place."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    doc_id = adapter.save_payload(
        "uri", {"version": 1}, [0.1] * 768, plugin="p", record_type="t"
    )

    # Update
    adapter.update_payload(doc_id, {"version": 2, "new_field": True}, [0.9] * 768)

    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT metadata FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()

    meta = json.loads(row[0])
    assert meta["version"] == 2
    assert meta["new_field"] is True
    adapter.close()


def test_update_payload_preserves_weight(tmp_path):
    """update_payload does not reset the weight row."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    doc_id = adapter.save_payload("uri", {}, [0.1] * 768, plugin="p", record_type="t")
    adapter.update_weight(doc_id, signal=5)

    # Update content
    adapter.update_payload(doc_id, {"updated": True}, [0.9] * 768)

    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT usage_score FROM doc_weights WHERE doc_id = ?", (doc_id,)
        ).fetchone()

    assert row[0] == 5.0  # Weight preserved
    adapter.close()


def test_update_payload_preserves_uri_plugin_record_type(tmp_path):
    """update_payload does not change uri, plugin, or record_type."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    doc_id = adapter.save_payload(
        "file:///original.md",
        {"v": 1},
        [0.1] * 768,
        plugin="my_plugin",
        record_type="my_type",
    )
    adapter.update_payload(doc_id, {"v": 2}, [0.9] * 768)

    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT uri, plugin, record_type FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()

    assert row[0] == "file:///original.md"
    assert row[1] == "my_plugin"
    assert row[2] == "my_type"
    adapter.close()


def test_update_payload_nonexistent_doc_errors(tmp_path):
    """update_payload raises ValueError for unknown doc_id."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    with pytest.raises(ValueError, match="No document with id=99999"):
        adapter.update_payload(99999, {"x": 1}, [0.1] * 768)
    adapter.close()


# --- delete_by_uri ---


def test_delete_by_uri_removes_all_chunks(tmp_path):
    """delete_by_uri removes all documents, vectors, and weights for a URI."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Two chunks from the same URI
    d1 = adapter.save_payload(
        "file:///doc.md", {"chunk": 1}, [0.1] * 768, plugin="p", record_type="t"
    )
    d2 = adapter.save_payload(
        "file:///doc.md", {"chunk": 2}, [0.2] * 768, plugin="p", record_type="t"
    )
    # Different URI — should NOT be deleted
    d3 = adapter.save_payload(
        "file:///other.md", {"chunk": 1}, [0.3] * 768, plugin="p", record_type="t"
    )

    count = adapter.delete_by_uri("file:///doc.md", plugin="p", record_type="t")

    assert count == 2

    with adapter._conn:
        remaining = adapter._conn.execute("SELECT id FROM documents").fetchall()
        remaining_ids = [r[0] for r in remaining]

    assert d1 not in remaining_ids
    assert d2 not in remaining_ids
    assert d3 in remaining_ids
    adapter.close()


def test_delete_by_uri_cleans_up_weights_and_vectors(tmp_path):
    """delete_by_uri also removes weight and vector rows."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    d1 = adapter.save_payload(
        "file:///doc.md", {}, [0.1] * 768, plugin="p", record_type="t"
    )
    adapter.update_weight(d1, signal=5)  # Give it a weight

    adapter.delete_by_uri("file:///doc.md", plugin="p", record_type="t")

    with adapter._conn:
        weight_row = adapter._conn.execute(
            "SELECT doc_id FROM doc_weights WHERE doc_id = ?", (d1,)
        ).fetchone()
        vec_row = adapter._conn.execute(
            "SELECT id FROM vec_documents WHERE id = ?", (d1,)
        ).fetchone()

    assert weight_row is None
    assert vec_row is None
    adapter.close()


def test_delete_by_uri_scoped_to_plugin_and_record_type(tmp_path):
    """delete_by_uri only deletes matching plugin+record_type, not all docs with that URI."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Same URI, different plugins
    adapter.save_payload(
        "file:///doc.md", {}, [0.1] * 768, plugin="plugin_a", record_type="type_x"
    )
    d2 = adapter.save_payload(
        "file:///doc.md", {}, [0.2] * 768, plugin="plugin_b", record_type="type_y"
    )

    count = adapter.delete_by_uri(
        "file:///doc.md", plugin="plugin_a", record_type="type_x"
    )

    assert count == 1
    with adapter._conn:
        remaining = adapter._conn.execute("SELECT id FROM documents").fetchall()
    assert len(remaining) == 1
    assert remaining[0][0] == d2
    adapter.close()


def test_delete_by_uri_returns_zero_for_no_match(tmp_path):
    """delete_by_uri returns 0 when nothing matches."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    count = adapter.delete_by_uri("file:///nonexistent.md", plugin="p", record_type="t")
    assert count == 0
    adapter.close()


def test_updated_vector_searchable(tmp_path):
    """After update_payload, the new vector is used in similarity search."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Doc starts with vector pointing in one direction
    v_original = [1.0] + [0.0] * 767
    v_new = [0.0, 1.0] + [0.0] * 766
    v_query = [0.0, 1.0] + [0.0] * 766  # matches v_new

    doc_id = adapter.save_payload("uri", {}, v_original, plugin="p", record_type="t")

    # Before update: query for v_new direction
    results_before = adapter.retrieve_by_vector_similarity(v_query, limit=1)
    distance_before = results_before[0]["score"]

    # Update to v_new
    adapter.update_payload(doc_id, {}, v_new)

    results_after = adapter.retrieve_by_vector_similarity(v_query, limit=1)
    distance_after = results_after[0]["score"]

    # After update, distance should be 0 (exact match)
    assert distance_after < distance_before
    adapter.close()
