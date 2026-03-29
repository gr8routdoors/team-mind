"""
SPEC-006 / STORY-001: EventFilter Data Model
SPEC-006 / STORY-002: Filtered Observer Broadcast
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


class _FireHoseObserver(IngestObserver):
    """Observer with no filter — gets everything."""

    def __init__(self, obs_name: str = "firehose"):
        self._name = obs_name
        self.received_events: list[IngestionEvent] = []

    @property
    def name(self) -> str:
        return self._name

    async def on_ingest_complete(self, events: list[IngestionEvent]) -> None:
        self.received_events = list(events)


class _FilteredObserver(IngestObserver):
    """Observer with an EventFilter."""

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
    """Processor that emits configurable events."""

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


# --- STORY-001: EventFilter Data Model ---


def test_event_filter_fields():
    """AC-001: EventFilter Fields"""
    ef = EventFilter(plugins=["java_plugin"], record_types=["code_signature"])
    assert ef.plugins == ["java_plugin"]
    assert ef.record_types == ["code_signature"]


def test_default_event_filter_is_none():
    """AC-002: Default event_filter Is None"""
    obs = _FireHoseObserver()
    assert obs.event_filter is None


def test_observer_declares_filter():
    """AC-003: Observer Declares Filter"""
    ef = EventFilter(plugins=["plugin_a"], record_types=["type_x"])
    obs = _FilteredObserver("test", ef)
    assert obs.event_filter is not None
    assert obs.event_filter.plugins == ["plugin_a"]
    assert obs.event_filter.record_types == ["type_x"]


def test_none_means_fire_hose():
    """AC-004: None Means Fire Hose (both fields None matches everything)"""
    ef = EventFilter(plugins=None, record_types=None)
    events = [
        IngestionEvent(plugin="a", record_type="x"),
        IngestionEvent(plugin="b", record_type="y"),
    ]
    # Filter with both None should match all
    filtered = [
        e
        for e in events
        if (ef.plugins is None or e.plugin in ef.plugins)
        and (ef.record_types is None or e.record_type in ef.record_types)
    ]
    assert len(filtered) == 2


# --- STORY-002: Filtered Observer Broadcast ---


@pytest.fixture
def sample_events():
    return [
        IngestionEvent(
            plugin="java_plugin", record_type="code_signature", uris=["u1"], doc_ids=[1]
        ),
        IngestionEvent(
            plugin="java_plugin", record_type="test_case", uris=["u2"], doc_ids=[2]
        ),
        IngestionEvent(
            plugin="markdown_plugin",
            record_type="markdown_chunk",
            uris=["u3"],
            doc_ids=[3],
        ),
        IngestionEvent(
            plugin="travel_plugin",
            record_type="user_interest",
            uris=["u4"],
            doc_ids=[4],
        ),
        IngestionEvent(
            plugin="python_plugin",
            record_type="code_signature",
            uris=["u5"],
            doc_ids=[5],
        ),
    ]


@pytest.mark.asyncio
async def test_unfiltered_observer_gets_all(tmp_path, sample_events):
    """AC-001: Unfiltered Observer Gets All Events"""
    registry = PluginRegistry()
    proc = _EventEmittingProcessor("emitter", sample_events)
    obs = _FireHoseObserver()
    registry.register(proc, semantic_types=["*"])
    registry.register(obs)

    pipeline = IngestionPipeline(registry)
    f = tmp_path / "test.md"
    f.write_text("x")
    await pipeline.ingest([f.as_uri()])

    assert len(obs.received_events) == 5


@pytest.mark.asyncio
async def test_filtered_observer_gets_matching(tmp_path, sample_events):
    """AC-002: Filtered Observer Gets Only Matching Events"""
    registry = PluginRegistry()
    proc = _EventEmittingProcessor("emitter", sample_events)
    obs = _FilteredObserver("filtered", EventFilter(plugins=["java_plugin"]))
    registry.register(proc, semantic_types=["*"])
    registry.register(obs)

    pipeline = IngestionPipeline(registry)
    f = tmp_path / "test.md"
    f.write_text("x")
    await pipeline.ingest([f.as_uri()])

    assert len(obs.received_events) == 2
    assert all(e.plugin == "java_plugin" for e in obs.received_events)


@pytest.mark.asyncio
async def test_filter_by_plugin_only(tmp_path, sample_events):
    """AC-003: Filter by Plugin Only"""
    registry = PluginRegistry()
    proc = _EventEmittingProcessor("emitter", sample_events)
    obs = _FilteredObserver("filtered", EventFilter(plugins=["java_plugin"]))
    registry.register(proc, semantic_types=["*"])
    registry.register(obs)

    pipeline = IngestionPipeline(registry)
    f = tmp_path / "test.md"
    f.write_text("x")
    await pipeline.ingest([f.as_uri()])

    assert all(e.plugin == "java_plugin" for e in obs.received_events)
    assert len(obs.received_events) == 2


@pytest.mark.asyncio
async def test_filter_by_doctype_only(tmp_path, sample_events):
    """AC-004: Filter by Doctype Only"""
    registry = PluginRegistry()
    proc = _EventEmittingProcessor("emitter", sample_events)
    obs = _FilteredObserver("filtered", EventFilter(record_types=["code_signature"]))
    registry.register(proc, semantic_types=["*"])
    registry.register(obs)

    pipeline = IngestionPipeline(registry)
    f = tmp_path / "test.md"
    f.write_text("x")
    await pipeline.ingest([f.as_uri()])

    assert all(e.record_type == "code_signature" for e in obs.received_events)
    assert len(obs.received_events) == 2  # java + python


@pytest.mark.asyncio
async def test_combined_filter(tmp_path, sample_events):
    """AC-005: Combined Filter"""
    registry = PluginRegistry()
    proc = _EventEmittingProcessor("emitter", sample_events)
    obs = _FilteredObserver(
        "filtered",
        EventFilter(plugins=["java_plugin"], record_types=["code_signature"]),
    )
    registry.register(proc, semantic_types=["*"])
    registry.register(obs)

    pipeline = IngestionPipeline(registry)
    f = tmp_path / "test.md"
    f.write_text("x")
    await pipeline.ingest([f.as_uri()])

    assert len(obs.received_events) == 1
    assert obs.received_events[0].plugin == "java_plugin"
    assert obs.received_events[0].record_type == "code_signature"


@pytest.mark.asyncio
async def test_no_matching_events_skips_observer(tmp_path, sample_events):
    """AC-006: No Matching Events Skips Observer"""
    registry = PluginRegistry()
    proc = _EventEmittingProcessor("emitter", sample_events)
    obs = _FilteredObserver("filtered", EventFilter(plugins=["nonexistent_plugin"]))
    registry.register(proc, semantic_types=["*"])
    registry.register(obs)

    pipeline = IngestionPipeline(registry)
    f = tmp_path / "test.md"
    f.write_text("x")
    await pipeline.ingest([f.as_uri()])

    assert not obs.called


@pytest.mark.asyncio
async def test_mixed_filtered_and_unfiltered(tmp_path, sample_events):
    """AC-007: Mixed Filtered and Unfiltered Observers"""
    registry = PluginRegistry()
    proc = _EventEmittingProcessor("emitter", sample_events)
    obs_all = _FireHoseObserver("firehose")
    obs_filtered = _FilteredObserver("filtered", EventFilter(plugins=["travel_plugin"]))
    registry.register(proc, semantic_types=["*"])
    registry.register(obs_all)
    registry.register(obs_filtered)

    pipeline = IngestionPipeline(registry)
    f = tmp_path / "test.md"
    f.write_text("x")
    await pipeline.ingest([f.as_uri()])

    assert len(obs_all.received_events) == 5
    assert len(obs_filtered.received_events) == 1
    assert obs_filtered.received_events[0].plugin == "travel_plugin"
