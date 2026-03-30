import re
import sqlite3
import json
import struct
import sqlite_vec

_SAFE_METADATA_KEY_RE = re.compile(r"^[A-Za-z0-9_]+$")


class StorageAdapter:
    """Embedded SQLite storage for tracking documents and vector embeddings."""

    # Over-fetch multiplier for KNN queries with post-filters.
    # sqlite-vec performs KNN before JOIN/WHERE, so we fetch more
    # candidates and filter in Python to compensate.
    KNN_OVERFETCH_MULTIPLIER = 4

    # How much usage_score influences ranking relative to vector distance.
    WEIGHT_INFLUENCE = 0.1

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        try:
            sqlite_vec.load(conn)
        except Exception as e:
            conn.close()
            raise RuntimeError(f"Missing dependency or failed to load sqlite-vec: {e}")
        return conn

    def initialize(self):
        """Creates required tables and checks for sqlite-vec extension."""
        self._conn = self._get_connection()

        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uri TEXT NOT NULL,
                    plugin TEXT NOT NULL DEFAULT '',
                    record_type TEXT NOT NULL DEFAULT '',
                    metadata JSON,
                    content_hash TEXT,
                    plugin_version TEXT DEFAULT '0.0.0',
                    semantic_type TEXT NOT NULL DEFAULT '',
                    media_type TEXT NOT NULL DEFAULT '',
                    parent_id INTEGER REFERENCES documents(id)
                )
            """)

            # Migrate existing databases: add columns if missing
            cursor = self._conn.execute("PRAGMA table_info(documents)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            if "plugin" not in existing_columns:
                self._conn.execute(
                    "ALTER TABLE documents ADD COLUMN plugin TEXT NOT NULL DEFAULT ''"
                )
            if "doctype" in existing_columns:
                self._conn.execute(
                    "ALTER TABLE documents RENAME COLUMN doctype TO record_type"
                )
                self._conn.execute("DROP INDEX IF EXISTS idx_documents_doctype")
                self._conn.execute("DROP INDEX IF EXISTS idx_documents_plugin_doctype")
                self._conn.execute(
                    "DROP INDEX IF EXISTS idx_documents_uri_plugin_doctype"
                )
            if (
                "record_type" not in existing_columns
                and "doctype" not in existing_columns
            ):
                self._conn.execute(
                    "ALTER TABLE documents ADD COLUMN record_type TEXT NOT NULL DEFAULT ''"
                )
            if "content_hash" not in existing_columns:
                self._conn.execute("ALTER TABLE documents ADD COLUMN content_hash TEXT")
            if "plugin_version" not in existing_columns:
                self._conn.execute(
                    "ALTER TABLE documents ADD COLUMN plugin_version TEXT DEFAULT '0.0.0'"
                )
            if "semantic_type" not in existing_columns:
                self._conn.execute(
                    "ALTER TABLE documents ADD COLUMN semantic_type TEXT NOT NULL DEFAULT ''"
                )
            if "media_type" not in existing_columns:
                self._conn.execute(
                    "ALTER TABLE documents ADD COLUMN media_type TEXT NOT NULL DEFAULT ''"
                )
            if "parent_id" not in existing_columns:
                self._conn.execute(
                    "ALTER TABLE documents ADD COLUMN parent_id INTEGER REFERENCES documents(id)"
                )

            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_plugin
                ON documents(plugin)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_record_type
                ON documents(record_type)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_plugin_record_type
                ON documents(plugin, record_type)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_uri_plugin_record_type
                ON documents(uri, plugin, record_type)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_semantic_type
                ON documents(semantic_type)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_parent_id
                ON documents(parent_id)
            """)
            self._conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_documents USING vec0(
                    id INTEGER PRIMARY KEY,
                    embedding float[768]
                )
            """)

            # Weighting tables
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS doc_weights (
                    doc_id INTEGER PRIMARY KEY REFERENCES documents(id),
                    usage_score REAL DEFAULT 0.0,
                    signal_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    tombstoned INTEGER DEFAULT 0,
                    decay_half_life_days REAL
                )
            """)

            # Migrate existing doc_weights: add signal_count if missing
            cursor = self._conn.execute("PRAGMA table_info(doc_weights)")
            weight_columns = {row[1] for row in cursor.fetchall()}
            if "signal_count" not in weight_columns:
                self._conn.execute(
                    "ALTER TABLE doc_weights ADD COLUMN signal_count INTEGER DEFAULT 0"
                )
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_doc_weights_tombstoned
                ON doc_weights(tombstoned)
            """)

    # --- Plugin persistence CRUD ---

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
        """Persist a dynamically registered plugin."""
        if self._conn is None:
            raise RuntimeError("Database not initialized")
        with self._conn:
            self._conn.execute(
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
        """Retrieve all enabled plugin records for startup recovery."""
        if self._conn is None:
            raise RuntimeError("Database not initialized")
        cursor = self._conn.execute(
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
        """Mark a plugin as disabled. Returns True if found."""
        if self._conn is None:
            raise RuntimeError("Database not initialized")
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE registered_plugins SET enabled = 0 WHERE plugin_name = ?",
                (plugin_name,),
            )
            return cursor.rowcount > 0

    def delete_plugin_record(self, plugin_name: str) -> bool:
        """Remove a plugin record entirely. Returns True if found."""
        if self._conn is None:
            raise RuntimeError("Database not initialized")
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM registered_plugins WHERE plugin_name = ?",
                (plugin_name,),
            )
            return cursor.rowcount > 0

    def save_parent(
        self,
        uri: str,
        plugin: str,
        record_type: str,
        metadata: dict | None = None,
        content_hash: str | None = None,
        plugin_version: str = "0.0.0",
        semantic_type: str = "",
        media_type: str = "",
    ) -> int:
        """Create a parent document — no vector embedding, no weight row.

        Returns the document ID for child segments to reference via parent_id.
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO documents (uri, plugin, record_type, metadata, content_hash, "
                "plugin_version, semantic_type, media_type, parent_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL) RETURNING id",
                (
                    uri,
                    plugin,
                    record_type,
                    json.dumps(metadata) if metadata is not None else None,
                    content_hash,
                    plugin_version,
                    semantic_type,
                    media_type,
                ),
            )
            return cursor.fetchone()[0]

    def save_payload(
        self,
        uri: str,
        metadata: dict,
        vector: list[float],
        plugin: str,
        record_type: str,
        parent_id: int | None = None,
        decay_half_life_days: float | None = None,
        content_hash: str | None = None,
        plugin_version: str = "0.0.0",
        semantic_type: str = "",
        media_type: str = "",
        initial_score: float = 0.0,
    ) -> int:
        """Saves a document, its embedding vector, and initializes its weight row."""
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        if parent_id is not None:
            row = self._conn.execute(
                "SELECT id FROM documents WHERE id = ?", (parent_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"No document with id={parent_id}")

        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO documents (uri, plugin, record_type, metadata, content_hash, plugin_version, semantic_type, media_type, parent_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
                (
                    uri,
                    plugin,
                    record_type,
                    json.dumps(metadata),
                    content_hash,
                    plugin_version,
                    semantic_type,
                    media_type,
                    parent_id,
                ),
            )
            doc_id = cursor.fetchone()[0]

            vec_bytes = struct.pack(f"{len(vector)}f", *vector)
            self._conn.execute(
                "INSERT INTO vec_documents (id, embedding) VALUES (?, ?)",
                (doc_id, vec_bytes),
            )

            # Auto-create weight row
            self._conn.execute(
                "INSERT INTO doc_weights (doc_id, usage_score, decay_half_life_days) VALUES (?, ?, ?)",
                (doc_id, initial_score, decay_half_life_days),
            )

            return doc_id

    def update_payload(
        self,
        doc_id: int,
        metadata: dict,
        vector: list[float],
    ) -> None:
        """Update an existing document's metadata and vector in place.

        The plugin/record_type/uri are immutable — only content changes.
        Preserves the existing weight row (usage_score, tombstone, etc.).
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        with self._conn:
            row = self._conn.execute(
                "SELECT id FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"No document with id={doc_id}")

            self._conn.execute(
                "UPDATE documents SET metadata = ? WHERE id = ?",
                (json.dumps(metadata), doc_id),
            )

            vec_bytes = struct.pack(f"{len(vector)}f", *vector)
            self._conn.execute(
                "UPDATE vec_documents SET embedding = ? WHERE id = ?",
                (vec_bytes, doc_id),
            )

    def delete_by_uri(
        self,
        uri: str,
        plugin: str,
        record_type: str,
    ) -> int:
        """Delete all documents (and their weights/vectors) for a URI/plugin/record_type combo.

        Returns the number of documents deleted. Used by plugins to wipe old
        chunks before re-ingesting an updated document.
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        with self._conn:
            # Find all matching doc IDs
            cursor = self._conn.execute(
                "SELECT id FROM documents WHERE uri = ? AND plugin = ? AND record_type = ?",
                (uri, plugin, record_type),
            )
            doc_ids = [row[0] for row in cursor.fetchall()]

            if not doc_ids:
                return 0

            placeholders = ",".join("?" for _ in doc_ids)

            # Delete weights, vectors, then documents
            self._conn.execute(
                f"DELETE FROM doc_weights WHERE doc_id IN ({placeholders})",
                doc_ids,
            )
            self._conn.execute(
                f"DELETE FROM vec_documents WHERE id IN ({placeholders})",
                doc_ids,
            )
            self._conn.execute(
                f"DELETE FROM documents WHERE id IN ({placeholders})",
                doc_ids,
            )

            return len(doc_ids)

    def lookup_existing_docs(
        self,
        uri: str,
        plugin: str,
        record_type: str,
    ) -> list[dict]:
        """Look up existing documents for a URI+plugin+record_type combo.

        Returns a list of dicts with id, content_hash, and plugin_version
        for each matching row. Used by the pipeline to build IngestionContext.
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        cursor = self._conn.execute(
            "SELECT id, content_hash, plugin_version FROM documents "
            "WHERE uri = ? AND plugin = ? AND record_type = ?",
            (uri, plugin, record_type),
        )
        return [
            {
                "id": row[0],
                "content_hash": row[1],
                "plugin_version": row[2],
            }
            for row in cursor.fetchall()
        ]

    def update_weight(
        self,
        doc_id: int,
        signal: int,
        tombstone: bool | None = None,
    ) -> dict:
        """Apply a feedback signal using cumulative moving average.

        Each signal is averaged into usage_score proportionally:
          new_count = old_count + 1
          new_score = old_score + (signal - old_score) / new_count

        This naturally bounds usage_score to [-5, +5] (the signal range)
        and gives each signal proportional weight.
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        with self._conn:
            row = self._conn.execute(
                "SELECT doc_id, usage_score, signal_count, tombstoned FROM doc_weights WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"No weight entry for doc_id={doc_id}")

            old_score = row[1]
            old_count = row[2]
            new_count = old_count + 1
            new_score = old_score + (signal - old_score) / new_count

            if tombstone is not None:
                self._conn.execute(
                    """UPDATE doc_weights
                       SET usage_score = ?, signal_count = ?,
                           last_accessed = datetime('now'), tombstoned = ?
                       WHERE doc_id = ?""",
                    (new_score, new_count, 1 if tombstone else 0, doc_id),
                )
            else:
                self._conn.execute(
                    """UPDATE doc_weights
                       SET usage_score = ?, signal_count = ?,
                           last_accessed = datetime('now')
                       WHERE doc_id = ?""",
                    (new_score, new_count, doc_id),
                )

            updated = self._conn.execute(
                "SELECT usage_score, signal_count, tombstoned, last_accessed FROM doc_weights WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()

            return {
                "doc_id": doc_id,
                "usage_score": updated[0],
                "signal_count": updated[1],
                "tombstoned": bool(updated[2]),
                "last_accessed": updated[3],
            }

    def retrieve_by_vector_similarity(
        self,
        target_vector: list[float],
        limit: int = 5,
        plugins: list[str] | None = None,
        record_types: list[str] | None = None,
        metadata_filters: dict[str, str] | None = None,
    ) -> list[dict]:
        """Retrieves documents by KNN similarity with composite scoring.

        Combines vector distance with usage-based weighting and time decay.
        Tombstoned documents are always excluded. When no weights exist,
        results are ranked by pure vector distance (equivalent to no weighting).

        metadata_filters: optional dict of key-value pairs. Each pair becomes
        a json_extract condition (AND semantics). NULL metadata rows are
        excluded when any filter is provided.
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        # Short-circuit: explicit empty list means "match nothing"
        if plugins is not None and len(plugins) == 0:
            return []
        if record_types is not None and len(record_types) == 0:
            return []

        has_filters = (
            plugins is not None or record_types is not None or bool(metadata_filters)
        )
        fetch_k = limit * self.KNN_OVERFETCH_MULTIPLIER if has_filters else limit

        vec_bytes = struct.pack(f"{len(target_vector)}f", *target_vector)

        # Build the query with optional filters
        where_clauses = ["COALESCE(w.tombstoned, 0) = 0"]
        params: list = [vec_bytes, fetch_k]

        if plugins is not None:
            placeholders = ",".join("?" for _ in plugins)
            where_clauses.append(f"d.plugin IN ({placeholders})")
            params.extend(plugins)

        if record_types is not None:
            placeholders = ",".join("?" for _ in record_types)
            where_clauses.append(f"d.record_type IN ({placeholders})")
            params.extend(record_types)

        if metadata_filters:
            for key, value in metadata_filters.items():
                if not _SAFE_METADATA_KEY_RE.match(key):
                    raise ValueError(
                        f"Invalid metadata filter key {key!r}: "
                        "only alphanumeric characters and underscores are allowed"
                    )
                where_clauses.append(f"json_extract(d.metadata, '$.{key}') = ?")
                params.append(value)

        extra_where = "AND " + " AND ".join(where_clauses)

        wi = self.WEIGHT_INFLUENCE
        query = f"""
            SELECT d.id, d.uri, d.plugin, d.record_type, d.metadata, v.distance,
                   COALESCE(w.usage_score, 0.0) AS usage_score,
                   COALESCE(w.decay_half_life_days, 0) AS decay_half_life,
                   w.created_at,
                   (v.distance - COALESCE(w.usage_score, 0.0) * {wi}
                    * CASE
                        WHEN w.decay_half_life_days IS NOT NULL
                             AND w.decay_half_life_days > 0
                        THEN POWER(0.5,
                             (JULIANDAY('now') - JULIANDAY(COALESCE(w.created_at, datetime('now'))))
                             / w.decay_half_life_days)
                        ELSE 1.0
                      END
                   ) AS final_rank
            FROM vec_documents v
            JOIN documents d ON v.id = d.id
            LEFT JOIN doc_weights w ON d.id = w.doc_id
            WHERE v.embedding MATCH ? AND k = ?
            {extra_where}
            ORDER BY final_rank ASC
            LIMIT ?
        """
        params.append(limit)

        cursor = self._conn.execute(query, params)

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "id": row[0],
                    "uri": row[1],
                    "plugin": row[2],
                    "record_type": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {},
                    "score": row[5],
                    "usage_score": row[6],
                    "final_rank": row[9],
                }
            )
        return results

    def retrieve_by_weight(
        self,
        limit: int = 5,
        plugins: list[str] | None = None,
        record_types: list[str] | None = None,
        metadata_filters: dict[str, str] | None = None,
    ) -> list[dict]:
        """Retrieves documents ranked by composite weight score (no vector required).

        Results are ranked by usage_score * decay descending. Tombstoned
        documents are always excluded.

        metadata_filters: optional dict of key-value pairs. Each pair becomes
        a json_extract condition (AND semantics). NULL metadata rows are
        excluded when any filter is provided.
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        # Short-circuit: explicit empty list means "match nothing"
        if plugins is not None and len(plugins) == 0:
            return []
        if record_types is not None and len(record_types) == 0:
            return []

        where_clauses = ["COALESCE(w.tombstoned, 0) = 0"]
        params: list = []

        if plugins is not None:
            placeholders = ",".join("?" for _ in plugins)
            where_clauses.append(f"d.plugin IN ({placeholders})")
            params.extend(plugins)

        if record_types is not None:
            placeholders = ",".join("?" for _ in record_types)
            where_clauses.append(f"d.record_type IN ({placeholders})")
            params.extend(record_types)

        if metadata_filters:
            for key, value in metadata_filters.items():
                if not _SAFE_METADATA_KEY_RE.match(key):
                    raise ValueError(
                        f"Invalid metadata filter key {key!r}: "
                        "only alphanumeric characters and underscores are allowed"
                    )
                where_clauses.append(f"json_extract(d.metadata, '$.{key}') = ?")
                params.append(value)

        where_sql = "WHERE " + " AND ".join(where_clauses)
        params.append(limit)

        query = f"""
            SELECT d.id, d.uri, d.plugin, d.record_type, d.metadata,
                   COALESCE(w.usage_score, 0.0) AS usage_score,
                   (COALESCE(w.usage_score, 0.0)
                    * CASE
                        WHEN w.decay_half_life_days IS NOT NULL
                             AND w.decay_half_life_days > 0
                        THEN POWER(0.5,
                             (JULIANDAY('now') - JULIANDAY(COALESCE(w.created_at, datetime('now'))))
                             / w.decay_half_life_days)
                        ELSE 1.0
                      END
                   ) AS weight_rank
            FROM documents d
            LEFT JOIN doc_weights w ON d.id = w.doc_id
            {where_sql}
            ORDER BY weight_rank DESC
            LIMIT ?
        """

        cursor = self._conn.execute(query, params)

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "id": row[0],
                    "uri": row[1],
                    "plugin": row[2],
                    "record_type": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {},
                    "usage_score": row[5],
                    "weight_rank": row[6],
                }
            )
        return results

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
