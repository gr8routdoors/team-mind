"""BDD tests for default_reliability field on RecordTypeSpec (SPEC-007 STORY-002)."""

from team_mind_mcp.server import RecordTypeSpec


def test_ac001_field_defaults_to_none():
    """AC-001: default_reliability defaults to None when not provided."""
    # Given a RecordTypeSpec without default_reliability
    spec = RecordTypeSpec(name="my_type", description="A type")

    # When the field is accessed
    result = spec.default_reliability

    # Then it is None
    assert result is None


def test_ac002_plugin_declares_default():
    """AC-002: default_reliability stores the declared value."""
    # Given a RecordTypeSpec with default_reliability=0.9
    spec = RecordTypeSpec(
        name="code_sig", description="Code signature", default_reliability=0.9
    )

    # When the field is accessed
    result = spec.default_reliability

    # Then it is 0.9
    assert result == 0.9


def test_ac003_backward_compatible():
    """AC-003: existing plugins that don't set default_reliability still register without error."""
    # Given an existing plugin that doesn't set default_reliability
    # When registered (i.e., RecordTypeSpec created without the field)
    try:
        spec = RecordTypeSpec(name="legacy_type", description="A legacy type")
    except TypeError as exc:
        raise AssertionError(
            f"Unexpected error creating RecordTypeSpec without default_reliability: {exc}"
        ) from exc

    # Then no error occurs and default_reliability is None
    assert spec.default_reliability is None
