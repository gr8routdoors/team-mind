"""
SPEC-008 / STORY-005: Pipeline Semantic Type Routing

BDD-style tests verifying that ingest() routes bundles based on semantic types
and filters URIs by each processor's supported media types.
"""

import pytest
from team_mind_mcp.server import IngestProcessor, PluginRegistry
from team_mind_mcp.ingestion import IngestionPipeline, IngestionBundle, IngestionEvent


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _TrackingProcessor(IngestProcessor):
    """Processor that records every bundle it receives."""

    def __init__(
        self,
        proc_name: str,
        media_types: list[str] | None = None,
    ):
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
# AC-001: Routes to Processors Registered for Semantic Type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_routes_to_matching_processor_only(tmp_path):
    """
    AC-001: bundle with specific semantic_type routes to matching processor only.
    """
    # Given processor A registered for "architecture_docs"
    # and processor B registered for "meeting_notes"
    proc_a = _TrackingProcessor("proc_a")
    proc_b = _TrackingProcessor("proc_b")

    registry = PluginRegistry()
    registry.register(proc_a, semantic_types=["architecture_docs"])
    registry.register(proc_b, semantic_types=["meeting_notes"])

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "design.md"
    f.write_text("design content")

    # When a bundle with semantic_types=["architecture_docs"] is ingested
    bundle = await pipeline.ingest([f.as_uri()], semantic_types=["architecture_docs"])

    # Then only processor A receives the bundle
    assert bundle is not None
    assert len(proc_a.received_bundles) == 1
    assert len(proc_b.received_bundles) == 0


# ---------------------------------------------------------------------------
# AC-002: Processor with registered_types=None receives nothing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_processor_with_none_semantic_types_skipped(tmp_path):
    """
    AC-002: processor with registered_types=None (available but not enabled) receives nothing.
    """
    # Given a processor registered without semantic_types (None)
    proc = _TrackingProcessor("proc_unregistered")

    registry = PluginRegistry()
    registry.register(proc, semantic_types=None)

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "notes.md"
    f.write_text("some notes")

    # When a bundle with any semantic_type is ingested
    bundle = await pipeline.ingest([f.as_uri()], semantic_types=["architecture_docs"])

    # Then the processor with None registration receives nothing
    assert bundle is not None
    assert len(proc.received_bundles) == 0


# ---------------------------------------------------------------------------
# AC-003: Empty semantic_types routes to wildcard processors only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_semantic_types_routes_to_wildcard_only(tmp_path):
    """
    AC-003: empty semantic_types -> only wildcard ["*"] processors receive the bundle.
    """
    # Given processor A registered for "architecture_docs"
    # and processor B registered for "*" (wildcard)
    proc_a = _TrackingProcessor("proc_specific")
    proc_wildcard = _TrackingProcessor("proc_wildcard")

    registry = PluginRegistry()
    registry.register(proc_a, semantic_types=["architecture_docs"])
    registry.register(proc_wildcard, semantic_types=["*"])

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "doc.md"
    f.write_text("content")

    # When a bundle with semantic_types=[] is ingested
    bundle = await pipeline.ingest([f.as_uri()], semantic_types=[])

    # Then only the wildcard processor receives the bundle
    assert bundle is not None
    assert len(proc_wildcard.received_bundles) == 1
    # And the specific processor does not receive the bundle
    assert len(proc_a.received_bundles) == 0


# ---------------------------------------------------------------------------
# AC-004: Media type filtering limits URIs passed to processor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_media_type_filtering_limits_uris(tmp_path):
    """
    AC-004: media type filtering limits URIs passed to processor.
    """
    # Given a processor with supported_media_types=["text/markdown"]
    proc = _TrackingProcessor("md_processor", media_types=["text/markdown"])

    registry = PluginRegistry()
    registry.register(proc, semantic_types=["*"])

    pipeline = IngestionPipeline(registry)

    md_file = tmp_path / "doc.md"
    md_file.write_text("markdown content")
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("text content")
    py_file = tmp_path / "script.py"
    py_file.write_text("print('hello')")

    # When a bundle containing .md, .txt, and .py files is ingested
    bundle = await pipeline.ingest(
        [md_file.as_uri(), txt_file.as_uri(), py_file.as_uri()],
        semantic_types=["architecture_docs"],
    )

    # Then only the .md file is included in the filtered bundle passed to the processor
    assert bundle is not None
    assert len(proc.received_bundles) == 1
    received_uris = proc.received_bundles[0].uris
    assert len(received_uris) == 1
    assert received_uris[0] == md_file.as_uri()


# ---------------------------------------------------------------------------
# AC-005: Processor receives empty filtered list -> skipped entirely
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_processor_skipped_when_filtered_uris_empty(tmp_path):
    """
    AC-005: processor receives empty filtered list -> skipped entirely.
    """
    # Given a processor that only accepts "application/json"
    proc = _TrackingProcessor("json_processor", media_types=["application/json"])

    registry = PluginRegistry()
    registry.register(proc, semantic_types=["*"])

    pipeline = IngestionPipeline(registry)

    md_file = tmp_path / "doc.md"
    md_file.write_text("markdown content")

    # When a bundle containing only a .md file is ingested
    bundle = await pipeline.ingest([md_file.as_uri()], semantic_types=["*"])

    # Then the processor is skipped (no bundle received)
    assert bundle is not None
    assert len(proc.received_bundles) == 0


