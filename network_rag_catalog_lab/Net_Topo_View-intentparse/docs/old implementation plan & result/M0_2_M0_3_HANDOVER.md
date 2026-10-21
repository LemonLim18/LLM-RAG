# CogniShield M0.2 + M0.3 local workflow restoration

## 2026-10-11 Studio generation continuation

Completed the requested authoring-path correction. The original chat preview/parameter modal, reference comparison, confirmation and Monaco workflow are reused; local chat no longer intercepts every authoring request. Original intent parsing, vendor references and validation remain in place. Local Ollama is selected at the provider boundary using `COGNISHIELD_LOCAL_OLLAMA_URL` and `COGNISHIELD_LOCAL_OLLAMA_MODEL`; normal-mode adapters remain unchanged. Simple supported intents still use the original deterministic parser/reference renderer, so the VLAN example does not itself demonstrate model inference.

- `backend/local_providers/studio.py` supplies the original engine's provider/builder and SQLite artifact bridge. `local_app.py` mounts only preview/generation/reference/result routes and maps generated virtual file paths into existing authoring revisions. Approved-artifact locks are retained. No new tables or migrations.
- `backend/ansible/api.py` persists local generated artifacts through that bridge and prevents inventory reconciliation and remote dry-run. Original structural/safety validation runs; native Ansible controller lint/check execution is not claimed. Remote run/deploy remains blocked.
- `frontend/components/ansible/AnsibleChatPanel.tsx` sends authoring requests through the original modal flow while explanation requests remain real local chat.
- `DeviceStatusDot.tsx` recognizes `up` as online; the backup provider already returned `up`, which the former indicator did not recognize.

Verification:
- `backend/.venv-m0/Scripts/python.exe studio_generation_smoke.py`: passed with temporary SQLite: preview, vendor-correct VLAN generation, generated YAML read/edit, Markdown save, application lifespan restart/reopen and blocked execution. Initial sandboxed run stalled and was stopped; authorized local run passed. No user inventory was changed by this script.
- A direct call through `local_providers.studio.provider('qwen2.5:1.5b')` returned `connected` from actual Ollama inference.
- `npm run build`: passed (3936 modules); existing CSS/chunk-size warnings only. No broad test suite or lint rerun.
- Browser: requested VLAN 10 / Art / R1; original preview and editable parameters appeared; Confirm & generate showed reference/generated comparison; Confirm & use opened Job 3 in Monaco. Saved `# Local authoring verification`, reopened it from the tree, and opened `preview_modal_dialog.md` with the actual preview trace. Job 3 and its draft artifacts are retained; no deployment or approval decision was performed. Existing unrelated unsaved editor content was preserved.
- Browser: Config Backup R1's indicator has `bg-success` (green). Existing historical short snapshots remain unchanged.
- Detached backend processes stopped during the interrupted session; a retained `run_environment.py` terminal session restored connectivity. One Windows socket error occurred during the earlier attempt. No infrastructure rewrite was made.

Limits: this is representative authoring verification, not an exhaustive vendor/model matrix. Original remote check/deploy remains unavailable; the Studio job inventory subpanel route is still not mounted locally. Model output quality depends on the installed model. Earlier handover limitations for other modules remain as recorded below.

Editable fixture inventory: `backend/simulation/README.md` lists every active JSON input and its schema. All data files remain in `backend/simulation/`; `observations.before-split.json` is recovery-only and is not read by the app. No fixture shape changes were needed in this continuation.

## 2026-10-11 requested provider fixes — latest result

Implementation is installed and the backend is running in local mode. **Full GUI acceptance remains INCOMPLETE**: browser control became unavailable after the interrupted walkthrough. No further browser troubleshooting or broad test run was performed.

### Implemented

