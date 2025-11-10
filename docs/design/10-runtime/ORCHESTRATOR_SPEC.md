# Eidolon – Orchestrator Adapter Spec (ORCH‑01)
---
id: ORCH-01
version: 0.1
owner: Orchestrator Team
status: draft
summary: Engine-agnostic adapter contract for submitting, running, tracking, cancelling, and testing Eidolon tasks across orchestration backends.
tags:
  - runtime
  - orchestrator
  - spec
last_updated: 2025-11-10
---

# Eidolon – Orchestrator Adapter Spec (ORCH‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Orchestrator Team

## 1. Purpose

Define a stable, engine‑agnostic adapter contract for submitting, running, tracking, and cancelling Eidolon tasks and jobs across multiple orchestration backends (Local, Airflow, Dagster, Temporal, Argo, Flyte). Provide a conformance test suite and a local reference runner. **v1 targets Local + Temporal; additional adapters remain behind feature flags until they pass the conformance suite and emit required telemetry.**

## 2. Concepts

* **Task**: the atomic unit of work (e.g., evaluate a file, synthesise ADRs).
* **Job**: a collection of Tasks with dependencies (DAG or steps).
* **Run**: an execution instance of a Job.

## 3. TaskSpec (canonical JSON)

```json
{
  "id": "evaluate-file:7b3c",
  "name": "evaluate-file",
  "image": "eidolon/worker:1.4.0",
  "command": ["python", "-m", "eidolon.tasks.evaluate_file"],
  "args": ["--path", "src/pkg/mod.py"],
  "env": {"LOG_LEVEL": "INFO"},
  "inputs": {"path": "src/pkg/mod.py", "plan_sha": "abc123"},
  "resources": {"cpu": 1, "memory": "1Gi", "gpu": 0},
  "timeouts": {"execution": "30m", "queue": "10m"},
  "retries": {"max": 3, "backoff": "5s", "jitter": true},
  "concurrency": {"class": "evaluator:llm", "max_in_flight": 50},
  "cache": {"key": "sha256:...:tool@1.4:policy@2025-10-01", "ttl": "30d"},
  "artifacts": {"outputs": [{"name": "evaluation", "path": "/out/evaluation.json"}]},
  "secrets": ["OPENAI_API_KEY"],
  "policy": {
    "egress": "deny",
    "network_profile": "restricted",
    "residency": {
      "required_regions": ["ap-southeast-2"],
      "preferred_regions": ["ap-southeast-2"],
      "fallback": "queue"
    }
  },
  "metadata": {
    "tenant": "acme",
    "repo": "proj-x",
    "run_id": "r-123",
    "context": {
      "trace_id": "e5d17b5b2fa2",
      "span_id": "2f9a1c4b7d3e",
      "task_id": "evaluate-file:7b3c"
    }
  }
}
```

### 3.1 Field semantics

* **image/command/args**: required for containerised engines; Local runner uses Python entrypoints.
* **resources**: minimum request; adapters may clamp to backend limits.
* **timeouts**: execution hard‑kill; queue timeout fails with `QueueTimeout`.
* **retries**: exponential backoff; adapters must implement idempotent re‑runs.
* **concurrency.class**: global token bucket key (e.g., limit LLM QPS); enforced by adapter or shared sidecar.
* **cache.key**: if present, adapter must attempt a cache lookup; cache store is provided by Control Plane.
* **artifacts.outputs**: adapter uploads paths to Object Store and returns signed URIs.
* **secrets**: opaque names resolved by Secret Manager; not logged.
* **policy**: sandbox hints (network profile, egress, residency). Residency hints are authoritative.
* **metadata**: free‑form labels plus the canonical telemetry context envelope (§15).

### 3.2 Residency semantics

