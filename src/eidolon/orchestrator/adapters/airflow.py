from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .base import Adapter, AdapterCallback, TaskResult
from ..models import TaskSpec

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AirflowAdapterConfig:
    base_url: str | None = None
    dag_id: str = "eidolon-task"
    simulated_latency: float = 2.0


class AirflowAdapter(Adapter):
    name = "airflow"

    def __init__(self, *, callback: AdapterCallback | None = None, config: AirflowAdapterConfig | None = None) -> None:
        super().__init__()
        self.callback = callback
        self.config = config or AirflowAdapterConfig()

    def run_task(self, task: TaskSpec, region: str, *, placement_id: str | None = None) -> dict[str, Any]:
        threading.Thread(
            target=self._trigger_and_wait,
            args=(task, region, placement_id, self.callback),
            daemon=True,
        ).start()
        return {"status": "submitted", "dag_id": self.config.dag_id}

    def _trigger_and_wait(
        self,
        task: TaskSpec,
        region: str,
        placement_id: str | None,
        callback: AdapterCallback | None,
    ) -> None:
        self._trigger_dag(task)
        time.sleep(self.config.simulated_latency)
        if callback:
            callback(
                task.id,
                TaskResult(status="succeeded", attempt=1, outputs={"adapter": "airflow", "dag_id": self.config.dag_id}),
            )

    def _trigger_dag(self, task: TaskSpec) -> None:
        if not self.config.base_url:
            return
        url = f"{self.config.base_url}/api/v1/dags/{self.config.dag_id}/dagRuns"
        payload = json.dumps({"conf": task.inputs, "dag_run_id": task.id}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=5)
            logger.info("Triggered Airflow DAG %s for task %s", self.config.dag_id, task.id)
        except urllib.error.URLError as exc:
            logger.warning("Airflow trigger failed for %s: %s", task.id, exc)
