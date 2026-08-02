"""
SPEC-002 / STORY-005: Doctype Discovery MCP Tool
"""

import json
import pytest
from team_mind_mcp.server import (
    RecordTypeSpec,
    ToolProvider,
    IngestProcessor,
    PluginRegistry,
)
from team_mind_mcp.discovery import DoctypeDiscoveryPlugin


class _Alpha(ToolProvider):
    @property
    def name(self) -> str:
        return "alpha"

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [
            RecordTypeSpec(
                name="type_a", description="Alpha A", schema={"f": {"type": "string"}}
            ),
            RecordTypeSpec(
                name="type_b", description="Alpha B", schema={"type": "object"}
            ),
        ]


class _Beta(IngestProcessor):
    @property
    def name(self) -> str:
        return "beta"

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [
            RecordTypeSpec(
                name="type_a", description="Beta A", schema={"type": "object"}
            ),
            RecordTypeSpec(
                name="type_c", description="Beta C", schema={"type": "object"}
            ),
        ]


class _Gamma(ToolProvider):
    @property
    def name(self) -> str:
        return "gamma"

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [
            RecordTypeSpec(
                name="type_d", description="Gamma D", schema={"type": "object"}
            )
        ]


@pytest.fixture
def registry_with_plugins():
    registry = PluginRegistry()
    registry.register(_Alpha())
    registry.register(_Beta())
    registry.register(_Gamma())
    return registry


def test_tool_registered(registry_with_plugins):
    """
    AC-001: Tool Registered
    """
    # Given the DoctypeDiscoveryPlugin is registered with the PluginRegistry
    plugin = DoctypeDiscoveryPlugin(registry_with_plugins)
    registry_with_plugins.register(plugin)

    # When an MCP client requests the list of available tools
    tools = registry_with_plugins.get_all_tools()

    # Then list_record_types appears in the tools list
    tool_names = [t.name for t in tools]
    assert "list_record_types" in tool_names

    # And it includes a description and input schema
    list_tool = next(t for t in tools if t.name == "list_record_types")
    assert list_tool.description
    assert list_tool.inputSchema


@pytest.mark.asyncio
async def test_returns_all_doctypes(registry_with_plugins):
    """
    AC-002: Returns All Doctypes
    """
    plugin = DoctypeDiscoveryPlugin(registry_with_plugins)

    # Given multiple plugins have been registered with various doctypes
    # When list_doctypes is called with no arguments
    response = await plugin.call_tool("list_record_types", {})
    result = json.loads(response[0].text)

    # Then the response includes every doctype from every registered plugin
    assert len(result) == 5  # 2 from alpha + 2 from beta + 1 from gamma


@pytest.mark.asyncio
async def test_filter_by_single_plugin(registry_with_plugins):
    """
    AC-003: Filter by Single Plugin
    """
    plugin = DoctypeDiscoveryPlugin(registry_with_plugins)

    # Given plugins "alpha" and "beta" are registered
    # When list_doctypes is called with plugins=["alpha"]
    response = await plugin.call_tool("list_record_types", {"plugins": ["alpha"]})
    result = json.loads(response[0].text)

    # Then only doctypes from "alpha" are returned
    assert len(result) == 2
    assert all(r["plugin"] == "alpha" for r in result)


@pytest.mark.asyncio
async def test_filter_by_multiple_plugins(registry_with_plugins):
    """
    AC-004: Filter by Multiple Plugins
    """
    plugin = DoctypeDiscoveryPlugin(registry_with_plugins)

    # Given plugins "alpha", "beta", and "gamma" are registered
    # When list_doctypes is called with plugins=["alpha", "gamma"]
    response = await plugin.call_tool(
        "list_record_types", {"plugins": ["alpha", "gamma"]}
    )
    result = json.loads(response[0].text)

    # Then doctypes from both "alpha" and "gamma" are returned
    assert len(result) == 3  # 2 from alpha + 1 from gamma
    # And doctypes from "beta" are excluded
    assert not any(r["plugin"] == "beta" for r in result)


@pytest.mark.asyncio
async def test_filter_by_doctype_names(registry_with_plugins):
    """
    AC-005: Filter by Doctype Names
    """
    plugin = DoctypeDiscoveryPlugin(registry_with_plugins)

    # Given plugins declare doctypes "type_a", "type_b", "type_c", "type_d"
    # When list_doctypes is called with doctypes=["type_a", "type_b"]
    response = await plugin.call_tool(
        "list_record_types", {"record_types": ["type_a", "type_b"]}
    )
    result = json.loads(response[0].text)

    # Then only doctype specs with those names are returned
    names = [r["name"] for r in result]
    assert all(n in ("type_a", "type_b") for n in names)
    # type_a appears from both alpha and beta
    assert len(result) == 3  # alpha:type_a, alpha:type_b, beta:type_a


