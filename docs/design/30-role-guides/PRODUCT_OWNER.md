---
id: ROLE-PRODUCT-OWNER
version: 1.0
owner: Product Team
status: draft
summary: Product Owner handbook for capturing requirements, partnering with the Product LLM, and tracking acceptance.
tags:
  - role-guide
  - product
  - requirements
last_updated: 2025-11-10
---

# Product Owner Guide (Discovery & Shaping)

## Mission

Turn conversations into clear, testable requirements that guide architecture and delivery.

## Your home base

* **Product view**: ProductChat, RequirementsTable, UseCaseCanvas, NFREditor.

## Daily rhythm

1. **Converse**: describe outcomes; let the Product LLM tease out use cases and NFRs.
2. **Curate**: edit for clarity; add acceptance criteria; de-duplicate.
3. **Submit**: send to Architect inbox for consideration; track status.

## Core actions

* Create/modify **RequirementRecords**; link to plan goals and ADRs once accepted.
* Review status and impact summaries (cost/perf implications from CASH-01/OBS-01).

## Playbooks

* **Ambiguous request**: ask for examples/constraints; prefer user stories with “Given/When/Then”.
* **Performance ask**: specify NFRs (p95, throughput, latency budgets); the system will estimate cost.
* **Big scope**: split into epics; allow Architect to phase DWIs.

## KPIs

* Requirement→Plan conversion rate; time-to-plan inclusion; churn rate (rejected/withdrawn).

## Permissions

* Create/edit requirements; read-only on code artefacts; no run or patch approvals.

## Escalation

* To **Architect** when requirements stall; to **Operator** only for scheduling major evaluation windows.
