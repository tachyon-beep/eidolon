# Eidolon – CodeGraph v1 Design Spike (CG‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Control Plane Lead

## 1. Purpose

Define the CodeGraph v1 data model, storage/query approach, and scanning strategy with concrete acceptance criteria and a 2‑week prototype plan. Optimise for Python initially, but keep language‑agnostic affordances.

## 2. Scope & goals

* Represent code artefacts (file, module, class, function) and relationships (contains, imports, calls, tests, ownership) with provenance.
* Support fast queries required by Planner, Conformance, Coder and Architect views.
* Scale to large repos/monorepos with incremental scanning.
* Be reproducible and easy to version/evolve.

Out of scope v1: deep interprocedural call‑graph for dynamic features; full multi‑language parity.

## 3. Core queries (drive the design)

* Q1: Given a file/module, list public classes/functions with metadata and docstrings.
* Q2: Given a function, show its parents (class/module), incoming/outgoing imports, and tests that exercise it (by heuristics + coverage data when present).
* Q3: Find all modules that import package X (for dependency boundary checks).
* Q4: List artefacts that changed in commit C and all dependants within the repo (fan‑out impact).
* Q5: Surface violations: e.g., anything in `ui.*` importing `data.*` (layering rules).
* Q6: Map artefacts to subsystem boundaries defined in `plan.yaml` and list drifts.
* Q7: For a requirement/ADR link, show affected artefacts and their risk profile.

Target latency: p95 ≤ 300 ms per query on a 5 MLOC repo; ≤ 500 ms for Q4/Q6.

## 4. Data model (property graph over relational tables)

### 4.1 Entities (nodes)

* **Repository**: id, name, default_branch
* **Commit**: id (SHA), repo_id, parent_sha, timestamp, author
* **Artefact**: id, repo_id, path, language, kind [file|module|class|function], name, fqname, visibility, summary, doc_digest, sha256, sloc, metrics (JSONB), owners (JSONB), tests (JSONB), created_at
* **Boundary**: id, type [subsystem|module_group|layer], name, selector (glob/regex), plan_version

### 4.2 Relationships (edges)

* **CONTAINS**(parent_artefact_id → child_artefact_id)
* **DECLARES**(file/module → class/function)
* **IMPORTS**(from_artefact_id → to_artefact_id, symbols JSONB, is_dynamic bool)
* **CALLS**(from_function_id → to_function_id, confidence float, optional v1)
* **TESTS**(test_artefact_id → target_artefact_id, method: coverage|naming|marker)
* **MAPS_TO_BOUNDARY**(artefact_id → boundary_id, source: plan|rule|inferred)

### 4.3 Provenance and versioning

All nodes/edges carry: commit_sha, tool_version, scanner_config_id. Primary keys include commit_sha to allow time‑travel; latest view provided by materialised views.

## 5. Storage approach

### v1 recommended: **Postgres (relational) + JSONB** for flexible attributes, with **edge tables** and **materialised views** for hot queries. Blobs (e.g., AST snapshots) go to the Object Store

**Why**: Mature, easy ops, strong indexing, transactional writes, well‑known at scale; avoids standing up a separate graph DB initially while still supporting graph‑like queries.

**Tables (sketch)**

* artefact(artefact_id PK, repo_id, path, kind, name, fqname, commit_sha, sha256, metrics JSONB, owners JSONB, visibility, sloc, doc_digest)
* edge_imports(src_id, dst_id, commit_sha, symbols JSONB, is_dynamic, PRIMARY KEY(src_id, dst_id, commit_sha))
* edge_contains(parent_id, child_id, commit_sha)
* edge_declares(file_or_module_id, decl_id, commit_sha)
* edge_tests(test_id, target_id, commit_sha, method)
* boundary(boundary_id PK, type, name, selector, plan_version)
* maps_to_boundary(artefact_id, boundary_id, commit_sha, source)
* commit(commit_sha PK, repo_id, parent_sha, timestamp, author)

**Indexes**

* artefact(repo_id, path), artefact(fqname), artefact(commit_sha)
* edge_imports(src_id), edge_imports(dst_id)
* maps_to_boundary(boundary_id), maps_to_boundary(artefact_id)

**Materialised views**

* `mv_latest_artefact` selecting max(commit_sha by topo) per artefact_id
* `mv_imports_latest` joining imports with latest artefacts
* `mv_boundary_members` resolving selectors into concrete artefact sets
* Refresh policies on run completion

