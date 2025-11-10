from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol

from ..models import TaskSpec
from ..telemetry import inject_env


class Adapter(ABC):
    name: str

    def __init__(self, *, telemetry_enabled: bool = True) -> None:
        self.telemetry_enabled = telemetry_enabled

    @abstractmethod
    def run_task(self, task: TaskSpec, region: str, *, placement_id: str | None = None) -> dict[str, Any]:  # pragma: no cover - interface
        ...

    def _prepare_env(self, task: TaskSpec) -> dict[str, str]:
        metadata = {
            "tenant": task.metadata.tenant if task.metadata else "",
            "repo": task.metadata.repo if task.metadata else "",
            "run_id": task.metadata.run_id if task.metadata else "",
        }
        context = task.metadata.context if task.metadata else None
        return inject_env(context, metadata) if (context and self.telemetry_enabled) else task.env


@dataclass(slots=True)
class TaskResult:
    status: str
    attempt: int
    outputs: dict[str, Any]


class AdapterCallback(Protocol):
    def __call__(self, task_id: str, result: TaskResult) -> None:  # pragma: no cover - protocol
        ...
