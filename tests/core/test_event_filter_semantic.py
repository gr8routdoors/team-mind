"""
SPEC-008 / STORY-006: EventFilter Semantic Type Support
"""

import pytest
from team_mind_mcp.server import (
    EventFilter,
    IngestObserver,
    IngestProcessor,
    PluginRegistry,
    RecordTypeSpec,
)
from team_mind_mcp.ingestion import IngestionEvent, IngestionPipeline, IngestionBundle


# --- Mock plugins ---


class _FilteredObserver(IngestObserver):
    """Observer with a configurable EventFilter."""

    def __init__(self, obs_name: str, ef: EventFilter):
        self._name = obs_name
        self._filter = ef
        self.received_events: list[IngestionEvent] = []
        self.called = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def event_filter(self) -> EventFilter | None:
        return self._filter

    async def on_ingest_complete(self, events: list[IngestionEvent]) -> None:
        self.received_events = list(events)
        self.called = True


class _EventEmittingProcessor(IngestProcessor):
    """Processor that emits a configured list of events."""

    def __init__(self, proc_name: str, events_to_emit: list[IngestionEvent]):
        self._name = proc_name
        self._events = events_to_emit

    @property
    def name(self) -> str:
        return self._name

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [RecordTypeSpec(name="test_type", description="test")]

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        return list(self._events)


# --- AC-001: Filter Events by Semantic Type ---


@pytest.mark.asyncio
async def test_filter_by_semantic_type(tmp_path):
    """AC-001: Filter Events by Semantic Type — only events whose semantic_types contain
    the filter value pass through (ANY-match semantics)."""
    # GIVEN an EventFilter with semantic_types=["architecture_docs"]
    ef = EventFilter(semantic_types=["architecture_docs"])

    events = [
        IngestionEvent(
            plugin="plugin_a",
            record_type="doc",
            uris=["u1"],
            semantic_types=["architecture_docs"],
        ),
        IngestionEvent(
            plugin="plugin_b",
            record_type="doc",
            uris=["u2"],
            semantic_types=["meeting_notes"],
        ),
        IngestionEvent(
            plugin="plugin_c",
            record_type="doc",
            uris=["u3"],
            semantic_types=["architecture_docs"],
        ),
    ]

    registry = PluginRegistry()
    proc = _EventEmittingProcessor("emitter", events)
    obs = _FilteredObserver("filtered", ef)
    registry.register(proc, semantic_types=["*"])
    registry.register(obs)

    pipeline = IngestionPipeline(registry)
    f = tmp_path / "test.md"
    f.write_text("x")
    # WHEN events with semantic types ["architecture_docs", "meeting_notes", "architecture_docs"] are filtered
    await pipeline.ingest([f.as_uri()])

    # THEN only the two events with semantic_type="architecture_docs" pass through
    assert len(obs.received_events) == 2
    assert all("architecture_docs" in e.semantic_types for e in obs.received_events)


# --- AC-002: Combined with Other Filter Fields ---


@pytest.mark.asyncio
async def test_combined_plugin_and_semantic_type_filter(tmp_path):
    """AC-002: Combined with Other Filter Fields — events must match BOTH plugin AND semantic_type."""
    # GIVEN an EventFilter with plugins=["markdown_plugin"] and semantic_types=["architecture_docs"]
    ef = EventFilter(plugins=["markdown_plugin"], semantic_types=["architecture_docs"])

    events = [
        # matches plugin AND semantic type → PASS
        IngestionEvent(
            plugin="markdown_plugin",
            record_type="doc",
            uris=["u1"],
            semantic_types=["architecture_docs"],
        ),
        # matches plugin but NOT semantic type → FAIL
        IngestionEvent(
            plugin="markdown_plugin",
            record_type="doc",
            uris=["u2"],
            semantic_types=["meeting_notes"],
        ),
        # matches semantic type but NOT plugin → FAIL
        IngestionEvent(
            plugin="other_plugin",
            record_type="doc",
            uris=["u3"],
            semantic_types=["architecture_docs"],
        ),
        # matches neither → FAIL
        IngestionEvent(
            plugin="other_plugin",
            record_type="doc",
            uris=["u4"],
            semantic_types=["meeting_notes"],
        ),
    ]

    registry = PluginRegistry()
    proc = _EventEmittingProcessor("emitter", events)
    obs = _FilteredObserver("filtered", ef)
    registry.register(proc, semantic_types=["*"])
    registry.register(obs)

    pipeline = IngestionPipeline(registry)
    f = tmp_path / "test.md"
    f.write_text("x")
    # WHEN events are filtered
    await pipeline.ingest([f.as_uri()])

    # THEN only events matching BOTH the plugin name AND containing "architecture_docs" pass
    assert len(obs.received_events) == 1
    assert obs.received_events[0].plugin == "markdown_plugin"
    assert "architecture_docs" in obs.received_events[0].semantic_types


