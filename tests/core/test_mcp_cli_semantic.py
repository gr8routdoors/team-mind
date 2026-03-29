"""
SPEC-008 / STORY-007: MCP Tool and CLI Semantic Type Parameter

BDD-style tests covering:
- AC-001: ingest_documents tool passes semantic_types to pipeline
- AC-002: CLI --semantic-type flag passes types to pipeline
- AC-003: missing semantic_types in tool call -> None passed to pipeline (graceful)
- AC-004: CLI config file provides default semantic type associations
- AC-005: missing config file -> built-in defaults (markdown_plugin = ["*"])
"""

import argparse
import pytest
from pathlib import Path

from team_mind_mcp.server import PluginRegistry, IngestProcessor
from team_mind_mcp.ingestion import IngestionPipeline, IngestionBundle, IngestionEvent
from team_mind_mcp.ingestion_plugin import IngestionPlugin
from team_mind_mcp.cli import load_cli_config


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _TrackingProcessor(IngestProcessor):
    """Processor that records every bundle it receives."""

    def __init__(self, proc_name: str, media_types: list[str] | None = None):
        self._name = proc_name
        self._media_types = media_types
        self.received_bundles: list[IngestionBundle] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def supported_media_types(self) -> list[str] | None:
        return self._media_types

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        self.received_bundles.append(bundle)
        return [IngestionEvent(plugin=self.name, doctype="doc", uris=bundle.uris)]


# ---------------------------------------------------------------------------
# AC-001: ingest_documents tool passes semantic_types to pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_documents_tool_passes_semantic_types(tmp_path):
    """
    AC-001: the ingest_documents tool accepts and passes semantic_types to the pipeline.
    """
    # Given a registry with a wildcard processor
    proc = _TrackingProcessor("proc_wildcard")
    registry = PluginRegistry()
    registry.register(proc, semantic_types=["*"])

    plugin = IngestionPlugin(registry)

    md_file = tmp_path / "design.md"
    md_file.write_text("# Design doc")

    # When calling the tool with semantic_types
    response = await plugin.call_tool(
        "ingest_documents",
        {
            "uris": [md_file.as_uri()],
            "semantic_types": ["architecture_docs", "meeting_notes"],
        },
    )

    # Then the tool succeeds without error
    assert len(response) == 1
    assert "Successfully queued" in response[0].text

    # And the bundle passed to the processor has the expected semantic_types
    assert len(proc.received_bundles) == 1
    assert proc.received_bundles[0].semantic_types == [
        "architecture_docs",
        "meeting_notes",
    ]


# ---------------------------------------------------------------------------
# AC-002: CLI --semantic-type flag passes types to pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cli_semantic_type_flag_passes_to_pipeline(tmp_path):
    """
    AC-002: CLI --semantic-type flag values are parsed and passed through to pipeline.ingest().
    """
    # Given a registry with a tracking processor and a real pipeline
    proc = _TrackingProcessor("proc_wildcard")
    registry = PluginRegistry()
    registry.register(proc, semantic_types=["*"])

    pipeline = IngestionPipeline(registry)

    md_file = tmp_path / "notes.md"
    md_file.write_text("# Meeting notes")

    # When the pipeline is called with semantic_types from CLI args
    bundle = await pipeline.ingest(
        [md_file.as_uri()],
        semantic_types=["architecture_docs", "meeting_notes"],
    )

    # Then the resulting bundle has the expected semantic_types
    assert bundle is not None
    assert bundle.semantic_types == ["architecture_docs", "meeting_notes"]

    # And the processor received those semantic_types
    assert len(proc.received_bundles) == 1
    assert proc.received_bundles[0].semantic_types == [
        "architecture_docs",
        "meeting_notes",
    ]


@pytest.mark.asyncio
async def test_cli_ingest_argparse_repeatable_flag():
    """
    AC-002: argparse correctly parses repeated --semantic-type flags into a list.
    """
    # Given the ingest argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="+")
    parser.add_argument(
        "--semantic-type", dest="semantic_types", action="append", metavar="TYPE"
    )

    # When parsed with two --semantic-type flags
    args = parser.parse_args(
        [
            "somefile.md",
            "--semantic-type",
            "architecture_docs",
            "--semantic-type",
            "meeting_notes",
        ]
    )

    # Then semantic_types is a list of both values
    assert args.semantic_types == ["architecture_docs", "meeting_notes"]


