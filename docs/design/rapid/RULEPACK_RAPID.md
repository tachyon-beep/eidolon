---
id: RAPID-RULEPACK
version: 0.1
owner: Refiner & Conformance Leads
status: draft
summary: Rapid design to deliver a shared Rulepack DSL/compiler consumed by GateChecks, Drift detection, and agent guardrails.
tags:
  - rapid-design
  - rulepack
  - policy
last_updated: 2025-11-10
---

# Rulepack DSL Rapid Design

## 1. Problem Statement
HLD/RF/DR specs assume a unified Rulepack DSL, but no executable form exists today. Without it, GateChecks, Drift detection, and guardrails will diverge or require hand-maintained SQL. This rapid effort builds the minimal compiler/runtime needed to express policy rules over CodeGraph + metadata.

## 2. Scope & Out-of-Scope
**In scope**
- Schema + validation (`rulepack.schema.json`).
- Authoring CLI (`rulepack init/test/publish`).
- Compiler that emits SQL fragments for CodeGraph tables (artefacts, file_metrics/imports/calls, boundary_stats).
- Runtime loader in Control Plane (Python) and tests proving DR‑01/RF‑01 flows consume the same output.

**Out of scope (for now)**
- Advanced AST selectors (beyond package/path/import/call attributes).
- Multi-tenant overrides and pack inheritance.
- UI authoring experience (text editor assumptions only).

## 3. Architecture Sketch
1. **Authoring** – YAML file with `metadata` + `rules[]`. Each rule includes `id`, `description`, `scopes`, `selector`, `predicate`, `severity`, `enforcement`, optional `autofix` hints.
2. **Compiler** – Python module that parses the YAML and translates selectors into SQL templates targeting CodeGraph tables (joins over `file_metrics`, `file_imports`, `function_calls`, `boundary_stats`). Output bundles compiled SQL + metadata JSON.
3. **Runtime** – Refiner GateCheck service and Drift detector both call `rulepack.compile(rule_id)` to obtain SQL, execute against Postgres/CodeGraph, and receive result rows with evidence links.

## 4. Interfaces
- CLI: `rulepack init`, `rulepack test <pack.yaml>`, `rulepack publish <pack.yaml>`.
- Pack schema: `rulepack.yaml` + optional `tests/*.yaml` describing fixtures.
- Runtime API: Control Plane loads packs from object store, caches compiled JSON, and exposes `RulepackRegistry.get(rule_id)` for Refiner/Drift.

## 5. Prototype Plan
1. Define `rulepack.schema.json` + minimal selector grammar (path glob, boundary, import pattern, call target, SLOC thresholds).
2. Implement compiler producing SQL for each selector type, plus DSL tests (e.g., layering, boundary import, sensitive call usage).
3. Hook DR‑01 Drift job to consume compiled SQL for two pilot rules (layering + call ban) and compare vs existing ad-hoc queries.
4. Hook RF‑01 GateCheck service to use the same compiled pack for design-time validation.
5. Package CLI + schema, publish sample packs (`layering-core`, `security-call-ban`).

## 6. Metrics & Exit Criteria
- Compiler passes unit tests covering ≥5 canonical rules.
- Drift detection runs using the compiled pack for at least 2 rule categories (layering, security) without regressions.
- GateCheck simulation uses the same pack to block/allow design deltas.
- Rulepack publish manifests stored in object store with version IDs referenced in run manifests.

## 7. Risks & Mitigations
- **Selector expressiveness vs SQL perf** – keep selectors constrained; enforce test-run before publish.
- **Authoring errors** – provide `rulepack test` with synthetic fixtures and lints.
- **Runtime drift** – central registry ensures Refiner/Drift load the same `rulepack_id`; version pinned in run manifests.

## 8. Next Steps
- Assign owners for schema + compiler + runtime wiring.
- Schedule 1-week spike to ship `rulepack` CLI and integrate two pilot rules end-to-end.
- Update DR‑01/RF‑01 docs once pilot packs validate.
