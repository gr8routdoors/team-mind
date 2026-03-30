"""
SPEC-010 / STORY-002: Per-Tenant Database Lifecycle

Verifies:
- get_adapter lazily creates tenant directory and data.sqlite on first access
- Per-tenant schema: documents, vec_documents, doc_weights present
- Per-tenant schema: registered_plugins absent (moved to system.sqlite)
- Per-tenant documents table has NO tenant_id column
- Composite identity key is (uri, plugin, record_type) — tenant is the database
- get_adapter raises ValueError for unregistered tenants
- Multiple tenants get isolated, separate database files
"""

import os
import sqlite3
import pytest

from team_mind_mcp.tenant_manager import TenantStorageManager
from team_mind_mcp.storage import StorageAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tenant_db_path(base: str, tenant_id: str) -> str:
    return os.path.join(base, "tenants", tenant_id, "data.sqlite")


def _get_tables(db_path: str) -> set[str]:
    """Return all regular table names in a SQLite database."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        return {row[0] for row in cursor.fetchall()}


def _get_columns(db_path: str, table: str) -> set[str]:
    """Return column names for a table in a SQLite database."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}


def _has_vec_documents_table(db_path: str) -> bool:
    """Return True if vec_documents virtual table exists in the database."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE name='vec_documents'"
        )
        return cursor.fetchone() is not None


# ---------------------------------------------------------------------------
# AC-1: Lazy creation — directory and data.sqlite created on first get_adapter
# ---------------------------------------------------------------------------

def test_tenant_dir_not_created_before_get_adapter(tmp_path):
    """Tenant directory is not created by create_tenant — only on get_adapter."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("lazy")

    # Directory must NOT exist yet
    assert not os.path.exists(os.path.join(base, "tenants", "lazy"))
    mgr.close()


def test_tenant_dir_created_on_first_get_adapter(tmp_path):
    """get_adapter creates the tenant directory on first call."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("new-tenant")

    tenant_dir = os.path.join(base, "tenants", "new-tenant")
    assert not os.path.exists(tenant_dir)

    mgr.get_adapter("new-tenant")

    assert os.path.isdir(tenant_dir)
    mgr.close()


def test_data_sqlite_created_on_first_get_adapter(tmp_path):
    """get_adapter creates data.sqlite inside the tenant directory."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("new-tenant")
    db_path = _tenant_db_path(base, "new-tenant")
    assert not os.path.exists(db_path)

    mgr.get_adapter("new-tenant")

    assert os.path.isfile(db_path)
    mgr.close()


def test_data_sqlite_not_created_for_default_before_access(tmp_path):
    """Default tenant's data.sqlite is not created by initialize() — only on get_adapter."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    # initialize() registers the default tenant but must not create the file
    db_path = _tenant_db_path(base, "default")
    assert not os.path.exists(db_path)

    mgr.get_adapter("default")
    assert os.path.isfile(db_path)
    mgr.close()


# ---------------------------------------------------------------------------
# AC-2: Per-tenant schema — required tables present
# ---------------------------------------------------------------------------

def test_per_tenant_db_has_documents_table(tmp_path):
    """data.sqlite contains the documents table."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.get_adapter("default")
    db_path = _tenant_db_path(base, "default")

    tables = _get_tables(db_path)
    assert "documents" in tables
    mgr.close()


def test_per_tenant_db_has_vec_documents_table(tmp_path):
    """data.sqlite contains the vec_documents virtual table."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.get_adapter("default")
    db_path = _tenant_db_path(base, "default")

    assert _has_vec_documents_table(db_path)
    mgr.close()


def test_per_tenant_db_has_doc_weights_table(tmp_path):
    """data.sqlite contains the doc_weights table."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.get_adapter("default")
    db_path = _tenant_db_path(base, "default")

    tables = _get_tables(db_path)
    assert "doc_weights" in tables
    mgr.close()


# ---------------------------------------------------------------------------
# AC-3: Per-tenant schema — registered_plugins absent
# ---------------------------------------------------------------------------

def test_per_tenant_db_has_no_registered_plugins_table(tmp_path):
    """data.sqlite must NOT contain the registered_plugins table."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.get_adapter("default")
    db_path = _tenant_db_path(base, "default")

    tables = _get_tables(db_path)
    assert "registered_plugins" not in tables
    mgr.close()


def test_per_tenant_db_no_registered_plugins_for_non_default_tenant(tmp_path):
    """Non-default tenant data.sqlite must NOT have registered_plugins either."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("user-123")
    mgr.get_adapter("user-123")
    db_path = _tenant_db_path(base, "user-123")

    tables = _get_tables(db_path)
    assert "registered_plugins" not in tables
    mgr.close()


