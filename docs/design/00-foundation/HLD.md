---
id: HLD
version: 1.0
owner: Architecture Team
status: draft
summary: End-to-end high level design for Eidolon covering context, containers, components, workflows, data models, interfaces, and risks.
tags:
  - foundation
  - architecture
  - hld
last_updated: 2025-11-10
---

# Eidolon – High Level Design (HLD)

Version: 1.0
Date: 10 Nov 2025
Owner: Architecture Team

## 1. Executive summary

Eidolon is a modular platform that scans source repositories, builds a code knowledge graph, and runs scalable evaluations per function, class, module, subsystem, and system. It supports top down design and stepwise refinement, synthesises architectural documentation, and publishes traceable artefacts. A Vue based web console provides telemetry and control. Eidolon is orchestrator agnostic and uses open source components suitable for commercial and government use.

## 2. Goals and non goals

### Goals

* Analyse Python codebases at multiple granularities with reproducible results
* Support top down design and stepwise refinement from goals to implementable tasks
* Produce C4 views, ADRs, interface specs, and runbooks with provenance
* Provide a real time web console for runs, artefacts, and governance
* Run locally or on Kubernetes, with pluggable workflow engines
* Use open source licences suitable for government and commercial use

### Non goals

* Eidolon is not an LLM product. LLMs are optional evaluators.
* It is not a full ALM or issue tracker. Integrations are supported.

## 3. User roles

* **Operator (Runs & Capacity)**: focuses on executing jobs and keeping the queue healthy. Starts, pauses, retries, and reorders runs. Watches throughput, errors, and cache efficiency. Minimal code context; deep on execution state.
* **Coder (Tactical Oversight)**: reviews per-function/class/module findings, agent responses, and proposed patches. Approves or edits changes, discusses bugs with function/class/module agents, and triggers targeted re-runs.
* **Architect (Strategic Oversight)**: big-picture view across system and subsystems. Discusses features and constraints with system/subsystem agents; validates HLD compliance, security posture, interoperability, and complex integration issues. Sends design deltas for refinement and records ADRs. Breaks requirements down into work packages for Coders.
* **Product Owner (Discovery & Shaping)**: converses with a product LLM about "what can my product do". The LLM elicits and structures requirements as records for the Architect to consider in the Architecture view.

## 4. Context (C4 level 1)

**Systems**: Source Control (Git), CI, Package Registry, Secrets Manager, Identity Provider (OIDC), Observability Stack, Storage (object store), Issue Tracker, Artefact Registry, Email or Chat for notifications, Optionally an LLM endpoint.
**Eidolon**: connects to repos, runs orchestrated tasks, stores results and generates documentation.

## 5. Containers (C4 level 2)

* **Eidolon Web (Vue 3)**: SPA for control and telemetry. Connects to API and WebSocket.
* **Eidolon API Gateway**: REST and WebSocket entry point. AuthN via OIDC, AuthZ via RBAC. Rate limiting and audit logging.
* **Control Plane**: run planner and dispatcher, policies, scheduling requests to the chosen orchestrator.
* **Worker Runtime**: task executors that run scanners, evaluators, and synthesis tasks. Packaged as containers.
* **Orchestrator Adapter**: glue for orchestration engines. **v1 ships Local + Temporal**, with Airflow/Dagster/Argo/Flyte behind feature flags until conformance + telemetry mature.
* **Metadata Store**: relational DB for runs, artefacts, policies, RBAC, and approvals.
* **Object Store**: immutable blobs for snapshots, JSONL results, diagrams, and SBOMs.
* **Search and Index**: optional OpenSearch for full text queries over findings and docs.
* **Observability**: Prometheus metrics, OpenTelemetry traces, Loki logs, Grafana dashboards.
* **Docs Publisher**: builds and serves documentation sites (MkDocs or Docusaurus).
* **Provenance Service**: signing and verification of artefacts, append only logs.

## 6. Component view (C4 level 3)

### 6.1 Control Plane

* **RunManager**: creates runs, calculates content hash keys, dedupes work
* **Planner**: builds plan.yaml from goals, constraints, and code graph
* **Refiner**: loops until design is implementable, updates plan version
* **Dispatcher**: submits tasks to the orchestrator adapter with concurrency guards
* **PolicyEngine**: enforces policies for approvals, rate limits, data handling

### 6.2 Worker Runtime

