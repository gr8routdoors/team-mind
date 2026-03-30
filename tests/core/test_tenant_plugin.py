"""
SPEC-010 / STORY-007: TenantPlugin MCP tools (register_tenant, list_tenants)
"""

import json
import pytest
from team_mind_mcp.tenant_manager import TenantStorageManager
from team_mind_mcp.tenant_plugin import TenantPlugin
from team_mind_mcp.server import PluginRegistry


@pytest.fixture
def tenant_manager(tmp_path):
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()
    yield mgr
    mgr.close()


def test_tenant_plugin_tools_registered(tenant_manager):
    """TenantPlugin exposes register_tenant and list_tenants tools."""
    plugin = TenantPlugin(tenant_manager)
    registry = PluginRegistry()
    registry.register(plugin)

    tool_names = [t.name for t in registry.get_all_tools()]
    assert "register_tenant" in tool_names
    assert "list_tenants" in tool_names


@pytest.mark.asyncio
async def test_register_tenant_creates_tenant(tenant_manager):
    """register_tenant tool creates a new tenant and returns registered status."""
    plugin = TenantPlugin(tenant_manager)

    response = await plugin.call_tool("register_tenant", {"tenant_id": "acme"})
    result = json.loads(response[0].text)

    assert result["status"] == "registered"
    assert result["tenant_id"] == "acme"

    # Verify tenant is retrievable via the manager
    tenants = tenant_manager.list_tenants()
    tenant_ids = [t["tenant_id"] for t in tenants]
    assert "acme" in tenant_ids


@pytest.mark.asyncio
async def test_register_tenant_is_idempotent(tenant_manager):
    """register_tenant called twice for the same tenant_id succeeds silently."""
    plugin = TenantPlugin(tenant_manager)

    await plugin.call_tool("register_tenant", {"tenant_id": "acme"})
    response = await plugin.call_tool("register_tenant", {"tenant_id": "acme"})
    result = json.loads(response[0].text)

    # Second call still returns registered successfully
    assert result["status"] == "registered"
    assert result["tenant_id"] == "acme"

    # Only one entry for acme in the list
    tenants = tenant_manager.list_tenants()
    acme_entries = [t for t in tenants if t["tenant_id"] == "acme"]
    assert len(acme_entries) == 1


@pytest.mark.asyncio
async def test_list_tenants_returns_all_registered(tenant_manager):
    """list_tenants returns a list including registered tenants."""
    plugin = TenantPlugin(tenant_manager)

    await plugin.call_tool("register_tenant", {"tenant_id": "tenant-a"})
    await plugin.call_tool("register_tenant", {"tenant_id": "tenant-b"})

    response = await plugin.call_tool("list_tenants", {})
    result = json.loads(response[0].text)

    tenant_ids = [t["tenant_id"] for t in result]
    assert "tenant-a" in tenant_ids
    assert "tenant-b" in tenant_ids
    # "default" is auto-created on initialize
    assert "default" in tenant_ids


@pytest.mark.asyncio
async def test_list_tenants_empty_by_default(tmp_path):
    """list_tenants on a freshly initialized manager returns only the default tenant."""
    base = str(tmp_path / "mind2")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    plugin = TenantPlugin(mgr)
    response = await plugin.call_tool("list_tenants", {})
    result = json.loads(response[0].text)

    tenant_ids = [t["tenant_id"] for t in result]
    assert tenant_ids == ["default"]
    mgr.close()