@pytest.mark.asyncio
async def test_combined_plugin_and_doctype_filters(registry_with_plugins):
    """
    AC-006: Combined Plugin and Doctype Filters
    """
    plugin = DoctypeDiscoveryPlugin(registry_with_plugins)

    # Given multiple plugins each declare multiple doctypes
    # When list_doctypes is called with plugins=["alpha"] and doctypes=["type_a"]
    response = await plugin.call_tool(
        "list_record_types", {"plugins": ["alpha"], "record_types": ["type_a"]}
    )
    result = json.loads(response[0].text)

    # Then only doctypes matching BOTH filters are returned
    assert len(result) == 1
    assert result[0]["plugin"] == "alpha"
    assert result[0]["name"] == "type_a"


@pytest.mark.asyncio
async def test_response_structure(registry_with_plugins):
    """
    AC-007: Response Structure
    """
    plugin = DoctypeDiscoveryPlugin(registry_with_plugins)

    # Given a plugin declares a doctype with name, description, and schema
    # When list_doctypes is called
    response = await plugin.call_tool("list_record_types", {"plugins": ["alpha"]})
    result = json.loads(response[0].text)

    # Then each entry includes plugin, name, description, and schema fields
    for entry in result:
        assert "plugin" in entry
        assert "name" in entry
        assert "description" in entry
        assert "schema" in entry

    # And the response is valid JSON (implicit — json.loads succeeded)


@pytest.mark.asyncio
async def test_no_doctypes_registered():
    """
    AC-008: No Doctypes Registered
    """
    # Given no plugins have declared any doctypes
    empty_registry = PluginRegistry()
    plugin = DoctypeDiscoveryPlugin(empty_registry)

    # When list_doctypes is called
    response = await plugin.call_tool("list_record_types", {})
    result = json.loads(response[0].text)

    # Then an empty list is returned
    assert result == []
    # And no error is raised (implicit)


# --- SPEC-012 / STORY-004: Discovery of submittable contracts ---


class _Catalog(ToolProvider):
    """Declares a submittable record type with a JSON Schema."""

    @property
    def name(self) -> str:
        return "catalog"

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [
            RecordTypeSpec(
                name="service_profile",
                description="A submittable service profile",
                schema={
                    "type": "object",
                    "properties": {"title": {"type": "string"}},
                },
                submittable=True,
            ),
        ]


class _Notes(ToolProvider):
    """Declares a non-submittable record type."""

    @property
    def name(self) -> str:
        return "notes"

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [
            RecordTypeSpec(
                name="scratch_note",
                description="A non-submittable note",
                schema={"type": "object"},
            ),
        ]


@pytest.mark.asyncio
async def test_ac_001_submittable_record_type_exposes_schema():
    """
    STORY-004 AC-001: Submittable record type exposes its schema.
    """
    # Given a submittable record type service_profile with a JSON Schema
    registry = PluginRegistry()
    registry.register(_Catalog())
    plugin = DoctypeDiscoveryPlugin(registry)

    # When list_record_types is called
    response = await plugin.call_tool("list_record_types", {})
    result = json.loads(response[0].text)

    # Then the result includes service_profile with its schema, plugin, description
    entry = next(r for r in result if r["name"] == "service_profile")
    assert entry["schema"] == {
        "type": "object",
        "properties": {"title": {"type": "string"}},
    }
    assert entry["plugin"] == "catalog"
    assert entry["description"] == "A submittable service profile"
    assert entry["submittable"] is True


@pytest.mark.asyncio
async def test_ac_002_submittable_flag_distinguishes_pushable_types():
    """
    STORY-004 AC-002: Submittable flag distinguishes pushable types.
    """
    # Given one submittable and one non-submittable record type are registered
    registry = PluginRegistry()
    registry.register(_Catalog())
    registry.register(_Notes())
    plugin = DoctypeDiscoveryPlugin(registry)

    # When list_record_types is called
    response = await plugin.call_tool("list_record_types", {})
    result = json.loads(response[0].text)

    # Then both are listed and each entry indicates whether it is submittable
    by_name = {r["name"]: r for r in result}
    assert by_name["service_profile"]["submittable"] is True
    assert by_name["scratch_note"]["submittable"] is False

    # And a caller can therefore tell which submit_structured will accept
    submittable_names = {r["name"] for r in result if r["submittable"]}
    assert submittable_names == {"service_profile"}


@pytest.mark.asyncio
async def test_ac_003_existing_plugin_and_record_filters_still_work():
    """
    STORY-004 AC-003: Existing plugin/record filters still work.
    """
    # Given record types from multiple plugins
    registry = PluginRegistry()
    registry.register(_Catalog())
    registry.register(_Notes())
    plugin = DoctypeDiscoveryPlugin(registry)

    # When list_record_types is called with a plugins filter
    response = await plugin.call_tool("list_record_types", {"plugins": ["catalog"]})
    result = json.loads(response[0].text)

    # Then only that plugin's record types are returned
    assert [r["name"] for r in result] == ["service_profile"]
    assert all(r["plugin"] == "catalog" for r in result)

    # And the same holds for a record_types name filter (existing behavior)
    response = await plugin.call_tool(
        "list_record_types", {"record_types": ["scratch_note"]}
    )
    result = json.loads(response[0].text)
    assert [r["name"] for r in result] == ["scratch_note"]
