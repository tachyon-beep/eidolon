from __future__ import annotations

import json
import yaml
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .models import JobSpec, Metadata, MetadataContext, Policy, ResidencyPolicy, TaskSpec
from .policy_engine import TenantPolicy, merge_residency_policy
from .telemetry import build_context


@dataclass(slots=True)
class ControlPlaneConfig:
    tenant_policy_path: Path
    job_dir: Path
    placements_path: Path


class ControlPlane:
    def __init__(self, config: ControlPlaneConfig) -> None:
        self.config = config
        self.config.job_dir.mkdir(parents=True, exist_ok=True)
        self.config.placements_path.parent.mkdir(parents=True, exist_ok=True)
        self.tenant_policy = self._load_tenant_policy()

    def _load_tenant_policy(self) -> TenantPolicy:
        payload = yaml.safe_load(self.config.tenant_policy_path.read_text(encoding="utf-8"))
        return TenantPolicy(
            tenant=payload["tenant"],
            required_regions=payload.get("required_regions", []),
            preferred_regions=payload.get("preferred_regions", []),
            fallback=payload.get("fallback", "block"),
        )

    def assemble_task(self, task_data: dict[str, Any], overrides: dict[str, Any] | None, repo: str, run_id: str) -> TaskSpec:
        residency = merge_residency_policy(self.tenant_policy, overrides)
        context = build_context(tenant=self.tenant_policy.tenant, repo=repo, run_id=run_id, task_id=task_data["id"])
        metadata = Metadata(tenant=self.tenant_policy.tenant, repo=repo, run_id=run_id, context=context)
        policy = Policy(
            egress=task_data.get("policy", {}).get("egress", "deny"),
            network_profile=task_data.get("policy", {}).get("network_profile", "restricted"),
            residency=residency,
        )
        return TaskSpec(
            id=task_data["id"],
            name=task_data.get("name", task_data["id"]),
            image=task_data.get("image", "eidolon/worker:latest"),
            command=task_data.get("command", []),
            args=task_data.get("args", []),
            env=task_data.get("env", {}),
            inputs=task_data.get("inputs", {}),
            resources=task_data.get("resources", {}),
            timeouts=task_data.get("timeouts", {}),
            retries=task_data.get("retries", {}),
            concurrency=task_data.get("concurrency", {}),
            cache=task_data.get("cache", {}),
            artifacts=task_data.get("artifacts", {}),
            secrets=task_data.get("secrets", []),
            policy=policy,
            metadata=metadata,
        )

    def assemble_job(self, payload: dict[str, Any], overrides: dict[str, Any] | None, repo: str, run_id: str) -> JobSpec:
        if "tasks" not in payload:
            raise ValueError("Job payload missing 'tasks' array")
        tasks = [self.assemble_task(task_data, overrides, repo, run_id) for task_data in payload["tasks"]]
        return JobSpec(
            id=payload["id"],
            name=payload.get("name", payload["id"]),
            tasks=tasks,
            dependencies=[tuple(dep) for dep in payload.get("dependencies", [])],
            max_parallelism=payload.get("max_parallelism", 100),
            metadata=payload.get("metadata", {}),
        )

    def persist_job(self, job: JobSpec) -> Path:
        path = self.config.job_dir / f"{job.id}.json"
        payload = {
            "id": job.id,
            "name": job.name,
            "tasks": [asdict(task) for task in job.tasks],
            "dependencies": job.dependencies,
            "max_parallelism": job.max_parallelism,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def record_placement(self, entry: dict[str, Any], result: TaskResult | None = None) -> None:
        logger = logging.getLogger(__name__)
        payload = dict(entry)
        payload.setdefault("run_id", entry.get("run_id", payload.get("run_id", "")))
        if result:
            payload["final_status"] = result.status
            payload["attempt"] = result.attempt
            payload["outputs"] = result.outputs
        logger.info(
            "PLACEMENT task=%s run=%s region=%s fallback=%s status=%s",
            payload.get("task_id"),
            payload.get("run_id"),
            payload.get("region"),
            payload.get("fallback"),
            payload.get("final_status", payload.get("status")),
        )
        with self.config.placements_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def load_job(self, job_id: str) -> JobSpec:
        path = self.config.job_dir / f"{job_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        tasks = [TaskSpec(**task) for task in payload["tasks"]]
        return JobSpec(
            id=payload["id"],
            name=payload.get("name", payload["id"]),
            tasks=tasks,
            dependencies=[tuple(dep) for dep in payload.get("dependencies", [])],
            max_parallelism=payload.get("max_parallelism", 100),
            metadata=payload.get("metadata", {}),
        )

    def list_jobs(self) -> list[str]:
        return sorted(p.stem for p in self.config.job_dir.glob("*.json"))
