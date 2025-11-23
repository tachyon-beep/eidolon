# Workflow Analysis Playbook (Eidolon)

Purpose: a repeatable way to discover, document, and grade user workflows in Eidolon so we can see what is supported, what is partial, and what is missing before prioritizing fixes.

## Inputs & Signals
- Product intent: README, ARCHITECTURE.md, MVP_SUMMARY.md, AGENT_HIERARCHY.md, UX_REVIEW.md.
- Actual behavior: API routes (`src/eidolon/api/routes.py`), orchestrators (`src/eidolon/agents/orchestrator.py`, `src/eidolon/orchestrator.py`), front-end views/components, DB schema (cards/agents), WebSocket events.
- Observed usage: run the UI, trigger analyses, capture logs, DB state (cards/agents), and cache stats.
- Constraints: environment (LLM keys, git availability, cache on/off), performance limits (file count), and error handling paths.

## Step-by-Step Process
1) Define scope and actors
   - State the question (e.g., “How do users run analyses and apply fixes?”).
   - Identify actors (human roles and system agents): analyst running Explore, developer applying fixes, reviewer reading Agent Snoop, automated WebSocket consumer.

2) Inventory canonical workflows (name them)
   - Create a short list of flows to inspect (e.g., “Full analysis from Explore”, “Card routing and status updates”, “Apply proposed fix”, “Incremental analysis”, “Cache management”, “Agent evidence review”).
   - For each, note the entry points (UI/API/CLI) and expected outputs (cards, agent tree, fixes applied).

3) Trace the workflow path
   - UI: start views/components, user inputs, state changes, WebSocket events, navigation.
   - API: endpoints called, payloads, success/error responses.
   - Backend: orchestrator branches (full vs incremental), cache usage, git checks, validation, side effects (cards created, agents saved, backups written).
   - Data: DB rows/tables touched (cards, agents, analysis_sessions), cache keys.

4) Capture “happy path” vs. “failure/edge path”
   - Happy path: preconditions satisfied (LLM key, git repo, valid path), expected sequence with timestamps where possible.
   - Failure modes: missing keys, invalid path, non-git repo, cache miss/hit behavior, WebSocket failure, validation errors on fixes.
   - Note what the user sees (UI feedback) vs. what the system logs.

5) Grade support level for each step
   - Fully supported: implemented and visible to user.
   - Partially supported: backend exists but no UI, or UI exists but data not linked.
   - Missing: not implemented or blocked by unmet prerequisite.
   - Record evidence: file refs (path:line) and UI behavior.

6) Identify gaps and their impact
   - For each gap, note: impact on user (blocked vs. inconvenient), severity, and scope (one view vs. system-wide).
   - Example format: “Gap: class tickets are not linked to their functions/modules in Graph tab → impact: cannot navigate from class card to functions.”

7) Propose remediation slices
   - Suggest the smallest increments: backend change, UI change, and glue (DB/API/UI/graph sync).
   - Add acceptance checks: “Graph tab shows parent module + child functions for class tickets; clicking navigates; code links resolved.”

8) Validate in-product
   - Re-run the flow with instrumentation on: confirm cards/agents created, WebSocket events arrive, status changes persist, backups exist for applied fixes.
   - Capture screenshots/logs for the report.

9) Report structure (per workflow)
   - Name: “Apply Proposed Fix”
   - Intent: user outcome expected.
   - Path: UI/API sequence.
   - Preconditions: keys, git, cache state, validation flags.
   - Observed behavior: what happens now (with evidence).
   - Support grade: full/partial/missing.
   - Gaps: bullets with impact.
   - Recommendations: ordered, minimal slices.

## Quick Reference: Current High-Signal Gaps (as of this analysis)
- Class/function tickets not linked to their functions/modules in Graph tab; graph shows IDs only.
- Incremental analysis lacks UI entry; non-git repos return 400 without user guidance.
- Fix apply lacks diff/rollback UX; single-hunk only; errors shown via blocking alerts.
- Routing/status updates are metadata only; no parent/child navigation or code/test link surfacing.
- Cache controls are all-or-nothing; no per-file invalidation or retention configuration.

## Outputs
- Workflow dossier per flow (using the report structure above).
- Consolidated gap list with severity and suggested slices.
- Optional: swimlane or sequence diagrams for the most important flows.

