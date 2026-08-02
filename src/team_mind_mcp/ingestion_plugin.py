import json

from mcp.types import Tool, TextContent
from team_mind_mcp.server import ToolProvider, PluginRegistry
from team_mind_mcp.ingestion import IngestionPipeline


class IngestionPlugin(ToolProvider):
    """Exposes the internal ingestion loop to external MCP Clients."""

    def __init__(self, registry: PluginRegistry, storage=None, tenant_manager=None):
        self.registry = registry
        self.pipeline = IngestionPipeline(
            self.registry, storage=storage, tenant_manager=tenant_manager
        )

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
                            "description": "List of URIs to ingest by reference (e.g., file:///path/to/docs, https://example.com/api.md)",
                        },
                        "documents": {
                            "type": "array",
                            "description": "Documents to ingest by value. Each item's 'uri' is the identity key; supply 'content' to pass raw content inline (no fetch), in which case 'media_type' is required. Omit 'content' to ingest the uri by reference.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "uri": {
                                        "type": "string",
                                        "description": "Identity key for idempotency / updates.",
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "Optional inline raw content; when present it is used directly with no fetch.",
                                    },
                                    "media_type": {
                                        "type": "string",
                                        "description": "Media type of the content (e.g. text/markdown). Required when 'content' is present.",
                                    },
                                },
                                "required": ["uri"],
                            },
                        },
                        "semantic_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Semantic types for routing this ingest to matching processors.",
                        },
                        "reliability_hint": {
                            "type": "number",
                            "description": "Optional reliability hint (0.0–1.0) for the ingested content.",
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant to ingest documents into (default: 'default').",
                        },
                    },
                    "anyOf": [
                        {"required": ["uris"]},
                        {"required": ["documents"]},
                    ],
                },
            ),
            Tool(
                name="submit_structured",
                description="Submit one or more pre-refined records for validated ingestion against their record types' JSON Schemas.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "records": {
                            "type": "array",
                            "description": "Batch of records; each validated and written independently.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "record_type": {
                                        "type": "string",
                                        "description": "The refined record type (routing key).",
                                    },
                                    "payload": {
                                        "type": "object",
                                        "description": "The record as JSON; validated against the record type's schema. Stored 1:1 as the metadata sub-document.",
                                    },
                                    "uri": {
                                        "type": "string",
                                        "description": "Identity key for idempotency / updates.",
                                    },
                                    "reliability_hint": {
                                        "type": "number",
                                        "description": "Optional confidence seed (0.0–1.0); top rung of SPEC-007 reliability seeding.",
                                    },
                                },
                                "required": ["record_type", "payload", "uri"],
                            },
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant for the batch (default: 'default').",
                        },
                    },
                    "required": ["records"],
                },
            ),
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name == "ingest_documents":
            return await self._call_ingest_documents(arguments)
        if name == "submit_structured":
            return await self._call_submit_structured(arguments)
        raise ValueError(f"Unsupported tool: {name}")

    @staticmethod
    def _normalize_documents(
        uris: list[str], documents: list[dict]
    ) -> tuple[list[str], dict[str, str], dict[str, str]]:
        """Fold ``uris`` (by-reference) and ``documents`` (by-value) into one form.

        Returns a single ordered URI list plus two per-URI maps: inline
        ``contents`` and declared ``media_types``. A document item carrying
        ``content`` but no ``media_type`` is rejected (media_type is required
        with inline content — SPEC-012 STORY-006 AC-002).

        Raises:
            ValueError: for an item missing ``uri`` or supplying ``content``
                without ``media_type``.
        """
        norm_uris: list[str] = list(uris)
        contents: dict[str, str] = {}
        declared_media_types: dict[str, str] = {}

        for item in documents:
            uri = item.get("uri")
            if not uri:
                raise ValueError("Each document item requires a 'uri'.")
            content = item.get("content")
            media_type = item.get("media_type")
            if content is not None and not media_type:
                raise ValueError(
                    f"Document item '{uri}' supplies content but no media_type; "
                    "media_type is required with inline content."
                )
            norm_uris.append(uri)
            if content is not None:
                contents[uri] = content
            if media_type:
                declared_media_types[uri] = media_type

        return norm_uris, contents, declared_media_types

    async def _call_ingest_documents(self, arguments: dict) -> list[TextContent]:
        uris = arguments.get("uris") or []
        documents = arguments.get("documents") or []
        if not uris and not documents:
            raise ValueError(
                "At least one URI or document is required for ingest_documents"
            )

        semantic_types = arguments.get("semantic_types")
        reliability_hint = arguments.get("reliability_hint")
        tenant_id = arguments.get("tenant_id", "default")

        try:
            norm_uris, contents, declared_media_types = self._normalize_documents(
                uris, documents
            )
            bundle = await self.pipeline.ingest(
                norm_uris,
                semantic_types=semantic_types,
                reliability_hint=reliability_hint,
                tenant_id=tenant_id,
                contents=contents,
                declared_media_types=declared_media_types,
            )
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

    async def _call_submit_structured(self, arguments: dict) -> list[TextContent]:
        records = arguments.get("records", [])
        tenant_id = arguments.get("tenant_id", "default")

        try:
            # Empty batch is rejected inside the pipeline (at least one record
            # required); a per-record error stays inside the results list.
            results = await self.pipeline.ingest_structured(
                records, tenant_id=tenant_id
            )
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"submit_structured failed: {str(e)}",
                )
            ]

        return [TextContent(type="text", text=json.dumps(results))]
