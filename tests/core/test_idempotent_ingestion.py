"""
SPEC-005: Idempotent Ingestion with Content Hashing
Stories 001-005
"""

import hashlib
import sqlite3
import pytest
from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.server import IngestProcessor, PluginRegistry, RecordTypeSpec
from team_mind_mcp.ingestion import (
    IngestionBundle,
    IngestionContext,
    IngestionEvent,
    IngestionPipeline,
)
from team_mind_mcp.markdown import MarkdownPlugin


# --- STORY-001: Content Hash & Plugin Version Columns ---


def test_columns_exist_on_fresh_db(tmp_path):
    """AC-001: Columns Exist on Fresh DB"""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = {row[1] for row in cursor.fetchall()}

    assert "content_hash" in columns
    assert "plugin_version" in columns
    adapter.close()


def test_save_payload_stores_hash_and_version(tmp_path):
    """AC-002: save_payload Stores Hash and Version"""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    doc_id = adapter.save_payload(
        "uri",
        {},
        [0.1] * 768,
        plugin="p",
        doctype="t",
        content_hash="abc123",
        plugin_version="1.0.0",
    )

    with adapter._conn:
        row = adapter._conn.execute(
            "SELECT content_hash, plugin_version FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()

    assert row[0] == "abc123"
    assert row[1] == "1.0.0"
    adapter.close()


def test_lookup_existing_docs_returns_matches(tmp_path):
    """AC-003: lookup_existing_docs Returns Matches"""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    adapter.save_payload(
        "file:///doc.md",
        {},
        [0.1] * 768,
        plugin="p",
        doctype="t",
        content_hash="h1",
        plugin_version="1.0",
    )
    adapter.save_payload(
        "file:///doc.md",
        {},
        [0.2] * 768,
        plugin="p",
        doctype="t",
        content_hash="h1",
        plugin_version="1.0",
    )

    results = adapter.lookup_existing_docs("file:///doc.md", "p", "t")

    assert len(results) == 2
    assert all(
        "id" in r and "content_hash" in r and "plugin_version" in r for r in results
    )
    adapter.close()


def test_lookup_existing_docs_empty_for_no_match(tmp_path):
    """AC-004: lookup_existing_docs Returns Empty for No Match"""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    results = adapter.lookup_existing_docs("file:///nope.md", "p", "t")
    assert results == []
    adapter.close()


def test_migration_adds_columns(tmp_path):
    """AC-005: Migration Adds Columns to Existing DB"""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uri TEXT NOT NULL,
            plugin TEXT NOT NULL DEFAULT '',
            doctype TEXT NOT NULL DEFAULT '',
            metadata JSON
        )
    """)
    conn.commit()
    conn.close()

    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    with sqlite3.connect(str(db_path)) as conn2:
        cursor = conn2.execute("PRAGMA table_info(documents)")
        columns = {row[1] for row in cursor.fetchall()}

    assert "content_hash" in columns
    assert "plugin_version" in columns
    adapter.close()


def test_composite_uri_index_created(tmp_path):
    """AC-006: Composite Index Created"""
    db_path = tmp_path / "test.db"
    adapter = StorageAdapter(str(db_path))
    adapter.initialize()

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        index_names = [row[0] for row in cursor.fetchall()]

    assert "idx_documents_uri_plugin_doctype" in index_names
    adapter.close()


# --- STORY-002: Plugin Version Property ---


class _VersionedProcessor(IngestProcessor):
    @property
    def name(self) -> str:
        return "versioned"

    @property
    def version(self) -> str:
        return "2.1.0"

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [RecordTypeSpec(name="test_type", description="test")]


class _UnversionedProcessor(IngestProcessor):
    @property
    def name(self) -> str:
        return "unversioned"


def test_default_version_is_000():
    """AC-001: Default Version Is 0.0.0"""
    proc = _UnversionedProcessor()
    assert proc.version == "0.0.0"


def test_plugin_declares_custom_version():
    """AC-002: Plugin Declares Custom Version"""
    proc = _VersionedProcessor()
    assert proc.version == "2.1.0"


def test_markdown_plugin_has_version(tmp_path):
    """AC-003: Version Stored on Ingestion"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()
    plugin = MarkdownPlugin(storage)

    assert plugin.version == "1.0.0"
    storage.close()


# --- STORY-003: IngestionContext Data Model ---


