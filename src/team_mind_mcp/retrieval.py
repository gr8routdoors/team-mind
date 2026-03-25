import json
import urllib.request
import urllib.parse
from pathlib import Path
from mcp.types import Tool, TextContent
from team_mind_mcp.server import ToolProvider
from team_mind_mcp.storage import StorageAdapter


class DocumentRetrievalPlugin(ToolProvider):
    """Fetches full document text from local DB or live URI pointer."""

    def __init__(self, storage: StorageAdapter):
        self.storage = storage

    @property
    def name(self) -> str:
        return "retrieval_plugin"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="get_full_document",
                description="Retrieve the complete text content of a document by its URI.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "uri": {"type": "string", "description": "The URI pointer"}
                    },
                    "required": ["uri"],
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name != "get_full_document":
            raise ValueError(f"Unsupported tool: {name}")

        uri = arguments.get("uri")
        if not uri:
            raise ValueError("URI is required for get_full_document")

        # 1. Fetch from Local DB if stored
        if self.storage._conn:
            with self.storage._conn:
                cursor = self.storage._conn.execute(
                    "SELECT metadata FROM documents WHERE uri = ?", (uri,)
                )
                row = cursor.fetchone()
                if row:
                    meta = json.loads(row[0]) if row[0] else {}
                    if "local_payload" in meta:
                        return [TextContent(type="text", text=meta["local_payload"])]

        # 2. Fallback to live URI retrieval
        try:
            if uri.startswith("file://"):
                path_str = urllib.parse.urlparse(uri).path
                path = Path(path_str)
                if not path.exists():
                    raise FileNotFoundError(f"File not found: {path}")
                content = path.read_text(encoding="utf-8")
            else:
                req = urllib.request.urlopen(uri)
                content = req.read().decode("utf-8")
            return [TextContent(type="text", text=content)]
        except Exception as e:
            # Throwing a ValueError here forces the MCP Gateway to return an MCP Error Schema
            raise ValueError(f"Document no longer available at {uri}. Details: {e}")
