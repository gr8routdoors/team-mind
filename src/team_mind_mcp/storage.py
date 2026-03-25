import sqlite3
import json
import struct
import sqlite_vec

class StorageAdapter:
    """Embedded SQLite storage for tracking documents and vector embeddings."""

    # Over-fetch multiplier for KNN queries with post-filters.
    # sqlite-vec performs KNN before JOIN/WHERE, so we fetch more
    # candidates and filter in Python to compensate.
    KNN_OVERFETCH_MULTIPLIER = 4

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
                    doctype TEXT NOT NULL DEFAULT '',
                    metadata JSON
                )
            """)

            # Migrate existing databases: add columns if missing
            cursor = self._conn.execute("PRAGMA table_info(documents)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            if "plugin" not in existing_columns:
                self._conn.execute("ALTER TABLE documents ADD COLUMN plugin TEXT NOT NULL DEFAULT ''")
            if "doctype" not in existing_columns:
                self._conn.execute("ALTER TABLE documents ADD COLUMN doctype TEXT NOT NULL DEFAULT ''")

            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_plugin
                ON documents(plugin)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_doctype
                ON documents(doctype)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_plugin_doctype
                ON documents(plugin, doctype)
            """)
            self._conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_documents USING vec0(
                    id INTEGER PRIMARY KEY,
                    embedding float[768]
                )
            """)

    def save_payload(self, uri: str, metadata: dict, vector: list[float],
                     plugin: str, doctype: str) -> int:
        """Saves a document and its embedding vector."""
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO documents (uri, plugin, doctype, metadata) VALUES (?, ?, ?, ?) RETURNING id",
                (uri, plugin, doctype, json.dumps(metadata))
            )
            doc_id = cursor.fetchone()[0]

            vec_bytes = struct.pack(f"{len(vector)}f", *vector)
            self._conn.execute(
                "INSERT INTO vec_documents (id, embedding) VALUES (?, ?)",
                (doc_id, vec_bytes)
            )
            return doc_id

    def retrieve_by_vector_similarity(self, target_vector: list[float], limit: int = 5,
                                      plugins: list[str] | None = None,
                                      doctypes: list[str] | None = None) -> list[dict]:
        """Retrieves documents by KNN similarity search with optional filters.

        Note: sqlite-vec performs KNN *before* filters are applied (post-filter).
        When filters are provided, we over-fetch from the vector index and filter
        in the SQL JOIN. The `limit` is a maximum, not a guarantee, when filters
        are active.
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        # Short-circuit: explicit empty list means "match nothing"
        if plugins is not None and len(plugins) == 0:
            return []
        if doctypes is not None and len(doctypes) == 0:
            return []

        has_filters = plugins is not None or doctypes is not None
        fetch_k = limit * self.KNN_OVERFETCH_MULTIPLIER if has_filters else limit

        vec_bytes = struct.pack(f"{len(target_vector)}f", *target_vector)

        # Build the query with optional filters
        where_clauses = []
        params: list = [vec_bytes, fetch_k]

        if plugins is not None:
            placeholders = ",".join("?" for _ in plugins)
            where_clauses.append(f"d.plugin IN ({placeholders})")
            params.extend(plugins)

        if doctypes is not None:
            placeholders = ",".join("?" for _ in doctypes)
            where_clauses.append(f"d.doctype IN ({placeholders})")
            params.extend(doctypes)

        extra_where = ""
        if where_clauses:
            extra_where = "AND " + " AND ".join(where_clauses)

        query = f"""
            SELECT d.id, d.uri, d.plugin, d.doctype, d.metadata, v.distance
            FROM vec_documents v
            JOIN documents d ON v.id = d.id
            WHERE v.embedding MATCH ? AND k = ?
            {extra_where}
            ORDER BY v.distance
            LIMIT ?
        """
        params.append(limit)

        cursor = self._conn.execute(query, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "uri": row[1],
                "plugin": row[2],
                "doctype": row[3],
                "metadata": json.loads(row[4]) if row[4] else {},
                "score": row[5]
            })
        return results

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
