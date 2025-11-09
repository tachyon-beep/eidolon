---
id: UX-02
version: 0.1
owner: Front-End Lead
status: draft
summary: Vue console resilience plan covering offline behaviour, error handling, accessibility, and telemetry integration.
tags:
  - ux
  - resilience
  - governance
last_updated: 2025-11-10
---

# Eidolon – Console Resilience & UX (UX‑02)

Version: 0.1
Date: 10 Nov 2025
Owner: Front‑End Lead

## 1. Purpose

Design the resilience, offline, and error‑handling behaviour of the Eidolon Vue 3 web console. Define how the UI behaves under degraded network conditions, long‑running tasks, backend partial outages, and large data volumes. Ensure accessibility (a11y), role clarity, and consistent feedback across Operator, Coder, Architect, and Product Owner views.

## 2. Objectives

* Keep the UI responsive and usable even when parts of the backend are slow or unavailable.
* Preserve user actions locally until confirmed by the server.
* Provide clear, consistent status messages for all failure and retry states.
* Maintain accessibility and keyboard control across all critical flows.

## 3. Scope

* Applies to all SPA routes and WebSocket interactions.
* Covers network loss, API timeouts, server 5xx, auth token expiry, and bulk data rendering.
* Integrates with OBS‑01 (telemetry), SEC‑01 (auth and data privacy), and INT‑01 (external provider feedback).

## 4. Architecture overview

* **Frontend**: Vue 3 + Vite + Pinia store; Axios for REST; WebSocket for live events.
* **Offline queue**: IndexedDB persistence layer (`eidolon-local`) for pending actions.
* **Sync manager**: background worker that retries queued actions with exponential backoff.
* **Notification bus**: global channel for toasts, banners, and modals; severity‑based styling.

## 5. Network resilience patterns

| Scenario               | UX Behaviour                                                             | Technical Handling                                                                                               |
| ---------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| Network loss           | Banner “Offline mode – changes queued”                                   | Axios interceptors detect `ERR_NETWORK`; queue actions in IndexedDB; UI switches to read‑only except queued ops. |
| API timeout (>10s)     | Spinner replaced with inline warning + “Retry” button                    | Retry up to 3×; then mark as `degraded`.                                                                         |
| WebSocket disconnect   | Toast + reconnect indicator; auto retry exponential backoff up to 5 min  | Fallback to polling every 30s.                                                                                   |
| Partial backend outage | Graceful degradation: disable affected panels; show empty state + reason | Per‑panel health from `/telemetry/health`.                                                                       |
| Auth expiry            | Modal prompt “Session expired – reauthenticate”                          | Refresh token via PKCE; queue actions until resolved.                                                            |

## 6. Data‑volume resilience

* **Virtual scrolling** for tables and logs (vue‑virtual‑scroller).
* **Progressive loading** for task lists >1k entries.
* **Chunked streaming** for logs via WebSocket or HTTP chunked.
* **Backpressure indicator**: displays queue depth and refresh lag.

## 7. Error taxonomy & UX responses

| Type       | Example               | User message                           | Recovery                  |
| ---------- | --------------------- | -------------------------------------- | ------------------------- |
| Validation | invalid field input   | Inline red text + tooltip              | Correct input, auto‑retry |
| Network    | ECONNRESET            | Banner “Lost connection, retrying…”    | Auto retry 3×             |
| Timeout    | 504 Gateway Timeout   | Toast “Server busy – we’ll retry soon” | Backoff retry             |
| Auth       | 401 Unauthorized      | Modal reauth prompt                    | Refresh/login again       |
| Rate limit | 429 Too Many Requests | Toast “Throttled – please wait”        | Cooldown counter          |
| Permission | 403 Forbidden         | Inline lock icon + tooltip             | Request approval          |
| Server     | 500 Internal Error    | Toast + error ID link                  | Retry later or report     |

## 8. Offline queue & replay

* Stored as JSON objects: `{method, url, body, headers, timestamp}`.
* Encrypted at rest via WebCrypto (AES‑GCM).
* Replay policy: retry up to 10× with exponential backoff + jitter; discard after 24h with warning.
* Conflict resolution: last‑write‑wins unless object has version mismatch → manual merge dialog.

## 9. Accessibility (a11y)

* WCAG 2.1 AA baseline.
* Keyboard navigation: Tab, Shift+Tab, Arrow keys for tables and diff viewers.
* Screen reader support: ARIA labels for all actionable elements.
* Colour contrast ≥ 4.5:1.
* Live region updates for status messages.
* Focus management after modal/dialog actions.

## 10. Performance targets

| Metric                    | Target                 |
| ------------------------- | ---------------------- |
| TTI (Time to Interactive) | < 3 s on 3G            |
| FPS during updates        | ≥ 55                   |
| Log stream latency        | < 2 s behind real time |
| Max memory footprint      | < 250 MB per tab       |
| UI error rate             | < 0.5% of actions      |

## 11. Telemetry & logging

* `ui_latency_ms`, `queue_depth`, `offline_actions`, `error_type`, `error_rate`, `reconnect_attempts`.
* Logs correlated with trace_id/span_id from OBS‑01.
* Errors batched and sent via `/telemetry/ui` endpoint on reconnect.

## 12. Role‑specific resilience notes

* **Operator view**: prioritise real‑time metrics; degrade gracefully with cached snapshots; allow manual refresh.
* **Coder view**: keep local diff cache; queued patch submissions replay automatically.
* **Architect view**: plan editor auto‑saves to local storage; merge conflict dialog if backend plan version advanced.
* **Product Owner view**: requirement form drafts stored locally until submit confirmed.

## 13. Visual language for state

* **Green**: success/healthy.
* **Amber**: degraded/partial data.
* **Red**: failed/blocked.
* **Blue**: pending/queued.
* Icons + subtle animations; avoid flashing.

## 14. Testing & chaos scenarios

* Simulate network loss, 5xx, token expiry, websocket churn.
* Measure recovery time to normal (<15s median).
* Automated e2e tests with Cypress intercepts + playwright network throttling.
* Accessibility audits with axe‑core; performance audits with Lighthouse.

## 15. Acceptance criteria

* UI remains responsive under offline mode; queued actions replay successfully ≥95% of time.
* All critical flows (run start, patch approve, drift resolve) have offline coverage.
* Auth expiry handled without data loss.
* Accessibility and performance targets met in automated tests.
* Error taxonomy messages verified for localisation and clarity.

## 16. Open questions

* Should Operator metrics auto‑refresh frequency adapt to browser focus state?
* Is a user‑visible “sync details” panel desirable for queued actions?
* Which browsers form the official support matrix (recommend Chrome/Edge/Firefox latest + Safari n‑1)?
