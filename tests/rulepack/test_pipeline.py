from __future__ import annotations

from pathlib import Path
from typing import Any

from eidolon.rulepack.pipeline import RulepackPipeline


def test_pipeline_runs_with_stubs(tmp_path: Path) -> None:
    scan_calls: list[tuple] = []
    ingest_calls: list[tuple] = []

    def stub_scan(repo: Path, records: Path, summary: Path, opts: dict[str, Any]) -> dict[str, Any]:
        scan_calls.append((repo, opts))
        records.write_text("{}", encoding="utf-8")
        summary.write_text("{}", encoding="utf-8")
        return {"repo_root": str(repo)}

    def stub_ingest(summary: dict[str, Any], records: Path, dsn: str) -> int:
        ingest_calls.append((summary, dsn))
        return 42

    def stub_drift(rulepack: Path, run_id: int, dsn: str) -> dict[str, Any]:
        return {"run_id": run_id, "rulepack": str(rulepack)}

    def stub_gate(rulepack: Path, run_id: int, dsn: str, changed_paths, changed_boundaries) -> dict[str, Any]:
        return {"run_id": run_id, "paths": changed_paths}

    pipeline = RulepackPipeline(
        scan_fn=stub_scan,
        ingest_fn=stub_ingest,
        drift_fn=stub_drift,
        gate_fn=stub_gate,
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    rulepack = tmp_path / "rulepack.yaml"
    rulepack.write_text("metadata: {id: RP, name: RP, version: 1, summary: s, owners: [o]}\nrules: []", encoding="utf-8")
    result = pipeline.run(
        repo=repo,
        rulepack=rulepack,
        dsn="postgresql://example",
        changed_paths=["src/*.py"],
    )
    assert result["run_id"] == 42
    assert result["drift"]["rulepack"] == str(rulepack)
    assert result["gatecheck"]["paths"] == ["src/*.py"]
    assert scan_calls
    assert ingest_calls
