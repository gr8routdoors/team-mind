"""
STORY-005: Document Retrieval Plugin
"""

import pytest
from team_mind_mcp.retrieval import DocumentRetrievalPlugin
from team_mind_mcp.storage import StorageAdapter


@pytest.mark.asyncio
async def test_retrieval_fetches_local_db_markdown(tmp_path):
    """
    AC-001: Fetches Local DB Markdown
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # Given a chunk of data was explicitly ingested with the store_local=True flag
    # We populate the StorageAdapter with a document containing 'local_payload'
    storage.save_payload(
        uri="virtual://in-db-only",
        metadata={
            "local_payload": "# Embedded Markdown\nThis comes directly from SQLite."
        },
        vector=[0.0] * 768,
        plugin="retrieval_test",
        doctype="embedded_doc",
    )
    plugin = DocumentRetrievalPlugin(storage)

    # When the AI client calls get_full_document
    response = await plugin.call_tool(
        "get_full_document", {"uri": "virtual://in-db-only"}
    )

    # Then the ResourceResolver bypasses the network/file-system
    # And fetches the exact JSON document payload directly from the StorageAdapter DB
    assert len(response) == 1
    assert "Embedded Markdown" in response[0].text

    storage.close()


@pytest.mark.asyncio
async def test_retrieval_fetches_live_file_content_via_uri_pointer(tmp_path):
    """
    AC-002: Fetches Live File Content via URI Pointer
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    plugin = DocumentRetrievalPlugin(storage)

    # Given an ingested bundle that was stored purely as a Pointer (URI) without duplicating the payload locally
    live_file = tmp_path / "live.md"
    live_file.write_text("This is live file content.")

    storage.save_payload(
        uri=live_file.as_uri(),
        metadata={"author": "test"},  # No local_payload
        vector=[0.0] * 768,
        plugin="retrieval_test",
        doctype="live_doc",
    )

    # When the AI client calls get_full_document
    response = await plugin.call_tool("get_full_document", {"uri": live_file.as_uri()})

    # Then the ResourceResolver successfully accesses the live pointer (e.g., local disk or remote fetch)
    # And streams the live content back to the client
    assert len(response) == 1
    assert response[0].text == "This is live file content."

    storage.close()


@pytest.mark.asyncio
async def test_retrieval_handles_unreachable_uri_pointers(tmp_path):
    """
    AC-003: Handles Unreachable URI Pointers
    """
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    plugin = DocumentRetrievalPlugin(storage)

    # Given an AI client requests a URI pointer that has been deleted or moved since ingestion
    missing_file = tmp_path / "deleted.md"
    # Never created so it's missing on disk.

    # When the ResourceResolver attempts to fetch the target
    # Then it gracefully catches the 404 or FileNotFoundError
    # And returns a clean MCP Error string indicating the document is no longer available at that Pointer
    with pytest.raises(
        ValueError, match="Document no longer available at file://.*deleted.md"
    ):
        await plugin.call_tool("get_full_document", {"uri": missing_file.as_uri()})

    storage.close()
