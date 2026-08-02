"""
SPEC-012 / STORY-002: save_metadata_record storage method.

The canonical write path needs a "document + weight, no vector" primitive for
record types with no embed_source. These tests pin that behavior at the storage
layer (in-memory SQLite).
"""

import pytest
from team_mind_mcp.storage import StorageAdapter


@pytest.fixture
def storage():
    adapter = StorageAdapter(":memory:")
    adapter.initialize()
    yield adapter
    adapter.close()


def _count(adapter: StorageAdapter, table: str, where: str, params: tuple) -> int:
    row = adapter._conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {where}", params
    ).fetchone()
    return row[0]


def test_save_metadata_record_inserts_document_and_weight_no_vector(storage):
    # Given a metadata-only record
    metadata = {"name": "Acme", "tier": "gold"}

    # When it is saved via save_metadata_record
    doc_id = storage.save_metadata_record(
        "uri://acme",
        metadata,
        plugin="p",
        record_type="profile",
        initial_score=0.5,
    )

    # Then a documents row and a doc_weights row exist, but NO vec_documents row
    assert isinstance(doc_id, int)
    assert _count(storage, "documents", "id = ?", (doc_id,)) == 1
    assert _count(storage, "doc_weights", "doc_id = ?", (doc_id,)) == 1
    assert _count(storage, "vec_documents", "id = ?", (doc_id,)) == 0


def test_save_metadata_record_seeds_initial_score(storage):
    # Given / When
    doc_id = storage.save_metadata_record(
        "uri://x", {"k": "v"}, plugin="p", record_type="t", initial_score=0.75
    )

    # Then usage_score is seeded, signal_count stays 0
    row = storage._conn.execute(
        "SELECT usage_score, signal_count FROM doc_weights WHERE doc_id = ?",
        (doc_id,),
    ).fetchone()
    assert row[0] == pytest.approx(0.75)
    assert row[1] == 0


def test_save_metadata_record_findable_via_json_extract(storage):
    # Given a saved metadata-only record
    storage.save_metadata_record(
        "uri://y", {"name": "Findable"}, plugin="p", record_type="t"
    )

    # When queried by metadata via json_extract
    row = storage._conn.execute(
        "SELECT uri FROM documents WHERE json_extract(metadata, '$.name') = ?",
        ("Findable",),
    ).fetchone()

    # Then it is retrievable
    assert row is not None
    assert row[0] == "uri://y"
