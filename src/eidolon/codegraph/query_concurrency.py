from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import psycopg
from psycopg_pool import ConnectionPool

from .queries import QUERIES, resolve_run_id

DEFAULT_DSN = "postgresql://eidolon:password@localhost:6543/eidolon"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CodeGraph queries under concurrent load")
    parser.add_argument("--run-id", type=int, default=None, help="scan_runs.id to benchmark (default latest)")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--clients", type=int, default=8, help="Number of concurrent clients")
    parser.add_argument("--iterations", type=int, default=10, help="Iterations per client")
    parser.add_argument("--threshold", type=int, default=1000, help="SLOC threshold for Q3")
    return parser.parse_args()


def run_query_set(conn: psycopg.Connection, run_id: int, threshold: int) -> dict[str, float]:
    timings: dict[str, float] = {}
    for name, query in QUERIES.items():
        params: tuple[Any, ...]
        if name == "Q3_heavy_modules_count":
            params = (run_id, threshold)
        else:
            params = (run_id,)
        start = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                cur.fetchall()
        duration = (time.perf_counter() - start) * 1000
        timings[name] = duration
    return timings


def main() -> None:
    args = parse_args()
    pool = ConnectionPool(conninfo=args.dsn, min_size=1, max_size=args.clients)
    with pool.connection() as conn:
        run_id = resolve_run_id(conn, args.run_id)

    durations: dict[str, list[float]] = {name: [] for name in QUERIES.keys()}

    def worker() -> None:
        for _ in range(args.iterations):
            with pool.connection() as conn:
                timings = run_query_set(conn, run_id, args.threshold)
                for name, duration in timings.items():
                    durations[name].append(duration)

    with ThreadPoolExecutor(max_workers=args.clients) as executor:
        futures = [executor.submit(worker) for _ in range(args.clients)]
        for future in as_completed(futures):
            future.result()

    summary = {
        "run_id": run_id,
        "clients": args.clients,
        "iterations": args.iterations,
        "results": {
            name: {
                "count": len(vals),
                "avg_ms": sum(vals) / len(vals) if vals else 0.0,
                "p95_ms": percentile(vals, 0.95),
                "max_ms": max(vals) if vals else 0.0,
            }
            for name, vals in durations.items()
        },
    }
    print(json.dumps(summary, indent=2))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    pct = max(0.0, min(1.0, pct))
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[int(k)]
    d0 = ordered[f] * (c - k)
    d1 = ordered[c] * (k - f)
    return d0 + d1


if __name__ == "__main__":  # pragma: no cover
    main()
