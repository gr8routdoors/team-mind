"""
SPEC-010 / STORY-001: TenantStorageManager and system.sqlite
"""

import os
import sqlite3
import pytest

from team_mind_mcp.tenant_manager import TenantStorageManager, _MAX_OPEN_ADAPTERS
from team_mind_mcp.storage import StorageAdapter


# ---------------------------------------------------------------------------
# AC-1: __init__ does not open any connections
# ---------------------------------------------------------------------------

def test_init_no_connections(tmp_path):
    """AC-1: __init__ accepts base_path and sets up state without opening connections."""
    mgr = TenantStorageManager(str(tmp_path / "data"))
    assert mgr._system_conn is None
    assert mgr._adapters == {}
    assert mgr.base_path == str(tmp_path / "data")


# ---------------------------------------------------------------------------
# AC-2: initialize() creates system.sqlite with required tables
# ---------------------------------------------------------------------------

def test_initialize_creates_system_sqlite(tmp_path):
    """AC-2: initialize() creates system.sqlite in base_path."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    assert os.path.exists(os.path.join(base, "system.sqlite"))
    mgr.close()


def test_initialize_creates_registered_plugins_table(tmp_path):
    """AC-2: initialize() creates registered_plugins table in system.sqlite."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()
    mgr.close()

    with sqlite3.connect(os.path.join(base, "system.sqlite")) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='registered_plugins'"
        )
        assert cursor.fetchone() is not None


def test_initialize_creates_tenants_table(tmp_path):
    """AC-2: initialize() creates tenants table in system.sqlite."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()
    mgr.close()

    with sqlite3.connect(os.path.join(base, "system.sqlite")) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tenants'"
        )
        assert cursor.fetchone() is not None


def test_initialize_is_idempotent(tmp_path):
    """AC-2: initialize() is safe to call on an existing database."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()
    mgr.close()

    # Second initialization should not raise
    mgr2 = TenantStorageManager(base)
    mgr2.initialize()
    mgr2.close()


def test_initialize_auto_creates_default_tenant(tmp_path):
    """AC-2: initialize() auto-creates the 'default' tenant."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    tenants = mgr.list_tenants()
    tenant_ids = [t["tenant_id"] for t in tenants]
    assert "default" in tenant_ids
    mgr.close()


# ---------------------------------------------------------------------------
# AC-3: create_tenant is idempotent
# ---------------------------------------------------------------------------

def test_create_tenant_inserts_row(tmp_path):
    """AC-3: create_tenant inserts a row into the tenants table."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("alice")

    tenants = mgr.list_tenants()
    ids = [t["tenant_id"] for t in tenants]
    assert "alice" in ids
    mgr.close()


def test_create_tenant_idempotent(tmp_path):
    """AC-3: calling create_tenant twice with the same id does not error."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("alice")
    mgr.create_tenant("alice")  # Should not raise

    tenants = mgr.list_tenants()
    alice_rows = [t for t in tenants if t["tenant_id"] == "alice"]
    assert len(alice_rows) == 1
    mgr.close()


def test_create_tenant_with_metadata(tmp_path):
    """AC-3: create_tenant stores metadata as JSON."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("bob", metadata={"region": "us-east"})

    tenants = mgr.list_tenants()
    bob = next(t for t in tenants if t["tenant_id"] == "bob")
    assert bob["metadata"] == {"region": "us-east"}
    mgr.close()


def test_create_tenant_does_not_create_directory(tmp_path):
    """AC-3: create_tenant does not create tenant directory (lazy)."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("lazy-tenant")

    tenant_dir = os.path.join(base, "tenants", "lazy-tenant")
    assert not os.path.exists(tenant_dir)
    mgr.close()


# ---------------------------------------------------------------------------
# AC-4: list_tenants
# ---------------------------------------------------------------------------

def test_list_tenants_returns_dicts_with_required_fields(tmp_path):
    """AC-4: list_tenants returns list of dicts with tenant_id and created_at."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("t1")
    mgr.create_tenant("t2")

    tenants = mgr.list_tenants()
    for t in tenants:
        assert "tenant_id" in t
        assert "created_at" in t

    ids = [t["tenant_id"] for t in tenants]
    assert "t1" in ids
    assert "t2" in ids
    mgr.close()


