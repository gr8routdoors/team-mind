"""
SPEC-012 / STORY-003: submit_structured endpoint + ingest_structured pipeline.

Batch push: strict per record, best-effort across the batch, with events for
observers. One test per acceptance criterion (AC-001..AC-007), Given/When/Then
inline per the project testing standards. Storage-backed by in-memory SQLite;
a minimal reference submittable plugin exercises the path end to end.
"""

import json

import pytest

from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.server import (
    ToolProvider,
    RecordTypeSpec,
    IngestObserver,
    EventFilter,
    PluginRegistry,
)
from team_mind_mcp.ingestion import IngestionPipeline
from team_mind_mcp.ingestion_plugin import IngestionPlugin


# --- Reference submittable plugin (test fixture, not shipped) ----------------

_SERVICE_PROFILE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "summary": {"type": "string"},
        "reliability_tier": {"type": "string"},
    },
    "required": ["name", "summary"],
}


class _ReferencePlugin(ToolProvider):
    """Declares one submittable record type (`service_profile`) with a JSON
    Schema and an embed source, so the push path can be exercised end to end."""

    @property
    def name(self) -> str:
        return "reference_plugin"

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [
            RecordTypeSpec(
                name="service_profile",
                description="A refined service profile record.",
                schema=_SERVICE_PROFILE_SCHEMA,
                submittable=True,
                embed_source=["summary"],
                default_reliability=0.5,
            )
        ]


class _RecordingObserver(IngestObserver):
    """Observer that records the events it is handed after filtering."""

    def __init__(self, obs_name: str, record_types: list[str] | None = None):
        self._name = obs_name
        self._filter = (
            EventFilter(record_types=record_types) if record_types is not None else None
        )
        self.received: list = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def event_filter(self) -> EventFilter | None:
        return self._filter

    async def on_ingest_complete(self, events: list) -> None:
        self.received.extend(events)


# --- Fixtures ----------------------------------------------------------------


@pytest.fixture
def storage():
    adapter = StorageAdapter(":memory:")
    adapter.initialize()
    yield adapter
    adapter.close()


@pytest.fixture
def registry():
    reg = PluginRegistry()
    reg.register(_ReferencePlugin())
    return reg


@pytest.fixture
def pipeline(registry, storage):
    return IngestionPipeline(registry, storage=storage)


@pytest.fixture
def plugin(registry, storage):
    return IngestionPlugin(registry, storage=storage)


def _count(adapter: StorageAdapter, table: str) -> int:
    return adapter._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _profile(uri: str, name: str, summary: str) -> dict:
    return {
        "record_type": "service_profile",
        "uri": uri,
        "payload": {"name": name, "summary": summary},
    }


# --- AC-001: Batch of valid records is written -------------------------------


@pytest.mark.asyncio
async def test_ac001_batch_of_valid_records_is_written(plugin, storage):
    # Given two records of a submittable type, each valid against its schema
    records = [
        _profile("service://a", "A", "team a payments service"),
        _profile("service://b", "B", "team b billing service"),
    ]

    # When submit_structured is called with both in `records`
    response = await plugin.call_tool("submit_structured", {"records": records})

    # Then both are written and the response lists two successes with doc_ids
    results = json.loads(response[0].text)
    assert len(results) == 2
    assert all(r["status"] == "written" for r in results)
    assert all(isinstance(r["doc_id"], int) for r in results)
    assert {r["uri"] for r in results} == {"service://a", "service://b"}
    assert _count(storage, "documents") == 2


# --- AC-002: One invalid record does not sink the batch ----------------------