# --- AC-003: None semantic_types Matches All ---


@pytest.mark.asyncio
async def test_none_semantic_types_matches_all(tmp_path):
    """AC-003: None semantic_types Matches All — all events pass regardless of semantic type."""
    # GIVEN an EventFilter with semantic_types=None
    ef = EventFilter(semantic_types=None)

    events = [
        IngestionEvent(
            plugin="plugin_a", record_type="doc", uris=["u1"], semantic_types=["type_a"]
        ),
        IngestionEvent(
            plugin="plugin_b", record_type="doc", uris=["u2"], semantic_types=["type_b"]
        ),
        IngestionEvent(
            plugin="plugin_c", record_type="doc", uris=["u3"], semantic_types=[]
        ),
    ]

    registry = PluginRegistry()
    proc = _EventEmittingProcessor("emitter", events)
    obs = _FilteredObserver("filtered", ef)
    registry.register(proc, semantic_types=["*"])
    registry.register(obs)

    pipeline = IngestionPipeline(registry)
    f = tmp_path / "test.md"
    f.write_text("x")
    # WHEN events with various semantic types are filtered
    await pipeline.ingest([f.as_uri()])

    # THEN all events pass through regardless of their semantic type
    assert len(obs.received_events) == 3


# --- AC-004: Empty List Matches No Events ---


@pytest.mark.asyncio
async def test_empty_semantic_types_matches_no_events(tmp_path):
    """AC-004: Empty List Matches No Events — semantic_types=[] blocks all events."""
    # GIVEN an EventFilter with semantic_types=[]
    ef = EventFilter(semantic_types=[])

    events = [
        IngestionEvent(
            plugin="plugin_a",
            record_type="doc",
            uris=["u1"],
            semantic_types=["architecture_docs"],
        ),
        IngestionEvent(
            plugin="plugin_b",
            record_type="doc",
            uris=["u2"],
            semantic_types=["meeting_notes"],
        ),
    ]

    registry = PluginRegistry()
    proc = _EventEmittingProcessor("emitter", events)
    obs = _FilteredObserver("filtered", ef)
    registry.register(proc, semantic_types=["*"])
    registry.register(obs)

    pipeline = IngestionPipeline(registry)
    f = tmp_path / "test.md"
    f.write_text("x")
    # WHEN events are filtered
    await pipeline.ingest([f.as_uri()])

    # THEN no events pass through on the semantic_types criterion
    assert not obs.called
    assert obs.received_events == []


# --- Unit-level: direct filter expression tests ---


def test_semantic_type_filter_any_match():
    """Verify ANY-match semantics: an event passes if any of its semantic_types is in the filter."""
    ef = EventFilter(semantic_types=["architecture_docs", "design_docs"])

    # Event with one overlapping type → passes
    e1 = IngestionEvent(
        plugin="p",
        record_type="d",
        semantic_types=["architecture_docs", "meeting_notes"],
    )
    assert ef.semantic_types is None or any(
        st in ef.semantic_types for st in e1.semantic_types
    )

    # Event with no overlap → blocked
    e2 = IngestionEvent(plugin="p", record_type="d", semantic_types=["meeting_notes"])
    assert not (
        ef.semantic_types is None
        or any(st in ef.semantic_types for st in e2.semantic_types)
    )


def test_event_filter_default_semantic_types_is_none():
    """EventFilter.semantic_types defaults to None (fire hose)."""
    ef = EventFilter()
    assert ef.semantic_types is None


def test_event_filter_accepts_semantic_types_field():
    """EventFilter can be constructed with semantic_types."""
    ef = EventFilter(semantic_types=["architecture_docs"])
    assert ef.semantic_types == ["architecture_docs"]
