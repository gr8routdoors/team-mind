"""
SPEC-008 / STORY-002: IngestProcessor.supported_media_types + media_types module
"""

import pytest
from team_mind_mcp.server import IngestProcessor
from team_mind_mcp.media_types import (
    MEDIA_TYPE_MAP,
    get_media_type,
    filter_uris_by_media_type,
)


# ---------------------------------------------------------------------------
# Minimal concrete subclasses used across tests
# ---------------------------------------------------------------------------


class _DefaultProcessor(IngestProcessor):
    """A processor that does NOT override supported_media_types."""

    @property
    def name(self) -> str:
        return "default_processor"


class _MarkdownProcessor(IngestProcessor):
    """A processor that restricts itself to markdown and plain-text."""

    @property
    def name(self) -> str:
        return "markdown_processor"

    @property
    def supported_media_types(self) -> list[str] | None:
        return ["text/markdown", "text/plain"]


class _LegacyProcessor(IngestProcessor):
    """Simulates a processor written before STORY-002 (no supported_media_types)."""

    @property
    def name(self) -> str:
        return "legacy_processor"

    async def process_bundle(self, bundle: object) -> list:  # type: ignore[override]
        return []


# ===========================================================================
# AC-001: Default supported_media_types Is None
# ===========================================================================


def test_default_supported_media_types_is_none() -> None:
    """
    AC-001: IngestProcessor subclass that does not override returns None.

    Given an IngestProcessor subclass that does not override supported_media_types
    When supported_media_types is accessed
    Then it returns None
    """
    # Given
    processor = _DefaultProcessor()

    # When
    result = processor.supported_media_types

    # Then
    assert result is None


# ===========================================================================
# AC-002: Processor Declares Media Types
# ===========================================================================


def test_processor_can_declare_supported_media_types() -> None:
    """
    AC-002: IngestProcessor subclass that overrides returns its list.

    Given an IngestProcessor subclass that overrides supported_media_types to
    return ["text/markdown", "text/plain"]
    When supported_media_types is accessed
    Then it returns ["text/markdown", "text/plain"]
    """
    # Given
    processor = _MarkdownProcessor()

    # When
    result = processor.supported_media_types

    # Then
    assert result == ["text/markdown", "text/plain"]


# ===========================================================================
# AC-003: Existing Processors Unaffected (backward compatibility)
# ===========================================================================


def test_legacy_processor_still_instantiates() -> None:
    """
    AC-003: Pre-STORY-002 processor instantiates without error.

    Given an existing IngestProcessor subclass written before this change
    When the processor is instantiated
    Then it continues to function without error
    """
    # Given / When
    processor = _LegacyProcessor()

    # Then — no exception raised, and supported_media_types returns None
    assert processor.supported_media_types is None


@pytest.mark.asyncio
async def test_legacy_processor_process_bundle_works() -> None:
    """
    AC-003: Pre-STORY-002 processor's process_bundle still functions.

    Given a legacy processor
    When process_bundle is called
    Then it returns without error
    """
    # Given
    processor = _LegacyProcessor()

    # When
    result = await processor.process_bundle(object())

    # Then
    assert result == []


# ===========================================================================
# MEDIA_TYPE_MAP contents
# ===========================================================================


def test_media_type_map_required_entries() -> None:
    """MEDIA_TYPE_MAP must contain all required extension → MIME mappings."""
    # Given the required mapping table
    required = {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
        ".java": "text/x-java",
        ".py": "text/x-python",
        ".xml": "application/xml",
        ".yaml": "application/x-yaml",
        ".yml": "application/x-yaml",
        ".csv": "text/csv",
    }

    # When / Then — each entry is present and correct
    for ext, expected_mime in required.items():
        assert ext in MEDIA_TYPE_MAP, f"Missing extension: {ext}"
        assert MEDIA_TYPE_MAP[ext] == expected_mime, (
            f"Wrong MIME for {ext}: {MEDIA_TYPE_MAP[ext]!r} != {expected_mime!r}"
        )


