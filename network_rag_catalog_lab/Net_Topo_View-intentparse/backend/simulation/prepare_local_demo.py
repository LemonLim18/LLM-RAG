"""Explicit, idempotent preparation of labelled local scenario records.

Run from backend with .venv-m0/Scripts/python.exe simulation/prepare_local_demo.py.
Never changes inventory, existing profiles, templates, or existing approvals.
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lab_config import DB_PATH, FIXTURE_DIR, LOCAL_LAB
from db.manager import DatabaseManager
from db.models import ConfigSnapshot
from deploy.change_request import ChangeRequestService
from deploy.audit import AuditLogger
from local_providers.authoring import AuthoringStore
from local_providers.workflows import LocalWorkflowProvider

def prepare():
    if not LOCAL_LAB: raise RuntimeError('Scenario preparation requires local_lab')
    if not DB_PATH.exists(): raise RuntimeError('Start local backend to initialize your inventory first')
    backup=DB_PATH.with_suffix('.demo-backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'.db')
    with sqlite3.connect(DB_PATH) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    db=DatabaseManager(str(DB_PATH))
    provider=LocalWorkflowProvider(FIXTURE_DIR)
    fixture,_=provider.read(db)
    service=ChangeRequestService(db)
    audit=AuditLogger(db)
    with db._connect() as c:
        admin=c.execute("SELECT username FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
    if not admin: raise RuntimeError('An administrator account is required')
    actor=admin[0]
    for device in db.get_all_devices():
        config=provider.capture_config(fixture,device)
        title=f'[Local sample] Review configuration for {device.hostname}'
        with db._connect() as c:
            exists=c.execute('SELECT id FROM change_requests WHERE title=?',(title,)).fetchone()
            snapshot=c.execute("SELECT id FROM config_snapshots WHERE device_id=? AND description='[Local sample] Initial simulated running configuration'",(device.id,)).fetchone()
        if not snapshot:
            db.save_config_snapshot(ConfigSnapshot(device_id=device.id,config_text=config,description='[Local sample] Initial simulated running configuration',source_type='simulated_fixture',owner_username=actor))
        if not exists:
            request=service.create(title,actor,'Review this simulated configuration; no deployment is requested.\n\n'+config,actor)
            service.submit_for_approval(request.id,actor)
            audit.log(action='submit_for_approval',request_id=request.id,actor=actor,comment='Explicit local sample preparation; no remote action.')
        for entry in fixture.deployment_history:
            history_title=f'[Local sample] {entry.label}: {device.hostname}'
            with db._connect() as c:
                found=c.execute('SELECT id FROM change_requests WHERE title=?',(history_title,)).fetchone()
            if found: continue
            request=service.create(history_title,actor,entry.message+' No device command was executed.',actor)
            service.submit_for_approval(request.id,actor)
            service.approve(request.id,actor)
            with db._connect() as c:
                c.execute('INSERT INTO jobs(request_id,device_id,status,stage,generated_config,execution_engine,owner_username,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',(request.id,device.id,'simulated_'+entry.outcome,'fixture replay; no execution',config,'no_op',actor,entry.timestamp,entry.timestamp))
            audit.log(action='sample_history_import',request_id=request.id,actor=actor,comment=entry.message+' Source: JSON simulation; commands executed: 0.')
    # Keep original Studio baseline files unchanged; create a new revision-backed example.
    store=AuthoringStore(db)
    path='playbooks/local_observation_example.yml'
    if path not in store.entries('ansible'):
        store.mutate('ansible',path,'---\n- name: Local authoring example (not executed)\n  hosts: localhost\n  gather_facts: false\n  tasks:\n    - name: Explain local simulation\n      ansible.builtin.debug:\n        msg: "Inventory is SQLite; network observations are JSON."\n',actor,'create')
    print('Prepared labelled snapshots, review requests and Studio example. Existing records preserved. Database backup created.')
    db.close()

if __name__=='__main__': prepare()
