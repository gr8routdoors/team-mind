"""
SPEC-008 / STORY-003: Semantic Types on Plugin Registration

Tests for:
  AC-001: Store Semantic Types on Registration
  AC-002: Store Supported Media Types on Registration
  AC-003: Retrieve Registered Semantic Types
  AC-004: Update Semantic Types Without Reinstall
"""

import json
import sqlite3
import pytest
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.server import PluginRegistry, IngestProcessor
from team_mind_mcp.lifecycle import LifecyclePlugin, load_persisted_plugins


# ---------------------------------------------------------------------------
# Minimal IngestProcessor fixture (no module-path loading needed)
# ---------------------------------------------------------------------------


class ArchDocsProcessor(IngestProcessor):
    """Processor that handles architecture docs."""

    @property
    def name(self) -> str:
        return "arch_docs_processor"

    async def process_bundle(self, bundle) -> list:
        return []


class WildcardProcessor(IngestProcessor):
    """Processor registered with wildcard semantic type."""

    @property
    def name(self) -> str:
        return "wildcard_processor"

    async def process_bundle(self, bundle) -> list:
        return []


class UnenabledProcessor(IngestProcessor):
    """Processor registered without semantic types (not enabled)."""

    @property
    def name(self) -> str:
        return "unenabled_processor"

    async def process_bundle(self, bundle) -> list:
        return []


# ---------------------------------------------------------------------------
# AC-001: Store Semantic Types on Registration
# ---------------------------------------------------------------------------


def test_ac001_semantic_types_persisted_as_json(tmp_path):
    """AC-001: semantic_types stored as JSON in registered_plugins row."""
    # Given a plugin registering with semantic_types=["architecture_docs", "meeting_notes"]
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # When the registration is persisted
    adapter.save_plugin_record(
        plugin_name="arch_plugin",
        plugin_type="ingest_processor",
        module_path="team_mind_mcp.test_plugins.SampleIngestProcessor",
        semantic_types=["architecture_docs", "meeting_notes"],
    )

    # Then the registered_plugins row has semantic_types stored as JSON
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT semantic_types FROM registered_plugins WHERE plugin_name = 'arch_plugin'"
        ).fetchone()

    assert row is not None
    assert json.loads(row[0]) == ["architecture_docs", "meeting_notes"]
    adapter.close()


# ---------------------------------------------------------------------------
# AC-002: Store Supported Media Types on Registration
# ---------------------------------------------------------------------------


def test_ac002_supported_media_types_persisted_as_json(tmp_path):
    """AC-002: supported_media_types stored as JSON in registered_plugins row."""
    # Given a plugin registering with supported_media_types=["text/markdown", "text/plain"]
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    # When the registration is persisted
    adapter.save_plugin_record(
        plugin_name="md_plugin",
        plugin_type="ingest_processor",
        module_path="team_mind_mcp.test_plugins.SampleIngestProcessor",
        supported_media_types=["text/markdown", "text/plain"],
    )

    # Then the registered_plugins row has supported_media_types stored as JSON
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT supported_media_types FROM registered_plugins WHERE plugin_name = 'md_plugin'"
        ).fetchone()

    assert row is not None
    assert json.loads(row[0]) == ["text/markdown", "text/plain"]
    adapter.close()


# ---------------------------------------------------------------------------
# AC-003: Retrieve Registered Semantic Types
# ---------------------------------------------------------------------------


def test_ac003_semantic_types_deserialized_on_retrieval(tmp_path):
    """AC-003: semantic_types is deserialized when retrieved via get_enabled_plugin_records."""
    # Given a registered plugin with semantic_types=["architecture_docs"]
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    adapter.save_plugin_record(
        plugin_name="arch_plugin",
        plugin_type="ingest_processor",
        module_path="team_mind_mcp.test_plugins.SampleIngestProcessor",
        semantic_types=["architecture_docs"],
        supported_media_types=["text/markdown"],
    )

    # When the plugin record is retrieved
    records = adapter.get_enabled_plugin_records()

    # Then semantic_types is deserialized to ["architecture_docs"]
    assert len(records) == 1
    assert records[0]["semantic_types"] == ["architecture_docs"]
    assert records[0]["supported_media_types"] == ["text/markdown"]
    adapter.close()


def test_ac003_null_semantic_types_returns_none(tmp_path):
    """AC-003: semantic_types=None is preserved through round-trip."""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    adapter.save_plugin_record(
        plugin_name="plain_plugin",
        plugin_type="ingest_processor",
        module_path="team_mind_mcp.test_plugins.SampleIngestProcessor",
    )

    records = adapter.get_enabled_plugin_records()
    assert len(records) == 1
    assert records[0]["semantic_types"] is None
    assert records[0]["supported_media_types"] is None
    adapter.close()


def test_ac003_registry_stores_semantic_types_per_processor():
    """AC-003: PluginRegistry._processor_semantic_types tracks types per processor."""
    # Given a processor registered with semantic_types
    registry = PluginRegistry()
    proc = ArchDocsProcessor()

    # When registering
    registry.register(proc, semantic_types=["architecture_docs"])

    # Then semantic_types is stored in the registry
    assert registry._processor_semantic_types["arch_docs_processor"] == [
        "architecture_docs"
    ]


