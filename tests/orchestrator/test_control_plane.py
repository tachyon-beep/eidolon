from __future__ import annotations

import json
from pathlib import Path

from eidolon.orchestrator.control_plane import ControlPlane, ControlPlaneConfig


def write_tenant_policy(path: Path) -> None:
    path.write_text(json.dumps({"tenant": "demo", "required_regions": ["ap-southeast-2"], "preferred_regions": []}), encoding="utf-8")


def test_assemble_persist_job(tmp_path: Path) -> None:
    tenant_policy_path = tmp_path / "tenant.json"
    write_tenant_policy(tenant_policy_path)
    config = ControlPlaneConfig(
        tenant_policy_path=tenant_policy_path,
        job_dir=tmp_path / "jobs",
        placements_path=tmp_path / "placements.jsonl",
    )
    cp = ControlPlane(config)
    job_payload = {
        "id": "job-1",
        "tasks": [{"id": "task-1", "command": ["python", "-c", "print('hello')"]}],
    }
    job = cp.assemble_job(job_payload, overrides=None, repo="repo", run_id="run")
    job_path = cp.persist_job(job)
    assert job_path.exists()