* **RepoScanner**: walks repos, builds AST and import graph, computes SHAs
* **Evaluator**: executes static checks and optional LLM reviews with retries
* **Synthesiser**: generates ADRs, C4, API specs, test strategy, runbooks
* **Publisher**: writes artefacts to object store and updates indices
* **Conformance**: checks architecture rules and cross cutting concerns

### 6.3 Orchestrator Adapter

* **LocalAdapter**: developer workstation/default CI runner (always on)
* **TemporalAdapter**: durable workflows and activities (**primary cloud target for v1**)
* **AirflowAdapter**: DAG generation and task submission (feature-flag)
* **DagsterAdapter**: asset jobs and partitions (feature-flag)
* **ArgoAdapter**: orchestrates K8s DAG/Step workflows via Argo templates (feature-flag)
* **FlyteAdapter**: manages strongly typed tasks, launch plans, and registries (feature-flag)

### 6.4 Data and Storage

* **Metadata DB**: Postgres. Entities: Run, Task, Artefact, Plan, Policy, User, Approval, Token, SLA, CostBudget
* **Blob Store**: S3 compatible. Layout by tenant, project, repo, run, artefact type
* **Search**: OpenSearch indices for findings, ADR text, evaluation notes

### 6.5 Telemetry

* **Metrics**: task latencies, queue depth, cache hit ratio, token usage
* **Traces**: end to end spans per run and per artefact
* **Logs**: structured JSON with correlation IDs

## 7. Key workflows

### 7.1 Plan and discover

1. Operator selects repo and commit; starts a run.
2. RunManager locks the run key based on commit SHA and policy version.
3. RepoScanner produces ModuleIndex and CodeGraph artefacts.
4. Planner creates plan.yaml and initial C4 Context and Container.

### 7.2 Stepwise refinement (Architect view)

1. Refiner expands subsystems into components and interfaces.
2. Conformance checks apply policies and rules (HLD compliance, security, interop).
3. Architect discusses design deltas with system/subsystem agents; records ADRs.
4. When implementable, emit tasks for evaluation and synthesis.

### 7.3 Evaluation and synthesis (Coder view)

1. Evaluate each artefact with static tools and optional LLM.
2. Coder reviews per-artefact agent notes, proposed patches, and test changes.
3. Coder approves, amends, or rejects changes; targeted re-runs as needed.
4. Synthesiser creates ADRs, C4 Component/Code views, API specs; Publisher updates docs.

### 7.4 Execution control (Operator view)

* Start/stop/pause runs, adjust concurrency, set priorities.
* Retry failed shards, thaw circuit breakers, and inspect queue health.
* Monitor cache hit ratio and token/compute budgets.

### 7.5 Requirements capture & triage (Product Owner to Architect)

1. Product Owner chats with the **Product LLM** about capabilities, outcomes, constraints.
2. LLM teases out structured requirements (Use Cases, NFRs, Risks) into a **RequirementRecord**.
3. RequirementRecords enter an **Architect Inbox** for review in the Architecture view.
4. Architect accepts/edits/rejects, links to plan.yaml goals, and schedules refinement.

## 8. Data model (selected)

### 8.1 plan.yaml (semantic outline)

* system: name, goals, NFRs, constraints
* context: actors and external systems
* decomposition: subsystems, components, interfaces
* risks: register with mitigations
* provenance: input SHAs, tool versions, policy id

### 8.2 RequirementRecord

* id, title, description, origin: "product-llm", owner, priority
* use_cases: [UC...]
* nfrs: ["Throughput>=X", ...]
* links: related ADRs, plan goals, issues
* status: Draft | Proposed | Accepted | Rejected
* provenance: chat transcript pointer, timestamps, signer

### 8.3 EvaluationRecord

* artefact_id, sha, toolchain versions
* metrics: cyclomatic, lloc, docstring, coverage
* checks: rule id, status, message
* reviews: engine, status, score
* timestamps, run_id, plan_version

### 8.4 ProvenanceEnvelope

* artefact pointer, digests, signer, signature, timestamp
* parent digests for tamper evidence

## 9. External interfaces

### 9.1 REST API (Eidolon API Gateway)

Base: `/api/v1`

* `POST /runs` start a run for repo and commit
* `GET /runs/{id}` fetch run status and telemetry
* `POST /plans` create or update a plan
* `GET /artefacts/{id}` retrieve metadata and signed URLs
* `GET /search` query findings and docs
* `POST /approvals` approve or reject items
* `POST /policies` create or update policies
* `POST /orchestrator/submit` advanced submissions

