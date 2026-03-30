"""
SPEC-011 / STORY-006: Aggregate Parent Scoring
"""

import pytest
from team_mind_mcp.storage import StorageAdapter

DUMMY_VECTOR = [0.0] * 768


@pytest.fixture
def adapter(tmp_path):
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    yield storage
    storage.close()


def test_ac001_returns_dict_with_required_keys(adapter):
    """
    AC-001: get_parent_aggregate_score(parent_id) returns a dict with keys
    parent_id, aggregate_score, segment_count, min_score, max_score.
    """
    # Given a parent with one child segment
    parent_id = adapter.save_parent(
        uri="user://user-1/prefs",
        plugin="test_plugin",
        record_type="profile",
    )
    adapter.save_payload(
        uri="user://user-1/prefs/seg-1",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
        initial_score=2.0,
    )

    # When get_parent_aggregate_score is called
    result = adapter.get_parent_aggregate_score(parent_id)

    # Then the result contains all required keys
    assert "parent_id" in result
    assert "aggregate_score" in result
    assert "segment_count" in result
    assert "min_score" in result
    assert "max_score" in result
    assert result["parent_id"] == parent_id


def test_ac002_aggregate_score_is_avg_of_non_tombstoned_children(adapter):
    """
    AC-002: aggregate_score is the AVG of usage_score across non-tombstoned
    child segments joined with doc_weights.
    """
    # Given a parent with three child segments with known scores
    parent_id = adapter.save_parent(
        uri="user://user-2/prefs",
        plugin="test_plugin",
        record_type="profile",
    )
    adapter.save_payload(
        uri="user://user-2/prefs/seg-1",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
        initial_score=1.0,
    )
    adapter.save_payload(
        uri="user://user-2/prefs/seg-2",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
        initial_score=3.0,
    )
    adapter.save_payload(
        uri="user://user-2/prefs/seg-3",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
        initial_score=5.0,
    )

    # When get_parent_aggregate_score is called
    result = adapter.get_parent_aggregate_score(parent_id)

    # Then aggregate_score is the average of 1.0, 3.0, 5.0 = 3.0
    assert result["aggregate_score"] == pytest.approx(3.0)


def test_ac003_segment_count_is_count_of_non_tombstoned_children(adapter):
    """
    AC-003: segment_count is the count of non-tombstoned children.
    """
    # Given a parent with two active and one tombstoned child
    parent_id = adapter.save_parent(
        uri="user://user-3/prefs",
        plugin="test_plugin",
        record_type="profile",
    )
    adapter.save_payload(
        uri="user://user-3/prefs/seg-1",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
    )
    adapter.save_payload(
        uri="user://user-3/prefs/seg-2",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
    )
    seg_tombstoned = adapter.save_payload(
        uri="user://user-3/prefs/seg-3",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
    )
    adapter.update_weight(seg_tombstoned, signal=0, tombstone=True)

    # When get_parent_aggregate_score is called
    result = adapter.get_parent_aggregate_score(parent_id)

    # Then segment_count reflects only non-tombstoned children
    assert result["segment_count"] == 2


def test_ac004_min_score_and_max_score_of_non_tombstoned_children(adapter):
    """
    AC-004: min_score and max_score are the MIN and MAX of non-tombstoned
    children's usage_score.
    """
    # Given a parent with children having scores -1.0, 2.0, 4.5
    parent_id = adapter.save_parent(
        uri="user://user-4/prefs",
        plugin="test_plugin",
        record_type="profile",
    )
    adapter.save_payload(
        uri="user://user-4/prefs/seg-1",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
        initial_score=-1.0,
    )
    adapter.save_payload(
        uri="user://user-4/prefs/seg-2",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
        initial_score=2.0,
    )
    adapter.save_payload(
        uri="user://user-4/prefs/seg-3",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
        initial_score=4.5,
    )

    # When get_parent_aggregate_score is called
    result = adapter.get_parent_aggregate_score(parent_id)

    # Then min_score and max_score are correct
    assert result["min_score"] == pytest.approx(-1.0)
    assert result["max_score"] == pytest.approx(4.5)


def test_ac005_no_children_returns_none_aggregates_and_zero_count(adapter):
    """
    AC-005: When the parent has no children, returns aggregate_score=None,
    segment_count=0, min_score=None, max_score=None.
    """
    # Given a parent with no children
    parent_id = adapter.save_parent(
        uri="user://user-5/empty-parent",
        plugin="test_plugin",
        record_type="profile",
    )

    # When get_parent_aggregate_score is called
    result = adapter.get_parent_aggregate_score(parent_id)

    # Then all aggregates are None and count is 0
    assert result["aggregate_score"] is None
    assert result["segment_count"] == 0
    assert result["min_score"] is None
    assert result["max_score"] is None


def test_ac005_all_tombstoned_returns_none_aggregates_and_zero_count(adapter):
    """
    AC-005 (edge): When all children are tombstoned, returns aggregate_score=None,
    segment_count=0, min_score=None, max_score=None.
    """
    # Given a parent with one child that is tombstoned
    parent_id = adapter.save_parent(
        uri="user://user-6/all-tombstoned",
        plugin="test_plugin",
        record_type="profile",
    )
    seg_id = adapter.save_payload(
        uri="user://user-6/all-tombstoned/seg-1",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
        initial_score=3.0,
    )
    adapter.update_weight(seg_id, signal=0, tombstone=True)

    # When get_parent_aggregate_score is called
    result = adapter.get_parent_aggregate_score(parent_id)

    # Then all aggregates are None and count is 0
    assert result["aggregate_score"] is None
    assert result["segment_count"] == 0
    assert result["min_score"] is None
    assert result["max_score"] is None


def test_ac006_tombstoned_segments_excluded_from_all_aggregates(adapter):
    """
    AC-006: Tombstoned segments are excluded from all aggregates (aggregate_score,
    segment_count, min_score, max_score).
    """
    # Given a parent with two active segments (scores 2.0, 4.0) and one
    # tombstoned segment (score 100.0) that should not affect the results
    parent_id = adapter.save_parent(
        uri="user://user-7/mixed",
        plugin="test_plugin",
        record_type="profile",
    )
    adapter.save_payload(
        uri="user://user-7/mixed/seg-active-1",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
        initial_score=2.0,
    )
    adapter.save_payload(
        uri="user://user-7/mixed/seg-active-2",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
        initial_score=4.0,
    )
    seg_tombstoned = adapter.save_payload(
        uri="user://user-7/mixed/seg-tombstoned",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment",
        parent_id=parent_id,
        initial_score=100.0,
    )
    adapter.update_weight(seg_tombstoned, signal=0, tombstone=True)

    # When get_parent_aggregate_score is called
    result = adapter.get_parent_aggregate_score(parent_id)

    # Then the tombstoned segment is excluded from all aggregates
    assert result["segment_count"] == 2
    assert result["aggregate_score"] == pytest.approx(3.0)  # AVG(2.0, 4.0)
    assert result["min_score"] == pytest.approx(2.0)
    assert result["max_score"] == pytest.approx(4.0)
