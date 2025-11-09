---
id: SEC-01
version: 0.1
owner: Security Lead
status: draft
summary: Security posture covering classification, LLM usage, redaction, residency, identity, provenance, and incident response for Eidolon.
tags:
  - security
  - governance
  - policy
last_updated: 2025-11-10
---

# Eidolon – Security & Data Handling Profile (SEC‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Security Lead

## 1. Purpose

Define Eidolon’s security posture and data‑handling rules suitable for commercial and government use. Cover data classification, LLM usage boundaries, redaction, residency, identity/authorisation, auditability, supply chain, and acceptance criteria. Aligns with the four role views and integrates with CG‑01, RF‑01, DR‑01, and ORCH‑01.

## 2. Security objectives

* Protect confidentiality and integrity of source code and artefacts.
* Ensure traceability (who did what, when, with what tools).
* Enforce least privilege and Tenant isolation.
* Provide safe LLM usage with redaction and egress controls.
* Meet baseline controls for ISO 27001 / SOC 2 Type II; enable mapping for ASD Essential Eight.

## 3. Data classification

Classes: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `SENSITIVE` (default for source code).

### 3.1 Classification matrix (examples)

* Source code (repos): **SENSITIVE**
* Plan/ADR/Requirements: **INTERNAL**
* Evaluation outputs (findings, patches): **CONFIDENTIAL** (may include sensitive snippets)
* Telemetry/metrics: **INTERNAL**
* Secrets/tokens: **SENSITIVE** (managed via external Secret Manager; see §8)
* Marketing/front‑of‑house docs: **PUBLIC**

### 3.2 Handling rules

* SENSITIVE data never leaves the Tenant boundary without explicit allow policy.
* Down‑classing requires Architect approval + ADR.
* Object Store buckets per class with distinct KMS keys and retention.

## 4. Identity & access (OIDC + RBAC)

* OIDC (OIDC/OAuth2) with short‑lived access tokens; refresh via PKCE.
* Roles: Viewer, Operator, Coder, Architect, Admin.
* Scopes per API group; fine‑grained resource checks (repo, project, tenant).
* Just‑in‑time (JIT) elevation for approvals; all elevations audited.

## 5. Tenant isolation

* Mandatory `tenant_id` on all records; Postgres RLS policies enforced.
* Secrets per Tenant via external Secret Manager; never shared service accounts.
* Network policy: K8s namespaces per Tenant with NetworkPolicies; optional VPC peering per Tenant.

## 6. LLM usage policy

### 6.1 Modes

* **Disabled**: no LLM calls allowed.
* **Strict**: only local/self‑hosted endpoints; no external egress; prompts and completions logged internally.
* **Balanced**: approved managed endpoints; prompts redacted; egress to allow‑listed domains. **Product view exception**: tenants may enable a *sanitised Product LLM bridge* that automatically routes Product Owner interactions through Balanced mode with forced redaction/audit while leaving other workflows Disabled/Strict.

### 6.2 Redaction & prompt hygiene

* Inline secret detection (entropy + pattern + ML) pre‑LLM; replace with placeholders.
* Maximum prompt size caps; disallow raw large file bodies.
* Prompt provenance: store prompt hash, tool versions; optional full prompt in SENSITIVE object store.

### 6.3 Allow‑list & denial

* Domain allow‑list per Tenant; egress default deny.
* Model card registry with risk labels (PII handling, training retention, region).
* **Product LLM bridge**: Balanced mode for the Product view requires dedicated allow‑list entries plus automated redaction logs stored under the Product Owner’s tenant. Disablement is a single switch in the Architecture view.

## 7. Data flows (DFD overview)

* **Ingress**: Git → RepoScanner (Workers) → Metadata DB + Object Store.
* **Processing**: Evaluator/Synthesiser containers access artefacts via presigned URLs; no direct DB writes.
* **Egress**: API Gateway mediates outbound HTTP; egress controller enforces allow‑list.
* **Console**: Vue Web via API/WebSocket; read‑only signed downloads.

## 8. Secrets management

* Stored in external Secret Manager (e.g., HashiCorp Vault, AWS Secrets Manager, Azure Key Vault).
* Retrieval just‑in‑time at task start; mounted as env/file; rotated on a schedule.
* Access logs include Run/Task IDs; secret values never written to logs/artefacts.

## 9. Cryptography & keys

