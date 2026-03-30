"""
SPEC-010 / STORY-003: Ingestion Pipeline Routing

Tests for:
- IngestionBundle defaults (tenant_id="default", storage=None)
- IngestionEvent has tenant_id field
- ingest() with tenant_id routes to correct shard
- ingest() auto-creates unknown tenant (no pre-registration needed)
- bundle.storage is set to the tenant-specific adapter during processing
- Documents from different tenants are isolated (same URI in different tenants)
- MarkdownPlugin uses bundle.storage correctly
"""

import pathlib
import pytest
import asyncio

from team_mind_mcp.ingestion import IngestionBundle, IngestionEvent, IngestionPipeline
from team_mind_mcp.tenant_manager import TenantStorageManager
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.markdown import MarkdownPlugin


# ---------------------------------------------------------------------------
# AC-001: IngestionBundle defaults
# ---------------------------------------------------------------------------


def test_bundle_has_tenant_id_field_defaulting_to_default():
    """IngestionBundle.tenant_id defaults to 'default'."""
    bundle = IngestionBundle(uris=["file:///doc.md"])
    assert bundle.tenant_id == "default"


def test_bundle_tenant_id_can_be_set():
    """IngestionBundle.tenant_id can be set to a custom value."""
    bundle = IngestionBundle(uris=["file:///doc.md"], tenant_id="user-123")
    assert bundle.tenant_id == "user-123"


def test_bundle_has_storage_field_defaulting_to_none():
    """IngestionBundle.storage defaults to None."""
    bundle = IngestionBundle(uris=["file:///doc.md"])
    assert bundle.storage is None


def test_bundle_storage_can_be_set(tmp_path):
    """IngestionBundle.storage can be set to a StorageAdapter."""
    db_path = str(tmp_path / "test.sqlite")
    adapter = StorageAdapter(db_path)
    adapter.initialize()
    bundle = IngestionBundle(uris=["file:///doc.md"], storage=adapter)
    assert bundle.storage is adapter
    adapter.close()


# ---------------------------------------------------------------------------
# AC-002: IngestionEvent has tenant_id field
# ---------------------------------------------------------------------------


def test_event_has_tenant_id_field_defaulting_to_default():
    """IngestionEvent.tenant_id defaults to 'default'."""
    event = IngestionEvent(plugin="test_plugin", record_type="doc")
    assert event.tenant_id == "default"


def test_event_tenant_id_can_be_set():
    """IngestionEvent.tenant_id can be set to a custom value."""
    event = IngestionEvent(plugin="test_plugin", record_type="doc", tenant_id="user-456")
    assert event.tenant_id == "user-456"


# ---------------------------------------------------------------------------
# AC-003: ingest() with tenant_id routes to correct shard
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_manager(tmp_path):
    mgr = TenantStorageManager(str(tmp_path / "mind"))
    mgr.initialize()
    yield mgr
    mgr.close()


@pytest.fixture
def simple_registry():
    """A minimal registry with no processors and no observers."""
    class _EmptyRegistry:
        def get_processors_for_semantic_types(self, semantic_types):
            return []
        def get_ingest_observers(self):
            return []
    return _EmptyRegistry()


@pytest.mark.asyncio
async def test_ingest_routes_to_specified_tenant(tmp_path, tenant_manager, simple_registry):
    """ingest() with tenant_id routes to that tenant's shard."""
    tenant_manager.create_tenant("user-123")
    pipeline = IngestionPipeline(simple_registry, tenant_manager=tenant_manager)

    md_file = tmp_path / "doc.md"
    md_file.write_text("# Hello")

    bundle = await pipeline.ingest([md_file.as_uri()], tenant_id="user-123")
    assert bundle is not None
    assert bundle.tenant_id == "user-123"


@pytest.mark.asyncio
async def test_ingest_default_tenant_id(tmp_path, tenant_manager, simple_registry):
    """ingest() defaults to tenant_id='default'."""
    pipeline = IngestionPipeline(simple_registry, tenant_manager=tenant_manager)

    md_file = tmp_path / "doc.md"
    md_file.write_text("# Hello")

    bundle = await pipeline.ingest([md_file.as_uri()])
    assert bundle is not None
    assert bundle.tenant_id == "default"


# ---------------------------------------------------------------------------
# AC-004: ingest() auto-creates unknown tenant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_auto_creates_unknown_tenant(tmp_path, tenant_manager, simple_registry):
    """ingest() auto-creates a tenant that was never pre-registered."""
    pipeline = IngestionPipeline(simple_registry, tenant_manager=tenant_manager)

    md_file = tmp_path / "doc.md"
    md_file.write_text("# Hello")

    # "new-user" was never created — pipeline should create it automatically
    bundle = await pipeline.ingest([md_file.as_uri()], tenant_id="new-user")
    assert bundle is not None
    assert bundle.tenant_id == "new-user"

    # Verify the tenant is now registered
    tenants = tenant_manager.list_tenants()
    tenant_ids = [t["tenant_id"] for t in tenants]
    assert "new-user" in tenant_ids


@pytest.mark.asyncio
async def test_ingest_auto_create_is_idempotent(tmp_path, tenant_manager, simple_registry):
    """ingest() for an already-registered tenant does not fail."""
    tenant_manager.create_tenant("existing")
    pipeline = IngestionPipeline(simple_registry, tenant_manager=tenant_manager)

    md_file = tmp_path / "doc.md"
    md_file.write_text("# Hello")

    # Should not raise even though tenant already exists
    bundle = await pipeline.ingest([md_file.as_uri()], tenant_id="existing")
    assert bundle is not None


# ---------------------------------------------------------------------------
# AC-005: bundle.storage is set to tenant-specific adapter during processing
# ---------------------------------------------------------------------------


