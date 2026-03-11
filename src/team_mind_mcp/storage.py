import sqlite3
import json
import struct
import sqlite_vec

class StorageAdapter:
    """Embedded SQLite storage for tracking documents and vector embeddings."""

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
                    uri TEXT UNIQUE NOT NULL,
                    metadata JSON
                )
            """)
            self._conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_documents USING vec0(
                    id INTEGER PRIMARY KEY,
                    embedding float[768]
                )
            """)

    def save_payload(self, uri: str, metadata: dict, vector: list[float]) -> int:
        """Saves a document and its embedding vector."""
        if self._conn is None:
            raise RuntimeError("Database not initialized")
            
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO documents (uri, metadata) VALUES (?, ?) RETURNING id",
                (uri, json.dumps(metadata))
            )
            doc_id = cursor.fetchone()[0]
            
            vec_bytes = struct.pack(f"{len(vector)}f", *vector)
            self._conn.execute(
                "INSERT INTO vec_documents (id, embedding) VALUES (?, ?)",
                (doc_id, vec_bytes)
            )
            return doc_id

    def retrieve_by_vector_similarity(self, target_vector: list[float], limit: int = 5) -> list[dict]:
        """Retrieves documents by KNN similarity search."""
        if self._conn is None:
            raise RuntimeError("Database not initialized")
            
        vec_bytes = struct.pack(f"{len(target_vector)}f", *target_vector)
        cursor = self._conn.execute(
            """
            SELECT d.id, d.uri, d.metadata, v.distance
            FROM vec_documents v
            JOIN documents d ON v.id = d.id
            WHERE v.embedding MATCH ? AND k = ?
            ORDER BY v.distance
            """,
            (vec_bytes, limit)
        )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "uri": row[1],
                "metadata": json.loads(row[2]) if row[2] else {},
                "score": row[3]
            })
        return results

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