* TLS 1.3 in transit; mTLS optional for intra‑cluster service mesh.
* At rest: KMS‑managed per‑class encryption keys; envelope encryption for object store items.
* Signing: cosign for container and artefact signing; verification on read path.

## 10. Supply chain security

* SBOM generation for every image; vulnerability scans on build and schedule.
* Dependency allow‑list; licence scanner blocks non‑compliant licences.
* Base images pinned by digest; rebuild cadence ≥ monthly or on high CVEs.

## 11. Logging, audit & provenance

* Structured logs with correlation IDs; retention per class.
* Immutable audit log (append‑only) for privileged actions: approvals, waivers, role elevations, runtime policy changes.
* ProvenanceEnvelope stamped on artefacts with signer, digests, timestamps.

## 12. Policy engine & enforcement

* Rulepack governs: layering, boundaries, security sinks, LLM egress, data residency.
* Enforcement modes: observe | warn | block.
* Waivers are time‑boxed with approver and reason; default expiry 7 days.

## 13. Data residency & locality

* Region pinning for Object Store and compute.
* Per‑Tenant residency policy (e.g., “AU‑only”); scheduler honours node labels/affinity.
* Cross‑region replication optional with customer approval; keys never leave region unless specified.

## 14. Retention & deletion

* Retention classes:

  * SENSITIVE: 90 days hot, 365 days archive
  * CONFIDENTIAL: 180 days
  * INTERNAL: 365 days
  * PUBLIC: retained as long as business needs; no restricted storage requirements
* Cryptographic erasure on Tenant delete; hard‑delete vs soft‑delete policies defined.

## 15. Network & runtime hardening

* Default egress: deny; task network profiles selectable via TaskSpec policy.
* Containers run rootless, read‑only FS, drop CAP_*; seccomp/apparmor profiles.
* Sandboxing: per‑task seccomp; optional gVisor/Kata Containers for high‑risk evaluators.

## 16. Incident response

* Playbooks for secret leakage, data exfil alerts, compromised worker, CVE emergency patches.
* “Big red switch”: immediate LLM disablement and egress lockdown via Control Plane.
* Forensics mode: snapshot logs and artefacts to a segregated evidence bucket.

## 17. Threat model summary (STRIDE)

* **Spoofing**: OIDC + short‑lived tokens; mTLS intra‑cluster optional.
* **Tampering**: signing; write‑once object store buckets for provenance.
* **Repudiation**: append‑only audit logs + time‑sync; ADR requirements for risky changes.
* **Information disclosure**: classification controls, egress deny, redaction.
* **DoS**: per‑Tenant quotas; concurrency gates; rate limiting on API.
* **Elevation of privilege**: RBAC, path‑level permissions for agents, code review on patches.

## 18. Role‑specific guardrails in UI

* Operator: cannot view code content by default; sees telemetry only.
* Coder: write access limited to allowed paths; large diffs require Architect sign‑off.
* Architect: can accept drifts via ADR; cannot change budgets or LLM modes without Admin.
* Product Owner: read‑only to code artefacts; can submit requirements only.

## 19. Compliance mapping (seed)

* ISO 27001: A.8 (Asset management), A.9 (Access control), A.12 (Ops security), A.14 (System acquisition, development), A.16 (Incident management).
* SOC 2: CC1.2, CC6.x (access), CC7.x (change/monitor), CC8.x (incident), A1.2 (logical access), A1.3 (system operations).
* ASD Essential Eight: app control (agents), patching cadence, macro controls (egress), MFA (IdP).

## 20. Metrics & controls

* Secret access anomalies, LLM egress attempts blocked, redaction hit rates, drift waiver counts, time‑to‑revoke.
* Dashboards in Architecture and Operator views show policy posture and exceptions.

## 21. Acceptance criteria (from Master List SEC‑01)

* Classification matrix and enforcement implemented across Object Store and API.
* LLM modes (disabled/strict/balanced) enforced with egress allow‑lists and redaction logs.
* Secrets are JIT fetched and never persist to artefacts; access is fully auditable.
* Provenance signing/verification required on artefact read path.
* Residency policies honoured in scheduling and storage; tests validate region pinning.

## 22. Open questions

* Default LLM mode per Tenant (recommend: Disabled by default).
* Minimum reviewer count for security‑affecting DWIs.
* Which sandboxing technology (gVisor vs Kata) as default for high‑risk tasks?
