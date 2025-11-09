# Eidolon – Drift Detection & Reconciliation (DR‑01)
---
id: DR-01
version: 0.1
owner: Conformance Lead
status: draft
summary: Drift detection pipeline, data model, UX flows, enforcement modes, and APIs aligning plan intent with code reality.
tags:
  - runtime
  - drift
  - conformance
last_updated: 2025-11-10
---

# Eidolon – Drift Detection & Reconciliation (DR‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Conformance Lead

## 1. Purpose

Define how Eidolon detects, classifies, surfaces, and resolves **drift** between the intended architecture (plan.yaml, ADRs, boundaries, policies) and the actual code and runtime artefacts (CodeGraph, configs). Provide role‑specific UX, APIs, enforcement modes, and audit trails.

## 2. Scope

* Sources of truth: **Plan Layer** (plan.yaml + ADRs + Rulepack) vs **Code Layer** (CodeGraph@latest, scanner findings).
* Drifts covered v1: boundary breaches, layering violations, unplanned components, interface divergence, security posture mismatches, policy‑forbidden dependencies, renames/moves outside selectors.
* Out of scope v1: runtime config drift (K8s manifests, infra as code) – tracked as DR‑EXT.

## 3. Definitions

* **Drift**: Any mismatch between Plan Layer intent and Code Layer facts, evaluated at a commit (or run) boundary.
* **Violation**: A drift that breaks a **blocking** rule.
* **Admissible Drift**: A drift that is permitted temporarily via waivers (time‑boxed).

## 4. Data model additions

### 4.1 DriftItem

```
{
  id, tenant_id, repo_id, commit_sha, detected_at,
  kind: "boundary|layering|unplanned|interface|security|rename|policy",
  severity: "info|warn|error|block",
  plan_context: { plan_version, rule_id?, boundary_id?, selector? },
  code_context: { artefact_ids:[], paths:[], symbols:[] },
  evidence: [uris...],
  suggested_actions: ["propose-plan-delta","generate-patch","create-adr","create-waiver"],
  status: "new|acknowledged|in-progress|waived|resolved|rejected",
  assignee, sla_due,
  links: { dwi_id?, adr_id?, patch_id?, requirement_ids:[] }
}
```

### 4.2 Waiver

```
{ id, drift_id, reason, expires_at, approver, scope: "artefact|boundary|rule", created_at }
```

## 5. Detection pipeline

1. **Trigger**: On run completion or on demand, **ConformanceJob** executes rulepack against `CodeGraph@latest` within the repo scope and current `plan.yaml` selectors.
2. **Diff Resolution**: Compute set differences:

   * `PlannedBoundaries` – `ResolvedBoundaries(CodeGraph)` → *unplanned components/deletions*
   * `Imports(CodeGraph)` ∩ *forbidden pairs(rulepack)* → *layering/boundary breaches*
   * `Interfaces(plan)` vs `ObservedInterfaces` (OpenAPI/IDL diffs) → *interface drift*
   * Security posture rules vs observed sinks/sources → *security drift*
3. **Classification**: Map findings to `DriftItem.kind` and assign severity via rulepack thresholds.
4. **De‑dupe**: Collapse duplicate signals across files into a single DriftItem with multiple artefacts.
5. **Persist**: Create DriftItems; attach evidence links (SQL queries, diffs, AST slices).

## 6. Enforcement modes

* **Observe**: Record drifts; no blocking.
* **Warn**: Surface in UI, emit alerts; merges allowed.
* **Block**: Fail the run and/or mark CI status as failed; require waiver or fix.

Mode is rule‑scoped in Rulepack v1 and overridable per tenant/project.

## 7. Reconciliation flows (role‑aware)

### 7.1 Architect view

* **Inbox**: DriftItems grouped by kind and boundary with trend sparkline.
* **Actions**:

  * *Propose Plan Delta* → opens a DWI with prefilled RefinementDelta to incorporate the code reality (e.g., accept a new component or boundary selector change).
  * *Create ADR* → required when accepting breaking changes or security posture shifts.
  * *Request Fix* → assigns to Coder with generated patch template.
  * *Waive* → time‑boxed waiver; requires approver and justification.
* **What‑if**: “Simulate merge” to preview conformance state after proposed delta.

### 7.2 Coder view

