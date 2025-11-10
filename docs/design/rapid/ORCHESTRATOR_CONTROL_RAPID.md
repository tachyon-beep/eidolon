---
id: RAPID-ORCH-CTRL
version: 0.1
owner: Orchestrator Lead
status: draft
summary: Rapid design to deliver the Control Plane/PolicyEngine that assembles TaskSpecs, enforces residency, and persists placements.
tags:
  - rapid-design
  - orchestrator
  - control-plane
last_updated: 2025-02-15
---

# Orchestrator Control Plane Rapid

## Problem Statement
TaskSpec schema now encodes residency + telemetry, but there is no Control Plane implementation to ingest tenant policies, assemble TaskSpecs, or persist placement telemetry. Without it, the scheduler/adapters can’t enforce policies in production.

## Scope
* PolicyEngine that merges tenant (SEC-01) + plan overrides and injects `policy.residency`.
* JobSpec/TaskSpec assembler + API for adapters/scheduler.
* Placement/result persistence (metadata DB, API endpoints).
* Hooks that trigger rulepack pipeline post-run.

## Out of scope
* Adapter-specific queue implementations (handled in other RAPIDs).
* UI changes in Refiner/Operator portals (consume APIs later).

## Plan
1. Build PolicyEngine module (SEC-01 config parsing + override resolution).
2. Implement Control Plane service that stores JobSpec/TaskSpec, exposes API for scheduler/adapters, and records placements/results.
3. Emit placement telemetry (metrics/logs) and integrate with residency pipeline.
4. Expose run status endpoints for CI/UI consumption.

## Exit Criteria
* Control Plane service runs locally with sample tenant configs and hands TaskSpecs to orchestrator prototype (Local/Temporal/Airflow adapters).
* Placements/results stored in metadata store and exposed via CLI/API.
* CI uses the API instead of direct CLI wiring.

> **Implementation note (2025-02)**: Control Plane + Airflow adapter stub now exist; pools can specify `adapter: airflow` while the CLI persists
> jobs and placements. Future work is exposing the service via HTTP and integrating with a real Airflow instance.
