"""
SPEC-002 / STORY-001: Doctype Specification Model
"""

import json
from team_mind_mcp.server import RecordTypeSpec, ToolProvider, IngestProcessor


class _PluginWithDoctypes(ToolProvider):
    @property
    def name(self) -> str:
        return "test_plugin"

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [
            RecordTypeSpec(
                name="note",
                description="A short note.",
                schema={"body": {"type": "string"}},
            )
        ]


class _PluginWithoutDoctypes(ToolProvider):
    @property
    def name(self) -> str:
        return "bare_plugin"


class _ProcessorWithDoctypes(IngestProcessor):
    @property
    def name(self) -> str:
        return "listener_plugin"

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [
            RecordTypeSpec(
                name="event",
                description="An ingested event.",
                schema={"timestamp": {"type": "string"}},
            )
        ]


def test_doctype_spec_fields():
    """
    AC-001: RecordTypeSpec Dataclass Fields
    """
    # Given the RecordTypeSpec dataclass is defined
    # When a new instance is created with name, description, and schema
    spec = RecordTypeSpec(
        name="user_interest",
        description="A user's stated interest",
        schema={"category": {"type": "string"}, "sentiment": {"type": "string"}},
    )

    # Then all three fields are accessible on the instance
    # And the fields match the values provided at construction
    assert spec.name == "user_interest"
    assert spec.description == "A user's stated interest"
    assert spec.schema["category"]["type"] == "string"


def test_plugin_declares_doctypes():
    """
    AC-002: Plugin Declares Doctypes
    """
    # Given a plugin that implements ToolProvider
    plugin = _PluginWithDoctypes()

    # When the plugin overrides the doctypes property
    specs = plugin.record_types

    # Then it returns a list of RecordTypeSpec instances
    assert len(specs) == 1
    assert isinstance(specs[0], RecordTypeSpec)

    # And each spec has a non-empty name and description
    assert specs[0].name == "note"
    assert len(specs[0].description) > 0


def test_doctypes_property_defaults_empty():
    """
    AC-003: Doctypes Property Defaults Empty
    """
    # Given a plugin that does NOT override the doctypes property
    plugin = _PluginWithoutDoctypes()

    # When the doctypes property is accessed
    specs = plugin.record_types

    # Then it returns an empty list
    assert specs == []
    # And no error is raised (implicit — we got here)


def test_schema_is_advisory_dict():
    """
    AC-004: Schema Is Advisory Dict
    """
    # Given a RecordTypeSpec with a schema containing JSON Schema-style field definitions
    spec = RecordTypeSpec(
        name="test",
        description="test",
        schema={"field_a": {"type": "string"}, "field_b": {"type": "integer"}},
    )

    # When the schema is accessed
    # Then it is a plain dict with string keys
    assert isinstance(spec.schema, dict)
    assert all(isinstance(k, str) for k in spec.schema)

    # And it can be serialized to JSON without error
    serialized = json.dumps(spec.schema)
    assert len(serialized) > 0
