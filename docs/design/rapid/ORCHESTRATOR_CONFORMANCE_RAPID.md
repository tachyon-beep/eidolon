---
id: RAPID-ORCH-CONF
version: 0.1
owner: Orchestrator QA Lead
status: draft
summary: Rapid design for an orchestrator/adapters conformance suite covering retries, timeouts, residency, and telemetry.
tags:
  - rapid-design
  - orchestrator
  - quality
last_updated: 2025-02-15
---

# Orchestrator Conformance Rapid

## Problem Statement
Adapters and scheduler need a standard test suite to ensure they honor policies (residency, timeouts, retries) before hitting production. Today we only have unit tests.

## Scope
* Build a conformance harness that drives adapters through scenarios (timeouts, retries, residency fallbacks, telemetry).
* Define pass/fail criteria and reporting format.
* Integrate suite into CI gate for new adapters.

## Exit Criteria
* Local/Temporal adapters pass the suite.
* New adapters must run the suite before merging.
* Report artifacts stored for auditing.
