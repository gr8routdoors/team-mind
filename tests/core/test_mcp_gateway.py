"""
STORY-001: MCP Gateway & Plugin Registry
"""
import pytest
from mcp.types import Tool, TextContent
from team_mind_mcp.server import MCPGateway, Plugin, PluginRegistry


class MockPlugin(Plugin):
    @property
    def name(self) -> str:
        return "mock_plugin"
        
    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="test_tool",
                description="A test tool",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
        
    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name == "test_tool":
            return [TextContent(type="text", text="success")]
        raise ValueError("Unknown tool")

@pytest.mark.asyncio
async def test_mcp_gateway_server_initialized():
    """
    AC-001: Server Initialized
    """
    # Given the core server is configured with default settings
    gateway = MCPGateway()
    
    # When the server process is started
    # Note: We can't easily start the full stdio loop in a unit test without mocking stdin/stdout,
    # but we CAN verify the server initializes and is ready for the transport bindings.
    
    # Then it successfully binds to an stdio or SSE transport
    assert gateway.server.name == "team-mind-mcp"
    
    # And it responds to MCP initialize handshakes
    options = gateway.server.create_initialization_options()
    assert options.server_name == "team-mind-mcp"
    assert options.server_version is not None

@pytest.mark.asyncio
async def test_mcp_gateway_plugin_registration():
    """
    AC-002: Plugin Registration
    """
    # Given a valid mock plugin that exposes a test_tool
    gateway = MCPGateway()
    plugin = MockPlugin()
    
    # When the plugin is added to the PluginRegistry
    gateway.registry.register(plugin)
    
    # And the MCP client requests the list of available tools
    tools = gateway.registry.get_all_tools()
    
    # Then the test_tool is returned in the tools list with its description and schema
    assert len(tools) == 1
    assert tools[0].name == "test_tool"
    assert tools[0].description == "A test tool"

@pytest.mark.asyncio
async def test_mcp_gateway_rejects_unregistered_tools():
    """
    AC-003: Rejects Unregistered Tools
    """
    # Given the MCP server is running with only test_tool registered
    gateway = MCPGateway()
    gateway.registry.register(MockPlugin())
    
    # When an AI client attempts to call unknown_tool
    # Then the server returns a standard MCP Error response indicating the tool does not exist
    # And the server does not crash
    from mcp.types import CallToolRequest, CallToolRequestParams
    
    from mcp.types import CallToolRequest, CallToolRequestParams, CallToolResult
    
    # We simulate the handler call by fetching the handler and passing the required Pydantic object
    handler = gateway.server.request_handlers[CallToolRequest]
    
    # The internal MCP handler expects a request object of type CallToolRequest
    request = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="unknown_tool", arguments={})
    )
    
    # The MCP SDK traps the ValueError we threw in test_mind_mcp/server.py
    # and wraps it in a ServerResult containing the CallToolResult
    response_payload = await handler(request)
    result = response_payload.root
    
    assert isinstance(result, CallToolResult)
    assert result.isError is True
    assert len(result.content) == 1
    assert "Unknown tool: unknown_tool" in result.content[0].text
