# Eidolon – Orchestrator Adapter Spec (ORCH‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Orchestrator Team

## 1. Purpose

Define a stable, engine‑agnostic adapter contract for submitting, running, tracking, and cancelling Eidolon tasks and jobs across multiple orchestration backends (Local, Airflow, Dagster, Temporal, Argo, Flyte). Provide a conformance test suite and a local reference runner.

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
  "policy": {"egress": "deny", "network_profile": "restricted"},
  "metadata": {"tenant": "acme", "repo": "proj-x", "run_id": "r-123"}
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
* **policy**: sandbox hints (network profile, egress). Adapters implement best‑effort.

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

* JobSpec → WorkflowTemplate; TaskSpec → template + step/DAG.
* Heartbeats via sidecar; cancellation via workflow terminate; logs via Argo logs API.

### 13.5 Flyte profile

* JobSpec → Flyte workflow; tasks as container tasks.
* Use resource requests/limits; cancellation via abort; artefacts via Flyte offloads.

## 14. Cache integration

* Pre‑task: adapter requests `CacheCheck(cache.key)` from Control Plane. If hit, adapter short‑circuits to `succeeded` with referenced artefacts.
* Post‑task: on success, adapter calls `CacheStore(key, outputs, metadata)`.

## 15. Telemetry

* Emit OpenTelemetry spans for job/run/task with attributes: orchestrator, queue_wait_ms, exec_ms, retries, cache_hit, resources_used.

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