Auth: OIDC bearer tokens.
AuthZ: RBAC with scopes: read, write, approve, admin.
Rate limits: token bucket per user and per tenant.

### 9.2 WebSocket events

Base: `/ws`
Events: `run.created`, `task.started`, `task.completed`, `run.metrics`, `alert.policy`, `approval.requested`, `docs.published`.

### 9.3 Inbound webhooks

* Git push and PR events
* CI pipeline status
* Issue Tracker events for traceability

## 10. Eidolon Web – Vue UX

### 10.1 Stack

* Vue 3, Vite, TypeScript, Pinia, Vue Router, Axios, ECharts or Chart.js, xterm.js, WebSocket client, OpenAPI client.

### 10.2 Four primary views

* **Operator** (`/operator`): execution-first dashboard.

  * Widgets: QueueDepth, Throughput, ErrorRate, CacheHit, TokenSpend.
  * Controls: StartRun, PauseRun, RetryFailed, ConcurrencySlider, PriorityEditor.
  * Panels: RunList, RunDetail (Gantt + DAG), LiveLog, AlertStream.

* **Coder** (`/coder`): tactical per-artefact triage.

  * Widgets: UnreviewedFindings, PatchQueue, TestStatus.
  * Panels: ArtefactInspector (function/class/module context), AgentChat (LLM + tools), DiffViewer, Approve/Reject bar, TargetedRerun.
  * Filters: file path, severity, rule id, subsystem.

* **Architecture** (`/architecture`): strategic system view.

  * Widgets: HLDCompliance score, ThreatModel status, Interop matrix.
  * Panels: C4Viewer (Context/Container/Component/Code), PlanEditor (plan.yaml with schema), ADRBoard, SubsystemAgentChat, IntegrationBugTracker.

* **Product Owner** (`/product`): discovery & shaping.

  * Panels: ProductChat (guided prompts), RequirementsTable, UseCaseCanvas, NFREditor.
  * Actions: SubmitToArchitect (creates RequirementRecord), LinkToRoadmap.

### 10.3 Routes

* `/` redirects to last used view.
* `/operator`, `/coder`, `/architecture`, `/product`.
* Deep links: `/runs/:id`, `/artefacts/:id`, `/plans/:id`, `/adrs/:id`.

### 10.4 Key components

* **TaskGraph** with drill-down to artefact context.
* **AgentChat** with tool buttons ("Propose patch", "Explain finding", "Generate tests").
* **C4Viewer** rendering Structurizr/PlantUML exports.
* **RequirementsTable** with statuses: Draft, Proposed, Accepted, Rejected.
* **ApprovalPanel** for coder approvals and architect ADR sign-off.

### 10.5 UX behaviours

* Live updates via WebSocket; offline-friendly queues for actions.
* Role-aware nav (users can access multiple views if permitted).
* Consistent keyboard shortcuts and a11y support.

## 11. Orchestration

### 11.1 Adapter contract

* Standard task spec with id, inputs, outputs, resources, concurrency class, retries, deadlines, secrets, cache key.
* Adapters translate spec to Airflow DAGs, Dagster jobs, Temporal workflows, or Argo/Flyte templates.

### 11.2 Concurrency and backpressure

* Global caps per evaluator and per tenant
* Priority queues for human in the loop items
* Exponential backoff and jitter
* Circuit breakers for flaky dependencies

## 12. Deployment view

### 12.1 Profiles

* **Local**: Docker Compose with Postgres, MinIO, Keycloak, and a single worker pool
* **Kubernetes**: Helm charts, Horizontal Pod Autoscalers, node pools for CPU and GPU

### 12.2 Secrets and config

* External Secrets Operator for K8s, sealed secrets for bootstrap
* Config via ConfigMaps and environment variables
* Per tenant encryption keys

### 12.3 Storage

* Postgres with PITR
* S3 compatible storage with versioning and lifecycle policies
* Optional WORM buckets for compliance

## 13. Observability and SRE

* OpenTelemetry SDK in all services
* Prometheus metrics scraped from services and workers
* Grafana dashboards for runs, latency, and error budgets
* Loki for logs with correlation IDs
* Alerting rules for queue depth, error rate, and cost anomalies

## 14. Security and compliance

* OIDC with short lived tokens, refresh via PKCE
* RBAC roles: Viewer, Operator, Architect, Approver, Admin
* Least privilege service accounts
* Transport encryption TLS 1.3
* SBOMs for all images
* Artefact signing with cosign and verification on read
* Audit logs retained per policy
* Optional data redaction before any external evaluator call
* Region pinning and data residency controls

