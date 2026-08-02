"""
SPEC-012 / STORY-001: Mandatory schema and registration guards.

Tests for:
  AC-001: Valid submittable record type registers
  AC-002: Missing/empty schema is rejected
  AC-003: Envelope field in schema is rejected
  AC-004: Duplicate submittable declarer is rejected
  AC-005: Multiple non-submittable producers allowed
  AC-006: embed_source is optional
"""

import pytest

from team_mind_mcp.server import (
    IngestProcessor,
    PluginRegistry,
    RecordTypeSpec,
    ToolProvider,
)


# ---------------------------------------------------------------------------
# Helpers: minimal plugins that declare record types
# ---------------------------------------------------------------------------

_SERVICE_PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "service_name": {"type": "string"},
        "description": {"type": "string"},
    },
    "required": ["service_name"],
}


class _RecordTypePlugin(ToolProvider):
    """A tool provider that declares a configurable set of record types."""

    def __init__(self, plugin_name: str, specs: list[RecordTypeSpec]) -> None:
        self._name = plugin_name
        self._specs = specs

    @property
    def name(self) -> str:
        return self._name

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return self._specs


class _NoteProducer(IngestProcessor):
    """An ingest processor that produces a non-submittable `note` record type."""

    def __init__(self, plugin_name: str) -> None:
        self._name = plugin_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [
            RecordTypeSpec(
                name="note",
                description=f"Note from {self._name}",
                submittable=False,
            )
        ]

    async def process_bundle(self, bundle) -> list:
        return []


# ---------------------------------------------------------------------------
# AC-001: Valid submittable record type registers
# ---------------------------------------------------------------------------


def test_ac001_valid_submittable_record_type_registers():
    """AC-001: A submittable record type with a non-empty schema registers and is retrievable."""
    # Given a plugin declaring `service_profile` with a non-empty schema and submittable=True
    registry = PluginRegistry()
    plugin = _RecordTypePlugin(
        "profile_plugin",
        [
            RecordTypeSpec(
                name="service_profile",
                description="A refined service profile",
                schema=_SERVICE_PROFILE_SCHEMA,
                submittable=True,
            )
        ],
    )

    # When the plugin is registered
    registry.register(plugin)

    # Then registration succeeds and the spec is retrievable via get_submittable_spec
    spec = registry.get_submittable_spec("service_profile")
    assert spec is not None
    assert spec.name == "service_profile"
    assert spec.submittable is True
    assert spec.plugin == "profile_plugin"


# ---------------------------------------------------------------------------
# AC-002: Missing/empty schema is rejected
# ---------------------------------------------------------------------------


def test_ac002_empty_schema_on_submittable_is_rejected():
    """AC-002: An empty schema on a submittable record type raises and does not register the plugin."""
    # Given a plugin declaring a submittable record type whose schema is an empty dict
    registry = PluginRegistry()
    plugin = _RecordTypePlugin(
        "empty_schema_plugin",
        [
            RecordTypeSpec(
                name="service_profile",
                description="Missing its schema",
                schema={},
                submittable=True,
            )
        ],
    )

    # When the plugin is registered
    # Then registration raises, identifying the record type as missing a schema
    with pytest.raises(ValueError, match="service_profile") as exc_info:
        registry.register(plugin)
    assert "schema" in str(exc_info.value).lower()

    # And the plugin is not registered
    assert registry.get_submittable_spec("service_profile") is None
    assert registry.get_record_type_catalog() == []
    assert registry.get_plugin_for_tool("service_profile") is None


# ---------------------------------------------------------------------------
# AC-003: Envelope field in schema is rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "envelope_field",
    ["uri", "id", "plugin", "content_hash", "vector", "tenant"],
)
def test_ac003_envelope_field_in_schema_is_rejected(envelope_field: str):
    """AC-003: A submittable schema declaring any envelope property raises, naming that field."""
    # Given a submittable record type whose schema declares an envelope field as a property
    registry = PluginRegistry()
    plugin = _RecordTypePlugin(
        "envelope_plugin",
        [
            RecordTypeSpec(
                name="service_profile",
                description="Declares an envelope field",
                schema={
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        envelope_field: {"type": "string"},
                    },
                },
                submittable=True,
            )
        ],
    )

    # When the plugin is registered
    # Then registration raises, naming the disallowed envelope field
    with pytest.raises(ValueError, match=envelope_field):
        registry.register(plugin)

    # And the plugin is not registered
    assert registry.get_submittable_spec("service_profile") is None
    assert registry.get_record_type_catalog() == []


# ---------------------------------------------------------------------------
# AC-004: Duplicate submittable declarer is rejected
# ---------------------------------------------------------------------------


def test_ac004_duplicate_submittable_declarer_is_rejected():
    """AC-004: A second plugin declaring the same submittable record type collides; the first stays sole declarer."""
    # Given `service_profile` already registered as submittable by plugin A
    registry = PluginRegistry()
    plugin_a = _RecordTypePlugin(
        "plugin_a",
        [
            RecordTypeSpec(
                name="service_profile",
                description="From A",
                schema=_SERVICE_PROFILE_SCHEMA,
                submittable=True,
            )
        ],
    )
    registry.register(plugin_a)

    plugin_b = _RecordTypePlugin(
        "plugin_b",
        [
            RecordTypeSpec(
                name="service_profile",
                description="From B",
                schema=_SERVICE_PROFILE_SCHEMA,
                submittable=True,
            )
        ],
    )

    # When plugin B registers the same submittable record type name
    # Then registration raises a collision error
    with pytest.raises(ValueError, match="service_profile"):
        registry.register(plugin_b)

    # And plugin A remains the sole declarer
    spec = registry.get_submittable_spec("service_profile")
    assert spec is not None
    assert spec.plugin == "plugin_a"


# ---------------------------------------------------------------------------
# AC-005: Multiple non-submittable producers allowed
# ---------------------------------------------------------------------------


def test_ac005_multiple_non_submittable_producers_allowed():
    """AC-005: Two plugins each producing a non-submittable `note` both register successfully."""
    # Given two plugins each producing a record type named `note` with submittable=False
    registry = PluginRegistry()
    producer_one = _NoteProducer("producer_one")
    producer_two = _NoteProducer("producer_two")

    # When both plugins are registered
    registry.register(producer_one)
    registry.register(producer_two)

    # Then both registrations succeed and both appear as producers of `note`
    producers = registry.get_plugins_for_record_type("note")
    assert sorted(producers) == ["producer_one", "producer_two"]

    # And the single-declarer rule does not apply to non-submittable types
    assert registry.get_submittable_spec("note") is None


# ---------------------------------------------------------------------------
# AC-006: embed_source is optional
# ---------------------------------------------------------------------------


def test_ac006_embed_source_is_optional():
    """AC-006: A submittable record type with embed_source=None registers (metadata-only)."""
    # Given a submittable record type with a valid schema and embed_source=None
    registry = PluginRegistry()
    plugin = _RecordTypePlugin(
        "metadata_only_plugin",
        [
            RecordTypeSpec(
                name="service_profile",
                description="Metadata-only, no vector",
                schema=_SERVICE_PROFILE_SCHEMA,
                submittable=True,
                embed_source=None,
            )
        ],
    )

    # When the plugin is registered
    registry.register(plugin)

    # Then registration succeeds and the spec records no embed source
    spec = registry.get_submittable_spec("service_profile")
    assert spec is not None
    assert spec.embed_source is None
