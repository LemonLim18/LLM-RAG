# M4 Knowledge Engineering integration — 2026-10-13

## Outcome and scope

The senior-authoring to junior-generation acceptance scenario was demonstrated through the existing GUI in an isolated environment. The authoritative engine remains the sibling V9 KnowledgeManagementService, SQLite authoring store, schema compiler, publisher, immutable KnowledgeSnapshot, and release-specific Chroma retrieval. CogniShield hosts adapters and an owned workspace; the sibling repository is read-only.

Runtime output is currently supported for **one operation, one stored Cisco IOS-XE target, and a declared compatible template version**. Knowledge management supports V9's vendor/platform/version bindings; successful runtime generation for other vendors, multiple tasks/devices, or actual network execution is not claimed. These are remaining extensions, not simulated successes.

## Connected workflow

1. Global Parameters stores reusable type/interpretation definitions and validated optional default/constraint presets in the V9 authoring records. Invalid JSON cannot silently save an older preset value.
2. Categories assigns existing parameters to the category pool. Operations selects that pool, sets required/optional mappings, and saves operation-specific rules. **Apply Global Preset** explicitly copies a preset into the selected operation contract; changing a global preset does not silently rewrite existing contracts.
3. The compiler generates the operation schema. Engineers do not hand-author schema documents.
4. Template Management saves Jinja2 assets and vendor/platform/version bindings using the existing Monaco editor. Render Preview validates the supplied parameters against the compiled schema and renders native configuration. Backend errors remain visible.
5. Validation checks the saved authoring catalog. Build creates a verified immutable package and index while preserving the active pointer. Publish builds and activates; an administrator can separately activate an available release or restore a previous valid release from Release History. Activation uses expected-release conflict checks and verifies frozen package/index contents before switching the pointer atomically.
6. Studio reads the active published snapshot. Its original interpretation/clarification/review/generation/file/Monaco workflow remains. Native configuration comes from the published Jinja template; the generated Ansible wrapper uses `cisco.ios.ios_config` with `src: native_config.txt` rather than reconstructing VLAN commands independently.
7. Studio jobs, native text, YAML, review Markdown, preview-dialog Markdown, session ownership and audit records persist through the existing application SQLite mechanisms.

JSON Schema `default` is an annotation and preview convenience; it does not itself inject missing runtime values. Required values still follow V9 clarification. Templates needing runtime-derived inventory context are directed to Studio rather than receiving a fabricated authoring preview.

## Verification evidence

All paths below are relative to the CogniShield repository. Test artifacts contain isolated data. The real user database `backend/db/m0_2_m0_3_browser_smoke.db`, default knowledge workspace, and user active release were not used for these mutations.

| Check | Actual result |
| --- | --- |
| Senior GUI authoring | Created `lab_label` string with length 1–24 and uppercase pattern, assigned it to VLAN, required it in `create_vlan`, applied constraints, and saved Cisco IOS-XE 17.9 template through Monaco. |
| Persistence and draft isolation | Actual backend process restart preserved records/schema/template. Unpublished changes were absent from runtime. `tmp/m4/before-restart.json`, `draft-isolation.json`. |
| Template preview | `CAMPUS` rendered; lowercase `campus` was rejected with HTTP 422. |
| Build/publish/activate GUI | Validation, build-only, frozen package inspection and explicit activation succeeded. First build failed while Ollama was stopped and left the active pointer unchanged. |
| Literal junior GUI request | `Create VLAN 240 on M4-SW1` requested the new required label; confirmation generated Job 1 and opened the native result in Monaco. |
| RAG/LLM junior GUI request | `Set up a new VLAN 241 on M4-SW1` used the published Chroma candidates and four actual local Qwen calls, requested operation confirmation and the new label, then generated Job 2 through the original dialogs and Monaco. `tmp/m4/rag-preview.json`, `studio-rag-result.jpg`. |
| Saved artifact verification | Both jobs identify the active immutable release; exact native text and matching Ansible wrapper, four saved files per job, pending status and audit rows were checked directly in isolated SQLite. `tmp/m4/acceptance-results.json`. |
| Negative/lifecycle tests | Invalid preset range, deleting a published parameter, unknown category membership, unbound template input, stale activation, missing release and unsupported IOS-XE 99.1 were rejected. Rollback switched the runtime schema while preserving draft revision, then restored the test release. `tmp/m4/lifecycle-results.json`. |
| New identities | `backend/tests/test_knowledge_management_creation.py` passed creation of a new category, parameter, mapping, operation and variant, generated constraints, overlap rejection, Chroma publication and Studio generation of `lab 5`. This complements the GUI modification of the existing VLAN operation. |
| Permanent lifecycle regression | Extended `backend/tests/test_knowledge_authoring.py` passed validated render, build-only isolation, frozen inspection, stale activation rejection, activation/rollback, draft isolation, admin publication, Studio consumption, audit and persistence. |
| Studio regression | `backend/tests/test_v9_studio_bridge.py` passed clarification/correction/range checks, native and Ansible artifacts, owner checks, audit, persistence, multi-task rejection and blocked local execution. |
| Input guard | Browser attempt to save malformed default JSON was blocked with native validation and an error message; the edit was cancelled. |
| Frontend | Final TypeScript + Vite production build passed: 3947 modules, 63 seconds. Existing CSS `@property` and large-chunk warnings remain. Sandbox denied configuration access; the authorized build succeeded. |
| Whitespace | Scoped diff check passes with `git -c core.whitespace=cr-at-eol diff --check`; existing CRLF files were retained rather than reformatted solely to suppress Windows line-ending warnings. |

