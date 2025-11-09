---
id: DATA-01
version: 0.1
owner: Data Lead
status: draft
summary: Unified data model, ERD, retention, and governance rules for Eidolon metadata, artefacts, and telemetry stores.
tags:
  - foundation
  - data
  - governance
last_updated: 2025-11-10
---

# Eidolon – Data Model Hardening & Retention (DATA‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Data Lead

## 1. Purpose

Unify and harden Eidolon’s core data model across Metadata DB, Object Store, and caches. Provide ERD, JSON Schemas, constraints, migrations, retention policies, and indexing strategies. Aligns with CG‑01 (CodeGraph), RF‑01 (Refiner), DR‑01 (Drift), ORCH‑01 (Adapter), DET‑01 (Determinism), CASH‑01 (Cache/Cost), OBS‑01 (Telemetry), and SEC‑01 (Classification & Residency).

## 2. Design principles

* **Single source of truth** per domain; cross‑references via stable IDs.
* **Strong referential integrity** in Postgres; blobs in Object Store carry ProvenanceEnvelope.
* **Versioned schemas** (semver) with forward‑compatible migrations.
* **Tenant isolation**: tenant_id on all tables + RLS policies.
* **Time travel** for key entities (plan versions, commits, runs).

## 3. Logical ERD (high‑level)

**Tenants(tenant_id)**

* Users(user_id, tenant_id, role)

**Projects(project_id, tenant_id)**

* Repos(repo_id, project_id, default_branch)
* Plans(plan_id, project_id, version, sha, status)
* ADRs(adr_id, project_id, plan_id, status)

**Runs(run_id, repo_id, plan_id, commit_sha, policy_id, determinism_mode, created_at, status)**

* Tasks(task_id, run_id, spec_hash, state, retries, started_at, finished_at)
* Artifacts(artifact_id, run_id, task_id, type, uri, class, size, hash, created_at)

**CodeGraph**

* Artefacts(artefact_id, repo_id, path, kind, fqname, commit_sha, sha256, metrics)
* Edges_Imports(src_id, dst_id, commit_sha, symbols, is_dynamic)
* Edges_Contains(parent_id, child_id, commit_sha)
* Boundaries(boundary_id, project_id, type, name, selector, plan_version)
* Maps_To_Boundary(artefact_id, boundary_id, commit_sha, source)

**Findings & Decisions**

* EvaluationRecords(eval_id, run_id, artefact_id, tool, tool_version, prompt_pack, score, status, manifest_hash, seed, temperature, created_at)
* DriftItems(drift_id, repo_id, commit_sha, kind, severity, status, evidence_uri, plan_context, code_context, created_at)
* Waivers(waiver_id, drift_id, approver, expires_at, reason)
* DesignWorkItems(dwi_id, plan_id, owner, state, created_at)
* RefinementDeltas(delta_id, dwi_id, base_plan_sha, patch, impact)
* Requirements(req_id, project_id, title, priority, status, links)

**Governance & Security**

* Policies(policy_id, tenant_id, doc, active)
* Provenance(prov_id, subject_id, subject_type, signer, signature, manifest_hash, created_at)
* Budgets(budget_id, tenant_id, tokens_in_cap, tokens_out_cap, cpu_hours_cap, gpu_hours_cap, storage_cap)

**Telemetry**

* Metrics(metric_id, name, value, unit, labels, ts)
* Alerts(alert_id, metric, threshold, window, severity, status, ts)
* SLOs(slo_id, name, target, window, achieved, last_breach)

## 4. Table sketches & constraints (Postgres)

### 4.1 Runs

```sql
CREATE TABLE runs (
  run_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  repo_id UUID NOT NULL REFERENCES repos(repo_id),
  plan_id UUID REFERENCES plans(plan_id),
  commit_sha TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  determinism_mode TEXT CHECK (determinism_mode IN ('D0','D1','D2')),
  manifest_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  status TEXT CHECK (status IN ('queued','running','completed','failed','cancelled','partial')),
  UNIQUE (tenant_id, run_id)
);
CREATE INDEX idx_runs_repo_commit ON runs(repo_id, commit_sha);
```

### 4.2 EvaluationRecords