class _StorageCapturingProcessor:
    """Minimal processor that captures the bundle.storage value it sees."""

    def __init__(self):
        self.captured_storage = None

    @property
    def name(self):
        return "capturing_processor"

    @property
    def version(self):
        return "1.0.0"

    @property
    def supported_media_types(self):
        return ["text/markdown", "text/plain", "*"]

    @property
    def record_types(self):
        return []

    @property
    def event_filter(self):
        return None

    async def process_bundle(self, bundle):
        self.captured_storage = bundle.storage
        return []


class _SingleProcessorRegistry:
    def __init__(self, processor):
        self._processor = processor

    def get_processors_for_semantic_types(self, semantic_types):
        return [self._processor]

    def get_ingest_observers(self):
        return []


@pytest.mark.asyncio
async def test_bundle_storage_is_tenant_specific_adapter(tmp_path, tenant_manager):
    """bundle.storage is set to the tenant-specific StorageAdapter during processing."""
    tenant_manager.create_tenant("user-abc")
    expected_adapter = tenant_manager.get_adapter("user-abc")

    processor = _StorageCapturingProcessor()
    registry = _SingleProcessorRegistry(processor)
    pipeline = IngestionPipeline(registry, tenant_manager=tenant_manager)

    md_file = tmp_path / "doc.md"
    md_file.write_text("# Hello\n\nSome content.")

    await pipeline.ingest([md_file.as_uri()], tenant_id="user-abc")

    # The processor should have seen the tenant-specific adapter
    assert processor.captured_storage is expected_adapter


# ---------------------------------------------------------------------------
# AC-006: Documents from different tenants are isolated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_isolation_same_uri(tmp_path, tenant_manager):
    """Same URI ingested into two different tenants creates isolated documents."""
    tenant_manager.create_tenant("tenant-a")
    tenant_manager.create_tenant("tenant-b")

    md_file = tmp_path / "shared.md"
    md_file.write_text("# Shared content\n\nParagraph text here.")

    # Use a real MarkdownPlugin that writes to bundle.storage
    processor_a = MarkdownPlugin(storage=None)  # storage=None — uses bundle.storage

    class _TwoTenantRegistry:
        def __init__(self, processor):
            self._processor = processor
        def get_processors_for_semantic_types(self, semantic_types):
            return [self._processor]
        def get_ingest_observers(self):
            return []

    registry = _TwoTenantRegistry(processor_a)
    pipeline = IngestionPipeline(registry, tenant_manager=tenant_manager)

    # Ingest same URI to two different tenants
    await pipeline.ingest([md_file.as_uri()], tenant_id="tenant-a")
    await pipeline.ingest([md_file.as_uri()], tenant_id="tenant-b")

    adapter_a = tenant_manager.get_adapter("tenant-a")
    adapter_b = tenant_manager.get_adapter("tenant-b")

    # Each tenant's shard should have documents for this URI
    # Chunks now use {uri}#chunk-{i} URIs; look up parent via markdown_source at base URI
    docs_a = adapter_a.lookup_existing_docs(md_file.as_uri(), "markdown_plugin", "markdown_source")
    docs_b = adapter_b.lookup_existing_docs(md_file.as_uri(), "markdown_plugin", "markdown_source")

    assert len(docs_a) > 0, "tenant-a should have documents"
    assert len(docs_b) > 0, "tenant-b should have documents"

    # Adapters are separate objects pointing to different database files
    assert adapter_a is not adapter_b


# ---------------------------------------------------------------------------
# AC-007: MarkdownPlugin uses bundle.storage correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_markdown_plugin_uses_bundle_storage(tmp_path, tenant_manager):
    """MarkdownPlugin writes to bundle.storage, not self.storage."""
    tenant_manager.create_tenant("md-tenant")

    md_file = tmp_path / "test.md"
    md_file.write_text("# Title\n\nParagraph one.\n\nParagraph two.")

    plugin = MarkdownPlugin(storage=None)  # No self.storage — must use bundle.storage

    class _MDRegistry:
        def __init__(self, p):
            self._p = p
        def get_processors_for_semantic_types(self, semantic_types):
            return [self._p]
        def get_ingest_observers(self):
            return []

    pipeline = IngestionPipeline(_MDRegistry(plugin), tenant_manager=tenant_manager)
    bundle = await pipeline.ingest([md_file.as_uri()], tenant_id="md-tenant")

    assert bundle is not None
    # Check that documents were written to the tenant shard
    # Chunks use {uri}#chunk-{i} URIs; look up parent via markdown_source at base URI
    adapter = tenant_manager.get_adapter("md-tenant")
    docs = adapter.lookup_existing_docs(md_file.as_uri(), "markdown_plugin", "markdown_source")
    assert len(docs) > 0, "MarkdownPlugin should have written parent document to bundle.storage"


@pytest.mark.asyncio
async def test_markdown_plugin_events_carry_tenant_id(tmp_path, tenant_manager):
    """IngestionEvents emitted during ingest carry the correct tenant_id."""
    tenant_manager.create_tenant("event-tenant")

    md_file = tmp_path / "events.md"
    md_file.write_text("# Events\n\nSome content here.")

    plugin = MarkdownPlugin(storage=None)

    class _MDRegistry:
        def __init__(self, p):
            self._p = p
        def get_processors_for_semantic_types(self, semantic_types):
            return [self._p]
        def get_ingest_observers(self):
            return []

    pipeline = IngestionPipeline(_MDRegistry(plugin), tenant_manager=tenant_manager)
    bundle = await pipeline.ingest([md_file.as_uri()], tenant_id="event-tenant")

    assert bundle is not None
    # Events on the returned bundle should carry tenant_id
    assert len(bundle.events) > 0
    for event in bundle.events:
        assert event.tenant_id == "event-tenant"
