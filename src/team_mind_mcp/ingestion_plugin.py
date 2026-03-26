from mcp.types import Tool, TextContent
from team_mind_mcp.server import ToolProvider, PluginRegistry
from team_mind_mcp.ingestion import IngestionPipeline


class IngestionPlugin(ToolProvider):
    """Exposes the internal ingestion loop to external MCP Clients."""

    def __init__(self, registry: PluginRegistry, storage=None):
        self.registry = registry
        self.pipeline = IngestionPipeline(self.registry, storage=storage)

    @property
    def name(self) -> str:
        return "ingestion_plugin"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="ingest_documents",
                description="Ingest new documents or URIs into the central knowledge base.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "uris": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of URIs to ingest (e.g., file:///path/to/docs, https://example.com/api.md)",
                        }
                    },
                    "required": ["uris"],
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name != "ingest_documents":
            raise ValueError(f"Unsupported tool: {name}")

        uris = arguments.get("uris", [])
        if not uris:
            raise ValueError("At least one URI is required for ingest_documents")

        try:
            bundle = await self.pipeline.ingest(uris)
            if bundle:
                return [
                    TextContent(
                        type="text",
                        text=f"Successfully queued {len(bundle.uris)} items for ingestion.",
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text="Failed to queue any items or no valid URIs found.",
                    )
                ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Failed to queue any items or no valid URIs found. Error: {str(e)}",
                )
            ]
