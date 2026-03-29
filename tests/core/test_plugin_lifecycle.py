"""
SPEC-006 / STORY-003: Plugin State Persistence Table
SPEC-006 / STORY-004: Dynamic Registration MCP Tools
SPEC-006 / STORY-005: Plugin Loader & Startup Recovery
"""

import json
import sqlite3
import pytest
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.server import (
    ToolProvider,
    IngestObserver,
    PluginRegistry,
    EventFilter,
)
from team_mind_mcp.lifecycle import (
    LifecyclePlugin,
    load_persisted_plugins,
)
from mcp.types import TextContent


# --- Test plugins (importable by module path) ---
# These are defined here so PluginLoader can import them via
# "team_mind_mcp.test_plugins.SampleToolPlugin" etc.


class SampleToolPlugin(ToolProvider):
    @property
    def name(self) -> str:
        return "sample_tool"

    def get_tools(self):
        from mcp.types import Tool

        return [
            Tool(
                name="sample_action",
                description="A sample action.",
                inputSchema={"type": "object", "properties": {}},
            )
        ]

    async def call_tool(self, name, arguments):
        return [TextContent(type="text", text="ok")]


class SampleObserverPlugin(IngestObserver):
    def __init__(self):
        self._event_filter_override = None

    @property
    def name(self) -> str:
        return "sample_observer"

    @property
    def event_filter(self) -> EventFilter | None:
        return getattr(self, "_event_filter_override", None)


# --- STORY-003: Plugin State Persistence Table ---


def test_registered_plugins_table_created(tmp_path):
    """AC-001: Table Created on Initialize"""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='registered_plugins'"
        )
        assert cursor.fetchone() is not None
    adapter.close()


def test_save_plugin_record(tmp_path):
    """AC-002: Save Plugin Record"""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    adapter.save_plugin_record(
        plugin_name="test_plugin",
        plugin_type="tool_provider",
        module_path="my_plugins.TestPlugin",
        config={"key": "value"},
        event_filter_json={"plugins": ["a"], "doctypes": ["b"]},
    )

    records = adapter.get_enabled_plugin_records()
    assert len(records) == 1
    assert records[0]["plugin_name"] == "test_plugin"
    assert records[0]["module_path"] == "my_plugins.TestPlugin"
    assert records[0]["config"] == {"key": "value"}
    assert records[0]["event_filter"] == {"plugins": ["a"], "doctypes": ["b"]}
    adapter.close()


def test_retrieve_enabled_plugins(tmp_path):
    """AC-003: Retrieve Enabled Plugins"""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    adapter.save_plugin_record("p1", "tool_provider", "mod.P1")
    adapter.save_plugin_record("p2", "ingest_processor", "mod.P2")
    adapter.save_plugin_record("p3", "ingest_observer", "mod.P3")

    # Disable one
    adapter.disable_plugin_record("p3")

    records = adapter.get_enabled_plugin_records()
    assert len(records) == 2
    names = [r["plugin_name"] for r in records]
    assert "p3" not in names
    adapter.close()


def test_disable_plugin(tmp_path):
    """AC-004: Disable Plugin"""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    adapter.save_plugin_record("p1", "tool_provider", "mod.P1")
    result = adapter.disable_plugin_record("p1")
    assert result is True

    # Still exists but not enabled
    enabled = adapter.get_enabled_plugin_records()
    assert len(enabled) == 0

    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT enabled FROM registered_plugins WHERE plugin_name = 'p1'"
        ).fetchone()
    assert row[0] == 0
    adapter.close()


def test_delete_plugin_record(tmp_path):
    """AC-005: Delete Plugin Record"""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    adapter.save_plugin_record("p1", "tool_provider", "mod.P1")
    result = adapter.delete_plugin_record("p1")
    assert result is True

    records = adapter.get_enabled_plugin_records()
    assert len(records) == 0
    adapter.close()


