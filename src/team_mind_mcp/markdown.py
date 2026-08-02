import json
import urllib.request
from mcp.types import Tool, TextContent
from team_mind_mcp.server import ToolProvider, IngestProcessor, RecordTypeSpec
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.ingestion import IngestionBundle, IngestionEvent
from team_mind_mcp.media_types import get_media_type
from team_mind_mcp.toolkit import (
    RecordValidationError,
    validate_record,
    write_record,
)

# Shared, single-source embedding + hashing (see team_mind_mcp.embedding).
# Re-exported under the historic private names for existing callers/tests.
from team_mind_mcp.embedding import mock_embed as _mock_embed
from team_mind_mcp.embedding import content_hash as _content_hash

__all__ = ["MarkdownPlugin", "_mock_embed", "_content_hash"]


class MarkdownPlugin(ToolProvider, IngestProcessor):
    """Parses markdown resources, generates embeddings, and exposes semantic search."""

    def __init__(self, storage: StorageAdapter | None):
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
    def record_types(self) -> list[RecordTypeSpec]:
        return [
            RecordTypeSpec(
                name="markdown_source",
                description="A parent document representing the source markdown file.",
                schema={
                    "type": "object",
                    "properties": {
                        "source_uri": {
                            "type": "string",
                            "description": "The original file URI.",
                        },
                        "chunk_count": {
                            "type": "integer",
                            "description": "Number of paragraph chunks.",
                        },
                    },
                    "required": ["source_uri", "chunk_count"],
                },
            ),
            RecordTypeSpec(
                name="markdown_chunk",
                description="A paragraph-level chunk extracted from a markdown document.",
                schema={
                    "type": "object",
                    "properties": {
                        "chunk": {
                            "type": "string",
                            "description": "The text content of the chunk.",
                        },
                    },
                    "required": ["chunk"],
                },
                embed_source=["chunk"],
            ),
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
                        "record_types": {
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
        record_types_filter = arguments.get("record_types")

        vector = _mock_embed(query)
        results = self.storage.retrieve_by_vector_similarity(
            vector,
            limit=limit,
            plugins=plugins_filter,
            record_types=record_types_filter,
        )

        # Format the SQLite results into an MCP TextContent response
        response_text = json.dumps(results, indent=2)
        return [TextContent(type="text", text=response_text)]

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        """Read URIs from bundle, chunk them, embed, and store."""
        if bundle.storage is None:
            raise RuntimeError(
                "bundle.storage must be set before calling process_bundle; "
                "use IngestionPipeline.ingest() to ensure storage is injected"
            )
        processed_uris: list[str] = []
        doc_ids: list[int] = []
        parent_doc_ids: list[int] = []
        semantic_type = ",".join(bundle.semantic_types)

        # Resolve the declared record type specs once. The parent is validated
        # against its schema then persisted via save_parent (no vector, no weight
        # — SPEC-011); segments are written through the canonical write_record
        # path (validation + embedding + weight). Stamp the chunk spec's plugin
        # so write_record records the correct envelope plugin even when the
        # plugin is used un-registered (direct process_bundle in tests).
        source_spec = next(
            (rt for rt in self.record_types if rt.name == "markdown_source"), None
        )
        chunk_spec = next(
            (rt for rt in self.record_types if rt.name == "markdown_chunk"), None
        )
        if chunk_spec is not None:
            chunk_spec.plugin = self.name

        for uri in bundle.uris:
            # By-value content (SPEC-012 STORY-006): when the caller supplied
            # inline content for this URI, use it directly — no fetch. Otherwise
            # fetch by reference (supporting file:// locally for MVP).
            if uri in bundle.contents:
                content = bundle.contents[uri]
            else:
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

                # Content changed or version changed → wipe old parent (cascades to children)
                bundle.storage.delete_by_uri(
                    uri, plugin=self.name, record_type="markdown_source"
                )
            else:
                current_hash = _content_hash(content)

            processed_uris.append(uri)
            # Prefer the caller-declared media type for inline items (their URI
            # carries no extension to infer from); fall back to extension-based
            # resolution for by-reference items.
            media_type = bundle.declared_media_types.get(uri) or get_media_type(uri)

            # Trivial chunking by paragraphs
            chunks = [p.strip() for p in content.split("\n\n") if p.strip()]

            # Create parent document for the source file. The parent payload is
            # validated against markdown_source's schema (so it is schema-checked
            # like every record), then persisted via save_parent — which, per
            # SPEC-011, writes NO vector and NO weight row. The parent is
            # deliberately NOT routed through write_record (that always creates a
            # weight row).
            parent_payload = {"source_uri": uri, "chunk_count": len(chunks)}
            if source_spec is not None:
                errors = validate_record(parent_payload, source_spec.schema)
                if errors:
                    raise RecordValidationError("markdown_source", errors)
            parent_id = bundle.storage.save_parent(
                uri=uri,
                plugin=self.name,
                record_type="markdown_source",
                metadata=parent_payload,
                content_hash=current_hash,
                plugin_version=self.version,
                semantic_type=semantic_type,
                media_type=media_type,
            )
            parent_doc_ids.append(parent_id)

            # Create segment per paragraph chunk via the canonical write_record
            # path: validates against markdown_chunk's schema, embeds the chunk
            # text (embed_source=["chunk"]) into a vector, seeds reliability
            # (hint -> default -> 0.0), and creates the weight row. The stored
            # metadata is the payload 1:1 ({"chunk": ...}) — no envelope fields.
            for i, chunk in enumerate(chunks):
                if chunk_spec is None:
                    continue
                doc_id = write_record(
                    bundle.storage,
                    "markdown_chunk",
                    {"chunk": chunk},
                    f"{uri}#chunk-{i}",
                    bundle.tenant_id,
                    spec=chunk_spec,
                    reliability_hint=bundle.reliability_hint,
                    parent_id=parent_id,
                    semantic_type=semantic_type,
                    media_type=media_type,
                    plugin_version=self.version,
                )
                doc_ids.append(doc_id)

        if processed_uris:
            return [
                IngestionEvent(
                    plugin=self.name,
                    record_type="markdown_source",
                    uris=processed_uris,
                    doc_ids=parent_doc_ids,
                    semantic_types=bundle.semantic_types,
                    tenant_id=bundle.tenant_id,
                ),
                IngestionEvent(
                    plugin=self.name,
                    record_type="markdown_chunk",
                    uris=processed_uris,
                    doc_ids=doc_ids,
                    semantic_types=bundle.semantic_types,
                    tenant_id=bundle.tenant_id,
                ),
            ]
        return []
