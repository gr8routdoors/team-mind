import asyncio
import pathlib
from dataclasses import dataclass, field
from typing import List, Any, Dict
from urllib.parse import urlparse

from team_mind_mcp.media_types import filter_uris_by_media_type


@dataclass
class IngestionEvent:
    """Structured event describing what an IngestProcessor wrote during ingestion."""

    plugin: str
    record_type: str
    uris: list[str] = field(default_factory=list)
    doc_ids: list[int] = field(default_factory=list)
    semantic_types: list[str] = field(default_factory=list)


@dataclass
class IngestionContext:
    """Per-URI context provided to processors during ingestion.

    The platform builds this by looking up existing documents for each URI.
    Processors use it to decide: skip, re-process, or wipe-and-replace.
    """

    uri: str
    is_update: bool = False
    content_changed: bool | None = None
    plugin_version_changed: bool = False
    previous_doc_ids: list[int] = field(default_factory=list)
    previous_content_hash: str | None = None
    previous_plugin_version: str | None = None


@dataclass
class IngestionBundle:
    uris: List[str]
    events: List[IngestionEvent] = field(default_factory=list)
    contexts: Dict[str, IngestionContext] = field(default_factory=dict)
    semantic_types: list[str] = field(default_factory=list)


class ResourceResolver:
    """Expands URIs (like directories) into constituent valid file URIs and validates schemas."""

    @staticmethod
    def resolve(uris: List[str]) -> List[str]:
        resolved = []
        for uri in uris:
            parsed = urlparse(uri)
            if parsed.scheme in ("http", "https"):
                resolved.append(uri)
                continue

            if parsed.scheme != "file":
                raise ValueError(f"Unsupported URI schema: {parsed.scheme} in {uri}")

            path = pathlib.Path(parsed.path)
            if not path.exists():
                raise FileNotFoundError(f"URI path does not exist: {uri}")

            if path.is_file():
                resolved.append(uri)
            elif path.is_dir():
                for file_path in path.rglob("*"):
                    if file_path.is_file():
                        resolved.append(file_path.as_uri())
        return resolved


class IngestionPipeline:
    """Two-phase ingestion pipeline with context-aware processing."""

    def __init__(self, registry: Any, storage: Any = None):
        self.registry = registry
        self.storage = storage

    def _build_contexts(
        self,
        uris: List[str],
        processor_name: str,
        processor_version: str,
        processor_record_types: list[str],
    ) -> Dict[str, IngestionContext]:
        """Build IngestionContext per URI by looking up existing docs."""
        contexts: Dict[str, IngestionContext] = {}

        if self.storage is None:
            # No storage = no context (all fresh)
            for uri in uris:
                contexts[uri] = IngestionContext(uri=uri)
            return contexts

        for uri in uris:
            # Check each record type the processor declares
            all_previous_ids = []
            prev_hash = None
            prev_version = None
            is_update = False

            for dt in processor_record_types:
                existing = self.storage.lookup_existing_docs(uri, processor_name, dt)
                if existing:
                    is_update = True
                    all_previous_ids.extend(doc["id"] for doc in existing)
                    # Use the most recent hash/version (last in list)
                    prev_hash = existing[-1].get("content_hash")
                    prev_version = existing[-1].get("plugin_version")

            version_changed = (
                prev_version is not None and prev_version != processor_version
            )

            contexts[uri] = IngestionContext(
                uri=uri,
                is_update=is_update,
                content_changed=None,  # Set by processor after hashing content
                plugin_version_changed=version_changed,
                previous_doc_ids=all_previous_ids,
                previous_content_hash=prev_hash,
                previous_plugin_version=prev_version,
            )

        return contexts

    async def ingest(
        self, uris: List[str], semantic_types: list[str] | None = None
    ) -> IngestionBundle | None:
        """Process URIs in two phases: processors write data, observers react.
        Returns the bundle with collected events, or None if no valid URIs."""
        resolved_uris = ResourceResolver.resolve(uris)

        if not resolved_uris:
            return None  # No-Op

        bundle = IngestionBundle(
            uris=resolved_uris, semantic_types=semantic_types or []
        )

        # Phase 1: Route to matching processors with per-processor bundle isolation.
        # When semantic_types=None (unspecified), treat as [] — only wildcard processors.
        # When semantic_types=[], only wildcard ["*"] processors receive the bundle.
        # When semantic_types specified, route to matching + wildcard processors.
        # Media type filtering always applies: processors only receive supported URIs.
        processor_tasks = []
        processors = self.registry.get_processors_for_semantic_types(
            semantic_types or []
        )

        for processor in processors:
            filtered_uris = filter_uris_by_media_type(
                resolved_uris, processor.supported_media_types
            )
            if not filtered_uris:
                continue
            record_type_names = [dt.name for dt in processor.record_types]
            contexts = self._build_contexts(
                filtered_uris,
                processor.name,
                processor.version,
                record_type_names,
            )
            # Create a per-processor bundle with filtered URIs — no shared state
            proc_bundle = IngestionBundle(
                uris=filtered_uris,
                contexts=contexts,
                semantic_types=bundle.semantic_types,
            )
            processor_tasks.append(processor.process_bundle(proc_bundle))

        all_events: List[IngestionEvent] = []
        if processor_tasks:
            results = await asyncio.gather(*processor_tasks)
            for event_list in results:
                if event_list:
                    all_events.extend(event_list)

        bundle.events = all_events

        # Phase 2: Broadcast collected events to observers (with filtering)
        observer_tasks = []
        for observer in self.registry.get_ingest_observers():
            ef = observer.event_filter
            if ef is None:
                # Fire hose — send all events
                filtered = all_events
            else:
                filtered = [
                    e
                    for e in all_events
                    if (ef.plugins is None or e.plugin in ef.plugins)
                    and (ef.record_types is None or e.record_type in ef.record_types)
                    and (
                        ef.semantic_types is None
                        or any(st in ef.semantic_types for st in e.semantic_types)
                    )
                ]
                if not filtered:
                    continue  # Skip observer entirely if nothing matches

            observer_tasks.append(observer.on_ingest_complete(filtered))

        if observer_tasks:
            await asyncio.gather(*observer_tasks)

        return bundle