# ---------------------------------------------------------------------------
# AC-4: documents table has NO tenant_id column
# ---------------------------------------------------------------------------

def test_documents_table_has_no_tenant_id_column(tmp_path):
    """documents table must not have a tenant_id column — tenant is the database."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.get_adapter("default")
    db_path = _tenant_db_path(base, "default")

    columns = _get_columns(db_path, "documents")
    assert "tenant_id" not in columns
    mgr.close()


def test_documents_table_has_expected_columns(tmp_path):
    """documents table has the expected columns: id, uri, plugin, record_type, metadata,
    content_hash, plugin_version, semantic_type, media_type."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.get_adapter("default")
    db_path = _tenant_db_path(base, "default")

    columns = _get_columns(db_path, "documents")
    expected = {"id", "uri", "plugin", "record_type", "metadata",
                "content_hash", "plugin_version", "semantic_type", "media_type"}
    assert expected.issubset(columns)
    mgr.close()


# ---------------------------------------------------------------------------
# AC-5: get_adapter raises ValueError for unregistered tenants
# ---------------------------------------------------------------------------

def test_get_adapter_raises_for_unregistered_tenant(tmp_path):
    """get_adapter raises ValueError when called with an unregistered tenant_id."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    with pytest.raises(ValueError, match="not registered"):
        mgr.get_adapter("ghost-tenant")
    mgr.close()


def test_get_adapter_raises_before_create_tenant(tmp_path):
    """get_adapter raises before create_tenant is called, even for a valid-looking id."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    with pytest.raises(ValueError, match="not registered"):
        mgr.get_adapter("user-999")
    mgr.close()


def test_get_adapter_succeeds_after_create_tenant(tmp_path):
    """get_adapter succeeds once create_tenant has been called."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("user-999")
    adapter = mgr.get_adapter("user-999")
    assert adapter is not None
    mgr.close()


# ---------------------------------------------------------------------------
# AC-6: Multiple tenants get isolated database files
# ---------------------------------------------------------------------------

def test_multiple_tenants_get_separate_db_files(tmp_path):
    """Each tenant gets its own data.sqlite at tenants/<tenant_id>/data.sqlite."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("alice")
    mgr.create_tenant("bob")

    mgr.get_adapter("alice")
    mgr.get_adapter("bob")
    mgr.get_adapter("default")

    assert os.path.isfile(_tenant_db_path(base, "alice"))
    assert os.path.isfile(_tenant_db_path(base, "bob"))
    assert os.path.isfile(_tenant_db_path(base, "default"))

    # All three must be different files
    paths = {
        _tenant_db_path(base, "alice"),
        _tenant_db_path(base, "bob"),
        _tenant_db_path(base, "default"),
    }
    assert len(paths) == 3
    mgr.close()


def test_tenant_databases_are_isolated(tmp_path):
    """Documents written to one tenant shard are not visible in another."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("alice")
    mgr.create_tenant("bob")

    alice_adapter = mgr.get_adapter("alice")
    bob_adapter = mgr.get_adapter("bob")

    # Write to alice's shard
    vector = [0.1] * 768
    alice_adapter.save_payload(
        uri="file://doc.md",
        metadata={"title": "alice doc"},
        vector=vector,
        plugin="test_plugin",
        record_type="note",
    )

    # Bob's shard should be empty
    bob_docs = bob_adapter.lookup_existing_docs("file://doc.md", "test_plugin", "note")
    assert bob_docs == []

    # Alice's shard should have the document
    alice_docs = alice_adapter.lookup_existing_docs("file://doc.md", "test_plugin", "note")
    assert len(alice_docs) == 1
    mgr.close()


# ---------------------------------------------------------------------------
# AC-7: StorageAdapter.initialize() does not create registered_plugins
# ---------------------------------------------------------------------------

def test_storage_adapter_initialize_no_registered_plugins_table(tmp_path):
    """StorageAdapter.initialize() must not create the registered_plugins table."""
    db_path = str(tmp_path / "standalone.db")
    adapter = StorageAdapter(db_path)
    adapter.initialize()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='registered_plugins'"
        )
        assert cursor.fetchone() is None

    adapter.close()


def test_storage_adapter_initialize_creates_correct_tables(tmp_path):
    """StorageAdapter.initialize() creates documents, doc_weights (and vec_documents)
    but NOT registered_plugins."""
    db_path = str(tmp_path / "standalone.db")
    adapter = StorageAdapter(db_path)
    adapter.initialize()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

    assert "documents" in tables
    assert "doc_weights" in tables
    assert "registered_plugins" not in tables

    adapter.close()
