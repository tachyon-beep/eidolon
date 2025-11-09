---
id: SUP-01
version: 0.1
owner: DevEx Lead / Security Lead
status: draft
summary: Supply-chain and licensing controls for dependencies, images, provenance, scanning, and waivers across Eidolon.
tags:
  - governance
  - supply-chain
  - licensing
last_updated: 2025-11-10
---

# Eidolon – Supply Chain & Licensing Policy (SUP‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: DevEx Lead / Security Lead

## 1. Purpose

Define supply‑chain security and licensing controls for Eidolon across build, dependency management, container images, provenance, and runtime verification. Provide concrete policies, automation hooks, and acceptance criteria. Aligns with SEC‑01 (classification/residency), ORCH‑01 (task policy & image digests), DATA‑01 (provenance tables), AGT‑01 (agent autoblocks), CASH‑01 (budgets), and OBS‑01 (telemetry).

## 2. Objectives

* Ensure only approved, verifiable dependencies and images are used.
* Provide tamper‑evident build artefacts with end‑to‑end provenance.
* Enforce licence compliance for government/commercial use.
* Detect and block known vulnerabilities before deployment or merge.

## 3. Policy overview

### 3.1 Dependency sources

* **Allow‑listed registries only** (e.g., PyPI via internal mirror, npm private registry, OS distro repos).
* **Disallow** git+https direct dependencies and VCS pinning without an ADR waiver.
* **Vendoring** permitted only with ADR + provenance (upstream commit, licence).

### 3.2 Version & integrity

* Lockfiles required for all languages (e.g., `requirements.lock`, `poetry.lock`, `package-lock.json`).
* Packages must resolve to immutable versions with checksums (hash‑pinned).
* **Reproducible builds**: same lockfiles + builder image digest → identical artefacts.

### 3.3 Licence policy

* **Allowed**: Apache‑2.0, MIT, BSD‑2/3‑Clause, MPL‑2.0.
* **Restricted (waiver)**: LGPL‑2.1/3.0 (dynamic link only), EPL‑2.0.
* **Prohibited**: GPL‑2.0/3.0 (except tooling not shipped), AGPL‑3.0, SSPL.
* Transitive licences evaluated; conflicts block merges.
* Generated code licence headers preserved; third‑party notices auto‑compiled.

### 3.4 Vulnerability policy

* Blocking on **CVSS ≥ 7.0** (High/Critical) unless waiver with expiry ≤ 30 days.
* **Disallow** known‑malicious packages and typosquats (curated deny‑list).
* New vulnerabilities after release trigger patch SLOs (see §10).

### 3.5 Container images

* Base images pinned by **digest** and **SBOM** available.
* Minimal runtime images (distroless/ubi‑micro) preferred; no compilers in runtime layers.
* Images signed (cosign keyless or KMS); provenance attested (SLSA Level 2+ target).
* **No root** user; read‑only FS; drop capabilities by default.

## 4. Tooling & automation

* **SBOM**: syft/bom (build time) → `CycloneDX` + `SPDX` formats; uploaded to Object Store and attached to provenance.
* **Vuln scanning**: grype/trivy at build + scheduled; results published as EvaluationRecords (`tool='vuln-scan'`).
* **Licence scanning**: scancode/licence‑checker; fail on prohibited; warn on restricted pending waiver.
* **Provenance**: SLSA attestation via `slsa-github-generator` or equivalent; linked to container digest and artefact hashes.
* **Image policy**: admission controller (Kyverno/OPA Gatekeeper) blocks unsigned/unknown‑digest images in K8s.

## 5. Build pipeline (reference)

1. **Source fetch** – verify commit signature (GPG/Sigstore) where available.
2. **Dependency resolve** – lockfiles verified; hashes checked.
3. **Compile/Test** – run unit/integration tests; generate coverage.
4. **SBOM & scans** – produce SBOM, run vuln + licence scans.
5. **Package** – build OCI images with reproducible flags.
6. **Sign & attest** – sign artefacts/images; create provenance.
7. **Publish** – push to registry/bucket; store metadata in DATA‑01 tables.
8. **Policy gate** – block release on policy failures; waivers recorded (time‑boxed).

## 6. Provenance model

* **ProvenanceEnvelope** (DATA‑01) extended with: builder image digest, source repo URL@commit, build tool versions, SBOM hash, scan results summary, signers.
* Read path verification: before execution, Worker downloads provenance and validates signature + digests; mismatches block task start (ORCH‑01 policy violation).

## 7. Runtime verification

* Workers verify:

  * Container image signed and matches digest allow‑list.
  * Executable checksum matches attested value.
  * SBOM present and vulnerability results below threshold.
* Periodic drift audits: compare running images vs registry digests; alert on mismatch.

## 8. Licencing enforcement in agents (AGT‑01 hook)

* Patch proposals adding a dependency must include: package name, version, licence, size, SBOM delta.
* Autoblock on prohibited licences; raise Architect approval on restricted.
* Diff viewer highlights licence changes in `pyproject.toml/requirements.txt` etc.

## 9. Governance & waivers

* Waivers record: reason, scope (package/version/project), risk assessment, compensating controls, expiry (≤ 30 days for CVEs; ≤ 90 days for licences).
* Waivers required ADR link; renewal creates a new ADR.

## 10. SLOs & response

* **High/Critical CVE** in prod images: patch available → deploy within **7 days**; if no patch, mitigation ADR within **3 days**.
* **Licence breach**: block merges immediately; remediation within **2 days**.
* Monthly patch windows for medium/low CVEs.

## 11. Telemetry (OBS‑01)

* Metrics: `sbom_generated_total`, `scan_fail_total`, `cve_block_total`, `licence_block_total`, `unsigned_image_block_total`.
* Alerts: new critical CVE affecting running images; unsigned image admission attempt.

## 12. Interfaces & APIs

```http
GET  /supply/sbom/{artifact_id}            # fetch SBOM (signed)
GET  /supply/scans/{artifact_id}           # vuln/licence scan reports
POST /supply/waivers                       # request waiver
GET  /supply/policy                        # current supply-chain policy doc
```

* Admission controller webhook for K8s: `/supply/admission/verify-image`.

## 13. Acceptance criteria

* All images and artefacts have SBOMs and provenance; verification enforced at runtime.
* Builds fail for prohibited licences or CVSS ≥ 7.0 without active waiver.
* Admission controller blocks unsigned/unknown images.
* Agent dependency changes follow policy with visible UI guardrails.
* Incident SLOs met in staging drills.

## 14. Open questions

* Minimum SLSA level target for GA (Level 3 vs 2)?
* Do we mandate commit signing for all repos or only for release branches?
* Which registries form the allow‑list by default for tenants (AWS ECR, GCR, GHCR)?
