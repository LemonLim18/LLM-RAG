# Iteration 3 Handover — Read-Only Shared Demo Inventory

**Date:** 2026-10-08
**Status:** Completed

## 1. Completion status

Iteration 3 is complete. The infrastructure explorer now reads the actual synthetic V9 inventory through typed FastAPI GET endpoints. The target resolver and API share the same existing `load_inventory()` authority; no second inventory, write path, AI session or infrastructure connection was introduced.

## 2. Backend routes and contracts

| Method and route | Response | Behavior |
|---|---|---|
| `GET /api/v1/inventory/devices` | `InventoryListResponse` | Returns API version, `source: synthetic`, canonical content revision and all safe device projections. |
| `GET /api/v1/inventory/devices/{device_id}` | `InventoryDetailResponse` | Returns the same revision/source plus one stable-ID device. Unknown IDs return HTTP 404 with `DEVICE_NOT_FOUND`, message and requested ID. |

The typed device projection includes stable ID, hostname, kind, display name, aliases, vendor, platform, version, site, role, location, recorded administrative status, tags, interfaces/neighbors and declared capabilities. It deliberately excludes management addresses, Ansible metadata, monitoring labels and external source references.

## 3. Inventory authority and V9 compatibility

`app.devices.inventory.load_inventory()` reads `data/inventory/devices.json` without caching. Both `resolve_queries()` and `resolve_intent_targets()` use this loader when no explicit inventory is provided. `app.workbench.inventory_service` calls the same function and only adapts its returned dictionaries into transport models.

The API revision is SHA-256 over a stable canonical serialization of the records returned by that loader. It detects logical record changes without treating JSON whitespace as an inventory change.

Automated parity checks confirmed the API exposes exactly the IDs returned by `load_inventory()`, including:

- `dev-r1`: R1 / Cisco
- `dev-r2`: R2 / Huawei
- `dev-r3`: R3 / Juniper

The current source contains six devices: R1, R2, R3, SW1, SW2 and SW3.

For the future authorized inventory-editing workflow, validation and atomic replacement must target the same `data/inventory/devices.json` file with an expected revision. Because both the API and target resolver perform ordinary uncached reads through `load_inventory()`, a valid newly registered device becomes visible to both without a mirror, synchronization job or second database. Reference integrity, backups, writer coordination and stale-session handling must be implemented and tested before writes are enabled.

## 4. Frontend changes

- `inventoryApi.ts` defines the single frontend inventory model and typed list request.
- `WorkbenchProvider` loads inventory with a five-second bound and provides explicit retry.
- The reducer owns only shared inventory load state, API devices and selected ID in addition to its existing shell state.
- `ExplorerPanel` presents loading, six-device ready, empty, filtered-empty and API-error states; selection details show actual platform/version/location, interface/capability counts and tags.
- The old device fixture no longer initializes the explorer. Monaco configuration examples remain separate fixtures with their own device display snapshot.
- Selecting R1, R2, R3 or SW1 activates the matching sample tab. SW2/SW3 remain selectable but do not invent configuration content.
- When inventory is unavailable, the explorer shows Retry while Monaco, existing tabs, layout and mock chat continue working.

## 5. Exact files changed

Added:

- `app/workbench/inventory_service.py`
- `frontend/src/services/inventoryApi.ts`
- `app_main_documents/09_ITERATION_3_HANDOVER.md`

Modified:

- `app/workbench/api.py`
- `app/workbench/models.py`
- `tests/test_workbench_api.py`
- `frontend/src/services/runtimeApi.ts`
- `frontend/src/app/types.ts`
- `frontend/src/app/WorkbenchProvider.tsx`
- `frontend/src/app/workbenchReducer.ts`
- `frontend/src/fixtures/workbenchDemo.ts`
- `frontend/src/features/explorer/ExplorerPanel.tsx`
- `frontend/src/features/workspace/ConfigurationEditor.tsx`
- `frontend/src/components/layout/StatusBar.tsx`
- `frontend/src/styles/workbench.css`
- `frontend/tests/workbench.spec.ts`
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`
- `app_main_documents/04_ARCHITECTURE_DECISIONS.md`

No files were removed. No dependency was added. The inventory JSON, target resolver, V9 planner/session code, catalog, SQLite data and published releases were not modified.

## 6. Verification and outcomes

All Python commands used the required workspace venv:

```powershell
$projectPython = 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe'
& $projectPython -m unittest tests.test_workbench_api -v
& $projectPython main.py --help
```

Results: 8/8 backend tests passed. They cover the existing health/runtime contracts, typed inventory routes, exact API/loader identity parity, R1/R2/R3 vendor parity, safe-field projection, known-device detail and unknown-device distinction. CLI help exited 0 with its existing options. The venv still prints the known stale Miniconda-location warning but resolves the required Python 3.13 interpreter.

Frontend verification from `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e -- --reporter=line
```

Results: lint passed; production build passed with 2,316 transformed modules and the pre-existing large Monaco chunk warning; Playwright passed 3/3 tests. Browser coverage includes real inventory list/detail/404 HTTP behavior, six-device explorer rendering, R1 parity, actual R3 metadata, Huawei filtering, Monaco edit/tab retention, mock chat, panel resizing, compact viewport and full API unavailability.

Visual inspection in the local browser confirmed six API devices, revision label, R1 real metadata/tags, existing Monaco content, connected runtime status and the Iteration 3 label.

## 7. Manual verification

Backend PowerShell:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2'
$projectPython = 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe'
& $projectPython -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
```

Frontend PowerShell:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm.cmd run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. Confirm six devices, select R3, filter for `huawei`, then stop the backend and reload to see the inventory retry state without losing Monaco.

Direct API checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/inventory/devices
Invoke-RestMethod http://127.0.0.1:8000/api/v1/inventory/devices/dev-r1
```

## 8. Known limitations

- Inventory is read-only; there is no create, update or delete route.
- The frontend fetches the list on initial load or explicit retry; it does not poll for out-of-band file changes.
- The list response intentionally carries the details needed by this small local explorer, so the explorer does not issue a second detail request after selection.
- Only four of six devices have sample Monaco documents. Selecting SW2 or SW3 keeps the current sample editor tab rather than fabricating configuration.
- Administrative `status` is recorded inventory data, not observed device connectivity. No live status is displayed.
- Revision is derived from logical loaded records, not exact file bytes; whitespace-only edits do not change it.

## 9. Recommended next single iteration

**Iteration 4 — Structured V9 Planning Session Creation:** expose only one typed session-creation operation backed by the existing V9 `create_session` application function, preserve all returned task/question/evidence identifiers, and connect one clearly labelled real-V9 prompt submission path in the chat. Include bounded unavailable/error handling and retain the current mock path as explicitly separate.

Do not include clarification answers, corrections, session resume, inventory writes, artifact persistence or device execution in the same iteration.
