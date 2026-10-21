# CogniShield M0.1 local simulation foundation

Verified on 2026-10-10 in `network_rag_catalog_lab/Net_Topo_View-intentparse`. This increment builds on M0. It does not modify the sibling V9 repository, integrate V9, introduce Knowledge Management, delete legacy code, or make remote execution available.

## Result

Local mode now has three explicit providers behind stable HTTP contracts:

| Concern | Provider | Authority | Source label |
| --- | --- | --- | --- |
| Inventory topology | SQLite (`DatabaseManager`) | `devices`, `interfaces`, `links` | `stored` / `stored_inventory` |
| Operational observations | editable `backend/simulation/observations.json` | Fixture v1, validated against SQLite inventory | `simulated` |
| Template and Studio authoring | SQLite revision overlay | `authoring_revisions`, with original source files as read-only baselines | `stored` |

The local app still starts no scheduler, crawler, NetBox synchronization, SDN controller, SSH session, device command, remote Ansible runner, telemetry collector, AI pipeline, or deployment service. `/api/v1/lab/capabilities` is the central capability contract. The frontend reads that contract through `LabContext` / `useCapability`; local-mode conditions are not scattered across pages.

`COGNISHIELD_OBSERVATION_PROVIDER=json_fixture` and the optional `COGNISHIELD_FIXTURE_DIR` are documented in [.env.example](../.env.example). `lab_config.py` rejects any non-fixture observation provider in `local_lab`, instead of falling back through connection timeouts.

## GUI, API, provider and storage map

The route shell remains [App.tsx](../frontend/src/App.tsx), the original navigation remains [Sidebar.tsx](../frontend/components/Sidebar.tsx), and client contracts remain in [api.ts](../frontend/src/services/api.ts).

| Page | Client / endpoint | M0.1 data path | Local contract |
| --- | --- | --- | --- |
| Dashboard | `dashboardApi`, `/dashboard/summary` | SQLite inventory + JSON summary overlay | Stored counts plus clearly labelled simulated status; no discovery |
| Global Service Profiles | `commonServicesApi`, `/common-services/*` | existing `common_service_profiles` SQLite table | Existing local profile CRUD; remote test calls remain unavailable |
| Device Inventory | `netboxApi`, `/netbox/devices`, interfaces and links | existing SQLite inventory tables and integrity checks | Full M0 stored CRUD; no NetBox sync |
| Onboard Device | `onboardingApi`, `/onboarding/*` | existing onboarding validators/state definitions | Page remains an honest unavailable workflow pending M0.2 local registration wiring; no SSH/ZTP claim |
| Topology Map | `topologyApi`, `/topology`, `/netbox/topology/planned/local` | SQLite nodes and links, JSON reachability overlay | Structure is always stored inventory; operational overlay is `simulated` |
| Performance / Syslog | `monitorApi`, `/monitor/*`, `syslogApi`, `/syslog/*` | JSON fixture, checked against SQLite device/interface IDs | Fixed refreshable metrics, alerts and events; remote sync controls disabled |
| Config Backup | `networkConfigBackupApi`, config-backup endpoints | existing `config_snapshots` SQLite data | Existing stored snapshot browsing/diff/import; fixture snapshots are schema-ready. Restore simulation wiring is M0.2 |
| Template Studio | `configApi`, `/config/templates`, schemas, render, validate | baseline `backend/templates` and schemas overlaid by `authoring_revisions` | Create, open, edit, validate, render, save and recover revisions locally; no Git sync |
| Ansible Studio | `ansibleApi`, `/ansible/files*` | authorized baseline roots overlaid by `authoring_revisions` | Original file tree/editor renders; local playbook authoring endpoint exists; AI, check, SSH, approval and deploy controls honestly disabled |
| Approval Queue | deploy queue/action clients | existing `change_requests`, audit/state-machine code | Remains unavailable pending M0.3 persisted local decision wiring; no deployment is claimed |
| Policies / operational history | policy and audit clients | existing policies, policy audit and operational record tables | Stored records remain readable; local evaluation workflow is M0.3 |

Existing validators and state machines were retained: inventory/interface/link ownership checks in the database manager, configuration schema validation, onboarding models, deployment change-request states, profile validation, policy/audit tables, and snapshot metadata. M0.1 does not introduce a competing database or duplicate CRUD tables.

## Fixture format and editing

[observations.json](../backend/simulation/observations.json) is deliberately human-editable. Its schema is [observations.schema.json](../backend/simulation/observations.schema.json). Fixture v1 accepts defaults, per-device availability/metric overrides, per-interface status/metrics, syslog, alerts, network events, and snapshot fixtures. Every timestamp must include a timezone; extra fields are rejected. Device and interface IDs must exist in the authoritative SQLite inventory and an interface must belong to the referenced device.

