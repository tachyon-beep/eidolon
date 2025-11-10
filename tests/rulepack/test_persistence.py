from __future__ import annotations

from typing import Any

import pytest

from eidolon.rulepack.compiler import CompiledRule
from eidolon.rulepack.models import RulePredicate, RulepackMetadata
from eidolon.rulepack.persistence import record_drift_report, record_gatecheck_report
from eidolon.rulepack.runtime import EvaluationReport, RuleEvaluation


class FakeCursor:
    def __init__(self, ops: list[tuple[str, Any, Any]]) -> None:
        self.ops = ops

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        self.ops.append(("execute", query, params))


class FakeConnection:
    def __init__(self, ops: list[tuple[str, Any, Any]]) -> None:
        self.ops = ops

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    def cursor(self) -> FakeCursor:
        self.ops.append(("cursor", None, None))
        return FakeCursor(self.ops)

    def commit(self) -> None:
        self.ops.append(("commit", None, None))


def build_report(*, enforcement: str = "block") -> EvaluationReport:
    rule = CompiledRule(
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
    )
    evaluation = RuleEvaluation(rule=rule, passed=False, matches=[{"path": "src/foo.py"}], metric=1.0)
    metadata = RulepackMetadata(id="RP-ID", name="Test", version="1.0.0", summary="", owners=["refiner"])
    return EvaluationReport(metadata=metadata, run_id=1, results=[evaluation])


def test_record_drift_report_inserts(monkeypatch: pytest.MonkeyPatch) -> None:
    ops: list[tuple[str, Any, Any]] = []

    def fake_connect(dsn: str) -> FakeConnection:
        ops.append(("connect", dsn, None))
        return FakeConnection(ops)

    monkeypatch.setattr("eidolon.rulepack.persistence.psycopg.connect", fake_connect)
    record_drift_report("postgresql://example", build_report())
    inserts = [op for op in ops if op[0] == "execute" and "INSERT INTO drift_results" in op[1]]
    assert inserts, "expected drift_results insert"


def test_record_gatecheck_report_inserts(monkeypatch: pytest.MonkeyPatch) -> None:
    ops: list[tuple[str, Any, Any]] = []

    def fake_connect(dsn: str) -> FakeConnection:
        ops.append(("connect", dsn, None))
        return FakeConnection(ops)

    monkeypatch.setattr("eidolon.rulepack.persistence.psycopg.connect", fake_connect)
    record_gatecheck_report("postgresql://example", build_report(enforcement="warn"), context={"dwi_id": "DWI-1"})
    inserts = [op for op in ops if op[0] == "execute" and "INSERT INTO gatecheck_results" in op[1]]
    assert inserts, "expected gatecheck_results insert"
