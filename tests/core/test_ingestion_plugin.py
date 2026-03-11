"""
STORY-008: Live MCP Ingestion Tool
"""
import pytest
from team_mind_mcp.server import MCPGateway
from team_mind_mcp.ingestion_plugin import IngestionPlugin

@pytest.mark.asyncio
async def test_mcp_ingestion_plugin_registration():
    """
    Verify the IngestionPlugin correctly registers the ingest_documents tool.
    """
    gateway = MCPGateway()
    plugin = IngestionPlugin(gateway.registry)
    gateway.registry.register(plugin)
    
    tools = gateway.registry.get_all_tools()
    assert any(t.name == "ingest_documents" for t in tools)

@pytest.mark.asyncio
async def test_mcp_ingestion_tool_call():
    """
    Verify the ingest_documents tool executes the pipeline successfully.
    """
    gateway = MCPGateway()
    plugin = IngestionPlugin(gateway.registry)
    
    # Send a dummy URI that should be handled gracefully
    response = await plugin.call_tool("ingest_documents", {"uris": ["file:///tmp/missing.md"]})
    
    # ResourceResolver skips missing files but doesn't crash the plugin tool response here
    assert len(response) == 1
    assert "Failed to queue any items or no valid URIs found." in response[0].text