- ZTP credential routes reuse the encrypted `device_credentials` vault. Onboarding credential inputs/save/test are enabled. Syslog/NTP tests validate the saved effective profile and return explicit simulated results; no remote packets or SSH calls occur.
- Operational topology and backup selection use `availability.json` device `status: active/inactive`. Planned topology retains every stored device. Inactive endpoints are removed from operational adjacency as well as nodes. The original Real-Time and Diff controls are enabled.
- Central `backend/simulation/` contains separate availability, syslog, alerts, and `metrics/1h.json`, `6h.json`, `24h.json` inputs, plus matching schemas. New devices inherit constant metrics and uptime. Existing API response fields are preserved. See `backend/simulation/README.md` for paths and editing examples. Original observations were preserved as `observations.before-split.json`.
- `configurations/device-<id>.json` supplies each device's current configuration. Initial configs include interfaces, routing, logging, NTP and management settings. Capture reads the file into the existing SQLite snapshots. Successful restore captures a safety snapshot, replaces the JSON configuration atomically and records the attempt; failed outcomes preserve it. Existing historical snapshots are untouched, so old short sample snapshots remain short.
- Local Ollama requests bypass proxy environment settings, discover installed chat models and support model selection, Studio chat, approval summary/Q&A and snapshot AI Suggest. Responses are real inference. Review scores use the existing GUI's 0–10 scale. Missing/invalid model output remains an error, not a fabricated rating.
- Approval Preview reads actual persisted request descriptions/job content when no Ansible job link exists. It no longer reports that every such request has nothing to preview. Existing historical sample requests are retained, not rewritten or approved automatically. Approved local requests explicitly do not imply deployment.
- Template Studio's right variables/preview sidebar was removed as requested. Its periodic refresh retains the populated explorer and expanded-folder state. Template authoring/revisions are retained; render APIs remain available, but the removed sidebar's render controls are no longer visible.
- The banner is replaced by a navbar environment toggle. Admin selection updates only `COGNISHIELD_MODE` in root `.env`. `backend/run_local.ps1` launches `run_environment.py`, which restarts the existing backend composition on mode changes. Windows worker trees are stopped together to release port 8000. Direct uvicorn runs instead report that a manual restart is needed. Actual-mode startup has NOT been tested against the unavailable infrastructure. Its dependencies must be installed separately; failed actual startup does not fall back to simulation. Recovery: set `COGNISHIELD_MODE=local_lab` in root `.env`.

No new database/table/migration, dependency upgrade, automatic commit, V9 change or user-data deletion was performed. Active SQLite is `backend/db/m0_2_m0_3_browser_smoke.db` despite its historical name; it is user data.

### Actual verification

- `backend/.venv-m0/Scripts/python.exe -m pytest tests/test_m0_2_m0_3_workflows.py tests/test_m0_1_providers.py -q -o faulthandler_timeout=30`: **6 passed**. Sandboxed run stalled; rerun outside the sandbox completed. Existing Starlette deprecation warning retained.
- `tests/test_local_provider_controls.py`: credential/profile check passed; fixture/restore check initially had an invalid test-device payload missing the required subnet mask. Corrected the test payload and reran only that test: **passed**. Total **8 distinct focused checks passed**, including JSON refresh/ranges, inactive topology, reference rejection, edited configuration capture, successful JSON restore and failed-restore preservation. Tests used temporary SQLite/fixtures and prohibited remote connections/process execution.
- `npm run build`: **passed**, 3936 modules, inherited CSS/chunk-size warnings. Initial unused icons after panel removal were corrected; Vite's sandbox EPERM required an outside-sandbox build. Two subsequent presentation-only string changes (approval wording and syslog help path) were not followed by another production build.
- Browser: inventory refreshed to R1/R2; Onboarding rendered with credential/test controls; navbar toggle present and banner absent. Studio listed `qwen2.5:1.5b` and returned a real NTP explanation. Approval Preview displayed saved request content, AI Summary returned ratings/explanation, and Q&A returned an actual model response. Model answers remain advisory and can be inaccurate.
- Browser Performance: 2/2 devices up, 4/4 interfaces up, CPU 26%, memory 44%, populated traffic/error/discard/packet charts, interface rows, uptime, risk scores and calculated alerts. Syslog was observed before its delayed fetch completed; subsequent server/API verification confirmed **4 events**, not an empty fixture.
- Final API checks: topology **2 nodes**, backup selection **2 devices**, environment active/selected `local_lab`, automatic restart enabled. After controlled restart, SQLite retained **2 devices / 3 existing snapshots**. Backup AI Suggest returned HTTP 200 from `qwen2.5:1.5b` with a 497-character description; no description was saved or snapshot modified by that check.

### Remaining manual GUI checks

1. Save your ZTP credentials, reload, and verify the configured username/status; run simulated connection, Syslog and NTP tests against saved profile values.
2. In Real-Time topology, change a device's `status` in `backend/simulation/availability.json`; refresh and confirm it hides/shows in topology and backup selection, while Planned retains it.
3. Select 1h/6h/24h; edit one range's device metrics and refresh. Verify Syslog after its delayed load or Refresh Logs.
4. Edit one device configuration JSON, capture, view/diff, use AI Suggest and save its description. Restore an earlier snapshot and inspect the configuration JSON. Do this with a disposable device if preserving your current mock configuration is important.
5. Open Template Studio and confirm the right panel is absent and expanded vendor folders remain steady during background refresh.
6. Actual-environment switching and return remain unverified; test only when the original remote services and normal-mode dependencies are available. Existing local editor Send for Approval still retains its earlier job/check prerequisites; this increment does not replace that pipeline.

