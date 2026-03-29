"""Tests for reliability_hint propagation through pipeline and MCP tool (SPEC-007 STORY-004)."""

import pytest
from team_mind_mcp.ingestion import IngestionPipeline, IngestionBundle, IngestionEvent
from team_mind_mcp.ingestion_plugin import IngestionPlugin
from team_mind_mcp.server import IngestProcessor, PluginRegistry


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _TrackingProcessor(IngestProcessor):
    """Processor that records every bundle it receives."""

    def __init__(self, proc_name: str = "tracking_proc"):
        self._name = proc_name
        self.received_bundles: list[IngestionBundle] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def supported_media_types(self) -> list[str] | None:
        return None

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        self.received_bundles.append(bundle)
        return [IngestionEvent(plugin=self.name, record_type="doc", uris=bundle.uris)]


# ---------------------------------------------------------------------------
# AC-001: Pipeline accepts reliability_hint and sets it on the bundle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_ingest_sets_reliability_hint(tmp_path):
    """
    AC-001: pipeline.ingest(uris, reliability_hint=0.8)
    -> bundle.reliability_hint == 0.8
    """
    proc = _TrackingProcessor()
    registry = PluginRegistry()
    registry.register(proc, semantic_types=["*"])

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "doc.md"
    f.write_text("content")

    bundle = await pipeline.ingest([f.as_uri()], reliability_hint=0.8)

    assert bundle is not None
    assert bundle.reliability_hint == 0.8


# ---------------------------------------------------------------------------
# AC-002: Processor bundle also receives reliability_hint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_proc_bundle_receives_reliability_hint(tmp_path):
    """
    AC-002 (gap fix): per-processor bundle also carries reliability_hint
    so processors can read it.
    """
    proc = _TrackingProcessor()
    registry = PluginRegistry()
    registry.register(proc, semantic_types=["*"])

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "doc.md"
    f.write_text("content")

    await pipeline.ingest([f.as_uri()], reliability_hint=0.7)

    assert len(proc.received_bundles) == 1
    assert proc.received_bundles[0].reliability_hint == 0.7


# ---------------------------------------------------------------------------
# AC-004: No hint means None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_ingest_no_hint_is_none(tmp_path):
    """
    AC-004: pipeline.ingest(uris) with no reliability_hint
    -> bundle.reliability_hint is None
    """
    proc = _TrackingProcessor()
    registry = PluginRegistry()
    registry.register(proc, semantic_types=["*"])

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "doc.md"
    f.write_text("content")

    bundle = await pipeline.ingest([f.as_uri()])

    assert bundle is not None
    assert bundle.reliability_hint is None


@pytest.mark.asyncio
async def test_proc_bundle_no_hint_is_none(tmp_path):
    """
    AC-004 (proc bundle): per-processor bundle also has None when not specified.
    """
    proc = _TrackingProcessor()
    registry = PluginRegistry()
    registry.register(proc, semantic_types=["*"])

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "doc.md"
    f.write_text("content")

    await pipeline.ingest([f.as_uri()])

    assert len(proc.received_bundles) == 1
    assert proc.received_bundles[0].reliability_hint is None


# ---------------------------------------------------------------------------
# AC-002: MCP tool ingest_documents accepts reliability_hint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_tool_schema_includes_reliability_hint():
    """
    AC-002: ingest_documents tool schema includes reliability_hint property.
    """
    registry = PluginRegistry()
    plugin = IngestionPlugin(registry)

    tools = plugin.get_tools()
    ingest_tool = next(t for t in tools if t.name == "ingest_documents")

    assert "reliability_hint" in ingest_tool.inputSchema["properties"]
    hint_schema = ingest_tool.inputSchema["properties"]["reliability_hint"]
    assert hint_schema["type"] == "number"


@pytest.mark.asyncio
async def test_mcp_tool_passes_reliability_hint_to_pipeline(tmp_path):
    """
    AC-002: ingest_documents(uris=[...], reliability_hint=0.7)
    -> bundle has reliability_hint=0.7
    """
    proc = _TrackingProcessor()
    registry = PluginRegistry()
    registry.register(proc, semantic_types=["*"])

    plugin = IngestionPlugin(registry)

    f = tmp_path / "doc.md"
    f.write_text("content")

    await plugin.call_tool(
        "ingest_documents",
        {"uris": [f.as_uri()], "reliability_hint": 0.7},
    )

    assert len(proc.received_bundles) == 1
    assert proc.received_bundles[0].reliability_hint == 0.7


# ---------------------------------------------------------------------------
# AC-003: CLI ingest accepts --reliability flag (argparse integration)
# ---------------------------------------------------------------------------


def test_cli_ingest_parser_accepts_reliability_flag():
    """
    AC-003: --reliability flag is accepted by the ingest subcommand parser
    and sets reliability_hint on args.
    """
    import argparse

    # Build the same parser as in cli.py and parse test args
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("targets", nargs="+")
    ingest_parser.add_argument("--recursive", action="store_true", default=True)
    ingest_parser.add_argument("--exclude", type=str, action="append")
    ingest_parser.add_argument(
        "--semantic-type", dest="semantic_types", action="append", metavar="TYPE"
    )
    ingest_parser.add_argument(
        "--reliability", dest="reliability_hint", type=float, default=None
    )

    args = parser.parse_args(["ingest", "/path/to/doc.md", "--reliability", "0.8"])

    assert args.reliability_hint == 0.8


def test_cli_ingest_parser_no_reliability_defaults_to_none():
    """
    AC-003 / AC-004: --reliability absent -> reliability_hint is None.
    """
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("targets", nargs="+")
    ingest_parser.add_argument("--recursive", action="store_true", default=True)
    ingest_parser.add_argument("--exclude", type=str, action="append")
    ingest_parser.add_argument(
        "--semantic-type", dest="semantic_types", action="append", metavar="TYPE"
    )
    ingest_parser.add_argument(
        "--reliability", dest="reliability_hint", type=float, default=None
    )

    args = parser.parse_args(["ingest", "/path/to/doc.md"])

    assert args.reliability_hint is None
