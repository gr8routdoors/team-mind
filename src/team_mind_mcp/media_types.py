"""Media type utilities for the team-mind ingestion pipeline.

Public API:
    MEDIA_TYPE_MAP  -- mapping from file extension (with leading dot) to MIME type
    get_media_type  -- resolve a URI to its MIME type string
    filter_uris_by_media_type -- keep only URIs whose media type is in a supported list
"""

from pathlib import Path
from urllib.parse import urlparse

MEDIA_TYPE_MAP: dict[str, str] = {
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

_FALLBACK = "application/octet-stream"


def get_media_type(uri: str) -> str:
    """Return the MIME type for a URI based on its file extension.

    Works for both ``file:///path/to/file.md`` and ``http://host/path/file.md``
    style URIs.  URIs with no recognised extension (including bare HTTP URLs
    without a path extension) return ``"application/octet-stream"``.

    Args:
        uri: The URI whose media type should be determined.

    Returns:
        A MIME type string, e.g. ``"text/markdown"``.
    """
    parsed = urlparse(uri)
    suffix = Path(parsed.path).suffix.lower()
    return MEDIA_TYPE_MAP.get(suffix, _FALLBACK)


def filter_uris_by_media_type(
    uris: list[str],
    supported: list[str] | None,
) -> list[str]:
    """Filter a list of URIs to those whose media type is in *supported*.

    Args:
        uris: The full list of candidate URIs.
        supported: A list of accepted MIME type strings, or ``None`` to accept
            all URIs without filtering.

    Returns:
        The subset of *uris* whose media type appears in *supported*, preserving
        original order.  If *supported* is ``None``, returns *uris* unchanged.
    """
    if supported is None:
        return uris
    return [uri for uri in uris if get_media_type(uri) in supported]
