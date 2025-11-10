# Observability Pipeline (RAPID-OBS-PIPE)

This directory houses the reference observability stack for orchestrator + rulepack telemetry.

## Components

- `otel-collector-config.yaml` – OpenTelemetry Collector to receive spans/logs/metrics via OTLP and forward to Prometheus/Loki/Tempo.
- `docker-compose.yaml` – local stack (Collector + Prometheus + Loki + Tempo + Grafana) for end-to-end smoke tests.
- `grafana/dashboards/` – panels covering queue latency, residency fallback counts, drift outcomes, etc.
- `alerts/` – Prometheus alert rules (e.g., `residency_fallback_total{mode="block"} > 0`).

## Usage

```bash
# Start stack + send sample telemetry
cd docs/observability
make stack-test

# Run orchestrator to emit real telemetry
ORCH_TELEMETRY_OTLP_ENDPOINT=http://localhost:4317 uv run eidolon-orchestrator-run ...

# View dashboards at http://localhost:3000 (Grafana)
```

CI (see `.github/workflows/observability.yml`) runs `stack_ci.sh` which starts the stack and pushes the sample telemetry to guarantee the collector path is healthy. Integrate this stack into your local testing before pushing telemetry changes.
