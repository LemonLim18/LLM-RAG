# Preliminary Architecture

**Status:** Architecture overview established in Iteration -1 and refined by the completed Iteration 0 source audit. Verified facts remain separate from proposed implementation behavior. The concrete contracts and next implementation scope are in [06_GUI_INTEGRATION_DESIGN.md](06_GUI_INTEGRATION_DESIGN.md); source-level reuse decisions are in [05_FYP_REUSE_AUDIT.md](05_FYP_REUSE_AUDIT.md).

## Verified repository facts

### V9 application

- `main.py` is the existing CLI entry point and calls application/session functions rather than presenting a service API.
- `app/pipeline.py` contains the current orchestration entry points, including `run`, `resume_task`, `correct_task`, and `refresh_plan`.
- `app/clarification.py` contains the persisted clarification-session behavior, including `create_session`, `load_session`, `apply_answer`, `apply_correction`, `confirm_session_order`, and `session_to_dict`.
- `app/planner/models.py` defines structured planning models including `ExecutionPlan`, `PlannedTask`, and `ClarificationAnswer`.
- `app/devices/inventory.py` currently loads device records from `data/inventory/devices.json`. The current inventory is file-backed and contains synthetic demo records; it is not yet an editable shared inventory service.
- `app/config.py` defines runtime paths and file-mode defaults. Session and other storage locations are already configuration concerns.
- `app/api/contracts.py` serves existing knowledge-management contracts. It is not, by itself, the proposed workbench service layer.
- The previous runtime handover at `docs/V9_RUNTIME_AUDIT.md` reports focused stabilization work, but the current iteration has not independently verified those runtime claims.

### Previous FYP prototype

- The prototype is located under `app_main_documents/Net_Topo_View-intentparse/`.
- Its frontend is a React/TypeScript Vite application. Iteration 0 verified actual Monaco `Editor` use in `frontend/components/ansible/PlaybookEditor.tsx`, `frontend/views/TemplateStudioView.tsx` and other views, plus `DiffEditor` use in `frontend/components/ansible/AnsibleChatPanel.tsx`. These are source observations, not a successful browser/build test.
- `frontend/src/App.tsx` and `frontend/src/services/api.ts` exist. The API facade covers many domains, including topology, deployment, monitoring, inventory-related operations, authentication, RAG, SSH, Ansible, intent, compliance, incidents, and telemetry.
- `backend/backend.py` creates a FastAPI application and registers a broad set of routers.
- `backend/llm/intent.py` and `backend/ansible/intent_pipeline/` contain the prototype's prior intent-processing implementation. They are not authoritative for the new product.
- `backend/ansible/api.py` combines a wide range of planning, approval, and execution concerns and requires source-level assessment before any selective reuse.
- `backend/db/schema.sql` describes a broad SQLite data model spanning inventory and several future operational domains. Its presence does not establish it as the chosen schema for the V9 workbench.

Iteration 0 recommends minor reuse of ChatInput and static SVG artwork, selective adaptation of layout/editor patterns, and new workbench controllers and services. The FYP inventory API schedules external synchronization, and its application lifespan starts operational services; neither is suitable for mounting in the local demo. See the reuse matrix for exact source paths and classifications.

## Proposed preliminary architecture

The milestone should use a modular monolith with explicit internal boundaries:

```text
React/TypeScript workbench
        |
        | typed HTTP contracts
        v
FastAPI application/service adapter
        |
        +--> V9 planning, retrieval, clarification, validation, rendering, sessions
        +--> demo inventory boundary and local persistence
        +--> artifact/draft and workbench-session persistence

Future adapters (deferred): NetBox, SSH, Ansible/Terraform, telemetry, identity
```

The diagram describes responsibilities, not approved file paths or implementation classes.

### Frontend boundary

The React/TypeScript frontend owns presentation and interaction state: workbench layout, explorer navigation, structured forms, chat display, Monaco editor state, comparisons, and activity presentation. It may validate basic input shape for usability, but it must not implement V9 planning, retrieval, target-resolution, or semantic-validation logic.

### FastAPI boundary

FastAPI is the transport and application-adapter layer. It should translate typed requests into calls to established V9 functions and translate V9 results and domain errors into stable, structured responses. It must not scrape CLI output or reproduce the old FYP intent parser.

### V9 boundary

V9 remains the source of truth for AI planning, retrieval, clarification, validation, rendering, and related session behavior. Any adaptations needed for GUI use should preserve CLI behavior and be placed behind shared application functions where feasible.

### Inventory boundary

The demo inventory is the initial inventory authority. Iteration 0 selects the existing `data/inventory/devices.json` as the proposed shared persisted source, with validated atomic CRUD writes and revision checks in a new local repository. V9's existing loader continues reading that file. No FYP schema or second mirrored inventory is proposed. Concurrent external writers, deletion references and stale sessions require implementation verification before CRUD is enabled.

### Artifact boundary

A generated artifact is an immutable record of V9 output for a specific plan task and target. A working draft is a separate user-editable derivative with an explicit relationship to that original. Saving a draft must not silently overwrite the generated source.

### External integration boundaries

Deferred external systems must eventually connect through replaceable ports/adapters with explicit configuration and error handling. The demo must not hide live integrations behind mocks or commit to vendor SDKs before the relevant iteration is authorized.

## Boundary and safety rules

- Stable identifiers, structured status, and typed errors cross the HTTP boundary; terminal formatting does not.
- The browser never becomes the authoritative planning engine or inventory source.
- V9 domain behavior should remain callable independently of FastAPI so the CLI remains useful.
- Persistence must distinguish synthetic current-session data from samples and replays.
- No local demo action may silently fall through to a live device or external service.
- Existing FYP code is reused only when its behavior, dependencies, security posture, tests, and architectural fit are understood.

## Iteration 0 design outcome and remaining verification

The detailed design proposes a new `frontend/` at the V9 root and a later isolated `app/workbench/` FastAPI package, React Context/reducer state, and explicit mock/local-V9/replay provenance. These directories are proposed additions, not newly existing implementation.

Saved-session GET must read stored JSON without V9's refreshing `load_session`; explicit resume revalidates and may regenerate configurations. Session concurrency uses a proposed saved-content hash alongside existing task/question/source revisions. Original artifacts and drafts receive separate identities and local stores outside knowledge data/releases.

Implementation must verify concurrency and recovery, inventory reference/staleness behavior, worker ContextVar handling, local Monaco assets and document lifecycle, and the compatibility of selected dependency versions. The current engine does not validate arbitrary edited configuration text. Historical test failures and local AI/RAG readiness remain unverified. These limits are tracked in the integration design; they are not authorization for extra work during Iteration 1.
