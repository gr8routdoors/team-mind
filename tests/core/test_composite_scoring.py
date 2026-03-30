"""
SPEC-004 / STORY-005: Composite Scoring in Retrieval
SPEC-004 / STORY-006: Tombstone Support
"""

import pytest
from team_mind_mcp.storage import StorageAdapter


@pytest.fixture
def weighted_storage(tmp_path):
    """Storage with documents at varying weights."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # All docs get similar vectors but different weights
    base_vec = [0.5] * 768

    # Doc 1: no weight (default 0)
    d1 = adapter.save_payload("uri1", {}, base_vec, plugin="p", record_type="t")

    # Doc 2: high weight
    d2 = adapter.save_payload("uri2", {}, base_vec, plugin="p", record_type="t")
    adapter.update_weight(d2, signal=5)

    # Doc 3: negative weight
    d3 = adapter.save_payload("uri3", {}, base_vec, plugin="p", record_type="t")
    adapter.update_weight(d3, signal=-3)

    # Doc 4: tombstoned
    d4 = adapter.save_payload("uri4", {}, base_vec, plugin="p", record_type="t")
    adapter.update_weight(d4, signal=0, tombstone=True)

    # Doc 5: different plugin for filter testing
    d5 = adapter.save_payload("uri5", {}, base_vec, plugin="other", record_type="t2")
    adapter.update_weight(d5, signal=4)

    yield adapter, {"d1": d1, "d2": d2, "d3": d3, "d4": d4, "d5": d5}
    adapter.close()


def test_weighted_results_differ_from_unweighted(weighted_storage):
    """
    STORY-005 / AC-001: Weighted Results Differ from Unweighted
    """
    adapter, ids = weighted_storage
    query_vec = [0.5] * 768

    results = adapter.retrieve_by_vector_similarity(query_vec, limit=10)

    # Doc with high weight (d2) should rank better than neutral (d1)
    result_ids = [r["id"] for r in results]
    d2_idx = result_ids.index(ids["d2"])
    d1_idx = result_ids.index(ids["d1"])
    assert d2_idx < d1_idx, "Higher-weighted doc should rank higher"


def test_no_weights_equals_baseline(tmp_path):
    """
    STORY-005 / AC-002: No Weights Equals Baseline
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    v1 = [1.0] + [0.0] * 767
    v2 = [0.0, 1.0] + [0.0] * 766

    d1 = adapter.save_payload("uri1", {}, v1, plugin="p", record_type="t")
    d2 = adapter.save_payload("uri2", {}, v2, plugin="p", record_type="t")

    # No feedback given — all usage_score=0, no decay
    results = adapter.retrieve_by_vector_similarity(v1, limit=2)

    # Results should be ordered by pure vector distance
    assert results[0]["id"] == d1  # closest to v1
    assert results[1]["id"] == d2
    adapter.close()


def test_decay_reduces_effective_score(tmp_path):
    """
    STORY-005 / AC-003: Decay Reduces Effective Score Over Time
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    vec = [0.5] * 768

    # Doc with decay, created "30 days ago"
    d1 = adapter.save_payload(
        "uri1", {}, vec, plugin="p", record_type="t", decay_half_life_days=30
    )
    adapter.update_weight(d1, signal=5)

    # Manually set created_at to 30 days ago
    with adapter._conn:
        adapter._conn.execute(
            "UPDATE doc_weights SET created_at = datetime('now', '-30 days') WHERE doc_id = ?",
            (d1,),
        )

    # Doc without decay, same weight
    d2 = adapter.save_payload("uri2", {}, vec, plugin="p", record_type="t")
    adapter.update_weight(d2, signal=5)

    results = adapter.retrieve_by_vector_similarity(vec, limit=2)

    # d2 (no decay, full score) should rank above d1 (decayed score)
    result_ids = [r["id"] for r in results]
    assert result_ids[0] == d2, "Non-decayed doc should rank higher"
    adapter.close()


def test_no_decay_means_full_score(tmp_path):
    """
    STORY-005 / AC-004: No Decay Means Full Score
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    vec = [0.5] * 768

    d1 = adapter.save_payload("uri1", {}, vec, plugin="p", record_type="t")
    adapter.update_weight(d1, signal=5)

    # Set created_at to 365 days ago — but no decay configured
    with adapter._conn:
        adapter._conn.execute(
            "UPDATE doc_weights SET created_at = datetime('now', '-365 days') WHERE doc_id = ?",
            (d1,),
        )

    results = adapter.retrieve_by_vector_similarity(vec, limit=1)

    # Should still have full weight effect (usage_score=5, no decay)
    assert results[0]["id"] == d1
    assert results[0]["usage_score"] == 5.0
    adapter.close()


