from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eidolon.orchestrator.adapters.base import Adapter, TaskResult
from eidolon.orchestrator.adapters.local import LocalAdapter
from eidolon.orchestrator.models import JobSpec, Metadata, MetadataContext, Policy, ResidencyPolicy, TaskSpec
from eidolon.orchestrator.persistence import PlacementRecorder
from eidolon.orchestrator.scheduler import Scheduler, WorkerPool


def make_task(task_id: str, residency: ResidencyPolicy) -> TaskSpec:
    metadata = Metadata(tenant="acme", repo="proj", run_id="run-1", context=MetadataContext(trace_id="t", span_id="s", task_id=task_id))
    return TaskSpec(
        id=task_id,
        name=task_id,
        image="eidolon/worker:latest",
        command=["python", "-m", "task"],
        policy=Policy(residency=residency),
        metadata=metadata,
    )


def build_scheduler():
    pools = [WorkerPool(region="ap-southeast-2", adapter_name="local"), WorkerPool(region="us-east-1", adapter_name="local")]
    adapters = {"local": LocalAdapter}
    return Scheduler(pools=pools, adapter_registry=adapters)


def test_scheduler_places_task_in_required_region(tmp_path: Path) -> None:
    scheduler = build_scheduler()
    residency = ResidencyPolicy(required_regions=["ap-southeast-2"], preferred_regions=["us-east-1"], fallback="block")
    job = JobSpec(id="job", name="job", tasks=[make_task("t1", residency=residency)])
    result = scheduler.submit_job(job)
    assert result[0]["region"] == "ap-southeast-2"


def test_scheduler_degrade_fallback_selects_preferred_region() -> None:
    scheduler = build_scheduler()
    residency = ResidencyPolicy(required_regions=["eu-central-1"], preferred_regions=["us-east-1"], fallback="degrade")
    job = JobSpec(id="job", name="job", tasks=[make_task("t1", residency=residency)])
    result = scheduler.submit_job(job)
    assert result[0]["region"] == "us-east-1"
    assert result[0]["fallback"] == "degrade"


def test_scheduler_queue_fallback_returns_queued_status() -> None:
    scheduler = build_scheduler()
    residency = ResidencyPolicy(required_regions=["eu-central-1"], preferred_regions=[], fallback="queue")
    job = JobSpec(id="job", name="job", tasks=[make_task("t1", residency=residency)])
    result = scheduler.submit_job(job)
    assert result[0]["status"] == "queued"
    assert result[0]["fallback"] == "queue"


class SyncAdapter(Adapter):
    name = "sync"

    def __init__(self, *, callback=None) -> None:
        super().__init__()
        self.callback = callback

    def run_task(self, task: TaskSpec, region: str, *, placement_id: str | None = None) -> dict[str, Any]:
        if self.callback:
            self.callback(task.id, TaskResult(status="succeeded", attempt=1, outputs={"region": region}))
        return {"status": "submitted"}


def test_scheduler_records_results(tmp_path: Path) -> None:
    recorder = PlacementRecorder(tmp_path / "placements.jsonl")
    class FakeControlPlane:
        def record_placement(self, entry, result=None):
            recorder.record(entry, result or TaskResult(status="unknown", attempt=0, outputs={}))

    control_plane = FakeControlPlane()
    scheduler = Scheduler(
        pools=[WorkerPool(region="ap-southeast-2", adapter_name="sync")],
        adapter_registry={"sync": lambda callback=None: SyncAdapter(callback=callback)},
        control_plane=control_plane,
    )
    residency = ResidencyPolicy(required_regions=["ap-southeast-2"])
    job = JobSpec(id="job", name="job", tasks=[make_task("t1", residency=residency)])
    scheduler.submit_job(job)
    assert scheduler.results["t1"].status == "succeeded"
    contents = (tmp_path / "placements.jsonl").read_text(encoding="utf-8")
    assert "\"final_status\": \"succeeded\"" in contents or "\"final_status\":\"succeeded\"" in contents
