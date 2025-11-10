from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from eidolon.rulepack.drift_job import DriftJob, render_summary
from eidolon.rulepack.errors import RulepackError


class DummyReport:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload


def fake_payload(run_id: int) -> dict[str, Any]:
    return {
        "metadata": {"id": "RP-TEST", "name": "Test", "version": "1.0.0", "summary": "", "owners": [], "tags": []},
        "run_id": run_id,
        "summary": {"total": 1, "passed": 1, "failed": 0},
        "results": [{"rule_id": "rule-a", "severity": "error", "enforcement": "block", "passed": True, "match_count": 0}],
    }


def test_drift_job_uses_explicit_run_id(tmp_path: Path) -> None:
    pack = tmp_path / "rulepack.yaml"
    pack.write_text("metadata: {}\n", encoding="utf-8")

    job = DriftJob(
        evaluator=lambda path, run_id, dsn: DummyReport(fake_payload(run_id)),
        connector=lambda dsn: None,  # not used
    )
    payload = job.run(rulepack_path=pack, run_id=42)
    assert payload["run_id"] == 42


class FakeCursor:
    def __init__(self, rows: list[tuple[int]]) -> None:
        self._rows = rows
        self._iter = iter(rows)

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    def execute(self, query: str, params: tuple[str]) -> None:
        self._iter = iter(self._rows)

    def fetchone(self) -> tuple[int] | None:
        return next(self._iter, None)


class FakeConnection:
    def __init__(self, rows: list[tuple[int]]) -> None:
        self._rows = rows

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    def cursor(self) -> FakeCursor:
        return FakeCursor(self._rows)


def test_drift_job_resolves_repo_root(tmp_path: Path) -> None:
    pack = tmp_path / "rulepack.yaml"
    pack.write_text("metadata: {}\n", encoding="utf-8")
    connector = lambda dsn: FakeConnection([(7,)])  # noqa: E731
    job = DriftJob(
        evaluator=lambda path, run_id, dsn: DummyReport(fake_payload(run_id)),
        connector=connector,
    )
    payload = job.run(rulepack_path=pack, repo_root="/repo")
    assert payload["run_id"] == 7


def test_drift_job_errors_when_repo_missing(tmp_path: Path) -> None:
    pack = tmp_path / "rulepack.yaml"
    pack.write_text("metadata: {}\n", encoding="utf-8")
    connector = lambda dsn: FakeConnection([])  # noqa: E731
    job = DriftJob(
        evaluator=lambda path, run_id, dsn: DummyReport(fake_payload(run_id)),
        connector=connector,
    )
    with pytest.raises(RulepackError):
        job.run(rulepack_path=pack, repo_root="/missing")


def test_render_summary_formats_failures() -> None:
    payload = {
        "metadata": {"id": "RP-TEST"},
        "run_id": 1,
        "summary": {"total": 2, "passed": 1, "failed": 1},
        "results": [
            {"rule_id": "ok", "passed": True, "severity": "info", "match_count": 0},
            {"rule_id": "fail", "passed": False, "severity": "error", "match_count": 2},
        ],
    }
    summary = render_summary(payload)
    assert "fail" in summary
    assert "2 match" in summary
