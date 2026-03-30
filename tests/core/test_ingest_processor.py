"""
SPEC-003 / STORY-002: Rename IngestListener to IngestProcessor
"""

import pytest
from team_mind_mcp.server import IngestProcessor, PluginRegistry
from team_mind_mcp.ingestion import IngestionBundle, IngestionEvent
from team_mind_mcp.markdown import MarkdownPlugin
from team_mind_mcp.storage import StorageAdapter


class _MockProcessor(IngestProcessor):
    @property
    def name(self) -> str:
        return "mock_processor"

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        return [
            IngestionEvent(
                plugin=self.name, record_type="mock_type", uris=bundle.uris, doc_ids=[1]
            )
        ]


def test_ingest_processor_abc_exists():
    """
    AC-001: IngestProcessor ABC Exists
    """
    # Given the server.py module
    # When IngestProcessor is imported (done at top)
    # Then it is an abstract base class with name and process_bundle methods
    assert hasattr(IngestProcessor, "name")
    assert hasattr(IngestProcessor, "process_bundle")


def test_ingest_listener_no_longer_importable():
    """
    AC-002: IngestListener No Longer Importable
    """
    # Given the server.py module
    # When an attempt is made to import IngestListener
    # Then an ImportError is raised
    with pytest.raises(ImportError):
        from team_mind_mcp.server import IngestListener  # noqa: F401


@pytest.mark.asyncio
async def test_process_bundle_returns_events():
    """
    AC-003: process_bundle Returns Events
    """
    # Given a plugin implementing IngestProcessor
    processor = _MockProcessor()
    bundle = IngestionBundle(uris=["file:///test.md"])

    # When process_bundle is called
    events = await processor.process_bundle(bundle)

    # Then the return type is list[IngestionEvent]
    assert isinstance(events, list)
    assert len(events) == 1
    assert isinstance(events[0], IngestionEvent)


@pytest.mark.asyncio
async def test_markdown_plugin_returns_events(tmp_path):
    """
    AC-004: MarkdownPlugin Returns Events
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    plugin = MarkdownPlugin(storage)

    # Given MarkdownPlugin processes a bundle with markdown files
    f1 = tmp_path / "a.md"
    f2 = tmp_path / "b.md"
    f1.write_text("Paragraph A1.\n\nParagraph A2.")
    f2.write_text("Paragraph B1.")
    bundle = IngestionBundle(uris=[f1.as_uri(), f2.as_uri()], storage=storage)

    # When process_bundle completes
    events = await plugin.process_bundle(bundle)

    # Then it returns IngestionEvent objects with correct fields
    assert len(events) == 1
    event = events[0]
    assert event.plugin == "markdown_plugin"
    assert event.record_type == "markdown_chunk"
    assert len(event.uris) == 2
    assert len(event.doc_ids) == 3  # 2 chunks from a.md + 1 from b.md

    storage.close()


def test_registry_tracks_processors():
    """
    AC-005: Registry Tracks Processors
    """
    registry = PluginRegistry()
    processor = _MockProcessor()

    # Given a plugin implementing IngestProcessor is registered
    registry.register(processor)

    # When get_ingest_processors() is called
    processors = registry.get_ingest_processors()

    # Then the plugin appears in the returned list
    assert processor in processors
