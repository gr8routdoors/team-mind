import json
from mcp.types import Tool, TextContent
from team_mind_mcp.server import ToolProvider, PluginRegistry


class DoctypeDiscoveryPlugin(ToolProvider):
    """Exposes the record type catalog as an MCP tool for AI client discovery."""

    def __init__(self, registry: PluginRegistry):
        self.registry = registry

    @property
    def name(self) -> str:
        return "discovery_plugin"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="list_record_types",
                description="Discover available record types and their schemas across all plugins.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plugins": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter to record types from these plugins only.",
                        },
                        "record_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter to these record type names only.",
                        },
                    },
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name != "list_record_types":
            raise ValueError(f"Unsupported tool: {name}")

        plugin_filter = arguments.get("plugins")
        record_type_filter = arguments.get("record_types")

        catalog = self.registry.get_record_type_catalog()

        # Apply filters
        if plugin_filter is not None:
            catalog = [dt for dt in catalog if dt.plugin in plugin_filter]
        if record_type_filter is not None:
            catalog = [dt for dt in catalog if dt.name in record_type_filter]

        result = [
            {
                "plugin": dt.plugin,
                "name": dt.name,
                "description": dt.description,
                "schema": dt.schema,
            }
            for dt in catalog
        ]

        return [TextContent(type="text", text=json.dumps(result, indent=2))]
