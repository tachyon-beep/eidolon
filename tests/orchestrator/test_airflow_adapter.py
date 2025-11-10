from __future__ import annotations

import time

from eidolon.orchestrator.adapters.airflow import AirflowAdapter, AirflowAdapterConfig
from eidolon.orchestrator.models import Metadata, MetadataContext, Policy, ResidencyPolicy, TaskSpec


def build_task(task_id: str) -> TaskSpec:
    metadata = Metadata(tenant="acme", repo="repo", run_id="run", context=MetadataContext(trace_id="t", span_id="s", task_id=task_id))
    return TaskSpec(
        id=task_id,
        name=task_id,
        image="",
        command=["python", "-c", "print('hello')"],
        policy=Policy(residency=ResidencyPolicy(required_regions=["ap-southeast-2"])),
        metadata=metadata,
    )


def test_airflow_adapter_invokes_callback() -> None:
    results: list[str] = []

    def callback(task_id: str, result):
        results.append(result.status)

    adapter = AirflowAdapter(callback=callback, config=AirflowAdapterConfig(simulated_latency=0.01))
    adapter.run_task(build_task("task"), region="ap-southeast-2")
    time.sleep(0.05)
    assert results == ["succeeded"]
