import hashlib
import json
import urllib.request
from mcp.types import Tool, TextContent
from team_mind_mcp.server import ToolProvider, IngestProcessor, DoctypeSpec
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.ingestion import IngestionBundle, IngestionEvent
from team_mind_mcp.media_types import get_media_type


def _mock_embed(text: str) -> list[float]:
    """Deterministically generates a 768-d vector from text for MVP."""
    vector = [0.0] * 768
    h = hashlib.md5(text.encode("utf-8")).digest()
    for i in range(min(16, len(h))):
        vector[i] = h[i] / 255.0
    return vector


def _content_hash(text: str) -> str:
    """SHA-256 hash of content for idempotent ingestion."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MarkdownPlugin(ToolProvider, IngestProcessor):
    """Parses markdown resources, generates embeddings, and exposes semantic search."""

    def __init__(self, storage: StorageAdapter):
        self.storage = storage

    @property
    def name(self) -> str:
        return "markdown_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_media_types(self) -> list[str]:
        return ["text/markdown", "text/plain"]

    @property
    def doctypes(self) -> list[DoctypeSpec]:
        return [
            DoctypeSpec(
                name="markdown_chunk",
                description="A paragraph-level chunk extracted from a markdown document.",
                schema={
                    "chunk": {
                        "type": "string",
                        "description": "The text content of the chunk.",
                    },
                    "plugin": {"type": "string", "description": "Owning plugin name."},
                },
            )
        ]

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="semantic_search",
                description="Search the knowledge base using semantic document similarity.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query text.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results to return.",
                        },
                        "plugins": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter results to these plugins only.",
                        },
                        "doctypes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter results to these document types only.",
                        },
                    },
                    "required": ["query"],
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name != "semantic_search":
            raise ValueError(f"Unsupported tool: {name}")

        query = arguments.get("query")
        if not query:
            raise ValueError("Query is required for semantic_search")

        limit = arguments.get("limit", 5)
        plugins_filter = arguments.get("plugins")
        doctypes_filter = arguments.get("doctypes")

        vector = _mock_embed(query)
        results = self.storage.retrieve_by_vector_similarity(
            vector, limit=limit, plugins=plugins_filter, doctypes=doctypes_filter
        )

        # Format the SQLite results into an MCP TextContent response
        response_text = json.dumps(results, indent=2)
        return [TextContent(type="text", text=response_text)]

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        """Read URIs from bundle, chunk them, embed, and store."""
        processed_uris: list[str] = []
        doc_ids: list[int] = []
        semantic_type = ",".join(bundle.semantic_types)

        for uri in bundle.uris:
            # Fetch content (supporting file:// locally for MVP)
            try:
                if uri.startswith("file://"):
                    req = urllib.request.urlopen(uri)
                    content = req.read().decode("utf-8")
                else:
                    continue
            except Exception:
                continue

            # Check ingestion context for idempotent processing
            ctx = bundle.contexts.get(uri)
            if ctx and ctx.is_update:
                current_hash = _content_hash(content)

                # Content unchanged and same plugin version → skip
                if (
                    ctx.previous_content_hash == current_hash
                    and not ctx.plugin_version_changed
                ):
                    continue

                # Content changed or version changed → wipe old chunks and re-ingest
                self.storage.delete_by_uri(
                    uri, plugin=self.name, doctype="markdown_chunk"
                )
            else:
                current_hash = _content_hash(content)

            processed_uris.append(uri)
            media_type = get_media_type(uri)

            # Trivial chunking by paragraphs
            chunks = [p.strip() for p in content.split("\n\n") if p.strip()]

            for chunk in chunks:
                vector = _mock_embed(chunk)
                metadata = {"chunk": chunk, "plugin": self.name}
                doc_id = self.storage.save_payload(
                    uri,
                    metadata,
                    vector,
                    plugin=self.name,
                    doctype="markdown_chunk",
                    content_hash=current_hash,
                    plugin_version=self.version,
                    semantic_type=semantic_type,
                    media_type=media_type,
                )
                doc_ids.append(doc_id)

        if processed_uris:
            return [
                IngestionEvent(
                    plugin=self.name,
                    doctype="markdown_chunk",
                    uris=processed_uris,
                    doc_ids=doc_ids,
                    semantic_types=bundle.semantic_types,
                )
            ]
        return []