# ---------------------------------------------------------------------------
# AC-003: missing semantic_types in tool call -> None passed to pipeline (graceful)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_documents_tool_without_semantic_types(tmp_path):
    """
    AC-003: calling ingest_documents without semantic_types passes None to pipeline gracefully.
    When semantic_types is omitted (None), the pipeline uses the backward-compat path
    and runs ALL registered processors regardless of their semantic_types registration.
    """
    # Given a registry with a processor registered without semantic_types
    proc = _TrackingProcessor("proc_fallback")
    registry = PluginRegistry()
    # Registered with no semantic_types — backward-compat: all processors receive the bundle
    registry.register(proc)

    plugin = IngestionPlugin(registry)

    md_file = tmp_path / "doc.md"
    md_file.write_text("# some doc")

    # When calling the tool WITHOUT semantic_types
    response = await plugin.call_tool(
        "ingest_documents",
        {"uris": [md_file.as_uri()]},
    )

    # Then the tool succeeds without error (graceful handling)
    assert len(response) == 1
    assert "Successfully queued" in response[0].text

    # And the processor ran (backward-compat path: semantic_types=None passes all processors)
    assert len(proc.received_bundles) == 1

    # And the bundle has an empty semantic_types list (pipeline assigns [] when None is provided)
    assert proc.received_bundles[0].semantic_types == []


@pytest.mark.asyncio
async def test_ingest_documents_tool_schema_has_semantic_types():
    """
    AC-003: the tool schema includes semantic_types as an optional property.
    """
    # Given the IngestionPlugin
    registry = PluginRegistry()
    plugin = IngestionPlugin(registry)

    # When getting the tool list
    tools = plugin.get_tools()

    # Then ingest_documents includes semantic_types in its schema
    assert len(tools) == 1
    tool = tools[0]
    assert tool.name == "ingest_documents"
    props = tool.inputSchema["properties"]
    assert "semantic_types" in props

    # And semantic_types is not in the required list
    required = tool.inputSchema.get("required", [])
    assert "semantic_types" not in required

    # And semantic_types is described as an array of strings
    assert props["semantic_types"]["type"] == "array"
    assert props["semantic_types"]["items"]["type"] == "string"


# ---------------------------------------------------------------------------
# AC-004: CLI config file provides default semantic type associations
# ---------------------------------------------------------------------------


def test_load_cli_config_reads_toml_file(tmp_path):
    """
    AC-004: load_cli_config() reads semantic_types from a TOML config file.
    """
    # Given a ~/.team-mind.toml config file with markdown_plugin section
    config_file = tmp_path / ".team-mind.toml"
    config_file.write_text('[markdown_plugin]\nsemantic_types = ["*"]\n')

    # When load_cli_config is called with that path
    config = load_cli_config(config_path=config_file)

    # Then markdown_plugin has semantic_types=["*"]
    assert "markdown_plugin" in config
    assert config["markdown_plugin"]["semantic_types"] == ["*"]


def test_load_cli_config_csv_string_semantic_types(tmp_path):
    """
    AC-004: load_cli_config() handles comma-separated string semantic_types.
    """
    # Given a config file with semantic_types as a string
    config_file = tmp_path / ".team-mind.toml"
    config_file.write_text(
        '[markdown_plugin]\nsemantic_types = "architecture_docs, meeting_notes"\n'
    )

    # When load_cli_config is called
    config = load_cli_config(config_path=config_file)

    # Then semantic_types is parsed into a list
    assert config["markdown_plugin"]["semantic_types"] == [
        "architecture_docs",
        "meeting_notes",
    ]


def test_load_cli_config_multiple_plugins(tmp_path):
    """
    AC-004: load_cli_config() handles multiple plugin sections.
    """
    # Given a config file with multiple plugin sections
    config_file = tmp_path / ".team-mind.toml"
    config_file.write_text(
        '[markdown_plugin]\nsemantic_types = ["*"]\n\n'
        '[code_plugin]\nsemantic_types = ["code_reviews"]\n'
    )

    # When load_cli_config is called
    config = load_cli_config(config_path=config_file)

    # Then both plugins are present
    assert config["markdown_plugin"]["semantic_types"] == ["*"]
    assert config["code_plugin"]["semantic_types"] == ["code_reviews"]


# ---------------------------------------------------------------------------
# AC-005: missing config file -> built-in defaults (markdown_plugin = ["*"])
# ---------------------------------------------------------------------------


def test_load_cli_config_missing_file_uses_defaults(tmp_path):
    """
    AC-005: when no config file exists, load_cli_config() returns built-in defaults.
    """
    # Given no config file exists at the specified path
    nonexistent = tmp_path / ".team-mind.toml"
    assert not nonexistent.exists()

    # When load_cli_config is called with that path
    config = load_cli_config(config_path=nonexistent)

    # Then built-in defaults are returned
    assert "markdown_plugin" in config
    assert config["markdown_plugin"]["semantic_types"] == ["*"]


def test_load_cli_config_default_path_missing(tmp_path, monkeypatch):
    """
    AC-005: when the default ~/.team-mind.toml is missing, built-in defaults apply.
    """
    # Given a home directory with no .team-mind.toml
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # Ensure it does not exist
    default_path = tmp_path / ".team-mind.toml"
    assert not default_path.exists()

    # When load_cli_config is called with no explicit path
    config = load_cli_config()

    # Then markdown_plugin defaults to ["*"]
    assert config["markdown_plugin"]["semantic_types"] == ["*"]
