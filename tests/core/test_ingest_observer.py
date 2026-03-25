"""
SPEC-003 / STORY-003: IngestObserver Interface
"""

import pytest
from team_mind_mcp.server import IngestObserver, PluginRegistry
from team_mind_mcp.ingestion import IngestionEvent


class _MockObserver(IngestObserver):
    def __init__(self, obs_name: str = "mock_observer"):
        self._name = obs_name
        self.received_events: list[IngestionEvent] = []

    @property
    def name(self) -> str:
        return self._name

    async def on_ingest_complete(self, events: list[IngestionEvent]) -> None:
        self.received_events.extend(events)


class _NoOpObserver(IngestObserver):
    """Observer that doesn't override on_ingest_complete."""

    @property
    def name(self) -> str:
        return "noop_observer"


def test_ingest_observer_abc_exists():
    """
    AC-001: IngestObserver ABC Exists
    """
    # Given the server.py module
    # When IngestObserver is imported (done at top)
    # Then it is an abstract base class with name and on_ingest_complete methods
    assert hasattr(IngestObserver, "name")
    assert hasattr(IngestObserver, "on_ingest_complete")


@pytest.mark.asyncio
async def test_observer_receives_events():
    """
    AC-002: Observer Receives Events
    """
    # Given a mock IngestObserver
    observer = _MockObserver()
    events = [
        IngestionEvent(plugin="p", doctype="d", uris=["file:///a.md"], doc_ids=[1]),
        IngestionEvent(plugin="q", doctype="e", uris=["file:///b.md"], doc_ids=[2]),
    ]

    # When on_ingest_complete is called with events
    await observer.on_ingest_complete(events)

    # Then the observer receives the full list
    assert len(observer.received_events) == 2
    assert observer.received_events[0].plugin == "p"
    assert observer.received_events[1].plugin == "q"


def test_observer_registered_in_registry():
    """
    AC-003: Observer Registered in Registry
    """
    registry = PluginRegistry()
    observer = _MockObserver()

    # Given a plugin implementing IngestObserver is registered
    registry.register(observer)

    # When get_ingest_observers() is called
    observers = registry.get_ingest_observers()

    # Then the plugin appears in the returned list
    assert observer in observers


@pytest.mark.asyncio
async def test_observer_default_noop():
    """
    AC-004: Observer Default No-Op
    """
    # Given a plugin that implements IngestObserver without overriding on_ingest_complete
    observer = _NoOpObserver()

    # When on_ingest_complete is called
    # Then it completes without error
    await observer.on_ingest_complete(
        [IngestionEvent(plugin="p", doctype="d", uris=[], doc_ids=[])]
    )


@pytest.mark.asyncio
async def test_multiple_observers():
    """
    AC-005: Multiple Observers
    """
    # Given two IngestObserver plugins
    obs1 = _MockObserver("obs1")
    obs2 = _MockObserver("obs2")
    events = [IngestionEvent(plugin="p", doctype="d", uris=["u"], doc_ids=[1])]

    # When events are broadcast to both observers
    await obs1.on_ingest_complete(events)
    await obs2.on_ingest_complete(events)

    # Then both observers receive the same list of events
    assert len(obs1.received_events) == 1
    assert len(obs2.received_events) == 1
    assert obs1.received_events[0] == obs2.received_events[0]