# ---------------------------------------------------------------------------
# AC-006: Wildcard processor receives bundle regardless of semantic types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wildcard_processor_receives_all_bundles(tmp_path):
    """
    AC-006: wildcard processor receives bundle regardless of semantic types.
    """
    # Given a processor registered for ["*"]
    proc_wildcard = _TrackingProcessor("proc_wildcard")
    proc_specific = _TrackingProcessor("proc_arch")

    registry = PluginRegistry()
    registry.register(proc_wildcard, semantic_types=["*"])
    registry.register(proc_specific, semantic_types=["architecture_docs"])

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "spec.md"
    f.write_text("spec content")

    # When a bundle with semantic_types=["architecture_docs"] is ingested
    bundle = await pipeline.ingest([f.as_uri()], semantic_types=["architecture_docs"])

    # Then the wildcard processor receives the bundle alongside the specific processor
    assert bundle is not None
    assert len(proc_wildcard.received_bundles) == 1
    assert len(proc_specific.received_bundles) == 1


# ---------------------------------------------------------------------------
# AC-007: Multiple semantic types in bundle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_semantic_types_routes_to_all_matching(tmp_path):
    """
    AC-007: multiple semantic types in bundle routes to all matching processors.
    """
    # Given processor A registered for "architecture_docs"
    # and processor B registered for "meeting_notes"
    proc_a = _TrackingProcessor("proc_arch")
    proc_b = _TrackingProcessor("proc_meetings")
    proc_c = _TrackingProcessor("proc_unrelated")

    registry = PluginRegistry()
    registry.register(proc_a, semantic_types=["architecture_docs"])
    registry.register(proc_b, semantic_types=["meeting_notes"])
    registry.register(proc_c, semantic_types=["code_reviews"])

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "doc.md"
    f.write_text("content")

    # When a bundle with semantic_types=["architecture_docs", "meeting_notes"] is ingested
    bundle = await pipeline.ingest(
        [f.as_uri()], semantic_types=["architecture_docs", "meeting_notes"]
    )

    # Then both processor A and processor B receive the bundle
    assert bundle is not None
    assert len(proc_a.received_bundles) == 1
    assert len(proc_b.received_bundles) == 1
    # And processor C (unrelated type) does not
    assert len(proc_c.received_bundles) == 0


# ---------------------------------------------------------------------------
# AC-008: Bundle semantic_types preserved in returned bundle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bundle_preserves_semantic_types(tmp_path):
    """
    The returned bundle carries the semantic_types from the ingest call.
    """
    # Given a wildcard processor
    proc = _TrackingProcessor("proc_wildcard")

    registry = PluginRegistry()
    registry.register(proc, semantic_types=["*"])

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "doc.md"
    f.write_text("content")

    # When ingested with specific semantic_types
    bundle = await pipeline.ingest([f.as_uri()], semantic_types=["architecture_docs"])

    # Then the returned bundle has those semantic_types
    assert bundle is not None
    assert bundle.semantic_types == ["architecture_docs"]


# ---------------------------------------------------------------------------
# AC-009: No matching processors returns empty events without error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_matching_processors_returns_empty_events(tmp_path):
    """
    AC-005 (no-match variant): no processors registered for unknown_type ->
    pipeline completes without error and no events are produced.
    """
    # Given no processors registered for "unknown_type"
    proc = _TrackingProcessor("proc_arch")

    registry = PluginRegistry()
    registry.register(proc, semantic_types=["architecture_docs"])

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "doc.md"
    f.write_text("content")

    # When a bundle with semantic_types=["unknown_type"] is ingested
    bundle = await pipeline.ingest([f.as_uri()], semantic_types=["unknown_type"])

    # Then the pipeline completes without error
    assert bundle is not None
    # And no events are produced
    assert bundle.events == []
    assert len(proc.received_bundles) == 0


# ---------------------------------------------------------------------------
# semantic_types=None behaves as empty list (wildcard-only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_none_semantic_types_routes_to_wildcard_only(tmp_path):
    """
    When semantic_types=None (not provided), behaves like [] — wildcard only.
    No blind broadcast to all registered processors.
    """
    # Given a specific processor and a wildcard processor
    proc_specific = _TrackingProcessor("proc_arch")
    proc_wildcard = _TrackingProcessor("proc_wildcard")

    registry = PluginRegistry()
    registry.register(proc_specific, semantic_types=["architecture_docs"])
    registry.register(proc_wildcard, semantic_types=["*"])

    pipeline = IngestionPipeline(registry)

    f = tmp_path / "doc.md"
    f.write_text("content")

    # When semantic_types is not provided (None)
    bundle = await pipeline.ingest([f.as_uri()])

    # Then only the wildcard processor receives the bundle
    assert bundle is not None
    assert len(proc_wildcard.received_bundles) == 1
    assert len(proc_specific.received_bundles) == 0
