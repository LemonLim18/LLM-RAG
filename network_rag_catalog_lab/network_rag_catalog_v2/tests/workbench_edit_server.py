"""Isolated API integration server. ONLY model interpretation is a test double."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
import app.config as config
from app.planner.models import ExecutionPlan, PlannedTask
from app import document_edits

root = Path(sys.argv[1]).resolve()
if not root.is_dir() or not root.name.startswith('v9-working-browser-edit-'):
    raise RuntimeError('A dedicated temporary edit test directory is required')
config.STORAGE_DIR = root
config.SESSIONS_DIR = root / 'sessions'
config.SESSIONS_DIR.mkdir(exist_ok=True)
identity = '00000000-0000-4000-8000-000000000112'
path = config.SESSIONS_DIR / f'{identity}.json'
if not path.exists():
    device = next(d for d in json.loads(config.INVENTORY_FILE.read_text()) if d['id'] == 'lab-sw1')
    output = dict(device_id=device['id'], configuration='! preserved\nvlan 20\n name STAFF\n exit\n! unrelated\n',
                  **{k: device[k] for k in ('hostname', 'vendor', 'platform', 'version')})
    task = PlannedTask('task-sw1', 'VLAN 20 baseline fixture', 'vlan', 'rename_vlan', {'vlan_id': 20, 'new_vlan_name': 'STAFF'}, ['SW1'],
                       target_devices=[device], device_id=device['id'], logical_intent_id='logical-vlan', status='rendered', configs=[output])
    plan = ExecutionPlan('Deterministic fixture, not live planning', tasks=[task], status='ready', runtime_authority='direct_files')
    data = dict(session_id=identity, created_at='2026-10-10T00:00:00Z', updated_at='2026-10-10T00:00:00Z',
                status='ready', schema_version=2, plan=asdict(plan), pending_questions=[], history=[])
    path.write_bytes(json.dumps(data, ensure_ascii=False).encode('utf-8'))

def controlled_interpret(instruction, schema, device, content):
    assert schema['properties']['new_vlan_name'] and device['id'] == 'lab-sw1'
    if instruction == 'Rename VLAN 20 from STAFF to ENGINEERING':
        return document_edits.Interpretation(outcome='edit', operation_id='rename_vlan', vlan_id=20, new_vlan_name='ENGINEERING', current_vlan_name='STAFF')
    if instruction == 'Rename VLAN 20 from ENGINEERING to FINANCE':
        assert 'name ENGINEERING' in content
        return document_edits.Interpretation(outcome='edit', operation_id='rename_vlan', vlan_id=20, new_vlan_name='FINANCE', current_vlan_name='ENGINEERING')
    return document_edits.Interpretation(outcome='unsupported')

document_edits.interpret = controlled_interpret
from app.workbench.api import create_app
import uvicorn
print('TEST ONLY: controlled interpreter; real catalog, renderer, API and persistence', flush=True)
uvicorn.run(create_app(), host='127.0.0.1', port=8000, log_level='warning')
