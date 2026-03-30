"""
SPEC-010 / STORY-005: Optional Vector Query (Weight-Ranked Retrieval)

Tests for the retrieve_documents MCP tool on DocumentRetrievalPlugin:
  - Default mode (vector) uses vector search
  - Weight mode calls weight-ranked retrieval
  - Weight mode does not require query_text
  - metadata_filters passed through to vector path
  - metadata_filters passed through to weight path
  - Vector mode missing query_text raises an error
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from mcp.types import TextContent
from team_mind_mcp.retrieval import DocumentRetrievalPlugin
from team_mind_mcp.storage import StorageAdapter


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    base_vec = [0.5] * 768

    adapter.save_payload(
        "uri1",
        {"category": "sports"},
        base_vec,
        plugin="p",
        record_type="t",
        initial_score=2.0,
    )
    adapter.save_payload(
        "uri2",
        {"category": "news"},
        base_vec,
        plugin="p",
        record_type="t",
        initial_score=1.0,
    )

    yield adapter
    adapter.close()


@pytest.fixture
def plugin(storage):
    return DocumentRetrievalPlugin(storage)


# ---------------------------------------------------------------------------
# Default mode (vector) uses vector search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_mode_uses_vector_search(plugin, storage):
    """retrieve_documents with no query_mode defaults to 'vector' and calls
    retrieve_by_vector_similarity."""
    with patch.object(
        storage, "retrieve_by_vector_similarity", wraps=storage.retrieve_by_vector_similarity
    ) as mock_vec:
        response = await plugin.call_tool(
            "retrieve_documents",
            {"query_text": "sports news"},
        )
    mock_vec.assert_called_once()
    assert len(response) == 1
    results = json.loads(response[0].text)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_explicit_vector_mode_uses_vector_search(plugin, storage):
    """retrieve_documents with query_mode='vector' calls retrieve_by_vector_similarity."""
    with patch.object(
        storage, "retrieve_by_vector_similarity", wraps=storage.retrieve_by_vector_similarity
    ) as mock_vec:
        response = await plugin.call_tool(
            "retrieve_documents",
            {"query_text": "sports news", "query_mode": "vector"},
        )
    mock_vec.assert_called_once()
    assert len(response) == 1
    results = json.loads(response[0].text)
    assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Weight mode calls weight-ranked retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_weight_mode_calls_retrieve_by_weight(plugin, storage):
    """retrieve_documents with query_mode='weight' calls retrieve_by_weight."""
    with patch.object(
        storage, "retrieve_by_weight", wraps=storage.retrieve_by_weight
    ) as mock_weight, patch.object(
        storage, "retrieve_by_vector_similarity"
    ) as mock_vec:
        response = await plugin.call_tool(
            "retrieve_documents",
            {"query_mode": "weight"},
        )
    mock_weight.assert_called_once()
    mock_vec.assert_not_called()
    assert len(response) == 1
    results = json.loads(response[0].text)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_weight_mode_does_not_require_query_text(plugin, storage):
    """retrieve_documents with query_mode='weight' succeeds without query_text."""
    response = await plugin.call_tool(
        "retrieve_documents",
        {"query_mode": "weight"},
    )
    assert len(response) == 1
    results = json.loads(response[0].text)
    assert isinstance(results, list)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_weight_mode_ignores_query_text_if_provided(plugin, storage):
    """retrieve_documents with query_mode='weight' ignores query_text even if given."""
    with patch.object(
        storage, "retrieve_by_weight", wraps=storage.retrieve_by_weight
    ) as mock_weight, patch.object(
        storage, "retrieve_by_vector_similarity"
    ) as mock_vec:
        response = await plugin.call_tool(
            "retrieve_documents",
            {"query_mode": "weight", "query_text": "this should be ignored"},
        )
    mock_weight.assert_called_once()
    mock_vec.assert_not_called()


# ---------------------------------------------------------------------------
# metadata_filters passed through to vector path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metadata_filters_passed_to_vector_path(plugin, storage):
    """metadata_filters are forwarded to retrieve_by_vector_similarity."""
    with patch.object(
        storage, "retrieve_by_vector_similarity", wraps=storage.retrieve_by_vector_similarity
    ) as mock_vec:
        response = await plugin.call_tool(
            "retrieve_documents",
            {
                "query_text": "sports",
                "query_mode": "vector",
                "metadata_filters": {"category": "sports"},
            },
        )
    call_kwargs = mock_vec.call_args
    assert call_kwargs is not None
    kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
    assert "metadata_filters" in kwargs
    assert kwargs["metadata_filters"] == {"category": "sports"}
    results = json.loads(response[0].text)
    # Only the sports document should be returned
    assert all(r.get("metadata", {}).get("category") == "sports" for r in results)


@pytest.mark.asyncio
async def test_metadata_filters_filter_vector_results(plugin, storage):
    """metadata_filters properly filter results in vector mode."""
    response = await plugin.call_tool(
        "retrieve_documents",
        {
            "query_text": "sports",
            "query_mode": "vector",
            "metadata_filters": {"category": "sports"},
        },
    )
    results = json.loads(response[0].text)
    assert len(results) >= 1
    assert all(r.get("metadata", {}).get("category") == "sports" for r in results)


# ---------------------------------------------------------------------------
# metadata_filters passed through to weight path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metadata_filters_passed_to_weight_path(plugin, storage):
    """metadata_filters are forwarded to retrieve_by_weight."""
    with patch.object(
        storage, "retrieve_by_weight", wraps=storage.retrieve_by_weight
    ) as mock_weight:
        response = await plugin.call_tool(
            "retrieve_documents",
            {
                "query_mode": "weight",
                "metadata_filters": {"category": "news"},
            },
        )
    call_kwargs = mock_weight.call_args
    assert call_kwargs is not None
    kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
    assert "metadata_filters" in kwargs
    assert kwargs["metadata_filters"] == {"category": "news"}


@pytest.mark.asyncio
async def test_metadata_filters_filter_weight_results(plugin, storage):
    """metadata_filters properly filter results in weight mode."""
    response = await plugin.call_tool(
        "retrieve_documents",
        {
            "query_mode": "weight",
            "metadata_filters": {"category": "news"},
        },
    )
    results = json.loads(response[0].text)
    assert len(results) >= 1
    assert all(r.get("metadata", {}).get("category") == "news" for r in results)


# ---------------------------------------------------------------------------
# Vector mode missing query_text raises error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vector_mode_missing_query_text_raises_error(plugin):
    """retrieve_documents with query_mode='vector' and no query_text raises ValueError."""
    with pytest.raises(ValueError, match="query_text"):
        await plugin.call_tool(
            "retrieve_documents",
            {"query_mode": "vector"},
        )


@pytest.mark.asyncio
async def test_default_mode_missing_query_text_raises_error(plugin):
    """retrieve_documents with default mode and no query_text raises ValueError."""
    with pytest.raises(ValueError, match="query_text"):
        await plugin.call_tool(
            "retrieve_documents",
            {},
        )


# ---------------------------------------------------------------------------
# Schema: retrieve_documents tool is in get_tools()
# ---------------------------------------------------------------------------


def test_retrieve_documents_tool_in_schema(plugin):
    """retrieve_documents tool appears in get_tools()."""
    tool_names = [t.name for t in plugin.get_tools()]
    assert "retrieve_documents" in tool_names


def test_retrieve_documents_schema_has_query_mode(plugin):
    """retrieve_documents inputSchema includes query_mode with correct enum."""
    tools = {t.name: t for t in plugin.get_tools()}
    schema = tools["retrieve_documents"].inputSchema
    props = schema["properties"]
    assert "query_mode" in props
    assert props["query_mode"].get("enum") == ["vector", "weight"]


def test_retrieve_documents_schema_has_metadata_filters(plugin):
    """retrieve_documents inputSchema includes metadata_filters as object."""
    tools = {t.name: t for t in plugin.get_tools()}
    schema = tools["retrieve_documents"].inputSchema
    props = schema["properties"]
    assert "metadata_filters" in props
    assert props["metadata_filters"]["type"] == "object"


def test_retrieve_documents_schema_has_query_text(plugin):
    """retrieve_documents inputSchema includes query_text."""
    tools = {t.name: t for t in plugin.get_tools()}
    schema = tools["retrieve_documents"].inputSchema
    props = schema["properties"]
    assert "query_text" in props


def test_retrieve_documents_schema_query_text_not_required(plugin):
    """query_text should not be in required (weight mode doesn't need it)."""
    tools = {t.name: t for t in plugin.get_tools()}
    schema = tools["retrieve_documents"].inputSchema
    required = schema.get("required", [])
    assert "query_text" not in required