# ---------------------------------------------------------------------------
# AC-5: get_adapter for registered tenant
# ---------------------------------------------------------------------------

def test_get_adapter_creates_directory_and_db(tmp_path):
    """AC-5: get_adapter lazily creates tenant directory and data.sqlite."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    adapter = mgr.get_adapter("default")
    assert adapter is not None

    tenant_dir = os.path.join(base, "tenants", "default")
    assert os.path.exists(tenant_dir)
    assert os.path.exists(os.path.join(tenant_dir, "data.sqlite"))
    mgr.close()


def test_get_adapter_returns_same_instance(tmp_path):
    """AC-5: get_adapter returns the cached adapter on subsequent calls."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    a1 = mgr.get_adapter("default")
    a2 = mgr.get_adapter("default")
    assert a1 is a2
    mgr.close()


def test_get_adapter_raises_for_unregistered_tenant(tmp_path):
    """AC-5: get_adapter raises ValueError for unregistered tenant."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    with pytest.raises(ValueError, match="not registered"):
        mgr.get_adapter("does-not-exist")
    mgr.close()


def test_get_adapter_returns_functional_storage_adapter(tmp_path):
    """AC-5: the StorageAdapter returned by get_adapter is initialized (tables exist)."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    adapter = mgr.get_adapter("default")
    # A functional adapter should allow querying the documents table
    cursor = adapter._conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
    assert cursor.fetchone() is not None
    mgr.close()


# ---------------------------------------------------------------------------
# AC-6: LRU eviction
# ---------------------------------------------------------------------------

def test_lru_eviction_closes_oldest_adapter(tmp_path):
    """AC-6: when more than 64 adapters are open, the LRU one is closed and evicted."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    # Create 65 tenants
    tenant_ids = [f"tenant-{i:03d}" for i in range(_MAX_OPEN_ADAPTERS + 1)]
    for tid in tenant_ids:
        mgr.create_tenant(tid)

    # Open adapters for all 65 tenants
    first_adapter = mgr.get_adapter(tenant_ids[0])
    for tid in tenant_ids[1:]:
        mgr.get_adapter(tid)

    # After opening 65 adapters, the first (LRU) should have been evicted
    assert len(mgr._adapters) == _MAX_OPEN_ADAPTERS
    assert tenant_ids[0] not in mgr._adapters

    # The first adapter should be closed
    assert first_adapter._conn is None
    mgr.close()


def test_lru_eviction_respects_recent_access(tmp_path):
    """AC-6: accessing an adapter moves it to the MRU position, preventing eviction."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    # Open 64 tenants
    tenant_ids = [f"tenant-{i:03d}" for i in range(_MAX_OPEN_ADAPTERS)]
    for tid in tenant_ids:
        mgr.create_tenant(tid)
    for tid in tenant_ids:
        mgr.get_adapter(tid)

    # Re-access the first tenant to make it the MRU
    first_adapter = mgr.get_adapter(tenant_ids[0])

    # Add a 65th tenant — should evict tenant_ids[1] (now the LRU), not tenant_ids[0]
    extra_id = "extra-tenant"
    mgr.create_tenant(extra_id)
    mgr.get_adapter(extra_id)

    assert tenant_ids[0] in mgr._adapters
    assert tenant_ids[1] not in mgr._adapters
    assert first_adapter._conn is not None  # Not closed
    mgr.close()


# ---------------------------------------------------------------------------
# AC-7: Plugin registry methods
# ---------------------------------------------------------------------------

