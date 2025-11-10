"""Send sample spans/logs/metrics to the local OTLP collector."""
from __future__ import annotations

import time

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.collector import metrics_exporter, trace_exporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

OTLP_ENDPOINT = "http://localhost:4317"

resource = Resource.create({"service.name": "orchestrator", "tenant": "demo", "run_id": "sample-run"})

trace_provider = TracerProvider(resource=resource)
trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter.OTLPSpanExporter(endpoint=OTLP_ENDPOINT)))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

metric_reader = PeriodicExportingMetricReader(metrics_exporter.OTLPMetricExporter(endpoint=OTLP_ENDPOINT))
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)
fallback_counter = meter.create_counter("residency_fallback_total")

with tracer.start_as_current_span("orchestrator.run", attributes={"run_id": "sample-run", "tenant": "demo"}) as span:
    span.add_event("scheduler.start")
    fallback_counter.add(1, attributes={"tenant": "demo", "mode": "block"})
    time.sleep(0.5)
    span.add_event("scheduler.end")

print("Sample telemetry sent to", OTLP_ENDPOINT)
