"""Start an isolated acceptance workspace; never migrates the ordinary database."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,choices=[8001],default=8001)
    parser.add_argument('--workspace',type=Path,required=True,help='Reuse an existing tmp/shared-ai-* acceptance workspace')
    args=parser.parse_args()
    from dev_local import port_in_use
    if any(port_in_use(port) for port in (8001,8002,5175,5176)):
        raise SystemExit('An acceptance/legacy server is already running. Reuse or stop it; only one acceptance environment is allowed.')
    workspace=args.workspace.resolve()
    if not workspace.is_relative_to((ROOT/'tmp').resolve()) or not workspace.name.startswith('shared-ai-'):
        raise ValueError('Acceptance workspace must be an explicit tmp/shared-ai-* directory')
    from llm.gateway_knowledge import read_release
    target=workspace/'knowledge/storage/catalog_releases'
    if not (workspace/'app.db').is_file() or not (workspace/'fixtures').is_dir():
        raise ValueError('Existing acceptance workspace is incomplete')
    release,_,pointer=read_release(target)
    os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_STUDIO_ENGINE='v9',
        COGNISHIELD_DB_PATH=str(workspace/'app.db'),COGNISHIELD_KNOWLEDGE_ROOT=str(workspace/'knowledge'),
        COGNISHIELD_FIXTURE_DIR=str(workspace/'fixtures'),AUTH_BYPASS_ROLES='0')
    # Reuse one explicit acceptance database; never create another workspace.
    from db.manager import DatabaseManager
    from db.models import Device, Interface
    database=DatabaseManager(str(workspace/'app.db'));database.initialize()
    database.upsert_device(Device(hostname='AI-LAB-EDGE',vendor='cisco_xe',model='C9300-24T',os_version='17.9',role='access',status='planned'))
    database.upsert_device(Device(hostname='AI-LAB-CORE',vendor='huawei_vrp',model='CloudEngine',os_version='V200R024C10',role='core',status='planned'))
    for device_id in [1,2]:
        for number in [1,2]: database.upsert_interface(Interface(device_id=device_id,name=f'GigabitEthernet1/0/{number}'))
    from db.local_migrations import ensure_local_schema
    from llm.gateway_store import ensure_schema
    ensure_local_schema(database._db_path);ensure_schema(database)
    # Deliberate sample facts, never inferred from a real device or copied to
    # ordinary inventory. They exercise the existing narrow V9 policy exactly.
    with database._connect() as conn:
        if conn.execute('SELECT engineering_facts_json FROM devices WHERE id=1').fetchone()[0]=='{}':
            conn.execute('UPDATE devices SET engineering_facts_json=? WHERE id=1',(json.dumps({
                'origin':'sample','model_family':'catalyst9300',
                'source_refs':{'fixture':'serve_ai_lab.py; planned demonstration, not discovery'},
                'capabilities':{'features':['vlan'],'validated_policies':['c9300_vlan_rename_v1'],'vtp_mode':'transparent'},
                'vlans':[{'vlan_id':100,'name':'STAFF'}]}),))
    from local_providers.authoring import AuthoringStore
    store=AuthoringStore(database)
    for path,content in [('playbooks/shared_demo.py','def add(a, b):\n    return a + b\n'),
                         ('playbooks/shared_ospf.cfg','router ospf 1\n network 192.0.2.0 0.0.0.255 area 0\n')]:
        if not store.latest('ansible',path) and not store.resolve('ansible',path).is_file():
            store.mutate('ansible',path,content,'acceptance','create',expected_revision=0)
    database.close()
    import local_app
    import auth.auth as auth_module
    assert Path(local_app.DB_PATH).resolve()==(workspace/'app.db').resolve()
    assert Path(local_app.inventory.DB_PATH).resolve()==(workspace/'app.db').resolve()
    assert Path(auth_module._DB_PATH).resolve()==(workspace/'app.db').resolve()
    app=local_app.app
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5174'],allow_methods=['*'],allow_headers=['*'],allow_private_network=True)
    print(json.dumps({'workspace':str(workspace),'port':args.port,'source_release':release.name,'ordinary_database_modified':False}),flush=True)
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=args.port)


if __name__=='__main__': main()
