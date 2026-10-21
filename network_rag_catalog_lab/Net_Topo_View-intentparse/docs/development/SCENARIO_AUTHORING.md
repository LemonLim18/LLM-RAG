# Central development network authoring

Definitions: `backend/development/scenarios/`. The validated format is
`backend/development/scenario.schema.json`, exported from the actual Pydantic
`Scenario` contract. A readable programmatic example lives in
`backend/development/examples.py`; `MIXED-PATH-001.json` is its bundled JSON form.
Neither contains evaluator expected diagnoses.

The selected editable state is `tmp/development-network/state.json` by default.
`COGNISHIELD_DEV_STATE` can select another file **inside this application workspace**.
Only the existing server writes it. Do not edit it while the app is running.
Existing version-1 definitions remain readable; expanded network observations
require `format_version: 2`, `model_scope: ipv4_observation` and the `network` object.
Persisted custom scenarios are not automatically replaced by bundled revisions.

## Author and validate without changing the running network

Run from the application root with its installed Python:

```powershell
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py create --id LAB-CUSTOM-001 --output backend/development/scenarios/LAB-CUSTOM-001.json
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py validate backend/development/scenarios/LAB-CUSTOM-001.json
```

Use `--from <file>` to duplicate another definition. Creation refuses to overwrite
an existing file. Output is restricted to `backend/development/` or `tmp/phase-d/`.
Codex can edit that dedicated definition and validate it; application inference
cannot create scenarios or acquire these developer controls.

New bundled files are loaded at server startup. To use a new file without a
restart, import it through the existing authenticated scenario API/UI. Import
rejects duplicate IDs; editing the selected scenario uses a revision-checked edit.

## Enable and use the server-controlled development provider

Set `COGNISHIELD_DEV_SIMULATION=1` in local development server configuration and
restart the existing `./run_local.ps1` composition on **5173/8000**. Production
defaults remain disabled and normal mode cannot fall back to simulation. Use one
disposable acceptance SQLite/state for mutating tests; preserve ordinary data.

The Development scenarios panel supports selection, JSON editing, import/export,
duplication and reset. For CLI controls, set `COGNISHIELD_DEV_TOKEN` in your local
shell to an existing authenticated developer bearer token. Do not save or paste
that token in source, reports or command examples. The CLI never mints credentials.
Admin authorization remains mandatory for activation and writes.

```powershell
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py list
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py import backend/development/scenarios/LAB-CUSTOM-001.json
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py activate MIXED-PATH-001
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py show
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py evaluate --prompt "Investigate whether Branch-Aster can reach Edge-Cedar. Explain both directions."
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py export --output tmp/phase-d/exported-scenario.json
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py reset HEALTHY-001
```

Writes use the server's current revision, or explicit `--expected-revision` for
optimistic concurrency. `apply-event <file>` uses the existing interface-event
endpoint; its file contains `interface_id` and `admin_status`. Bringing admin up
does not infer operational/protocol recovery. The existing event editor is bounded
to its reviewed CLI edit forms; unsupported vendor edits fail rather than guessing.

The exploratory evaluate command archives actual gateway output and marks
independent grading **NOT RUN**. HTTP success is not a reasoning pass. Curated
expected assertions belong in `docs/evaluations`, never model-visible definitions.

## Declared network semantics

- Scenario-scoped device/interface/link/route/flow identities are explicit. Flow
  addresses must belong to the declared source/destination interface and VRF.
- `network.tables` are separate per device/VRF. Exact route matching uses longest
  prefix, declared preference then metric. The model never guesses vendor defaults.
  Incomplete tables remain unknown because a missing more-specific route matters.
- A route explicitly forwards, discards or leaks to another VRF. Recursive next-hop
  resolution is bounded and detects cycles. Interface state and explicit neighbor
  resolution must be known; planned topology alone is insufficient.
- Forward and return paths are calculated separately. ECMP branches remain separate;
  one surviving branch is not universal success. Maximum 32 hops and 16 branches;
  truncated exploration is unknown. No NAT, stateful firewall or IPv6 forwarding.
- Stateless IPv4 ACL rules execute in listed order at the declared ingress/egress
  interface/VRF. Ports require TCP/UDP. Default action and attachment completeness
  are explicit; unknown attachment completeness is not implicit permit.
- OSPF/BGP are typed configuration/neighbor observations and prerequisite checks,
  not complete protocol implementations. OSPF 2-Way between broadcast DROthers is
  not universally a fault. BGP Established with zero accepted prefixes is distinct
  from session failure. Idle alone cannot establish a cause. Exact platform CLI
  conformance, LSDB behavior and full best-path selection remain separate gates.
