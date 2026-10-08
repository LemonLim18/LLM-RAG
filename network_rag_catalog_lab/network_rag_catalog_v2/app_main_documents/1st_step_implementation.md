# Codex Task — Phase 0 + Phase 1: Transition V9 into an AI Infrastructure Management Workbench

## Project vision

We are developing a polished, modular, AI-intelligent Infrastructure Automation and Orchestration Management Platform, initially focused on multi-vendor network infrastructure, with future extensibility toward Linux server-fleet management.

This is intended to become a professional infrastructure engineering and applied-AI portfolio project, with a target demonstrable release before December 2026.

The desired user experience is a VS Code-inspired web workbench containing an infrastructure explorer, central workspace, integrated AI copilot panel, configuration previews, clarification interactions and activity/output logs.

**Do not build merely a CLI wrapper or a chatbot page.**

## Existing foundations

**Project A — New core engine:** `network_rag_catalog_v2`

This contains the improved V9 network RAG/automation planning implementation. Its latest local working tree includes recent fixes for vendor semantic protection, evidence invalidation and operation confirmation. Preserve those changes.

Important areas to inspect:

- `main.py`
- `app/clarification.py`
- `app/pipeline.py`
- `app/planner/models.py`
- `app/questions.py`
- `app/devices/`
- `app/parameters/`
- `app/knowledge/`
- `app/api/contracts.py`
- `app/config.py`
- Existing tests and documentation

**Project B — Previous FYP prototype:** `Net_Topo_View-intentparse`

Inspect the old prototype source, especially the React/TypeScript/Vite frontend, FastAPI backend, API client, inventory/topology components, device drivers, monitoring, configuration management and Ansible-related functionality.

Locate this source in the provided workspace. If it is missing, report the missing path rather than assuming its contents.

The old project is a reusable reference, not the authority for AI planning. Do not reuse its old intent parser when V9 already provides an improved replacement. Do not retain the old product name.

## Core architecture

Target the following separation:

React + TypeScript workbench
→ typed API client
→ FastAPI integration layer
→ existing V9 services
→ structured session/plan/configuration results.

In parallel, preserve a modular integration boundary for inventory, topology, monitoring and future execution services.

Do not mix presentation logic, AI planning logic, knowledge authoring and infrastructure execution into one module.

Do not invoke `main.py` through subprocesses to process requests. Reuse the underlying Python functions or refactor minimally to provide a clean service boundary.

Keep the CLI working as a development and regression-testing interface.

## Phase A — Inspect and plan

Before implementing, inspect the actual code of both projects and produce `docs/GUI_INTEGRATION_PLAN.md`.

Include:

1. Current V9 entry points and reusable session functions.
2. Old FYP frontend/backend modules suitable for reuse.
3. A reuse/adapt/replace/discard decision for relevant modules.
4. Proposed directory and dependency structure.
5. Backend API contracts and data flow.
6. Frontend component hierarchy.
7. A complete user interaction/state diagram.
8. Important dependencies, technical risks and migration constraints.

Prefer a modular monolith for the first version. Do not introduce unnecessary microservices, message brokers or plugin frameworks.

## Phase B — Implement the first functional vertical slice

Build a working web GUI with:

**Layout**
- Left infrastructure explorer.
- Central task/plan/configuration workspace.
- Right AI chat/copilot panel.
- Bottom activity/logs panel.
- Basic responsive behavior and clear loading/error states.

Reuse appropriate FYP frontend components when they fit the new architecture, rather than recreating everything automatically.

**Backend**
Expose typed FastAPI endpoints for:

- Creating a planning/clarification session from a prompt.
- Retrieving an existing session.
- Submitting answers to clarification questions.
- Correcting an individual task field.
- Confirming task order where necessary.
- Reading available inventory/device metadata.
- Checking backend, model and RAG availability.

Use the current V9 clarification/session code as the authoritative behavior.

Preserve session IDs, question IDs, task IDs, revisions, source revisions, structured answer kinds, provenance, issues, target resolutions, knowledge authority and vendor compatibility information.

**Frontend interactions**
- Submit natural-language requests.
- Display operation and target resolution.
- Display multi-intent and multi-device tasks separately.
- Show each missing-field question as an appropriate control: single selection, multiple selection, text input or nested field editor.
- Send stable option identifiers, never display indices, as authoritative answer values.
- Update the plan after clarification.
- Show per-device rendered configurations.
- Allow reviewing parameters, validation messages and provenance.
- Expose detailed JSON diagnostics in a collapsible developer panel rather than dumping raw JSON as the main interface.

Do not duplicate schema validation, parameter inference or vendor-support decisions in frontend code.

## Safety and existing behavior

For this phase, the application is **preview-only**. No SSH, Ansible execution, device configuration changes or unapproved infrastructure actions.

Existing synthetic inventory fixtures must be clearly identified as demo data. Do not present synthetic state as discovered live infrastructure.

Keep direct-file versus published-release knowledge authority explicit in the GUI.

Preserve V9's semantic protections, structured validation, stale-answer rejection and session behavior.

The old FYP's real execution functionality may be inventoried and prepared for later integration, but it must not become active in Phase 1.

## Required acceptance tests

The browser should support the following workflows through the actual FastAPI/V9 integration:

1. Create VLAN 100 named STAFF on R1, producing a Cisco preview.
2. Configure OSPF on the Penang edge Juniper router, with interactive interface/area clarification and Junos preview.
3. Submit a multi-intent request targeting Cisco R1, Huawei R2 and Cisco SW1, showing distinct tasks and configurations.
4. Request an unsupported Huawei VLAN state change, receiving an explicit block without generating description-changing configuration.
5. Submit a semantic VLAN rename request, with structured operation confirmation and parameter clarification where genuinely required.
6. Reload a saved session and continue its outstanding clarification without losing task state.

The GUI must clearly differentiate ready, needs_clarification, blocked, failed and other actual backend states.

Add backend API tests and appropriate frontend tests. Keep the existing CLI and regression suite functional.

## Implementation constraints

- Inspect before editing.
- Reuse existing correct code rather than duplicating it.
- Preserve clean abstraction boundaries.
- Avoid unrelated refactors.
- Do not automatically reconcile all catalog differences or change SQLite/published releases.
- Do not silently change V9 semantics to make the GUI easier.
- Keep implementation understandable and traceable.
- Prioritize a complete working vertical slice over elaborate styling or unfinished modules.
- Use appropriate Python and TypeScript typing.
- Add reasonable API error handling, request validation, CORS development configuration and frontend loading states.

If an existing V9 extraction/clarification bug is discovered, document it and address it only if necessary for the vertical slice; do not hide it using frontend guesses.

## Final deliverables

1. Functional first-version GUI and FastAPI integration.
2. `docs/GUI_INTEGRATION_PLAN.md`.
3. Clear setup and run instructions for Windows PowerShell.
4. API contract documentation.
5. Relevant backend and frontend tests.
6. Summary of reused FYP modules versus newly implemented modules.
7. Exact changed-file list.
8. Remaining risks and recommended next phase.

Conclude with a working end-to-end demonstration path: open the browser, type a network automation request, answer structured clarification questions, and inspect the generated configuration preview.

Do not attempt to implement the entire platform, server automation, live deployment or monitoring stack in this assignment.