---
id: RAPID-TASKSPEC-RESIDENCY
version: 0.1
owner: Orchestrator & Security Leads
status: draft
summary: Rapid design for propagating tenant residency policies into ORCH-01 TaskSpecs and scheduler placement.
tags:
  - rapid-design
  - orchestrator
  - security
last_updated: 2025-11-10
---

# TaskSpec Residency & Locality Rapid Design

## Problem statement

SEC-01 enforces region pinning per tenant, but ORCH-01 TaskSpec lacks fields to express residency/locality. Without explicit hints, orchestrators cannot guarantee data stays in approved regions.

## Scope & goals

* Extend TaskSpec with residency metadata consumed by the Control Plane and adapters.
* Define scheduler behaviour (affinity/anti-affinity, allowed regions, fallback policy).
* Ensure provenance/audit captures placement decisions.

## Proposed TaskSpec fields

```json
"policy": {
  "egress": "deny",
  "network_profile": "restricted",
  "residency": {
    "required_regions": ["ap-southeast-2"],
    "preferred_regions": ["ap-southeast-2"],
    "fallback": "block|degrade"
  }
}
```

* **required_regions**: hard constraints; adapters must reject scheduling outside the set.
* **preferred_regions**: hints for multi-region tenants.
* **fallback**: what to do if capacity unavailable (`block`, `queue`, `degrade`).

## Control Plane changes

* PolicyEngine reads tenant residency from SEC-01 config; injects into TaskSpec.
* Scheduler filters worker pools/nodes by region labels; logs placement decision with trace_id.
* Orchestrator adapters map residency to backend-specific constructs (e.g., Temporal namespaces, K8s node selectors, Flyte domains).

## Audit & telemetry

* Metadata DB records `{task_id, region, residency_source, decision}`.
* OBS-01 metrics: `residency_enforced_total`, `residency_violation_total`, `residency_fallback_total{mode}`.
* Alerts when fallback mode triggered or policy violated; include fallback counts in dashboards.

## Prototype plan

1. Add residency fields to TaskSpec schema and update Local + Temporal adapters.
2. Create mock tenant policies to test block/degrade paths.
3. Instrument scheduler to emit placement logs + metrics.
4. Update SEC-01 acceptance criteria to cover residency enforcement tests.

## Risks & mitigations

* **Backend limitations**: some orchestrators may lack per-task region control—keep feature flagged until parity exists.
* **Capacity exhaustion**: implement queue + alert instead of silent fallback.
* **Complex policies**: start with single-region requirement; multi-region/DR later.

## Exit criteria

* TaskSpec schema merged with residency section.
* Local + Temporal adapters honour residency settings in integration tests.
* Audit trail shows placement + policy compliance per task.
