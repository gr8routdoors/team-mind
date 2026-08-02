"""Shared deterministic embedding + content hashing helpers.

These back both the raw-ingestion path (MarkdownPlugin), the retrieval path,
and the canonical structured write path (``toolkit.write_record``). Keeping a
single implementation guarantees ingest and query share one vector space.
"""

import hashlib


def mock_embed(text: str) -> list[float]:
    """Deterministically generate a 768-d vector from text for MVP."""
    vector = [0.0] * 768
    h = hashlib.md5(text.encode("utf-8")).digest()
    for i in range(min(16, len(h))):
        vector[i] = h[i] / 255.0
    return vector


def content_hash(text: str) -> str:
    """SHA-256 hash of content for idempotent ingestion."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
