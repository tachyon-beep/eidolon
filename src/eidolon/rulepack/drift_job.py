from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

import psycopg

from .errors import RulepackError
from .runtime import DEFAULT_DSN as RUNTIME_DSN, evaluate_rulepack_file
from .persistence import record_drift_report


class DriftJob:
    """Evaluates a rulepack against a CodeGraph scan run."""

    def __init__(
        self,
        *,
        dsn: str = RUNTIME_DSN,
        evaluator: Callable[[Path, int, str], Any] | None = None,
        connector: Callable[[str], psycopg.Connection] | None = None,
    ) -> None:
        self.dsn = dsn
        self._evaluate = evaluator or (lambda path, run_id, dsn: evaluate_rulepack_file(path, run_id=run_id, dsn=dsn))
        self._connect = connector or psycopg.connect

    def run(
        self,
        *,
        rulepack_path: Path,
        run_id: int | None = None,
        repo_root: str | None = None,
        output: Path | None = None,
        record: bool = False,
    ) -> dict[str, Any]:
        resolved_run_id = self._resolve_run_id(run_id=run_id, repo_root=repo_root)
        report = self._evaluate(rulepack_path, resolved_run_id, self.dsn)
        if record:
            record_drift_report(self.dsn, report)
        payload = report.to_dict()
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def _resolve_run_id(self, *, run_id: int | None, repo_root: str | None) -> int:
        if run_id is not None:
            return run_id
        if not repo_root:
            raise RulepackError("Either --run-id or --repo-root must be provided.")
        with self._connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM scan_runs WHERE repo_root = %s ORDER BY created_at DESC LIMIT 1",
                    (repo_root,),
                )
                row = cur.fetchone()
        if not row:
            raise RulepackError(f"No scan_runs entries found for repo_root={repo_root!r}")
        return int(row[0])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate drift using the shared Rulepack DSL against CodeGraph runs.")
    parser.add_argument("--rulepack", required=True, type=Path, help="Path to the rulepack YAML file")
    parser.add_argument("--dsn", default=RUNTIME_DSN, help=f"Postgres DSN hosting CodeGraph tables (default: {RUNTIME_DSN})")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-id", type=int, help="Existing scan_runs.id to evaluate")
    group.add_argument("--repo-root", help="Resolve the latest scan run for this repo path")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON file to write the evaluation report (default: print to stdout)",
    )
    parser.add_argument(
        "--human",
        action="store_true",
        help="Print a condensed human-readable summary instead of JSON",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Persist results into drift_results for later queries",
    )
    return parser


def handle_cli(args: argparse.Namespace) -> int:
    job = DriftJob(dsn=args.dsn)
    payload = job.run(
        rulepack_path=args.rulepack,
        run_id=args.run_id,
        repo_root=args.repo_root,
        output=args.output,
        record=args.record,
    )
    if args.human:
        print(render_summary(payload))
    elif not args.output:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Wrote drift report to {args.output}")
    return 0


def render_summary(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    header = f"Rulepack {payload['metadata']['id']} on run {payload['run_id']}: {summary['failed']} failed / {summary['total']} total"
    details = []
    for result in payload["results"]:
        if result["passed"]:
            continue
        details.append(
            f"- [{result['severity']}] {result['rule_id']} ({result['match_count']} match{'es' if result['match_count'] != 1 else ''})"
        )
    if not details:
        details.append("- All rules passed.")
    return "\n".join([header, *details])


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        exit_code = handle_cli(args)
    except RulepackError as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from exc
    raise SystemExit(exit_code)


if __name__ == "__main__":  # pragma: no cover
    main()
