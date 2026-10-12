# Editable network simulation

SQLite owns inventory IDs, service profiles, templates, approvals, snapshots and audit history. These JSON files supply external observations only. Saving JSON and refreshing the page rereads it; no frontend edits or backend restart are needed.

| File | Edit here |
| --- | --- |
| `observations.json` | Shared availability, uptime and interface defaults |
| `availability.json` | Device `status: active/inactive`, `availability: up/down/unknown`, and interface status overrides |
| `metrics/1h.json`, `metrics/6h.json`, `metrics/24h.json` | CPU, memory, traffic bps, utilization, errors/discards per second, unicast/multicast/broadcast packets per second; timestamps are literal and deterministic |
| `syslog.json` | Syslog, network events, and event templates expanded for each stored device |
| `alerts.json` | Explicit alert observations and thresholds calculated against metric values |
| `configurations/device-<SQLite ID>.json` | Each device's current configuration response, in `config_text` |
| `workflow_outcomes.json` | ZTP and restore success/failure, plus initial configuration for newly registered devices |

Schemas alongside these files describe the accepted fields. Unknown device/interface IDs or malformed values return a visible validation error. JSON cannot register devices or change inventory identity. `observations.before-split.json` preserves the previous fixture for recovery; it is not loaded.

## Examples

Hide device 1 from operational topology and backup selection while retaining planned inventory:

```json
{"devices":[{"device_id":1,"status":"inactive","availability":"down"}],"interfaces":[]}
```

Set `active` and `up` to show it again. Devices absent from the override list inherit the same defaults, including newly registered devices. Copy a complete metric point from `defaults.metrics` into a device's `metrics` array in the desired range file and add its `device_id` to override that device. The original API response shapes are unchanged. Each range has 61 fixed points; defaults deliberately remain constant (CPU 26%, memory 44%, traffic 12/8 Mbps, errors 2/s, discards 1/s).

Edit `configurations/device-1.json`'s `config_text`, preserving the ID and JSON escaping. Capture creates a new immutable SQLite snapshot. A successful restore first captures a safety snapshot and then atomically replaces this JSON configuration with the selected snapshot. Failed fixture outcomes leave the file unchanged and record the failed attempt. Snapshot descriptions remain separately editable metadata. Existing old snapshots are not rewritten with the new defaults.

New configuration files are initialized when backup devices are listed or captured. Change `capture.default_config` in `workflow_outcomes.json` for future devices; `{hostname}` and `{management_ip}` are substituted from SQLite. Existing device files are preserved.

Set `restore.default_status` or `ztp_publish.default_status` to `failed` with an explanatory `message`, or add a `device_outcomes` entry containing `device_id`, `status` and `message`. No SSH, DHCP/TFTP delivery or physical deployment is performed.

## Environment and AI

Root `.env` selects `COGNISHIELD_MODE=local_lab` or `normal`. Run `backend/run_local.ps1` to enable the navbar selector's automatic restart. Direct uvicorn starts require a manual restart after changing mode. Actual mode uses the preserved original adapters and requires their dependencies and reachable services; a failure never silently falls back to simulation.

`COGNISHIELD_LOCAL_OLLAMA_URL=http://127.0.0.1:11434` and `COGNISHIELD_LOCAL_OLLAMA_MODEL=auto` select actual local inference. Set an installed model tag instead of `auto` to pin it. The model menu lists installed chat models, excludes embedding models, and changes the active process selection. Restart restores the `.env` choice. Normal mode retains its existing `OLLAMA_BASE_URL` / `OLLAMA_MODEL` configuration.

Credential saves use the existing encrypted SQLite vault. Local connection tests validate saved credentials/profile targets and label results simulated; they do not authenticate to a remote server.
