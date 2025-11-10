from __future__ import annotations

import json
import sys
from pathlib import Path

from eidolon.orchestrator import cli


def write_yaml(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_produces_placements(tmp_path: Path, monkeypatch) -> None:
    job = {
        "id": "job",
        "tasks": [
            {
                "id": "task-1",
                "name": "task-1",
                "command": ["python", "-m", "task"],
            }
        ],
    }
    tenant_policy = {"tenant": "acme", "required_regions": ["ap-southeast-2"], "preferred_regions": ["ap-southeast-2"], "fallback": "block"}
    pools = {"pools": [{"region": "ap-southeast-2", "adapter": "local"}]}
    job_path = tmp_path / "job.json"
    tenant_path = tmp_path / "tenant.json"
    pools_path = tmp_path / "pools.json"
    output_path = tmp_path / "output.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")
    tenant_path.write_text(json.dumps(tenant_policy), encoding="utf-8")
    pools_path.write_text(json.dumps(pools), encoding="utf-8")
    argv = [
        "prog",
        "--job",
        str(job_path),
        "--tenant-policy",
        str(tenant_path),
        "--pools",
        str(pools_path),
        "--repo",
        "proj",
        "--run-id",
        "run-1",
        "--output",
        str(output_path),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    cli.main()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["placements"][0]["region"] == "ap-southeast-2"


def test_cli_runs_rulepack_pipeline(tmp_path: Path, monkeypatch) -> None:
    job = {
        "id": "job",
        "tasks": [
            {
                "id": "task-1",
                "name": "task-1",
                "command": ["python", "-m", "task"],
            }
        ],
    }
    tenant_policy = {"tenant": "acme", "required_regions": ["ap-southeast-2"], "preferred_regions": ["ap-southeast-2"], "fallback": "block"}
    pools = {"pools": [{"region": "ap-southeast-2", "adapter": "local"}]}
    job_path = tmp_path / "job.json"
    tenant_path = tmp_path / "tenant.json"
    pools_path = tmp_path / "pools.json"
    output_path = tmp_path / "output.json"
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    rulepack_path = tmp_path / "rulepack.yaml"
    job_path.write_text(json.dumps(job), encoding="utf-8")
    tenant_path.write_text(json.dumps(tenant_policy), encoding="utf-8")
    pools_path.write_text(json.dumps(pools), encoding="utf-8")
    rulepack_path.write_text("metadata: {id: RP, name: RP, version: 1, summary: s, owners: [o]}\nrules: []", encoding="utf-8")

    class FakePipeline:
        def __init__(self) -> None:
            self.called = False

        def run(self, **kwargs):
            self.called = True
            self.kwargs = kwargs
            return {"run_id": 123}

    fake_pipeline = FakePipeline()
    monkeypatch.setattr(cli, "RulepackPipeline", lambda: fake_pipeline)
    argv = [
        "prog",
        "--job",
        str(job_path),
        "--tenant-policy",
        str(tenant_path),
        "--pools",
        str(pools_path),
        "--repo",
        "proj",
        "--repo-path",
        str(repo_path),
        "--rulepack",
        str(rulepack_path),
        "--run-id",
        "run-1",
        "--output",
        str(output_path),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    cli.main()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["rulepack_pipeline"]["run_id"] == 123
    assert fake_pipeline.called
