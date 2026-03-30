"""
SPEC-010 / STORY-004: Metadata Search Filters

Tests for metadata_filters parameter on:
  - retrieve_by_vector_similarity
  - retrieve_by_weight
"""

import pytest
from team_mind_mcp.storage import StorageAdapter


@pytest.fixture
def storage(tmp_path):
    """StorageAdapter with a set of documents having varying metadata."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    base_vec = [0.5] * 768

    # Doc 1: category=sports, league=nfl
    d1 = adapter.save_payload(
        "uri1",
        {"category": "sports", "league": "nfl"},
        base_vec,
        plugin="p",
        record_type="t",
        initial_score=1.0,
    )

    # Doc 2: category=sports, league=nba
    d2 = adapter.save_payload(
        "uri2",
        {"category": "sports", "league": "nba"},
        base_vec,
        plugin="p",
        record_type="t",
        initial_score=1.0,
    )

    # Doc 3: category=news, no league
    d3 = adapter.save_payload(
        "uri3",
        {"category": "news"},
        base_vec,
        plugin="p",
        record_type="t",
        initial_score=1.0,
    )

    # Doc 4: NULL metadata
    d4 = adapter.save_payload(
        "uri4",
        {},
        base_vec,
        plugin="p",
        record_type="t",
        initial_score=1.0,
    )
    # Force metadata to NULL in the database
    with adapter._conn:
        adapter._conn.execute(
            "UPDATE documents SET metadata = NULL WHERE id = ?", (d4,)
        )

    # Doc 5: category=sports, league=nfl — tombstoned
    d5 = adapter.save_payload(
        "uri5",
        {"category": "sports", "league": "nfl"},
        base_vec,
        plugin="p",
        record_type="t",
    )
    adapter.update_weight(d5, signal=0, tombstone=True)

    yield adapter, {"d1": d1, "d2": d2, "d3": d3, "d4": d4, "d5": d5}
    adapter.close()


# ---------------------------------------------------------------------------
# retrieve_by_vector_similarity — metadata_filters
# ---------------------------------------------------------------------------


class TestRetrieveByVectorSimilarityMetadataFilters:
    def test_no_filters_returns_all_non_tombstoned(self, storage):
        """No metadata_filters — existing behavior unchanged."""
        adapter, ids = storage
        results = adapter.retrieve_by_vector_similarity([0.5] * 768, limit=10)
        result_ids = {r["id"] for r in results}
        assert ids["d1"] in result_ids
        assert ids["d2"] in result_ids
        assert ids["d3"] in result_ids
        assert ids["d4"] in result_ids
        # tombstoned doc excluded
        assert ids["d5"] not in result_ids

    def test_single_filter_returns_matching_docs(self, storage):
        """Single key-value filter returns only matching documents."""
        adapter, ids = storage
        results = adapter.retrieve_by_vector_similarity(
            [0.5] * 768,
            limit=10,
            metadata_filters={"category": "sports"},
        )
        result_ids = {r["id"] for r in results}
        assert ids["d1"] in result_ids
        assert ids["d2"] in result_ids
        assert ids["d3"] not in result_ids
        assert ids["d4"] not in result_ids

    def test_single_filter_non_matching_returns_empty(self, storage):
        """Filter with no matching documents returns empty list."""
        adapter, ids = storage
        results = adapter.retrieve_by_vector_similarity(
            [0.5] * 768,
            limit=10,
            metadata_filters={"category": "finance"},
        )
        assert results == []

    def test_multiple_filters_and_semantics(self, storage):
        """Multiple filters use AND semantics — all must match."""
        adapter, ids = storage
        results = adapter.retrieve_by_vector_similarity(
            [0.5] * 768,
            limit=10,
            metadata_filters={"category": "sports", "league": "nfl"},
        )
        result_ids = {r["id"] for r in results}
        assert ids["d1"] in result_ids
        assert ids["d2"] not in result_ids  # league=nba, not nfl
        assert ids["d3"] not in result_ids
        assert ids["d4"] not in result_ids

    def test_null_metadata_excluded_when_filters_provided(self, storage):
        """NULL metadata rows are excluded when any filter is provided."""
        adapter, ids = storage
        results = adapter.retrieve_by_vector_similarity(
            [0.5] * 768,
            limit=10,
            metadata_filters={"category": "sports"},
        )
        result_ids = {r["id"] for r in results}
        assert ids["d4"] not in result_ids

    def test_tombstoned_excluded_even_with_matching_filters(self, storage):
        """Tombstoned documents are excluded regardless of metadata match."""
        adapter, ids = storage
        results = adapter.retrieve_by_vector_similarity(
            [0.5] * 768,
            limit=10,
            metadata_filters={"category": "sports", "league": "nfl"},
        )
        result_ids = {r["id"] for r in results}
        assert ids["d5"] not in result_ids

    def test_empty_filters_dict_behaves_like_no_filters(self, storage):
        """Empty dict for metadata_filters behaves the same as None."""
        adapter, ids = storage
        results_none = adapter.retrieve_by_vector_similarity(
            [0.5] * 768, limit=10, metadata_filters=None
        )
        results_empty = adapter.retrieve_by_vector_similarity(
            [0.5] * 768, limit=10, metadata_filters={}
        )
        assert {r["id"] for r in results_none} == {r["id"] for r in results_empty}


# ---------------------------------------------------------------------------
# retrieve_by_weight — basic behavior + metadata_filters
# ---------------------------------------------------------------------------


class TestRetrieveByWeight:
    def test_no_filters_returns_all_non_tombstoned(self, storage):
        """No metadata_filters — returns all non-tombstoned docs, ranked by weight."""
        adapter, ids = storage
        results = adapter.retrieve_by_weight(limit=10)
        result_ids = {r["id"] for r in results}
        assert ids["d1"] in result_ids
        assert ids["d2"] in result_ids
        assert ids["d3"] in result_ids
        assert ids["d4"] in result_ids
        # tombstoned excluded
        assert ids["d5"] not in result_ids

    def test_returns_weight_rank_field(self, storage):
        """Results include weight_rank field."""
        adapter, ids = storage
        results = adapter.retrieve_by_weight(limit=10)
        for r in results:
            assert "weight_rank" in r

    def test_single_filter_returns_matching_docs(self, storage):
        """Single key-value filter returns only matching documents."""
        adapter, ids = storage
        results = adapter.retrieve_by_weight(
            limit=10,
            metadata_filters={"category": "sports"},
        )
        result_ids = {r["id"] for r in results}
        assert ids["d1"] in result_ids
        assert ids["d2"] in result_ids
        assert ids["d3"] not in result_ids
        assert ids["d4"] not in result_ids

    def test_single_filter_non_matching_returns_empty(self, storage):
        """Filter with no matching documents returns empty list."""
        adapter, ids = storage
        results = adapter.retrieve_by_weight(
            limit=10,
            metadata_filters={"category": "finance"},
        )
        assert results == []

    def test_multiple_filters_and_semantics(self, storage):
        """Multiple filters use AND semantics — all must match."""
        adapter, ids = storage
        results = adapter.retrieve_by_weight(
            limit=10,
            metadata_filters={"category": "sports", "league": "nfl"},
        )
        result_ids = {r["id"] for r in results}
        assert ids["d1"] in result_ids
        assert ids["d2"] not in result_ids
        assert ids["d3"] not in result_ids
        assert ids["d4"] not in result_ids

    def test_null_metadata_excluded_when_filters_provided(self, storage):
        """NULL metadata rows are excluded when any filter is provided."""
        adapter, ids = storage
        results = adapter.retrieve_by_weight(
            limit=10,
            metadata_filters={"category": "news"},
        )
        result_ids = {r["id"] for r in results}
        assert ids["d4"] not in result_ids

    def test_tombstoned_excluded_even_with_matching_filters(self, storage):
        """Tombstoned documents are excluded regardless of metadata match."""
        adapter, ids = storage
        results = adapter.retrieve_by_weight(
            limit=10,
            metadata_filters={"category": "sports", "league": "nfl"},
        )
        result_ids = {r["id"] for r in results}
        assert ids["d5"] not in result_ids

    def test_empty_filters_dict_behaves_like_no_filters(self, storage):
        """Empty dict for metadata_filters behaves the same as None."""
        adapter, ids = storage
        results_none = adapter.retrieve_by_weight(limit=10, metadata_filters=None)
        results_empty = adapter.retrieve_by_weight(limit=10, metadata_filters={})
        assert {r["id"] for r in results_none} == {r["id"] for r in results_empty}

    def test_results_ordered_by_weight_rank_descending(self, tmp_path):
        """Results are ordered by weight_rank descending (higher is better)."""
        db_path = tmp_path / "test.db"
        adapter = StorageAdapter(str(db_path))
        adapter.initialize()

        base_vec = [0.5] * 768
        d1 = adapter.save_payload("uri1", {"cat": "a"}, base_vec, plugin="p", record_type="t")
        d2 = adapter.save_payload("uri2", {"cat": "a"}, base_vec, plugin="p", record_type="t")

        adapter.update_weight(d2, signal=5)  # d2 gets high weight

        results = adapter.retrieve_by_weight(limit=10)
        result_ids = [r["id"] for r in results]
        assert result_ids[0] == d2, "Higher-weighted doc should rank first"
        adapter.close()

    def test_limit_respected(self, storage):
        """limit parameter is respected."""
        adapter, ids = storage
        results = adapter.retrieve_by_weight(limit=2)
        assert len(results) <= 2

    def test_plugin_filter_applied(self, tmp_path):
        """plugins parameter filters by plugin."""
        db_path = tmp_path / "test.db"
        adapter = StorageAdapter(str(db_path))
        adapter.initialize()

        base_vec = [0.5] * 768
        d1 = adapter.save_payload("uri1", {"x": "1"}, base_vec, plugin="alpha", record_type="t")
        d2 = adapter.save_payload("uri2", {"x": "1"}, base_vec, plugin="beta", record_type="t")

        results = adapter.retrieve_by_weight(limit=10, plugins=["alpha"])
        result_ids = {r["id"] for r in results}
        assert d1 in result_ids
        assert d2 not in result_ids
        adapter.close()

    def test_record_type_filter_applied(self, tmp_path):
        """record_types parameter filters by record_type."""
        db_path = tmp_path / "test.db"
        adapter = StorageAdapter(str(db_path))
        adapter.initialize()

        base_vec = [0.5] * 768
        d1 = adapter.save_payload("uri1", {"x": "1"}, base_vec, plugin="p", record_type="chunk")
        d2 = adapter.save_payload("uri2", {"x": "1"}, base_vec, plugin="p", record_type="summary")

        results = adapter.retrieve_by_weight(limit=10, record_types=["chunk"])
        result_ids = {r["id"] for r in results}
        assert d1 in result_ids
        assert d2 not in result_ids
        adapter.close()