Published test release: `3ee58ee401954856a53cc2ceb71aae1c`. Baseline/rollback release: `428e4a0588dc4d078e4ee1c68da0d051`.

Job 2 native result:

```text
vlan 241
 name CAMPUS
! M4 senior-authored campus configuration
```

The saved screenshot includes an earlier failed request using an unavailable old model. Reload discovered installed `qwen2.5:1.5b`; the subsequent request succeeded. This is recorded rather than hidden or represented as uninterrupted service availability.

## Source map

- `backend/local_providers/knowledge.py`: authenticated management, render, build, inspection and activation APIs.
- `backend/local_providers/knowledge_worker.py`: read-only V9 import and owned authoring workspace adapter.
- `backend/local_providers/knowledge_lifecycle.py`: V9 publication staging, verified activation/history, presets and preview.
- `backend/local_providers/v9_worker.py`: active snapshot, original interpretation/RAG/schema/render pipeline.
- `backend/local_providers/v9_studio.py`: existing Studio contract, corrections, SQLite persistence, native artifact and Ansible wrapper.
- `frontend/src/services/api.ts`: API entry points.
- `frontend/views/KnowledgeEngineeringView.tsx`: live authoring state and mutations.
- `frontend/views/knowledge/{KnowledgeLayouts,LatestLayouts}.tsx`: existing forms, Monaco, persistent errors and lifecycle controls.
- `backend/tests/test_knowledge_{authoring,management_creation}.py`, `test_v9_studio_bridge.py`: isolated regression entry points.

## Run and continue

Isolated environment: frontend `http://127.0.0.1:5175`, backend `http://127.0.0.1:8001`, application DB `tmp/m4/app.db`, knowledge `tmp/m4/k`, fixtures `tmp/m4/fixtures`. Backend runner: `backend/.venv-m0/Scripts/python.exe tmp/m4/serve.py` from repository root. Frontend uses `VITE_API_URL=http://127.0.0.1:8001` and `VITE_WS_URL=ws://127.0.0.1:8001`. These test settings do not replace the user's `.env`.

Ollama must be running with a chat model (verified `qwen2.5:1.5b`) and embedding model (verified `nomic-embed-text`). `.env.example` documents `COGNISHIELD_KNOWLEDGE_EMBED_MODEL`. `COGNISHIELD_STUDIO_ENGINE=v9` applies to local mode; `original` retains the old local adapter. Normal mode remains on its established adapter and was not tested against remote infrastructure.

Standalone backend checks run from the repository root:

```powershell
backend/.venv-m0/Scripts/python.exe backend/tests/test_knowledge_authoring.py
backend/.venv-m0/Scripts/python.exe backend/tests/test_knowledge_management_creation.py
backend/.venv-m0/Scripts/python.exe backend/tests/test_v9_studio_bridge.py
```

They require the configured V9 Python environment and installed local Ollama models; they do not mock model/index success. No automatic commit or network deployment was performed. Next functional expansion should be a separately verified runtime adapter for another vendor/platform or multi-target request, not a rewrite of this working authoring/publication chain.

Final service check after interruption recovery: frontend 5175, backend 8001 and Ollama 11434 returned HTTP 200. The initial sandboxed regression rerun could not complete under local socket restrictions; the authorized isolated run passed.