## End-to-End Decision Tree (LLM Analysis → Recommendations → Cards → Execution)
1) Entry: “Analyze path”
   - Inputs: repo/path, optional include/exclude, mode (full vs incremental), credentials (LLM key), git availability.
   - Decisions:
     - Path valid? If no → surface error (UI toast) and stop.
     - Git repo? If incremental requested and no git → fall back to full or ask user.
     - Cache valid? If yes → reuse; if no → compute fresh.
   - Outcome: Start analysis session; stream `analysis_started`.

2) Precompute context
   - Actions: build AST + call/import graph; gather file list; compute metrics (complexity/length).
   - Decisions:
     - Exceeded size limits? If yes → warn and cap scope.
     - Graph built? If no → degrade gracefully (no callers/callees hints).
   - Outcome: Context bundles per level ready (System/SubSystem/Module/Class/Function).

3) Hierarchical LLM passes (per scope)
   - For each scope, send tailored pack:
     - System: topology, subsystems, hotspots.
     - Subsystem: modules, coupling, risk themes.
     - Module: imports, classes/functions, smells, metrics.
     - Class: class + methods, peer classes, module context.
     - Function: body, signature, docstring, callers/callees, nearby helpers.
   - Decisions:
     - LLM call succeeds? If no → retry, then mark partial and continue.
     - Context too large? Trim to top-N items by risk/complexity.
   - Outcome per element: structured grade (A/B/C/D/E or GOOD/NEUTRAL/BAD) + list of atomic recommendations.

4) Recommendation handling
   - Each recommendation is surfaced as an individual UI element tied to its source element (with IDs, file refs, graph links).
   - Decisions:
     - Auto-promote? Default is manual promotion; optionally auto-promote above severity threshold.
     - Merge duplicates? If similar recs exist, suggest merge.
   - Outcome: recommendations ready for promotion; user sees grade + rec list.

5) Promotion to cards
   - User picks recommendations to promote → cards.
   - Decisions:
     - Card type (Review/Change/Architecture/Defect/Test/Requirement).
     - Edit metadata (title/summary/priority/links/parent).
     - Routing target tab.
   - Outcome: card created with audit log; routing metadata set; WebSocket `card_updated`.

6) Card orchestration (architect → coding → tests)
   - Architect LLM decomposes card into changes/tasks.
   - Coding LLMs implement changes (per file/function); lint/tests run; backups optional.
   - Decisions:
     - Need human approval before apply? If yes → hold and request approval.
     - Validation passes? If no → return to architect for revision or flag to user.
   - Outcome: proposed fix (with diff, validation flags) and status updates.

7) Apply fix and integrate
   - User reviews proposed fix (diff, confidence, backup path) and applies.
   - Decisions:
     - Apply now vs. defer; create patch vs. direct write; rollback needed?
     - Multiple hunks? If multi-hunk unsupported, require manual apply.
   - Outcome: file updated + backup; card moves to Done/Approved; audit log entry; WebSocket `fix_applied`.

8) Close the loop
   - Decisions:
     - Additional cards spawned? Link children/parents.
     - Retest? If tests failed or coverage low, rerun.
   - Outcome: updated cards/agents; session stats; ready for next iteration.

## Lifecycle Views for Bugs vs. Features
Bug pipeline (end-to-end):
- Detect: hierarchical review surfaces issues; recommendations promoted to Defect/Review cards.
- Plan: optional architect LLM refines scope/acceptance; link to code/tests; set priority.
- Build: coding agents generate proposed fixes (per module/class/function); lint/tests run.
- Validate: test agents execute checks; validation flags stored on proposed fixes.
- Apply: operator reviews diff/backup info; applies; card status → Done/Approved.
- Close: operator signs off; parent/child links updated; audit and metrics recorded.

Feature pipeline (end-to-end):
- Shape: operator discusses with Business Architect LLM to produce Requirement cards with acceptance criteria and scope.
- Architect: Solution Architect LLM decomposes into Architecture/Change cards, mapped to system → subsystem → module tasks.
- Plan: route tasks to Code tab; set priorities/owners; link to files/modules.
- Build: coding agents implement per module/class/function; generate proposed fixes; lint/tests run.
- Integrate: assemble multi-module changes; run broader test suites; resolve conflicts.
- Close: operator reviews outputs and test results; mark cards Done/Approved; capture follow-ups as new cards if needed.
