import asyncio
from typing import Any, Callable, Dict, List

from mcp.server import Server
from mcp.types import Tool, TextContent


from abc import ABC, abstractmethod

class ToolProvider(ABC):
    """Base interface for plugins that expose MCP Tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
        
    def get_tools(self) -> List[Tool]:
        """Return a list of MCP Tools exposed by this plugin."""
        return []
        
    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        """Execute a tool by name."""
        raise NotImplementedError

class IngestListener(ABC):
    """Base interface for plugins that process ingestion events."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    async def process_bundle(self, bundle: Any) -> None:
        """Process an incoming ingestion bundle from the pipeline."""
        pass


class PluginRegistry:
    """Manages the lifecycle and routing for all active plugins."""
    
    def __init__(self):
        self._tool_providers: Dict[str, ToolProvider] = {}
        self._tool_routes: Dict[str, ToolProvider] = {}
        self._ingest_listeners: List[IngestListener] = []
        
    def register(self, plugin: Any) -> None:
        """Register a new plugin components (Tools, Listeners, or both)."""
        if isinstance(plugin, ToolProvider):
            self._tool_providers[plugin.name] = plugin
            for tool in plugin.get_tools():
                if tool.name in self._tool_routes:
                    raise ValueError(f"Tool collision: {tool.name} is already registered.")
                self._tool_routes[tool.name] = plugin
                
        if isinstance(plugin, IngestListener):
            self._ingest_listeners.append(plugin)
            
    def get_all_tools(self) -> List[Tool]:
        """Aggregate all tools from all registered providers."""
        tools = []
        for provider in self._tool_providers.values():
            tools.extend(provider.get_tools())
        return tools
        
    def get_plugin_for_tool(self, tool_name: str) -> ToolProvider | None:
        """Find the provider responsible for a specific tool."""
        return self._tool_routes.get(tool_name)
        
    def get_ingest_listeners(self) -> List[IngestListener]:
        """Return the ordered list of ingestion listeners."""
        return self._ingest_listeners


class MCPGateway:
    """The core MCP server that routes requests to the PluginRegistry."""
    
    def __init__(self, name: str = "team-mind-mcp"):
        self.server = Server(name)
        self.registry = PluginRegistry()
        self._setup_handlers()
        
    def _setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            return self.registry.get_all_tools()
            
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
            plugin = self.registry.get_plugin_for_tool(name)
            if not plugin:
                raise ValueError(f"Unknown tool: {name}")
            
            args = arguments or {}
            return await plugin.call_tool(name, args)
            
    async def run_stdio_async(self):
        """Run the server using stdio transport (required for MCP over pipes)."""
        import mcp.server.stdio
        
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
