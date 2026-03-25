"""
SPEC-004 / STORY-003: Provide Feedback MCP Tool
"""

import json
import pytest
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.feedback import FeedbackPlugin
from team_mind_mcp.server import PluginRegistry


@pytest.fixture
def storage_with_doc(tmp_path):
    """Creates storage with one document that has a weight row."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()
    doc_id = adapter.save_payload(
        uri="file:///test.md",
        metadata={"text": "hello"},
        vector=[0.1] * 768,
        plugin="test_plugin",
        doctype="test_type",
    )
    return adapter, doc_id


def test_feedback_tool_registered(storage_with_doc):
    """
    AC-001: Tool Registered
    """
    adapter, _ = storage_with_doc
    plugin = FeedbackPlugin(adapter)
    registry = PluginRegistry()
    registry.register(plugin)

    tools = registry.get_all_tools()
    tool_names = [t.name for t in tools]
    assert "provide_feedback" in tool_names
    adapter.close()


@pytest.mark.asyncio
async def test_positive_feedback_increases_score(storage_with_doc):
    """
    AC-002: Positive Feedback Increases Score
    """
    adapter, doc_id = storage_with_doc
    plugin = FeedbackPlugin(adapter)

    response = await plugin.call_tool(
        "provide_feedback", {"doc_id": doc_id, "signal": 3}
    )
    result = json.loads(response[0].text)

    assert result["usage_score"] == 3.0
    adapter.close()


@pytest.mark.asyncio
async def test_negative_feedback_decreases_score(storage_with_doc):
    """
    AC-003: Negative Feedback Decreases Score
    """
    adapter, doc_id = storage_with_doc
    plugin = FeedbackPlugin(adapter)

    # First give +2
    await plugin.call_tool("provide_feedback", {"doc_id": doc_id, "signal": 2})
    # Then -2
    response = await plugin.call_tool(
        "provide_feedback", {"doc_id": doc_id, "signal": -2}
    )
    result = json.loads(response[0].text)

    assert result["usage_score"] == 0.0
    adapter.close()


@pytest.mark.asyncio
async def test_signal_clamped_to_range(storage_with_doc):
    """
    AC-004: Signal Clamped to Range
    """
    adapter, doc_id = storage_with_doc
    plugin = FeedbackPlugin(adapter)

    with pytest.raises(ValueError, match="Signal must be an integer from -5 to"):
        await plugin.call_tool("provide_feedback", {"doc_id": doc_id, "signal": 10})
    adapter.close()


@pytest.mark.asyncio
async def test_nonexistent_doc_errors(storage_with_doc):
    """
    AC-005: Nonexistent Doc ID Errors
    """
    adapter, _ = storage_with_doc
    plugin = FeedbackPlugin(adapter)

    with pytest.raises(ValueError, match="No weight entry for doc_id=99999"):
        await plugin.call_tool("provide_feedback", {"doc_id": 99999, "signal": 1})
    adapter.close()


@pytest.mark.asyncio
async def test_reason_stored(storage_with_doc):
    """
    AC-006: Reason Stored
    """
    adapter, doc_id = storage_with_doc
    plugin = FeedbackPlugin(adapter)

    response = await plugin.call_tool(
        "provide_feedback",
        {"doc_id": doc_id, "signal": 1, "reason": "very helpful"},
    )
    result = json.loads(response[0].text)

    assert result["reason"] == "very helpful"
    assert result["usage_score"] == 1.0
    adapter.close()


@pytest.mark.asyncio
async def test_last_accessed_updated(storage_with_doc):
    """
    AC-007: Last Accessed Updated
    """
    adapter, doc_id = storage_with_doc
    plugin = FeedbackPlugin(adapter)

    await plugin.call_tool("provide_feedback", {"doc_id": doc_id, "signal": 1})

    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT last_accessed FROM doc_weights WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()

    assert row[0] is not None
    adapter.close()
