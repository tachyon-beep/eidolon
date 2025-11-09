# Eidolon – Refiner Workflow v1 (RF‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Architecture Lead

## 1. Purpose

Make the Refiner loop explicit: states, transitions, data model, APIs, and exit criteria for “implementable” design. Supports human‑in‑the‑loop discussions with subsystem/system agents and records decisions as ADRs and plan.yaml deltas.

## 2. Scope

* Applies in the **Architecture** view primarily; produces work for **Coder** and **Operator** views.
* Covers: plan branching, parallel edits, conflict resolution, acceptance gates, and reconciliation with CodeGraph.

## 3. Artefacts

* **Plan**: `plan.yaml` versioned document (semver + content hash).
* **DesignWorkItem (DWI)**: unit of refinement for a subsystem/component/interface.
* **DesignSession**: conversational context (Architect ↔ Agents) producing deltas.
* **RefinementDelta**: proposed changes to Plan boundaries, components, interfaces, risks.
* **GateCheck**: machine results for compliance/security/interop.
* **ADR**: decision records linked to deltas and gates.

## 4. State machine

```
[DWI:New]
  -> author starts session -> [In-Progress]
[In-Progress]
  -> auto gate checks pass -> [Ready-For-Review]
[In-Progress]
  -> author pauses -> [Paused]
[Ready-For-Review]
  -> reviewer requests changes -> [Changes-Requested]
[Ready-For-Review]
  -> reviewer approves -> [Approved]
[Changes-Requested]
  -> author updates -> [In-Progress]
[Approved]
  -> apply delta + record ADR -> [Merged]
[Merged]
  -> post-merge conformance + drift reconcile -> [Complete]
[Any]
  -> abandon -> [Abandoned]
```

## 5. Exit criteria (Implementable Definition)

A DWI is **Implementable** when all are true:

1. **Boundaries**: component has a subsystem boundary and layer defined.
2. **Contracts**: interfaces specified (OpenAPI/IDL stubs with at least 1 endpoint/method and error model).
3. **Policies**: security posture declared (authn/authz, data sensitivity, residency) and passes GateCheck.
4. **Dependencies**: dependencies enumerated and policy‑compliant (no forbidden imports per rulepack).
5. **Testing**: test strategy (“Given/When/Then” examples or contract tests) captured.
6. **Traceability**: links to RequirementRecords (if any) and to ADR(s).
7. **Conformance**: simulated conformance query against CodeGraph passes or is waived via ADR.

## 6. Parallel edits and conflict resolution

* Branching model: each DWI uses **plan branches** (lightweight overlay over base plan). Multiple DWIs may edit different parts concurrently.
* Conflict detection: JSON Patch merge with path‑level locks; conflicts flagged when two DWIs edit the same path.
* Resolution: 3‑way merge tool in Architecture view with semantic hints (boundary/selector diffs, interface diffs). All resolutions emit an ADR entry.

## 7. Gate checks (automated)

* **HLD Compliance**: layering rules, boundary walls, naming conventions.
* **Security**: data classification alignment, dependency allowlist, secret sink usage checks.
* **Interoperability**: interface stability, versioning policy, compatibility matrix.
* **Integration Complexity**: fan‑in/fan‑out degree, critical path length.
* **Risk**: risk register update requirement if thresholds exceeded.
  Each GateCheck yields status: pass | warn | fail, plus evidence links.

## 8. Data model (selected)

### 8.1 DesignWorkItem

```
{
  id, plan_version, scope: {subsystem, components[]},
  owner, reviewers[],
  state: "New|In-Progress|Ready-For-Review|Changes-Requested|Approved|Merged|Complete|Abandoned",
  design_session_id,
  delta_id,
  created_at, updated_at
}
```

### 8.2 RefinementDelta (JSON Patch over plan)

```
{
  id, base_plan_sha, patch: [ {op, path, value}... ],
  impact: { imports_changed: int, boundaries_touched: int },
  links: { requirements: [...], related_adrs: [...] }
}
```

### 8.3 GateCheck

```
{ id, dwi_id, type: "hld|security|interop|risk|complexity",
  status: "pass|warn|fail", evidence: [uris...], rulepack_id,
  created_at }
```

## 9. APIs

```http
POST /refine/dwis                  # create DWI
GET  /refine/dwis?state=...        # list DWIs
POST /refine/dwis/{id}/start       # begin DesignSession
POST /refine/dwis/{id}/pause       # pause
POST /refine/dwis/{id}/submit      # move to Ready-For-Review
POST /refine/dwis/{id}/decision    # approve|request-changes|abandon
POST /refine/dwis/{id}/merge       # apply delta, create ADR
GET  /refine/dwis/{id}/gates       # gate results
POST /refine/deltas                # propose delta
POST /refine/gates/run             # run gate checks now
```

## 10. Interaction patterns

* **Architect ↔ Agents**: DesignSession keeps full transcript and tool invocations as provenance; only deltas merged affect plan.
* **Coder handoff**: When DWI is Implementable and Merged, tasks for implementation/evaluation are emitted to the Operator queue.
* **Product Owner linkage**: Requirements can seed DWIs; acceptance links maintained bi‑directionally.

## 11. Reconciliation with CodeGraph

* Pre‑merge: simulate conformance against latest CodeGraph (dry‑run queries).
* Post‑merge: a **Reconcile** job updates boundaries and selectors; any code that violates new rules is raised as **Drift** items for Coder triage.

## 12. Audit and provenance

* Every transition recorded with actor, time, and hash of delta.
* ADR required for: boundary changes, security posture changes, breaking interface changes.

## 13. Acceptance criteria

* State machine implemented with server‑side enforcement.
* Implementable checklist enforced by API; cannot merge without passing gates or ADR waivers.
* Parallel DWIs on disjoint plan paths merge without conflict; conflicting paths produce a deterministic resolution flow.
* Conformance dry‑run works against CodeGraph; violations highlighted prior to merge.

## 14. Open questions

* Do we require two reviewers for security impacting DWIs by default?
* Default timeouts for DWIs in review/paused states?
* Template libraries for common interface contracts?
