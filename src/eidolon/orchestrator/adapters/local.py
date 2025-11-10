from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Callable

from .base import Adapter, AdapterCallback, TaskResult
from ..models import TaskSpec

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LocalAdapterConfig:
    log_dir: Path = Path(".orchestrator/logs")
    artefact_dir: Path = Path(".orchestrator/artifacts")


class LocalAdapter(Adapter):
    name = "local"

    def __init__(self, *, callback: AdapterCallback | None = None, config: LocalAdapterConfig | None = None) -> None:
        super().__init__()
        self.callback = callback
        self.config = config or LocalAdapterConfig()
        self.config.log_dir.mkdir(parents=True, exist_ok=True)
        self.config.artefact_dir.mkdir(parents=True, exist_ok=True)

    def run_task(self, task: TaskSpec, region: str, *, placement_id: str | None = None) -> dict[str, Any]:
        thread = threading.Thread(
            target=self._execute_task,
            args=(task, region, placement_id, self.callback),
            daemon=True,
        )
        thread.start()
        return {"status": "submitted"}

    def _execute_task(self, task: TaskSpec, region: str, placement_id: str | None, callback: AdapterCallback | None) -> None:
        env = self._prepare_env(task)
        command = task.command + task.args
        attempt = 0
        max_attempts = int(task.retries.get("max", 1)) if task.retries else 1
        queue_timeout_s = _parse_duration(task.timeouts.get("queue", "0s")) if task.timeouts else 0
        execution_timeout_s = _parse_duration(task.timeouts.get("execution", "0s")) if task.timeouts else 0
        queue_start = time.monotonic()
        while attempt < max_attempts:
            attempt += 1
            if queue_timeout_s and (time.monotonic() - queue_start) > queue_timeout_s:
                self._complete(task, TaskResult(status="queue_timeout", attempt=attempt, outputs={}))
                return
            try:
                logger.info("LocalAdapter starting task %s attempt %s trace=%s", task.id, attempt, env.get("EID_TRACE_ID"))
                log_file = self.config.log_dir / f"{task.id}-{attempt}.log"
                with log_file.open("w", encoding="utf-8") as lf:
                    proc = subprocess.Popen(
                        command,
                        env=env,
                        stdout=lf,
                        stderr=subprocess.STDOUT,
                        cwd=env.get("EID_REPO", "."),
                    )
                    try:
                        proc.wait(timeout=execution_timeout_s or None)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        self._complete(task, TaskResult(status="deadline_exceeded", attempt=attempt, outputs={}), callback)
                        return
                if proc.returncode == 0:
                    artefact_path = self.config.artefact_dir / f"{task.id}-stdout.txt"
                    artefact_path.write_text(log_file.read_text(encoding="utf-8") if log_file.exists() else "", encoding="utf-8")
                    self._complete(
                        task,
                        TaskResult(
                            status="succeeded",
                            attempt=attempt,
                            outputs={"logs": str(log_file), "artefacts": [str(artefact_path)]},
                        ),
                        callback,
                    )
                    return
                logger.warning("Task %s exited with %s", task.id, proc.returncode)
            except OSError as exc:
                logger.error("LocalAdapter failed to start task %s: %s", task.id, exc)
                self._complete(task, TaskResult(status="system_error", attempt=attempt, outputs={"error": str(exc)}), callback)
                return
        self._complete(task, TaskResult(status="failed", attempt=attempt, outputs={}), callback)

    def _complete(self, task: TaskSpec, result: TaskResult, callback: AdapterCallback | None) -> None:
        if callback:
            callback(task.id, result)
        logger.info("Task %s completed with status %s attempt %s", task.id, result.status, result.attempt)


def _parse_duration(value: str) -> int:
    if not value:
        return 0
    units = {"s": 1, "m": 60, "h": 3600}
    suffix = value[-1]
    if suffix not in units:
        raise ValueError(f"Unsupported duration string: {value}")
    return int(value[:-1]) * units[suffix]
