---
id: AGT-01
version: 0.1
owner: Evaluator Team / Security Lead
status: draft
summary: Guardrail policy defining agent capabilities, path permissions, patch limits, sandboxing, approval flow, and telemetry ties across Eidolon.
tags:
  - governance
  - guardrails
  - security
last_updated: 2025-11-10
---

# Eidolon – Agent Guardrails & Permissions (AGT‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Evaluator Team / Security Lead

## 1. Purpose

Define what agents may see, decide, and change — and under what controls. Cover tool palettes, file/path permissions, patch size limits, sandboxing, approval flow, provenance, and audit. Integrates with SEC‑01 (policy), ORCH‑01 (task policy), RF‑01 (DWIs), DR‑01 (drift), DET‑01 (determinism), CASH‑01 (cost), DATA‑01 (schemas), and OBS‑01 (telemetry).

## 2. Agent classes

* **Function Agent** – analyses a single function; proposes doc/test/patch.
* **Class Agent** – aggregates across methods; proposes refactors.
* **Module Agent** – operates within a module/package; can move symbols internally.
* **Subsystem Agent** – read‑only by default; proposes design deltas (via DWI) rather than patches.
* **System Agent** – advisory only; no write perms.

## 3. Capability model

### 3.1 Tool palette (whitelist per class)

| Tool              | Fn        | Class       | Module              | Subsystem          | System |
| ----------------- | --------- | ----------- | ------------------- | ------------------ | ------ |
| "Explain finding" | ✅         | ✅           | ✅                   | ✅                  | ✅      |
| "Generate tests"  | ✅         | ✅           | ✅                   | ⚠️ (proposal only) | ⚠️     |
| "Propose patch"   | ✅ (≤ fn)  | ✅ (≤ class) | ✅ (≤ module)        | ❌                  | ❌      |
| "Refactor symbol" | ✅ (local) | ✅ (class)   | ✅ (within module)   | ❌                  | ❌      |
| "Move file"       | ❌         | ❌           | ⚠️ (needs approval) | ❌                  | ❌      |
| "Open DWI"        | ⚠️        | ⚠️          | ⚠️                  | ✅                  | ✅      |
| "Run checks"      | ✅         | ✅           | ✅                   | ✅                  | ✅      |

Legend: ✅ allowed; ⚠️ allowed with approval or gated; ❌ disallowed.

### 3.2 Data access

* Agents receive **only** the minimal context: AST slice + surrounding lines + symbol table + metrics + plan boundary info.
* Raw secrets redacted before context (SEC‑01 redaction pipeline).

## 4. Path & content permissions

* **Allow‑list** per Project defining writable paths (glob):

  * `src/**` (code)
  * `tests/**` (tests)
  * `docs/**` (docs)
* **Deny‑list** always:

  * `infra/**`, `deploy/**`, `.github/**`, `scripts/release/**`
  * `**/secrets/**`, `**/*.pem`, `**/*.key`
* **Escalation**: file moves across subsystem boundaries require Architect approval (Architecture view).

## 5. Patch limits & heuristics

* **Size caps**:

  * Function Agent ≤ 80 changed LOC; Class Agent ≤ 150; Module Agent ≤ 300.
* **Blast radius**: max files touched per patch: Fn=1, Class=3, Module=5.
* **Complexity**: forbid simultaneous API surface changes and algorithmic refactors in same patch; split automatically.
* **Safety checks (must pass before submit)**:

  * compiles/types clean (ruff/mypy/pyright);
  * tests added/updated when code paths are changed;
  * no new deps added without approval;
  * licence headers preserved;
  * secrets check passes.

## 6. Sandboxing & runtime

* Execute code generation and validation in **restricted containers** (rootless, read‑only FS, seccomp/apparmor; optional gVisor/Kata per SEC‑01).
* **Egress default deny**; allow‑list for fetching stdlib docs only.
* CPU/GPU quotas via ORCH‑01 `resources` and `concurrency.class`.

## 7. Approval workflow (state machine)

```
[Draft] --self-checks pass--> [Proposed]
[Proposed] --Coder review approve--> [Approved]
[Proposed] --Coder requests changes--> [Changes-Requested]
[Approved] --CI checks pass--> [Ready-to-Merge]
[Ready-to-Merge] --Architect sign-off (if boundary/API)--> [Merge-Allowed]
[Merge-Allowed] --Operator triggers/CI auto--> [Merged]
[Any] --policy violation--> [Rejected]
```

* Boundary/interface changes always require Architect sign‑off; minor internal fixes do not.

## 8. Provenance & audit

Every patch includes a **PatchEnvelope**:

```
{
  patch_id, agent_class, inputs: {artefact_id, commit_sha, context_digest},
  prompt_pack, tool_versions, determinism: {mode, seed, temp},
  checks: {lint, type, tests},
  supply_chain: {dependency_changes: [], licences: [], sbom_delta},
  drift_links: {drift_item_ids: [], boundary_ids: []},
  signature: {signer, signature},
  created_at
}
```

Stored in Object Store; hash recorded in Metadata DB. Visible in Coder/Architect views.

## 9. Unsafe patterns & auto‑blocks

* Writes to deny‑listed paths → block.
* Adds network calls or subprocess launches → block unless approved.
* Introduces dynamic import hacks to skirt boundaries → block and flag DR‑01.
* Adds dependency on forbidden packages/licences → block via SUP‑01.
* Oversized diffs → auto‑split or require manual review.

## 10. Rate & cost guards

* Token budgets enforced per Agent via `concurrency.class` and CASH‑01 budgets.
* Patch generation rate limited: default 10 proposals/hour per repo; burst tokens for incidents.

## 11. APIs

```http
POST /agents/patches           # create draft from agent
POST /agents/patches/{id}/submit
POST /agents/patches/{id}/decision {approve|request-changes|reject}
GET  /agents/patches/{id}/envelope
POST /agents/analysis          # run explain/test-gen without write perms
```

## 12. Telemetry & SLOs

* Metrics: `patches_proposed`, `patches_approved`, `auto_block_rate`, `avg_review_time`, `rollback_rate` (7 days), `false_positive_block_rate`.
* Alerts: rollback_rate > 2%; auto_block_rate spike > 20% day‑over‑day.

## 13. UI behaviours

* Coder view shows guardrail status chips (size, paths, tests, deps, licence) with tooltips.
* Diff viewer highlights boundary crossings and licence changes.
* One‑click “split patch” if caps exceeded.

## 14. Acceptance criteria

* Agents cannot modify deny‑listed paths; attempts are logged and surfaced.
* All patches carry valid PatchEnvelope with reproducible inputs (DET‑01 alignment).
* PatchEnvelope must include SUP‑01 metadata (dependency/licence deltas) and DR‑01 context (linked DriftItems/boundaries) so reviewers have a consolidated guardrail report.
* Oversized or boundary‑crossing patches require appropriate approvals.
* Rollback rate under 2% over 30 days in staging; guardrails reduce review time by ≥ 20%.

## 15. Open questions

* Default per‑role patch size caps?
* Should Module Agent ever be allowed to add a new dependency if licence ok?
* Auto‑format and re‑order imports: do we count those lines in LOC caps or ignore cosmetic churn?
