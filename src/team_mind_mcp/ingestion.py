import asyncio
import pathlib
from dataclasses import dataclass
from typing import List, Any
from urllib.parse import urlparse

@dataclass
class IngestionBundle:
    uris: List[str]

class ResourceResolver:
    """Expands URIs (like directories) into constituent valid file URIs and validates schemas."""
    
    @staticmethod
    def resolve(uris: List[str]) -> List[str]:
        resolved = []
        for uri in uris:
            parsed = urlparse(uri)
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
    """Event-driven ingestion pipeline orchestrating URI parsing into bundles."""
    def __init__(self, registry: Any):
        self.registry = registry
        
    async def ingest(self, uris: List[str]) -> IngestionBundle | None:
        """Process URIs, expand them, and broadcast bundle to all plugins. 
        Returns the bundle or None if no valid files were resolved (No-Op)."""
        resolved_uris = ResourceResolver.resolve(uris)
        
        if not resolved_uris:
            return None # No-Op
            
        bundle = IngestionBundle(uris=resolved_uris)
        
        # Broadcast to all listeners concurrently
        aws = []
        for listener in self.registry.get_ingest_listeners():
            aws.append(listener.process_bundle(bundle))
                
        if aws:
            await asyncio.gather(*aws)
            
        return bundle
