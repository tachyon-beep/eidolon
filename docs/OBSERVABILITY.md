# Eidolon – Observability & SLOs (OBS‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Platform Observability Lead

## 1. Purpose

Define the observability framework and service level objectives (SLOs) for Eidolon. Establish metrics, traces, logs, dashboards, alerting, and role‑specific telemetry views. Integrates with ORCH‑01 (runs, tasks), DET‑01 (determinism metrics), CASH‑01 (cost metrics), DR‑01 (drift counts), and SEC‑01 (security events).

## 2. Objectives

* Provide real‑time visibility into system health, performance, and reliability.
* Enable diagnosis of performance regressions and cost anomalies.
* Support SLO‑driven alerting and post‑incident analysis.
* Expose data to Operator, Coder, and Architect views without security leakage.

## 3. Observability stack

| Layer      | Tool                                             | Purpose                                       |
| ---------- | ------------------------------------------------ | --------------------------------------------- |
| Metrics    | **Prometheus**                                   | Quantitative metrics collection               |
| Logs       | **Loki**                                         | Structured, indexed logs with correlation IDs |
| Traces     | **OpenTelemetry + Tempo**                        | Distributed tracing across services           |
| Dashboards | **Grafana**                                      | Visualisation and alert rules                 |
| Events     | **WebSocket / Kafka**                            | Streaming operational events                  |
| APM        | **Optional: OpenTelemetry Collector + Tempo UI** | Deep traces and spans analysis                |

### 3.1 Correlation model

Each run, task, and artefact carries a **trace_id** and **span_id** propagated end‑to‑end:

```
trace_id = HMAC(tenant_id, run_id)
span_id = HMAC(trace_id, task_id)
```

These IDs appear in:

* Logs (prefixed by `[trace:span]`)
* Prometheus labels (`trace_id`, `tenant`, `repo`)
* WebSocket events for UI correlation.

## 4. Metrics taxonomy

### 4.1 System metrics (global)

| Category    | Metric                                                                                   | Unit             | Description                    |
| ----------- | ---------------------------------------------------------------------------------------- | ---------------- | ------------------------------ |
| API         | `api_latency_ms`, `api_5xx_rate`, `api_req_rate`                                         | ms, %, rps       | API Gateway latency and errors |
| Queue       | `queue_depth`, `queue_wait_ms`, `queue_throughput`                                       | count, ms        | Run queue health               |
| Worker      | `task_exec_ms`, `task_retries`, `task_failures`, `task_cpu_pct`, `task_mem_bytes`        | various          | Worker efficiency              |
| Cache       | `cache_hit_ratio`, `cache_lookup_ms`, `cache_store_ms`, `cache_evictions`                | %, ms, ms, count | CACHE‑01 integration           |
| Cost        | `tokens_in/out`, `cpu_hours`, `budget_util_pct`                                          | tokens, h, %     | Derived from CASH‑01           |
| Determinism | `equivalence_score`, `variance_exceeded_rate`, `flaky_rate`                              | %, %             | From DET‑01                    |
| Drift       | `drift_detected_total`, `drift_blocking_total`, `drift_tta_seconds`, `drift_ttr_seconds` | count, s         | From DR‑01                     |
| Security    | `egress_blocked_total`, `redactions_applied_total`, `secret_access_total`                | count            | From SEC‑01                    |

### 4.2 Business metrics

| Metric                      | Owner         | Description                                              |
| --------------------------- | ------------- | -------------------------------------------------------- |
| `time_to_first_finding`     | Operator      | Lag between run start and first evaluation result        |
| `approval_cycle_time`       | Coder         | Time between finding creation and approval/closure       |
| `design_refinement_cycle`   | Architect     | Avg. time from DWI start to merge                        |
| `requirement_to_plan_cycle` | Product Owner | Avg. latency from requirement creation to plan inclusion |

## 5. Log schema (JSON)

```
{
  "timestamp": "2025-11-10T03:24:00Z",
  "level": "INFO|WARN|ERROR",
  "trace_id": "...",
  "span_id": "...",
  "tenant": "acme",
  "service": "worker|api|control-plane|orchestrator",
  "component": "Evaluator|RepoScanner|Synthesiser|Publisher",
  "task_id": "...",
  "message": "Human-readable summary",
  "context": {"exception": "", "artefact_id": "", "metrics": {...}}
}
```

