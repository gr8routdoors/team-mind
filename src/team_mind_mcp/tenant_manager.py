import sqlite3
import json
import os
from collections import OrderedDict

from team_mind_mcp.storage import StorageAdapter

_MAX_OPEN_ADAPTERS = 64


class TenantStorageManager:
    """Manages per-tenant SQLite databases and the global system.sqlite."""

    def __init__(self, base_path: str):
        self.base_path = base_path
        self._adapters: OrderedDict[str, StorageAdapter] = OrderedDict()
        self._system_conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize system.sqlite and ensure default tenant exists."""
        os.makedirs(self.base_path, exist_ok=True)
        system_db_path = os.path.join(self.base_path, "system.sqlite")
        self._system_conn = sqlite3.connect(system_db_path)

        with self._system_conn:
            self._system_conn.execute("""
                CREATE TABLE IF NOT EXISTS registered_plugins (
                    plugin_name TEXT PRIMARY KEY,
                    plugin_type TEXT NOT NULL,
                    module_path TEXT NOT NULL,
                    config JSON,
                    event_filter JSON,
                    semantic_types JSON,
                    supported_media_types JSON,
                    enabled INTEGER DEFAULT 1,
                    registered_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            # Migrate existing registered_plugins: add columns if missing
            cursor = self._system_conn.execute("PRAGMA table_info(registered_plugins)")
            plugin_columns = {row[1] for row in cursor.fetchall()}
            if "semantic_types" not in plugin_columns:
                self._system_conn.execute(
                    "ALTER TABLE registered_plugins ADD COLUMN semantic_types JSON"
                )
            if "supported_media_types" not in plugin_columns:
                self._system_conn.execute(
                    "ALTER TABLE registered_plugins ADD COLUMN supported_media_types JSON"
                )
            self._system_conn.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    metadata JSON
                )
            """)

        # Auto-create the default tenant
        self.create_tenant("default")

    def close(self) -> None:
        """Close all open tenant adapters and the system connection."""
        for adapter in self._adapters.values():
            adapter.close()
        self._adapters.clear()

        if self._system_conn is not None:
            self._system_conn.close()
            self._system_conn = None

    # ------------------------------------------------------------------
    # Tenant management
    # ------------------------------------------------------------------

    def create_tenant(self, tenant_id: str, metadata: dict | None = None) -> None:
        """Register a new tenant in system.sqlite.

        Idempotent: calling with an already-registered tenant_id does nothing.
        Does NOT create the directory or data.sqlite (lazy).
        """
        if self._system_conn is None:
            raise RuntimeError("TenantStorageManager not initialized")
        with self._system_conn:
            self._system_conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, metadata) VALUES (?, ?)",
                (tenant_id, json.dumps(metadata) if metadata is not None else None),
            )

    def list_tenants(self) -> list[dict]:
        """Return all registered tenants from system.sqlite."""
        if self._system_conn is None:
            raise RuntimeError("TenantStorageManager not initialized")
        cursor = self._system_conn.execute(
            "SELECT tenant_id, created_at, metadata FROM tenants"
        )
        results = []
        for row in cursor.fetchall():
            results.append({
                "tenant_id": row[0],
                "created_at": row[1],
                "metadata": json.loads(row[2]) if row[2] else None,
            })
        return results

    def get_adapter(self, tenant_id: str) -> StorageAdapter:
        """Get or lazily create a StorageAdapter for a tenant.

        Raises ValueError if the tenant is not registered in system.sqlite.
        Applies LRU eviction when more than 64 adapters are open.
        """
        if self._system_conn is None:
            raise RuntimeError("TenantStorageManager not initialized")

        # Verify tenant is registered
        row = self._system_conn.execute(
            "SELECT tenant_id FROM tenants WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Tenant '{tenant_id}' is not registered")

        # Return cached adapter (move to end to mark as recently used)
        if tenant_id in self._adapters:
            self._adapters.move_to_end(tenant_id)
            return self._adapters[tenant_id]

        # Evict least-recently-used adapter if at capacity
        if len(self._adapters) >= _MAX_OPEN_ADAPTERS:
            _, evicted = self._adapters.popitem(last=False)
            evicted.close()

        # Lazily create tenant directory and open adapter
        tenant_dir = os.path.join(self.base_path, "tenants", tenant_id)
        os.makedirs(tenant_dir, exist_ok=True)
        db_path = os.path.join(tenant_dir, "data.sqlite")

        adapter = StorageAdapter(db_path)
        try:
            adapter.initialize()
        except Exception:
            adapter.close()
            raise

        self._adapters[tenant_id] = adapter
        return adapter

    # ------------------------------------------------------------------
    # Plugin registry (delegates to system.sqlite)
    # ------------------------------------------------------------------

    def save_plugin_record(
        self,
        plugin_name: str,
        plugin_type: str,
        module_path: str,
        config: dict | None = None,
        event_filter_json: dict | None = None,
        semantic_types: list[str] | None = None,
        supported_media_types: list[str] | None = None,
    ) -> None:
        """Persist a dynamically registered plugin to system.sqlite."""
        if self._system_conn is None:
            raise RuntimeError("TenantStorageManager not initialized")
        with self._system_conn:
            self._system_conn.execute(
                "INSERT OR REPLACE INTO registered_plugins "
                "(plugin_name, plugin_type, module_path, config, event_filter, "
                "semantic_types, supported_media_types) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    plugin_name,
                    plugin_type,
                    module_path,
                    json.dumps(config) if config else None,
                    json.dumps(event_filter_json) if event_filter_json else None,
                    json.dumps(semantic_types) if semantic_types is not None else None,
                    json.dumps(supported_media_types)
                    if supported_media_types is not None
                    else None,
                ),
            )

    def get_enabled_plugin_records(self) -> list[dict]:
        """Retrieve all enabled plugin records from system.sqlite."""
        if self._system_conn is None:
            raise RuntimeError("TenantStorageManager not initialized")
        cursor = self._system_conn.execute(
            "SELECT plugin_name, plugin_type, module_path, config, event_filter, "
            "semantic_types, supported_media_types "
            "FROM registered_plugins WHERE enabled = 1"
        )
        return [
            {
                "plugin_name": row[0],
                "plugin_type": row[1],
                "module_path": row[2],
                "config": json.loads(row[3]) if row[3] else None,
                "event_filter": json.loads(row[4]) if row[4] else None,
                "semantic_types": json.loads(row[5]) if row[5] else None,
                "supported_media_types": json.loads(row[6]) if row[6] else None,
            }
            for row in cursor.fetchall()
        ]

    def disable_plugin_record(self, plugin_name: str) -> bool:
        """Mark a plugin as disabled in system.sqlite. Returns True if found."""
        if self._system_conn is None:
            raise RuntimeError("TenantStorageManager not initialized")
        with self._system_conn:
            cursor = self._system_conn.execute(
                "UPDATE registered_plugins SET enabled = 0 WHERE plugin_name = ?",
                (plugin_name,),
            )
            return cursor.rowcount > 0

    def delete_plugin_record(self, plugin_name: str) -> bool:
        """Remove a plugin record from system.sqlite. Returns True if found."""
        if self._system_conn is None:
            raise RuntimeError("TenantStorageManager not initialized")
        with self._system_conn:
            cursor = self._system_conn.execute(
                "DELETE FROM registered_plugins WHERE plugin_name = ?",
                (plugin_name,),
            )
            return cursor.rowcount > 0
