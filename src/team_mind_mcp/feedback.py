import json
from mcp.types import Tool, TextContent
from team_mind_mcp.server import ToolProvider
from team_mind_mcp.tenant_manager import TenantStorageManager


class FeedbackPlugin(ToolProvider):
    """Exposes feedback signaling as an MCP tool for AI agents and humans."""

    def __init__(self, tenant_manager: TenantStorageManager):
        self.tenant_manager = tenant_manager

    @property
    def name(self) -> str:
        return "feedback_plugin"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="provide_feedback",
                description="Provide relevance feedback on a document to influence future search rankings.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doc_id": {
                            "type": "integer",
                            "description": "The document ID to provide feedback on.",
                        },
                        "signal": {
                            "type": "integer",
                            "description": "Feedback signal from -5 (strongly demote) to +5 (strongly promote).",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Optional reason for the feedback (for audit trail).",
                        },
                        "tombstone": {
                            "type": "boolean",
                            "description": "If true, mark document as tombstoned (excluded from results). If false, un-tombstone.",
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant to apply feedback to (default: 'default').",
                        },
                    },
                    "required": ["doc_id", "signal"],
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name != "provide_feedback":
            raise ValueError(f"Unsupported tool: {name}")

        doc_id = arguments.get("doc_id")
        signal = arguments.get("signal")
        reason = arguments.get("reason")
        tombstone = arguments.get("tombstone")
        tenant_id = arguments.get("tenant_id", "default")

        if doc_id is None or signal is None:
            raise ValueError("doc_id and signal are required")

        if not isinstance(signal, int) or signal < -5 or signal > 5:
            raise ValueError("Signal must be an integer from -5 to +5")

        try:
            adapter = self.tenant_manager.get_adapter(tenant_id)
            result = adapter.update_weight(
                doc_id=doc_id, signal=signal, tombstone=tombstone
            )
            if reason:
                result["reason"] = reason
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except ValueError:
            raise
