# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Eidolon is a platform for architecture conformance, drift detection, and code governance. It consists of three core subsystems:

1. **CodeGraph** – AST scanning and metrics collection for Python codebases
2. **Rulepack** – A DSL for expressing architecture policies (layering, security, boundaries) that compile to SQL queries
3. **Orchestrator** – Residency-aware task scheduling with tenant policy enforcement

The design library lives under `docs/design/` and is organized by audience and lifecycle.

## Development Commands

### Environment Setup
This project uses `uv` as the package manager (Python 3.13+):
```bash
uv sync                    # Install dependencies
uv run pytest              # Run all tests
uv run pytest tests/rulepack/test_compiler.py  # Run a single test file
uv run pytest tests/rulepack/test_compiler.py::test_layering_selector  # Run a single test
```

### CodeGraph Operations
```bash
# Scan a repository to collect metrics
uv run eidolon-codegraph-scan --repo /path/to/repo --output scan.json

# Ingest scan results into Postgres
uv run eidolon-codegraph-ingest --scan scan.json --dsn "postgresql://..."

# Query benchmarks against CodeGraph tables
uv run eidolon-codegraph-query-bench --dsn "postgresql://..." --run-id 123
```

### Rulepack Authoring & Testing
```bash
# Create a new rulepack from template
uv run eidolon-rulepack init --output my-pack/rulepack.yaml

# Validate and compile a rulepack
uv run eidolon-rulepack test my-pack/rulepack.yaml --show-sql

# Publish compiled rulepack artifact
uv run eidolon-rulepack publish my-pack/rulepack.yaml --output my-pack/compiled/v1.json

# Evaluate a rulepack against a scan run
uv run eidolon-rulepack eval my-pack/rulepack.yaml --run-id 123 --dsn "postgresql://..."
```

### Drift Detection & GateCheck
```bash
# Run drift detection job against a scan run or repo
uv run eidolon-rulepack-drift --rulepack rulepacks/layering-core/rulepack.yaml --run-id 123 --record

# Run GateCheck for changed files/boundaries (used in CI)
uv run eidolon-rulepack-gatecheck --rulepack rulepacks/security-call-ban/rulepack.yaml \
  --run-id 123 \
  --changed-path src/app/auth.py \
  --changed-boundary app \
  --record

# End-to-end pipeline: scan → ingest → drift/gate
uv run eidolon-rulepack-pipeline --repo /path/to/repo --rulepack my-pack/rulepack.yaml
```

### Orchestrator Prototype
```bash
# Run residency-aware orchestrator locally
uv run eidolon-orchestrator-run \
  --job job.yaml \
  --tenant-policy tenant.yaml \
  --pools pools.yaml \
  --repo /path/to/repo \
  --run-id 123
```

## Architecture Overview

### CodeGraph (src/eidolon/codegraph/)
- **scanner.py** – Traverses Python files, parses AST, collects metrics (SLOC, imports, calls, functions)
- **ingest.py** – Writes scan results to Postgres (scan_runs, file_metrics, file_imports, function_calls, boundary_stats tables)
- **queries.py** – Benchmark queries for testing query performance
- **compare.py** – Diffs two scan runs to identify code changes

Key data model tables (Postgres):
- `scan_runs` – Metadata for each scan (repo, commit, timestamp)
- `file_metrics` – Per-file metrics (path, package, SLOC, class_count, function_count)
- `file_imports` – Import graph edges
- `function_calls` – Call graph edges
- `boundary_stats` – Aggregated metrics per boundary (component/subsystem)

### Rulepack (src/eidolon/rulepack/)
- **loader.py** – Loads and validates rulepack YAML files
- **compiler.py** – Translates DSL selectors into SQL queries against CodeGraph tables
- **runtime.py** – Executes compiled rules against Postgres and returns match results
- **persistence.py** – Records rule evaluation results (rulepack_runs, rule_matches tables)
- **drift_job.py** – Drift detection pipeline (DR-01 spec)
- **gatecheck_job.py** – GateCheck pipeline for CI/CD (RF-01 spec)

Rulepack DSL structure:
```yaml
metadata:
  id: RP-EXAMPLE
  version: 1.0.0
  description: Example policy pack

rules:
  - id: RULE-001
    description: Enforce layering boundaries
    selector:
      type: import
      source_boundary: ui
      target_boundary: data
    predicate:
      operator: forbidden
    severity: error
    enforcement: block
```

