# Eidolon

This repo contains the Eidolon platform code and the design library under `docs/design/`. The design tree is organised by audience and lifecycle so contributors can find specs quickly and apply consistent review policies.

## Design structure

- `docs/design/00-foundation/` – system HLD, CodeGraph, data model, and refiner workflow basics.
- `docs/design/10-runtime/` – runtime execution topics: orchestration, caching, determinism, drift, integrations.
- `docs/design/20-governance/` – security, supply chain, agent guardrails, observability, and UX resilience.
- `docs/design/30-role-guides/` – (placeholder) role-specific playbooks for Operator/Coder/Architect/Product Owner.

Each subfolder carries its own `README.md` plus the specs that belong to that domain. See `docs/design/README.md` for the ASCII map.

See `docs/README.md` for documentation standards (including mandatory frontmatter for every doc).

## Tooling

- `uv run eidolon-rulepack init|test|publish|eval` – author, validate, publish, and execute Rulepack DSL bundles against CodeGraph runs; see `docs/design/rapid/RULEPACK_RAPID.md`.
- `uv run eidolon-rulepack-drift --rulepack <yaml> (--run-id <id>|--repo-root <path>) [--record]` – run the drift evaluation job that loads the shared Rulepack, queries Postgres for the requested scan run, optionally records into `drift_results`, and emits a JSON report (or human summary with `--human`).
- `uv run eidolon-rulepack-gatecheck --rulepack <yaml> (--run-id <id>|--repo-root <path>) [--changed-path ... --changed-boundary ... --record]` – execute the GateCheck flow for plan deltas by filtering matches to the touched paths/boundaries, optionally persisting into `gatecheck_results`, and surfacing pass/warn/fail outcomes per RF-01.

Published packs live under `rulepacks/` (e.g., `rulepacks/layering-core`, `rulepacks/security-call-ban`).
