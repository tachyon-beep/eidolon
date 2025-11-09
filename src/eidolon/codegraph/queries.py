from __future__ import annotations

import argparse
import json
import time
from typing import Any

import psycopg

DEFAULT_DSN = "postgresql://eidolon:password@localhost:6543/eidolon"


QUERIES = {
    "Q1_top_sloc": """
        SELECT path, sloc, class_count, function_count
        FROM file_metrics
        WHERE run_id = %s
        ORDER BY sloc DESC
        LIMIT 50
    """,
    "Q2_top_functions": """
        SELECT path, function_count
        FROM file_metrics
        WHERE run_id = %s
        ORDER BY function_count DESC
        LIMIT 50
    """,
    "Q3_heavy_modules_count": """
        SELECT COUNT(*)
        FROM file_metrics
        WHERE run_id = %s AND sloc > %s
    """,
    "Q4_package_summary": """
        SELECT split_part(path, '/', 1) AS package, COUNT(*) AS modules, SUM(sloc) AS total_sloc
        FROM file_metrics
        WHERE run_id = %s
        GROUP BY package
        ORDER BY total_sloc DESC
        LIMIT 20
    """,
    "Q5_avg_parse_time": """
        SELECT AVG(parse_ms)
        FROM file_metrics
        WHERE run_id = %s
    """,
    "Q6_sloc_p95": """
        SELECT percentile_disc(0.95) WITHIN GROUP (ORDER BY sloc)
        FROM file_metrics
        WHERE run_id = %s
    """,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CodeGraph query benchmarks")
    parser.add_argument("--run-id", type=int, default=None, help="scan_runs.id to benchmark (default latest)")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--threshold", type=int, default=1000, help="SLOC threshold for Q3")
    return parser.parse_args()


def resolve_run_id(conn: psycopg.Connection, run_id: int | None) -> int:
    if run_id is not None:
        return run_id
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM scan_runs ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            raise SystemExit("No scan_runs found")
        return row[0]


def run_queries(conn: psycopg.Connection, run_id: int, threshold: int) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for name, query in QUERIES.items():
        params: tuple[Any, ...]
        if name == "Q3_heavy_modules_count":
            params = (run_id, threshold)
        else:
            params = (run_id,)
        start = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute(query, params)
            # only fetch when needed to avoid loading huge result sets
            if cur.description:
                cur.fetchall()
        duration = (time.perf_counter() - start) * 1000
        results[name] = {"duration_ms": duration}
    return results


def main() -> None:
    args = parse_args()
    with psycopg.connect(args.dsn) as conn:
        run_id = resolve_run_id(conn, args.run_id)
        results = run_queries(conn, run_id, args.threshold)
        print(json.dumps({"run_id": run_id, "results": results}, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
