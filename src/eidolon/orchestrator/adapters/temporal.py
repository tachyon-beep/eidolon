from __future__ import annotations

import logging
from typing import Any

import logging
import random
import threading
import time
from dataclasses import dataclass
from typing import Any

from .base import Adapter, AdapterCallback, TaskResult
from ..models import TaskSpec

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TemporalAdapterConfig:
    region_queue_map: dict[str, str]
    heartbeat_interval: float = 5.0
    simulate_latency: tuple[float, float] = (1.0, 3.0)


class TemporalAdapter(Adapter):
    name = "temporal"

    def __init__(self, *, callback: AdapterCallback | None = None, config: TemporalAdapterConfig | None = None) -> None:
        super().__init__()
        self.callback = callback
        self.config = config or TemporalAdapterConfig(region_queue_map={})

    def run_task(self, task: TaskSpec, region: str, *, placement_id: str | None = None) -> dict[str, Any]:
        queue = self.config.region_queue_map.get(region, f"default-{region}")
        env = self._prepare_env(task)
        logger.info(
            "TemporalAdapter dispatch task %s to queue=%s trace=%s span=%s",
            task.id,
            queue,
            env.get("EID_TRACE_ID"),
            env.get("EID_SPAN_ID"),
        )
        threading.Thread(
            target=self._simulate_execution,
            args=(task, queue, self.callback),
            daemon=True,
        ).start()
        return {"status": "submitted", "queue": queue}

    def _simulate_execution(self, task: TaskSpec, queue: str, callback: AdapterCallback | None) -> None:
        latency = random.uniform(*self.config.simulate_latency)
        heartbeat_interval = self.config.heartbeat_interval
        elapsed = 0.0
        while elapsed < latency:
            logger.info("TemporalAdapter heartbeat task=%s queue=%s elapsed=%.1fs", task.id, queue, elapsed)
            time.sleep(min(heartbeat_interval, latency - elapsed))
            elapsed += heartbeat_interval
        logger.info("TemporalAdapter completed task=%s queue=%s", task.id, queue)
        if callback:
            callback(task.id, TaskResult(status="succeeded", attempt=1, outputs={"queue": queue}))
