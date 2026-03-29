"""
SPEC-003 / STORY-001: IngestionEvent Data Model
"""

import json
from dataclasses import asdict
from team_mind_mcp.ingestion import IngestionEvent


def test_event_fields():
    """
    AC-001: Event Fields
    """
    # Given the IngestionEvent dataclass is defined
    # When an instance is created with all fields
    event = IngestionEvent(
        plugin="test_plugin",
        record_type="test_type",
        uris=["file:///a.md", "file:///b.md"],
        doc_ids=[1, 2, 3],
    )

    # Then all four fields are accessible and match
    assert event.plugin == "test_plugin"
    assert event.record_type == "test_type"
    assert event.uris == ["file:///a.md", "file:///b.md"]
    assert event.doc_ids == [1, 2, 3]


def test_event_serializable():
    """
    AC-002: Event Serializable
    """
    # Given an IngestionEvent with populated fields
    event = IngestionEvent(plugin="p", record_type="d", uris=["file:///x.md"], doc_ids=[42])

    # When it is converted to a dict
    d = asdict(event)

    # Then all fields are present and can be serialized to JSON
    assert "plugin" in d
    assert "record_type" in d
    assert "uris" in d
    assert "doc_ids" in d
    serialized = json.dumps(d)
    assert len(serialized) > 0


def test_empty_doc_ids_allowed():
    """
    AC-003: Empty Doc IDs Allowed
    """
    # Given a processor that filters out all URIs
    # When it creates an IngestionEvent with empty lists
    event = IngestionEvent(plugin="p", record_type="d", uris=[], doc_ids=[])

    # Then the event is valid with empty lists
    assert event.uris == []
    assert event.doc_ids == []
