"""
SPEC-007 / STORY-005: MarkdownPlugin Reliability Integration

Tests that MarkdownPlugin resolves reliability_hint and default_reliability,
passing the final value as initial_score to save_payload.
"""

import pytest
from team_mind_mcp.markdown import MarkdownPlugin
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.ingestion import IngestionBundle
from team_mind_mcp.server import RecordTypeSpec


@pytest.fixture
def storage(tmp_path):
    """Real StorageAdapter backed by a temp SQLite db."""
    db_path = tmp_path / "test_reliability.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()
    yield adapter
    adapter.close()


def _get_usage_scores(adapter: StorageAdapter) -> list[float]:
    """Fetch all usage_score values from doc_weights."""
    rows = adapter._conn.execute(
        "SELECT usage_score FROM doc_weights ORDER BY doc_id"
    ).fetchall()
    return [row[0] for row in rows]


@pytest.mark.asyncio
async def test_ac001_uses_hint_when_provided(storage, tmp_path):
    """
    AC-001: Uses Hint When Provided

    Given a bundle with reliability_hint=0.8
    When MarkdownPlugin processes the bundle
    Then saved documents have usage_score=0.8
    """
    # Given
    md_file = tmp_path / "doc.md"
    md_file.write_text("Paragraph one.\n\nParagraph two.")
    plugin = MarkdownPlugin(storage)

    bundle = IngestionBundle(
        uris=[md_file.as_uri()],
        reliability_hint=0.8,
        storage=storage,
    )

    # When
    await plugin.process_bundle(bundle)

    # Then
    scores = _get_usage_scores(storage)
    assert len(scores) == 2
    for score in scores:
        assert score == pytest.approx(0.8), f"Expected usage_score=0.8, got {score}"


@pytest.mark.asyncio
async def test_ac002_falls_back_to_default(tmp_path):
    """
    AC-002: Falls Back to Default

    Given a bundle with reliability_hint=None and MarkdownPlugin declares default_reliability=0.5
    When MarkdownPlugin processes the bundle
    Then saved documents have usage_score=0.5
    """
    # Given — subclass that sets default_reliability on its record type
    class MarkdownPluginWithDefault(MarkdownPlugin):
        @property
        def record_types(self) -> list[RecordTypeSpec]:
            return [
                RecordTypeSpec(
                    name="markdown_chunk",
                    description="Chunk from markdown document.",
                    default_reliability=0.5,
                )
            ]

    db_path = tmp_path / "test_default.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    md_file = tmp_path / "doc.md"
    md_file.write_text("Hello world.\n\nSecond para.")
    plugin = MarkdownPluginWithDefault(storage)

    bundle = IngestionBundle(
        uris=[md_file.as_uri()],
        reliability_hint=None,
        storage=storage,
    )

    # When
    await plugin.process_bundle(bundle)

    # Then
    rows = storage._conn.execute(
        "SELECT usage_score FROM doc_weights ORDER BY doc_id"
    ).fetchall()
    scores = [row[0] for row in rows]
    assert len(scores) == 2
    for score in scores:
        assert score == pytest.approx(0.5), f"Expected usage_score=0.5, got {score}"

    storage.close()


@pytest.mark.asyncio
async def test_ac003_no_hint_no_default_uses_zero(storage, tmp_path):
    """
    AC-003: No Hint No Default Uses Zero

    Given a bundle with reliability_hint=None and a plugin with default_reliability=None
    When the plugin processes the bundle
    Then saved documents have usage_score=0.0
    """
    # Given — standard MarkdownPlugin has default_reliability=None
    md_file = tmp_path / "doc.md"
    md_file.write_text("Only one paragraph.")
    plugin = MarkdownPlugin(storage)

    # Confirm no default_reliability set on the markdown_chunk record type (index 1)
    chunk_rt = next(rt for rt in plugin.record_types if rt.name == "markdown_chunk")
    assert chunk_rt.default_reliability is None

    bundle = IngestionBundle(
        uris=[md_file.as_uri()],
        reliability_hint=None,
        storage=storage,
    )

    # When
    await plugin.process_bundle(bundle)

    # Then
    scores = _get_usage_scores(storage)
    assert len(scores) == 1
    assert scores[0] == pytest.approx(0.0), f"Expected usage_score=0.0, got {scores[0]}"


@pytest.mark.asyncio
async def test_ac004_plugin_can_override_hint(tmp_path):
    """
    AC-004: Plugin Can Override Hint

    Given a plugin that always sets initial_score to 0.95 regardless of hint
    When it processes a bundle with reliability_hint=0.3
    Then saved documents have usage_score=0.95 (plugin has last word)
    """
    # Given — custom plugin that ignores the bundle hint and always uses 0.95
    class AlwaysHighReliabilityPlugin(MarkdownPlugin):
        async def process_bundle(self, bundle: IngestionBundle):
            import urllib.request
            from team_mind_mcp.markdown import _mock_embed, _content_hash
            from team_mind_mcp.media_types import get_media_type
            from team_mind_mcp.ingestion import IngestionEvent

            processed_uris = []
            doc_ids = []
            semantic_type = ",".join(bundle.semantic_types)
            forced_score = 0.95  # always override

            for uri in bundle.uris:
                try:
                    if uri.startswith("file://"):
                        req = urllib.request.urlopen(uri)
                        content = req.read().decode("utf-8")
                    else:
                        continue
                except Exception:
                    continue

                current_hash = _content_hash(content)
                processed_uris.append(uri)
                media_type = get_media_type(uri)
                chunks = [p.strip() for p in content.split("\n\n") if p.strip()]

                for chunk in chunks:
                    vector = _mock_embed(chunk)
                    metadata = {"chunk": chunk, "plugin": self.name}
                    doc_id = self.storage.save_payload(
                        uri,
                        metadata,
                        vector,
                        plugin=self.name,
                        record_type="markdown_chunk",
                        content_hash=current_hash,
                        plugin_version=self.version,
                        semantic_type=semantic_type,
                        media_type=media_type,
                        initial_score=forced_score,
                    )
                    doc_ids.append(doc_id)

            if processed_uris:
                return [
                    IngestionEvent(
                        plugin=self.name,
                        record_type="markdown_chunk",
                        uris=processed_uris,
                        doc_ids=doc_ids,
                        semantic_types=bundle.semantic_types,
                    )
                ]
            return []

    db_path = tmp_path / "test_override.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    md_file = tmp_path / "doc.md"
    md_file.write_text("Single paragraph content.")
    plugin = AlwaysHighReliabilityPlugin(storage)

    bundle = IngestionBundle(
        uris=[md_file.as_uri()],
        reliability_hint=0.3,
    )

    # When
    await plugin.process_bundle(bundle)

    # Then
    rows = storage._conn.execute(
        "SELECT usage_score FROM doc_weights ORDER BY doc_id"
    ).fetchall()
    scores = [row[0] for row in rows]
    assert len(scores) == 1
    assert scores[0] == pytest.approx(0.95), (
        f"Expected usage_score=0.95 (plugin override), got {scores[0]}"
    )

    storage.close()
