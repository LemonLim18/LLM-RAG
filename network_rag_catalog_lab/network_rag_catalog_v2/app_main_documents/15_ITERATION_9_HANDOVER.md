# Iteration 9 — Add-only Synthetic Device Registration

## 1. Iteration identifier and objective

Register one synthetic device and its optional initial interfaces atomically in V9's existing JSON inventory, discoverable through the inventory API and unchanged target resolver. No edit/delete, topology changes, external services, execution, session refresh or artifact work.

## 2. Completion status

**Completed** for add-only synthetic registration in a single workbench process. All 70 workbench backend tests pass, including 13 focused registration tests. Frontend lint/build, 22 deterministic browser checks (2 live-AI checks skipped), and one unmocked GUI-to-FastAPI registration check using temporary inventory pass. V9 core and user inventory were not modified. No live inference or device connectivity was exercised.

## 3. Files added, modified or removed

Paths relative to the V9 repository root.

Added:

- `app/workbench/inventory_registration.py`
- `tests/test_workbench_registration.py`
- `tests/workbench_inventory_server.py`
- `frontend/src/features/explorer/AddDeviceForm.tsx`
- `frontend/tests/registration.spec.ts`
- `frontend/integration/registration.spec.ts`
- `frontend/playwright.registration.config.ts`
- `app_main_documents/15_ITERATION_9_HANDOVER.md`

Modified:

