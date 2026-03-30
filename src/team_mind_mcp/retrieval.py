import hashlib
import json
import random
import struct
import urllib.request
import urllib.parse
from pathlib import Path
from mcp.types import Tool, TextContent
from team_mind_mcp.server import ToolProvider
from team_mind_mcp.storage import StorageAdapter


def _embed(text: str) -> list[float]:
    """Generate a deterministic mock vector for the given text."""
    seed_bytes = hashlib.sha256(text.encode()).digest()
    seed = int.from_bytes(seed_bytes[:4], "big")
    rng = random.Random(seed)
    return [rng.uniform(-1, 1) for _ in range(768)]


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
                name="retrieve_documents",
                description=(
                    "Search stored documents. Use 'vector' mode for semantic similarity "
                    "(requires query_text), or 'weight' mode for recency/usage ranked "
                    "retrieval (no query_text needed)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query_text": {
                            "type": "string",
                            "description": "Search query (required for vector mode).",
                        },
                        "query_mode": {
                            "type": "string",
                            "enum": ["vector", "weight"],
                            "description": (
                                "Use 'vector' for semantic similarity search (requires "
                                "query_text), 'weight' for recency/usage ranked retrieval "
                                "(no query_text needed)."
                            ),
                        },
                        "metadata_filters": {
                            "type": "object",
                            "description": "Filter results by metadata key-value pairs (AND semantics).",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default 10).",
                        },
                    },
                    "required": [],
                },
            ),
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
            ),
        ]

    async def _retrieve_documents(self, arguments: dict) -> list[TextContent]:
        """Handle the retrieve_documents tool call."""
        query_mode = arguments.get("query_mode", "vector")
        query_text = arguments.get("query_text")
        limit = arguments.get("limit", 5)
        plugins_filter = arguments.get("plugins")
        record_types_filter = arguments.get("record_types")
        metadata_filters = arguments.get("metadata_filters")

        if query_mode == "weight":
            results = self.storage.retrieve_by_weight(
                limit=limit,
                plugins=plugins_filter,
                record_types=record_types_filter,
                metadata_filters=metadata_filters,
            )
        else:
            # vector mode (default)
            if not query_text:
                raise ValueError("query_text is required for vector mode")
            vector = _embed(query_text)
            results = self.storage.retrieve_by_vector_similarity(
                vector,
                limit=limit,
                plugins=plugins_filter,
                record_types=record_types_filter,
                metadata_filters=metadata_filters,
            )

        return [TextContent(type="text", text=json.dumps(results))]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name == "retrieve_documents":
            return await self._retrieve_documents(arguments)
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
