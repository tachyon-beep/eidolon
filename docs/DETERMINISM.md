# Eidolon – Determinism & Evaluator Flakiness (DET‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Evaluator Team Lead

## 1. Purpose

Guarantee reproducibility and predictable behaviour of Eidolon evaluations (static tools and optional LLMs). Define modes, manifests, variance thresholds, retry policies, and replay tooling. Integrates with ORCH‑01 (cache/telemetry), CG‑01 (artefact IDs), RF‑01 (gates), and DR‑01 (drift semantics).

## 2. Scope

* Applies to all **Evaluator** tasks and any agent invoking analysis or patch generation.
* Covers: randomness control, temperature caps, floating dependency lock‑down, stable chunking, prompt provenance, and statistical equivalence checking.

Out of scope v1: deterministic GPU kernels across vendors; cross‑model alignment.

## 3. Determinism modes

* **D0 – Best Effort**: static tools pinned; LLMs unconstrained (for exploratory sessions). Not used in CI.
* **D1 – Stable** (default for CI): static tools pinned; LLMs use bounded variance with fixed seeds and temperature caps; results must fall within thresholds.
* **D2 – Strict**: static tools pinned; LLMs disabled or local deterministic models only; byte‑identical outputs required.

Mode is selected per run; PolicyEngine can elevate to D2 for sensitive projects.

## 4. Run Manifest (authoritative)

`run-manifest.json` attached to each Run:

```
{
  "run_id": "r-123",
  "repo": "proj-x",
  "commit_sha": "6f3a...",
  "plan_sha": "abc123",
  "policy_id": "default@2025-10-01",
  "determinism_mode": "D1",
  "toolchain": {
    "python": "3.11.7",
    "evaluator": {"ruff": "0.6.9", "mypy": "1.11.1", "bandit": "1.7.9"},
    "scanner": "cg@1.0.0",
    "synthesiser": "syn@1.1.0"
  },
  "llm_profile": {
    "provider": "local|managed",
    "model": "name@version",
    "temperature": 0.2,
    "top_p": 0.9,
    "seed": 42,
    "max_tokens": 2048,
    "prompt_pack": "arch-critique@2025-10-15"
  },
  "chunking": {"strategy": "ast-scope", "max_chars": 8000, "overlap": 256},
  "environment": {"tz": "UTC", "locale": "en_AU"}
}
```

Control Plane signs the manifest; Workers read‑only.

## 5. Prompt & input provenance

* Store **prompt pack** ID, **prompt hash**, and **tool versions** with each EvaluationRecord.
* Persist only hashes by default; full prompts stored in SENSITIVE object store when policy allows.
* Record **input digests** for every artefact and config used in generation/evaluation.

## 6. Seeds and randomness

* Global run seed from manifest; task seeds derived deterministically: `task_seed = HMAC(run_seed, task_id)`.
* For LLMs that accept seeds: pass `task_seed` and set `temperature ≤ 0.2` in D1, `0.0` in D2.
* For tools without seed support: wrap with retry‑with‑jitter disabled; capture non‑deterministic warnings.

## 7. Stable chunking & ordering

* Use AST‑anchored chunking (function/class boundaries).
* Sort deterministically (path, then start‑line).
* Disallow heuristic reflow that depends on token counters in D1/D2.

## 8. Floating dependency control

* Lock files per evaluator (`requirements.lock`).
* Container images pinned by digest; ORCH‑01 task spec includes image digest.
* Time‑based data (dates, timestamps) mocked to manifest `environment.tz`.

## 9. Bounded‑variance acceptance (D1)

Define **equivalence classes** instead of byte identity for LLM outputs:

* **Textual JSON**: parse to schema; ignore key order/whitespace; compare values with tolerance for floats.
* **Natural language**: compare **scores** from a deterministic rubric grader; success if score ≥ threshold (e.g., 0.95) or if extracted structured fields match.
* **Patch proposals**: diffs must compile and pass tests; minor differences in comments acceptable.

Record **EquivalenceReport** alongside EvaluationRecord:

```
{ "baseline_id": "run:r-100:task:t-77", "method": "json/schema|nlp/rubric|compile/tests", "score": 0.97, "threshold": 0.95 }
```

## 10. Replay tooling

* `eidolon replay --run r-123 [--subset artefact_glob] [--mode D1|D2]` re‑executes tasks with the manifest.
* Supports **baseline selection** (previous successful run) and emits EquivalenceReports.
* Integrates with ORCH‑01: respects cache; `--no-cache` flag for full replay.

## 11. Flakiness management

* **Retry policy**: transient categories (`RetriableNetwork`, `ResourceExhausted`, `SystemError`) retried with capped backoff; `UserCodeError` not auto‑retried unless marked flaky.
* **Quarantine**: mark evaluator tool as flaky when failure rate > threshold over N tasks; route to a smaller concurrency class; raise alert.
* **A/B sentinel tasks**: run a small, fixed sample each release to detect drift before full runs.

## 12. Metrics & alerts

* Metrics per task: `determinism_mode`, `seed`, `temp`, `equivalence_score`, `variance_exceeded`, `retries`, `flaky_flag`.
* Alerts: variance breach rate > 2% over last 1k tasks; evaluator quarantine activated; replay mismatch on D2.

## 13. Integration points

* **ORCH‑01**: TaskSpec carries determinism fields; heartbeats include seed/temp for debugging. Cache keys embed `prompt_pack` and tool versions.
* **CG‑01**: Artefact SHA and commit SHA drive cache keys; stable IDs ensure repeatable fan‑out.
* **RF‑01/DR‑01**: Gate checks can require D2 for security‑sensitive DWIs; drifts cannot be waived if replay mismatches persist.

## 14. Acceptance criteria

* D1: ≥ 95% of replays produce equivalent outputs on two successive runs of the same SHA.
* D2: ≥ 99.9% byte‑identical outputs (excluding timestamps) for static‑tool‑only paths; LLMs disabled or local deterministic.
* Replay tool reproduces an entire run with `--no-cache` and reports EquivalenceReports.
* Quarantine reduces flaky failure rate by ≥ 80% under load tests.

## 15. Open questions

* Which deterministic rubric grader to adopt for NL equivalence (internal rules vs lightweight classifier)?
* What default temperature for D1 across different model families (0.1–0.3)?
* Should D2 allow small, whitelisted normalisations (e.g., whitespace) or require exact bytes?