- Metric samples retain timestamps, units, cadence and missing values. Counters
  are not rates; resets/wraps prevent naive deltas. High utilization plus increasing
  drops is a correlation/hypothesis, not uniquely established congestion causation.
- All calculations use one scenario snapshot and its epoch/revision. Historical
  and stale observations cannot certify current state. Uploaded content cannot
  enable simulation, alter sources, authorize a tool or publish knowledge.

Bundled expanded examples:

| Definition | Declared scope |
| --- | --- |
| `MIXED-PATH-001` | Cisco/Juniper/Huawei three-device path, separate forward/return tables and addresses. |
| `PROTOCOL-MIXED-001` | The same inventory with timestamped OSPF/BGP peer observations and current CLI excerpts. |
| `PERFORMANCE-MIXED-001` | Declared traffic/counter series and a correlation assessment, not a unique congestion diagnosis. |

OSPF process IDs are local identities, not equality prerequisites. Area type,
authentication and MTU-ignore observations may be unknown; a missing value cannot
be turned into a confirmed mismatch. BGP peer projections preserve local/remote
addresses and AS roles, received/advertised/withdrawn routes, RIB completeness and
next-hop validity separately. Neither Established nor a nonempty configuration
proves end-to-end forwarding. Use explicit simulated path observations for that.
Changing interface administrative state through the existing event endpoint does
not simulate a complete protocol convergence event sequence; edit and validate
the related declared observations explicitly where that sequence is not modeled.

## Recovery

Reset through the manager/API adopts the bundled definition explicitly. Restore a
custom file through validated import/edit; do not blindly overwrite newer state.
Disable `COGNISHIELD_DEV_SIMULATION` and restart to return to ordinary readers.
No scenario rows are copied into ordinary inventory. JSON state supports one
application writer; the CLI uses that writer's API rather than a competing store.


## Complete24-source Workbench starters

The existing Workbench's **Lab starter scenario** selector offers healthy,
policy/forwarding and stale/conflicting-observation packs. Create from lab starter
creates an owned draft only. Save/Validate/Activate remains explicit; this control
does not change ordinary inventory or publish V9 knowledge.

Bundled source folders:

- `backend/development/scenarios/healthy_all_sources_v2/`
- `backend/development/scenarios/acl_forward_all_sources_v1/`
- `backend/development/scenarios/stale_conflict_all_sources_v1/`

Each manifest declares all24 categories and a fixed virtual clock. The latter two
use `configs/running_configs/` and `configs/config_snapshots/` for independent text
files. Edit those files or their source JSON, validate and import to an owned draft.
Changing a current file does not overwrite an older saved file.

```powershell
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py bundle-create --variant acl --id MY-EDITABLE-LAB --linked-configs --output backend/development/scenarios/my_editable_lab
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py bundle-validate backend/development/scenarios/my_editable_lab
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/development_scenario.py bundle-import backend/development/scenarios/my_editable_lab
```

`bundle-import` uses your existing authenticated admin token and validates a saved
draft; it does not activate automatically. `--variant conflict` supplies a complete
alternative. Creation refuses an existing destination. The optional linked-config
export uses text assets through the existing path containment and size checks;
PDF/image assets retain their existing encoded-byte/digest contract.

Source-health records preserve authored claims. The effective availability of the
selected revision is returned separately after configured overrides. A stale or
error source is not proof of a physical network failure; conflicting claims must
be reconciled. All starter data is simulated and no physical collection is run.

## Independent observed topology

`topology_observed.json` and `topology_history.json` accept independently authored
endpoint identities in each record's `values`:

```json
{
  "endpoints": {
    "src_device_id": 1100,
    "src_interface_id": 1,
    "dst_device_id": 1300,
    "dst_interface_id": 4
  },
  "oper_status": "up",
  "discovery_protocol": "LLDP"
}
```

Both devices and each interface's owner must exist in the same draft inventory.
The record's observer must be one endpoint. An optional record interface must
also belong to that relationship. Explicit endpoints take precedence over a
legacy `link_id`; old references remain readable with a planned-reference label.
They do not become independent discovery simply because a source says LLDP.

In Workbench, select **Observed links** or **Topology history**. The preview shows
the relationship, and named device/interface selectors edit those same schema
fields. Changing a device clears an incompatible port; select a recorded port
explicitly. Save, Validate and Activate remain separate. The intended graph is
not changed. Current-plan comparisons exclude older observations unless history
is requested; a missing current observation does not mean physical disconnection.

Actual JSON/GUI/both-assistant evidence and original failures are indexed in
`../evaluations/phase_g_source_matrix.json`. This bounded source acceptance does
not establish the full24-source or fresh-model-quality gate.