* **Triage**: table of assigned DriftItems with quick‑fix affordances.
* **Automations**: "Generate patch" calls agent to rewrite imports, move files into correct boundary, or adjust interface stubs.
* **Safety**: Patches gated by tests/lint and require approval.
* **Feedback**: Resolve closes the DriftItem; comments capture remediation notes.

### 7.3 Operator view

* **Signals**: run status includes drift summary; blocking drifts stop publish.
* **Controls**: retry after patch; temporarily raise priority for blocking drifts.

### 7.4 Product Owner view

* **Awareness only**: high‑severity drifts flagged when related to accepted requirements; no actions.

## 8. UX specifics

* Drift badge on nav with counts by severity.
* DriftItem detail side‑panel: rule text, evidence queries, affected artefacts, links to DWI/ADR/patch.
* Bulk actions: acknowledge, assign, waive (with limits), or create DWIs in batch.
* Timeline: shows detection, actions, and resolution with actors and hashes.

## 9. APIs

```http
GET  /drift?repo=...&severity=...&status=...        # list
GET  /drift/{id}                                     # detail
POST /drift/{id}/assign { assignee }
POST /drift/{id}/action   { type: "propose-delta|generate-patch|create-adr|waive|resolve|reject", payload: {...} }
POST /drift/scan { repo, commit_sha?, mode: "observe|warn|block" }
GET  /drift/stats?repo=...                            # counts and trends
```

## 10. Rulepack hooks

* Rules emit **severity**, **enforcement mode**, **category**, **message template**, **auto‑fix hints**.
* Example layering rule:

```
rule: layering-ui-not-depend-data
when: import from /^ui\./ to /^data\./
severity: error
mode: block
autofix: { action: "suggest-facade", message: "Introduce service in app layer" }
```

## 10.1 Rulepack DSL (shared contract)

* **Ownership**: jointly by the Refiner team (plan/GateCheck side) and Conformance team (drift enforcement). Published as `rulepack.schema.json`.
* **Schema**: YAML or JSON document with:

  ```
  id: RP-2025-11-01
  version: 1.0.0
  owners: ["refiner", "conformance"]
  rules:
    - id: layering-ui-not-depend-data
      selector: import from /^ui\./ to /^data\./
      severity: error
      enforcement: block
      autofix: { action: "suggest-facade", message: "Introduce service in app layer" }
      scopes: ["drift", "gatecheck"]
  ```

* **Lifecycle**:
  * Stored in `rulepacks/` with semantic versioning.
  * Refiner GateChecks compile the same DSL to evaluate proposed plan deltas.
  * Drift detection uses the compiled selectors to query CodeGraph. Version pinned per run via `rulepack_id`.
* **Execution interface**: `rulepack.compile(rule_id)` → SQL/Query fragments for CodeGraph; `rulepack.evaluate(delta)` → pass/fail with evidence.
* **Open issues**: richer selectors (AST, boundary membership), macro support, and multi-tenancy overrides. Track in RP-DSL backlog.

## 11. CI/PR integration

* GitHub/GitLab status checks reflect drift outcome per run.
* PR comments show DriftItems with links to fix or propose plan changes.
* Optional: pre‑commit hook for local developer feedback (observe mode).

## 12. Metrics & SLOs

* **Time‑to‑acknowledge** (TTA) DriftItem p50/p95
* **Time‑to‑resolution** (TTR) by kind/severity
* **Reopen rate** of resolved drifts within 7 days
* **Auto‑fix success rate** for generated patches

Targets v1: TTA p95 < 1 business day; TTR p95 < 5 business days for non‑blocking.

## 13. Security & audit

* Waivers require approver role; all waivers are time‑boxed with default 7 days.
* Every state change recorded with actor and signature (ProvenanceEnvelope link).
* Drift related patches must pass security and licence checks.

## 14. Performance & scale

* Detection uses SQL compiled queries against `mv_imports_latest` and `mv_boundary_members`.
* Batch classification with cursor paging; UI uses server‑side pagination.
* Incremental: only analyse changed artefacts and their dependants for a commit.

## 15. Acceptance criteria

* Blocking drift prevents docs publish/"green" status without waiver.
* Architect can accept code reality via DWI + ADR and see conformance turn green in a dry‑run preview.
* Coder can resolve at least three built‑in drift kinds using generated patches with guardrails.
* Metrics recorded and visible in Architecture and Operator views.

## 16. Open questions

* Default expiry for waivers per severity?
* How many bulk DWIs allowed per action to avoid mega‑deltas?
* Should interface drift auto‑generate contract tests?
