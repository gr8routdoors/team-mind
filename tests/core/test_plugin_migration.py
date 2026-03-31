"""
SPEC-002 / STORY-006: Migrate Existing Plugins to Doctypes
"""

import json
import pytest
from team_mind_mcp.markdown import MarkdownPlugin
from team_mind_mcp.server import RecordTypeSpec
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.ingestion import IngestionBundle


def test_markdown_plugin_declares_record_type(tmp_path):
    """
    AC-001: MarkdownPlugin Declares Doctype
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # Given the MarkdownPlugin class
    plugin = MarkdownPlugin(storage)

    # When its doctypes property is accessed
    specs = plugin.record_types

    # Then it returns a list containing RecordTypeSpecs for markdown_source and markdown_chunk
    assert len(specs) == 2
    names = [s.name for s in specs]
    assert "markdown_source" in names
    assert "markdown_chunk" in names

    # And the markdown_chunk spec includes a description and schema describing the chunk metadata
    chunk_spec = next(s for s in specs if s.name == "markdown_chunk")
    assert isinstance(chunk_spec, RecordTypeSpec)
    assert len(chunk_spec.description) > 0
    assert "chunk" in chunk_spec.schema

    storage.close()


@pytest.mark.asyncio
async def test_markdown_plugin_passes_plugin_and_record_type_on_save(tmp_path):
    """
    AC-002: MarkdownPlugin Passes Plugin and Doctype on Save
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    plugin = MarkdownPlugin(storage)

    # Given the MarkdownPlugin is processing a markdown bundle
    md_file = tmp_path / "test.md"
    md_file.write_text("Hello world paragraph.")
    bundle = IngestionBundle(uris=[md_file.as_uri()], storage=storage)

    # When it calls storage.save_payload
    await plugin.process_bundle(bundle)

    # Then it passes plugin="markdown_plugin" and record_type="markdown_chunk"
    with storage._conn:
        cursor = storage._conn.execute(
            "SELECT plugin, record_type FROM documents WHERE record_type = 'markdown_chunk'"
        )
        rows = cursor.fetchall()

    assert len(rows) >= 1
    assert rows[0][0] == "markdown_plugin"
    assert rows[0][1] == "markdown_chunk"

    storage.close()


@pytest.mark.asyncio
async def test_semantic_search_accepts_filters(tmp_path):
    """
    AC-003 & AC-004: Semantic Search Accepts Plugin and Doctype Filters (multi-value)
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    plugin = MarkdownPlugin(storage)

    # Ingest some markdown
    md_file = tmp_path / "test.md"
    md_file.write_text("Interesting travel content.\n\nAnother paragraph about food.")
    bundle = IngestionBundle(uris=[md_file.as_uri()], storage=storage)
    await plugin.process_bundle(bundle)

    # Also insert a document from a different plugin to test filtering
    storage.save_payload(
        "other://doc",
        {"data": "other"},
        [0.0] * 768,
        plugin="other_plugin",
        record_type="other_type",
    )

    # When semantic_search is called with plugin and doctype filters
    response = await plugin.call_tool(
        "semantic_search",
        {
            "query": "travel",
            "plugins": ["markdown_plugin"],
            "record_types": ["markdown_chunk"],
        },
    )
    results = json.loads(response[0].text)

    # Then results are scoped to the markdown plugin only
    assert all(r["plugin"] == "markdown_plugin" for r in results)
    assert all(r["record_type"] == "markdown_chunk" for r in results)

    # Multi-value: search across both plugins
    response_multi = await plugin.call_tool(
        "semantic_search",
        {"query": "travel", "plugins": ["markdown_plugin", "other_plugin"]},
    )
    results_multi = json.loads(response_multi[0].text)
    plugins_found = {r["plugin"] for r in results_multi}
    assert "markdown_plugin" in plugins_found

    storage.close()


@pytest.mark.asyncio
async def test_response_metadata_includes_plugin_and_doctype(tmp_path):
    """
    AC-005: Response Metadata Includes Plugin and Doctype
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    plugin = MarkdownPlugin(storage)

    md_file = tmp_path / "test.md"
    md_file.write_text("Sample content for testing.")
    bundle = IngestionBundle(uris=[md_file.as_uri()], storage=storage)
    await plugin.process_bundle(bundle)

    # When semantic_search returns results
    response = await plugin.call_tool("semantic_search", {"query": "sample"})
    results = json.loads(response[0].text)

    # Then each result includes plugin and record_type
    assert len(results) > 0
    for r in results:
        assert "plugin" in r
        assert "record_type" in r
        assert r["plugin"] == "markdown_plugin"
        assert r["record_type"] == "markdown_chunk"

    storage.close()