Stopped after the requested fixes and bounded verification. The older sections below are historical and are superseded where they describe single-file observations, disabled AI, or SQLite-only simulated running configuration.

Verified on 2026-10-10 in `network_rag_catalog_lab/Net_Topo_View-intentparse`. This increment retains the M0/M0.1 local startup, SQLite authority, JSON observation provider, authoring revisions and normal-mode adapters. It does not touch the sibling V9 repository, enable remote execution, integrate V9, or redesign the frontend.

## Preserved behavior and corrected local deviations

The original route shell and pages remain in use: `App.tsx`, `Sidebar.tsx`, `OnboardingView.tsx`, `ConfigBackupView.tsx`, `AnsibleStudioView.tsx`, the existing Profile, Approval, policy, Dashboard, Topology, Performance and Syslog views. M0.1 had correctly kept their read-only/state display paths but left several original workflows unavailable in local mode. This increment restores their local service connections without restoring any remote adapter.

| Existing GUI workflow | Local path now used | Result |
| --- | --- | --- |
| Onboard Device | existing view → `/onboarding/*` → original rendering plus `AuthoringStore` overlay → SQLite | Selects planned SQLite inventory; profile values and effective saved template revisions influence genuine Day-0 render; edits persist as overrides; fixture controls the ZTP staging outcome. No DHCP/TFTP/SSH/provisioning is performed. |
| Global Service Profiles | existing Profile UI → `common_services` routes → `common_service_profiles` | Existing validation and assignment semantics are reused; profile values supply Day-0 parameters. |
| Config Backup | existing backup modal/history/diff UI → existing snapshot routes plus local capture/restore routes → `config_snapshots` | Capture writes a real snapshot, diff/history/download keep using existing services, and restore records a simulated attempt. Successful restore changes only local simulated device configuration; a fixture failure leaves it unchanged. |
| Ansible Studio and Template Studio | existing explorer/editor/tabs → config/Ansible APIs → `authoring_revisions` | Local file/template authoring and recoverable revisions remain available. Baseline repository files remain protected. AI generation and remote execution stay unavailable. Template Studio remains free of the optional Git-status error fixed in M0.1. |
| Approval Queue | existing queue UI → original `deploy.approval` routes and `ChangeRequestService` → `change_requests` and audit | Requests are created, submitted, approved/rejected through original state transitions and audit behavior. Approval never marks a deployment as executed. |
| Policies / compliance | existing policies and result routes → `ComplianceEvaluator` → stored snapshots/policies | A supported policy is evaluated against stored configuration and result/history are persisted. Rules without suitable stored or simulated evidence remain honestly limited. |
| Dashboard / Topology / Performance / Syslog | existing views → M0.1 observation routes → SQLite inventory + `observations.json` | Inventory and topology shape stay authoritative SQLite; fixture supplies stable operational overlay, metrics, alerts and events. |

The local Onboard refresh control now refreshes SQLite planned inventory directly instead of attempting a NetBox connection. Credential-status probing is also skipped in local mode. The original normal-mode NetBox path is retained. Capability values in `local_providers/capabilities.py` explicitly enable local workflow UI while keeping SSH, deployment, controller, crawler, NetBox sync, remote Ansible and physical ZTP disabled.

The local-lab shell no longer blocks **Onboard Device** or **Approval Queue** before their existing views can reach these providers. The Dashboard now loads the persisted local approval queue and accurately describes simulated Syslog observations. Local approval confirmation explicitly records that it creates a decision and audit record only; it cannot execute or deploy. The deferred Knowledge, Intent Parser, SDN, playbook comparison, and intent-history pages remain unavailable.

## SQLite and JSON ownership

SQLite remains the sole mutable application authority. The additive migration [m0_2_m0_3_local_workflows.sql](../backend/db/migrations/m0_2_m0_3_local_workflows.sql) adds:

- `simulated_device_configs`: the local simulated running configuration for a known SQLite device, optionally tied to its snapshot.
- `local_workflow_attempts`: append-only local capture, restore and ZTP-publication outcomes.

`local_migrations.py` creates a backup before applying the migration and records its version. Existing `devices`, `interfaces`, `links`, `common_service_profiles`, `config_snapshots`, `authoring_revisions`, change-request, policy and audit tables are reused unchanged.

