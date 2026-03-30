import json
from mcp.types import Tool, TextContent
from team_mind_mcp.server import ToolProvider
from team_mind_mcp.tenant_manager import TenantStorageManager


class TenantPlugin(ToolProvider):
    """Exposes tenant management as MCP tools."""

    def __init__(self, tenant_manager: TenantStorageManager):
        self.tenant_manager = tenant_manager

    @property
    def name(self) -> str:
        return "tenant_plugin"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="register_tenant",
                description="Register a new tenant for data isolation.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tenant_id": {
                            "type": "string",
                            "description": "Unique identifier for the tenant.",
                        },
                    },
                    "required": ["tenant_id"],
                },
            ),
            Tool(
                name="list_tenants",
                description="List all registered tenants.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name == "register_tenant":
            tenant_id = arguments.get("tenant_id")
            if not tenant_id:
                raise ValueError("tenant_id is required")
            self.tenant_manager.create_tenant(tenant_id)
            result = {"status": "registered", "tenant_id": tenant_id}
            return [TextContent(type="text", text=json.dumps(result))]

        elif name == "list_tenants":
            tenants = self.tenant_manager.list_tenants()
            return [TextContent(type="text", text=json.dumps(tenants))]

        else:
            raise ValueError(f"Unsupported tool: {name}")
