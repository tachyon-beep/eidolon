from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import psycopg
from psycopg import Cursor

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
        boundary TEXT NOT NULL,
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
    CREATE TABLE IF NOT EXISTS file_imports (
        run_id INTEGER NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
        path TEXT NOT NULL,
        import_name TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_file_imports_run_path
        ON file_imports(run_id, path)
    """,
    """
    CREATE TABLE IF NOT EXISTS function_defs (
        run_id INTEGER NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
        path TEXT NOT NULL,
        function_name TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_function_defs_run_path
        ON function_defs(run_id, path)
    """,
    """
    CREATE TABLE IF NOT EXISTS function_calls (
        run_id INTEGER NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
        path TEXT NOT NULL,
        callee_name TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_function_calls_run_path
        ON function_calls(run_id, path)
    """,
    """
    CREATE TABLE IF NOT EXISTS import_edges (
        run_id INTEGER NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
        source_boundary TEXT NOT NULL,
        target_name TEXT NOT NULL,
        usage_count INTEGER NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_import_edges_run_source
        ON import_edges(run_id, source_boundary)
    """,
    """
    CREATE TABLE IF NOT EXISTS boundary_stats (
        run_id INTEGER NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
        boundary TEXT NOT NULL,
        module_count INTEGER NOT NULL,
        total_sloc BIGINT NOT NULL,
        total_functions BIGINT NOT NULL,
        total_classes BIGINT NOT NULL,
        PRIMARY KEY (run_id, boundary)
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
    metric_rows = []
    import_rows = []
    function_rows = []
    call_rows = []
    with conn.cursor() as cur:
        for record in records:
            metric_rows.append(
                (
                    run_id,
                    record["path"],
                    record.get("package", record["path"].split("/", 1)[0]),
                    record["sha256"],
                    int(record["size_bytes"]),
                    int(record["sloc"]),
                    int(record["class_count"]),
                    int(record["function_count"]),
                    int(record["import_count"]),
                    float(record["parse_ms"]),
                )
            )
            for import_name in record.get("imports", []):
                import_rows.append((run_id, record["path"], import_name))
            for fn_name in record.get("functions", []):
                function_rows.append((run_id, record["path"], fn_name))
            for call_name in record.get("calls", []):
                call_rows.append((run_id, record["path"], call_name))
            if len(metric_rows) >= batch_size:
                _flush_metrics(cur, metric_rows)
                metric_rows.clear()
            if len(import_rows) >= batch_size:
                _flush_imports(cur, import_rows)
                import_rows.clear()
            if len(function_rows) >= batch_size:
                _flush_functions(cur, function_rows)
                function_rows.clear()
            if len(call_rows) >= batch_size:
                _flush_calls(cur, call_rows)
                call_rows.clear()
        if metric_rows:
            _flush_metrics(cur, metric_rows)
        if import_rows:
            _flush_imports(cur, import_rows)
        if function_rows:
            _flush_functions(cur, function_rows)
        if call_rows:
            _flush_calls(cur, call_rows)
    conn.commit()


def _flush_metrics(cur: psycopg.Cursor, rows: list[tuple]) -> None:
    cur.executemany(
        """
        INSERT INTO file_metrics (
            run_id, path, boundary, sha256, size_bytes, sloc,
            class_count, function_count, import_count, parse_ms
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows,
    )


def _flush_imports(cur: psycopg.Cursor, rows: list[tuple]) -> None:
    cur.executemany(
        """
        INSERT INTO file_imports (run_id, path, import_name)
        VALUES (%s,%s,%s)
        """,
        rows,
    )


def _flush_functions(cur: psycopg.Cursor, rows: list[tuple]) -> None:
    cur.executemany(
        """
        INSERT INTO function_defs (run_id, path, function_name)
        VALUES (%s,%s,%s)
        """,
        rows,
    )


def _flush_calls(cur: psycopg.Cursor, rows: list[tuple]) -> None:
    cur.executemany(
        """
        INSERT INTO function_calls (run_id, path, callee_name)
        VALUES (%s,%s,%s)
        """,
        rows,
    )


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
        build_import_edges(conn, run_id)
        build_boundary_stats(conn, run_id)
        print(f"Inserted run {run_id} with records from {records_path}")


def build_import_edges(conn: psycopg.Connection, run_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM import_edges WHERE run_id = %s", (run_id,))
        cur.execute(
            """
            INSERT INTO import_edges (run_id, source_boundary, target_name, usage_count)
            SELECT %s AS run_id,
                   fm.boundary AS source_boundary,
                   split_part(fi.import_name, '.', 1) AS target_name,
                   COUNT(*) AS usage_count
            FROM file_imports fi
            JOIN file_metrics fm ON fm.run_id = fi.run_id AND fm.path = fi.path
            WHERE fi.run_id = %s
            GROUP BY fm.boundary, split_part(fi.import_name, '.', 1)
            """,
            (run_id, run_id),
        )
    conn.commit()


def build_boundary_stats(conn: psycopg.Connection, run_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM boundary_stats WHERE run_id = %s", (run_id,))
        cur.execute(
            """
            INSERT INTO boundary_stats (run_id, boundary, module_count, total_sloc, total_functions, total_classes)
            SELECT %s AS run_id,
                   boundary,
                   COUNT(*) AS module_count,
                   SUM(sloc) AS total_sloc,
                   SUM(function_count) AS total_functions,
                   SUM(class_count) AS total_classes
            FROM file_metrics
            WHERE run_id = %s
            GROUP BY boundary
            """,
            (run_id, run_id),
        )
    conn.commit()


if __name__ == "__main__":  # pragma: no cover
    main()
