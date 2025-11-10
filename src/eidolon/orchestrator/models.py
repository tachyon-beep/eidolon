from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Literal


Region = str
ResidencyFallback = Literal["block", "queue", "degrade"]


@dataclass(slots=True)
class ResidencyPolicy:
    required_regions: list[Region]
    preferred_regions: list[Region] = field(default_factory=list)
    fallback: ResidencyFallback = "block"

    def validate(self) -> None:
        if not self.required_regions:
            raise ValueError("ResidencyPolicy requires at least one required region")
        if self.fallback not in {"block", "queue", "degrade"}:
            raise ValueError(f"Unsupported fallback mode: {self.fallback}")


@dataclass(slots=True)
class Policy:
    egress: Literal["deny", "allow"] = "deny"
    network_profile: Literal["restricted", "default", "permissive"] = "restricted"
    residency: ResidencyPolicy | None = None


@dataclass(slots=True)
class MetadataContext:
    trace_id: str
    span_id: str
    task_id: str
    parent_span_id: str | None = None
    residency_fallback: ResidencyFallback | None = None


@dataclass(slots=True)
class Metadata:
    tenant: str
    repo: str
    run_id: str
    context: MetadataContext


@dataclass(slots=True)
class TaskSpec:
    id: str
    name: str
    image: str
    command: list[str]
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    resources: dict[str, Any] = field(default_factory=lambda: {"cpu": 1, "memory": "1Gi", "gpu": 0})
    timeouts: dict[str, str] = field(default_factory=lambda: {"execution": "30m", "queue": "10m"})
    retries: dict[str, Any] = field(default_factory=lambda: {"max": 3, "backoff": "5s", "jitter": True})
    concurrency: dict[str, Any] = field(default_factory=dict)
    cache: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    secrets: list[str] = field(default_factory=list)
    policy: Policy = field(default_factory=Policy)
    metadata: Metadata | None = None


@dataclass(slots=True)
class JobSpec:
    id: str
    name: str
    tasks: list[TaskSpec]
    dependencies: list[tuple[str, str]] = field(default_factory=list)
    max_parallelism: int = 100
    metadata: dict[str, Any] = field(default_factory=dict)

    def find_task(self, task_id: str) -> TaskSpec:
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise KeyError(f"Task {task_id} not found")