def test_ac003_semantic_types_passed_on_startup_recovery(tmp_path):
    """AC-003: load_persisted_plugins passes semantic_types from DB to registry."""
    # Given a persisted plugin record with semantic_types
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    storage.save_plugin_record(
        plugin_name="sample_ingest_processor",
        plugin_type="ingest_processor",
        module_path="team_mind_mcp.test_plugins.SampleIngestProcessor",
        semantic_types=["architecture_docs"],
    )

    # When loading on startup
    registry = PluginRegistry()
    loaded = load_persisted_plugins(storage, registry)

    # Then the registry has the semantic_types stored
    assert loaded == 1
    assert registry._processor_semantic_types.get("sample_ingest_processor") == [
        "architecture_docs"
    ]
    storage.close()


# ---------------------------------------------------------------------------
# AC-004: Update Semantic Types Without Reinstall
# ---------------------------------------------------------------------------


def test_ac004_update_semantic_types_in_place(tmp_path):
    """AC-004: Re-registering a plugin updates semantic_types without uninstall/reinstall."""
    # Given a registered plugin with semantic_types=["architecture_docs"]
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    adapter.save_plugin_record(
        plugin_name="arch_plugin",
        plugin_type="ingest_processor",
        module_path="team_mind_mcp.test_plugins.SampleIngestProcessor",
        semantic_types=["architecture_docs"],
    )

    # When the plugin is re-registered with updated semantic_types
    adapter.save_plugin_record(
        plugin_name="arch_plugin",
        plugin_type="ingest_processor",
        module_path="team_mind_mcp.test_plugins.SampleIngestProcessor",
        semantic_types=["architecture_docs", "design_docs"],
    )

    # Then the semantic_types column is updated
    records = adapter.get_enabled_plugin_records()
    assert len(records) == 1  # No duplicate row created
    assert records[0]["semantic_types"] == ["architecture_docs", "design_docs"]
    adapter.close()


# ---------------------------------------------------------------------------
# Additional: get_processors_for_semantic_types routing logic
# ---------------------------------------------------------------------------


def test_get_processors_for_semantic_types_matches_specific():
    """Processors with matching specific semantic types are returned."""
    registry = PluginRegistry()
    proc = ArchDocsProcessor()
    registry.register(proc, semantic_types=["architecture_docs", "meeting_notes"])

    result = registry.get_processors_for_semantic_types(["architecture_docs"])
    assert proc in result


def test_get_processors_for_semantic_types_wildcard():
    """Processors with ["*"] receive all bundles."""
    registry = PluginRegistry()
    proc = WildcardProcessor()
    registry.register(proc, semantic_types=["*"])

    result = registry.get_processors_for_semantic_types([])
    assert proc in result

    result2 = registry.get_processors_for_semantic_types(["any_type"])
    assert proc in result2


def test_get_processors_for_semantic_types_skips_none():
    """Processors with semantic_types=None are skipped (not enabled for routing)."""
    registry = PluginRegistry()
    proc = UnenabledProcessor()
    registry.register(proc, semantic_types=None)

    result = registry.get_processors_for_semantic_types(["anything"])
    assert proc not in result


def test_unregister_cleans_up_processor_semantic_types():
    """unregister() removes entry from _processor_semantic_types."""
    registry = PluginRegistry()
    proc = ArchDocsProcessor()
    registry.register(proc, semantic_types=["architecture_docs"])

    registry.unregister("arch_docs_processor")

    assert "arch_docs_processor" not in registry._processor_semantic_types


@pytest.mark.asyncio
async def test_register_plugin_tool_includes_semantic_types_in_result(tmp_path):
    """LifecyclePlugin._register returns semantic_types in result JSON."""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    registry = PluginRegistry()
    lifecycle = LifecyclePlugin(registry, storage)
    registry.register(lifecycle)

    response = await lifecycle.call_tool(
        "register_plugin",
        {
            "module_path": "team_mind_mcp.test_plugins.SampleIngestProcessor",
            "semantic_types": ["architecture_docs", "meeting_notes"],
        },
    )
    result = json.loads(response[0].text)

    assert result["status"] == "registered"
    assert result["semantic_types"] == ["architecture_docs", "meeting_notes"]

    # And the registry has the types stored
    assert registry._processor_semantic_types.get("sample_ingest_processor") == [
        "architecture_docs",
        "meeting_notes",
    ]
    storage.close()


@pytest.mark.asyncio
async def test_register_plugin_tool_persists_supported_media_types(tmp_path):
    """LifecyclePlugin._register persists supported_media_types to storage."""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    registry = PluginRegistry()
    lifecycle = LifecyclePlugin(registry, storage)
    registry.register(lifecycle)

    await lifecycle.call_tool(
        "register_plugin",
        {
            "module_path": "team_mind_mcp.test_plugins.SampleIngestProcessor",
            "supported_media_types": ["text/markdown", "text/plain"],
        },
    )

    records = storage.get_enabled_plugin_records()
    proc_record = next(
        (r for r in records if r["plugin_name"] == "sample_ingest_processor"), None
    )
    assert proc_record is not None
    assert proc_record["supported_media_types"] == ["text/markdown", "text/plain"]
    storage.close()
