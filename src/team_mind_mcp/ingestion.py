import asyncio
import pathlib
from dataclasses import dataclass, field
from typing import List, Any, Dict
from urllib.parse import urlparse


@dataclass
class IngestionEvent:
    """Structured event describing what an IngestProcessor wrote during ingestion."""

    plugin: str
    doctype: str
    uris: list[str] = field(default_factory=list)
    doc_ids: list[int] = field(default_factory=list)


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
        processor_doctypes: list[str],
    ) -> Dict[str, IngestionContext]:
        """Build IngestionContext per URI by looking up existing docs."""
        contexts: Dict[str, IngestionContext] = {}

        if self.storage is None:
            # No storage = no context (all fresh)
            for uri in uris:
                contexts[uri] = IngestionContext(uri=uri)
            return contexts

        for uri in uris:
            # Check each doctype the processor declares
            all_previous_ids = []
            prev_hash = None
            prev_version = None
            is_update = False

            for dt in processor_doctypes:
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

    async def ingest(self, uris: List[str]) -> IngestionBundle | None:
        """Process URIs in two phases: processors write data, observers react.
        Returns the bundle with collected events, or None if no valid URIs."""
        resolved_uris = ResourceResolver.resolve(uris)

        if not resolved_uris:
            return None  # No-Op

        bundle = IngestionBundle(uris=resolved_uris)

        # Phase 1: Build contexts and broadcast to all processors
        processors = self.registry.get_ingest_processors()
        processor_tasks = []

        for processor in processors:
            doctype_names = [dt.name for dt in processor.doctypes]
            contexts = self._build_contexts(
                resolved_uris,
                processor.name,
                processor.version,
                doctype_names,
            )
            # Attach contexts to bundle for this processor
            bundle.contexts = contexts
            processor_tasks.append(processor.process_bundle(bundle))

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
                    and (ef.doctypes is None or e.doctype in ef.doctypes)
                ]
                if not filtered:
                    continue  # Skip observer entirely if nothing matches

            observer_tasks.append(observer.on_ingest_complete(filtered))

        if observer_tasks:
            await asyncio.gather(*observer_tasks)

        return bundle