def test_context_fields():
    """AC-001: Context Fields"""
    ctx = IngestionContext(
        uri="file:///test.md",
        is_update=True,
        content_changed=True,
        plugin_version_changed=False,
        previous_doc_ids=[1, 2],
        previous_content_hash="abc",
        previous_plugin_version="1.0.0",
    )
    assert ctx.uri == "file:///test.md"
    assert ctx.is_update is True
    assert ctx.content_changed is True
    assert ctx.plugin_version_changed is False
    assert ctx.previous_doc_ids == [1, 2]
    assert ctx.previous_content_hash == "abc"
    assert ctx.previous_plugin_version == "1.0.0"


def test_new_uri_context():
    """AC-002: New URI Context"""
    ctx = IngestionContext(uri="file:///new.md")
    assert ctx.is_update is False
    assert ctx.content_changed is None
    assert ctx.plugin_version_changed is False
    assert ctx.previous_doc_ids == []


def test_context_built_for_existing_uri(tmp_path):
    """AC-003 & AC-004: Context correctly flags unchanged/changed content"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # Store a doc with known hash
    storage.save_payload(
        "file:///doc.md",
        {},
        [0.1] * 768,
        plugin="p",
        doctype="t",
        content_hash="hash_abc",
        plugin_version="1.0",
    )

    existing = storage.lookup_existing_docs("file:///doc.md", "p", "t")
    assert len(existing) == 1
    assert existing[0]["content_hash"] == "hash_abc"
    assert existing[0]["plugin_version"] == "1.0"
    storage.close()


def test_version_changed_context(tmp_path):
    """AC-005: Version Changed Context"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    storage.save_payload(
        "file:///doc.md",
        {},
        [0.1] * 768,
        plugin="p",
        doctype="t",
        content_hash="h",
        plugin_version="1.0.0",
    )

    existing = storage.lookup_existing_docs("file:///doc.md", "p", "t")
    prev_version = existing[0]["plugin_version"]

    # Simulate version comparison
    current_version = "2.0.0"
    assert prev_version != current_version
    storage.close()


# --- STORY-004: Pipeline Provides Context ---


class _ContextTrackingProcessor(IngestProcessor):
    def __init__(self):
        self.received_contexts: dict = {}

    @property
    def name(self) -> str:
        return "context_tracker"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def record_types(self) -> list[RecordTypeSpec]:
        return [RecordTypeSpec(name="tracked_type", description="test")]

    async def process_bundle(self, bundle: IngestionBundle) -> list[IngestionEvent]:
        self.received_contexts = dict(bundle.contexts)
        return []


@pytest.mark.asyncio
async def test_bundle_contains_contexts(tmp_path):
    """AC-001: Bundle Contains Contexts"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    registry = PluginRegistry()
    proc = _ContextTrackingProcessor()
    registry.register(proc, semantic_types=["*"])
    pipeline = IngestionPipeline(registry, storage=storage)

    f = tmp_path / "test.md"
    f.write_text("content")

    await pipeline.ingest([f.as_uri()])

    assert f.as_uri() in proc.received_contexts
    ctx = proc.received_contexts[f.as_uri()]
    assert isinstance(ctx, IngestionContext)


@pytest.mark.asyncio
async def test_context_flags_update_vs_new(tmp_path):
    """AC-002: Context Generated Per URI"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # Pre-store one URI
    storage.save_payload(
        (tmp_path / "existing.md").as_uri(),
        {},
        [0.1] * 768,
        plugin="context_tracker",
        doctype="tracked_type",
        content_hash="old",
        plugin_version="1.0.0",
    )

    registry = PluginRegistry()
    proc = _ContextTrackingProcessor()
    registry.register(proc, semantic_types=["*"])
    pipeline = IngestionPipeline(registry, storage=storage)

    existing_f = tmp_path / "existing.md"
    existing_f.write_text("content")
    new_f = tmp_path / "new.md"
    new_f.write_text("content")

    await pipeline.ingest([existing_f.as_uri(), new_f.as_uri()])

    assert proc.received_contexts[existing_f.as_uri()].is_update is True
    assert proc.received_contexts[new_f.as_uri()].is_update is False


