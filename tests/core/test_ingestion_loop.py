"""
STORY-003: URI-based Bundle Ingestion Loop
"""
import pytest
import os
import pathlib
from team_mind_mcp.server import PluginRegistry, IngestListener
from team_mind_mcp.ingestion import IngestionPipeline, IngestionBundle

class TrackerPlugin(IngestListener):
    """Mock plugin to track received bundles."""
    def __init__(self, name: str):
        self._name = name
        self.received_bundles: list[IngestionBundle] = []
        
    @property
    def name(self) -> str:
        return self._name
        
    async def process_bundle(self, bundle: IngestionBundle) -> None:
        self.received_bundles.append(bundle)

@pytest.mark.asyncio
async def test_ingestion_successful_broadcast(tmp_path):
    """
    AC-001: Successful Broadcast
    """
    # Given a PluginRegistry with two active plugins
    registry = PluginRegistry()
    p1 = TrackerPlugin("p1")
    p2 = TrackerPlugin("p2")
    registry.register(p1)
    registry.register(p2)
    pipeline = IngestionPipeline(registry)
    
    file1 = tmp_path / "a.md"
    file2 = tmp_path / "b.md"
    file1.write_text("File A context")
    file2.write_text("File B context")
    uris = [file1.as_uri(), file2.as_uri()]
    
    # When a user submits a list of valid URIs for ingestion
    bundle = await pipeline.ingest(uris)
    
    # Then a single IngestionBundle is created containing all the URIs
    assert bundle is not None
    assert len(bundle.uris) == 2
    
    # And both plugins receive the .process_bundle() event synchronously or asynchronously
    assert len(p1.received_bundles) == 1
    assert len(p2.received_bundles) == 1
    assert p1.received_bundles[0] == bundle

@pytest.mark.asyncio
async def test_ingestion_unsupported_uris():
    """
    AC-002: Unsupported URIs
    """
    # Given an ingestion request
    registry = PluginRegistry()
    pipeline = IngestionPipeline(registry)
    
    # When a user submits a malformed URI or a schema that no resolver supports
    # Then the ResourceResolver throws a clear validation error
    # And the bundle is marked as failed without crashing the core engine
    with pytest.raises(ValueError, match="Unsupported URI schema: unknown"):
        await pipeline.ingest(["unknown://xyz"])

@pytest.mark.asyncio
async def test_ingestion_empty_bundle_prevention(tmp_path):
    """
    AC-003: Empty Bundle Prevention
    """
    # Given an ingestion request for a directory
    registry = PluginRegistry()
    p1 = TrackerPlugin("p1")
    registry.register(p1)
    pipeline = IngestionPipeline(registry)
    
    empty_dir = tmp_path / "empty_folder"
    empty_dir.mkdir()
    
    # When the directory URI contains no valid or supported actual files
    bundle = await pipeline.ingest([empty_dir.as_uri()])
    
    # Then the ingestion pipeline detects the empty state
    # And immediately returns a successful No-Op without broadcasting an empty bundle to plugins
    assert bundle is None
    assert len(p1.received_bundles) == 0
