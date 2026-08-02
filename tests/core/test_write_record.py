"""
SPEC-012 / STORY-002: Canonical validated write path (write_record toolkit).

One test per acceptance criterion (AC-001..AC-009). Storage-backed by in-memory
SQLite. Given/When/Then structure per project testing standards.
"""

import pytest

from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.server import RecordTypeSpec
from team_mind_mcp.ingestion import IngestionContext
from team_mind_mcp.embedding import mock_embed
from team_mind_mcp.toolkit import write_record, RecordValidationError


@pytest.fixture
def storage():
    adapter = StorageAdapter(":memory:")
    adapter.initialize()
    yield adapter
    adapter.close()


def _count(adapter: StorageAdapter, table: str) -> int:
    return adapter._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _metadata(adapter: StorageAdapter, doc_id: int) -> dict:
    import json

    row = adapter._conn.execute(
        "SELECT metadata FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    return json.loads(row[0])


def _usage_score(adapter: StorageAdapter, doc_id: int) -> float:
    row = adapter._conn.execute(
        "SELECT usage_score FROM doc_weights WHERE doc_id = ?", (doc_id,)
    ).fetchone()
    return row[0]


_DEFAULT_SCHEMA: dict = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
}


def _embed_spec(
    schema: dict | None = None,
    embed_source: list[str] | None = ["summary"],
    default_reliability: float | None = None,
) -> RecordTypeSpec:
    """A record type that (by default) embeds its `summary` field."""
    return RecordTypeSpec(
        name="fact",
        description="A refined fact.",
        schema=schema if schema is not None else _DEFAULT_SCHEMA,
        plugin="test_plugin",
        default_reliability=default_reliability,
        embed_source=embed_source,
    )


# AC-001: Valid payload is written with vector and metadata 1:1
def test_ac001_valid_payload_written_with_vector_and_metadata_1to1(storage):
    # Given a record type with a schema and embed_source = ["summary"]
    spec = _embed_spec()
    payload = {"summary": "the quarterly numbers look strong"}

    # When write_record is called with a payload that satisfies the schema
    doc_id = write_record(
        storage, "fact", payload, "uri://fact-1", "default", spec=spec
    )

    # Then the stored metadata equals the payload exactly (1:1)
    assert isinstance(doc_id, int)
    assert _metadata(storage, doc_id) == payload

    # And a vector was computed from the summary field (doc is vector-retrievable)
    assert _count(storage, "vec_documents") == 1
    results = storage.retrieve_by_vector_similarity(
        mock_embed(payload["summary"]), limit=5
    )
    assert doc_id in [r["id"] for r in results]

    # And a weight row was created
    assert _count(storage, "doc_weights") == 1


# AC-002: Invalid payload writes nothing
def test_ac002_invalid_payload_writes_nothing(storage):
    # Given a record type whose schema requires field `name`
    spec = _embed_spec(
        schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        embed_source=None,
    )

    # When write_record is called with a payload missing `name`
    with pytest.raises(RecordValidationError) as exc:
        write_record(storage, "fact", {"other": 1}, "uri://bad", "default", spec=spec)

    # Then the error lists `name`
    assert any("name" in e for e in exc.value.errors)

    # And nothing was written to documents, vec_documents, or doc_weights
    assert _count(storage, "documents") == 0
    assert _count(storage, "vec_documents") == 0
    assert _count(storage, "doc_weights") == 0


# AC-003: No embed_source => metadata-only, no vector
def test_ac003_no_embed_source_metadata_only_no_vector(storage):
    # Given a record type with a valid schema and embed_source = None
    spec = _embed_spec(
        schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        embed_source=None,
    )
    payload = {"name": "metadata-only-record"}

    # When write_record writes a valid payload
    doc_id = write_record(
        storage, "fact", payload, "uri://meta-1", "default", spec=spec
    )

    # Then a documents row and metadata are stored
    assert _metadata(storage, doc_id) == payload

    # And no vec_documents row is created
    assert _count(storage, "vec_documents") == 0

    # And the record is retrievable via metadata search (json_extract)
    row = storage._conn.execute(
        "SELECT id FROM documents WHERE json_extract(metadata, '$.name') = ?",
        ("metadata-only-record",),
    ).fetchone()
    assert row is not None and row[0] == doc_id


