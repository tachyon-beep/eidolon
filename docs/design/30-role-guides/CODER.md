---
id: ROLE-CODER
version: 1.0
owner: Tactical Oversight Guild
status: draft
summary: Coder handbook covering triage, guardrails, and patch approval flows for Eidolon findings.
tags:
  - role-guide
  - coder
  - quality
last_updated: 2025-11-10
---

# Coder Guide (Tactical Oversight)

## Mission

Review, fix, and land correct changes. Keep quality high with fast, safe loops.

## Your home base

* **Coder view**: UnreviewedFindings, PatchQueue, TestStatus, ArtefactInspector, AgentChat, DiffViewer.

## Daily rhythm

1. **Triage**: filter by severity and subsystem; pick top priority items.
2. **Inspect**: open ArtefactInspector; read agent notes; reproduce locally if needed.
3. **Decide**: Approve/Edit/Reject patches; request targeted re-run.
4. **Close the loop**: ensure tests pass; confirm drift items resolved.

## Core actions

* Chat with Function/Class/Module agents (explain, generate tests, propose patch).
* Approve or revise patches; split oversized diffs; run targeted re-checks.
* Raise **DesignWorkItem** when tactical fix reveals strategic design gap.

## Guardrails (AGT-01)

* Path allow-list only (`src/**`, `tests/**`, `docs/**`).
* Size caps (≤80/150/300 LOC by agent scope); blast radius limits.
* Secret/licence checks must pass; new deps require policy approval.

## Playbooks

* **Boundary breach (ui→data)**: accept agent auto-fix (facade), add contract tests, re-run.
* **Non-deterministic critique**: switch to D2 for the artefact; re-evaluate without LLM.
* **Mass rename/move**: open DWI for boundary change; don’t brute-force patches.

## KPIs

* Approval cycle time; Rollback rate (<2%); Findings triaged per day; Cache savings.

## Permissions

* Approve patches; create DWIs; targeted re-runs. No global run control.

## Escalation

* To **Architect** for subsystem impacts; **Operator** for capacity; **Security** for licence/CVE blocks.
