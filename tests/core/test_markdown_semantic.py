"""
STORY-008: MarkdownPlugin Media Type and Semantic Type Awareness
"""

import pytest
from unittest.mock import MagicMock
from team_mind_mcp.markdown import MarkdownPlugin
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.ingestion import IngestionBundle


# ---------------------------------------------------------------------------
# AC-001: Declares Supported Media Types
# ---------------------------------------------------------------------------


def test_supported_media_types_property():
    """MarkdownPlugin declares supported_media_types."""
    # Given the MarkdownPlugin processor
    storage = MagicMock(spec=StorageAdapter)
    plugin = MarkdownPlugin(storage)

    # When supported_media_types is accessed
    result = plugin.supported_media_types

    # Then it returns ["text/markdown", "text/plain"]
    assert result == ["text/markdown", "text/plain"]


# ---------------------------------------------------------------------------
# AC-002: Stores semantic_type on Document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_bundle_passes_semantic_type_to_save_payload(tmp_path):
    """process_bundle passes semantic_type to save_payload."""
    # Given a bundle with semantic_type="architecture_docs" routed to the MarkdownPlugin
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    plugin = MarkdownPlugin(storage)

    md_file = tmp_path / "design.md"
    md_file.write_text("Architecture overview paragraph.")

    bundle = IngestionBundle(
        uris=[md_file.as_uri()],
        semantic_types=["architecture_docs"],
        storage=storage,
    )

    # When the plugin processes and saves a document
    await plugin.process_bundle(bundle)

    # Then all document rows (parent + chunk) have semantic_type="architecture_docs"
    with storage._conn:
        cursor = storage._conn.execute("SELECT semantic_type FROM documents")
        rows = cursor.fetchall()

    assert len(rows) == 2  # 1 parent + 1 chunk
    assert all(row[0] == "architecture_docs" for row in rows)

    storage.close()


@pytest.mark.asyncio
async def test_process_bundle_joins_multiple_semantic_types(tmp_path):
    """process_bundle comma-joins multiple semantic_types."""
    # Given a bundle with multiple semantic_types
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    plugin = MarkdownPlugin(storage)

    md_file = tmp_path / "design.md"
    md_file.write_text("Some content.")

    bundle = IngestionBundle(
        uris=[md_file.as_uri()],
        semantic_types=["architecture_docs", "design"],
        storage=storage,
    )

    # When the plugin processes and saves a document
    await plugin.process_bundle(bundle)

    # Then all document rows (parent + chunk) have semantic_type as a comma-joined string
    with storage._conn:
        cursor = storage._conn.execute("SELECT semantic_type FROM documents")
        rows = cursor.fetchall()

    assert len(rows) == 2  # 1 parent + 1 chunk
    assert all(row[0] == "architecture_docs,design" for row in rows)

    storage.close()


# ---------------------------------------------------------------------------
# AC-003: Stores media_type on Document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_bundle_passes_media_type_for_md_file(tmp_path):
    """process_bundle stores media_type=text/markdown for .md URIs."""
    # Given a URI "design.md" processed by the MarkdownPlugin
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    plugin = MarkdownPlugin(storage)

    md_file = tmp_path / "design.md"
    md_file.write_text("Design content.")

    bundle = IngestionBundle(uris=[md_file.as_uri()], storage=storage)

    # When the document is saved
    await plugin.process_bundle(bundle)

    # Then all document rows (parent + chunk) have media_type="text/markdown"
    with storage._conn:
        cursor = storage._conn.execute("SELECT media_type FROM documents")
        rows = cursor.fetchall()

    assert len(rows) == 2  # 1 parent + 1 chunk
    assert all(row[0] == "text/markdown" for row in rows)

    storage.close()


@pytest.mark.asyncio
async def test_process_bundle_passes_media_type_for_txt_file(tmp_path):
    """process_bundle stores media_type=text/plain for .txt URIs."""
    # Given a URI "notes.txt" processed by the MarkdownPlugin
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    plugin = MarkdownPlugin(storage)

    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("Plain text content.")

    bundle = IngestionBundle(uris=[txt_file.as_uri()], storage=storage)

    # When the document is saved
    await plugin.process_bundle(bundle)

    # Then all document rows (parent + chunk) have media_type="text/plain"
    with storage._conn:
        cursor = storage._conn.execute("SELECT media_type FROM documents")
        rows = cursor.fetchall()

    assert len(rows) == 2  # 1 parent + 1 chunk
    assert all(row[0] == "text/plain" for row in rows)

    storage.close()


# ---------------------------------------------------------------------------
# AC-004: Removes Hardcoded .md Extension Check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plugin_accepts_txt_uris(tmp_path):
    """MarkdownPlugin processes .txt files when passed in bundle (no .md extension gate)."""
    # Given the MarkdownPlugin processor with no hardcoded .md extension check
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    plugin = MarkdownPlugin(storage)

    # And a .txt file passed in the bundle (pipeline handles media type filtering)
    txt_file = tmp_path / "readme.txt"
    txt_file.write_text("Plain text paragraph one.\n\nParagraph two.")

    bundle = IngestionBundle(uris=[txt_file.as_uri()], storage=storage)

    # When the plugin processes the bundle
    await plugin.process_bundle(bundle)

    # Then the .txt file is successfully ingested (not skipped due to extension)
    with storage._conn:
        cursor = storage._conn.execute("SELECT uri FROM documents")
        rows = cursor.fetchall()

    # 1 parent (base URI) + 2 chunks (segment URIs)
    assert len(rows) == 3
    # Parent uses the base URI
    assert rows[0][0] == txt_file.as_uri()
    # Chunks use segment URI convention
    assert rows[1][0] == f"{txt_file.as_uri()}#chunk-0"
    assert rows[2][0] == f"{txt_file.as_uri()}#chunk-1"

    storage.close()


def test_no_md_extension_check_in_source():
    """Verify no hardcoded .endswith('.md') in MarkdownPlugin.process_bundle."""
    import inspect
    from team_mind_mcp.markdown import MarkdownPlugin

    # Given the MarkdownPlugin processor code
    source = inspect.getsource(MarkdownPlugin.process_bundle)

    # When routing is handled by semantic type and media type filtering
    # Then there is no hardcoded .md extension check
    assert '.endswith(".md")' not in source
    assert "endswith('.md')" not in source


# ---------------------------------------------------------------------------
# AC: IngestionEvent includes semantic_types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_bundle_includes_semantic_types_in_event(tmp_path):
    """process_bundle includes semantic_types in the returned IngestionEvent."""
    # Given a bundle with semantic_types routed to MarkdownPlugin
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    plugin = MarkdownPlugin(storage)

    md_file = tmp_path / "spec.md"
    md_file.write_text("Spec content paragraph.")

    bundle = IngestionBundle(
        uris=[md_file.as_uri()],
        semantic_types=["specs"],
        storage=storage,
    )

    # When the plugin processes the bundle
    events = await plugin.process_bundle(bundle)

    # Then two IngestionEvents are returned: one for markdown_source, one for markdown_chunk
    assert len(events) == 2
    assert events[0].record_type == "markdown_source"
    assert events[0].semantic_types == ["specs"]
    assert events[1].record_type == "markdown_chunk"
    assert events[1].semantic_types == ["specs"]

    storage.close()
