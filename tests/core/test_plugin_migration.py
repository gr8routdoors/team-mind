"""
SPEC-002 / STORY-006: Migrate Existing Plugins to Doctypes
"""
import json
import pytest
from team_mind_mcp.markdown import MarkdownPlugin
from team_mind_mcp.server import DoctypeSpec
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.ingestion import IngestionBundle


def test_markdown_plugin_declares_doctype(tmp_path):
    """
    AC-001: MarkdownPlugin Declares Doctype
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # Given the MarkdownPlugin class
    plugin = MarkdownPlugin(storage)

    # When its doctypes property is accessed
    specs = plugin.doctypes

    # Then it returns a list containing a DoctypeSpec with name="markdown_chunk"
    assert len(specs) == 1
    assert isinstance(specs[0], DoctypeSpec)
    assert specs[0].name == "markdown_chunk"

    # And the spec includes a description and schema describing the chunk metadata
    assert len(specs[0].description) > 0
    assert "chunk" in specs[0].schema

    storage.close()


@pytest.mark.asyncio
async def test_markdown_plugin_passes_plugin_and_doctype_on_save(tmp_path):
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
    bundle = IngestionBundle(uris=[md_file.as_uri()])

    # When it calls storage.save_payload
    await plugin.process_bundle(bundle)

    # Then it passes plugin="markdown_plugin" and doctype="markdown_chunk"
    with storage._conn:
        cursor = storage._conn.execute(
            "SELECT plugin, doctype FROM documents"
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
    bundle = IngestionBundle(uris=[md_file.as_uri()])
    await plugin.process_bundle(bundle)

    # Also insert a document from a different plugin to test filtering
    storage.save_payload(
        "other://doc", {"data": "other"}, [0.0] * 768,
        plugin="other_plugin", doctype="other_type"
    )

    # When semantic_search is called with plugin and doctype filters
    response = await plugin.call_tool("semantic_search", {
        "query": "travel",
        "plugins": ["markdown_plugin"],
        "doctypes": ["markdown_chunk"]
    })
    results = json.loads(response[0].text)

    # Then results are scoped to the markdown plugin only
    assert all(r["plugin"] == "markdown_plugin" for r in results)
    assert all(r["doctype"] == "markdown_chunk" for r in results)

    # Multi-value: search across both plugins
    response_multi = await plugin.call_tool("semantic_search", {
        "query": "travel",
        "plugins": ["markdown_plugin", "other_plugin"]
    })
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
    bundle = IngestionBundle(uris=[md_file.as_uri()])
    await plugin.process_bundle(bundle)

    # When semantic_search returns results
    response = await plugin.call_tool("semantic_search", {"query": "sample"})
    results = json.loads(response[0].text)

    # Then each result includes plugin and doctype
    assert len(results) > 0
    for r in results:
        assert "plugin" in r
        assert "doctype" in r
        assert r["plugin"] == "markdown_plugin"
        assert r["doctype"] == "markdown_chunk"

    storage.close()
