# Eidolon – Integration Contracts (INT‑01)

Version: 0.1
Date: 10 Nov 2025
Owner: Integrations Lead

## 1. Purpose

Define stable, versioned contracts between Eidolon and external systems: Git forges, CI/CD, issue trackers, VCS hosting, chat/notifications, and artifact registries. Cover webhook events, REST/GraphQL APIs, auth methods, degraded modes, retries, and compatibility policy. Integrates with DR‑01 (drift in PRs), ORCH‑01 (status checks), DATA‑01 (IDs & ERD), SEC‑01 (identity & egress), and OBS‑01 (telemetry).

## 2. Scope

* **Providers**: GitHub, GitLab, Bitbucket; CI (GitHub Actions, GitLab CI, Jenkins, CircleCI); Issue trackers (Jira, GitHub Issues); Chat (Slack, MS Teams); Artifact registries (Docker/OCI, PyPI); Secrets managers (Vault, AWS/Azure/GC secrets).
* **Operations**: Trigger runs, update checks/statuses, post comments, create issues, consume webhooks, fetch diffs, attach artifacts.

## 3. Versioning & compatibility

* **External API** of Eidolon: semantic versioned `/api/v1` with HATEOAS links; two minor versions supported concurrently (e.g., v1.7 and v1.8).
* **Webhooks**: `X-Eidolon-Event` header with schema `$id` and `version`.
* **Provider contracts**: track per‑provider API version (e.g., GitHub v3 REST / v4 GraphQL). Pin versions in adapter.

## 4. Auth patterns

* **Outbound to provider**: OAuth app or PAT (scoped minimal), or app installation (GitHub App).
* **Inbound to Eidolon**: HMAC‑signed webhooks with per‑provider shared secret; IP allow‑lists option.
* **Secrets**: fetched from Secret Manager per SEC‑01; no long‑lived secrets in DB.

## 5. Webhook schemas (inbound to Eidolon)

### 5.1 Git push

```json
{
  "$id": "eidolon.webhooks.git.push@v1",
  "repo": {"provider":"github","full_name":"acme/proj"},
  "after":"6f3a...", "before":"b2c1...",
  "commits":[{"id":"6f3a...","added":[],"removed":[],"modified":["src/x.py"]}],
  "branch":"main", "pusher":"alice"
}
```

Action: enqueue **scan+evaluate** run for commit `after` if branch matches policy.

### 5.2 Pull Request / Merge Request

```json
{
  "$id": "eidolon.webhooks.git.pr@v1",
  "repo": {"provider":"gitlab","full_name":"acme/proj"},
  "pr": {"id":123, "title":"refactor X", "state":"opened"},
  "head_sha":"abc...", "base_sha":"def...",
  "author":"bob", "draft":false
}
```

Action: diff‑scoped run; attach DriftItems and Evaluations as PR comments and a single **status check**.

### 5.3 CI pipeline status

```json
{
  "$id": "eidolon.webhooks.ci.status@v1",
  "provider":"github-actions",
  "repo":"acme/proj",
  "run_id":"gh-12345",
  "status":"queued|in_progress|success|failure",
  "commit":"6f3a..."
}
```

Action: mirror status to Operator view; gate merges if policy requires.

### 5.4 Issue created/updated

```json
{
  "$id": "eidolon.webhooks.issue@v1",
  "provider":"jira",
  "issue_key":"ACME-42",
  "summary":"Bug in module A",
  "changes": {"status":"In Progress"}
}
```

Action: link to DriftItem or Requirement; update traceability.

## 6. Outbound actions (from Eidolon)

### 6.1 Commit status / check run

```json
{
  "context":"Eidolon",
  "state":"success|failure|neutral|pending",
  "target_url":"https://eidolon/runs/r-123",
  "description":"Drift: 0 blocking; Evaluations: 102/102 pass"
}
```

### 6.2 PR/MR comment bundle

```markdown
**Eidolon Summary (r-123)**
- Drift: 2 warnings, 0 blocking
- Findings: 3 fixes proposed (links)
- Cost: est $2.10, actual $1.87
[View details](https://eidolon/runs/r-123)
```

### 6.3 Create issue / task

```json
{
  "title":"Boundary breach: ui→data in module X",
  "body":"See DriftItem d-456. Auto-fix available.",
  "labels":["eidolon","drift","security"],
  "assignees":["alice"]
}
```

### 6.4 Artifact attachment

* Attach signed artefacts (ADRs, reports) to PRs or issues via provider APIs. Use presigned URLs; avoid direct embedding of sensitive data.

## 7. Provider adapters (capabilities & caveats)

* **GitHub**: App installation preferred; REST v3 + GraphQL v4; checks API for per‑job summaries. Rate limits respected; secondary rate limit backoff.
* **GitLab**: Personal/project tokens or OAuth; use status and MR notes; higher payload limits on self‑hosted.
* **Bitbucket**: Webhooks and statuses; limited checks UI—fallback to comments.
* **Jira**: Cloud/Server REST; link DriftItem/Requirement to issues via custom fields.
* **Slack/Teams**: Webhooks + OAuth bots; interactive action buttons link back to Eidolon views.
* **Jenkins/CircleCI**: Trigger jobs with parameters; poll or webhook back.

## 8. Degraded modes & retries

* If provider down or rate‑limited:

  * Queue outbound actions with exponential backoff and jitter; dead‑letter after N tries with Operator alert.
  * UI shows **Degraded: ProviderName** with impact summary.
  * Never block local evaluations unless policy mandates external checks.
* Idempotency keys on POSTs to avoid duplicate comments/issues.

## 9. Mapping to DR‑01 and RF‑01

* PR diffs seed **diff‑scoped** CodeGraph scans; blocking drift marks checks `failure`.
* Architect acceptance of drift via DWI updates PR check in real time (dry‑run conformance).

## 10. Events & telemetry (OBS‑01)

* Emit `integration.call` metric with labels: provider, verb, endpoint, status, latency_ms, rate_limited:boolean.
* Alert when failure rate > 5% over 10m or rate‑limit backoff sustained > 30m.

## 11. API surface (Eidolon public)

```http
POST /integrations/providers/{name}/install           # store tokens/keys
GET  /integrations/providers                           # list & health
POST /integrations/triggers/run                        # manual trigger for repo@sha
POST /integrations/pr/{provider}/{repo}/{number}/comment
POST /integrations/status/{provider}/{repo}/{sha}
GET  /integrations/events?since=1h                     # event stream for audit
```

## 12. Security & compliance

* Principle of least privilege on provider tokens; rotate every 90 days.
* Signed webhook verification; reject unsigned/invalid.
* Egress allow‑lists per provider domains (SEC‑01).
* Data minimisation: store provider payload hashes unless required for features.

## 13. Testing & sandboxes

* Provider sandbox environments used for CI (GitHub Enterprise Server, GitLab self‑hosted).
* Contract tests: simulate events, assert status/check updates, idempotency, and degraded‑mode behaviour.

## 14. Acceptance criteria

* For each provider in scope, all webhook types and outbound actions validated in staging via contract tests.
* Rate limit handling verified; no data loss; duplicate suppression works via idempotency keys.
* Degraded modes surface in UI with clear operator actions; local runs continue unless policy blocks.
* Public API `/api/v1` documented with OpenAPI; SDK stubs generated for JS/Python.

## 15. Open questions

* Priority order of providers for v1 GA? (suggest: GitHub, GitLab, Jira, Slack).
* Do we support commit signing verification and require DCO for PRs?
* Should Eidolon post inline code review comments or only summary comments to reduce noise?
