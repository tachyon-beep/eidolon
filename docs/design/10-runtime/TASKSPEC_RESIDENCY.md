---
id: ORCH-01-RESIDENCY
version: 0.1
owner: Orchestrator & Security Leads
status: draft
summary: Residency propagation pipeline for TaskSpec → scheduler → adapters with auditability hooks.
tags:
  - orchestrator
  - security
  - residency
last_updated: 2025-02-15
---

# TaskSpec Residency Enforcement

This note operationalises RAPID-TASKSPEC-RESIDENCY. It explains how tenant/plan residency policies flow into TaskSpec,
what the scheduler/adapters must do with those hints, and how auditors retrieve evidence.

## 1. Source of truth

1. **Tenant catalog (SEC-01)** – declares `home_region`, optionally `secondary_regions`, and severity if placement drifts.
2. **Plan metadata** – DWIs can request stricter residency (e.g., keep ADR generation in `eu-central-1`).
3. **PolicyEngine** – merges tenant + plan inputs and produces the `policy.residency` block that is injected into every TaskSpec.

```json
"policy": {
  "egress": "deny",
  "network_profile": "restricted",
  "residency": {
    "required_regions": ["ap-southeast-2"],
    "preferred_regions": ["ap-southeast-2", "ap-south-1"],
    "fallback": "queue"
  }
}
```

## 2. Scheduler behaviour

* Filter worker pools/nodes by a `region=<iso-code>` label. Pools lacking the label are considered non-compliant.
* If no pool satisfies `required_regions`:
  * `fallback=block` → fail the task immediately with `PolicyViolation`.
  * `fallback=queue` → keep the task pending until capacity reappears; emit metric `residency_pending_total{region}`.
  * `fallback=degrade` → spill into `preferred_regions` **and** set `metadata.context.residency_fallback="degrade"` so telemetry can alert.
* Record placement decisions in the Metadata DB: `{task_id, run_id, region, residency_source, fallback_mode, decided_at}`.
* Emit OpenTelemetry span attribute `residency.region` for every task run.

## 3. Adapter responsibilities

* Adapters receive the already-filtered TaskSpec and MUST honor it:
  * K8s adapters apply a `nodeSelector`/`topologySpreadConstraint` over the region label.
  * Temporal adapter selects the namespace/worker queue that maps 1:1 with a region.
  * Local adapter enforces via feature flag (only regions explicitly enabled for dev).
* If an adapter loses affinity (e.g., region label removed), it must surface `PolicyViolation` back to Control Plane.

## 4. Audit & observability

* `drift_results` / `gatecheck_results` already receive residency fallback metrics via rulepacks; this doc focuses on runtime evidence.
* Control Plane stores placement documents in `metadata.residency_log`. Operators query via `GET /orchestrator/runs/{id}/placements` (API stub).
* Prometheus metrics:
  * `residency_enforced_total{tenant,region}` – increments whenever a task is scheduled in a required region.
  * `residency_fallback_total{tenant,mode}` – increments on block/queue/degrade.
* Loki log format: `PLACEMENT task=<id> run=<id> region=<iso> fallback=<mode> trace=<trace_id>`.

## 5. Next steps

1. Extend Local + Temporal adapters to translate `policy.residency` into concrete placement knobs.
2. Populate scheduler placement logs + API.
3. Add residency coverage to ORCH-01 conformance suite (mock pool with/without region labels).
