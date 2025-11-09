---
id: ROLE-ARCHITECT
version: 1.0
owner: Architecture Council
status: draft
summary: Architect handbook for managing plan.yaml, ADRs, drift reconciliation, and strategic decisions.
tags:
  - role-guide
  - architect
  - governance
last_updated: 2025-11-10
---

# Architect Guide (Strategic Oversight)

## Mission

Shape the system. Maintain HLD conformance, security posture, and interoperability while enabling delivery.

## Your home base

* **Architecture view**: HLDCompliance, ThreatModel, Interop matrix, C4Viewer, PlanEditor, ADRBoard, SubsystemAgentChat, IntegrationBugTracker.

## Daily rhythm

1. **Inbox**: new Requirements and DriftItems (grouped by boundary).
2. **Refinement**: pick DesignWorkItems, run gate checks, progress to Implementable.
3. **Decisions**: author ADRs for boundary/interface/security changes.
4. **Recon**: dry-run conformance; simulate merges; hand off tasks to Operator/Coder.

## Core actions

* Curate `plan.yaml` (boundaries, interfaces, policies).
* Approve design-affecting patches; accept/reject drifts via ADR + DWI.
* Tune Rulepack; manage waivers (time-boxed) for unavoidable drifts.

## Playbooks

* **Drift storm**: batch create DWIs; prioritise by blast radius and risk; set temporary `warn` mode for low-risk rules.
* **Security posture shift**: run ThreatModel, update policies, push ADR; require D2 runs for impacted areas.
* **Interoperability break**: version interfaces; stage compatibility matrix; require contract tests.

## KPIs

* DWI throughput/merge time; HLD compliance trend; Drift TTA/TTR; Waiver count and age.

## Permissions

* Approve ADRs; merge DWIs; change policies/rules; accept boundary changes. Limited run controls.

## Escalation

* To **Operator** for capacity, **Security** for policy exceptions, **Product Owner** for scope trade-offs.
