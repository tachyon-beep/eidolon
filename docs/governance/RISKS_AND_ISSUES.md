---
id: GOV-RISK-REGISTER
version: 0.1
owner: Architecture & PMO
status: draft
summary: Central register for Eidolon risks and issues referenced across design documents; includes owner, mitigation, and status.
tags:
  - governance
  - risk
  - issues
last_updated: 2025-11-10
---

# Risks & Issues Register

| ID | Title | Description | Owner | Mitigation/Next Step | Status |
| --- | --- | --- | --- | --- | --- |
| R-001 | CodeGraph performance | 5 MLOC target with unresolved artefact IDs/selectors | CodeGraph Lead | Synthetic 10.6 M SLOC + CPython scans ingested; queries/concurrency under p95 <4 ms; rename stability validated | Closed |
| R-002 | Rulepack DSL gap | Policy DSL referenced but not fully specified | Refiner + Drift Leads | Finalise schema + compiler (see DR-01 §10.1) | Mitigating |
| R-003 | Orchestrator matrix | Supporting 6 adapters inflates QA/scope | Orchestrator Team | v1 limited to Local + Temporal; others feature-flagged | Mitigating |
| R-004 | Product LLM vs SEC defaults | Product view depends on LLM while tenants default to Disabled | Security + Product | Sanitised bridge documented; deliver redaction/audit path before enabling | In progress |
| R-005 | TaskSpec residency hints | SEC-01 requires per-tenant region pinning; TaskSpec lacks knobs | Architecture + Security | Design residency fields + scheduler integration | Open |
| I-001 | Integration prioritisation | Provider priority undecided, blocking GTM sequencing | Integrations Lead | Produce phased provider roadmap (GitHub/Jira first) | Open |
| I-002 | Telemetry propagation | Need concrete plan tying ORCH-01 spans to OBS-01 metrics | Observability Lead | Define instrumentation spec + tooling ownership | Open |

Add new entries here and cross-link to ADRs, rulepacks, or roadmap items as they emerge.