def test_save_and_get_plugin_record(tmp_path):
    """AC-7: save_plugin_record persists to system.sqlite; get_enabled_plugin_records retrieves it."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.save_plugin_record(
        plugin_name="my_plugin",
        plugin_type="tool_provider",
        module_path="my_module.MyPlugin",
        config={"key": "val"},
        event_filter_json={"plugins": ["foo"]},
        semantic_types=["code"],
        supported_media_types=["text/plain"],
    )

    records = mgr.get_enabled_plugin_records()
    assert len(records) == 1
    r = records[0]
    assert r["plugin_name"] == "my_plugin"
    assert r["plugin_type"] == "tool_provider"
    assert r["module_path"] == "my_module.MyPlugin"
    assert r["config"] == {"key": "val"}
    assert r["event_filter"] == {"plugins": ["foo"]}
    assert r["semantic_types"] == ["code"]
    assert r["supported_media_types"] == ["text/plain"]
    mgr.close()


def test_disable_plugin_record(tmp_path):
    """AC-7: disable_plugin_record marks plugin disabled; excluded from get_enabled_plugin_records."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.save_plugin_record("p1", "tool_provider", "m.P1")
    result = mgr.disable_plugin_record("p1")
    assert result is True

    records = mgr.get_enabled_plugin_records()
    assert all(r["plugin_name"] != "p1" for r in records)
    mgr.close()


def test_disable_plugin_record_returns_false_if_not_found(tmp_path):
    """AC-7: disable_plugin_record returns False for unknown plugin."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    result = mgr.disable_plugin_record("nonexistent")
    assert result is False
    mgr.close()


def test_delete_plugin_record(tmp_path):
    """AC-7: delete_plugin_record removes the record entirely."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.save_plugin_record("p2", "tool_provider", "m.P2")
    result = mgr.delete_plugin_record("p2")
    assert result is True

    records = mgr.get_enabled_plugin_records()
    assert all(r["plugin_name"] != "p2" for r in records)
    mgr.close()


def test_delete_plugin_record_returns_false_if_not_found(tmp_path):
    """AC-7: delete_plugin_record returns False for unknown plugin."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    result = mgr.delete_plugin_record("nonexistent")
    assert result is False
    mgr.close()


def test_plugin_records_stored_in_system_sqlite_not_tenant_db(tmp_path):
    """AC-7: plugin records are in system.sqlite, not in a tenant data.sqlite."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.save_plugin_record("p3", "tool_provider", "m.P3")

    # Check it's in system.sqlite
    with sqlite3.connect(os.path.join(base, "system.sqlite")) as conn:
        cursor = conn.execute("SELECT plugin_name FROM registered_plugins WHERE plugin_name='p3'")
        assert cursor.fetchone() is not None

    # Check it's NOT in default tenant db
    mgr.get_adapter("default")
    tenant_db = os.path.join(base, "tenants", "default", "data.sqlite")
    with sqlite3.connect(tenant_db) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='registered_plugins'"
        )
        # The table should not exist in the tenant db
        assert cursor.fetchone() is None
    mgr.close()


# ---------------------------------------------------------------------------
# AC-8: close()
# ---------------------------------------------------------------------------

def test_close_closes_all_adapters(tmp_path):
    """AC-8: close() closes all open tenant adapters."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.create_tenant("t1")
    mgr.create_tenant("t2")
    a1 = mgr.get_adapter("t1")
    a2 = mgr.get_adapter("t2")

    mgr.close()

    assert a1._conn is None
    assert a2._conn is None


def test_close_closes_system_connection(tmp_path):
    """AC-8: close() closes the system.sqlite connection."""
    base = str(tmp_path / "mind")
    mgr = TenantStorageManager(base)
    mgr.initialize()

    mgr.close()

    assert mgr._system_conn is None


# ---------------------------------------------------------------------------
# AC-9: StorageAdapter.initialize() no longer creates registered_plugins table
# ---------------------------------------------------------------------------

def test_storage_adapter_does_not_create_registered_plugins(tmp_path):
    """AC-9: StorageAdapter.initialize() no longer creates the registered_plugins table."""
    db_path = str(tmp_path / "test.db")
    adapter = StorageAdapter(db_path)
    adapter.initialize()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='registered_plugins'"
        )
        assert cursor.fetchone() is None

    adapter.close()
