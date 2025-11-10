from __future__ import annotations

import logging
import os
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .adapters.base import AdapterCallback, TaskResult
from .control_plane import ControlPlane
from .models import JobSpec, TaskSpec

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkerPool:
    region: str
    adapter_name: str  # e.g., "local", "temporal"


PlacementRecord = dict[str, str]


class ResidencyError(RuntimeError):
    pass


class Scheduler:
    def __init__(
        self,
        pools: Iterable[WorkerPool],
        adapter_registry: dict[str, Callable[..., Any]],
        control_plane: ControlPlane | None = None,
    ) -> None:
        self.pools = list(pools)
        self.adapters = adapter_registry
        self.placements: list[PlacementRecord] = []
        self.placements_by_task: dict[str, PlacementRecord] = {}
        self.results: dict[str, TaskResult] = {}
        self.control_plane = control_plane
        self._task_timings: dict[str, tuple[float, Any | None, dict[str, str]]] = {}
        self.tracer = None
        self.fallback_counter = None
        self.queue_latency_hist = None
        self._init_telemetry()

    def submit_job(self, job: JobSpec) -> list[dict[str, str]]:
        queue = deque(job.tasks)
        results: list[dict[str, str]] = []
        while queue:
            task = queue.popleft()
            record = self._schedule_task(task)
            results.append(record)
        return results

    def _schedule_task(self, task: TaskSpec) -> dict[str, str]:
        policy = task.policy.residency
        if not policy:
            raise ResidencyError(f"Task {task.id} missing residency policy")
        matching = [pool for pool in self.pools if pool.region in policy.required_regions]
        chosen_pool: WorkerPool | None = matching[0] if matching else None
        fallback_mode = "none"
        if not chosen_pool:
            match policy.fallback:
                case "block":
                    self._record_fallback("block", task.metadata)
                    raise ResidencyError(f"No capacity for task {task.id} in required regions")
                case "queue":
                    logger.info("Task %s queued due to residency capacity", task.id)
                    fallback_mode = "queue"
                    self._record_fallback("queue", task.metadata)
                    return {
                        "task_id": task.id,
                        "status": "queued",
                        "region": ",".join(policy.required_regions),
                        "fallback": fallback_mode,
                    }
                case "degrade":
                    preferred = [pool for pool in self.pools if pool.region in policy.preferred_regions]
                    if not preferred:
                        raise ResidencyError(f"Degrade fallback selected but no preferred pools for task {task.id}")
                    chosen_pool = preferred[0]
                    fallback_mode = "degrade"
                    self._record_fallback("degrade", task.metadata)
        assert chosen_pool is not None
        adapter_factory = self.adapters[chosen_pool.adapter_name]
        adapter = adapter_factory(callback=self._build_callback(task.id))
        if task.metadata:
            task.metadata.context.residency_fallback = None if fallback_mode == "none" else fallback_mode
        attrs = self._span_attributes(task, chosen_pool.region)
        timing_needed = self.queue_latency_hist is not None
        span = None
        if self.tracer:
            span = self.tracer.start_span("orchestrator.task", attributes=attrs)
            timing_needed = True
        if timing_needed:
            self._task_timings[task.id] = (time.perf_counter(), span, attrs)
        record = {
            "task_id": task.id,
            "region": chosen_pool.region,
            "adapter": chosen_pool.adapter_name,
            "fallback": fallback_mode,
            "status": "submitted",
        }
        self.placements.append(record)
        self.placements_by_task[task.id] = record
        adapter_result = adapter.run_task(task, chosen_pool.region)
        record["status"] = adapter_result.get("status", record["status"])
        return record

    def _build_callback(self, task_id: str) -> AdapterCallback:
        def _callback(completed_task_id: str, result: TaskResult) -> None:
            logger.info("Scheduler received completion for %s status=%s", completed_task_id, result.status)
            self.results[completed_task_id] = result
            placement = self.placements_by_task.get(completed_task_id)
            if placement:
                placement["status"] = result.status
                placement["attempt"] = str(result.attempt)
                placement["outputs"] = result.outputs
                if self.control_plane:
                    self.control_plane.record_placement(placement, result)
            timing = self._task_timings.pop(completed_task_id, None)
            if timing:
                start_time, span, attrs = timing
                if self.queue_latency_hist:
                    self.queue_latency_hist.record(time.perf_counter() - start_time, attributes=attrs)
                if span:
                    span.set_attribute("task.status", result.status)
                    span.end()

        return _callback

    def _init_telemetry(self) -> None:
        endpoint = os.getenv("ORCH_TELEMETRY_OTLP_ENDPOINT")
        if not endpoint:
            return
        resource = Resource.create({"service.name": "eidolon-orchestrator"})
        trace_provider = TracerProvider(resource=resource)
        trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(trace_provider)
        self.tracer = trace.get_tracer("eidolon.orchestrator")

        metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint))
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        meter = metrics.get_meter("eidolon.orchestrator")
        self.fallback_counter = meter.create_counter("residency_fallback_total")
        self.queue_latency_hist = meter.create_histogram("orchestrator_queue_latency_seconds")

    def _span_attributes(self, task: TaskSpec, region: str) -> dict[str, str]:
        attrs = {"task_id": task.id, "region": region}
        if task.metadata:
            attrs["tenant"] = task.metadata.tenant
            attrs["run_id"] = task.metadata.run_id
        return attrs

    def _record_fallback(self, mode: str, metadata: Any | None) -> None:
        if not self.fallback_counter or mode == "none":
            return
        attrs = {"mode": mode}
        if metadata:
            attrs["tenant"] = metadata.tenant
            attrs["run_id"] = metadata.run_id
        self.fallback_counter.add(1, attrs)