[workflow_outcomes.json](../backend/simulation/workflow_outcomes.json) is the editable simulated external-outcome fixture. Its contract is documented by [workflow_outcomes.schema.json](../backend/simulation/workflow_outcomes.schema.json) and is validated with strict Pydantic models before use. Set a `device_outcomes` entry for a known SQLite `device_id` to `success` or `failure`, save the file, then perform the existing GUI action again. A malformed fixture or an unknown device reference returns a useful error and does not change inventory or stored configuration. `observations.json` remains the M0.1 fixture for reachability, interface state, performance, alerts and syslog.

For Config Backup, `capture.device_configs` optionally supplies a per-device simulated running configuration. For example:

```json
{
  "device_id": 1,
  "config_text": "hostname {hostname}\\nntp server 192.0.2.77\\n"
}
```

It is substituted into the original capture workflow only for that known SQLite device; the resulting capture, diff, restore attempt and audit remain SQLite records. When no matching entry exists, `capture.default_config` remains the input.

## Provider map

| Concern | Provider | Provenance |
| --- | --- | --- |
| Inventory, topology, profile assignments, snapshots, authoring, approvals, policies, audit | `DatabaseManager` and existing services | `stored` |
| Availability, metrics, traffic, syslog and monitoring events | `JsonObservations` / `observations.json` | `simulated` |
| Capture, ZTP staging and restore responses | `LocalWorkflowProvider` / `workflow_outcomes.json` | `simulated` |
| Day-0 generation, Jinja validation/rendering, configuration diff and policy calculation | existing CogniShield logic | `local_render` / `stored` inputs |

`backend/local_app.py` is deliberately the local composition boundary: it imports neither startup scheduler nor crawler nor remote execution provider. Its local workflow endpoints invoke the existing renderer, snapshot/diff services, change-request state machine, audit logger and evaluator where each is meaningful. `backend/integrated_backend.py` and normal-mode adapters remain preserved for a later selectable real provider.

## Verification

Focused implementation suite was run once after the implementation:

```powershell
Set-Location backend
$env:PYTHONPATH=$PWD
.\.venv-m0\Scripts\python.exe -m pytest tests/test_m0_local.py tests/test_m0_1_providers.py tests/test_m0_2_m0_3_workflows.py tests/unit/test_policy_compliance_engine.py tests/unit/test_compliance_scope_resolver.py -q
```

Result: **16 passed, 1 warning** in 2.51 seconds. The warning is Starlette's inherited TestClient/httpx deprecation notice.

The added focused workflow tests cover effective profile/template Day-0 generation, saved override selection, fixture-controlled ZTP success and failure, capture, snapshot diff, successful and failed restore, Studio revision persistence, approval submission/approval with audit, supported policy evaluation, fixture validation/refresh and remote-execution isolation.

After restoring the local page connections and per-device capture fixture support, `tests/test_m0_2_m0_3_workflows.py -q` passed: **2 passed, 1 inherited TestClient deprecation warning**. `npm run build` also passed. The existing CSS `@property` and large output-chunk warnings remain.

`npm run build` passed after the final frontend change. Vite reported the existing CSS `@property` compatibility warning and its existing large-chunk warning. The inherited lint baseline was not re-run: M0 recorded 546 errors and 35 warnings, and this increment did not change lint configuration.

The complete browser workflow walkthrough remains **partially unverified**. Browser access was restored in the latest continuation; exact results are below. The earlier report that `backend/db/m0_2_m0_3_browser_smoke.db` was removed was incorrect: this file holds the user's R1/R2 lab inventory and is now explicitly selected in `.env`. Preserve it as user data.

### Manual browser verification checklist

For any future remaining verification, use a separately named disposable database. Do not replace or remove `db/m0_2_m0_3_browser_smoke.db`: despite its historical name, it is the current user lab database. The following is a checklist, not a claim that these steps passed:

1. Open **Template Studio**. Confirm it opens without **Git status failed**, edit and save a disposable template, then reopen it and confirm the saved revision is shown.
2. Open **Global Service Profiles**, save an NTP value, then open **Onboard Device**, select the planned device, generate Day-0, and confirm that generated configuration contains the profile NTP value. Edit and save its Day-0 override, stage it with **Publish**, and confirm a `simulated` ZTP outcome with no device-provisioning claim.
3. Open **Config Backup**, capture a snapshot, import or capture a changed version, inspect the existing diff, and restore the selected version. Confirm the result is labelled simulated and that no command/deployment is reported.
4. Open **Ansible Studio**, create a disposable project/file, edit and save it, reload the page, and reopen the file to confirm its stored revision.
5. Create a valid local change request through its supported source, submit it to **Approval Queue**, approve or reject it, and confirm persisted decision/audit history without a deployment status.
6. Add a supported policy and use the existing policy action against stored configuration; confirm the persisted calculated result. Open **Dashboard**, **Topology**, **Performance**, and **Syslog**; confirm inventory shape comes from the SQLite device/interface/link records and displayed operational values carry a simulated source.
7. Edit a valid value in `backend/simulation/observations.json`, use the affected page’s **Refresh** control, and confirm the changed deterministic value appears. Restore the fixture baseline after the check.
8. Restart only the disposable local backend, reload the browser, and confirm the saved Day-0/template/file/snapshot/approval records still appear. Preserve the user's active database and all existing data.

