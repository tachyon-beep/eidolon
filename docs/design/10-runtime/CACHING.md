# Eidolon – Caching & Cost Governance (CASH‑01)
---
id: CASH-01
version: 0.1
owner: Platform Lead
status: draft
summary: Unified caching and cost governance model covering keys, TTLs, invalidation, budgets, and telemetry across Eidolon runs.
tags:
  - runtime
  - caching
  - cost
last_updated: 2025-11-10
---

# Eidolon – Caching & Cost Governance (CASH‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Platform Lead

## 1. Purpose

Define a unified caching and cost governance model for Eidolon that reduces spend and runtime while preserving correctness. Covers cache key derivation, layers, TTLs, invalidation, failure semantics, pre‑flight cost estimation, budgets/quotas, and telemetry. Integrates with ORCH‑01 (TaskSpec.cache), CG‑01 (artefact/commit SHAs), DET‑01 (determinism modes), and SEC‑01 (classification and residency).

## 2. Principles

* **Correctness first**: caches must be keyed by all inputs that affect observable output.
* **Idempotent & reproducible**: cache entries include provenance (manifest hashes, tool versions).
* **Cheap to check, fast to miss**: cache lookup latency < 10 ms p95.
* **Transparent to users**: Operator/Coder/Architect can see hits/misses and reasons.

## 3. Cache layers

1. **Result cache (primary)** – keyed on content + config; stores Evaluation/Synthesis outputs.
2. **Blob cache** – ASTs, tokenised chunks, diagrams.
3. **Plan cache** – resolved selectors, boundary memberships, compiled rulepacks.
4. **Network/cache of record** – optional HTTP cache for third‑party docs/spec pulls (hash‑validated).

Backends: Redis (lookup index) + Object Store (payloads); Postgres holds provenance and index for audit.

## 4. Key derivation (canonical)

```
cache_key = SHA256(
  artefact_sha ||
  commit_sha ||
  task_name ||
  tool_versions_hash ||
  policy_id ||
  determinism_mode ||
  prompt_pack_id ||
  llm_profile_hash ||
  chunking_hash ||
  inputs_hash
)
```

* **artefact_sha**: from CG‑01 (file/module/function).
* **tool_versions_hash**: pinned versions for evaluator/synthesiser.
* **prompt_pack_id/llm_profile_hash**: from DET‑01’s manifest.
* **inputs_hash**: any extra flags/options serialised and hashed.

Cache scope includes **tenant_id** to prevent bleed; SEC‑01 residency honoured by bucket selection.

## 5. TTLs & eviction

* Default TTLs: `result=30d`, `blob=60d`, `plan=7d`.
* LRU within class; size caps per Tenant and per cache layer (configurable).
* **Pinning**: Architecture can pin entries for regulated audits.
* Eviction policy emits `cache.evicted` events with provenance.

## 6. Invalidation

* **Content change**: new artefact_sha → different key (cold).
* **Toolchain/policy change**: version bump or policy ID change → different key.
* **Prompt change**: prompt_pack_id change → different key.
* **Forced bust**: Operator/Coder can `--no-cache` or per‑rule invalidate; all invalidations logged.

## 7. Partial/failure semantics

* **Write on success only** by default.
* **Partial cache**: optional mode to store intermediate artefacts with `status=partial`; readers must honour `status`.
* **Negative caching**: backoff window for recurrent deterministic failures (e.g., compile error) keyed to inputs; prevents thundering herds.

## 8. Pre‑flight cost estimator

### 8.1 Inputs

* Files to evaluate (N), average tokens per artefact (T), model cost tables (per‑1K input/output), compute rates (CPU/GPU per hour), expected cache hit rate (H), concurrency caps.

### 8.2 Formulae (simplified)

* **LLM tokens**: `LLM_in = N*(1-H)*T_in`, `LLM_out = N*(1-H)*T_out`
* **LLM cost**: `Cost_LLM = (LLM_in*Cin + LLM_out*Cou)/1000`
* **Compute**: `Time_task = Base + Eval*(1-H)`; `Cost_CPU = ceil(sum(Time_task)/Slot_eff)*Rate_CPU`
* **Total**: `Cost_total = Cost_LLM + Cost_CPU + Storage_io`

Estimator returns *p50/p95* with a confidence band using historical run telemetry. Displays in Operator view before starting a run; warns on budget breaches.

## 9. Budgets, quotas & enforcement

* **Budgets**: per Tenant monthly caps for `tokens_in`, `tokens_out`, CPU‑hours, GPU‑hours, storage GB‑months.
* **Soft cap**: warnings at 80%; **hard cap**: block or degrade (skip expensive LLM steps) at 100%.
* **Quotas**: per‑run and per‑day ceilings; per‑user burst limits.
* **Priority classes**: `background|standard|urgent` affect queueing and cap allocation.
* All decisions flow through ORCH‑01 `concurrency.class` and **PolicyEngine**; breaches recorded as policy events.

## 10. UI and operator experience

* Operator view shows **Forecast panel** (costs, time), **Cache panel** (hit/miss ratio, reasons), and **Budget panel** (usage vs caps).
* Coder view shows cache status per artefact with reasons (e.g., tool version changed).
* Architect view shows cost deltas for design options (e.g., enabling certain checks).

## 11. Telemetry & metrics

* **Per task**: `cache_hit:boolean`, `cache_ttl_remaining`, `lookup_ms`, `store_ms`, `payload_bytes`
* **Per run**: `hit_rate`, `savings_tokens`, `savings_ms`, `evictions`, `negative_cache_hits`
* **Cost**: `est_llm_tokens_in/out`, `est_cpu_hours`, `actual_*` variants for variance tracking.
* Alerts: hit rate drop > 20% week‑over‑week; budget soft cap reached; estimator variance > 25% p95.

## 12. Governance & audit

* Cache entries include ProvenanceEnvelope: manifest hash, signer, timestamps.
* All forced busts and policy overrides recorded with actor and reason.
* Per‑Tenant cache export for audit (index + pointers, no payload by default).

## 13. Interfaces

* ORCH‑01: `CacheCheck(key)` and `CacheStore(key, outputs, meta)` RPCs.
* API: `GET /cache/lookup?key=...`, `POST /cache/invalidate`, `GET /budgets`, `POST /budgets`, `GET /cost/estimate`.
* Events: `cache.hit`, `cache.miss`, `cache.store`, `cache.evicted`, `budget.warn`, `budget.block`.

## 14. Performance targets

* Lookup p95 ≤ 10 ms; Store p95 ≤ 50 ms; Index sync lag ≤ 500 ms.
* Estimator runtime ≤ 250 ms for 10k artefacts.
* Baseline cache hit rate ≥ 60% on stable repos; ≥ 80% after warm‑up.

## 15. Acceptance criteria

* Keys derive from all material inputs; collisions prevented in tests.
* Forecast appears pre‑run with p50/p95 bands and matches actuals within 25% p95.
* Budgets enforce soft/hard caps correctly with clear UI and audit entries.
* Negative caching prevents > 70% of repeated deterministic failures under load tests.
* Residency and Tenant isolation preserved across cache layers.

## 16. Open questions

* Do we need per‑project sub‑budgets within a Tenant?
* Should we expose cache warm‑up jobs per branch for CI acceleration?
* Minimum viable rate card for GPU tasks in v1?
