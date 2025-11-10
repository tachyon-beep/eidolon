from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from .adapters.local import LocalAdapter
from .adapters.temporal import TemporalAdapter
from .adapters.airflow import AirflowAdapter
from .control_plane import ControlPlane, ControlPlaneConfig
from .scheduler import Scheduler, WorkerPool
# control plane handles placement persistence
from eidolon.rulepack.pipeline import RulepackPipeline


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_scheduler(pools_data: list[dict[str, str]], *, control_plane: ControlPlane | None = None) -> Scheduler:
    pools = [WorkerPool(region=item["region"], adapter_name=item["adapter"]) for item in pools_data]
    adapters = {
        "local": LocalAdapter,
        "temporal": TemporalAdapter,
        "airflow": AirflowAdapter,
    }
    return Scheduler(pools=pools, adapter_registry=adapters, control_plane=control_plane)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prototype residency-aware orchestrator runner")
    parser.add_argument("--job", required=True, type=Path, help="Path to JobSpec YAML/JSON")
    parser.add_argument("--tenant-policy", required=True, type=Path, help="Tenant residency policy (YAML/JSON)")
    parser.add_argument("--pools", required=True, type=Path, help="Worker pool configuration (YAML)")
    parser.add_argument("--plan-overrides", type=Path, help="Optional plan residency overrides (YAML)")
    parser.add_argument("--run-id", required=True, help="Run identifier for telemetry context")
    parser.add_argument("--repo", required=True, help="Repository identifier")
    parser.add_argument("--repo-path", type=Path, help="Filesystem path to repo (required when running rulepack pipeline)")
    parser.add_argument("--output", type=Path, help="Optional JSON file to dump placements")
    parser.add_argument("--rulepack", type=Path, help="Optional rulepack to evaluate post-run")
    parser.add_argument(
        "--pipeline-dsn",
        default="postgresql://eidolon:password@localhost:6543/eidolon",
        help="Postgres DSN used by the rulepack pipeline",
    )
    parser.add_argument("--pipeline-skip-drift", action="store_true", help="Skip drift evaluation during pipeline run")
    parser.add_argument("--pipeline-skip-gatecheck", action="store_true", help="Skip GateCheck evaluation during pipeline run")
    parser.add_argument("--pipeline-changed-path", action="append", dest="pipeline_changed_paths", help="GateCheck changed-path glob")
    parser.add_argument("--pipeline-changed-boundary", action="append", dest="pipeline_changed_boundaries", help="GateCheck changed-boundary glob")
    args = parser.parse_args()

    job_payload = load_yaml(args.job)
    plan_overrides = load_yaml(args.plan_overrides) if args.plan_overrides else None
    control_plane = ControlPlane(
        ControlPlaneConfig(
            tenant_policy_path=args.tenant_policy,
            job_dir=Path(".orchestrator") / "jobs",
            placements_path=Path(".orchestrator") / "placements.jsonl",
        )
    )
    job = control_plane.assemble_job(job_payload, plan_overrides, repo=args.repo, run_id=args.run_id)
    control_plane.persist_job(job)
    scheduler = build_scheduler(load_yaml(args.pools)["pools"], control_plane=control_plane)
    placements = scheduler.submit_job(job)
    output_payload = {
        "placements": placements,
        "telemetry": [
            {
                "trace_id": task.metadata.context.trace_id,
                "span_id": task.metadata.context.span_id,
                "task_id": task.metadata.context.task_id,
            }
            for task in job.tasks
            if task.metadata
        ],
    }
    if args.rulepack:
        if not args.repo_path:
            parser.error("--repo-path is required when --rulepack is provided")
        pipeline = RulepackPipeline()
        pipeline_result = pipeline.run(
            repo=args.repo_path,
            rulepack=args.rulepack,
            dsn=args.pipeline_dsn,
            changed_paths=args.pipeline_changed_paths,
            changed_boundaries=args.pipeline_changed_boundaries,
            skip_gatecheck=args.pipeline_skip_gatecheck,
            skip_drift=args.pipeline_skip_drift,
        )
        output_payload["rulepack_pipeline"] = pipeline_result
    payload = json.dumps(output_payload, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":  # pragma: no cover
    main()