## Remaining limitation and smallest follow-up

Remote operations remain intentionally unavailable in local mode: SSH/device commands, discovery/crawling, NetBox synchronization, DHCP/TFTP ZTP delivery, real provisioning, OpenDaylight actions, remote Ansible execution and real telemetry collection. No fallback converts a failed real provider into fixture data.

The full browser acceptance checklist is not complete. Profile-influenced Day-0/ZTP staging, backup capture/diff/restore, Studio file reopen, approval decisions, policy results and a controlled restart of all workflow records have not been individually demonstrated in this continuation. No M0.4 or V9 work was started.

## Latest continuation: populated local scenarios and actual local chat

The existing observation provider now supplies deterministic device uptime, reachability, interface admin/oper status, CPU/memory, traffic, errors/discards and unicast/multicast/broadcast packet rates. `observations.json` contains 12 timestamped samples, interface defaults, per-inventory-device event templates and calculated thresholds. Explicit device/interface overrides still validate against SQLite inventory. Edit values in this file and refresh the relevant view; timestamps and measurements do not randomize.

`workflow_outcomes.json` remains the editable configuration-response/ZTP/restore input. Configuration capture detects changed fixture text; an unchanged fixture preserves a successful simulated restore's stored running state. Native configuration braces are preserved. Both JSON schema files were updated. A labelled `deployment_history` fixture can be explicitly imported into SQLite history; this records `simulated_success`/`simulated_failed`, `no_op`, and `fixture replay; no execution`, never a real deployment.

From `backend`, `.\.venv-m0\Scripts\python.exe simulation/prepare_local_demo.py` prepares labelled snapshots, pending reviews, a new revision-backed Studio example and fixture history against existing inventory. It creates a timestamped SQLite backup before adding records and does not overwrite inventory or original templates. This command completed against the active R1/R2 database. Existing lab records and backups are preserved.

Non-secret `.env` selection:

```dotenv
COGNISHIELD_MODE=local_lab
COGNISHIELD_OBSERVATION_PROVIDER=json_fixture
COGNISHIELD_DB_PATH=db/m0_2_m0_3_browser_smoke.db
COGNISHIELD_LOCAL_OLLAMA_URL=http://127.0.0.1:11434
COGNISHIELD_LOCAL_OLLAMA_MODEL=auto
```

The restored original AI panel uses the existing Ollama provider through `local_providers/chat.py`, selecting the installed `qwen2.5:1.5b` chat model (embedding models excluded). Chat sessions use the existing SQLite table with authenticated ownership checks. Replies are actual inference, not fixtures. Normal mode continues through the original integrated backend; changing modes requires a backend restart and does not silently fall back from real services to simulation.

Actual verification for these changes:

- Six affected provider/workflow tests passed; frontend build passed with inherited CSS/chunk warnings before this continuation. Neither was rerun merely for reassurance.
- Backend restarted using the explicitly selected R1/R2 database. Existing inventory remained present.
- Browser Performance showed 2/2 devices and interfaces up, populated traffic/error/discard/packet charts, CPU 38%, memory 59%, uptime 10 days, four Syslog events and two calculated alerts.
- Browser Dashboard showed the same two stored devices/interfaces, four fixture Syslog events, two labelled pending reviews, two `simulated_success` history rows with `fixture replay; no execution`, and persisted audit entries.
- Original Studio chat sent `Reply with only: Local chat connected` and received `Local chat connected.` from local Ollama in the browser. No remote execution occurred.
- No additional tests or polishing were performed in this finishing continuation.

Limitations: actual conversational AI is restored, but the old intent-to-job/RAG/Check/approval toolbar pipeline is not replaced by this chat adapter. The editor's Send for Approval remains dependent on the original job/check prerequisites; a plain local file does not satisfy them. Remote actions remain unavailable. Full platform acceptance therefore remains **INCOMPLETE**, even though the observed Dashboard, Performance and local chat paths work. Stop here per the user's bounded continuation request.
