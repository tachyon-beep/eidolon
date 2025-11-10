---
id: RAPID-OBS-PIPE
version: 0.1
owner: Observability Lead
status: done
summary: Rapid design to deliver the telemetry pipeline (collector, dashboards, alerts) for orchestrator + rulepack runs.
tags:
  - rapid-design
  - observability
  - telemetry
last_updated: 2025-02-15
---

# Observability Pipeline Rapid

## Problem Statement
Telemetry context is defined but there’s no collector stack or dashboards consuming orchestrator/rulepack signals. Without it, we can’t monitor residency enforcement, drift outcomes, or queue latency.

## Scope
* OpenTelemetry Collector deployment for spans/logs/metrics.
* Prometheus/Loki/Tempo configs with tenant/run labels.
* Dashboards + alerts for residency, queue latency, drift/gate outcomes.

## Plan
1. Define collector configuration and env var contract with adapters.
2. Deploy reference stack (docker-compose or helm chart).
3. Build Grafana dashboards + alert rules.
4. Document onboarding checklist for new services.

## Exit Criteria
* CI smoke test pushes spans/logs/metrics through collector (GH Action `observability.yml`).
* Dashboards show per-tenant residency/drift metrics.
* Alert rules fire on residency fallback/blocking drift.

> **Implementation note (2025-02)**: See `docs/observability/` for the OTLP collector stack (Prometheus/Loki/Tempo/Grafana) and
> `docs/observability/sample_telemetry.py` + `stack_ci.sh` for pushing test signals. Set `ORCH_TELEMETRY_OTLP_ENDPOINT` when running the
> orchestrator to emit real telemetry and inspect the dashboards/alerts provisioned under `docs/observability/grafana`.
