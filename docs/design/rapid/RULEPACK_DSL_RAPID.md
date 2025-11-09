---
id: RAPID-RULEPACK
version: 0.1
owner: Refiner & Conformance Leads
status: draft
summary: Rapid design for the shared Rulepack DSL powering GateChecks and Drift enforcement.
tags:
  - rapid-design
  - rulepack
  - policy
last_updated: 2025-11-10
---

# Rulepack DSL Rapid Design

## Problem statement

Multiple specs rely on a shared “Rulepack” DSL (GateChecks, Drift detection, Guardrails) but no canonical schema/compiler exists. Without it, policy automation will stall.

## Scope & goals

* Define DSL syntax/semantics (selectors, actions, metadata).
* Publish JSON Schema + versioning rules.
* Implement compiler that emits SQL/AST queries for CodeGraph and plan contexts.
* Provide SDK bindings (Python/TypeScript) for authoring/testing packs.

## Key concepts

* **Rule**: `{ id, selector, predicate, severity, enforcement, autofix, scopes }`.
* **Selector**: DSL referencing artefact attributes (path, boundary, import graph) and plan elements.
* **Scopes**: `drift`, `gatecheck`, `guardrail` to control which systems consume a rule.
* **Packages**: versioned bundles (`rulepack.yaml` + compiled artifacts + tests).

## Architecture

1. Author rulepack in YAML → run `rulepack build` to validate schema, compile selectors to SQL fragments, and generate fixtures.
2. Publish pack to object store with signed metadata; record `rulepack_id` in Metadata DB.
3. Drift jobs and GateChecks load the same compiled output via Control Plane.

## Interfaces

* CLI: `rulepack init`, `rulepack test`, `rulepack publish`.
* Control Plane API: `GET /rulepacks/{id}`, `POST /rulepacks/{id}/activate`.
* Compiler output: `rules.json` with SQL templates + variable bindings.

## Prototype plan

1. Define JSON Schema + selector grammar (start with path glob + regex + graph traversals).
2. Implement compiler (Python) that translates selectors to SQL using CTEs referencing CodeGraph tables.
3. Write conformance tests for sample packs (layering, boundary, security sinks, **sandbox/egress** policy rule from SEC scope).
4. Integrate with Refiner GateCheck and Drift detection “hello world” flows.

## Risks

* Selector expressiveness vs. performance—limit features initially (no recursive queries beyond fixed depth).
* Multi-tenant overrides—defer to future version; start with per-tenant pack selection.
* Tooling adoption—provide VS Code snippets + validation to reduce friction.
* Security coverage—ensure SEC-01 sandbox/egress rules are first-class citizens in initial sample packs.

## Exit criteria

* Rulepack schema published with version strategy.
* Compiler passes test suite (at least 5 real rules) and outputs SQL consumed by DR-01.
* Control Plane stores `rulepack_id` per run and surfaces pack metadata in UI.