Retention: 30 days (hot), 90 days (archive). Correlated to provenance logs for audit.

## 6. Trace schema

* Span attributes: `service`, `task_name`, `tenant`, `repo`, `cpu_ms`, `mem_bytes`, `queue_wait_ms`, `cache_hit:boolean`, `retries`, `errors`, `llm_tokens_in/out`.
* Links: `parent_span_id`, `child_span_ids`.
* Traces visualised in Tempo or Grafana; colour‑coded by task state.

## 7. Dashboards (Grafana)

### 7.1 Operator dashboard

* Queue depth, throughput, error rate, latency distribution.
* Cache hit/miss ratio and token usage.
* Cost forecast vs actual per run.
* Concurrency utilisation by class.
* Alert panel: SLO violations and budget breaches.

### 7.2 Coder dashboard

* Evaluation success/failure rate.
* Median approval cycle time.
* Flaky evaluator trends (DET‑01).
* Drift backlog size (DR‑01).
* Cache savings.

### 7.3 Architect dashboard

* DWI throughput and merge time.
* Drift heatmap by subsystem.
* HLD compliance score trend.
* Requirement conversion funnel.
* Security posture summary (redactions, egress blocks).

### 7.4 Product dashboard

* Requirement backlog counts.
* Feature latency (requirement→plan→implementation).
* Run cost breakdown per subsystem.

## 8. Alerting & SLOs

### 8.1 Global service SLOs

| SLO                     | Target                | Window     |
| ----------------------- | --------------------- | ---------- |
| API availability        | 99.9%                 | 30 days    |
| Queue latency p95       | < 2 min               | 7 days     |
| Task success rate       | ≥ 99.5%               | 7 days     |
| Drift detection latency | < 10 min from run end | 1 day      |
| Cache lookup p95        | < 10 ms               | 1 day      |
| Replay equivalence (D1) | ≥ 95%                 | 30 days    |
| Audit log completeness  | 100%                  | continuous |

### 8.2 Alert thresholds (examples)

* `api_5xx_rate > 1% for 5m`
* `task_failures > 0.5% of total for 10m`
* `cache_hit_ratio < 50% over 24h`
* `budget_util_pct > 80%` soft alert; `> 100%` hard block.
* `variance_exceeded_rate > 2%` from DET‑01.

### 8.3 Escalations

* PagerDuty integration for Sev1 (service outage).
* Slack/email for Sev2 (SLO breach but degraded only).
* In‑app banner for soft policy alerts (cost, drift, determinism).

## 9. Telemetry API

```http
GET /telemetry/metrics?scope=run|tenant&window=24h
GET /telemetry/traces/{trace_id}
GET /telemetry/logs?service=worker&level=ERROR&since=1h
GET /telemetry/slo/status
POST /telemetry/alert/test
```

## 10. Data model extensions

* `MetricRecord`: { name, value, unit, labels, timestamp }
* `AlertRecord`: { id, metric, threshold, window, severity, action }
* `SLORecord`: { name, target, achieved, window, last_breach }

## 11. Security & tenancy

* Metrics tagged with tenant_id; per‑tenant Prometheus namespaces or label filters.
* Logs and traces scoped by tenant; access via RBAC (SEC‑01 alignment).
* Aggregated metrics (for global ops) anonymised.

## 12. Governance

* Monthly SLO review; breaches logged as incidents with root‑cause notes.
* Observability code changes require Architecture review.
* Dashboard definitions stored as IaC (Grafana JSON dashboards in repo).

## 13. Acceptance criteria

* Full traceability from run → task → artefact → drift → audit log in < 5 clicks in UI.
* 100% of services emit OTel spans and Prometheus metrics with tenant labels.
* Dashboards online with live data and alerting validated in staging.
* All SLOs defined in configuration; monthly SLO report generated automatically.

## 14. Open questions

* Should we integrate anomaly detection (ML) for token/cost anomalies or stick to rule‑based thresholds v1?
* Retention durations per tenant tier (Gov vs Commercial)?
* Policy for log redaction in multi‑tenant observability clusters?