@pytest.mark.asyncio
async def test_ac002_one_invalid_record_does_not_sink_the_batch(pipeline, storage):
    # Given three records where the second fails schema validation (no summary)
    records = [
        _profile("service://one", "One", "first"),
        {
            "record_type": "service_profile",
            "uri": "service://two",
            "payload": {"name": "Two"},  # missing required `summary`
        },
        _profile("service://three", "Three", "third"),
    ]

    # When submit_structured is called
    results = await pipeline.ingest_structured(records)

    # Then records 1 and 3 are written and record 2's validation errors reported
    assert results[0]["status"] == "written"
    assert results[1]["status"] == "error"
    assert any("summary" in e for e in results[1]["errors"])
    assert results[2]["status"] == "written"

    # And records 1 and 3 are not rolled back; nothing is written for record 2
    assert _count(storage, "documents") == 2
    assert storage.lookup_existing_docs(
        "service://one", "reference_plugin", "service_profile"
    )
    assert storage.lookup_existing_docs(
        "service://three", "reference_plugin", "service_profile"
    )
    assert not storage.lookup_existing_docs(
        "service://two", "reference_plugin", "service_profile"
    )


# --- AC-003: Observers fire on submitted record_type -------------------------


@pytest.mark.asyncio
async def test_ac003_observers_fire_on_submitted_record_type(registry, storage):
    # Given one observer subscribed to service_profile and one to another type
    matching = _RecordingObserver("matching", record_types=["service_profile"])
    other = _RecordingObserver("other", record_types=["some_other_type"])
    registry.register(matching)
    registry.register(other)
    pipeline = IngestionPipeline(registry, storage=storage)

    # When a valid service_profile record is submitted
    await pipeline.ingest_structured(
        [_profile("service://obs", "Obs", "observe this service")]
    )

    # Then the subscribed observer is called with an IngestionEvent for it
    assert len(matching.received) == 1
    event = matching.received[0]
    assert event.record_type == "service_profile"
    assert event.plugin == "reference_plugin"
    assert len(event.doc_ids) == 1

    # And the observer filtered to a different record type is not called
    assert other.received == []


# --- AC-004: Non-submittable record_type is rejected -------------------------


@pytest.mark.asyncio
async def test_ac004_non_submittable_record_type_is_rejected(pipeline, storage):
    # Given a record whose record_type has no submittable declarer
    records = [
        {
            "record_type": "ghost_type",
            "uri": "service://ghost",
            "payload": {"anything": 1},
        }
    ]

    # When it is submitted
    results = await pipeline.ingest_structured(records)

    # Then that record's result is a "not submittable" error, nothing written
    assert results[0]["status"] == "error"
    assert "not submittable" in " ".join(results[0]["errors"]).lower()
    assert _count(storage, "documents") == 0


# --- AC-005: Single-record list behaves as one write -------------------------


@pytest.mark.asyncio
async def test_ac005_single_record_list_behaves_as_one_write(pipeline, storage):
    # Given a records list with exactly one valid record
    records = [_profile("service://solo", "Solo", "only one service")]

    # When submit_structured is called
    results = await pipeline.ingest_structured(records)

    # Then one document is written and one per-record result is returned
    assert len(results) == 1
    assert results[0]["status"] == "written"
    assert _count(storage, "documents") == 1


# --- AC-006: Re-submitting same uri updates, not duplicates ------------------


@pytest.mark.asyncio
async def test_ac006_resubmitting_same_uri_updates_not_duplicates(pipeline, storage):
    # Given a record with uri = "service://payments" already ingested
    uri = "service://payments"
    first = await pipeline.ingest_structured([_profile(uri, "Payments", "version one")])
    first_id = first[0]["doc_id"]

    # When the same uri/record_type is submitted again with a changed payload
    second = await pipeline.ingest_structured(
        [_profile(uri, "Payments", "version two — changed")]
    )

    # Then the existing document is updated in place, no duplicate created
    assert second[0]["doc_id"] == first_id
    assert _count(storage, "documents") == 1
    row = storage._conn.execute(
        "SELECT metadata FROM documents WHERE id = ?", (first_id,)
    ).fetchone()
    assert json.loads(row[0])["summary"] == "version two — changed"


# --- AC-007: Empty batch is rejected -----------------------------------------


@pytest.mark.asyncio
async def test_ac007_empty_batch_is_rejected(plugin, storage):
    # Given a records list that is empty
    # When submit_structured is called
    response = await plugin.call_tool("submit_structured", {"records": []})

    # Then a clear error stating at least one record is required is returned
    assert len(response) == 1
    assert "at least one record" in response[0].text.lower()

    # And nothing is written
    assert _count(storage, "documents") == 0
