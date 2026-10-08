# Iteration 2 Handover — Read-Only FastAPI Service Boundary and Frontend Connectivity

**Date:** 2026-10-08
**Status:** Completed

## 1. Objective and completion status

Iteration 2 delivered one independently testable workflow: the React workbench can detect the local FastAPI service and display its actual passive V9 runtime authority, while remaining usable when that service is unavailable. No V9 planning or session operation is exposed.

## 2. Backend entry point and routes

Entry point: `app.workbench.api:app`, launched with Uvicorn from the V9 repository root.

| Method and route | Model | Behavior |
|---|---|---|
| `GET /api/v1/health` | `HealthResponse` | Confirms only that the HTTP composition is serving requests. |
| `GET /api/v1/runtime/status` | `RuntimeStatusResponse` | Reads existing V9 runtime mode, authoring authority and active release pointer. It does not contact Ollama, load Chroma, ingest knowledge or create/refresh a session. |

Development CORS permits `http://127.0.0.1:5173` and `http://localhost:5173` by default. `NETWORK_RAG_CORS_ORIGINS` can replace that comma-separated list. Only read-only GET methods are allowed.

## 3. Response models and authority semantics

`HealthResponse` contains `status: ok`, the fixed local service name and API version 1.

`RuntimeStatusResponse` contains:

- `service: ready` for the adapter itself.
- `knowledge.status`, configured `files | published` mode, effective `direct_files | published_release` authority, independent `json | sqlite` authoring authority, the actual active release ID when published, and a bounded error code when authority cannot be resolved.
- Separate LLM, embedding and retrieval records. Every one is `not_checked`; configured model names are informational and do not claim availability.

Direct-file mode always returns a null active release ID. Published mode returns the ID from the validated active pointer or `MISSING_ACTIVE_RELEASE`. No source revision is computed and no release is created or refreshed.

Observed against the current checkout: runtime mode `files`, effective authority `direct_files`, authoring authority `sqlite`, no active release ID, and LLM/embeddings/retrieval all `not_checked`.

## 4. Frontend API client and states

`frontend/src/services/runtimeApi.ts` defines the transport types and reads both endpoints. Its base URL is `VITE_API_BASE_URL` or relative `/api/v1`. The Vite development proxy target is configurable with `VITE_DEV_API_TARGET` and defaults to local port 8000.

`frontend/src/features/connectivity/useBackendStatus.ts` exposes:

- `loading` while the bounded request is pending;
- `connected` with the typed runtime snapshot;
- `disconnected` for transport failure/timeouts;
- `error` for unsuccessful HTTP responses;
- `retry()` after failure.

The existing status bar presents the result and effective authority. Monaco, sample inventory, activity and mock chat do not depend on API success. Chat labels explicitly state that messages are not sent to the status API, FastAPI, V9 or a model.

## 5. Files added and modified

Added:

- `app/workbench/__init__.py`
- `app/workbench/api.py`
- `app/workbench/models.py`
- `app/workbench/runtime_status.py`
- `tests/test_workbench_api.py`
- `frontend/src/services/runtimeApi.ts`
- `frontend/src/features/connectivity/useBackendStatus.ts`
- `app_main_documents/08_ITERATION_2_HANDOVER.md`

Modified:

- `requirements.txt`
- `frontend/vite.config.ts`
- `frontend/playwright.config.ts`
- `frontend/README.md`
- `frontend/src/components/layout/StatusBar.tsx`
- `frontend/src/components/layout/WorkbenchLayout.tsx`
- `frontend/src/features/chat/ChatPanel.tsx`
- `frontend/src/app/workbenchReducer.ts`
- `frontend/src/fixtures/workbenchDemo.ts`
- `frontend/src/styles/workbench.css`
- `frontend/tests/workbench.spec.ts`
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`
- `app_main_documents/04_ARCHITECTURE_DECISIONS.md`

No files were removed. No V9 planner, session, retrieval, inventory, catalog, template, SQLite or published-release file was modified for this iteration.

## 6. Dependencies

Backend requirements now explicitly include FastAPI `>=0.115,<1`, Uvicorn `>=0.30,<1` and HTTPX `>=0.27,<1`. No frontend dependency was added. An initial check mistakenly used global Python and installed FastAPI 0.142.4/Starlette 1.7.0 there; final verification and all maintained commands use the project venv below.

The authoritative project environment is `C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv` (Python 3.13.11). A no-index dry run confirmed every declaration in `requirements.txt` is installed there, and `pip check` reported no broken requirements. Relevant venv versions are FastAPI 0.141.1, Starlette 1.6.0, Uvicorn 0.52.4, HTTPX 0.28.1 and Pydantic 2.13.5.

## 7. Verification commands and results

From the V9 repository root:

```powershell
$projectPython = 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe'
& $projectPython -m unittest tests.test_workbench_api -v
& $projectPython main.py --help
```

Results: 4/4 focused backend contract/authority/CORS tests passed in the workspace `.venv` (Python 3.13.11). CLI help retained its planning, resume, interactive, verbose and edit options. The environment prints an existing stale Miniconda-location warning while still resolving the venv interpreter correctly.

Real HTTP verification used:

```powershell
$projectPython = 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe'
& $projectPython -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/runtime/status
```

Both routes returned HTTP 200 from Uvicorn with the authority values recorded above. The unit suite validates registered route models/methods and authority behavior directly, while the browser suite and PowerShell requests exercise the real HTTP process.

From `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e -- --reporter=line
```

Results: lint passed; the production build passed with 2,315 transformed modules and the existing greater-than-500-kB Monaco chunk warning; Playwright passed 3/3 tests. The browser suite starts real Uvicorn and Vite processes, verifies connected direct-file authority, preserves the Iteration 1 editor/explorer/chat/resizing behavior, and simulates backend unavailability while confirming retry and continued Monaco/mock-chat use.

The connected and stopped-backend states were also visually inspected in the in-app browser. The status bar visibly changed from `Backend connected · Direct files` / `AI not checked` to `Backend error (HTTP 500)` / `Retry`, while the other workbench regions remained rendered.

## 8. Running both services

Backend PowerShell:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2'
$projectPython = 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe'
& $projectPython -m pip install -r requirements.txt
& $projectPython -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
```

Frontend PowerShell:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. Stop either server with `Ctrl+C`.

## 9. Known limitations

- Status requests intentionally do not prove Ollama/model availability, embedding availability, Chroma/index state, catalog consistency or source freshness.
- Connectivity is checked on initial load and explicit retry, not continuously polled.
- A stopped backend reached through Vite's development proxy appears as an HTTP 500 error; direct deployments may present it as a transport-disconnected state. Both are explicit recoverable UI states.
- The service exposes no inventory, session, plan, clarification, configuration or draft endpoint.
- API authentication is absent because the milestone remains local/demo-only.
- The existing Monaco bundle-size warning and low inherited DOMPurify advisories remain unchanged from Iteration 1.

## 10. Recommended exact Iteration 3

**Iteration 3 — Read-Only Shared Demo Inventory:** expose only typed `GET /api/v1/inventory/devices` and `GET /api/v1/inventory/devices/{device_id}` responses backed by the existing uncached `load_inventory()` source, including a content-derived inventory revision and explicit synthetic provenance. Replace the explorer's device-list fixture with this read-only data while retaining honest loading/error/sample fallback presentation.

Acceptance should cover exact V9 field mapping, frontend selection, API-unavailable behavior, revision stability/change detection and existing Monaco/mock-chat regression. Do not add inventory writes, AI sessions, target planning, NetBox, device connectivity or artifact persistence in the same iteration.
