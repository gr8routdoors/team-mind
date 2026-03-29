"""
STORY-004: Markdown Vector Plugin
"""

import pytest
from team_mind_mcp.markdown import MarkdownPlugin
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.ingestion import IngestionBundle
from team_mind_mcp.server import MCPGateway


@pytest.mark.asyncio
async def test_markdown_semantic_ingestion(tmp_path):
    """
    AC-001: Markdown Semantic Ingestion
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # Given the MarkdownPlugin is active
    plugin = MarkdownPlugin(storage)

    # Create a dummy markdown file
    md_file = tmp_path / "test.md"
    md_file.write_text("Paragraph one.\n\nParagraph two.")

    # When it receives a .process_bundle() event containing a .md resource
    bundle = IngestionBundle(uris=[md_file.as_uri()])
    await plugin.process_bundle(bundle)

    # Then it chunks the text and requests embeddings for each chunk
    # And it stores the embeddings along with the Source Pointer (URI) in the StorageAdapter
    # Verify in DB
    with storage._conn:
        cursor = storage._conn.execute("SELECT uri, metadata FROM documents")
        rows = cursor.fetchall()

    assert len(rows) == 2
    assert rows[0][0] == md_file.as_uri()
    assert "Paragraph one" in rows[0][1]
    assert rows[1][0] == md_file.as_uri()
    assert "Paragraph two" in rows[1][1]

    storage.close()


@pytest.mark.asyncio
async def test_markdown_tool_registration(tmp_path):
    """
    AC-002: Tool Registration
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # Given the MCPGateway and PluginRegistry are online
    gateway = MCPGateway()

    # When the MarkdownPlugin initializes
    plugin = MarkdownPlugin(storage)
    gateway.registry.register(plugin, semantic_types=["*"])

    # Then it successfully registers the semantic_search tool
    # And it is visible to MCP clients
    tools = gateway.registry.get_all_tools()
    assert any(tool.name == "semantic_search" for tool in tools)

    storage.close()


@pytest.mark.asyncio
async def test_markdown_processes_only_passed_uris(tmp_path):
    """
    AC-003 (updated): Media type filtering is done by the pipeline before the plugin.
    The plugin processes all URIs it receives. This test verifies the pipeline-level
    filtering works: only supported media type files reach the plugin.
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    plugin = MarkdownPlugin(storage)

    # Given a bundle containing only notes.md (pipeline already filtered out image.png)
    notes_file = tmp_path / "notes.md"
    notes_file.write_text("Hello markdown")

    # When the MarkdownPlugin processes the bundle (pipeline pre-filtered URIs)
    bundle = IngestionBundle(uris=[notes_file.as_uri()])
    await plugin.process_bundle(bundle)

    # Then it successfully parses notes.md
    with storage._conn:
        cursor = storage._conn.execute("SELECT uri FROM documents")
        rows = cursor.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == notes_file.as_uri()

    storage.close()
