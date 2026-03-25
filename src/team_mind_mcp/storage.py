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
                    doctype TEXT NOT NULL DEFAULT '',
                    metadata JSON
                )
            """)

            # Migrate existing databases: add columns if missing
            cursor = self._conn.execute("PRAGMA table_info(documents)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            if "plugin" not in existing_columns:
                self._conn.execute(
                    "ALTER TABLE documents ADD COLUMN plugin TEXT NOT NULL DEFAULT ''"
                )
            if "doctype" not in existing_columns:
                self._conn.execute(
                    "ALTER TABLE documents ADD COLUMN doctype TEXT NOT NULL DEFAULT ''"
                )

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

            # Weighting tables
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS doc_weights (
                    doc_id INTEGER PRIMARY KEY REFERENCES documents(id),
                    usage_score REAL DEFAULT 0.0,
                    last_accessed TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    tombstoned INTEGER DEFAULT 0,
                    decay_half_life_days REAL
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_doc_weights_tombstoned
                ON doc_weights(tombstoned)
            """)

    def save_payload(
        self,
        uri: str,
        metadata: dict,
        vector: list[float],
        plugin: str,
        doctype: str,
        decay_half_life_days: float | None = None,
    ) -> int:
        """Saves a document, its embedding vector, and initializes its weight row."""
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO documents (uri, plugin, doctype, metadata) VALUES (?, ?, ?, ?) RETURNING id",
                (uri, plugin, doctype, json.dumps(metadata)),
            )
            doc_id = cursor.fetchone()[0]

            vec_bytes = struct.pack(f"{len(vector)}f", *vector)
            self._conn.execute(
                "INSERT INTO vec_documents (id, embedding) VALUES (?, ?)",
                (doc_id, vec_bytes),
            )

            # Auto-create weight row
            self._conn.execute(
                "INSERT INTO doc_weights (doc_id, decay_half_life_days) VALUES (?, ?)",
                (doc_id, decay_half_life_days),
            )

            return doc_id

    def update_weight(
        self,
        doc_id: int,
        signal: int,
        tombstone: bool | None = None,
    ) -> dict:
        """Apply a feedback signal to a document's weight. Returns updated weight info."""
        if self._conn is None:
            raise RuntimeError("Database not initialized")

        with self._conn:
            # Verify doc exists
            row = self._conn.execute(
                "SELECT doc_id, usage_score, tombstoned FROM doc_weights WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"No weight entry for doc_id={doc_id}")

            new_score = row[1] + signal

            if tombstone is not None:
                self._conn.execute(
                    """UPDATE doc_weights
                       SET usage_score = ?, last_accessed = datetime('now'),
                           tombstoned = ?
                       WHERE doc_id = ?""",
                    (new_score, 1 if tombstone else 0, doc_id),
                )
            else:
                self._conn.execute(
                    """UPDATE doc_weights
                       SET usage_score = ?, last_accessed = datetime('now')
                       WHERE doc_id = ?""",
                    (new_score, doc_id),
                )

            updated = self._conn.execute(
                "SELECT usage_score, tombstoned, last_accessed FROM doc_weights WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()

            return {
                "doc_id": doc_id,
                "usage_score": updated[0],
                "tombstoned": bool(updated[1]),
                "last_accessed": updated[2],
            }

    def retrieve_by_vector_similarity(
        self,
        target_vector: list[float],
        limit: int = 5,
        plugins: list[str] | None = None,
        doctypes: list[str] | None = None,
    ) -> list[dict]:
        """Retrieves documents by KNN similarity with composite scoring.

        Combines vector distance with usage-based weighting and time decay.
        Tombstoned documents are always excluded. When no weights exist,
        results are ranked by pure vector distance (equivalent to no weighting).
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
        where_clauses = ["COALESCE(w.tombstoned, 0) = 0"]
        params: list = [vec_bytes, fetch_k]

        if plugins is not None:
            placeholders = ",".join("?" for _ in plugins)
            where_clauses.append(f"d.plugin IN ({placeholders})")
            params.extend(plugins)

        if doctypes is not None:
            placeholders = ",".join("?" for _ in doctypes)
            where_clauses.append(f"d.doctype IN ({placeholders})")
            params.extend(doctypes)

        extra_where = "AND " + " AND ".join(where_clauses)

        wi = self.WEIGHT_INFLUENCE
        query = f"""
            SELECT d.id, d.uri, d.plugin, d.doctype, d.metadata, v.distance,
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
                    "doctype": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {},
                    "score": row[5],
                    "usage_score": row[6],
                    "final_rank": row[9],
                }
            )
        return results

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
