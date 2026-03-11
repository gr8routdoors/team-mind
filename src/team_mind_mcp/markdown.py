import hashlib
import json
import urllib.request
from mcp.types import Tool, TextContent
from team_mind_mcp.server import Plugin
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.ingestion import IngestionBundle

def _mock_embed(text: str) -> list[float]:
    """Deterministically generates a 768-d vector from text for MVP."""
    vector = [0.0] * 768
    h = hashlib.md5(text.encode('utf-8')).digest()
    for i in range(min(16, len(h))):
        vector[i] = h[i] / 255.0
    return vector

class MarkdownPlugin(Plugin):
    """Parses markdown resources, generates embeddings, and exposes semantic search."""
    
    def __init__(self, storage: StorageAdapter):
        self.storage = storage
        
    @property
    def name(self) -> str:
        return "markdown_plugin"
        
    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="semantic_search",
                description="Search the knowledge base using semantic document similarity.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query text."},
                        "limit": {"type": "integer", "description": "Max results to return."}
                    },
                    "required": ["query"]
                }
            )
        ]
        
    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name != "semantic_search":
            raise ValueError(f"Unsupported tool: {name}")
            
        query = arguments.get("query")
        if not query:
            raise ValueError("Query is required for semantic_search")
            
        limit = arguments.get("limit", 5)
        
        vector = _mock_embed(query)
        results = self.storage.retrieve_by_vector_similarity(vector, limit=limit)
        
        # Format the SQLite results into an MCP TextContent response
        response_text = json.dumps(results, indent=2)
        return [TextContent(type="text", text=response_text)]
        
    async def process_bundle(self, bundle: IngestionBundle) -> None:
        """Filter for .md files, read them, chunk them, embed, and store."""
        for uri in bundle.uris:
            if not uri.endswith(".md"):
                continue
                
            # Fetch content (supporting file:// locally for MVP)
            try:
                if uri.startswith("file://"):
                    req = urllib.request.urlopen(uri)
                    content = req.read().decode('utf-8')
                else:
                    # In a real system, we'd use ResourceResolver for http/https etc
                    continue
            except Exception:
                continue
                
            # Trivial chunking by paragraphs
            chunks = [p.strip() for p in content.split("\n\n") if p.strip()]
            
            for chunk in chunks:
                vector = _mock_embed(chunk)
                metadata = {"chunk": chunk, "plugin": self.name}
                self.storage.save_payload(uri, metadata, vector)