def test_event_filter_round_trip(tmp_path):
    """AC-006: Event Filter Serialized as JSON"""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    ef = {"plugins": ["java_plugin"], "doctypes": ["code_signature"]}
    adapter.save_plugin_record("p1", "ingest_observer", "mod.P1", event_filter_json=ef)

    records = adapter.get_enabled_plugin_records()
    assert records[0]["event_filter"] == ef
    adapter.close()


# --- STORY-004: Dynamic Registration MCP Tools ---


def test_lifecycle_tools_registered(tmp_path):
    """AC-001: Tools Registered"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    registry = PluginRegistry()
    plugin = LifecyclePlugin(registry, storage)
    registry.register(plugin)

    tools = registry.get_all_tools()
    tool_names = [t.name for t in tools]
    assert "register_plugin" in tool_names
    assert "unregister_plugin" in tool_names
    assert "list_plugins" in tool_names
    storage.close()


@pytest.mark.asyncio
async def test_register_plugin_successfully(tmp_path):
    """AC-002: Register Plugin Successfully"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    registry = PluginRegistry()
    lifecycle = LifecyclePlugin(registry, storage)
    registry.register(lifecycle)

    response = await lifecycle.call_tool(
        "register_plugin",
        {"module_path": "team_mind_mcp.test_plugins.SampleToolPlugin"},
    )
    result = json.loads(response[0].text)

    assert result["status"] == "registered"
    assert result["plugin_name"] == "sample_tool"
    assert "sample_action" in result["tools_registered"]
    storage.close()


@pytest.mark.asyncio
async def test_registered_plugin_tools_visible(tmp_path):
    """AC-003: Registered Plugin Tools Visible"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    registry = PluginRegistry()
    lifecycle = LifecyclePlugin(registry, storage)
    registry.register(lifecycle)

    await lifecycle.call_tool(
        "register_plugin",
        {"module_path": "team_mind_mcp.test_plugins.SampleToolPlugin"},
    )

    tools = registry.get_all_tools()
    tool_names = [t.name for t in tools]
    assert "sample_action" in tool_names
    storage.close()


@pytest.mark.asyncio
async def test_unregister_plugin_removes_tools(tmp_path):
    """AC-004: Unregister Plugin Removes Tools"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    registry = PluginRegistry()
    lifecycle = LifecyclePlugin(registry, storage)
    registry.register(lifecycle)

    await lifecycle.call_tool(
        "register_plugin",
        {"module_path": "team_mind_mcp.test_plugins.SampleToolPlugin"},
    )

    response = await lifecycle.call_tool(
        "unregister_plugin", {"plugin_name": "sample_tool"}
    )
    result = json.loads(response[0].text)

    assert result["status"] == "unregistered"
    assert "sample_action" in result["tools_removed"]

    tools = registry.get_all_tools()
    tool_names = [t.name for t in tools]
    assert "sample_action" not in tool_names
    storage.close()


@pytest.mark.asyncio
async def test_list_plugins(tmp_path):
    """AC-005: List Plugins Returns Roster"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    registry = PluginRegistry()
    lifecycle = LifecyclePlugin(registry, storage)
    registry.register(lifecycle)

    await lifecycle.call_tool(
        "register_plugin",
        {"module_path": "team_mind_mcp.test_plugins.SampleToolPlugin"},
    )

    response = await lifecycle.call_tool("list_plugins", {})
    result = json.loads(response[0].text)

    names = [p["name"] for p in result]
    assert "lifecycle_plugin" in names
    assert "sample_tool" in names
    storage.close()


@pytest.mark.asyncio
async def test_invalid_module_path_errors(tmp_path):
    """AC-006: Invalid Module Path Errors"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    registry = PluginRegistry()
    lifecycle = LifecyclePlugin(registry, storage)

    with pytest.raises(ValueError, match="Could not import module"):
        await lifecycle.call_tool(
            "register_plugin",
            {"module_path": "nonexistent.module.Plugin"},
        )
    storage.close()