To change simulated R1 values, add a `devices` item with `device_id: 1`, save JSON, and use the page’s existing **Refresh** control. Browser verification temporarily set R1 `up`, CPU `73`, memory `61`, utilization `73`, and a warning alert at the fixed timestamp `2026-01-01T00:12:00Z`; the checked-in fixture was then restored to its inventory-neutral baseline. No current-time or random measurements are generated. Invalid JSON or invalid references return an explicit error and leave SQLite inventory unchanged; the UI says that no live state is implied.

## Template Studio correction

Opening Template Studio previously ran `templateGitApi.status()` from [TemplateStudioView.tsx](../frontend/views/TemplateStudioView.tsx) even though Git status is not meaningful in local mode. The local backend correctly returned unavailable, but the UI surfaced it as the misleading **Git status failed** error.

The status request is now capability-gated by `template_git.status`; Git synchronization remains off. The existing authoring UI was preserved. Saves now append recoverable revisions to SQLite and do not modify baseline template, playbook, or schema files. Local Jinja parsing and JSON Schema checks report genuine authoring errors. Rendering also filters profile defaults when a strict template schema rejects additional properties, fixing the inherited validation failure without weakening schema validation.

## Database change and preservation

The additive [m0_1_authoring.sql](../backend/db/migrations/m0_1_authoring.sql) migration adds `authoring_revisions` and its audit index. [local_migrations.py](../backend/db/local_migrations.py) takes a SQLite backup before applying this version and records it in `schema_migrations`; it does not regenerate or remove existing data. Revisions record namespace, authorized relative path, revision number, file/folder kind, soft-deleted state, actor and timestamp. The first local change snapshots the disk baseline as revision 1, making a later local edit recoverable while keeping the repository file untouched.

## Actual verification

| Check | Outcome |
| --- | --- |
| Provider and M0 regression suite | `14 passed, 1 warning`: M0 tests, fixture reference/error/refresh/source-label tests, template revisions/strict schema tests, workspace path guard tests, and policy unit tests |
| Frontend production build | Passed with `npm run build`; existing CSS `@property` and large-chunk warnings remain |
| Template Studio in browser | Opened without **Git status failed**; created disposable `cisco_ios/m01_browser`, wrote source, saved a SQLite revision, rendered `hostname m01-router`, and observed local syntax validation pass; the disposable template was then soft-deleted |
| Editable fixture in browser | First malformed alert intentionally produced a visible fixture validation error; after changing `time` to schema-required `timestamp`, then setting `metric`, `value`, and `threshold`, **Refresh** showed R1 Up, CPU 73%, memory 61%, one simulated warning, and `utilization_pct = 73` at the fixed fixture timestamp. The inventory-neutral fixture was restored after the check. |
| Ansible Studio in browser | Original Studio/file tree/editor renders; local Create created a disposable `playbooks/m01_browser.yml`; revision cleanup soft-deleted it. AI, check, SSH, approval and deploy controls were visibly disabled with local-lab explanations |
| External execution | No remote job was launched and no device command/deployment was sent during the checks |
| Frontend lint | Ran `npm run lint`: 581 problems (546 errors, 35 warnings), matching the M0 post-change baseline; no lint rules were disabled |

Run from the project root:

```powershell
Set-Location backend
$env:PYTHONPATH=$PWD
.\.venv-m0\Scripts\python.exe -m pytest tests/test_m0_local.py tests/test_m0_1_providers.py tests/unit/test_policy_compliance_engine.py tests/unit/test_compliance_scope_resolver.py -q
Set-Location ..\frontend
npm run build
```

The frontend’s inherited lint debt remains documented in [M0_HANDOVER.md](M0_HANDOVER.md): M0 measured 546 errors and 35 warnings, versus the original 570 errors and 36 warnings. M0.1 did not disable lint rules or claim a clean lint result.

## Remaining scoped work

M0.2 should connect existing onboarding validation to SQLite registration/local status, expose fixture-backed snapshot restore simulation and expand page-specific simulation states for Config Backup, Syslog, Topology and Global Profiles. It should retain the current provider contracts.

M0.3 should wire persisted approval decisions and audit history through the existing change-request state machine, enable supported stored policy evaluation records, and complete page-by-page browser verification for those workflows. Neither phase should enable real execution.

For a future normal-mode adapter, implement the same provider contracts behind explicit configuration and preserve the source labels: remote values must report `real`, SQLite values `stored`, and fixtures `simulated`. Switching providers must remain an application-start configuration choice with a capability change, never an implicit connection attempt. V9/AI integration remains a separate, later authorized phase.