**Alternatives (kept in reserve)**

* Neo4j/JanusGraph for native graph traversal if QPS/latency demands outgrow SQL
* OpenSearch for free‑text over docstrings and findings (already in HLD)
* DuckDB/Parquet for offline analytics

## 6. Scanning strategy

### 6.1 Initial full scan

* Walk repo; for Python: parse files using `ast` module; extract module, classes, functions, imports; compute SHA256 and SLOC; detect tests (pytest/naming heuristics); owners (CODEOWNERS/gitattributes).
* Persist artefacts and edges with commit_sha.

### 6.2 Incremental scan (diff‑based)

* Inputs: merge‑base and target commit SHAs. Use `git diff --name-status`.
* For modified files: reparse file → update artefact rows and edges for that file.
* For moves/renames: maintain stable artefact_id via content hash + history lookups.
* Impact re‑resolution:

  * recompute `edge_imports` for the changed file
  * recompute `maps_to_boundary` if path changed
  * optional: queue dependants by reverse `edge_imports` to refresh summaries/caches

### 6.3 Heuristics and limits

* Skip vendored or generated paths via patterns.
* Cap per‑file parse time; mark as partial on timeout (flag for Coder view).
* Detect dynamic imports (`__import__`, importlib) and mark `is_dynamic=true`.

## 7. API surfaces

* `POST /graph/scan` { repo, base_sha, head_sha }
* `GET /graph/artefacts?path=...|fqname=...`
* `GET /graph/dependants?artefact_id=...`
* `GET /graph/violations?rulepack=...`
* `GET /graph/boundary-members?boundary_id=...`
* `GET /graph/stats` { nodes, edges, freshness }

## 8. Conformance rules (examples)

* Layering: disallow `ui.* -> data.*` imports
* Boundary walls: forbid imports across subsystem boundaries unless whitelisted
* Security: only modules in `auth.*` may import `crypto.*`

Rules expressed as DSL over selectors, compiled to SQL against edge tables and boundary mappings.

## 9. Performance targets & benchmarking plan

* Dataset: synthetic 5–50 MLOC repo, realistic Python package layout
* Benchmarks:

  * Full scan throughput: ≥ 250 files/sec per 4 vCPU worker
  * Incremental scan of 1 kLOC diff: ≤ 30 s end‑to‑end
  * Query p95: Q1–Q3 ≤ 300 ms; Q4/Q6 ≤ 500 ms
* Tooling: `pytest-benchmark`, `locust` for API, container resource limits recorded

## 10. Data quality & provenance

* Each artefact and edge row tagged with `scanner_version`, `policy_id`, timestamps
* Validation: schema constraints (FKs), AST parse success rates, dynamic import flags
* Replay: given commit_sha and scanner_version, re‑emitting identical rows (within allowed deltas)

## 11. Evolution & compatibility

* Version documents: `codegraph.schema.json` with semver
* Migrations: additive first; deprecations with dual‑write then drop
* Fallback: export/import as JSONL for portability between storage backends

## 12. Security & privacy

* Do not store raw source in DB; store digests and pointers to object store
* Redact secrets discovered during scan; emit SEC findings separately
* Tenant scoping on every table (tenant_id columns + RLS policy if available)

## 13. Open issues (acceptance gates)

* CG‑A: Decide stable artefact_id scheme (path vs content‑hash vs hybrid)
* CG‑B: Confirm boundary selector language (glob + regex + fqname prefixes)
* CG‑C: Define minimal CALLS extraction (optional v1)
* CG‑D: Finalise materialised view refresh cadence

## 14. 2‑week prototype plan

**Week 1**

* Implement Python scanner (files → artefacts + imports)
* Postgres schema + ingest pipeline for a mid‑size repo
* Implement Q1–Q3 endpoints; baseline benchmarks

**Week 2**

* Incremental diff scan + dependants API (Q4)
* Boundary mapping + layering rule checks (Q5/Q6)
* Materialised views + refresh on run complete
* Report: performance, gaps, and go/no‑go for v1

## 15. Acceptance criteria (mirrors Master Issue CG‑01)

* Schema and JSON Schema published
* 5 MLOC repo ingested; Q1–Q3 p95 ≤ 300 ms; Q4/Q6 p95 ≤ 500 ms
* Incremental scan of 1 kLOC diff ≤ 30 s
* Reproducibility: identical outputs across two runs with same SHA and scanner version
