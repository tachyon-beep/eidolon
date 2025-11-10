from __future__ import annotations

import argparse
import fnmatch
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Iterable

import psycopg

from .compiler import CompiledRule, predicate_to_dict
from .errors import RulepackError
from .runtime import DEFAULT_DSN as RUNTIME_DSN, EvaluationReport, evaluate_rulepack_file
from .persistence import record_gatecheck_report


RowFilterFn = Callable[[CompiledRule, list[dict[str, Any]]], list[dict[str, Any]]]


@dataclass(slots=True)
class GateCheckResult:
    rule_id: str
    status: str
    severity: str
    enforcement: str
    matches: list[dict[str, Any]]
    match_count: int
    predicate: dict[str, Any]
    metric: float | None
    autofix: dict[str, str] | None


class GateCheckRunner:
    """Runs GateChecks against a CodeGraph snapshot using the shared Rulepack evaluator."""

    def __init__(
        self,
        *,
        dsn: str = RUNTIME_DSN,
        changed_paths: Iterable[str] | None = None,
        changed_boundaries: Iterable[str] | None = None,
        evaluator: Callable[[Path, int, RowFilterFn | None], EvaluationReport] | None = None,
        connector: Callable[[str], psycopg.Connection] | None = None,
    ) -> None:
        self.dsn = dsn
        self.changed_paths = tuple(changed_paths or ())
        self.changed_boundaries = tuple(changed_boundaries or ())
        self._evaluate_fn = evaluator
        self._connector = connector or psycopg.connect

    def run(
        self,
        *,
        rulepack_path: Path,
        run_id: int | None = None,
        repo_root: str | None = None,
        record: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_run_id = self._resolve_run_id(run_id=run_id, repo_root=repo_root)
        report = self._evaluate(rulepack_path, resolved_run_id)
        if record:
            record_gatecheck_report(self.dsn, report, context=context)
        gate_report = self._build_gate_report(report)
        gate_report["filters"] = {
            "changed_paths": list(self.changed_paths),
            "changed_boundaries": list(self.changed_boundaries),
        }
        return gate_report

    def _evaluate(self, rulepack_path: Path, run_id: int) -> EvaluationReport:
        row_filter: RowFilterFn | None = self._row_filter if (self.changed_paths or self.changed_boundaries) else None
        if self._evaluate_fn:
            return self._evaluate_fn(rulepack_path, run_id, row_filter)
        return evaluate_rulepack_file(rulepack_path, run_id=run_id, dsn=self.dsn, row_filter=row_filter)

    def _row_filter(self, rule: CompiledRule, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not (self.changed_paths or self.changed_boundaries):
            return rows
        filtered: list[dict[str, Any]] = []
        for row in rows:
            if self._matches_path(row) or self._matches_boundary(row):
                filtered.append(row)
        return filtered

    def _matches_path(self, row: dict[str, Any]) -> bool:
        if not self.changed_paths:
            return False
        path = row.get("path")
        if not isinstance(path, str):
            return False
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.changed_paths)

    def _matches_boundary(self, row: dict[str, Any]) -> bool:
        if not self.changed_boundaries:
            return False
        candidates = [row.get("boundary"), row.get("source_boundary"), row.get("target_name")]
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            if any(fnmatch.fnmatch(candidate, pattern) for pattern in self.changed_boundaries):
                return True
        return False

    def _resolve_run_id(self, *, run_id: int | None, repo_root: str | None) -> int:
        if run_id is not None:
            return run_id
        if not repo_root:
            raise RulepackError("Either --run-id or --repo-root must be provided.")
        with self._connector(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM scan_runs WHERE repo_root = %s ORDER BY created_at DESC LIMIT 1",
                    (repo_root,),
                )
                row = cur.fetchone()
        if not row:
            raise RulepackError(f"No scan_runs entries found for repo_root={repo_root!r}")
        return int(row[0])

    def _build_gate_report(self, report: EvaluationReport) -> dict[str, Any]:
        results: list[GateCheckResult] = []
        overall_status = "pass"
        for evaluation in report.results:
            status = self._rule_status(evaluation)
            overall_status = self._combine_status(overall_status, status)
            results.append(
                GateCheckResult(
                    rule_id=evaluation.rule.id,
                    status=status,
                    severity=evaluation.rule.severity,
                    enforcement=evaluation.rule.enforcement,
                    matches=evaluation.matches,
                    match_count=len(evaluation.matches),
                    predicate=predicate_to_dict(evaluation.rule.predicate),
                    metric=evaluation.metric,
                    autofix=evaluation.rule.autofix,
                )
            )
        return {
            "metadata": {
                "id": report.metadata.id,
                "name": report.metadata.name,
                "version": report.metadata.version,
            },
            "run_id": report.run_id,
            "status": overall_status,
            "rules": [asdict(result) for result in results],
        }

    @staticmethod
    def _rule_status(evaluation) -> str:
        if evaluation.passed:
            return "pass"
        enforcement = evaluation.rule.enforcement
        if enforcement == "block":
            return "fail"
        if enforcement == "warn":
            return "warn"
        return "pass"

    @staticmethod
    def _combine_status(current: str, new: str) -> str:
        if current == "fail" or new == "fail":
            return "fail"
        if current == "warn" or new == "warn":
            return "warn"
        return "pass"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run GateChecks for a plan delta using the shared Rulepack runtime.")
    parser.add_argument("--rulepack", required=True, type=Path, help="Path to the rulepack YAML file")
    parser.add_argument("--dsn", default=RUNTIME_DSN, help=f"Postgres DSN hosting CodeGraph tables (default: {RUNTIME_DSN})")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-id", type=int, help="Existing scan_runs.id to evaluate")
    group.add_argument("--repo-root", help="Resolve the latest scan run for this repo path")
    parser.add_argument("--changed-path", action="append", dest="changed_paths", help="Glob of changed file paths (repeatable)")
    parser.add_argument(
        "--changed-boundary",
        action="append",
        dest="changed_boundaries",
        help="Glob of changed subsystem boundaries (repeatable)",
    )
    parser.add_argument(
        "--human",
        action="store_true",
        help="Print a human-readable summary instead of JSON output",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON file to write the GateCheck report; stdout if omitted",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Persist results into gatecheck_results for later queries",
    )
    parser.add_argument(
        "--dwi-id",
        help="DesignWorkItem identifier for provenance",
    )
    parser.add_argument(
        "--plan-version",
        help="Plan version or SHA associated with this GateCheck",
    )
    parser.add_argument(
        "--context-json",
        help="Additional JSON context to store alongside the GateCheck results",
    )
    return parser


def handle_cli(args: argparse.Namespace) -> int:
    runner = GateCheckRunner(
        dsn=args.dsn,
        changed_paths=args.changed_paths,
        changed_boundaries=args.changed_boundaries,
    )
    context: dict[str, Any] = {}
    if args.dwi_id:
        context["dwi_id"] = args.dwi_id
    if args.plan_version:
        context["plan_version"] = args.plan_version
    if args.context_json:
        try:
            context.update(json.loads(args.context_json))
        except json.JSONDecodeError as exc:
            raise RulepackError(f"Failed to parse --context-json: {exc}") from exc
    payload = runner.run(
        rulepack_path=args.rulepack,
        run_id=args.run_id,
        repo_root=args.repo_root,
        record=args.record,
        context=context or None,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote GateCheck report to {args.output}")
    elif args.human:
        print(render_summary(payload))
    else:
        print(json.dumps(payload, indent=2))
    return 0


def render_summary(report: dict[str, Any]) -> str:
    summary = f"GateCheck {report['metadata']['id']} run {report['run_id']}: {report['status']}"
    lines = [summary]
    for rule in report["rules"]:
        if rule["status"] == "pass":
            continue
        lines.append(
            f"- [{rule['status']}] {rule['rule_id']} ({rule['match_count']} match{'es' if rule['match_count'] != 1 else ''})"
        )
    if len(lines) == 1:
        lines.append("- All rules passed.")
    return "\n".join(lines)


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
