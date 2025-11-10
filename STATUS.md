## Status Snapshot (Feb 2025)

1. **Rulepack RAPID** – Done. DSL/runtime tooling is live, rulepacks reside in `rulepacks/`, the rulepack pipeline runs in CI (`.github/workflows/orchestrator-rulepack.yml`), and `eidolon-rulepack-status` gates builds.

2. **TaskSpec Residency RAPID** – Done. Control Plane + PolicyEngine assemble TaskSpecs, scheduler/adapters enforce residency + fallbacks, placements recorded to `.orchestrator/placements.jsonl`, and an Airflow adapter stub plus docker-compose playground exist.

3. **Observability RAPID** – Done. `docs/observability/` has the OTLP collector stack (Prometheus/Loki/Tempo/Grafana), sample telemetry script, Makefile (`make stack-test`), and GH Action (`.github/workflows/observability.yml`). Scheduler emits OTLP spans/metrics when `ORCH_TELEMETRY_OTLP_ENDPOINT` is set.

4. **Control Plane** – Prototype supports TaskSpec assembly/persistence, placement logging, CLI helpers, and adapters (Local/Temporal/Airflow). Next step is exposing proper APIs/DB integration.

5. **Telemetry RAPID** – Residency telemetry path is wired (queue latency histogram, `residency_fallback_total` counter) with dashboards/alerts; additional services can hook in via OTLP.

6. **Orchestrator Conformance RAPID** – Not started; conformance suite still queued.

### Key directories/tools
- `uv run eidolon-orchestrator-run …` – run scheduler/adapters (set `ORCH_TELEMETRY_OTLP_ENDPOINT` for telemetry).
- `docs/observability/` – OTLP stack + sample telemetry (`make stack-test`).
- `docs/orchestrator/airflow/` – Airflow docker-compose + sample DAG for `adapter: airflow` pools.
- `eidolon-rulepack-pipeline` / `eidolon-rulepack-status` – rulepack enforcement CLI.