### Orchestrator (src/eidolon/orchestrator/)
- **scheduler.py** – Assigns tasks to worker pools based on residency policies
- **models.py** – JobSpec, TaskSpec, ResidencyPolicy data classes
- **residency.py** – Residency policy evaluation (required_regions, fallback modes)
- **telemetry.py** – Telemetry envelope generation for traceability
- **adapters/** – Pluggable backends (local, Temporal) for task execution

Residency fallback modes:
- `block` – Fail if no capacity in required regions
- `queue` – Wait for capacity in required regions
- `degrade` – Fall back to preferred regions if required unavailable

### Design Library (docs/design/)
- `00-foundation/` – Core architecture (HLD, CodeGraph design, data model, refiner workflow)
- `10-runtime/` – Execution topics (orchestration, caching, determinism, drift detection, integrations)
- `20-governance/` – Security, guardrails, supply chain, observability, UX resilience
- `30-role-guides/` – Role-specific playbooks (Operator/Coder/Architect/Product Owner)
- `rapid/` – Rapid design spikes for high-risk components

All design docs require AI-friendly frontmatter (see `docs/README.md`):
```yaml
---
id: SPEC-ID
version: semver
owner: team/person
status: draft|review|approved|deprecated
summary: 1-2 sentence overview
tags: [keywords]
last_updated: YYYY-MM-DD
---
```

## Database Setup

Eidolon assumes Postgres with CodeGraph schema. The default DSN is `postgresql://localhost/eidolon_codegraph`. Override with `--dsn` flag or `EIDOLON_DSN` environment variable.

Key tables:
- `scan_runs` – Tracks each scan execution
- `file_metrics` – Per-file AST metrics and hashes
- `file_imports` – Import graph (source_file → imported_module)
- `function_calls` – Call graph (caller_function → callee_name)
- `boundary_stats` – Aggregated stats per boundary (SLOC, complexity, import fan-in/out)
- `rulepack_runs` – Rulepack evaluation metadata
- `rule_matches` – Individual rule violations with evidence
- `drift_results` – Drift detection findings (DR-01)
- `gatecheck_results` – GateCheck outcomes per plan delta (RF-01)

## Rulepack Catalog

Published rulepacks live under `rulepacks/`:
- `layering-core` – Enforces subsystem layering boundaries (UI/App/Data tiers) and per-boundary size limits
- `security-call-ban` – Prohibits dangerous runtime evaluation (exec, eval, __import__) and guards boundary sinks

To author a new rulepack:
1. Run `uv run eidolon-rulepack init --output my-pack/rulepack.yaml`
2. Edit the YAML to define rules with selectors, predicates, severity, enforcement
3. Test with `uv run eidolon-rulepack test my-pack/rulepack.yaml --show-sql`
4. Publish with `uv run eidolon-rulepack publish my-pack/rulepack.yaml --output my-pack/compiled/v1.json`

## Key Design Specs

- **RF-01** (Refiner Workflow) – Plan/refine loop, GateChecks, DWI (Design Work Item) lifecycle
- **DR-01** (Drift Detection) – Conformance pipeline, drift classification, reconciliation flows
- **CG-01** (CodeGraph Design) – Scanner architecture, metrics collection, storage schema
- **SEC-01** (Security Policies) – Guardrails, supply chain verification, agent safety
- **DATA-01** (Data Model Hardening) – Retention policies, audit trails, versioning

See `docs/design/README.md` for the full map.

## Testing Guidelines

- Tests live under `tests/` mirroring `src/eidolon/` structure
- Use `pytest.ini` config (pythonpath=src, testpaths=tests)
- Rulepack tests should validate both DSL compilation and SQL correctness
- CodeGraph tests should use synthetic repos (see `eidolon-synthesize-repo`) for reproducible scanning
- Orchestrator tests should mock adapters or use local adapter for determinism

## Git Workflow

- Main branch: `main`
- Recent commits focus on: rulepack implementation, drift detection, orchestrator residency, rapid design docs
- No pre-commit hooks or CI/CD configured yet (manual testing via `uv run pytest`)

## Common Patterns

### Adding a new rule selector type
1. Update `RulepackCompiler` in `src/eidolon/rulepack/compiler.py` to handle new selector type
2. Add SQL generation logic for the new selector (joins against CodeGraph tables)
3. Add test cases in `tests/rulepack/test_compiler.py`
4. Update rulepack schema documentation in `docs/design/rapid/RULEPACK_RAPID.md`

### Adding a new orchestrator adapter
1. Create new adapter in `src/eidolon/orchestrator/adapters/`
2. Implement `submit_task(task: TaskSpec, pool: WorkerPool) -> dict` interface
3. Register in adapter_registry (see `cli.py`)
4. Add tests in `tests/orchestrator/`

### Adding a new drift detection rule kind
1. Update `DriftItem.kind` enum in DR-01 spec
2. Extend `drift_job.py` to classify new drift type
3. Add rulepack rules to detect the new drift category
4. Update `drift_results` schema if new evidence fields needed
