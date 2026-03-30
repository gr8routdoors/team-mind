"""
SPEC-004 / STORY-003: Provide Feedback MCP Tool
"""

import json
import pytest
from team_mind_mcp.tenant_manager import TenantStorageManager
from team_mind_mcp.feedback import FeedbackPlugin
from team_mind_mcp.server import PluginRegistry


@pytest.fixture
def manager_with_doc(tmp_path):
    """Creates TenantStorageManager with one document in default tenant."""
    mgr = TenantStorageManager(str(tmp_path / "mind"))
    mgr.initialize()
    adapter = mgr.get_adapter("default")
    doc_id = adapter.save_payload(
        uri="file:///test.md",
        metadata={"text": "hello"},
        vector=[0.1] * 768,
        plugin="test_plugin",
        record_type="test_type",
    )
    yield mgr, adapter, doc_id
    mgr.close()


def test_feedback_tool_registered(manager_with_doc):
    """
    AC-001: Tool Registered
    """
    mgr, _, _ = manager_with_doc
    plugin = FeedbackPlugin(mgr)
    registry = PluginRegistry()
    registry.register(plugin)

    tools = registry.get_all_tools()
    tool_names = [t.name for t in tools]
    assert "provide_feedback" in tool_names


@pytest.mark.asyncio
async def test_positive_feedback_increases_score(manager_with_doc):
    """
    AC-002: Positive Feedback Increases Score
    """
    mgr, _, doc_id = manager_with_doc
    plugin = FeedbackPlugin(mgr)

    response = await plugin.call_tool(
        "provide_feedback", {"doc_id": doc_id, "signal": 3}
    )
    result = json.loads(response[0].text)

    assert result["usage_score"] == 3.0


@pytest.mark.asyncio
async def test_negative_feedback_decreases_score(manager_with_doc):
    """
    AC-003: Negative Feedback Decreases Score
    """
    mgr, _, doc_id = manager_with_doc
    plugin = FeedbackPlugin(mgr)

    # First give +2
    await plugin.call_tool("provide_feedback", {"doc_id": doc_id, "signal": 2})
    # Then -2
    response = await plugin.call_tool(
        "provide_feedback", {"doc_id": doc_id, "signal": -2}
    )
    result = json.loads(response[0].text)

    assert result["usage_score"] == 0.0


@pytest.mark.asyncio
async def test_signal_clamped_to_range(manager_with_doc):
    """
    AC-004: Signal Clamped to Range
    """
    mgr, _, doc_id = manager_with_doc
    plugin = FeedbackPlugin(mgr)

    with pytest.raises(ValueError, match="Signal must be an integer from -5 to"):
        await plugin.call_tool("provide_feedback", {"doc_id": doc_id, "signal": 10})


@pytest.mark.asyncio
async def test_nonexistent_doc_errors(manager_with_doc):
    """
    AC-005: Nonexistent Doc ID Errors
    """
    mgr, _, _ = manager_with_doc
    plugin = FeedbackPlugin(mgr)

    with pytest.raises(ValueError, match="No weight entry for doc_id=99999"):
        await plugin.call_tool("provide_feedback", {"doc_id": 99999, "signal": 1})


@pytest.mark.asyncio
async def test_reason_stored(manager_with_doc):
    """
    AC-006: Reason Stored
    """
    mgr, _, doc_id = manager_with_doc
    plugin = FeedbackPlugin(mgr)

    response = await plugin.call_tool(
        "provide_feedback",
        {"doc_id": doc_id, "signal": 1, "reason": "very helpful"},
    )
    result = json.loads(response[0].text)

    assert result["reason"] == "very helpful"
    assert result["usage_score"] == 1.0


@pytest.mark.asyncio
async def test_last_accessed_updated(manager_with_doc):
    """
    AC-007: Last Accessed Updated
    """
    mgr, adapter, doc_id = manager_with_doc
    plugin = FeedbackPlugin(mgr)

    await plugin.call_tool("provide_feedback", {"doc_id": doc_id, "signal": 1})

    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT last_accessed FROM doc_weights WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()

    assert row[0] is not None