* `policy.residency.required_regions`: hard affinity. The scheduler filters worker pools by region labels and rejects scheduling outside the set.
* `policy.residency.preferred_regions`: ties broken across compliant pools; also used when `fallback=degrade`.
* `policy.residency.fallback`: `block` (fail fast with `PolicyViolation`), `queue` (stay pending), `degrade` (spill into `preferred_regions` while emitting an audit event + metrics).
* Placement decisions MUST be logged with `{task_id, run_id, region, residency_source, fallback_mode}` and persisted with the Job metadata for audits and SEC-01 evidence.

## 4. JobSpec

```json
{
  "id": "job-run:9f21",
  "name": "evaluate-repo",
  "tasks": [TaskSpec...],
  "dependencies": [["evaluate-A", "aggregate-1"], ["evaluate-B", "aggregate-1"]],
  "max_parallelism": 200,
  "metadata": {"run_id": "r-123"}
}
```

Dependencies are ordered pairs (A → B) meaning B waits for A.

## 5. Adapter API (gRPC/HTTP)

```
POST   /adapter/jobs            -> { job_id }
POST   /adapter/jobs/{id}/start -> { run_id }
POST   /adapter/runs/{id}/cancel
GET    /adapter/runs/{id}/status -> { state, tasks:[...] }
GET    /adapter/runs/{id}/logs?task=... -> stream text
GET    /adapter/runs/{id}/artifacts -> [{task_id, name, uri}]
WS     /adapter/events -> run.started|task.started|task.succeeded|task.failed|run.completed
```

### 5.1 States (canonical)

* **Run**: `queued | running | cancelling | completed | failed | cancelled | partial`
* **Task**: `pending | starting | running | succeeded | failed | skipped | cancelled`

### 5.2 Progress and heartbeats

Adapters MUST emit heartbeats every ≤ 30 s per running task. Missing 3 heartbeats marks task `lost`; retry according to policy.

## 6. Error taxonomy

* `Cancelled` – user/operator cancellation
* `QueueTimeout` – exceeded queue timeout
* `DeadlineExceeded` – exceeded execution timeout
* `ResourceExhausted` – OOM/OOD/GPU pre‑emption
* `RetriableNetwork` – transient network failure
* `DependencyFailed` – upstream task failed
* `PolicyViolation` – egress/permissions breach
* `UserCodeError` – task process exit code != 0 (non‑transient)
* `SystemError` – adapter/engine internal

Each error carries: `category`, `message`, `details`, `attempt`, `timestamp`.

## 7. Cancellation protocol

* **Soft cancel**: send SIGTERM / grace period (default 30 s), publish `task.cancelling` event.
* **Hard kill**: after grace, SIGKILL/force delete pod. Adapters must guarantee no further writes.
* **Idempotency**: cancel may be called multiple times; final state is `cancelled` or `completed`.

## 8. Logs & artefacts

* Logs are streamed with per‑line correlation IDs and limited to 1 MB/min per task (configurable).
* Artefacts uploaded to Object Store via sidecar/uploader with retries; URIs returned via `/artifacts`.

## 9. Secrets

* Secrets fetched JIT at start; mounted as env or files; redacted in logs; audit who/when accessed.

## 10. Concurrency limits

* **Global** per `concurrency.class` (e.g., `evaluator:llm=50`).
* **Per‑tenant** caps from Control Plane budgets.
* Adapters MUST NOT exceed provided limits; they may queue locally.

## 11. Conformance test suite

* **Structure**: 60 scenarios across happy‑path and 50+ failure modes.
* **Areas**: retries/backoff, timeouts, cancellation, partial failures, lost heartbeats, artefact upload retry, log truncation, concurrency enforcement, cache hits/misses.
* **Outcome**: JSON report with pass/fail and timing; badge recorded in Metadata Store.

## 12. Local reference runner

* Executes JobSpec directly in a worker pool (no external engine).
* Implements full contract: retries, heartbeats, log streaming, artefact uploads, concurrency throttles.
* Used for dev and CI; must pass the same conformance suite.

