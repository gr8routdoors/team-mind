"""Tests for reliability_hint field on IngestionBundle (SPEC-007 STORY-001)."""

from team_mind_mcp.ingestion import IngestionBundle


# AC-001: Field Exists and Defaults to None
def test_reliability_hint_defaults_to_none():
    # Given an IngestionBundle created without specifying reliability_hint
    bundle = IngestionBundle(uris=["file:///some/file.txt"])

    # When reliability_hint is accessed
    result = bundle.reliability_hint

    # Then it is None
    assert result is None


# AC-002: Hint Propagates Through Bundle
def test_reliability_hint_propagates_with_bundle():
    # Given a bundle created with reliability_hint=0.8
    bundle = IngestionBundle(uris=["file:///some/file.txt"], reliability_hint=0.8)

    # When a processor receives the bundle (simulated by accessing the field)
    received_hint = bundle.reliability_hint

    # Then bundle.reliability_hint is 0.8
    assert received_hint == 0.8


# AC-003: Hint Accessible in Processor
def test_reliability_hint_accessible_in_processor():
    # Given a processor that reads bundle.reliability_hint
    received_hints = []

    def mock_processor(bundle: IngestionBundle) -> None:
        received_hints.append(bundle.reliability_hint)

    # When the pipeline ingests with reliability_hint=0.7
    bundle = IngestionBundle(uris=["file:///some/file.txt"], reliability_hint=0.7)
    mock_processor(bundle)

    # Then the processor sees 0.7
    assert received_hints == [0.7]