## 15. Cost and performance controls

* Content addressed caching keyed on artefact SHA, tool version, and policy id
* Sharding by repository and path prefix
* Batch sizes tuned per evaluator
* Budget caps per tenant, soft and hard limits
* Adaptive sampling of expensive evaluators

## 16. Failure modes

* Orchestrator outage: queue requests and degrade to static checks
* LLM endpoint failure: skip non mandatory reviews with notices
* Object store read failure: retry with exponential backoff
* Plan conflict: reject with diff and require human merge

## 17. Testing strategy

* Contract tests for adapter spec
* Golden tests for Synthesiser outputs
* Replay tests using recorded runs
* Load tests for RunManager and WebSocket scale
* Security tests: OIDC, RBAC, and privilege escalation

## 18. Technology choices and licences

* Vue 3, Vite, Pinia, Chart.js or ECharts (open source licences)
* FastAPI or Flask for API Gateway (MIT)
* Postgres (PostgreSQL licence)
* MinIO or S3 (AGPL or AWS service)
* OpenSearch (Apache 2.0)
* Orchestrators: Airflow, Dagster, Argo, Flyte, Temporal adapters (Apache 2.0 or similar)
* Observability: Prometheus, Grafana, Loki, OpenTelemetry (Apache 2.0)

## 19. Roadmap

**Phase 0**: core scan, evaluate, and publish static docs.
**Phase 1**: top down planning and refinement loop, C4 generation.
**Phase 2**: approvals and provenance, ADR workflow.
**Phase 3**: multi tenant scale, budgets, and cost panel.
**Phase 4**: advanced conformance rules and threat modelling.

## 20. Risks and mitigations

* Evaluator non determinism: fix by version pinning, content hashing, and replayable prompts
* Orchestrator lock in: keep a strict adapter contract and conformance tests
* Cost overrun: budgets, sampling, and hard caps
* Developer trust: transparent provenance and human approval gates

## 21. Example API definitions (abridged)

```http
POST /api/v1/runs            # Operator view starts a run
{ "repo": "git@corp/repo.git", "commit": "6f3a...", "policy": "default@2025-10-01" }

POST /api/v1/runs/{id}/control
{ "action": "pause|resume|retry", "concurrency": 24, "priority": 5 }

GET /api/v1/findings?artefact=...&status=unreviewed   # Coder triage
POST /api/v1/patches { "artefact_id": "...", "diff": "..." }
POST /api/v1/approvals { "item_id": "patch-123", "decision": "approve|reject", "comment": "..." }

POST /api/v1/requirements        # Product Owner capture
{ "title": "Bulk import CSV", "nfrs": ["P95<2s"], "notes": "..." }
GET  /api/v1/requirements/inbox  # Architect inbox
POST /api/v1/requirements/{id}/decision { "decision": "accept|reject", "links": ["plan://G1"] }
```

## 22. Vue component tree (abridged)

```
App
 ├─ TopNav
 ├─ SideNav
 └─ RouterView
    ├─ OverviewPage
    │   ├─ KpiTiles
    │   ├─ RecentRuns
    │   └─ AlertsPanel
    ├─ RunsPage
    │   ├─ RunsTable
    │   └─ RunFilters
    ├─ RunDetailPage
    │   ├─ RunHeader
    │   ├─ TaskGraph
    │   ├─ LogStream
    │   └─ MetricsCharts
    ├─ PlanPage
    │   ├─ PlanEditor
    │   └─ C4Viewer
    ├─ ArtefactsPage
    │   └─ ArtefactTable
    ├─ ApprovalsPage
    │   └─ ApprovalPanel
    └─ SettingsPage
        ├─ IntegrationsForm
        └─ PolicyEditor
```

## 23. Example orchestrator task spec (neutral)

```yaml
id: evaluate-file
resources:
  cpu: 1
  memory: 1Gi
inputs:
  path: "src/pkg/module.py"
  plan_sha: "abc123"
retries: { max: 3, backoff: 5s, jitter: true }
cache_key: "sha256:...:tool@1.4:policy@2025-10-01"
secrets: ["OPENAI_API_KEY"]
outputs:
  - name: "evaluation.json"
```

## 24. Open issues

* Exact schema for CodeGraph v1
* Choice of diagram source (Structurizr DSL vs PlantUML)
* Default conformance rule set for Python projects
* Choice of default orchestrator for reference deployment

---

**End of HLD v1**
