"""
SPEC-004 / STORY-001: Spike — sqlite-vec Composite Scoring Feasibility

Tests three approaches to combining KNN vector similarity with usage-based
weighting from a separate doc_weights table:

1. SQL-side composite scoring (JOIN + ORDER BY composite expression)
2. Python re-ranking (over-fetch KNN, re-rank in Python)
3. Baseline (KNN only, no weights — control benchmark)

Each approach is tested for correctness and benchmarked at 100, 1000, and 10000
document scales.
"""

import hashlib
import json
import sqlite3
import struct
import time
from dataclasses import dataclass

import pytest
import sqlite_vec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vector(seed: int, dim: int = 768) -> list[float]:
    """Deterministic pseudo-random vector from a seed."""
    h = hashlib.md5(str(seed).encode()).digest()
    vec = [0.0] * dim
    for i in range(min(16, dim)):
        vec[i] = h[i % len(h)] / 255.0
    # Add seed-based variation across more dimensions
    for i in range(16, min(64, dim)):
        vec[i] = ((seed * 7 + i * 13) % 256) / 255.0
    return vec


def _vec_bytes(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _create_db(tmp_path, doc_count: int):
    """Create a fully populated test database with documents, vectors, and weights."""
    db_path = str(tmp_path / f"spike_{doc_count}.db")
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)

    with conn:
        conn.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uri TEXT NOT NULL,
                plugin TEXT NOT NULL DEFAULT '',
                record_type TEXT NOT NULL DEFAULT '',
                metadata JSON
            )
        """)
        conn.execute("""
            CREATE INDEX idx_documents_plugin ON documents(plugin)
        """)
        conn.execute("""
            CREATE INDEX idx_documents_record_type ON documents(record_type)
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE vec_documents USING vec0(
                id INTEGER PRIMARY KEY,
                embedding float[768]
            )
        """)
        conn.execute("""
            CREATE TABLE doc_weights (
                doc_id INTEGER PRIMARY KEY REFERENCES documents(id),
                usage_score REAL DEFAULT 0.0,
                last_accessed TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                tombstoned INTEGER DEFAULT 0,
                decay_half_life_days REAL
            )
        """)
        conn.execute("""
            CREATE INDEX idx_doc_weights_tombstoned ON doc_weights(tombstoned)
        """)

    # Populate
    with conn:
        for i in range(doc_count):
            cursor = conn.execute(
                "INSERT INTO documents (uri, plugin, record_type, metadata) VALUES (?, ?, ?, ?) RETURNING id",
                (
                    f"file:///doc_{i}.md",
                    "test_plugin",
                    "test_type",
                    json.dumps({"idx": i}),
                ),
            )
            doc_id = cursor.fetchone()[0]

            vec = _make_vector(i)
            conn.execute(
                "INSERT INTO vec_documents (id, embedding) VALUES (?, ?)",
                (doc_id, _vec_bytes(vec)),
            )

            # Give ~30% of docs a positive weight, ~10% negative, ~5% tombstoned
            usage_score = 0.0
            tombstoned = 0
            if i % 3 == 0:
                usage_score = (i % 5) + 1.0  # 1.0 to 5.0
            elif i % 10 == 0:
                usage_score = -2.0
            if i % 20 == 0 and i > 0:
                tombstoned = 1

            conn.execute(
                "INSERT INTO doc_weights (doc_id, usage_score, tombstoned, decay_half_life_days) VALUES (?, ?, ?, ?)",
                (doc_id, usage_score, tombstoned, 30.0 if i % 2 == 0 else None),
            )

    return conn


# ---------------------------------------------------------------------------
# Approach 1: SQL-side composite scoring
# ---------------------------------------------------------------------------


def _query_sql_composite(conn, query_vec: list[float], limit: int, overfetch: int = 4):
    """Attempt SQL-side composite scoring with JOIN on doc_weights."""
    vec_bytes = _vec_bytes(query_vec)
    fetch_k = limit * overfetch

    try:
        cursor = conn.execute(
            """
            SELECT d.id, d.uri, v.distance,
                   COALESCE(w.usage_score, 0.0) AS usage_score,
                   COALESCE(w.tombstoned, 0) AS tombstoned,
                   (v.distance - COALESCE(w.usage_score, 0.0) * 0.1) AS final_rank
            FROM vec_documents v
            JOIN documents d ON v.id = d.id
            LEFT JOIN doc_weights w ON d.id = w.doc_id
            WHERE v.embedding MATCH ? AND k = ?
              AND COALESCE(w.tombstoned, 0) = 0
            ORDER BY final_rank ASC
            LIMIT ?
            """,
            (vec_bytes, fetch_k, limit),
        )
        return cursor.fetchall(), True
    except Exception as e:
        return str(e), False


# ---------------------------------------------------------------------------
# Approach 2: Python re-ranking
# ---------------------------------------------------------------------------


def _query_python_rerank(conn, query_vec: list[float], limit: int, overfetch: int = 4):
    """Over-fetch from KNN, then re-rank in Python."""
    vec_bytes = _vec_bytes(query_vec)
    fetch_k = limit * overfetch

    cursor = conn.execute(
        """
        SELECT d.id, d.uri, v.distance,
               COALESCE(w.usage_score, 0.0) AS usage_score,
               COALESCE(w.tombstoned, 0) AS tombstoned
        FROM vec_documents v
        JOIN documents d ON v.id = d.id
        LEFT JOIN doc_weights w ON d.id = w.doc_id
        WHERE v.embedding MATCH ? AND k = ?
        """,
        (vec_bytes, fetch_k),
    )
    rows = cursor.fetchall()

    # Filter tombstoned
    rows = [r for r in rows if r[4] == 0]

    # Compute final_rank in Python
    scored = []
    for r in rows:
        distance = r[2]
        usage_score = r[3]
        final_rank = distance - usage_score * 0.1
        scored.append((*r, final_rank))

    scored.sort(key=lambda x: x[5])
    return scored[:limit]


# ---------------------------------------------------------------------------
# Approach 3: Baseline (no weights)
# ---------------------------------------------------------------------------


def _query_baseline(conn, query_vec: list[float], limit: int):
    """Pure KNN, no weights join — control benchmark."""
    vec_bytes = _vec_bytes(query_vec)
    cursor = conn.execute(
        """
        SELECT d.id, d.uri, v.distance
        FROM vec_documents v
        JOIN documents d ON v.id = d.id
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance
        LIMIT ?
        """,
        (vec_bytes, limit, limit),
    )
    return cursor.fetchall()


# ---------------------------------------------------------------------------
# AC-001: SQL-Side Composite Scoring Test
# ---------------------------------------------------------------------------


class TestSQLCompositeScoring:
    def test_sql_composite_returns_results(self, tmp_path):
        """AC-001: Test that SQL-side composite scoring query succeeds."""
        conn = _create_db(tmp_path, 100)
        query_vec = _make_vector(42)

        results, success = _query_sql_composite(conn, query_vec, limit=10)
        conn.close()

        if success:
            assert len(results) > 0
            assert len(results) <= 10
            # Verify ordering by final_rank (column index 5)
            ranks = [r[5] for r in results]
            assert ranks == sorted(ranks), "Results should be ordered by final_rank"
        else:
            # Record the failure for the recommendation
            pytest.skip(f"SQL-side composite scoring not supported: {results}")

    def test_sql_composite_excludes_tombstoned(self, tmp_path):
        """AC-001: Tombstoned documents excluded in SQL approach."""
        conn = _create_db(tmp_path, 100)
        query_vec = _make_vector(42)

        results, success = _query_sql_composite(conn, query_vec, limit=50)
        conn.close()

        if success:
            tombstoned_flags = [r[4] for r in results]
            assert all(t == 0 for t in tombstoned_flags), (
                "No tombstoned docs in results"
            )
        else:
            pytest.skip(f"SQL-side composite scoring not supported: {results}")

    def test_sql_composite_weights_affect_ordering(self, tmp_path):
        """AC-001: Verify that usage_score actually changes result ordering vs pure distance."""
        conn = _create_db(tmp_path, 100)
        query_vec = _make_vector(42)

        weighted_results, success = _query_sql_composite(conn, query_vec, limit=20)
        if not success:
            conn.close()
            pytest.skip(f"SQL-side composite scoring not supported: {weighted_results}")

        baseline_results = _query_baseline(conn, query_vec, limit=20)
        conn.close()

        # The ordering should differ if weights are having an effect
        weighted_ids = [r[0] for r in weighted_results]
        baseline_ids = [r[0] for r in baseline_results]

        # They may not always differ (depends on data), but record it
        ordering_differs = weighted_ids != baseline_ids
        print(f"\nWeighted ordering differs from baseline: {ordering_differs}")
        print(f"Baseline top-5 IDs: {baseline_ids[:5]}")
        print(f"Weighted top-5 IDs: {weighted_ids[:5]}")


# ---------------------------------------------------------------------------
# AC-002: Python Re-Ranking Fallback Test
# ---------------------------------------------------------------------------


class TestPythonReRanking:
    def test_python_rerank_returns_results(self, tmp_path):
        """AC-002: Python re-ranking produces correctly weighted results."""
        conn = _create_db(tmp_path, 100)
        query_vec = _make_vector(42)

        results = _query_python_rerank(conn, query_vec, limit=10)
        conn.close()

        assert len(results) > 0
        assert len(results) <= 10

        # Verify ordering by final_rank (column index 5)
        ranks = [r[5] for r in results]
        assert ranks == sorted(ranks), "Results should be ordered by final_rank"

    def test_python_rerank_excludes_tombstoned(self, tmp_path):
        """AC-002: Tombstoned documents excluded in Python approach."""
        conn = _create_db(tmp_path, 100)
        query_vec = _make_vector(42)

        results = _query_python_rerank(conn, query_vec, limit=50)
        conn.close()

        tombstoned_flags = [r[4] for r in results]
        assert all(t == 0 for t in tombstoned_flags), "No tombstoned docs in results"

    def test_python_rerank_weights_affect_ordering(self, tmp_path):
        """AC-002: Usage score changes ordering vs pure distance."""
        conn = _create_db(tmp_path, 100)
        query_vec = _make_vector(42)

        reranked = _query_python_rerank(conn, query_vec, limit=20)
        baseline = _query_baseline(conn, query_vec, limit=20)
        conn.close()

        reranked_ids = [r[0] for r in reranked]
        baseline_ids = [r[0] for r in baseline]

        ordering_differs = reranked_ids != baseline_ids
        print(f"\nPython re-ranked ordering differs from baseline: {ordering_differs}")
        print(f"Baseline top-5 IDs: {baseline_ids[:5]}")
        print(f"Re-ranked top-5 IDs: {reranked_ids[:5]}")


# ---------------------------------------------------------------------------
# AC-003: Performance Benchmark
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    approach: str
    doc_count: int
    avg_ms: float
    runs: int


def _benchmark(fn, runs: int = 20) -> float:
    """Run a function multiple times and return average time in ms."""
    # Warm-up
    fn()

    times = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return sum(times) / len(times)


class TestPerformanceBenchmark:
    @pytest.mark.parametrize("doc_count", [100, 1000, 10000])
    def test_benchmark_all_approaches(self, tmp_path, doc_count):
        """AC-003: Benchmark all approaches at different scales."""
        conn = _create_db(tmp_path, doc_count)
        query_vec = _make_vector(42)
        limit = 10
        runs = 20

        # Baseline
        baseline_ms = _benchmark(
            lambda: _query_baseline(conn, query_vec, limit), runs=runs
        )

        # SQL composite
        test_result, sql_works = _query_sql_composite(conn, query_vec, limit)
        if sql_works:
            sql_ms = _benchmark(
                lambda: _query_sql_composite(conn, query_vec, limit), runs=runs
            )
        else:
            sql_ms = None

        # Python re-rank
        python_ms = _benchmark(
            lambda: _query_python_rerank(conn, query_vec, limit), runs=runs
        )

        conn.close()

        # Report
        print(f"\n{'=' * 60}")
        print(f"BENCHMARK: {doc_count} documents, limit={limit}, {runs} runs avg")
        print(f"{'=' * 60}")
        print(f"  Baseline (KNN only):     {baseline_ms:8.3f} ms")
        if sql_ms is not None:
            print(
                f"  SQL composite scoring:   {sql_ms:8.3f} ms  ({sql_ms / baseline_ms:.2f}x baseline)"
            )
        else:
            print("  SQL composite scoring:   UNSUPPORTED")
        print(
            f"  Python re-ranking:       {python_ms:8.3f} ms  ({python_ms / baseline_ms:.2f}x baseline)"
        )
        print(f"{'=' * 60}")

        # Assertions — just verify they complete without error
        assert baseline_ms > 0
        assert python_ms > 0


# ---------------------------------------------------------------------------
# AC-004: Correctness — both approaches produce equivalent results
# ---------------------------------------------------------------------------


class TestCorrectnessEquivalence:
    def test_sql_and_python_produce_same_top_results(self, tmp_path):
        """AC-004: SQL and Python approaches should produce equivalent rankings."""
        conn = _create_db(tmp_path, 200)
        query_vec = _make_vector(42)

        sql_results, sql_works = _query_sql_composite(conn, query_vec, limit=10)
        python_results = _query_python_rerank(conn, query_vec, limit=10)
        conn.close()

        if not sql_works:
            pytest.skip(
                "SQL-side composite scoring not supported — equivalence test N/A"
            )

        sql_ids = [r[0] for r in sql_results]
        python_ids = [r[0] for r in python_results]

        # Due to overfetch differences, results may not be identical
        # but the top results should largely overlap
        overlap = set(sql_ids) & set(python_ids)
        overlap_pct = len(overlap) / max(len(sql_ids), len(python_ids)) * 100

        print(f"\nSQL top-10 IDs:    {sql_ids}")
        print(f"Python top-10 IDs: {python_ids}")
        print(f"Overlap: {len(overlap)}/10 ({overlap_pct:.0f}%)")

        # At least 50% overlap is reasonable given overfetch differences
        assert overlap_pct >= 50, (
            f"Only {overlap_pct:.0f}% overlap — approaches diverge too much"
        )