@pytest.mark.asyncio
async def test_duplicate_registration_errors(tmp_path):
    """AC-007: Duplicate Registration Errors"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    registry = PluginRegistry()
    lifecycle = LifecyclePlugin(registry, storage)
    registry.register(lifecycle)

    await lifecycle.call_tool(
        "register_plugin",
        {"module_path": "team_mind_mcp.test_plugins.SampleToolPlugin"},
    )

    with pytest.raises(ValueError, match="already registered"):
        await lifecycle.call_tool(
            "register_plugin",
            {"module_path": "team_mind_mcp.test_plugins.SampleToolPlugin"},
        )
    storage.close()


# --- STORY-005: Plugin Loader & Startup Recovery ---


def test_enabled_plugins_loaded_on_startup(tmp_path):
    """AC-001: Enabled Plugins Loaded on Startup"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # Persist two plugin records
    storage.save_plugin_record(
        "sample_tool",
        "tool_provider",
        "team_mind_mcp.test_plugins.SampleToolPlugin",
    )
    storage.save_plugin_record(
        "sample_observer",
        "ingest_observer",
        "team_mind_mcp.test_plugins.SampleObserverPlugin",
    )

    registry = PluginRegistry()
    loaded = load_persisted_plugins(storage, registry)

    assert loaded == 2
    tools = registry.get_all_tools()
    assert any(t.name == "sample_action" for t in tools)
    storage.close()


def test_disabled_plugins_not_loaded(tmp_path):
    """AC-002: Disabled Plugins Not Loaded"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    storage.save_plugin_record(
        "sample_tool",
        "tool_provider",
        "team_mind_mcp.test_plugins.SampleToolPlugin",
    )
    storage.disable_plugin_record("sample_tool")

    registry = PluginRegistry()
    loaded = load_persisted_plugins(storage, registry)

    assert loaded == 0
    storage.close()


def test_failed_load_logged_not_fatal(tmp_path):
    """AC-003: Failed Load Logged Not Fatal"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # One valid, one invalid
    storage.save_plugin_record(
        "sample_tool",
        "tool_provider",
        "team_mind_mcp.test_plugins.SampleToolPlugin",
    )
    storage.save_plugin_record(
        "bad_plugin",
        "tool_provider",
        "nonexistent.module.BadPlugin",
    )

    registry = PluginRegistry()
    loaded = load_persisted_plugins(storage, registry)

    # Valid one loaded, bad one skipped
    assert loaded == 1
    tools = registry.get_all_tools()
    assert any(t.name == "sample_action" for t in tools)
    storage.close()


def test_event_filters_restored(tmp_path):
    """AC-004: Event Filters Restored"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    storage.save_plugin_record(
        "sample_observer",
        "ingest_observer",
        "team_mind_mcp.test_plugins.SampleObserverPlugin",
        event_filter_json={"plugins": ["java_plugin"], "record_types": ["code_sig"]},
    )

    registry = PluginRegistry()
    load_persisted_plugins(storage, registry)

    observers = registry.get_ingest_observers()
    assert len(observers) == 1
    ef = observers[0].event_filter
    assert ef is not None
    assert ef.plugins == ["java_plugin"]
    assert ef.record_types == ["code_sig"]
    storage.close()


def test_core_plugins_unaffected(tmp_path):
    """AC-005: Core Plugins Unaffected"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # Register a "core" plugin first
    from team_mind_mcp.markdown import MarkdownPlugin

    registry = PluginRegistry()
    core_plugin = MarkdownPlugin(storage)
    registry.register(core_plugin)

    # Persist a dynamic plugin
    storage.save_plugin_record(
        "sample_tool",
        "tool_provider",
        "team_mind_mcp.test_plugins.SampleToolPlugin",
    )

    loaded = load_persisted_plugins(storage, registry)
    assert loaded == 1

    # Core plugin still there
    tools = registry.get_all_tools()
    tool_names = [t.name for t in tools]
    assert "semantic_search" in tool_names  # core
    assert "sample_action" in tool_names  # dynamic
    storage.close()
