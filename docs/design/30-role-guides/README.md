---
id: ROLE-README
version: 1.0
owner: Product & Architecture Teams
status: draft
summary: Directory of role guides plus shared workflows, shortcuts, and glossary references.
tags:
  - role-guide
  - index
last_updated: 2025-11-10
---

# Eidolon – Role Guides Overview

Use this summary to jump to the detailed handbooks:

| Role | Focus | Link |
| --- | --- | --- |
| Operator | Runs & capacity, concurrency knobs, budgets | [Operator Guide](./OPERATOR.md) |
| Coder | Tactical quality control, guardrails, agent collab | [Coder Guide](./CODER.md) |
| Architect | Strategic oversight, plan.yaml, ADRs, drift | [Architect Guide](./ARCHITECT.md) |
| Product Owner | Requirement capture, NFRs, backlog shaping | [Product Owner Guide](./PRODUCT_OWNER.md) |

## Shared essentials

* **Provenance everywhere**: ADRs, patches, scans, and runs carry signatures and hashes.
* **Modes matter**: determinism (D0/D1/D2) and LLM mode (Disabled/Strict/Balanced) change behaviour and costs.
* **Budgets are real**: token/compute budgets enforced per Tenant; plan work accordingly.
* **Traceability**: Everything ties back to `plan.yaml`, CodeGraph, and Requirements.

## Quick reference shortcuts

* `g` then `o` – Operator view
* `g` then `c` – Coder view
* `g` then `a` – Architecture view
* `g` then `p` – Product view
* `/` – global search    |    `.` – command palette    |    `?` – keyboard cheatsheet

## Glossary

* **DWI**: Design Work Item (unit of refinement)
* **Drift**: divergence between plan.yaml and code reality
* **Rulepack**: conformance/security/interop rules
* **ProvenanceEnvelope**: signed metadata for artefacts
* **EquivalenceReport**: replay variance report for D1