## 13. Adapter mappings (profiles)

> **Adapter rollout plan**: LocalAdapter and TemporalAdapter are **GA in v1**. The Airflow, Dagster, Argo, and Flyte adapters share the contract below but remain feature-flagged until they pass the full conformance suite and emit OBS-01 telemetry.

### 13.1 Airflow profile

* Map JobSpec to a DAG with `KubernetesPodOperator` or `TaskFlow` tasks.
* Heartbeats via task logs + sensor; cancellation via `dag_run` terminate.
* Limitations: queue timeouts approximated with SLA/mixed.

### 13.2 Dagster profile

* Map tasks to ops; dependencies to graph/job.
* Use run worker pods; emit heartbeats via logs; cancellation via run termination.

### 13.3 Temporal profile

* JobSpec → Workflow; TaskSpec → Activity with timeouts and retry policy.
* Heartbeats via `record_heartbeat`; cancellation via workflow/activity cancel.

### 13.4 Argo Workflows profile

* Map JobSpec to Argo DAG/Steps templates; tasks reference reusable container specs.
* Pass artefacts via template outputs/parameters; heartbeat via a sidecar container emitting heartbeats to Control Plane.
* Cancellation handled through workflow terminate; adapters reconcile final state and ensure no further writes after termination.
* Limitations: queue timeouts approximated with `activeDeadlineSeconds` + sensors.

### 13.5 Flyte profile

* JobSpec compiles into strongly typed Flyte tasks/launch plans with interface validation and versioned registration.
* Artifacts exchange via Flyte’s typed inputs/outputs; runtime enforces schema and raises typed errors on mismatch.
* Cancellation via Flyte abort; adapters surface typed I/O validation errors as `UserCodeError`.
* Registry sync required before submission to ensure launch plans exist with correct versions/resources.

## 14. Cache integration

* Pre‑task: adapter requests `CacheCheck(cache.key)` from Control Plane. If hit, adapter short‑circuits to `succeeded` with referenced artefacts.
* Post‑task: on success, adapter calls `CacheStore(key, outputs, metadata)`.

## 15. Telemetry

* Control Plane computes `{trace_id, span_id, tenant, repo, run_id, task_id}` and injects them into `metadata.context`.
* Adapters MUST propagate these values via env vars (`EID_TRACE_ID`, `EID_SPAN_ID`, `EID_TENANT`, `EID_RUN_ID`, `EID_TASK_ID`) to downstream workers.
* Emit OpenTelemetry spans for job/run/task with attributes: orchestrator, queue_wait_ms, exec_ms, retries, cache_hit, resources_used, residency_region, residency_fallback_mode.
* Logs must be prefixed with `[trace=<trace_id> span=<span_id>]` (or structured equivalently) and exported to the collector sidecar.
* Metrics (queue latency, task_exec_ms, cache_hits, residency_fallback_total) carry the tenant/repo/run/task labels derived from the context payload; use hashed IDs when mandated by SEC-01.

## 16. Security posture

* Default network egress: deny; allowlist per task.
* Rootless containers where possible; read‑only FS; tmpfs scratch; seccomp/apparmor profiles for K8s adapters.

## 17. Limits & policies

* Max task size (env + inputs) 64 KiB; args length 4 KiB.
* Max logs per task 50 MB (configurable).
* Max parallel tasks per run bounded by `max_parallelism`.

## 18. Acceptance criteria (from Master List ORCH‑01)

* Spec published; Local and Airflow adapters pass full conformance suite; Temporal passes core profile.
* Cancellation protocol works across adapters with deterministic final states.
* Concurrency classes enforced without leaks under load.
* Cache integration yields ≥ 60% hit rate on unchanged runs in benchmarks.

## 19. Open questions

* Do we require per‑adapter feature flags for unsupported fields?
* Should we expose a streaming artefact channel for very large outputs?
* Standard way to express GPU types (vendor‑agnostic)?
