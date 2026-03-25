import asyncio
import pathlib
from dataclasses import dataclass, field
from typing import List, Any
from urllib.parse import urlparse


@dataclass
class IngestionEvent:
    """Structured event describing what an IngestProcessor wrote during ingestion."""

    plugin: str
    doctype: str
    uris: list[str] = field(default_factory=list)
    doc_ids: list[int] = field(default_factory=list)


@dataclass
class IngestionBundle:
    uris: List[str]
    events: List[IngestionEvent] = field(default_factory=list)


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
    """Two-phase ingestion pipeline: process then observe."""

    def __init__(self, registry: Any):
        self.registry = registry

    async def ingest(self, uris: List[str]) -> IngestionBundle | None:
        """Process URIs in two phases: processors write data, observers react.
        Returns the bundle with collected events, or None if no valid URIs."""
        resolved_uris = ResourceResolver.resolve(uris)

        if not resolved_uris:
            return None  # No-Op

        bundle = IngestionBundle(uris=resolved_uris)

        # Phase 1: Broadcast to all processors, collect events
        processor_tasks = []
        for processor in self.registry.get_ingest_processors():
            processor_tasks.append(processor.process_bundle(bundle))

        all_events: List[IngestionEvent] = []
        if processor_tasks:
            results = await asyncio.gather(*processor_tasks)
            for event_list in results:
                if event_list:
                    all_events.extend(event_list)

        bundle.events = all_events

        # Phase 2: Broadcast collected events to all observers
        observer_tasks = []
        for observer in self.registry.get_ingest_observers():
            observer_tasks.append(observer.on_ingest_complete(all_events))

        if observer_tasks:
            await asyncio.gather(*observer_tasks)

        return bundle