- `app/workbench/api.py`
- `app/workbench/planning_service.py`
- `tests/test_workbench_planning.py`
- `frontend/src/services/inventoryApi.ts`
- `frontend/src/app/WorkbenchProvider.tsx`
- `frontend/src/app/types.ts`
- `frontend/src/app/workbenchReducer.ts`
- `frontend/src/features/explorer/ExplorerPanel.tsx`
- `frontend/src/features/chat/useLocalPlanning.ts`
- `frontend/src/components/layout/StatusBar.tsx`
- `frontend/src/styles/workbench.css`
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`
- `app_main_documents/04_ARCHITECTURE_DECISIONS.md`

No source files removed, no dependencies added/installed, no Git commit. Existing dirty/untracked work from earlier iterations is preserved; the full Git diff is not solely Iteration 9. `data/inventory/devices.json`, V9 domain/CLI, SQLite, knowledge catalogs/releases and user sessions are unchanged by implementation/tests. A verified disposable seven-record browser fixture was removed after testing; none of its data was a user registration.

## 4. Architectural decisions and reasons

### Pre-implementation FYP assessment (2026-10-09)

Scoped sources under `app_main_documents/Net_Topo_View-intentparse/`:

- `frontend/views/NetBoxDevices.tsx`: device form requires management IP/mask, collects credentials and constructs management interface names. Device POST is followed by a separate interface save; failures can leave partial registration. Separate interface forms validate L2/L3 address semantics, allow management flags and refresh cached lists. Retain grouped fields, inline validation, pending guards and confirmed refresh conceptually, not this large controller or its visual structure.
- `frontend/src/services/api.ts` (`netboxApi`): typed-shaped create/list/interface methods use numeric device IDs and sync status fields. Retain the small typed transport boundary, not the broad facade or old vendor tokens.
- `backend/netbox/api.py`: hostname duplicate check, device/interface request models, SQLite persistence and asynchronous NetBox/Telegraf/syslog sync. Reject this coupling and all credential/connectivity behavior. Registration need not assume management addresses exist.
- `backend/db/models.py`, `backend/db/schema.sql`, `backend/db/repositories/device_repo.py`: devices/interfaces/links have numeric SQL keys, per-device interface-name uniqueness and topology relations; repository delegates upserts and supports crawl sync. Retain scoped identity/reference validation conceptually. Do not port SQLite, upsert/edit/delete, topology, or crawl synchronization.

V9 differs: `load_inventory()` returns uncached dictionaries from the configured `devices.json`; `target_query` builds vocabulary from hostname/display name/aliases and inventory attributes. Raw device IDs are not a natural-language target attribute. Interface names/aliases are nested, case-insensitive lookup identities; management can be a descriptive role, not a fabricated address or an FYP L2/L3 object. Capabilities are declared features, not proof of operation compatibility. No complete reusable inventory-schema validator exists; existing context validators validate operation parameters rather than proposed inventory writes.

### Bounded design selected before coding

A new strict add-only contract will collect hostname/display name, kind, vendor/platform pair, version, site/role, optional location/aliases/tags, explicitly declared features, and zero or more initial interfaces (name/aliases/type/role/enabled). Server-generated `dev-<UUID>` IDs match the existing opaque string-ID convention. No default interfaces, addresses, links, credentials, validated-policy declarations or discovered status are invented. Only supported vendor/platform pairs are offered; operation rendering remains V9's decision.

Validate the entire proposed list's consumed field shapes, identities, interface identity uniqueness and existing neighbor references while retaining original dictionaries and unknown attributes. Append only; never serialize old records through the safe GUI projection. Use the existing logical-record `_revision`, shared planning/answer busy gate, sibling temporary write/fsync/replace and a final pre-replace revision check. Single process only, not cross-process CAS. No second authority or speculative repository framework. Initial interfaces share the same transaction; full interface management is deferred.

Use a native workbench dialog and existing provider/reducer inventory cache. Explicit refresh after POST selects the registered record without assuming a matching Monaco sample. Pending, stale/conflict, validation and uncertain transport outcomes are distinct; no automatic retry. Existing saved plans remain untouched and source/context checks continue rejecting stale answers. No actual FYP source reuse is planned: its dependencies and model differ substantially.

### Implemented contract and schema requirements

Entry point remains `app.workbench.api:app`. Only one inventory mutation was added:

```text
POST /api/v1/inventory/devices
Request: DeviceRegistration { expected_inventory_revision: SHA256, device: NewInventoryDevice }
Success: HTTP 201 InventoryDetailResponse
{ api_version: 1, source: "synthetic", inventory_revision: SHA256, device: InventoryDevice }
```

Example request (illustrative, not a record added to user inventory):

```json
{
  "expected_inventory_revision": "<64-character revision from inventory GET>",
  "device": {
    "hostname": "R99", "display_name": "Demo router 99", "kind": "router",
    "vendor": "juniper", "platform": "junos", "version": "23.4",
    "site": "Lab", "role": "edge", "location": "Rehearsal",
    "aliases": ["edge-r99"], "tags": ["synthetic"],
    "capabilities": {"features": ["ospf", "interface"]},
    "interfaces": [{"name": "ge-0/0/0", "aliases": [], "type": "ethernet", "role": "uplink", "enabled": true}]
  }
}
```

Required new-device fields: hostname, display name, kind, vendor/platform, software version as a string, site, role, and explicitly selected capabilities. Kinds: router/switch/firewall. This bounded transport accepts Cisco/iosxe, Huawei/vrp, Juniper/junos only; matching a pair is **not** hardware/version/render certification. Nonempty feature declarations may include interface, vlan, ip_address, static_routing, ospf, bgp, isis, acl and qos. At least one is required because V9 interprets an empty feature list as no category restriction—not as no supported operations. No validated policy/resource claims are assigned.

Optional location, aliases and tags remain descriptive. Text and lists are bounded; controls/newlines are rejected, and identity tokens use an explicit safe character set. Unknown request fields are forbidden, including caller-supplied IDs, credentials, management addresses, topology neighbors or operational metadata. Server-generated `dev-<UUID>` IDs are immutable opaque string identities. The safe response retains the established inventory projection; `source_refs` and existing private metadata are not exposed.

Zero to 64 initial interfaces can be submitted in the same atomic operation. Each requires name, ethernet/loopback type, role and a strict boolean administrative enabled value; aliases are optional. User-entered role `management` is descriptive only, not a special IP or discovery workflow. Interface aliases may repeat their own canonical name, as existing V9 data does; aliases/names may not identify different interfaces on the same device. No existing interface is edited/deleted and no neighbor/link is created. Rich VLAN/resource/policy-specific interface fields remain outside this registration form.

`StoredDevice`/`StoredInterface` validate the complete proposed inventory's fields consumed by the existing safe projection/resolver. They allow unknown existing attributes, which remain in their original dictionaries: old records are never rewritten from these models. Whole-list checks enforce unique IDs and unambiguous hostname/display-name/alias ownership, per-device interface identities and resolvable existing neighbor references. Existing planned-device references are preserved because no old ID or record can be removed or changed. This is structural registration validation, not a new V9 operation-policy engine.

`load_inventory()` itself has no typed schema validator. The adapter uses it to confirm its snapshot and uses actual `resolve_intent_targets` with the complete proposed list to verify each new hostname/display-name/alias identifies exactly the new record before saving. Normal subsequent API and V9 reads remain uncached calls to the original loader.

| Error | Behavior |
|---|---|
| Invalid/missing request fields, vendor/platform mismatch, unknown feature/field | 422 typed request validation; no write |
| Duplicate/ambiguous device or interface identity | 409 `IDENTITY_CONFLICT`; form values retained |
| Expected logical revision differs, or inventory changes before replacement | 409 `STALE_INVENTORY`; reload and explicit user review required |
| Existing inventory malformed, bad references, duplicate IDs or unsafe shapes | 409 `INVALID_INVENTORY`; no repair/overwrite |
| Planning, answer or another registration owns the process mutation gate | 503 `PLANNER_BUSY`; registration does not start |
| Read/write/fsync/replace error | 503 `INVENTORY_STORAGE_UNAVAILABLE`; no raw filesystem exception exposed; inspect inventory before retry |

Adapter errors use typed `InventoryErrorResponse.detail` with code/message and optional current_inventory_revision. Responses do not expose filesystem paths or legacy credentials.

### Storage, optimistic revisions and mutation coordination

Registration accesses `app.devices.inventory.INVENTORY_FILE`, the same configured path used by `load_inventory()`, not a second dataset. The default remains `data/inventory/devices.json`.

1. Acquire the same `PlanningService` busy gate used by creation and answers. Inventory writes do not occupy or evict creation receipt/cache IDs.
2. Read and strictly parse the existing file (duplicate JSON keys/nonfinite data rejected), validate its records, and confirm the loader sees the same snapshot.
3. Compare `expected_inventory_revision` with the existing `_revision(records)`: SHA-256 of UTF-8 canonical JSON with sorted keys and compact separators. **This is the established logical-record revision, not raw-byte revision.** Whitespace-only changes remain compatible; list/field/value changes conflict.
4. Append the new raw record and validate the complete proposed list and actual V9 selector behavior. Construct the safe response before committing.
5. Write the full proposed JSON into an exclusive sibling `.tmp`, flush/fsync, recheck the current logical revision, then `os.replace` the authority file. ASCII escaping keeps Unicode descriptions compatible with V9's existing default-encoding reader. Temporary names end in `.tmp`, so they do not enter V9 JSON source/context hashes.
6. Return the safe new device and updated logical revision; release the gate in `finally`. Ordinary error cleanup removes only this operation's temporary file.

Readers observe a complete old or new file under local atomic replacement; simulated partial temporary writes, fsync failure and replacement failure all leave the previous inventory bytes intact. Successful writes preserve every original logical record/attribute, but do reformat the JSON file. Out-of-band changes observed before replacement are rejected; the small check/replace window is **not cross-process CAS**. Multiple Uvicorn processes, independent CLI writers, remote filesystems, power-loss directory durability and OneDrive conflict behavior are not certified.

No automatic backup/rollback catalog or second authoritative store was introduced. The early design's proposed backup workflow remains deferred; this add-only implementation proves logical old-record preservation and pre-replacement failure safety, not recovery from disk loss or an external writer. Back up the authority before manual experiments where independent recovery is needed.

Inventory/source revision changes leave saved V9 files byte-for-byte unchanged. Existing answer checks reject `STALE_SOURCE`; no load/resume/refresh/replan runs during registration. The GUI marks its retained plan historical after confirmed registration or an explicitly reloaded changed inventory revision. It does not invent a new session revision or infer which request caused a changed inventory.

### Frontend behavior and FYP outcome

`AddDeviceForm` is a native, keyboard-operable dialog in the existing explorer, using workbench CSS tokens and one typed inventory client. It displays the expected revision, identity/context fields, paired vendor/platform choices, explicit feature selection and repeatable unsaved initial-interface rows. Required fields, pending guards, inline backend errors and reload-before-retry states prevent blind duplicate submissions. Inputs remain available for correction after conflicts; there is no automatic POST replay.

After confirmed POST, the provider performs a real inventory GET and selects the returned ID through the existing reducer without changing the current sample document or Plan Review. A failed GET after confirmed save offers reload only. A lost POST response remains uncertain until the user reloads and inspects; duplicate identities and stale revision checks prevent the same device from silently being added twice. The existing confirmed V9 result and Monaco edits remain separate. Demo mock messages never register devices.

**FYP influence:** grouped metadata/interface entry, inline feedback, duplicate checks and post-save list refresh were useful concepts. Direct source reuse: **none**. We intentionally rejected its management-IP requirement, credential storage, integer SQL identities, separate non-atomic device/interface saves, external sync jobs, cache ownership and large page controller. The smaller typed add-only dialog and one JSON transaction fit the current workbench/V9 authority better. Full interface management, IP assignment, topology and external integrations remain deferred.

## 5. Tests run, exact commands and outcomes

From the V9 repository root:

```powershell
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_workbench_registration.py' -v
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_workbench_*.py' -v
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' main.py --help
git diff --check
```

Final combined workbench run: **70 passed** (57 existing tests plus 13 registration tests). Final focused registration run: **13 passed**, including explicit partial-write failure injection. Existing mutation-route expectation was extended only for the authorized inventory POST. V9 semantics were not changed and tests were not weakened to permit invalid data.

Registration checks cover stable generated IDs; strict invalid/missing fields/vendor/platform; duplicate IDs/hostname/aliases/display name/interfaces; unchanged complete original dictionaries including unrecognized private fields; no exposure of those fields; stale revisions and whitespace compatibility; invalid existing shapes/references; filesystem open/partial-write/fsync/replace failures; final-check external changes; complete old/new reader snapshots; shared gate exclusion in both directions; and source/context revision invalidation with unchanged saved-session bytes and no answer application. Every test compares the **real user inventory bytes and mtime** before/after while all mutations use temporary copies.

**V9 discoverability evidence:** actual unmodified `load_inventory`, `resolve_targets` and `resolve_intent_targets` discover R99 by hostname, case variant, alias and display name with the returned stable ID. Inventory list/detail agree on the same ID/vendor/interface records. A broad Juniper query remains `AMBIGUOUS_TARGET`, and an unknown R404 remains unresolved. Raw generated IDs are **not** a natural-language selector in the current attribute registry; tests confirm rejection rather than adding an ID alias or changing core behavior. Device IDs work in existing inventory detail GET.

From `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e
npm.cmd run test:e2e -- tests/registration.spec.ts
npm.cmd run test:e2e -- --config playwright.registration.config.ts
```

Results: lint passed; TypeScript/Vite build passed (2,324 modules; existing Monaco >500-kB chunk warning). Standard automated Chrome suite: **22 passed, 2 skipped** (opt-in live-AI tests). Registration subset: **3 passed**, including a final rerun after historical labeling on revision reload. Coverage includes required inputs/capabilities, optional interfaces, pending/double-submit guard, current revision, duplicate/stale errors, reload behavior, lost-response uncertainty, confirmed-save/reload failure, immediate selection and preservation of existing Local V9 plan, Monaco edits and Demo mock separation.

Separate integration configuration: **1 passed**, an **unmocked browser → FastAPI → temporary V9 JSON** registration, initial interface, safe detail GET equality and visibility after browser reload. `tests/workbench_inventory_server.py` copies the real records into a temporary directory before starting its application and redirects only that process's loader path; normal application code gains no alternative inventory setting. It never writes the real inventory. No Ollama or external service is required. This is actual browser interaction evidence, not live inference or a separate manual visual review.

Initial failures were resolved: the first structural validator mistakenly rejected a valid existing interface repeating its own canonical name as an alias; it now follows V9 ownership semantics while still rejecting cross-interface collisions. A mocked stale-revision browser test assumed a single mount GET, but React Strict Mode can issue two; the fixture now models revision changes by mutation phase instead of incidental GET count. The final relevant checks pass.

Python execution used only the project venv. Approved outside-sandbox runs avoided the previously recorded Miniconda-base/OneDrive access limitations; no alternate interpreter or package installation was used. Existing broad domain baseline failures (2 assertions and 192 template-example subcase errors) were not rerun/repaired because no core interface changed. Workbench tests exercise the real loader/resolver and existing answer staleness path directly. Live inference/RAG was not reverified.

User inventory verification before/after tests: SHA-256 `8779de05d5982390bc56bbb7b57807d19c77441acbe56cd346047bc9ddabc616`, length 29,001 bytes, mtime UTC `2026-10-05 01:08:06`. The actual six-device authority was not used as registration test storage. CLI help exited 0 with existing options.

Documentation verification: all 21 listed added/modified paths exist, handover code fences are balanced, and `git diff --check` passes. Progress and decisions now record only the completed add-only boundary and preserve historical test/readiness limitations. Existing unrelated dirty files are not attributed to this iteration.

## 6. Remaining issues and risks

- Single workbench process only; no multi-worker/CLI compare-and-swap, filesystem-wide lock, power-loss guarantee or persistent registration-request journal. A timed-out POST can have saved; inspect refreshed inventory instead of blind retry.
- Existing malformed inventory blocks writes rather than being repaired. Validation covers inventory structure/identities/references used by this adapter, not every vendor resource/policy field in rich historical records.
- Initial interface metadata is descriptive. No management IP, neighbor link, speed, switchport, LAG or policy-specific resource state is invented. Version/vendor choices and feature declarations do not guarantee V9 can render an operation.
- Only registration is implemented; existing-device/interface edit/delete, inventory synchronization, discovery, topology and execution remain deferred. Unsaved form-row removal is not an inventory deletion operation.
- Adding inventory changes source/context revisions globally; old saved sessions remain historical and may reject new answers. No refresh/resumption is implemented. Raw device-ID prompt selectors remain unsupported by V9.
- No persistent backup/undo feature; old records are preserved logically, not as an immutable old byte snapshot after successful replacement. External writers can still race after the final check.
- Broad catalog/test drift, inherited dependency advisories and Monaco bundle warning remain unchanged. Live Ollama/RAG was not reverified. Windows test-process termination can leave disposable OS-temp fixtures; these are not an alternate inventory authority.

## 7. Suggested next iteration

**Iteration 10 — Read-only generated configuration presentation in Monaco.** Allow a selected existing V9 task's actual configuration to open as a clearly labelled read-only Monaco document with stable session/task/device association; keep independent sample edits intact. No artifact persistence, editable drafts, diff, new mutation, inventory editing or session refresh in that single presentation deliverable. Recommendation only; no Iteration 10 work started.

## 8. Exact reproduction/verification instructions

Backend PowerShell (one process, no reload during mutations):

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2'
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
```

Frontend in another PowerShell:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm.cmd run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. Choose **Add Device**, enter a unique hostname/display name, version, site/role, vendor/platform and at least one declared feature. Optionally add initial interface rows with explicit names/roles and administrative enabled flags. Review the revision, submit once, then verify the selected API record and metadata. Existing plan and sample edits must remain intact; old plans are labelled historical, not refreshed.

**Manual registration on the normal server intentionally changes the shared inventory.** To reproduce safely without adding any real demo records, stop normal servers and run the isolated integration command above instead. It owns ports 8000/5173 and writes only a temporary copy. The backend registration tests prove actual V9 target resolution and source-stale behavior against controlled copies. Do not point test storage at the user authority or run prototype test trees.

To inspect a registered device without planning:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/inventory/devices'
$registeredDeviceId = Read-Host 'Registered device ID'
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/inventory/devices/$registeredDeviceId"
```

No registration is automatically retried, and no existing session is refreshed. Stop after Iteration 9.
