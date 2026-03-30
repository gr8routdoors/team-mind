"""
SPEC-010 / STORY-007: FeedbackPlugin with TenantStorageManager
"""

import json
import pytest
from team_mind_mcp.tenant_manager import TenantStorageManager
from team_mind_mcp.feedback import FeedbackPlugin


@pytest.fixture
def tenant_manager(tmp_path):
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()
    yield mgr
    mgr.close()


@pytest.fixture
def doc_id_in_default(tenant_manager):
    """Save a document into the default tenant shard, return its doc_id."""
    adapter = tenant_manager.get_adapter("default")
    doc_id = adapter.save_payload(
        uri="file:///test.md",
        metadata={"text": "hello"},
        vector=[0.1] * 768,
        plugin="test_plugin",
        record_type="test_type",
    )
    return doc_id


@pytest.fixture
def doc_id_in_custom_tenant(tenant_manager):
    """Create a 'custom' tenant, save a document there, return its doc_id."""
    tenant_manager.create_tenant("custom")
    adapter = tenant_manager.get_adapter("custom")
    doc_id = adapter.save_payload(
        uri="file:///custom-test.md",
        metadata={"text": "custom tenant doc"},
        vector=[0.2] * 768,
        plugin="test_plugin",
        record_type="test_type",
    )
    return doc_id


@pytest.mark.asyncio
async def test_feedback_with_tenant_manager_default(tenant_manager, doc_id_in_default):
    """FeedbackPlugin with TenantStorageManager resolves default tenant adapter."""
    plugin = FeedbackPlugin(tenant_manager)

    response = await plugin.call_tool(
        "provide_feedback",
        {"doc_id": doc_id_in_default, "signal": 3, "tenant_id": "default"},
    )
    result = json.loads(response[0].text)

    assert result["usage_score"] == 3.0


@pytest.mark.asyncio
async def test_feedback_resolves_correct_adapter_per_tenant(
    tenant_manager, doc_id_in_default, doc_id_in_custom_tenant
):
    """FeedbackPlugin resolves the correct adapter based on tenant_id argument."""
    plugin = FeedbackPlugin(tenant_manager)

    # Provide feedback on the custom tenant's document
    response = await plugin.call_tool(
        "provide_feedback",
        {"doc_id": doc_id_in_custom_tenant, "signal": 5, "tenant_id": "custom"},
    )
    result = json.loads(response[0].text)
    assert result["usage_score"] == 5.0

    # Provide feedback on the default tenant's document
    response = await plugin.call_tool(
        "provide_feedback",
        {"doc_id": doc_id_in_default, "signal": 1, "tenant_id": "default"},
    )
    result = json.loads(response[0].text)
    assert result["usage_score"] == 1.0


@pytest.mark.asyncio
async def test_feedback_defaults_to_default_tenant_when_no_tenant_id(
    tenant_manager, doc_id_in_default
):
    """FeedbackPlugin defaults to 'default' tenant when tenant_id is not provided."""
    plugin = FeedbackPlugin(tenant_manager)

    # No tenant_id argument — should fall back to "default"
    response = await plugin.call_tool(
        "provide_feedback",
        {"doc_id": doc_id_in_default, "signal": 2},
    )
    result = json.loads(response[0].text)

    assert result["usage_score"] == 2.0


@pytest.mark.asyncio
async def test_feedback_wrong_tenant_raises(tenant_manager):
    """Providing a doc_id that doesn't exist in the target tenant raises ValueError."""
    plugin = FeedbackPlugin(tenant_manager)

    # doc_id 99999 doesn't exist in "default" shard → ValueError
    with pytest.raises(ValueError, match="No weight entry"):
        await plugin.call_tool(
            "provide_feedback",
            {"doc_id": 99999, "signal": 1, "tenant_id": "default"},
        )


def test_feedback_plugin_schema_has_tenant_id(tenant_manager):
    """provide_feedback tool schema includes tenant_id property."""
    plugin = FeedbackPlugin(tenant_manager)
    tools = plugin.get_tools()
    assert len(tools) == 1
    schema = tools[0].inputSchema
    assert "tenant_id" in schema["properties"]
