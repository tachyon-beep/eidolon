from __future__ import annotations

from pathlib import Path

from eidolon.rulepack.status import evaluate_status


def test_evaluate_status_passes_when_no_failures() -> None:
    payload = {
        "rulepack_pipeline": {
            "drift": {"summary": {"failed": 0}},
            "gatecheck": {"status": "pass"},
        }
    }
    ok, reasons = evaluate_status(payload)
    assert ok is True
    assert reasons == []


def test_evaluate_status_detects_failures() -> None:
    payload = {
        "rulepack_pipeline": {
            "drift": {"summary": {"failed": 2}},
            "gatecheck": {"status": "fail"},
        }
    }
    ok, reasons = evaluate_status(payload)
    assert ok is False
    assert len(reasons) == 2