# ===========================================================================
# get_media_type — known extensions
# ===========================================================================


@pytest.mark.parametrize(
    "uri, expected",
    [
        ("file:///home/user/notes.md", "text/markdown"),
        ("file:///home/user/readme.txt", "text/plain"),
        ("file:///src/main/App.java", "text/x-java"),
        ("file:///scripts/run.py", "text/x-python"),
        ("file:///config/settings.json", "application/json"),
        ("file:///data/export.xml", "application/xml"),
        ("file:///config/app.yaml", "application/x-yaml"),
        ("file:///config/app.yml", "application/x-yaml"),
        ("file:///data/report.csv", "text/csv"),
        # HTTP URIs with extensions
        ("http://example.com/docs/guide.md", "text/markdown"),
    ],
)
def test_get_media_type_known_extensions(uri: str, expected: str) -> None:
    """get_media_type resolves known file extensions correctly."""
    # Given a URI with a known extension
    # When get_media_type is called
    result = get_media_type(uri)

    # Then the correct MIME type is returned
    assert result == expected


# ===========================================================================
# get_media_type — unknown / no extension fallback
# ===========================================================================


@pytest.mark.parametrize(
    "uri",
    [
        "file:///home/user/no_extension",
        "http://example.com/endpoint",
        "file:///data/something.unknown",
    ],
)
def test_get_media_type_unknown_returns_octet_stream(uri: str) -> None:
    """get_media_type returns application/octet-stream for unrecognised URIs."""
    # Given a URI with no recognised extension
    # When get_media_type is called
    result = get_media_type(uri)

    # Then the fallback MIME type is returned
    assert result == "application/octet-stream"


# ===========================================================================
# filter_uris_by_media_type — supported is None (pass-through)
# ===========================================================================


def test_filter_uris_none_supported_returns_all() -> None:
    """filter_uris_by_media_type returns all URIs when supported is None."""
    # Given a list of URIs and supported=None
    uris = [
        "file:///a.md",
        "file:///b.txt",
        "file:///c.json",
    ]

    # When filter_uris_by_media_type is called
    result = filter_uris_by_media_type(uris, None)

    # Then the original list is returned unchanged
    assert result == uris


# ===========================================================================
# filter_uris_by_media_type — matching subset
# ===========================================================================


def test_filter_uris_keeps_matching_types() -> None:
    """filter_uris_by_media_type keeps only URIs whose type is in supported."""
    # Given a mixed list and a supported set
    uris = [
        "file:///doc.md",
        "file:///data.json",
        "file:///notes.txt",
        "file:///app.py",
    ]
    supported = ["text/markdown", "text/plain"]

    # When filter_uris_by_media_type is called
    result = filter_uris_by_media_type(uris, supported)

    # Then only markdown and plain-text URIs remain
    assert result == ["file:///doc.md", "file:///notes.txt"]


def test_filter_uris_empty_supported_returns_none() -> None:
    """filter_uris_by_media_type returns empty list when supported is empty."""
    # Given a list of URIs and an empty supported list
    uris = ["file:///doc.md", "file:///data.json"]

    # When filter_uris_by_media_type is called with an empty list
    result = filter_uris_by_media_type(uris, [])

    # Then nothing passes the filter
    assert result == []


def test_filter_uris_preserves_order() -> None:
    """filter_uris_by_media_type preserves the original URI ordering."""
    # Given URIs in a specific order
    uris = [
        "file:///z_doc.md",
        "file:///a_readme.txt",
        "file:///m_doc.md",
    ]
    supported = ["text/markdown", "text/plain"]

    # When filtered
    result = filter_uris_by_media_type(uris, supported)

    # Then order is preserved
    assert result == uris


def test_filter_uris_empty_input() -> None:
    """filter_uris_by_media_type handles an empty URI list gracefully."""
    # Given an empty list
    result = filter_uris_by_media_type([], ["text/markdown"])

    # Then the result is also empty
    assert result == []
