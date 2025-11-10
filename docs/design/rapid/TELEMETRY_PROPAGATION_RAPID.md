---
id: RAPID-TELEMETRY
version: 0.1
owner: Observability Lead
status: draft
summary: Rapid design for propagating ORCH-01 trace/span IDs and metrics into the OBS-01 stack with per-tenant visibility.
tags:
  - rapid-design
  - observability
  - telemetry
last_updated: 2025-11-10
---

# Telemetry Propagation Rapid Design

## Problem statement

OBS-01 requires per-tenant metrics, logs, and traces keyed by `trace_id = HMAC(tenant_id, run_id)`, but ORCH-01 only briefly mentions OpenTelemetry spans. Without a concrete plan, services may ship under-instrumented.

## Scope & goals

* Define canonical context propagation (headers/env vars) for `trace_id`, `span_id`, and tenant labels across Control Plane, workers, and adapters.
* Specify metrics/log schemas consumed by Prometheus/Loki/Tempo stacks.
* Ensure cache/cost/guardrail events attach the same IDs for cross-correlation.

## Architecture

1. **Trace context generator** in Control Plane: for each run/task, compute `trace_id`, `span_id`, `tenant`, `repo`, `run_id`, `task_id`.
2. **Propagation**: inject context into TaskSpec env vars and adapter API payloads (`EID_TRACE_ID`, `EID_SPAN_ID`, `EID_TENANT`).
3. **Adapters**: emit OpenTelemetry spans with these IDs, forward logs (with `[trace:span]` prefix) to a collector sidecar.
4. **Collector**: scrapes metrics/logs/traces, enriches with tenant labels, forwards to Prometheus/Loki/Tempo.

## Interfaces

* TaskSpec additions: `metadata.context = { trace_id, span_id, tenant, run_id, task_id }`.
* Worker SDK: helper to initialise OTel span + logger using provided env vars.
* Metrics labels: `tenant`, `repo`, `run_id`, `task_id`, `trace_id` (hashed for privacy if needed).

## Prototype plan

1. Update Local adapter + worker harness to read context env vars and emit spans/logs/metrics via OpenTelemetry SDK.
2. Configure a minimal collector stack (OTel Collector + Prometheus + Tempo) locally.
3. Run sample job → verify trace fan-out (run span → task spans) and metrics alignment (queue latency, task_exec_ms) **including cache hits and LLM evaluator spans** to ensure continuity through asynchronous hops.
4. Document onboarding checklist for new services/adapters.

## Risks & mitigations

* **Label explosion**: keep cardinality manageable (hash run_id if necessary); use exemplars for per-task metrics.
* **Non-OTel adapters**: provide a shim library or sidecar to translate logs to spans.
* **Data privacy**: ensure `trace_id` is derived (HMAC) and not raw tenant IDs.
* **Async gaps**: explicitly test trace continuity through cache layers and LLM evaluators to avoid broken spans.

## Exit criteria

* ORCH-01 updated with context propagation requirements (pointer to this doc).
* Local + Temporal adapters emit traces/metrics/logs with consistent IDs in staging environment.
* OBS-01 dashboards ingest the new labels and show per-tenant slices.

> **Implementation note (2025-02)**: TaskSpec metadata/context is now part of ORCH-01 (§3 + §15) and the end-to-end envelope
> is captured in `docs/design/10-runtime/TELEMETRY_CONTEXT.md`. Adapters still need to plumb env vars + OTLP exporters, but
> the propagation contract is frozen for implementation.
