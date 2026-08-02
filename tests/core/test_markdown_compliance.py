"""
SPEC-012 / STORY-005: MarkdownPlugin compliance.

The existing plugin is brought under mandatory validation without losing
SPEC-011 parent/segment behavior. One test per acceptance criterion, with
inline Given/When/Then structure (project testing standards).

Note: AC-004 (the mandatory-schema guard applied to ALL record types) lives in
``test_submittable_registration.py`` alongside the other registration-guard ACs.
"""

import pytest

from team_mind_mcp.markdown import MarkdownPlugin
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.ingestion import IngestionBundle
from team_mind_mcp.toolkit import write_record, RecordValidationError


@pytest.fixture
def storage(tmp_path):
    adapter = StorageAdapter(str(tmp_path / "compliance.db"))
    adapter.initialize()
    yield adapter
    adapter.close()


def _rows(adapter: StorageAdapter, sql: str, params: tuple = ()) -> list:
    return adapter._conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------------------
# AC-001: Markdown ingestion still yields parent + segments (SPEC-011 parity)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ac001_ingestion_yields_parent_and_segments(storage, tmp_path):
    # Given a markdown file with two paragraphs
    md_file = tmp_path / "doc.md"
    md_file.write_text("Paragraph one.\n\nParagraph two.")
    plugin = MarkdownPlugin(storage)

    # When MarkdownPlugin processes it via the raw path
    bundle = IngestionBundle(uris=[md_file.as_uri()], storage=storage)
    await plugin.process_bundle(bundle)

    # Then exactly one markdown_source parent is written (no parent_id)
    parents = _rows(
        storage,
        "SELECT id FROM documents WHERE record_type = 'markdown_source'",
    )
    assert len(parents) == 1
    parent_id = parents[0][0]
    assert (
        _rows(storage, "SELECT parent_id FROM documents WHERE id = ?", (parent_id,))[0][
            0
        ]
        is None
    )

    # And one markdown_chunk segment per paragraph, each linked by parent_id
    segments = _rows(
        storage,
        "SELECT id, parent_id FROM documents WHERE record_type = 'markdown_chunk' ORDER BY id",
    )
    assert len(segments) == 2
    assert all(seg[1] == parent_id for seg in segments)

    # And SPEC-011 parity holds: the parent has NO vector and NO weight row
    assert (
        _rows(storage, "SELECT 1 FROM vec_documents WHERE id = ?", (parent_id,)) == []
    )
    assert (
        _rows(storage, "SELECT 1 FROM doc_weights WHERE doc_id = ?", (parent_id,)) == []
    )

    # And each segment has BOTH a vector and a weight row
    for seg_id, _ in segments:
        assert (
            _rows(storage, "SELECT 1 FROM vec_documents WHERE id = ?", (seg_id,)) != []
        )
        assert (
            _rows(storage, "SELECT 1 FROM doc_weights WHERE doc_id = ?", (seg_id,))
            != []
        )


# ---------------------------------------------------------------------------
# AC-002: Chunk metadata is payload-only (no envelope fields such as `plugin`)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ac002_chunk_metadata_is_payload_only(storage, tmp_path):
    # Given a markdown file processed by the migrated MarkdownPlugin
    md_file = tmp_path / "notes.md"
    md_file.write_text("Only paragraph.")
    plugin = MarkdownPlugin(storage)

    # When a chunk is written
    bundle = IngestionBundle(uris=[md_file.as_uri()], storage=storage)
    await plugin.process_bundle(bundle)

    # Then its metadata contains only payload fields (the chunk text)
    import json

    meta_json = _rows(
        storage,
        "SELECT metadata FROM documents WHERE record_type = 'markdown_chunk'",
    )[0][0]
    metadata = json.loads(meta_json)
    assert set(metadata.keys()) == {"chunk"}
    assert metadata["chunk"] == "Only paragraph."

    # And it does NOT contain the envelope field `plugin`
    assert "plugin" not in metadata


# ---------------------------------------------------------------------------
# AC-003: Markdown chunk writes go through validation (same path as any record)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ac003_chunk_writes_go_through_validation(storage):
    # Given the plugin's real markdown_chunk record type spec
    plugin = MarkdownPlugin(storage)
    chunk_spec = next(rt for rt in plugin.record_types if rt.name == "markdown_chunk")

    # When a chunk payload that violates the schema (chunk must be a string) is
    # written through the same canonical path the plugin uses (write_record)
    with pytest.raises(RecordValidationError) as exc:
        write_record(
            storage,
            "markdown_chunk",
            {"chunk": 123},  # wrong type
            "file:///bad.md#chunk-0",
            "default",
            spec=chunk_spec,
        )

    # Then the write is rejected by the validation path and nothing is written
    assert exc.value.record_type == "markdown_chunk"
    assert _rows(storage, "SELECT COUNT(*) FROM documents")[0][0] == 0
    assert _rows(storage, "SELECT COUNT(*) FROM vec_documents")[0][0] == 0
