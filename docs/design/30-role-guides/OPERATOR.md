---
id: ROLE-OPERATOR
version: 1.0
owner: Runs & Capacity Team
status: draft
summary: Operator handbook for managing Eidolon runs, queues, and capacity while keeping budgets and determinism modes in check.
tags:
  - role-guide
  - operator
  - runtime
last_updated: 2025-11-10
---

# Operator Guide (Runs & Capacity)

## Mission

Keep Eidolon humming: healthy queues, predictable throughput, clean recoveries.

## Your home base

* **Operator view**: QueueDepth, Throughput, ErrorRate, CacheHit, TokenSpend, Concurrency utilisation.
* **Drill-downs**: RunList → RunDetail (Gantt + DAG), LiveLog, AlertStream, Budget panel.

## Daily rhythm

1. **Morning sweep**: check SLO widgets (queue p95 < 2m, task success ≥ 99.5%).
2. **Backlog triage**: raise/trim priorities; thaw circuit breakers.
3. **Forecast checks**: review cost/time estimates for large runs before start.
4. **Health watch**: cache hit ratio, token spend, rate-limit banners.

## Core actions

* Start/Pause/Resume/Retry runs.
* Adjust **concurrency sliders** (per `concurrency.class`).
* Trigger **cache warm-ups** and **replays** (DET-01) when needed.
* Flip **LLM mode** (Disabled/Strict/Balanced) if authorised.

## Playbooks

* **Bursty backlog**: cap per-tenant parallelism; prioritise diff-scoped runs; warm cache for hot modules.
* **Evaluator flakiness**: move class to quarantine; lower parallelism; schedule replay (D1/D2).
* **Rate-limited provider**: switch panel to Degraded; queue outbound actions with backoff; notify owners.
* **Budget breach**: enforce soft caps; negotiate deltas; if hard cap hit, degrade by skipping expensive LLM steps.

## Alerts you own

* `task_failures`, `cache_hit_ratio drop`, `budget_util_pct`, `api_5xx_rate`.

## KPIs

* Queue p95 latency; Task success; Time-to-first-finding; Forecast vs actual cost variance.

## Permissions

* Run control, concurrency, cache ops. No code write access.

## Escalation

* To **Coder** for persistent task failures; **Architect** for blocking drift; **Security** for egress blocks.
