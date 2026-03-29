"""
SPEC-002 / STORY-003: Scoped Storage Queries
"""

import pytest
from team_mind_mcp.storage import StorageAdapter


@pytest.fixture
def populated_storage(tmp_path):
    """Creates a storage with documents from multiple plugins and doctypes."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Base vector with small variations per document
    def make_vector(idx):
        v = [0.0] * 768
        v[idx % 768] = 1.0
        return v

    # plugin_x: type_a (2 docs), type_b (1 doc)
    adapter.save_payload(
        "uri_xa1", {"n": "xa1"}, make_vector(0), plugin="plugin_x", record_type="type_a"
    )
    adapter.save_payload(
        "uri_xa2", {"n": "xa2"}, make_vector(1), plugin="plugin_x", record_type="type_a"
    )
    adapter.save_payload(
        "uri_xb1", {"n": "xb1"}, make_vector(2), plugin="plugin_x", record_type="type_b"
    )

    # plugin_y: type_a (1 doc), type_c (1 doc)
    adapter.save_payload(
        "uri_ya1", {"n": "ya1"}, make_vector(3), plugin="plugin_y", record_type="type_a"
    )
    adapter.save_payload(
        "uri_yc1", {"n": "yc1"}, make_vector(4), plugin="plugin_y", record_type="type_c"
    )

    # plugin_z: type_b (1 doc)
    adapter.save_payload(
        "uri_zb1", {"n": "zb1"}, make_vector(5), plugin="plugin_z", record_type="type_b"
    )

    yield adapter
    adapter.close()


def _query_vector():
    """A neutral query vector (all zeros — equidistant to everything)."""
    return [0.0] * 768


def test_unfiltered_search_returns_all(populated_storage):
    """
    AC-001: Unfiltered Search Returns All
    """
    # Given documents from multiple plugins and doctypes exist in storage
    # When retrieve_by_vector_similarity is called with no filters
    results = populated_storage.retrieve_by_vector_similarity(_query_vector(), limit=10)

    # Then results include documents from all plugins and doctypes
    assert len(results) == 6

    # And results are ordered by vector similarity
    scores = [r["score"] for r in results]
    assert scores == sorted(scores)


def test_filter_by_single_record_type(populated_storage):
    """
    AC-002: Filter by Single Doctype
    """
    # Given documents with doctypes "type_a" and "type_b" exist
    # When called with doctypes=["type_a"]
    results = populated_storage.retrieve_by_vector_similarity(
        _query_vector(), limit=10, record_types=["type_a"]
    )

    # Then only documents with record_type = "type_a" are returned
    assert all(r["record_type"] == "type_a" for r in results)
    assert len(results) == 3  # xa1, xa2, ya1


def test_filter_by_multiple_record_types(populated_storage):
    """
    AC-003: Filter by Multiple Doctypes
    """
    # Given documents with doctypes "type_a", "type_b", and "type_c" exist
    # When called with doctypes=["type_a", "type_b"]
    results = populated_storage.retrieve_by_vector_similarity(
        _query_vector(), limit=10, record_types=["type_a", "type_b"]
    )

    # Then only documents with record_type in ("type_a", "type_b") are returned
    assert all(r["record_type"] in ("type_a", "type_b") for r in results)
    # And documents with record_type = "type_c" are excluded
    assert not any(r["record_type"] == "type_c" for r in results)
    assert len(results) == 5


def test_filter_by_single_plugin(populated_storage):
    """
    AC-004: Filter by Single Plugin
    """
    # Given documents from plugins "plugin_x" and "plugin_y" exist
    # When called with plugins=["plugin_x"]
    results = populated_storage.retrieve_by_vector_similarity(
        _query_vector(), limit=10, plugins=["plugin_x"]
    )

    # Then only documents from plugin = "plugin_x" are returned
    assert all(r["plugin"] == "plugin_x" for r in results)
    assert len(results) == 3


def test_filter_by_multiple_plugins(populated_storage):
    """
    AC-005: Filter by Multiple Plugins
    """
    # Given documents from plugins "plugin_x", "plugin_y", and "plugin_z" exist
    # When called with plugins=["plugin_x", "plugin_y"]
    results = populated_storage.retrieve_by_vector_similarity(
        _query_vector(), limit=10, plugins=["plugin_x", "plugin_y"]
    )

    # Then only documents from those two plugins are returned
    assert all(r["plugin"] in ("plugin_x", "plugin_y") for r in results)
    assert len(results) == 5


def test_combined_plugin_and_record_type_filter(populated_storage):
    """
    AC-006: Combined Plugin and Doctype Filter
    """
    # Given documents across multiple plugins and doctypes exist
    # When called with plugins=["plugin_x"] and doctypes=["type_a"]
    results = populated_storage.retrieve_by_vector_similarity(
        _query_vector(), limit=10, plugins=["plugin_x"], record_types=["type_a"]
    )

    # Then only documents matching BOTH filters are returned
    assert all(
        r["plugin"] == "plugin_x" and r["record_type"] == "type_a" for r in results
    )
    assert len(results) == 2  # xa1, xa2


def test_empty_filter_list_returns_nothing(populated_storage):
    """
    AC-007: Empty Filter List Returns Nothing
    """
    # Given documents exist in storage
    # When called with doctypes=[] (empty list)
    results = populated_storage.retrieve_by_vector_similarity(
        _query_vector(), limit=10, record_types=[]
    )

    # Then no results are returned
    assert len(results) == 0
    # And no error is raised (implicit)


def test_post_filter_knn_behavior(tmp_path):
    """
    AC-008: Post-Filter Behavior with KNN Limit
    """
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # Given 10 documents: 5 with record_type="type_a" and 5 with record_type="type_b"
    for i in range(5):
        v = [0.0] * 768
        v[i] = 1.0
        adapter.save_payload(f"uri_a{i}", {}, v, plugin="p", record_type="type_a")
    for i in range(5, 10):
        v = [0.0] * 768
        v[i] = 1.0
        adapter.save_payload(f"uri_b{i}", {}, v, plugin="p", record_type="type_b")

    # When called with limit=5 and record_types=["type_a"]
    results = adapter.retrieve_by_vector_similarity(
        [0.0] * 768, limit=5, record_types=["type_a"]
    )

    # Then results contain only record_type="type_a" documents
    assert all(r["record_type"] == "type_a" for r in results)

    # And the result count may be fewer than limit due to post-filter KNN behavior
    assert len(results) <= 5
    assert len(results) > 0

    adapter.close()
