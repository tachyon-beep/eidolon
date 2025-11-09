---
id: RAPID-CG-SCALE
version: 0.1
owner: CodeGraph Lead
status: draft
summary: Rapid design to derisk CodeGraph throughput/latency targets and artefact ID strategy on 5 MLOC repos.
tags:
  - rapid-design
  - codegraph
  - performance
last_updated: 2025-11-10
---

# CodeGraph Scale & Performance Rapid Design

## Problem statement

CodeGraph v1 promises ≤300 ms queries on 5 MLOC repos, full scans at ≥250 files/sec, and stable artefact IDs across renames. Those targets underpin Planner, Refiner, Drift, and Conformance workflows but remain unproven.

## Scope & goals

* Validate parsing pipeline throughput on representative Python repos (0.5–5 MLOC).
* Finalise artefact ID scheme (path + commit vs content hash) and boundary selector resolution.
* Measure query latencies for Q1–Q6 (see CG‑01) using realistic Postgres indexes/materialised views.
* Confirm incremental scan behaviour for renames/moves and dynamic imports.

Out of scope: multi-language support, advanced CALLS extraction beyond heuristics, OpenSearch indexing.

## Architecture sketch

1. **Scanner workers** (Rust or Python) emit artefact + edge rows to a queue.
2. **Ingest service** batches rows into Postgres, maintaining MVCC snapshots per commit.
3. **Materialised views** (`mv_latest_artefact`, `mv_imports_latest`, `mv_boundary_members`) refreshed after ingest.
4. **Query service** exposes REST/GraphQL for Planner/Drift with prepared SQL using the views.

Key decisions:

* Artefact ID = stable UUID derived from repo_id + path hash + first commit, with redirect table for renames.
* Boundary resolution compiled from plan selectors once per run; caches pinned by rulepack version.

## Interfaces & data contracts

* Scanner → Ingest: protobuf `ArtefactRecord` / `EdgeRecord` (id, path, sha256, metrics, commit_sha).
* Query API: `GET /graph/artefacts?path=...`, `GET /graph/dependants?id=...`, `GET /graph/violations?rulepack=...`.
* Metrics: `scan_files_per_sec`, `query_latency_ms{query=Qn}`, `mv_refresh_sec`.

## Prototype/validation plan

1. Generate synthetic repo (5 MLOC) + sample real project (e.g., CPython mirror).
2. Run scanner locally (4 vCPU) → record files/sec, memory footprint, disk IO (`read_mb_s`, `write_mb_s`).
3. Load Postgres (size ~50–70 GB) → run Q1–Q6 under *concurrent* load (≥10 parallel queries) and capture p95 latencies.
4. Execute a cross-repo join scenario (e.g., dependency map across shared libraries) to anticipate SCALE-01 needs.
5. Rename/move 1k files → measure incremental scan + boundary mapping accuracy.
6. Document bottlenecks; adjust indexes/materialised views.

## Risks & mitigations

* **IO-bound scans**: switch to Rust parser or multi-process pool; avoid Python GIL bottleneck.
* **Query drift**: adopt `EXPLAIN ANALYZE` and tuned indexes before shipping.
* **Artefact ID churn**: add redirect table + tests ensuring history survives path changes.
* **Memory pressure**: track peak RSS per worker; consider streaming AST summaries to avoid loading full files.

## Exit criteria

* Empirical evidence meeting throughput and query targets on ≥2 repos.
* Artefact ID scheme documented + tested (rename, merge, dynamic import scenarios).
* Dashboard (Grafana) panels showing scan throughput and query latency baselines.

## Current snapshot (2025‑11‑09)

* Synthetic dataset (`110 packages × 100 modules × 10 classes × 20 functions × padding 20`): 11 110 files (~10.6 M SLOC).
* Scanner metrics: 31.7 s runtime, 349 files/sec, avg parse 1.28 ms, p95 1.34 ms, peak RSS 60 MB (see `benchmarks/reports/synthetic_large_scan.json`).
* Records ingested into Postgres (`scan_runs.id=1`) using `eidolon-codegraph-ingest`; `file_metrics` contains 11 110 rows.
* Query benchmark (`eidolon-codegraph-query-bench`) results: Q1/Q2/Q4 multi-row selects in 1–2 ms; aggregate queries in <1 ms on local instance.
* Concurrent query bench (`eidolon-codegraph-query-concurrency --clients 8 --iterations 20`) against run `id=2`: p95 latencies remain below 4 ms for all test queries; see `benchmarks/reports/concurrency_run2.json`.
* Rename/move simulation: `eidolon-synthetic-rename --count 1000` moved 1k modules; follow-up scan ingested as run `id=2`. SHA-based comparison (`eidolon-codegraph-compare`) detected exactly 1 000 renamed artefacts, 10 001 unchanged, zero adds/removals (see `benchmarks/reports/rename_comparison.json`). Demonstrates SHA stability for rename detection prior to introducing formal artefact IDs.
* Real repo baseline: cloned CPython (`benchmarks/cpython`), scanned/injected as run `id=3`. Scan summary: 6 132 `.py` files (~1.4 M SLOC). Serialized queries stay under 2 ms; concurrent bench with 8 clients shows p95 ≤1.6 ms (see `benchmarks/reports/cpython_concurrency.json`).
