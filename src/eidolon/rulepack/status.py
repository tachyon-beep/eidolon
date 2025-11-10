from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Tuple, List


def evaluate_status(payload: dict[str, Any]) -> Tuple[bool, List[str]]:
    if "rulepack_pipeline" not in payload:
        return True, ["No rulepack_pipeline section present"]

    pipeline = payload["rulepack_pipeline"]
    reasons: list[str] = []

    drift = pipeline.get("drift")
    if drift:
        summary = drift.get("summary", {})
        failed = summary.get("failed")
        if isinstance(failed, (int, float)) and failed > 0:
            reasons.append(f"Drift blocking rules failed ({int(failed)} finding(s))")

    gate = pipeline.get("gatecheck")
    if gate and gate.get("status") == "fail":
        reasons.append("GateCheck reported fail status")

    return (len(reasons) == 0), reasons


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check rulepack pipeline status JSON and fail on policy violations")
    parser.add_argument("path", type=Path, help="Path to orchestrator/rulepack pipeline JSON output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat missing rulepack_pipeline data as an error",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = json.loads(args.path.read_text(encoding="utf-8"))
    ok, reasons = evaluate_status(data)
    if "rulepack_pipeline" not in data and args.strict:
        print("rulepack_pipeline section missing; failing due to --strict")
        raise SystemExit(1)
    if not ok:
        print("Rulepack enforcement failed:\n" + "\n".join(f"- {reason}" for reason in reasons))
        raise SystemExit(1)
    print("Rulepack enforcement passed")


if __name__ == "__main__":  # pragma: no cover
    main()
