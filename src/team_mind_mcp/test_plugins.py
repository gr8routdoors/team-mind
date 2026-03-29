"""Sample plugins for testing dynamic loading. Not part of production."""

from mcp.types import Tool, TextContent
from team_mind_mcp.server import (
    ToolProvider,
    IngestObserver,
    IngestProcessor,
    EventFilter,
)


class SampleToolPlugin(ToolProvider):
    @property
    def name(self) -> str:
        return "sample_tool"

    def get_tools(self):
        return [
            Tool(
                name="sample_action",
                description="A sample action.",
                inputSchema={"type": "object", "properties": {}},
            )
        ]

    async def call_tool(self, name, arguments):
        return [TextContent(type="text", text="ok")]


class SampleObserverPlugin(IngestObserver):
    def __init__(self):
        self._event_filter_override = None

    @property
    def name(self) -> str:
        return "sample_observer"

    @property
    def event_filter(self) -> EventFilter | None:
        return getattr(self, "_event_filter_override", None)


class SampleIngestProcessor(IngestProcessor):
    """Sample ingest processor for testing semantic type routing."""

    @property
    def name(self) -> str:
        return "sample_ingest_processor"

    async def process_bundle(self, bundle) -> list:
        return []