def test_filters_work_with_composite_scoring(weighted_storage):
    """
    STORY-005 / AC-005: Plugin and Doctype Filters Still Work
    """
    adapter, ids = weighted_storage
    query_vec = [0.5] * 768

    results = adapter.retrieve_by_vector_similarity(
        query_vec, limit=10, plugins=["p"], record_types=["t"]
    )

    # Only plugin "p", doctype "t" — excludes d5 (plugin="other")
    result_ids = [r["id"] for r in results]
    assert ids["d5"] not in result_ids
    assert ids["d4"] not in result_ids  # tombstoned


# STORY-006: Tombstone Support


def test_tombstoned_excluded_from_search(weighted_storage):
    """
    STORY-006 / AC-001: Tombstoned Excluded from Search
    """
    adapter, ids = weighted_storage
    query_vec = [0.5] * 768

    results = adapter.retrieve_by_vector_similarity(query_vec, limit=10)

    result_ids = [r["id"] for r in results]
    assert ids["d4"] not in result_ids


@pytest.mark.asyncio
async def test_tombstone_via_feedback_tool(tmp_path):
    """
    STORY-006 / AC-002: Tombstone via Feedback Tool
    """
    from team_mind_mcp.feedback import FeedbackPlugin
    from team_mind_mcp.tenant_manager import TenantStorageManager
    import json

    mgr = TenantStorageManager(str(tmp_path / "mind"))
    mgr.initialize()
    adapter = mgr.get_adapter("default")

    doc_id = adapter.save_payload("uri", {}, [0.1] * 768, plugin="p", record_type="t")
    plugin = FeedbackPlugin(mgr)

    response = await plugin.call_tool(
        "provide_feedback", {"doc_id": doc_id, "signal": 0, "tombstone": True}
    )
    result = json.loads(response[0].text)

    assert result["tombstoned"] is True

    # Verify excluded from search
    results = adapter.retrieve_by_vector_similarity([0.1] * 768, limit=10)
    assert all(r["id"] != doc_id for r in results)
    mgr.close()


@pytest.mark.asyncio
async def test_un_tombstone_restores_document(tmp_path):
    """
    STORY-006 / AC-003: Un-Tombstone Restores Document
    """
    from team_mind_mcp.feedback import FeedbackPlugin
    from team_mind_mcp.tenant_manager import TenantStorageManager
    import json

    mgr = TenantStorageManager(str(tmp_path / "mind2"))
    mgr.initialize()
    adapter = mgr.get_adapter("default")

    doc_id = adapter.save_payload("uri", {}, [0.1] * 768, plugin="p", record_type="t")
    plugin = FeedbackPlugin(mgr)

    # Tombstone
    await plugin.call_tool(
        "provide_feedback", {"doc_id": doc_id, "signal": 0, "tombstone": True}
    )

    # Un-tombstone
    response = await plugin.call_tool(
        "provide_feedback", {"doc_id": doc_id, "signal": 0, "tombstone": False}
    )
    result = json.loads(response[0].text)
    assert result["tombstoned"] is False

    # Verify it reappears
    results = adapter.retrieve_by_vector_similarity([0.1] * 768, limit=10)
    assert any(r["id"] == doc_id for r in results)
    mgr.close()


def test_tombstoned_row_still_in_database(weighted_storage):
    """
    STORY-006 / AC-004: Tombstoned Row Still in Database
    """
    adapter, ids = weighted_storage

    # Verify both rows still exist
    with adapter._conn:
        doc_row = adapter._conn.execute(
            "SELECT id FROM documents WHERE id = ?", (ids["d4"],)
        ).fetchone()
        weight_row = adapter._conn.execute(
            "SELECT doc_id FROM doc_weights WHERE doc_id = ?", (ids["d4"],)
        ).fetchone()

    assert doc_row is not None
    assert weight_row is not None
