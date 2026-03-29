"""Tests for semantic_types field on IngestionBundle and IngestionEvent (STORY-004)."""

from team_mind_mcp.ingestion import IngestionBundle, IngestionEvent


# ---------------------------------------------------------------------------
# AC-001: IngestionBundle Has semantic_types Field
# ---------------------------------------------------------------------------


def test_bundle_semantic_types_set_by_caller():
    # Given an IngestionBundle constructed with semantic_types
    bundle = IngestionBundle(
        uris=["file:///doc.md"],
        semantic_types=["architecture_docs", "meeting_notes"],
    )
    # When semantic_types is accessed
    # Then it returns the provided list
    assert bundle.semantic_types == ["architecture_docs", "meeting_notes"]


# ---------------------------------------------------------------------------
# AC-002: IngestionEvent Has semantic_types Field
# ---------------------------------------------------------------------------


def test_event_semantic_types_set_on_construction():
    # Given an IngestionEvent constructed with semantic_types
    event = IngestionEvent(
        plugin="test-plugin",
        doctype="doc",
        semantic_types=["architecture_docs"],
    )
    # When semantic_types is accessed
    # Then it returns the provided list
    assert event.semantic_types == ["architecture_docs"]


# ---------------------------------------------------------------------------
# AC-003: Semantic Types Propagate from Bundle to Event (integration)
# ---------------------------------------------------------------------------


def _stub_processor_create_event(bundle: IngestionBundle) -> IngestionEvent:
    """Minimal stub processor that creates an event copying semantic_types from bundle."""
    return IngestionEvent(
        plugin="stub-plugin",
        doctype="doc",
        uris=bundle.uris,
        semantic_types=list(bundle.semantic_types),
    )


def test_semantic_types_propagate_from_bundle_to_event():
    # Given an IngestionBundle with semantic_types
    bundle = IngestionBundle(
        uris=["file:///meeting.md"],
        semantic_types=["meeting_notes", "design_specs"],
    )
    # When a processor creates an IngestionEvent from this bundle
    event = _stub_processor_create_event(bundle)
    # Then the event's semantic_types matches the bundle's semantic_types
    assert event.semantic_types == ["meeting_notes", "design_specs"]


# ---------------------------------------------------------------------------
# AC-004: Default semantic_types Is Empty List on Both
# ---------------------------------------------------------------------------


def test_bundle_semantic_types_defaults_to_empty_list():
    # Given an IngestionBundle created without specifying semantic_types
    bundle = IngestionBundle(uris=["file:///doc.md"])
    # When semantic_types is accessed
    # Then it returns []
    assert bundle.semantic_types == []


def test_event_semantic_types_defaults_to_empty_list():
    # Given an IngestionEvent created without specifying semantic_types
    event = IngestionEvent(plugin="test-plugin", doctype="doc")
    # When semantic_types is accessed
    # Then it returns []
    assert event.semantic_types == []


def test_bundle_semantic_types_default_is_independent_across_instances():
    # Verify that the default_factory=list creates independent lists (not shared mutable default)
    bundle1 = IngestionBundle(uris=["file:///a.md"])
    bundle2 = IngestionBundle(uris=["file:///b.md"])
    bundle1.semantic_types.append("architecture_docs")
    assert bundle2.semantic_types == []


def test_event_semantic_types_default_is_independent_across_instances():
    # Verify that the default_factory=list creates independent lists (not shared mutable default)
    event1 = IngestionEvent(plugin="p", doctype="d")
    event2 = IngestionEvent(plugin="p", doctype="d")
    event1.semantic_types.append("meeting_notes")
    assert event2.semantic_types == []