```sql
CREATE TABLE evaluation_records (
  eval_id UUID PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  artefact_id UUID NOT NULL,
  tool TEXT NOT NULL,
  tool_version TEXT NOT NULL,
  prompt_pack TEXT,
  score NUMERIC(5,3),
  status TEXT CHECK (status IN ('pass','warn','fail')),
  equivalence_method TEXT,
  equivalence_score NUMERIC(5,3),
  manifest_hash TEXT NOT NULL,
  seed BIGINT,
  temperature NUMERIC(3,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_eval_run_artifact ON evaluation_records(run_id, artefact_id);
```

### 4.3 DriftItems & Waivers

```sql
CREATE TABLE drift_items (
  drift_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  repo_id UUID NOT NULL,
  commit_sha TEXT NOT NULL,
  kind TEXT NOT NULL,
  severity TEXT CHECK (severity IN ('info','warn','error','block')),
  status TEXT CHECK (status IN ('new','acknowledged','in-progress','waived','resolved','rejected')),
  plan_context JSONB,
  code_context JSONB,
  evidence_uri TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_drift_repo_commit ON drift_items(repo_id, commit_sha);

CREATE TABLE waivers (
  waiver_id UUID PRIMARY KEY,
  drift_id UUID NOT NULL REFERENCES drift_items(drift_id) ON DELETE CASCADE,
  approver UUID NOT NULL REFERENCES users(user_id),
  reason TEXT,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 4.4 Provenance

```sql
CREATE TABLE provenance (
  prov_id UUID PRIMARY KEY,
  subject_type TEXT NOT NULL,
  subject_id UUID NOT NULL,
  signer TEXT NOT NULL,
  signature TEXT NOT NULL,
  manifest_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(subject_type, subject_id)
);
```

### 4.5 API tokens

```sql
CREATE TABLE api_tokens (
  token_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
  hashed_token TEXT NOT NULL,
  scopes TEXT[] NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  last_used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by UUID REFERENCES users(user_id),
  rotated_from UUID REFERENCES api_tokens(token_id)
);
CREATE INDEX idx_tokens_tenant_user ON api_tokens(tenant_id, user_id);
CREATE INDEX idx_tokens_expires ON api_tokens(expires_at);
```

### 4.6 Service Level Objectives / Agreements

```sql
CREATE TABLE slos (
  slo_id UUID PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
  name TEXT NOT NULL UNIQUE,
  metric TEXT NOT NULL,
  target_pct NUMERIC(5,2) NOT NULL,
  window_days INT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sla_commitments (
  sla_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
  slo_id UUID NOT NULL REFERENCES slos(slo_id) ON DELETE CASCADE,
  policy_id UUID REFERENCES policies(policy_id) ON DELETE SET NULL,
  breach_action TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 4.7 Referential integrity & indexes

To meet the “strong referential integrity” principle, apply the following constraints (table names match §4.1–4.6 and the ERD entities):

```sql
ALTER TABLE repos
  ADD CONSTRAINT repos_project_fk
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;

ALTER TABLE users
  ADD CONSTRAINT users_tenant_fk
  FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE;

ALTER TABLE runs
  ADD CONSTRAINT runs_repo_fk
  FOREIGN KEY (repo_id) REFERENCES repos(repo_id) ON DELETE RESTRICT,
  ADD CONSTRAINT runs_plan_fk
  FOREIGN KEY (plan_id) REFERENCES plans(plan_id) ON DELETE SET NULL;

ALTER TABLE tasks
  ADD CONSTRAINT tasks_run_fk
  FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE;

ALTER TABLE artifacts
  ADD CONSTRAINT artifacts_run_fk
  FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
  ADD CONSTRAINT artifacts_task_fk
  FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE SET NULL;

ALTER TABLE artefacts
  ADD CONSTRAINT artefacts_repo_fk
  FOREIGN KEY (repo_id) REFERENCES repos(repo_id) ON DELETE CASCADE;

ALTER TABLE edges_imports
  ADD CONSTRAINT edges_imports_src_fk
  FOREIGN KEY (src_id) REFERENCES artefacts(artefact_id) ON DELETE CASCADE,
  ADD CONSTRAINT edges_imports_dst_fk
  FOREIGN KEY (dst_id) REFERENCES artefacts(artefact_id) ON DELETE CASCADE;

ALTER TABLE edges_contains
  ADD CONSTRAINT edges_contains_parent_fk
  FOREIGN KEY (parent_id) REFERENCES artefacts(artefact_id) ON DELETE CASCADE,
  ADD CONSTRAINT edges_contains_child_fk
  FOREIGN KEY (child_id) REFERENCES artefacts(artefact_id) ON DELETE CASCADE;

ALTER TABLE boundaries
  ADD CONSTRAINT boundaries_project_fk
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;

ALTER TABLE maps_to_boundary
  ADD CONSTRAINT maps_to_boundary_art_fk
  FOREIGN KEY (artefact_id) REFERENCES artefacts(artefact_id) ON DELETE CASCADE,
  ADD CONSTRAINT maps_to_boundary_boundary_fk
  FOREIGN KEY (boundary_id) REFERENCES boundaries(boundary_id) ON DELETE CASCADE;

ALTER TABLE evaluation_records
  ADD CONSTRAINT eval_run_fk
  FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
  ADD CONSTRAINT eval_artefact_fk
  FOREIGN KEY (artefact_id) REFERENCES artefacts(artefact_id) ON DELETE SET NULL;

ALTER TABLE drift_items
  ADD CONSTRAINT drift_repo_fk
  FOREIGN KEY (repo_id) REFERENCES repos(repo_id) ON DELETE CASCADE;

ALTER TABLE waivers
  ADD CONSTRAINT waivers_drift_fk
  FOREIGN KEY (drift_id) REFERENCES drift_items(drift_id) ON DELETE CASCADE,
  ADD CONSTRAINT waivers_approver_fk
  FOREIGN KEY (approver) REFERENCES users(user_id) ON DELETE RESTRICT;

ALTER TABLE designworkitems
  ADD CONSTRAINT dwi_plan_fk
  FOREIGN KEY (plan_id) REFERENCES plans(plan_id) ON DELETE CASCADE;

ALTER TABLE refinementdeltas
  ADD CONSTRAINT delta_dwi_fk
  FOREIGN KEY (dwi_id) REFERENCES designworkitems(dwi_id) ON DELETE CASCADE;

ALTER TABLE requirements
  ADD CONSTRAINT req_project_fk
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;

ALTER TABLE policies
  ADD CONSTRAINT policies_tenant_fk
  FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE;

ALTER TABLE budgets
  ADD CONSTRAINT budgets_tenant_fk
  FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE;

ALTER TABLE api_tokens
  ADD CONSTRAINT tokens_tenant_fk
  FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
  ADD CONSTRAINT tokens_user_fk
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
  ADD CONSTRAINT tokens_rotated_fk
  FOREIGN KEY (rotated_from) REFERENCES api_tokens(token_id) ON DELETE SET NULL,
  ADD CONSTRAINT tokens_creator_fk
  FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL;

ALTER TABLE slos
  ADD CONSTRAINT slos_tenant_fk
  FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE;

ALTER TABLE sla_commitments
  ADD CONSTRAINT sla_tenant_fk
  FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
  ADD CONSTRAINT sla_slo_fk
  FOREIGN KEY (slo_id) REFERENCES slos(slo_id) ON DELETE CASCADE,
  ADD CONSTRAINT sla_policy_fk
  FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE SET NULL;
```

Recommended supporting indexes for the hottest joins/lookups:

```sql
CREATE INDEX idx_tasks_run ON tasks(run_id);
CREATE INDEX idx_artifacts_run_task ON artifacts(run_id, task_id);
CREATE INDEX idx_eval_run_art ON evaluation_records(run_id, artefact_id);
CREATE INDEX idx_maps_boundary ON maps_to_boundary(boundary_id, artefact_id);
CREATE INDEX idx_edges_imports_dst ON edges_imports(dst_id);
CREATE INDEX idx_sla_tenant ON sla_commitments(tenant_id);
CREATE INDEX idx_slo_metric ON slos(metric);
```

## 5. JSON Schemas (abridged)

### 5.1 EvaluationRecord payload (object store)

```json
{
  "$id": "https://eidolon/schemas/evaluationrecord.json",
  "type": "object",
  "required": ["artefact","sha","metrics","checks","reviews","manifest_hash","tool","tool_version"],
  "properties": {
    "artefact": {"type":"string"},
    "sha": {"type":"string"},
    "metrics": {"type":"object"},
    "checks": {"type":"array","items":{"type":"object"}},
    "reviews": {"type":"array","items":{"type":"object"}},
    "manifest_hash": {"type":"string"},
    "tool": {"type":"string"},
    "tool_version": {"type":"string"},
    "prompt_pack": {"type":"string"}
  }
}
```

### 5.2 RequirementRecord (from HLD)

```json
{
  "$id": "https://eidolon/schemas/requirement.json",
  "type": "object",
  "required": ["id","title","status"],
  "properties": {
    "id": {"type":"string"},
    "title": {"type":"string"},
    "description": {"type":"string"},
    "priority": {"type":"string","enum":["low","medium","high"]},
    "status": {"type":"string","enum":["Draft","Proposed","Accepted","Rejected"]},
    "links": {"type":"object"}
  }
}
```

### 5.3 ProvenanceEnvelope

```json
{
  "$id": "https://eidolon/schemas/provenance.json",
  "type": "object",
  "required": ["subject","digests","signer","signature","timestamp"],
  "properties": {
    "subject": {"type":"string"},
    "digests": {"type":"object"},
    "signer": {"type":"string"},
    "signature": {"type":"string"},
    "timestamp": {"type":"string","format":"date-time"}
  }
}
```

## 6. Indexing & performance

* Composite indexes for hot paths: `(tenant_id, repo_id, commit_sha)`, `(run_id, task_id)`, `(artefact_id, created_at)`.
* Partial indexes for open DriftItems and active DWIs.
* Materialised views for **latest** snapshots (e.g., mv_latest_artefact, mv_boundary_members).

## 7. Retention & TTLs (align with SEC‑01)

* **EvaluationRecords**: 180 days (INTERNAL/CONFIDENTIAL class); archive older payloads; keep metadata 365 days.
* **DriftItems**: retain resolved for 365 days; waivers until 2 years after expiry.
* **Runs/Tasks**: metadata 365 days; logs 30/90 days (hot/archive).
* **Provenance**: immutable; 7 years default for regulated tenants.
* **Requirements/Plans/ADRs**: indefinite; versioned.

Retention executed via scheduled jobs; cryptographic erasure for Tenant deletes.

## 8. Migrations & versioning

* Use `schemaverse` (semver) per entity; migrations as idempotent SQL scripts with checks.
* Dual‑write period for major changes; backfill jobs; compatibility views.
* Automated migration tests: upgrade + rollback on synthetic dataset.

## 9. Data quality & validation

* DB constraints + JSON Schema validation on blob ingestion.
* Periodic integrity checks (FK orphans, duplicate artefacts, bad digests).
* Reconciliation jobs: compare CodeGraph imports vs stored edges; compare Plan selectors to boundary mappings.

## 10. Access & tenancy (RLS)

* `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`
* Policies:

```sql
CREATE POLICY tenant_isolation ON runs
USING (tenant_id = current_setting('eidolon.tenant_id')::uuid);
```

* Set `eidolon.tenant_id` per connection via API Gateway.

## 11. Governance & audit

* Schema changes require ADR; provenance recorded for migration scripts.
* Data exports logged with subject, time, and scope.

## 12. Acceptance criteria

* Unified ERD and schemas published; all services compile against generated types.
* RLS enforced on all tables; tests show cross‑tenant access is impossible.
* Retention jobs remove/archival per class with audit logs.
* Migration test suite passes (upgrade + rollback); integrity checks clean on 100M‑row synthetic dataset.
* Query p95 targets met on hot paths after indexing/materialised views.

## 13. Open questions

* Do we promote multi‑region read replicas for read‑heavy tenants?
* Standardise JSONB vs typed columns for select flexible fields (trade‑off doc)?
* How to expose per‑tenant data export self‑service safely (signed bundle)?
