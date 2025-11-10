from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable

import psycopg

from eidolon.codegraph.ingest import (
    build_boundary_stats,
    build_import_edges,
    ensure_schema,
    insert_file_metrics,
    insert_run,
    load_records,
)
from eidolon.codegraph.scanner import CodeGraphScanner

from .drift_job import DriftJob
from .gatecheck_job import GateCheckRunner


ScannerFn = Callable[[Path, Path, Path, dict[str, Any]], dict[str, Any]]
IngestFn = Callable[[dict[str, Any], Path, str], int]
DriftFn = Callable[[Path, int, str], dict[str, Any]]
GateFn = Callable[[Path, int, str, list[str] | None, list[str] | None], dict[str, Any]]


def default_scan(repo: Path, records_path: Path, summary_path: Path, scan_opts: dict[str, Any]) -> dict[str, Any]:
    scanner = CodeGraphScanner(
        repo,
        exclude_dirs=scan_opts.get("exclude") or (),
        follow_symlinks=scan_opts.get("follow_symlinks", False),
    )
    report = scanner.scan(records_path=records_path)
    summary_path.write_text(report.to_json(), encoding="utf-8")
    return json.loads(report.to_json())


def default_ingest(summary: dict[str, Any], records_path: Path, dsn: str) -> int:
    repo_root = summary.get("repo_root")
    if not repo_root:
        raise SystemExit("Summary JSON missing repo_root; cannot ingest.")
    with psycopg.connect(dsn) as conn:
        ensure_schema(conn)
        run_id = insert_run(conn, repo_root, summary)
        insert_file_metrics(conn, run_id, load_records(records_path))
        build_import_edges(conn, run_id)
        build_boundary_stats(conn, run_id)
        return run_id


def default_drift(rulepack_path: Path, run_id: int, dsn: str) -> dict[str, Any]:
    job = DriftJob(dsn=dsn)
    return job.run(rulepack_path=rulepack_path, run_id=run_id, record=True)


def default_gate(rulepack_path: Path, run_id: int, dsn: str, changed_paths: list[str] | None, changed_boundaries: list[str] | None) -> dict[str, Any]:
    runner = GateCheckRunner(
        dsn=dsn,
        changed_paths=changed_paths,
        changed_boundaries=changed_boundaries,
    )
    return runner.run(rulepack_path=rulepack_path, run_id=run_id, record=True, context={"run_id": run_id})


class RulepackPipeline:
    def __init__(
        self,
        *,
        scan_fn: ScannerFn = default_scan,
        ingest_fn: IngestFn = default_ingest,
        drift_fn: DriftFn = default_drift,
        gate_fn: GateFn = default_gate,
    ) -> None:
        self.scan_fn = scan_fn
        self.ingest_fn = ingest_fn
        self.drift_fn = drift_fn
        self.gate_fn = gate_fn

    def run(
        self,
        repo: Path,
        rulepack: Path,
        *,
        dsn: str,
        changed_paths: list[str] | None = None,
        changed_boundaries: list[str] | None = None,
        skip_gatecheck: bool = False,
        skip_drift: bool = False,
        scan_opts: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scan_opts = scan_opts or {}
        with tempfile.TemporaryDirectory() as tmpdir:
            records_path = Path(tmpdir) / "records.jsonl"
            summary_path = Path(tmpdir) / "summary.json"
            summary = self.scan_fn(repo, records_path, summary_path, scan_opts)
            run_id = self.ingest_fn(summary, records_path, dsn)
            output: dict[str, Any] = {
                "run_id": run_id,
                "repo_root": summary.get("repo_root"),
            }
            if not skip_drift:
                output["drift"] = self.drift_fn(rulepack, run_id, dsn)
            if not skip_gatecheck:
                output["gatecheck"] = self.gate_fn(rulepack, run_id, dsn, changed_paths, changed_boundaries)
            return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run scanner → ingest → rulepack drift/gate pipeline")
    parser.add_argument("repo", type=Path, help="Repository path to scan")
    parser.add_argument("--rulepack", type=Path, required=True, help="Rulepack YAML file to evaluate")
    parser.add_argument("--dsn", default="postgresql://eidolon:password@localhost:6543/eidolon", help="Postgres DSN")
    parser.add_argument("--skip-drift", action="store_true", help="Skip the drift evaluation step")
    parser.add_argument("--skip-gatecheck", action="store_true", help="Skip the GateCheck evaluation step")
    parser.add_argument("--changed-path", action="append", dest="changed_paths", help="Changed path glob (GateCheck filter)")
    parser.add_argument("--changed-boundary", action="append", dest="changed_boundaries", help="Changed boundary glob (GateCheck filter)")
    parser.add_argument("--follow-symlinks", action="store_true", help="Pass through to scanner")
    parser.add_argument("--exclude", action="append", help="Additional directories to exclude from scan")
    parser.add_argument("--output", type=Path, help="Optional JSON file to write full pipeline output")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    pipeline = RulepackPipeline()
    result = pipeline.run(
        repo=args.repo,
        rulepack=args.rulepack,
        dsn=args.dsn,
        changed_paths=args.changed_paths,
        changed_boundaries=args.changed_boundaries,
        skip_gatecheck=args.skip_gatecheck,
        skip_drift=args.skip_drift,
        scan_opts={"exclude": args.exclude, "follow_symlinks": args.follow_symlinks},
    )
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":  # pragma: no cover
    main()
