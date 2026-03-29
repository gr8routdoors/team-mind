"""
SPEC-003 / STORY-004: Two-Phase Ingestion Pipeline
"""

import asyncio
import pytest
from team_mind_mcp.server import IngestProcessor, IngestObserver, PluginRegistry
from team_mind_mcp.ingestion import IngestionPipeline, IngestionBundle, IngestionEvent


class _ProcessorA(IngestProcessor):
    @property
    def name(self) -> str:
        return "processor_a"

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        return [
            IngestionEvent(
                plugin=self.name, doctype="type_a", uris=bundle.uris[:1], doc_ids=[10]
            ),
            IngestionEvent(
                plugin=self.name, doctype="type_b", uris=bundle.uris[:1], doc_ids=[11]
            ),
        ]


class _ProcessorB(IngestProcessor):
    @property
    def name(self) -> str:
        return "processor_b"

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        return [
            IngestionEvent(
                plugin=self.name,
                doctype="type_c",
                uris=bundle.uris,
                doc_ids=[20, 21, 22],
            )
        ]


class _EmptyProcessor(IngestProcessor):
    @property
    def name(self) -> str:
        return "empty_processor"

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        return []


class _SlowProcessor(IngestProcessor):
    """Processor that takes time to simulate slow ingestion."""

    def __init__(self):
        self.completed = False

    @property
    def name(self) -> str:
        return "slow_processor"

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        await asyncio.sleep(0.1)
        self.completed = True
        return [
            IngestionEvent(
                plugin=self.name, doctype="slow_type", uris=bundle.uris, doc_ids=[99]
            )
        ]


class _TrackingObserver(IngestObserver):
    def __init__(self, obs_name: str = "tracking_observer"):
        self._name = obs_name
        self.received_events: list[IngestionEvent] = []
        self.called = False

    @property
    def name(self) -> str:
        return self._name

    async def on_ingest_complete(self, events: list[IngestionEvent]) -> None:
        self.received_events = list(events)
        self.called = True


class _TimingObserver(IngestObserver):
    """Observer that records whether a slow processor was done when it ran."""

    def __init__(self, slow_processor: _SlowProcessor):
        self._slow = slow_processor
        self.processor_was_done = False

    @property
    def name(self) -> str:
        return "timing_observer"

    async def on_ingest_complete(self, events: list[IngestionEvent]) -> None:
        self.processor_was_done = self._slow.completed


@pytest.mark.asyncio
async def test_phase1_collects_events(tmp_path):
    """
    AC-001: Phase 1 Collects Events
    """
    registry = PluginRegistry()
    registry.register(_ProcessorA(), semantic_types=["*"])
    registry.register(_ProcessorB(), semantic_types=["*"])
    pipeline = IngestionPipeline(registry)

    f = tmp_path / "test.md"
    f.write_text("content")

    # When the pipeline ingests a bundle
    bundle = await pipeline.ingest([f.as_uri()])

    # Then events from both processors are collected into a single flat list
    assert bundle is not None
    assert len(bundle.events) == 3  # 2 from A + 1 from B


@pytest.mark.asyncio
async def test_phase2_broadcasts_to_observers(tmp_path):
    """
    AC-002: Phase 2 Broadcasts to Observers
    """
    registry = PluginRegistry()
    registry.register(_ProcessorA(), semantic_types=["*"])
    observer = _TrackingObserver()
    registry.register(observer)
    pipeline = IngestionPipeline(registry)

    f = tmp_path / "test.md"
    f.write_text("content")

    # When the pipeline ingests a bundle
    await pipeline.ingest([f.as_uri()])

    # Then the observer's on_ingest_complete is called with events from Phase 1
    assert observer.called
    assert len(observer.received_events) == 2  # 2 events from ProcessorA


@pytest.mark.asyncio
async def test_observers_run_after_processors_complete(tmp_path):
    """
    AC-003: Observers Run After Processors Complete
    """
    slow = _SlowProcessor()
    timing_obs = _TimingObserver(slow)

    registry = PluginRegistry()
    registry.register(slow, semantic_types=["*"])
    registry.register(timing_obs)
    pipeline = IngestionPipeline(registry)

    f = tmp_path / "test.md"
    f.write_text("content")

    # When the pipeline ingests a bundle
    await pipeline.ingest([f.as_uri()])

    # Then the observer does not receive events until all processors have finished
    assert timing_obs.processor_was_done is True


@pytest.mark.asyncio
async def test_no_events_still_calls_observers(tmp_path):
    """
    AC-004: No Events Means No Observer Phase
    """
    registry = PluginRegistry()
    registry.register(_EmptyProcessor(), semantic_types=["*"])
    observer = _TrackingObserver()
    registry.register(observer)
    pipeline = IngestionPipeline(registry)

    f = tmp_path / "test.md"
    f.write_text("content")

    # When the pipeline ingests (processor returns no events)
    await pipeline.ingest([f.as_uri()])

    # Then observers are still called with an empty event list
    assert observer.called
    assert observer.received_events == []


@pytest.mark.asyncio
async def test_pipeline_returns_events(tmp_path):
    """
    AC-005: Pipeline Returns Events
    """
    registry = PluginRegistry()
    registry.register(_ProcessorA(), semantic_types=["*"])
    pipeline = IngestionPipeline(registry)

    f = tmp_path / "test.md"
    f.write_text("content")

    # When pipeline.ingest completes
    bundle = await pipeline.ingest([f.as_uri()])

    # Then the returned bundle includes the collected IngestionEvent list
    assert bundle is not None
    assert len(bundle.events) == 2
    assert all(isinstance(e, IngestionEvent) for e in bundle.events)


@pytest.mark.asyncio
async def test_multiple_processors_emit_events(tmp_path):
    """
    AC-006: Multiple Processors Emit Events
    """
    registry = PluginRegistry()
    registry.register(_ProcessorA(), semantic_types=["*"])  # emits 2 events
    registry.register(
        _ProcessorB(), semantic_types=["*"]
    )  # emits 3... wait, 1 event with 3 doc_ids
    pipeline = IngestionPipeline(registry)

    f = tmp_path / "test.md"
    f.write_text("content")

    # When the pipeline completes Phase 1
    bundle = await pipeline.ingest([f.as_uri()])

    # Then the combined event list has events from both processors
    assert bundle is not None
    plugins_in_events = {e.plugin for e in bundle.events}
    assert "processor_a" in plugins_in_events
    assert "processor_b" in plugins_in_events
    assert len(bundle.events) == 3  # 2 from A + 1 from B
