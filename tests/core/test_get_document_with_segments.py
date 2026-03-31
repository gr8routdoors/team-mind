"""
SPEC-011 / STORY-005: Get Document with Segments
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


def test_ac001_parent_doc_id_returns_parent_metadata_and_children(adapter):
    """
    AC-001: When called with a parent doc_id, returns parent metadata + all
    non-tombstoned child segments with usage_score.
    """
    # Given a parent document with two child segments
    parent_id = adapter.save_parent(
        uri="user://user-1/sports-preferences",
        plugin="travel_plugin",
        record_type="interest_profile",
        metadata={"profile_type": "sports"},
    )
    seg_id_1 = adapter.save_payload(
        uri="user://user-1/sports/nfl-bears",
        metadata={"league": "nfl", "team": "bears"},
        vector=DUMMY_VECTOR,
        plugin="travel_plugin",
        record_type="sport_interest",
        parent_id=parent_id,
        initial_score=3.2,
    )
    seg_id_2 = adapter.save_payload(
        uri="user://user-1/sports/nba-bulls",
        metadata={"league": "nba", "team": "bulls"},
        vector=DUMMY_VECTOR,
        plugin="travel_plugin",
        record_type="sport_interest",
        parent_id=parent_id,
        initial_score=2.4,
    )

    # When get_document_with_segments is called with the parent's doc_id
    result = adapter.get_document_with_segments(parent_id)

    # Then the result has "parent" and "segments" keys
    assert "parent" in result
    assert "segments" in result

    # And the parent metadata is correct
    parent = result["parent"]
    assert parent["id"] == parent_id
    assert parent["uri"] == "user://user-1/sports-preferences"
    assert parent["plugin"] == "travel_plugin"
    assert parent["record_type"] == "interest_profile"
    assert parent["metadata"] == {"profile_type": "sports"}

    # And both segments are returned with usage_score
    segments = result["segments"]
    assert len(segments) == 2
    seg_ids = {s["id"] for s in segments}
    assert seg_ids == {seg_id_1, seg_id_2}

    for seg in segments:
        assert "usage_score" in seg
        assert "id" in seg
        assert "uri" in seg
        assert "record_type" in seg
        assert "metadata" in seg


def test_ac002_segment_doc_id_returns_parent_and_siblings(adapter):
    """
    AC-002: When called with a segment doc_id, resolves via parent_id and
    returns parent metadata + all non-tombstoned sibling segments.
    """
    # Given a parent document with two child segments
    parent_id = adapter.save_parent(
        uri="user://user-2/music-preferences",
        plugin="media_plugin",
        record_type="genre_profile",
        metadata={"profile_type": "music"},
    )
    seg_id_1 = adapter.save_payload(
        uri="user://user-2/music/jazz",
        metadata={"genre": "jazz"},
        vector=DUMMY_VECTOR,
        plugin="media_plugin",
        record_type="genre_interest",
        parent_id=parent_id,
    )
    seg_id_2 = adapter.save_payload(
        uri="user://user-2/music/blues",
        metadata={"genre": "blues"},
        vector=DUMMY_VECTOR,
        plugin="media_plugin",
        record_type="genre_interest",
        parent_id=parent_id,
    )

    # When get_document_with_segments is called with a segment's doc_id
    result = adapter.get_document_with_segments(seg_id_1)

    # Then parent metadata matches the actual parent
    parent = result["parent"]
    assert parent["id"] == parent_id
    assert parent["uri"] == "user://user-2/music-preferences"
    assert parent["record_type"] == "genre_profile"
    assert parent["metadata"] == {"profile_type": "music"}

    # And all siblings (including the queried segment) are in the segments list
    segments = result["segments"]
    assert len(segments) == 2
    seg_ids = {s["id"] for s in segments}
    assert seg_ids == {seg_id_1, seg_id_2}


def test_ac003_standalone_doc_returns_empty_segments(adapter):
    """
    AC-003: A standalone doc (no parent_id, no children) returns
    {"parent": {..., "aggregate_score": None, "segment_count": 0}, "segments": []}.
    """
    # Given a standalone document (saved via save_payload with no parent_id)
    standalone_id = adapter.save_payload(
        uri="user://user-3/standalone-note",
        metadata={"note": "standalone"},
        vector=DUMMY_VECTOR,
        plugin="notes_plugin",
        record_type="note",
    )

    # When get_document_with_segments is called
    result = adapter.get_document_with_segments(standalone_id)

    # Then segments list is empty
    assert result["segments"] == []

    # And aggregate_score is None and segment_count is 0
    parent = result["parent"]
    assert parent["aggregate_score"] is None
    assert parent["segment_count"] == 0
    assert parent["id"] == standalone_id
    assert parent["uri"] == "user://user-3/standalone-note"


def test_ac004_tombstoned_segments_excluded_from_results(adapter):
    """
    AC-004: Tombstoned segments are excluded from the "segments" list
    and from the aggregate score calculation.
    """
    # Given a parent with three segments, one of which will be tombstoned
    parent_id = adapter.save_parent(
        uri="user://user-4/food-preferences",
        plugin="food_plugin",
        record_type="cuisine_profile",
        metadata={"profile_type": "food"},
    )
    seg_active_1 = adapter.save_payload(
        uri="user://user-4/food/italian",
        metadata={"cuisine": "italian"},
        vector=DUMMY_VECTOR,
        plugin="food_plugin",
        record_type="cuisine_interest",
        parent_id=parent_id,
        initial_score=4.0,
    )
    seg_tombstoned = adapter.save_payload(
        uri="user://user-4/food/french",
        metadata={"cuisine": "french"},
        vector=DUMMY_VECTOR,
        plugin="food_plugin",
        record_type="cuisine_interest",
        parent_id=parent_id,
        initial_score=5.0,
    )
    seg_active_2 = adapter.save_payload(
        uri="user://user-4/food/thai",
        metadata={"cuisine": "thai"},
        vector=DUMMY_VECTOR,
        plugin="food_plugin",
        record_type="cuisine_interest",
        parent_id=parent_id,
        initial_score=2.0,
    )

    # When the second segment is tombstoned
    adapter.update_weight(seg_tombstoned, signal=0, tombstone=True)

    # When get_document_with_segments is called
    result = adapter.get_document_with_segments(parent_id)

    # Then only non-tombstoned segments appear
    segment_ids = {s["id"] for s in result["segments"]}
    assert seg_tombstoned not in segment_ids
    assert seg_active_1 in segment_ids
    assert seg_active_2 in segment_ids
    assert len(result["segments"]) == 2


def test_ac005_parent_includes_aggregate_score_and_segment_count(adapter):
    """
    AC-005: The "parent" dict includes aggregate_score (AVG of non-tombstoned
    children's usage_score) and segment_count (count of non-tombstoned children).
    """
    # Given a parent with two non-tombstoned children with known scores
    parent_id = adapter.save_parent(
        uri="user://user-5/travel-preferences",
        plugin="travel_plugin",
        record_type="destination_profile",
        metadata={"profile_type": "travel"},
    )
    adapter.save_payload(
        uri="user://user-5/travel/paris",
        metadata={"city": "paris"},
        vector=DUMMY_VECTOR,
        plugin="travel_plugin",
        record_type="destination_interest",
        parent_id=parent_id,
        initial_score=3.0,
    )
    adapter.save_payload(
        uri="user://user-5/travel/tokyo",
        metadata={"city": "tokyo"},
        vector=DUMMY_VECTOR,
        plugin="travel_plugin",
        record_type="destination_interest",
        parent_id=parent_id,
        initial_score=5.0,
    )

    # When get_document_with_segments is called
    result = adapter.get_document_with_segments(parent_id)

    # Then aggregate_score is the average of the two scores: (3.0 + 5.0) / 2
    parent = result["parent"]
    assert parent["segment_count"] == 2
    assert parent["aggregate_score"] == pytest.approx(4.0)


def test_ac005_aggregate_score_none_when_all_tombstoned(adapter):
    """
    AC-005 (edge): aggregate_score is None when all children are tombstoned.
    """
    # Given a parent with one child that is tombstoned
    parent_id = adapter.save_parent(
        uri="user://user-6/single-segment",
        plugin="test_plugin",
        record_type="parent_type",
    )
    seg_id = adapter.save_payload(
        uri="user://user-6/segment/only",
        metadata={},
        vector=DUMMY_VECTOR,
        plugin="test_plugin",
        record_type="segment_type",
        parent_id=parent_id,
        initial_score=3.0,
    )
    adapter.update_weight(seg_id, signal=0, tombstone=True)

    # When get_document_with_segments is called
    result = adapter.get_document_with_segments(parent_id)

    # Then aggregate_score is None and segment_count is 0
    assert result["parent"]["aggregate_score"] is None
    assert result["parent"]["segment_count"] == 0
    assert result["segments"] == []


def test_ac006_raises_value_error_for_unknown_doc_id(adapter):
    """
    AC-006: Raises ValueError if doc_id does not exist.
    """
    # Given an empty database
    # When get_document_with_segments is called with a nonexistent doc_id
    # Then a ValueError is raised
    with pytest.raises(ValueError, match="No document with id=9999"):
        adapter.get_document_with_segments(9999)


def test_story010_segments_returned_in_insertion_order(adapter):
    """
    SPEC-011 / STORY-010: get_document_with_segments returns segments in
    insertion order, guaranteed by ORDER BY d.id with autoincrement IDs.
    """
    # Given a parent document with 5 segments inserted in a known sequence
    parent_id = adapter.save_parent(
        uri="file:///doc.md",
        plugin="test_plugin",
        record_type="document",
        metadata={},
    )
    segment_ids = []
    for i in range(5):
        seg_id = adapter.save_payload(
            uri=f"file:///doc.md#chunk-{i}",
            metadata={"index": i},
            vector=DUMMY_VECTOR,
            plugin="test_plugin",
            record_type="chunk",
            parent_id=parent_id,
        )
        segment_ids.append(seg_id)

    # When get_document_with_segments is called
    result = adapter.get_document_with_segments(parent_id)

    # Then segments are returned in exact insertion order
    # (ORDER BY d.id guarantees this because SQLite uses autoincrement IDs
    # that increase monotonically with each insertion)
    segments = result["segments"]
    assert len(segments) == 5

    for i in range(5):
        # Assert ordered list comparison — not set-based — for id and uri
        assert segments[i]["id"] == segment_ids[i]
        assert segments[i]["uri"] == f"file:///doc.md#chunk-{i}"
