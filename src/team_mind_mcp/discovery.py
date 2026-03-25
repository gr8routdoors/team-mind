import json
from mcp.types import Tool, TextContent
from team_mind_mcp.server import ToolProvider, PluginRegistry


class DoctypeDiscoveryPlugin(ToolProvider):
    """Exposes the doctype catalog as an MCP tool for AI client discovery."""

    def __init__(self, registry: PluginRegistry):
        self.registry = registry

    @property
    def name(self) -> str:
        return "discovery_plugin"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="list_doctypes",
                description="Discover available document types and their schemas across all plugins.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plugins": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter to doctypes from these plugins only.",
                        },
                        "doctypes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter to these doctype names only.",
                        },
                    },
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name != "list_doctypes":
            raise ValueError(f"Unsupported tool: {name}")

        plugin_filter = arguments.get("plugins")
        doctype_filter = arguments.get("doctypes")

        catalog = self.registry.get_doctype_catalog()

        # Apply filters
        if plugin_filter is not None:
            catalog = [dt for dt in catalog if dt.plugin in plugin_filter]
        if doctype_filter is not None:
            catalog = [dt for dt in catalog if dt.name in doctype_filter]

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
