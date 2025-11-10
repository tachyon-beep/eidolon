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
- `uv run eidolon-rulepack-pipeline --repo <path> --rulepack <yaml>` – end-to-end scan ⇒ ingest ⇒ drift/gate pipeline; writes placement + telemetry JSON and records results in Postgres. Pair it with `uv run eidolon-rulepack-status <json>` to gate CI on rule failures.
- `uv run eidolon-rulepack-drift --rulepack <yaml> (--run-id <id>|--repo-root <path>) [--record]` – run the drift evaluation job that loads the shared Rulepack, queries Postgres for the requested scan run, optionally records into `drift_results`, and emits a JSON report (or human summary with `--human`).
- `uv run eidolon-rulepack-gatecheck --rulepack <yaml> (--run-id <id>|--repo-root <path>) [--changed-path ... --changed-boundary ... --record]` – execute the GateCheck flow for plan deltas by filtering matches to the touched paths/boundaries, optionally persisting into `gatecheck_results`, and surfacing pass/warn/fail outcomes per RF-01.
- `uv run eidolon-orchestrator-run --job job.yaml --tenant-policy tenant.yaml --pools pools.yaml --repo <repo> --run-id <id>` – run the residency-aware orchestrator prototype locally; outputs placement decisions + telemetry envelopes and writes execution records to `.orchestrator/placements.jsonl`. Pools can reference `adapter: airflow` to exercise the Airflow adapter stub.
- Set `ORCH_TELEMETRY_OTLP_ENDPOINT=http://localhost:4317` before running the orchestrator to emit OTLP telemetry into the docs/observability stack.
- GitHub Actions workflow `.github/workflows/observability.yml` spins up the OTLP stack under `docs/observability/` and runs the sample telemetry script.
- GitHub Actions workflow `.github/workflows/orchestrator-rulepack.yml` runs the orchestrator + rulepack pipeline (scanner→ingest→drift→gate) on every push/PR to keep DR‑01/RF‑01 in CI.
- `docs/orchestrator/airflow/` contains a docker-compose stack for bringing up a local Airflow environment (admin/admin) to test the adapter.

Published packs live under `rulepacks/` (e.g., `rulepacks/layering-core`, `rulepacks/security-call-ban`).
