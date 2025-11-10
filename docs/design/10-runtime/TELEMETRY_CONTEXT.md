---
id: ORCH-01-TELEMETRY
version: 0.1
owner: Observability Lead
status: draft
summary: Context propagation contract for traces/metrics/logs mentioned in RAPID-TELEMETRY.
tags:
  - observability
  - telemetry
  - orchestrator
last_updated: 2025-02-15
---

# Telemetry Context Propagation

Implements RAPID-TELEMETRY by defining how Control Plane through adapters/workers propagate trace IDs, tenant labels, and
task metadata.

## 1. Canonical payload

```json
"metadata": {
  "tenant": "acme",
  "repo": "proj-x",
  "run_id": "r-123",
  "context": {
    "trace_id": "e5d17b5b2fa2",
    "span_id": "2f9a1c4b7d3e",
    "parent_span_id": "a18d1c",
    "task_id": "evaluate-file:7b3c",
    "residency_fallback": null
  }
}
```

* `trace_id` = `HMAC(tenant_id, run_id)` to avoid leaking tenant IDs while keeping determinism.
* `span_id` = unique per task submission; workers create child spans when invoking nested tools/LLMs.
* `residency_fallback` is optional but enables correlation between runtime placement and policy metrics.

## 2. Propagation surfaces

* **TaskSpec.env**: Control Plane injects `EID_TRACE_ID`, `EID_SPAN_ID`, `EID_TENANT`, `EID_RUN_ID`, `EID_TASK_ID`, `EID_REPO`.
* **Adapter requests**: For engines with native headers (Temporal, Flyte), adapters add the same key/value pairs to outbound RPC metadata.
* **Worker SDK**: `eidolon.telemetry.init()` reads env vars, creates a root span named after the task, attaches standard attributes, and configures log handlers to prefix `[trace= span=]`.

## 3. Collector pipeline

1. Workers emit OTLP spans/metrics/logs to the sidecar collector (OTel Collector).
2. Collector enriches signals with tenant/repo/run/task labels and pushes to Prometheus/Loki/Tempo using remote-write/exporters.
3. Tempo receives spans grouped by `trace_id`; Grafana dashboards join metrics via exemplars referencing the same ID.

## 4. Required metrics/logs

* `orchestrator_queue_latency_ms{tenant,repo,run_id,task_id}`
* `orchestrator_task_exec_ms{tenant,...}` with exemplars pointing at the `trace_id`.
* `orchestrator_cache_hit_total`, `residency_fallback_total`, `task_retries_total`, `task_llm_cost_usd`.
* Logs must include JSON structure: `{ "trace_id": ..., "span_id": ..., "tenant": ..., "message": ... }`.

## 5. Compliance checklist

- [ ] TaskSpec metadata/context present in ORCH-01 schema.
- [ ] Env var injection implemented in Local + Temporal adapters.
- [ ] Worker SDK uses provided IDs when initialising OpenTelemetry instrumentation.
- [ ] Collector deployment template available in `deploy/observability/` (future work).
- [ ] OBS-01 dashboards display per-tenant drilldowns using the propagated labels.
