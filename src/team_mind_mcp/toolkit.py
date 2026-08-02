"""Canonical validated write path for records (SPEC-012, STORY-002).

Every record — pushed externally via ``submit_structured`` or written by a
plugin refining raw input — goes through :func:`write_record`. It is the single
write choke point: it validates the payload against the record type's JSON
Schema, embeds (when an ``embed_source`` is declared), hashes, seeds reliability,
and writes idempotently. This prevents write-sprawl (the framework writing one
way, plugins another) and makes schema enforcement universal and free.
"""

import json
from typing import Any

from jsonschema import Draft202012Validator

from team_mind_mcp.embedding import content_hash, mock_embed
from team_mind_mcp.ingestion import IngestionContext
from team_mind_mcp.server import RecordTypeSpec


class RecordValidationError(ValueError):
    """Raised when a payload fails JSON Schema validation. Nothing is written.

    ``errors`` carries the structured error strings from :func:`validate_record`.
    """

    def __init__(self, record_type: str, errors: list[str]):
        self.record_type = record_type
        self.errors = errors
        super().__init__(
            f"Record '{record_type}' failed validation: " + "; ".join(errors)
        )


def validate_record(payload: dict, schema: dict) -> list[str]:
    """Validate ``payload`` against a JSON Schema.

    Returns an empty list when valid, else a stable, sorted list of structured
    error strings (``"<path>: <message>"``, or just the message for root errors).
    """
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda e: (list(e.absolute_path), e.message),
    )
    formatted: list[str] = []
    for err in errors:
        path = ".".join(str(p) for p in err.absolute_path)
        formatted.append(f"{path}: {err.message}" if path else err.message)
    return formatted


def _resolve_field_path(payload: dict, path: str) -> Any:
    """Resolve a dotted field path against the payload; None if any part misses."""
    current: Any = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _build_embed_text(payload: dict, embed_source: list[str]) -> str:
    """Concatenate the text at each embed_source field path (in order)."""
    parts: list[str] = []
    for path in embed_source:
        value = _resolve_field_path(payload, path)
        if value is not None:
            parts.append(value if isinstance(value, str) else str(value))
    return " ".join(parts)


def _canonical_json(payload: dict) -> str:
    """Stable JSON serialization for hashing (key order independent)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _resolve_existing_doc_id(
    storage: Any,
    uri: str,
    plugin: str,
    record_type: str,
    context: IngestionContext | None,
) -> int | None:
    """Find the doc_id to update, if any (context first, storage fallback)."""
    if context is not None and context.previous_doc_ids:
        return context.previous_doc_ids[0]
    existing = storage.lookup_existing_docs(uri, plugin, record_type)
    if existing:
        return existing[0]["id"]
    return None


def write_record(
    storage: Any,
    record_type: str,
    payload: dict,
    uri: str,
    tenant_id: str,
    *,
    spec: RecordTypeSpec,
    reliability_hint: float | None = None,
    context: IngestionContext | None = None,
    parent_id: int | None = None,
) -> int:
    """Canonical record write. Owns, in order:

    1. VALIDATION (always): validate ``payload`` against ``spec.schema``; on
       failure raise :class:`RecordValidationError` and write NOTHING.
    2. Embedding: if ``spec.embed_source`` is set, embed the concatenated text
       from those field paths (768-d); else no vector.
    3. content_hash over the canonical payload.
    4. Reliability ladder: ``reliability_hint`` → ``spec.default_reliability`` → 0.0.
    5. Idempotency: INSERT a new doc, or UPDATE the existing one in place
       (preserving doc_id + weight row), based on ``context`` / storage lookup.
    6. Store the payload 1:1 as ``metadata``. Return the doc_id.
    """
    # 1. VALIDATION — always, before any write.
    errors = validate_record(payload, spec.schema)
    if errors:
        raise RecordValidationError(record_type, errors)

    # 2. Embedding (optional, driven by the declared embed_source).
    vector: list[float] | None = None
    if spec.embed_source:
        vector = mock_embed(_build_embed_text(payload, spec.embed_source))

    # 3. content_hash over the payload.
    payload_hash = content_hash(_canonical_json(payload))

    # 4. Reliability seeding ladder (SPEC-007).
    if reliability_hint is not None:
        initial_score = reliability_hint
    elif spec.default_reliability is not None:
        initial_score = spec.default_reliability
    else:
        initial_score = 0.0

    # 5. Idempotency — update in place when a prior doc exists, else insert.
    existing_id = _resolve_existing_doc_id(
        storage, uri, spec.plugin, record_type, context
    )

    if existing_id is not None:
        if vector is not None:
            storage.update_payload(
                existing_id, payload, vector, content_hash=payload_hash
            )
        else:
            storage.update_metadata(existing_id, payload, content_hash=payload_hash)
        return existing_id

    # 6. INSERT — payload stored 1:1 as metadata; envelope fields on the row.
    if vector is not None:
        return storage.save_payload(
            uri,
            payload,
            vector,
            plugin=spec.plugin,
            record_type=record_type,
            parent_id=parent_id,
            content_hash=payload_hash,
            initial_score=initial_score,
        )
    return storage.save_metadata_record(
        uri,
        payload,
        plugin=spec.plugin,
        record_type=record_type,
        parent_id=parent_id,
        content_hash=payload_hash,
        initial_score=initial_score,
    )
