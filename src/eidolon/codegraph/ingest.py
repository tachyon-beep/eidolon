from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import psycopg
from psycopg import sql

DEFAULT_DSN = "postgresql://eidolon:password@localhost:6543/eidolon"


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS scan_runs (
        id SERIAL PRIMARY KEY,
        repo_root TEXT NOT NULL,
        summary JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS file_metrics (
        id SERIAL PRIMARY KEY,
        run_id INTEGER NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
        path TEXT NOT NULL,
        sha256 CHAR(64) NOT NULL,
        size_bytes BIGINT NOT NULL,
        sloc INTEGER NOT NULL,
        class_count INTEGER NOT NULL,
        function_count INTEGER NOT NULL,
        import_count INTEGER NOT NULL,
        parse_ms DOUBLE PRECISION NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_file_metrics_run_path
        ON file_metrics(run_id, path)
    """,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest scanner JSON into Postgres")
    parser.add_argument("records", type=Path, help="Path to JSONL file emitted by eidolon-codegraph-scan --records")
    parser.add_argument(
        "--summary",
        type=Path,
        required=True,
        help="Summary JSON file emitted by eidolon-codegraph-scan --summary",
    )
    parser.add_argument(
        "--dsn",
        default=DEFAULT_DSN,
        help=f"Postgres DSN (default: {DEFAULT_DSN})",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=1000,
        help="Batch size for inserts",
    )
    return parser.parse_args()


def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        for stmt in SCHEMA_STATEMENTS:
            cur.execute(stmt)
    conn.commit()


def load_records(path: Path) -> Iterable[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def insert_run(conn: psycopg.Connection, repo_root: str, summary: dict) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scan_runs (repo_root, summary) VALUES (%s, %s) RETURNING id",
            (repo_root, json.dumps(summary) if summary else None),
        )
        run_id = cur.fetchone()[0]
    conn.commit()
    return run_id


def insert_file_metrics(conn: psycopg.Connection, run_id: int, records: Iterable[dict[str, object]], batch_size: int = 1000) -> None:
    rows = []
    with conn.cursor() as cur:
        for record in records:
            rows.append(
                (
                    run_id,
                    record["path"],
                    record["sha256"],
                    int(record["size_bytes"]),
                    int(record["sloc"]),
                    int(record["class_count"]),
                    int(record["function_count"]),
                    int(record["import_count"]),
                    float(record["parse_ms"]),
                )
            )
            if len(rows) >= batch_size:
                cur.executemany(
                    """
                    INSERT INTO file_metrics (
                        run_id, path, sha256, size_bytes, sloc,
                        class_count, function_count, import_count, parse_ms
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    rows,
                )
                rows.clear()
        if rows:
            cur.executemany(
                """
                INSERT INTO file_metrics (
                    run_id, path, sha256, size_bytes, sloc,
                    class_count, function_count, import_count, parse_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                rows,
            )
    conn.commit()


def summary_from_file(path: Path | None) -> dict | None:
    if not path:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    records_path = args.records.resolve()
    summary = summary_from_file(args.summary)
    if not summary:
        raise SystemExit("Summary JSON is required to determine repo_root.")
    repo_root = summary.get("repo_root", "")
    if not repo_root:
        raise SystemExit("Summary JSON missing repo_root.")

    with psycopg.connect(args.dsn) as conn:
        ensure_schema(conn)
        run_id = insert_run(conn, repo_root, summary)
        insert_file_metrics(conn, run_id, load_records(records_path), batch_size=args.batch)
        print(f"Inserted run {run_id} with records from {records_path}")


if __name__ == "__main__":  # pragma: no cover
    main()