# AC-004: reliability_hint wins the ladder
def test_ac004_reliability_hint_wins(storage):
    # Given a record type with default_reliability = 0.5
    spec = _embed_spec(default_reliability=0.5)

    # When write_record writes with reliability_hint = 0.8
    doc_id = write_record(
        storage,
        "fact",
        {"summary": "hint wins"},
        "uri://r1",
        "default",
        spec=spec,
        reliability_hint=0.8,
    )

    # Then usage_score is seeded to 0.8
    assert _usage_score(storage, doc_id) == pytest.approx(0.8)


# AC-005: default_reliability used when no hint
def test_ac005_default_reliability_used_when_no_hint(storage):
    # Given a record type with default_reliability = 0.5
    spec = _embed_spec(default_reliability=0.5)

    # When write_record writes with reliability_hint = None
    doc_id = write_record(
        storage, "fact", {"summary": "use default"}, "uri://r2", "default", spec=spec
    )

    # Then usage_score is seeded to 0.5
    assert _usage_score(storage, doc_id) == pytest.approx(0.5)


# AC-006: Platform default 0.0 when neither given
def test_ac006_platform_default_zero(storage):
    # Given a record type with default_reliability = None
    spec = _embed_spec(default_reliability=None)

    # When write_record writes with reliability_hint = None
    doc_id = write_record(
        storage, "fact", {"summary": "no seeds"}, "uri://r3", "default", spec=spec
    )

    # Then usage_score is seeded to 0.0
    assert _usage_score(storage, doc_id) == pytest.approx(0.0)


# AC-007: First write inserts
def test_ac007_first_write_inserts(storage):
    # Given no existing document for (uri, plugin, record_type)
    spec = _embed_spec()
    assert _count(storage, "documents") == 0

    # When write_record writes a valid payload
    doc_id = write_record(
        storage, "fact", {"summary": "first"}, "uri://ins-1", "default", spec=spec
    )

    # Then a new document is inserted with a fresh doc_id
    assert isinstance(doc_id, int)
    assert _count(storage, "documents") == 1
    existing = storage.lookup_existing_docs("uri://ins-1", "test_plugin", "fact")
    assert len(existing) == 1 and existing[0]["id"] == doc_id


# AC-008: Re-write with changed payload updates in place
def test_ac008_rewrite_updates_in_place(storage):
    # Given an existing document for the same uri and record_type
    spec = _embed_spec()
    first_id = write_record(
        storage,
        "fact",
        {"summary": "version one"},
        "uri://upd-1",
        "default",
        spec=spec,
        reliability_hint=0.7,
    )
    # Apply a feedback signal so we can prove the weight row survives the update
    storage.update_weight(first_id, signal=3)
    signal_count_before = storage._conn.execute(
        "SELECT signal_count FROM doc_weights WHERE doc_id = ?", (first_id,)
    ).fetchone()[0]

    # When write_record writes a payload with a different content hash
    ctx = IngestionContext(
        uri="uri://upd-1", is_update=True, previous_doc_ids=[first_id]
    )
    second_id = write_record(
        storage,
        "fact",
        {"summary": "version two — changed"},
        "uri://upd-1",
        "default",
        spec=spec,
        context=ctx,
    )

    # Then the existing document is updated in place (same doc_id, no duplicate)
    assert second_id == first_id
    assert _count(storage, "documents") == 1
    assert _metadata(storage, first_id) == {"summary": "version two — changed"}

    # And its doc_id and weight row are preserved (not duplicated / not reset)
    assert _count(storage, "doc_weights") == 1
    signal_count_after = storage._conn.execute(
        "SELECT signal_count FROM doc_weights WHERE doc_id = ?", (first_id,)
    ).fetchone()[0]
    assert signal_count_after == signal_count_before


# AC-009: Payload key `uri` stays namespaced under metadata
def test_ac009_payload_uri_key_stays_namespaced(storage):
    # Given a schema that permits a payload property literally named `uri`
    spec = _embed_spec(
        schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "uri": {"type": "string"},
            },
            "required": ["summary"],
        },
    )
    payload = {"summary": "has a uri key", "uri": "x"}

    # When write_record writes a payload containing uri = "x"
    doc_id = write_record(
        storage, "fact", payload, "uri://envelope", "default", spec=spec
    )

    # Then the value is stored at metadata.uri
    meta_uri = storage._conn.execute(
        "SELECT json_extract(metadata, '$.uri') FROM documents WHERE id = ?",
        (doc_id,),
    ).fetchone()[0]
    assert meta_uri == "x"

    # And it does not collide with the envelope uri column
    envelope_uri = storage._conn.execute(
        "SELECT uri FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()[0]
    assert envelope_uri == "uri://envelope"
