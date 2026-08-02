"""
SPEC-012 / STORY-006: Raw content by-value ingestion.

A caller may supply raw content inline (by value) instead of a fetchable URI.
Decoding stays in the plugin; the framework only threads the inline content and
the declared media_type through the bundle. One test per acceptance criterion.
"""

from unittest.mock import patch

import pytest

from team_mind_mcp.ingestion import IngestionBundle, IngestionEvent, IngestionPipeline
from team_mind_mcp.ingestion_plugin import IngestionPlugin
from team_mind_mcp.markdown import MarkdownPlugin
from team_mind_mcp.server import IngestProcessor, MCPGateway, PluginRegistry
from team_mind_mcp.storage import StorageAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _TrackingProcessor(IngestProcessor):
    """Records every bundle it receives, for routing assertions."""

    def __init__(self, proc_name: str, media_types: list[str] | None = None):
        self._name = proc_name
        self._media_types = media_types
        self.received_bundles: list[IngestionBundle] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def supported_media_types(self) -> list[str] | None:
        return self._media_types

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        self.received_bundles.append(bundle)
        return [IngestionEvent(plugin=self.name, record_type="doc", uris=bundle.uris)]


def _markdown_gateway() -> tuple[IngestionPlugin, StorageAdapter]:
    """A gateway wiring MarkdownPlugin as a wildcard processor over :memory: SQLite."""
    gateway = MCPGateway()
    storage = StorageAdapter(":memory:")
    storage.initialize()
    md = MarkdownPlugin(storage)
    gateway.registry.register(md, semantic_types=["*"])
    plugin = IngestionPlugin(gateway.registry, storage=storage)
    return plugin, storage


def _uris_in_storage(storage: StorageAdapter) -> list[str]:
    with storage._conn:
        cursor = storage._conn.execute("SELECT uri FROM documents ORDER BY id")
        return [row[0] for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# AC-001: Inline content is processed without a fetch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac001_inline_content_processed_without_fetch() -> None:
    """AC-001: inline content on a non-fetchable uri is processed with no fetch."""
    # Given a non-fetchable uri carrying inline markdown content
    plugin, storage = _markdown_gateway()
    documents = [
        {
            "uri": "mem://note/1",
            "content": "Paragraph one.\n\nParagraph two.",
            "media_type": "text/markdown",
        }
    ]

    # When ingestion runs (urlopen is booby-trapped to prove no fetch happens)
    def _explode(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("inline content must not trigger a network fetch")

    with patch("team_mind_mcp.markdown.urllib.request.urlopen", _explode):
        response = await plugin.call_tool("ingest_documents", {"documents": documents})

    # Then the provided content is processed and a document is written for the uri
    assert "Successfully queued" in response[0].text
    stored = _uris_in_storage(storage)
    assert "mem://note/1" in stored
    assert "mem://note/1#chunk-0" in stored
    assert "mem://note/1#chunk-1" in stored
    storage.close()


# ---------------------------------------------------------------------------
# AC-002: Content without media_type is rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac002_content_without_media_type_rejected() -> None:
    """AC-002: content present but no media_type is rejected; nothing is written."""
    # Given an inline item with content but no media_type
    plugin, storage = _markdown_gateway()
    documents = [{"uri": "mem://note/2", "content": "Some body text."}]

    # When ingestion runs
    response = await plugin.call_tool("ingest_documents", {"documents": documents})

    # Then the item is rejected with an error requiring media_type
    assert "media_type" in response[0].text
    # And nothing is written for that item
    assert _uris_in_storage(storage) == []
    storage.close()


# ---------------------------------------------------------------------------
# AC-003: Mixed batch of URI and inline items
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac003_mixed_batch_uri_and_inline(tmp_path) -> None:
    """AC-003: a URI-only item is fetched; an inline item uses provided content."""
    # Given one fetchable URI-only item and one inline item
    plugin, storage = _markdown_gateway()
    md_file = tmp_path / "on_disk.md"
    md_file.write_text("Disk paragraph.")
    inline_uri = "mem://note/3"

    # When ingestion runs over the mixed batch
    response = await plugin.call_tool(
        "ingest_documents",
        {
            "uris": [md_file.as_uri()],
            "documents": [
                {
                    "uri": inline_uri,
                    "content": "Inline paragraph.",
                    "media_type": "text/markdown",
                }
            ],
        },
    )

    # Then both items are processed (URI fetched from disk, inline used as-is)
    assert "Successfully queued" in response[0].text
    stored = _uris_in_storage(storage)
    assert md_file.as_uri() in stored
    assert inline_uri in stored
    storage.close()


# ---------------------------------------------------------------------------
# AC-004: uri remains the identity key for inline content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac004_uri_is_identity_key_for_inline() -> None:
    """AC-004: re-ingesting the same uri with new content updates, not duplicates."""
    # Given an inline item first ingested under mem://note/42
    plugin, storage = _markdown_gateway()
    uri = "mem://note/42"

    await plugin.call_tool(
        "ingest_documents",
        {
            "documents": [
                {"uri": uri, "content": "First.", "media_type": "text/markdown"}
            ]
        },
    )
    first_parents = [u for u in _uris_in_storage(storage) if u == uri]
    assert len(first_parents) == 1

    # When the same uri is ingested again with different content
    await plugin.call_tool(
        "ingest_documents",
        {
            "documents": [
                {"uri": uri, "content": "Second body.", "media_type": "text/markdown"}
            ]
        },
    )

    # Then idempotency keys on uri: the parent is updated, not duplicated
    parents = [u for u in _uris_in_storage(storage) if u == uri]
    assert len(parents) == 1
    # And the new content is what is stored
    with storage._conn:
        cursor = storage._conn.execute(
            "SELECT metadata FROM documents WHERE uri = ?", (f"{uri}#chunk-0",)
        )
        chunk_rows = cursor.fetchall()
    assert len(chunk_rows) == 1
    assert "Second body" in chunk_rows[0][0]
    storage.close()


# ---------------------------------------------------------------------------
# AC-005: media_type filtering still applies to inline content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac005_media_type_filtering_applies_to_inline() -> None:
    """AC-005: only processors supporting the declared media_type receive inline content."""
    # Given a text/markdown processor and an application/json processor
    proc_md = _TrackingProcessor("md_proc", media_types=["text/markdown"])
    proc_json = _TrackingProcessor("json_proc", media_types=["application/json"])
    registry = PluginRegistry()
    registry.register(proc_md, semantic_types=["*"])
    registry.register(proc_json, semantic_types=["*"])
    pipeline = IngestionPipeline(registry)

    inline_uri = "mem://note/5"

    # When inline content declared as text/markdown is routed
    bundle = await pipeline.ingest(
        [inline_uri],
        semantic_types=["*"],
        contents={inline_uri: "hello"},
        declared_media_types={inline_uri: "text/markdown"},
    )

    # Then only the text/markdown processor receives it
    assert bundle is not None
    assert len(proc_md.received_bundles) == 1
    assert proc_md.received_bundles[0].uris == [inline_uri]
    assert proc_md.received_bundles[0].contents == {inline_uri: "hello"}
    # And the application/json-restricted processor does not
    assert len(proc_json.received_bundles) == 0