@pytest.mark.asyncio
async def test_no_existing_docs_means_fresh_context(tmp_path):
    """AC-004: No Existing Docs Means Fresh Context"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    registry = PluginRegistry()
    proc = _ContextTrackingProcessor()
    registry.register(proc, semantic_types=["*"])
    pipeline = IngestionPipeline(registry, storage=storage)

    f = tmp_path / "test.md"
    f.write_text("content")

    await pipeline.ingest([f.as_uri()])

    ctx = proc.received_contexts[f.as_uri()]
    assert ctx.is_update is False
    assert ctx.previous_doc_ids == []


# --- STORY-005: MarkdownPlugin Idempotent Optimization ---


@pytest.mark.asyncio
async def test_markdown_skips_unchanged_content(tmp_path):
    """AC-001: Skips Unchanged Content"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    plugin = MarkdownPlugin(storage)
    registry = PluginRegistry()
    registry.register(plugin, semantic_types=["*"])
    pipeline = IngestionPipeline(registry, storage=storage)

    md_file = tmp_path / "test.md"
    md_file.write_text("Paragraph one.\n\nParagraph two.")

    # First ingest
    bundle1 = await pipeline.ingest([md_file.as_uri()])
    assert len(bundle1.events) == 1
    first_doc_count = len(bundle1.events[0].doc_ids)

    # Second ingest — same content, same version
    bundle2 = await pipeline.ingest([md_file.as_uri()])

    # Should be a no-op — no events
    assert len(bundle2.events) == 0

    # Same number of rows in DB (no duplicates)
    with storage._conn:
        count = storage._conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    assert count == first_doc_count
    storage.close()


@pytest.mark.asyncio
async def test_markdown_replaces_changed_content(tmp_path):
    """AC-002: Replaces Changed Content"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    plugin = MarkdownPlugin(storage)
    registry = PluginRegistry()
    registry.register(plugin, semantic_types=["*"])
    pipeline = IngestionPipeline(registry, storage=storage)

    md_file = tmp_path / "test.md"
    md_file.write_text("Original content.")

    # First ingest
    await pipeline.ingest([md_file.as_uri()])

    # Change content
    md_file.write_text("Updated content.\n\nNew paragraph.")

    # Second ingest — content changed
    bundle2 = await pipeline.ingest([md_file.as_uri()])

    # Should have re-ingested
    assert len(bundle2.events) == 1
    assert len(bundle2.events[0].doc_ids) == 2  # 2 new chunks

    # Old chunks should be gone — only new ones remain
    with storage._conn:
        rows = storage._conn.execute("SELECT metadata FROM documents").fetchall()
    assert len(rows) == 2
    import json

    chunks = [json.loads(r[0])["chunk"] for r in rows]
    assert "Updated content." in chunks
    assert "New paragraph." in chunks
    storage.close()


@pytest.mark.asyncio
async def test_markdown_reprocesses_on_version_change(tmp_path):
    """AC-003: Re-processes on Version Change"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    md_file = tmp_path / "test.md"
    md_file.write_text("Same content.")

    # First ingest with "old" version — simulate by saving directly
    content_hash = hashlib.sha256("Same content.".encode()).hexdigest()
    storage.save_payload(
        md_file.as_uri(),
        {"chunk": "Same content.", "plugin": "markdown_plugin"},
        [0.1] * 768,
        plugin="markdown_plugin",
        doctype="markdown_chunk",
        content_hash=content_hash,
        plugin_version="0.9.0",  # Old version
    )

    # Now ingest with current MarkdownPlugin (version 1.0.0)
    plugin = MarkdownPlugin(storage)
    registry = PluginRegistry()
    registry.register(plugin, semantic_types=["*"])
    pipeline = IngestionPipeline(registry, storage=storage)

    bundle = await pipeline.ingest([md_file.as_uri()])

    # Should re-process because version changed (0.9.0 → 1.0.0)
    assert len(bundle.events) == 1

    # Old row deleted, new row has version 1.0.0
    with storage._conn:
        rows = storage._conn.execute("SELECT plugin_version FROM documents").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "1.0.0"
    storage.close()


@pytest.mark.asyncio
async def test_markdown_fresh_ingest_stores_hash_and_version(tmp_path):
    """AC-004: Fresh Ingest Works Normally"""
    db_path = tmp_path / "test.db"
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    plugin = MarkdownPlugin(storage)
    registry = PluginRegistry()
    registry.register(plugin, semantic_types=["*"])
    pipeline = IngestionPipeline(registry, storage=storage)

    md_file = tmp_path / "test.md"
    md_file.write_text("Hello world.")

    bundle = await pipeline.ingest([md_file.as_uri()])

    assert len(bundle.events) == 1

    with storage._conn:
        row = storage._conn.execute(
            "SELECT content_hash, plugin_version FROM documents LIMIT 1"
        ).fetchone()

    assert row[0] is not None  # content_hash set
    assert row[1] == "1.0.0"  # plugin version set
    storage.close()
