from __future__ import annotations

from pathlib import Path
from typing import Callable

from eidolon.rulepack.compiler import CompiledRule
from eidolon.rulepack.gatecheck_job import GateCheckRunner, render_summary
from eidolon.rulepack.models import RulePredicate, RulepackMetadata
from eidolon.rulepack.runtime import EvaluationReport, RuleEvaluation


def build_report(
    *,
    run_id: int,
    rows: list[dict[str, str]],
    enforcement: str = "block",
    severity: str = "error",
) -> EvaluationReport:
    rule = CompiledRule(
        id="rule",
        description="",
        severity=severity,
        enforcement=enforcement,
        selector_source="file_metrics",
        predicate=RulePredicate(kind="forbid"),
        scopes=[],
        category=None,
        autofix=None,
        sql="SELECT 1",
        parameters={},
    )
    evaluation = RuleEvaluation(
        rule=rule,
        passed=len(rows) == 0,
        matches=rows,
        metric=float(len(rows)),
    )
    metadata = RulepackMetadata(
        id="RP-TEST",
        name="Test",
        version="1.0.0",
        summary="",
        owners=["refiner"],
    )
    return EvaluationReport(metadata=metadata, run_id=run_id, results=[evaluation])


def fake_evaluator_factory(rows: list[dict[str, str]], enforcement: str = "block") -> Callable:
    def _evaluate(path: Path, run_id: int, row_filter):
        filtered_rows = rows
        if row_filter:
            filtered_rows = row_filter(
                CompiledRule(
                    id="rule",
                    description="",
                    severity="error",
                    enforcement=enforcement,
                    selector_source="file_metrics",
                    predicate=RulePredicate(kind="forbid"),
                    scopes=[],
                    category=None,
                    autofix=None,
                    sql="SELECT 1",
                    parameters={},
                ),
                rows,
            )
        return build_report(run_id=run_id, rows=filtered_rows, enforcement=enforcement)

    return _evaluate


def test_gatecheck_runner_filters_matches_by_path(tmp_path: Path) -> None:
    evaluator = fake_evaluator_factory(
        rows=[{"path": "src/foo.py"}, {"path": "src/bar.py"}],
        enforcement="block",
    )
    runner = GateCheckRunner(
        changed_paths=["src/foo.py"],
        evaluator=evaluator,
    )
    report = runner.run(rulepack_path=tmp_path / "pack.yaml", run_id=1)
    assert report["status"] == "fail"
    assert report["rules"][0]["match_count"] == 1

    runner_none = GateCheckRunner(
        changed_paths=["does_not_match"],
        evaluator=evaluator,
    )
    report_none = runner_none.run(rulepack_path=tmp_path / "pack.yaml", run_id=1)
    assert report_none["status"] == "pass"
    assert report_none["rules"][0]["match_count"] == 0


def test_gatecheck_runner_warn_status(tmp_path: Path) -> None:
    evaluator = fake_evaluator_factory(rows=[{"path": "src/foo.py"}], enforcement="warn")
    runner = GateCheckRunner(changed_paths=["src/*"], evaluator=evaluator)
    report = runner.run(rulepack_path=tmp_path / "pack.yaml", run_id=1)
    assert report["status"] == "warn"
    assert report["rules"][0]["status"] == "warn"


def test_render_summary_formats_output() -> None:
    report = {
        "metadata": {"id": "RP-TEST"},
        "run_id": 7,
        "status": "fail",
        "rules": [
            {"rule_id": "ok", "status": "pass", "match_count": 0},
            {"rule_id": "bad", "status": "fail", "match_count": 2},
        ],
    }
    summary = render_summary(report)
    assert "bad" in summary
    assert "fail" in summary
