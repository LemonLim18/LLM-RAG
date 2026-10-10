"""Test-only persisted-session server. Never uses the user's session/artifact storage."""
from dataclasses import asdict
import json
from pathlib import Path
import sys

import app.config as config
from app.planner.models import ExecutionPlan, PlannedTask

root = Path(sys.argv[1]).resolve()
if not root.is_dir() or not root.name.startswith('v9-original-browser-'):
    raise RuntimeError('A dedicated temporary test directory is required')
config.STORAGE_DIR = root
config.SESSIONS_DIR = root / 'sessions'
config.SESSIONS_DIR.mkdir(exist_ok=True)
identity = '00000000-0000-4000-8000-000000000111'
path = config.SESSIONS_DIR / f'{identity}.json'
if not path.exists():
    device = dict(id='dev-r1', hostname='R1', vendor='cisco', platform='ios', version='15')
    output = dict(device_id='dev-r1', hostname='R1', vendor='cisco', platform='ios', version='15',
                  configuration='! persisted integration original\r\nrouter ospf 10\r\n  ! exact whitespace  \r\n')
    task = PlannedTask('task-r1', 'Configure OSPF', 'routing', 'configure_ospf', {}, ['R1'], target_devices=[device],
                       device_id='dev-r1', logical_intent_id='logical-ospf', status='rendered', configs=[output])
    plan = ExecutionPlan('Configure OSPF', tasks=[task], status='ready', runtime_authority='direct_files')
    data = dict(session_id=identity, created_at='2026-10-09T00:00:00Z', updated_at='2026-10-09T00:00:00Z',
                status='ready', schema_version=2, plan=asdict(plan), pending_questions=[], history=[])
    # Same full version-2 serializer shape. No planner/model initialization.
    path.write_bytes(json.dumps(data, ensure_ascii=False).encode('utf-8'))

from app.workbench.api import create_app
import uvicorn

assert not any(module in sys.modules for module in ('app.clarification', 'app.pipeline', 'langchain_ollama', 'chromadb'))
uvicorn.run(create_app(), host='127.0.0.1', port=8000, log_level='warning')
