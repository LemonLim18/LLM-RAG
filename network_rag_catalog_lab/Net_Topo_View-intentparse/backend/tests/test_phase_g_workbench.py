"""Independent authoring/reader boundaries; no real model score is inferred."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from development.bundles import compile_bundle,load_bundle,safe_file
from development.source_registry import SOURCES
from local_providers.development import ScenarioManager


def draft_bundle():
    stamp='2026-10-19T01:00:00Z'
    sources={entry.key:{'schema_version':'1.0','category':entry.key,'status':'MISSING','captured_at':stamp,
        'data':{'records':[]}} for entry in SOURCES}
    sources['inventory'].update(status='AVAILABLE',data={'complete':True,'devices':[
        dict(id=7001,hostname='LAB-R1',management_ip='192.0.2.171',vendor='cisco_xe',os_version='17.9')],
        'interfaces':[dict(id=701,device_id=7001,name='GigabitEthernet1',prefix='10.77.0.1/30',admin_status='up',oper_status='up')]})
    sources['topology_planned']['data']={'links':[]}
    for key in ['documents','attachments','diagrams']:sources[key]['data']={'files':[]}
    sources['knowledge']['data']={'release_policy':'active_immutable_release','mutable':False,'query':'Published OSPF operation requirements'}
    sources['simulation']['data']={}
    sources['conversation']['data']={'turns':[],'assistant_kind':'floating'}
    record=lambda key,kind,text,current:dict(id=key,device_id=7001,interface_id=None,timestamp=stamp,
        kind=kind,source='scenario-author',current=current,depends_on=[],values={'config_text':text})
    sources['running_configs'].update(status='AVAILABLE',data={'records':[record('current-r1','running_configuration','hostname LAB-R1\r\n! T1 \u4e2d\r\n',True)]})
    sources['config_snapshots'].update(status='AVAILABLE',data={'records':[record('saved-r1','configuration_snapshot','hostname LAB-R1\r\n! ORIGINAL\r\n',False)]})
    return {'manifest':{'schema_version':'1.0','scenario_id':'S-TEST-BUNDLE','name':'Independent edited sources',
        'scenario_revision':1,'created_by':'test-author','created_at':stamp,'mode':'development_scenario',
        'clock':{'now':stamp,'timezone':'UTC','paused':True,'rate':0},
        'source_files':{entry.key:entry.key+'.json' for entry in SOURCES},
        'policy':{'real_device_access':False,'deploy_allowed':False}},'sources':sources,'assets':{}}


@pytest.mark.parametrize('scope',['current','historical','both'])
def test_named_change_reader_does_not_substitute_configuration_text(tmp_path,scope):
    from llm.gateway_network import NetworkQuery
    bundle=load_bundle(Path(__file__).resolve().parents[1]/'development/scenarios/healthy_all_sources_v2')
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    saved=manager.save_draft(bundle,owner='alice',expected=None)
    receipt=manager.validate_draft(saved['draft_id'],owner='alice',expected=saved['draft_revision'])
    manager.activate_draft(saved['draft_id'],owner='alice',expected=saved['draft_revision'],expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    result=manager.result('configuration',NetworkQuery(source_scope=scope,source_categories=['config_changes']),[manager.inventory()['devices'][0]])
    assert len(result.data['records'])==1 and result.data['records'][0]['kind']=='configuration_change'


def test_full_bundle_retains_known_unavailable_dependencies_without_content_leak(tmp_path):
    from llm.gateway_network import NetworkQuery
    bundle=load_bundle(Path(__file__).resolve().parents[1]/'development/scenarios/healthy_all_sources_v2')
    bundle['sources']['running_configs']['status']='ERROR'
    scenario=compile_bundle(bundle)
    assert not scenario['records']['running_configuration']
    assert scenario['unavailable_record_refs']['active-1100']=='running_configs'
    change=next(row for row in scenario['records']['configuration'] if row['kind']=='configuration_change')
    assert 'active-1100' in change['depends_on']
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    saved=manager.save_draft(bundle,owner='alice',expected=None)
    receipt=manager.validate_draft(saved['draft_id'],owner='alice',expected=saved['draft_revision'])
    manager.activate_draft(saved['draft_id'],owner='alice',expected=saved['draft_revision'],expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    changes=manager.result('configuration',NetworkQuery(source_categories=['config_changes']),[manager.inventory()['devices'][0]])
    assert changes.data['records'][0]['unavailable_dependencies']==[{'record_ref':'active-1100','source_category':'running_configs','status':'ERROR'}]
    current=manager.result('configuration',NetworkQuery(source_scope='current',source_categories=['running_configs']),manager.inventory()['devices'])
    assert current.status=='error' and not current.data['records']
    broken=deepcopy(bundle);broken['sources']['config_changes']['data']['records'][0]['depends_on']=['never-declared']
    with pytest.raises(ValueError,match='Invalid evidence dependency'):compile_bundle(broken)


def test_current_configuration_reports_status_and_never_substitutes_saved_text(tmp_path):
    from db.manager import DatabaseManager
    from llm.gateway_services import registry_for
    from llm.tools import ToolAuthorization
    from llm.gateway_findings import network_answer
    db=DatabaseManager(str(tmp_path/'ordinary.db'));db.initialize()
    manager=ScenarioManager(tmp_path/'scenario.json',enabled_default=False);db._development_scenario=manager
    try:
        for status in ['AVAILABLE','STALE','ERROR','MISSING']:
            bundle=draft_bundle();bundle['sources']['running_configs']['status']=status
            saved=manager.save_draft(bundle,owner='alice',expected=None)
            receipt=manager.validate_draft(saved['draft_id'],owner='alice',expected=saved['draft_revision'])
            manager.activate_draft(saved['draft_id'],owner='alice',expected=saved['draft_revision'],expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
            auth=ToolAuthorization('alice','engineer','floating','test',frozenset({'network.configuration'}))
            result=asyncio.run(registry_for(db).invoke('network.configuration',{'device_refs':['7001'],'source_scope':'current','source_categories':['running_configs'],'query':'Show current running configuration'},auth))
            answer=network_answer([{'tool':'network.configuration','status':result.status,'message':result.message,'data':result.data,'scope_devices':[{'id':7001,'hostname':'LAB-R1'}],'evidence_ids':[result.evidence[0].id]}],result.evidence,question='Show current running configuration')
            assert status in answer and '2026-10-19T01:00:00' in answer
            assert 'LAB-R1' in answer
            assert '! ORIGINAL' not in answer
            if status in {'ERROR','MISSING'}:assert not result.data['records'] and '! T1' not in answer
            else:assert '! T1' in answer
            if status=='STALE':
                assert 'current simulated running configuration' not in answer
                assert result.evidence[0].freshness=='stale'
    finally:db.close()


def test_24_source_compiler_preserves_current_saved_text_and_statuses():
    bundle=draft_bundle();scenario=compile_bundle(bundle)
    assert len(scenario['source_statuses'])==24
    assert scenario['records']['running_configuration'][0]['values']['config_text'].endswith('! T1 \u4e2d\r\n')
    assert scenario['records']['configuration'][0]['current'] is False
    assert scenario['source_statuses']['telemetry']['status']=='MISSING'
    assert scenario['availability']['telemetry'] is False


def test_inventory_reader_preserves_authored_capture_and_source_availability(tmp_path):
    from db.manager import DatabaseManager
    from llm.gateway_services import registry_for
    from llm.tools import ToolAuthorization
    from llm.gateway_findings import network_answer
    db=DatabaseManager(str(tmp_path/'ordinary.db'));db.initialize()
    manager=ScenarioManager(tmp_path/'scenario.json',enabled_default=False);db._development_scenario=manager
    try:
        for status in ['AVAILABLE','STALE','ERROR','MISSING']:
            bundle=draft_bundle();bundle['sources']['inventory']['status']=status
            bundle['sources']['inventory']['captured_at']='2026-10-19T00:59:00Z'
            saved=manager.save_draft(bundle,owner='alice',expected=None)
            receipt=manager.validate_draft(saved['draft_id'],owner='alice',expected=saved['draft_revision'])
            manager.activate_draft(saved['draft_id'],owner='alice',expected=saved['draft_revision'],expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
            with patch.dict(os.environ,{'COGNISHIELD_MODE':'local_lab'}):
                auth=ToolAuthorization('alice','engineer','floating','test',frozenset({'inventory.read'}))
                result=asyncio.run(registry_for(db).invoke('inventory.read',{},auth))
            assert result.evidence[0].captured_at=='2026-10-19T00:59:00+00:00'
            assert result.evidence[0].origin=='simulated'
            answer=network_answer([{'tool':'inventory.read','status':result.status,'message':result.message,'data':result.data,'evidence_ids':[result.evidence[0].id]}],result.evidence,['management_address'])
            if status in {'ERROR','MISSING'}:
                assert result.status in {'error','unavailable'}
                assert result.data['devices']==[]
                assert status in answer and 'unavailable' in answer.lower()
                assert '192.0.2.171' not in answer
            else:
                assert result.status=='success'
                assert '192.0.2.171' in answer and '2026-10-19T00:59:00' in answer
                if status=='STALE':assert result.evidence[0].freshness=='stale'
        with db._connect() as c:assert c.execute('SELECT COUNT(*) FROM devices').fetchone()[0]==0
    finally:db.close()


def test_recognized_compound_device_name_does_not_invent_an_unknown_suffix():
    from llm.gateway_network import route_network
    inventory={'devices':[{'id':1,'hostname':'LAB-R1','management_ip':'192.0.2.10','aliases':[],'interfaces':[]}]}
    assert route_network('What is the current configuration for LAB-R1?',inventory)[1]['device_refs']==['LAB-R1']
    assert route_network('Compare LAB-R1 with R1.',inventory)[1]['device_refs']==['LAB-R1','R1']


def test_literal_current_config_request_is_distinct_from_explanation_or_comparison():
    from llm.gateway_references import configuration_text_request
    for prompt in ['What is the current configuration for LAB-R1?','Show LAB-R1 current running configuration after the activated edit.','Read the saved configuration for LAB-R1.']:
        assert configuration_text_request(prompt)
    for prompt in ['Explain what the current configuration does.','Compare current configuration with backups.','What changed in the configuration?','Generate a configuration.']:
        assert not configuration_text_request(prompt)


def test_editing_bundle_draft_does_not_change_active_reader(tmp_path):
    manager=ScenarioManager(tmp_path/'state.json');bundle=draft_bundle()
    revision=manager.snapshot()[1]['source_revision']
    saved=manager.save_draft(bundle,owner='alice',expected=None)
    assert manager.snapshot()[1]['source_revision']==revision
    receipt=manager.validate_draft(saved['draft_id'],owner='alice',expected=saved['draft_revision'])
    manager.activate_draft(saved['draft_id'],owner='alice',expected=saved['draft_revision'],expected_active=revision,validation_hash=receipt['validation_hash'])
    scenario,meta=manager.snapshot();assert scenario['id']=='S-TEST-BUNDLE'
    with manager.pin():
        before=manager.snapshot()
        changed=deepcopy(bundle);changed['sources']['running_configs']['data']['records'][0]['values']['config_text']='! T2\n'
        updated=manager.save_draft(changed,owner='alice',expected=saved['draft_revision'],draft_id=saved['draft_id'])
        check=manager.validate_draft(saved['draft_id'],owner='alice',expected=updated['draft_revision'])
        manager.activate_draft(saved['draft_id'],owner='alice',expected=updated['draft_revision'],expected_active=meta['source_revision'],validation_hash=check['validation_hash'])
        assert manager.snapshot()==before
    assert manager.snapshot()[0]['records']['running_configuration'][0]['values']['config_text']=='! T2\n'
    assert manager.snapshot()[0]['records']['configuration'][0]['values']['config_text'].endswith('! ORIGINAL\r\n')
    assert any(r['values']['config_text'].endswith('! T1 \u4e2d\r\n') for r in manager.snapshot()[0]['records']['configuration'])


def test_draft_owner_validation_and_mode_activation_boundaries(tmp_path):
    from fastapi import HTTPException
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    initial=manager.snapshot()[1]['source_revision'];draft=manager.save_draft(draft_bundle(),owner='alice',expected=None)
    assert not manager.is_enabled()
    with pytest.raises(HTTPException):manager.get_draft(draft['draft_id'],owner='bob')
    with pytest.raises(HTTPException):manager.activate_draft(draft['draft_id'],owner='alice',expected=1,expected_active=initial,validation_hash='0'*64)
    check=manager.validate_draft(draft['draft_id'],owner='alice',expected=1)
    manager.activate_draft(draft['draft_id'],owner='alice',expected=1,expected_active=initial,validation_hash=check['validation_hash'])
    assert manager.is_enabled()
    current=manager.snapshot()[1]['source_revision'];manager.deactivate(owner='alice',expected_active=current)
    assert not manager.is_enabled()


def test_actual_authenticated_api_and_existing_authorized_configuration_reader(tmp_path):
    import httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from llm.gateway_store import ensure_schema
    from llm.gateway import AIGateway
    from llm.tools import ToolAuthorization
    from local_providers.development_api import router
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    db._development_scenario=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    app=FastAPI();app.state.local_db=db;app.include_router(router)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            endpoint='/api/v1/development-network/workbench'
            assert (await client.get(endpoint)).status_code==401
            assert (await client.get(endpoint+'/starter?variant=acl')).status_code==401
            client.headers['Authorization']='Bearer '+create_access_token(900,'alice','engineer')
            assert (await client.post(endpoint+'/drafts',json={'bundle':draft_bundle()})).status_code==403
            assert (await client.get(endpoint+'/starter?variant=conflict')).status_code==403
            client.headers['Authorization']='Bearer '+create_access_token(900,'alice','admin')
            status=(await client.get(endpoint)).json();assert status['enabled'] is False
            for variant in ['healthy','acl','conflict']:
                template=await client.get(endpoint+'/starter',params={'variant':variant})
                assert template.status_code==200
                assert len(compile_bundle(template.json())['source_statuses'])==24
            assert (await client.get(endpoint+'/starter?variant=not-a-starter')).status_code==422
            assert db._development_scenario.is_enabled() is False
            response=await client.post(endpoint+'/drafts',json={'bundle':draft_bundle()});assert response.status_code==200,response.text
            draft=response.json();identity=draft['draft_id']
            receipt=(await client.post(endpoint+'/drafts/'+identity+'/validate',json={'expected_revision':1})).json()
            response=await client.post(endpoint+'/drafts/'+identity+'/activate',json={'expected_revision':1,'expected_active':status['context']['source_revision'],'validation_hash':receipt['validation_hash']})
            assert response.status_code==200,response.text
            gateway=AIGateway(db);cid=gateway.store.create('alice','floating')['id']
            auth=ToolAuthorization('alice','admin','floating',cid,frozenset({'network.configuration'}))
            result=await gateway.registry.invoke('network.configuration',{'device_refs':['LAB-R1'],'source_scope':'current'},auth)
            assert result.status=='success' and result.evidence[0].origin=='simulated'
            from llm.gateway_network import timestamp
            assert timestamp(result.evidence[0].captured_at)==timestamp('2026-10-19T01:00:00Z')
            assert result.data['records'][0]['config_text'].endswith('! T1 \u4e2d\r\n')
            client.headers['Authorization']='Bearer '+create_access_token(901,'bob','admin')
            assert (await client.get(endpoint+'/drafts/'+identity)).status_code==404
    try:
        with patch.dict(os.environ,{'COGNISHIELD_DEV_WORKBENCH':'1','COGNISHIELD_DEV_SIMULATION':'0'}):asyncio.run(exercise())
    finally:db.close()


def test_linked_paths_and_external_file_edits_require_explicit_validation(tmp_path):
    bundle=draft_bundle();root=tmp_path/'bundle';root.mkdir()
    (root/'manifest.json').write_text(json.dumps(bundle['manifest']),encoding='utf-8')
    for key,value in bundle['sources'].items():(root/(key+'.json')).write_text(json.dumps(value),encoding='utf-8')
    (root/'configs').mkdir();(root/'configs/r1.cfg').write_bytes(b'hostname LAB-R1\r\n! FILE\r\n')
    source=bundle['sources']['running_configs'];values=source['data']['records'][0]['values']
    values.pop('config_text');values['config_file']='configs/r1.cfg'
    (root/'running_configs.json').write_text(json.dumps(source),encoding='utf-8')
    loaded=load_bundle(root);assert compile_bundle(loaded)['records']['running_configuration'][0]['values']['config_text'].endswith('! FILE\r\n')
    (root/'configs/r1.cfg').write_bytes(b'hostname LAB-R1\n! EDITED\n')
    assert compile_bundle(loaded)['records']['running_configuration'][0]['values']['config_text'].endswith('! FILE\r\n')
    assert compile_bundle(load_bundle(root))['records']['running_configuration'][0]['values']['config_text'].endswith('! EDITED\n')
    for value in ['../secret','.env','test_oracles/expected.json','C:/secret','configs\\r1.cfg']:
        with pytest.raises(ValueError):safe_file(root,value)
    private=tmp_path/'test_oracles';private.mkdir();(private/'manifest.json').write_text('{}')
    with pytest.raises(ValueError,match='oracle'):load_bundle(private)


def test_invalid_temporal_metric_and_authorization_metadata_are_rejected():
    bundle=draft_bundle();bundle['manifest']['policy']['real_device_access']=True
    with pytest.raises(ValueError):compile_bundle(bundle)
    bundle=draft_bundle();bundle['sources']['telemetry'].update(status='AVAILABLE',data={'records':[
        dict(id='cpu',device_id=7001,timestamp='2026-10-19T01:00:00Z',kind='metric_sample',source='collector',values={'value':110,'unit':'percent'})]})
    with pytest.raises(ValueError):compile_bundle(bundle)


def test_generated_source_schemas_validate_the_actual_starter():
    from development.starter import starter_bundle
    from development.bundles import source_schema
    from jsonschema import Draft202012Validator
    bundle=starter_bundle()
    for source in SOURCES:
        validator=Draft202012Validator(source_schema(source.key))
        validator.validate(bundle['sources'][source.key])
    bundle=draft_bundle();bundle['sources']['running_configs']['data']['records'][0]['timestamp']='2030-01-01T00:00:00Z'
    with pytest.raises(ValueError):compile_bundle(bundle)


@pytest.mark.parametrize('variant',['healthy','acl','conflict'])
def test_distinct_complete_starters_retain_all_sources_and_declared_differences(variant):
    from development.starter import starter_bundle
    from development.bundles import source_schema
    from development.network_model import NetworkModel,assess_flow,protocol_findings
    from jsonschema import Draft202012Validator
    bundle=starter_bundle(variant)
    for source in SOURCES:Draft202012Validator(source_schema(source.key)).validate(bundle['sources'][source.key])
    scenario=compile_bundle(bundle);model=NetworkModel.model_validate(scenario['network'])
    result=assess_flow(scenario,model.flows[0])
    assert len(bundle['sources'])==24 and len(bundle['assets'])>=3
    assert not bundle['manifest']['policy']['real_device_access']
    if variant=='acl':
        assert bundle['manifest']['scenario_id']!='S-HEALTHY-ALL-SOURCES'
        assert result['forward']['status']=='failed'
        assert any('policy' in str(branch.get('reason','')).lower() for branch in result['forward']['branches'])
        saved=bundle['sources']['config_snapshots']['data']['records'][1]['values']['config_text']
        current=bundle['sources']['running_configs']['data']['records'][1]['values']['config_text']
        assert 'reviewed-filter' in current and 'reviewed-filter' not in saved
        assert 'no adjacency transition' not in bundle['sources']['syslog']['data']['records'][0]['values']['message']
    elif variant=='conflict':
        assert bundle['manifest']['scenario_id']!='S-HEALTHY-ALL-SOURCES'
        assert bundle['sources']['syslog']['status']=='STALE'
        assert bundle['sources']['protocol_state']['status']=='CONFLICTING'
        assert any(finding.get('conflict') for finding in protocol_findings(model))
    else:assert result['forward']['status']=='delivered' and result['return']['status']=='delivered'


def test_cli_linked_starter_roundtrip_uses_text_assets_and_preserves_snapshots():
    import tempfile
    from types import SimpleNamespace
    from scripts.development_scenario import main,ROOT
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/phase-g',prefix='starter-roundtrip-') as directory:
        target=Path(directory)/'bundle'
        args=SimpleNamespace(command='bundle-create',variant='acl',id='S-CLI-ACL',linked_configs=True,output=str(target))
        asyncio.run(main(args))
        bundle=load_bundle(target);scenario=compile_bundle(bundle)
        assert len(bundle['sources'])==24
        current=bundle['sources']['running_configs']['data']['records'][1]['values']
        saved=bundle['sources']['config_snapshots']['data']['records'][1]['values']
        assert current['config_file']!=saved['config_file']
        assert 'reviewed-filter' in bundle['assets'][current['config_file']]
        assert 'reviewed-filter' not in bundle['assets'][saved['config_file']]
        assert scenario['records']['running_configuration'][1]['values']['config_text']==(target/current['config_file']).read_text()
        with pytest.raises(ValueError,match='must not already exist'):asyncio.run(main(args))


def test_one_direction_policy_drop_is_confirmed_in_scope_despite_healthy_return(tmp_path):
    from development.starter import starter_bundle
    from llm.gateway_network import NetworkQuery
    from llm.orchestration.scenario_reasoning import assess_scenario
    manager=ScenarioManager(tmp_path/'state.json');bundle=starter_bundle('acl')
    draft=manager.save_draft(bundle,owner='alice',expected=None)
    receipt=manager.validate_draft(draft['draft_id'],owner='alice',expected=1)
    manager.activate_draft(draft['draft_id'],owner='alice',expected=1,
        expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    result=manager.result('state',NetworkQuery(),manager.inventory()['devices'])
    assessment=assess_scenario([{'tool':'network.state','status':'success','data':result.data,
        'evidence_ids':[result.evidence[0].id]}],result.evidence)
    assert assessment['conclusion_status']=='confirmed_within_scenario'
    assert any('LAB-R2' in text and 'ge-0/0/0.0' in text and 'ingress' in text for text in assessment['findings'])


def test_activated_document_bytes_are_sealed_pinned_and_not_read_in_ordinary_mode(tmp_path):
    import base64,hashlib
    from uuid import uuid4
    from db.manager import DatabaseManager
    from llm.gateway import AIGateway
    from llm.gateway_models import TurnRequest
    from llm.gateway_store import ensure_schema
    from llm.tools import ToolAuthorization
    bundle=draft_bundle();raw=b'# Development note\nThe maintenance window is 17:40 UTC.\n'
    bundle['sources']['documents'].update(status='AVAILABLE',data={'files':[{'path':'docs/window.md','name':'Maintenance.md'}]})
    bundle['assets']['docs/window.md']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False);db._development_scenario=manager
    def activate(value,draft_id=None,expected=None):
        entry=manager.save_draft(value,owner='alice',draft_id=draft_id,expected=expected)
        receipt=manager.validate_draft(entry['draft_id'],owner='alice',expected=entry['draft_revision'])
        manager.activate_draft(entry['draft_id'],owner='alice',expected=entry['draft_revision'],expected_active=manager.snapshot(fresh=True)[1]['source_revision'],validation_hash=receipt['validation_hash'])
        return entry
    async def exercise():
        saved=activate(bundle)
        gateway=AIGateway(db)
        for surface in ['floating','studio']:
            cid=gateway.store.create('alice',surface)['id']
            auth=ToolAuthorization('alice','admin',surface,cid,frozenset({'document.read'}))
            body=TurnRequest(request_id=uuid4(),prompt='What does Maintenance.md say?')
            with manager.pin():
                result=await gateway.registry.invoke('document.read',{'turn':body.model_dump(mode='json')},auth)
                assert result.status=='success'
                assert any('17:40 UTC' in row['text'] for row in result.data['context'])
                assert result.evidence[0].origin=='simulated'
                assert result.evidence[0].captured_at=='2026-10-19T01:00:00+00:00'
                # Saving a new draft cannot mutate bytes of the activated revision.
                changed=deepcopy(bundle);replacement=b'# Development note\nWindow moved to 18:20 UTC.\n'
                changed['assets']['docs/window.md']={'base64':base64.b64encode(replacement).decode(),'sha256':hashlib.sha256(replacement).hexdigest()}
                edited=manager.save_draft(changed,owner='alice',draft_id=saved['draft_id'],expected=saved['draft_revision'])
                assert manager.activated_bundle()['assets']['docs/window.md']==bundle['assets']['docs/window.md']
                saved=manager.save_draft(bundle,owner='alice',draft_id=saved['draft_id'],expected=edited['draft_revision'])
        with db._connect() as connection:assert connection.execute('SELECT count(*) FROM ai_attachments').fetchone()[0]==0
        manager.deactivate(owner='alice',expected_active=manager.snapshot()[1]['source_revision'])
        result=await gateway.registry.invoke('document.read',{'turn':body.model_dump(mode='json')},auth)
        assert result.data['context']==[]
    try:
        with patch.dict(os.environ,{'COGNISHIELD_DEV_WORKBENCH':'1','COGNISHIELD_DEV_SIMULATION':'0'}):asyncio.run(exercise())
    finally:db.close()


def test_asset_digest_and_file_extension_are_validated_before_activation():
    from development.starter import starter_bundle
    bundle=starter_bundle();bundle['assets']['docs/operations.md']['sha256']='0'*64
    with pytest.raises(ValueError,match='digest'):compile_bundle(bundle)
    bundle=starter_bundle();bundle['sources']['documents']['data']['files'][0]['name']='script.exe'
    with pytest.raises(ValueError,match='type'):compile_bundle(bundle)


def test_corrupt_sealed_bundle_fails_closed_but_existing_turn_keeps_its_pin(tmp_path):
    from fastapi import HTTPException
    from development.starter import starter_bundle
    manager=ScenarioManager(tmp_path/'state.json');bundle=starter_bundle()
    draft=manager.save_draft(bundle,owner='alice',expected=None)
    receipt=manager.validate_draft(draft['draft_id'],owner='alice',expected=1)
    manager.activate_draft(draft['draft_id'],owner='alice',expected=1,expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    with manager.pin():
        sealed=manager.activated_bundle()
        state=manager._read();state['workbench_bundles'][state['selected']]['assets']['docs/operations.md']['base64']='dGFtcGVyZWQ='
        manager._write(state)
        assert manager.activated_bundle()==sealed
    with pytest.raises(HTTPException) as failure:manager.activated_bundle()
    assert failure.value.status_code==503 and 'integrity' in failure.value.detail


def test_store_quota_rejection_preserves_the_readable_state(tmp_path):
    from fastapi import HTTPException
    manager=ScenarioManager(tmp_path/'state.json');before=manager.path.read_bytes()
    with pytest.raises(HTTPException):manager._write({**manager._read(),'oversized':'x'*16_000_001})
    assert manager.path.read_bytes()==before


def test_malformed_document_fields_have_actionable_source_pointer():
    from development.starter import starter_bundle
    bundle=starter_bundle();bundle['sources']['documents']['data']['files'][0]['name']={'not':'a filename'}
    with pytest.raises(ValueError,match=r'documents.json#/data/files/0/name'):compile_bundle(bundle)


def test_scenario_conversation_setup_uses_user_requests_only():
    bundle=draft_bundle();bundle['sources']['conversation']['data']={'turns':[{'role':'assistant','content':'Invented successful read'}]}
    with pytest.raises(ValueError):compile_bundle(bundle)


def test_simulation_source_selector_and_unavailable_status_do_not_leak_model_rows(tmp_path):
    from development.starter import starter_bundle
    from llm.gateway_network import NetworkQuery
    bundle=starter_bundle();manager=ScenarioManager(tmp_path/'state.json')
    def activate():
        entry=manager.save_draft(bundle,owner='alice',expected=None)
        receipt=manager.validate_draft(entry['draft_id'],owner='alice',expected=1)
        manager.activate_draft(entry['draft_id'],owner='alice',expected=1,expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    activate();query=NetworkQuery(source_categories=['simulation'])
    result=manager.result('state',query,manager.inventory()['devices'])
    assert result.status=='success' and result.data['records']
    assert all(r['source_category']=='simulation' for r in result.data['records'])
    assert any(r['kind']=='forwarding_assessment' for r in result.data['records'])
    bundle['sources']['simulation']['status']='UNAVAILABLE';activate()
    result=manager.result('state',query,manager.inventory()['devices'])
    assert result.status=='unavailable' and result.data['records']==[]
    assert result.data['source_statuses']['simulation']=='UNAVAILABLE'


def test_assessment_uses_authorized_records_not_display_truncation(tmp_path):
    from development.starter import starter_bundle
    from llm.gateway_network import NetworkQuery
    from llm.orchestration.verification import assessment_context
    from llm.orchestration.scenario_reasoning import assess_scenario
    manager=ScenarioManager(tmp_path/'state.json');bundle=starter_bundle()
    entry=manager.save_draft(bundle,owner='alice',expected=None);receipt=manager.validate_draft(entry['draft_id'],owner='alice',expected=1)
    manager.activate_draft(entry['draft_id'],owner='alice',expected=1,expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    result=manager.result('state',NetworkQuery(),manager.inventory()['devices'])
    assert result.data['truncated'] is False
    display=deepcopy(result.data);display['truncated']=True
    display['records']=[r for r in display['records'] if r['kind'] in {'forwarding_assessment','protocol_assessment'}]
    context=[{'tool':'network.state','status':'success','data':display,'evidence_ids':[result.evidence[0].id]}]
    full=assessment_context(context,[('network.state',result)])
    assessment=assess_scenario(full,result.evidence)
    assert assessment['conclusion_status']=='healthy_within_tested_scope'
    from llm.orchestration.synthesis import projection
    hidden=deepcopy(context);hidden[0]['data']['records']=[]
    packet=projection(assessment_context(hidden,[('network.state',result)]),result.evidence,assessment,'Investigate whether these routers can communicate using the recorded topology and forwarding evidence.',investigation=True)
    assert packet['forwarding_results'][0]['forward']['status']=='delivered'
    assert packet['forwarding_results'][0]['return']['status']=='delivered'
    assert any('Egress sequence' in finding for finding in assessment['findings'])
    assert not any(' → ' in finding and '(' in finding for finding in assessment['findings'])
    partial=result.model_copy(deep=True);partial.data['truncated']=True
    assert assess_scenario(assessment_context(context,[('network.state',partial)]),partial.evidence)['conclusion_status']=='insufficient_evidence'


def test_health_reader_exposes_effective_status_without_overwriting_authored_claim(tmp_path):
    from development.starter import starter_bundle
    from llm.gateway_network import NetworkQuery
    manager=ScenarioManager(tmp_path/'state.json');bundle=starter_bundle()
    bundle['sources']['source_health']['data']['overrides']=[{'category':'telemetry','status':'ERROR'}]
    draft=manager.save_draft(bundle,owner='alice',expected=None)
    receipt=manager.validate_draft(draft['draft_id'],owner='alice',expected=1)
    manager.activate_draft(draft['draft_id'],owner='alice',expected=1,
        expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    devices=manager.inventory()['devices']
    telemetry=manager.result('telemetry',NetworkQuery(source_categories=['telemetry']),devices)
    assert telemetry.status=='error' and telemetry.data['records']==[]
    health=manager.result('state',NetworkQuery(source_categories=['source_health']),devices)
    assert health.data['records'][0]['sources']['telemetry']=='AVAILABLE'
    assert health.data['effective_source_statuses']['telemetry']['status']=='ERROR'
    assert health.data['effective_source_statuses']['source_health']['status']=='AVAILABLE'
    assert 'effective_source_statuses' not in manager.result('state',NetworkQuery(source_categories=['controller_state']),devices).data


def test_conflicting_current_interface_records_are_not_hidden_by_forwarding_model(tmp_path):
    from development.starter import starter_bundle
    from llm.gateway_network import NetworkQuery
    from llm.orchestration.scenario_reasoning import assess_scenario
    manager=ScenarioManager(tmp_path/'state.json');bundle=starter_bundle()
    bundle['sources']['device_state']['data']['records'][0]['values'].update(admin_status='down',oper_status='down')
    entry=manager.save_draft(bundle,owner='alice',expected=None);receipt=manager.validate_draft(entry['draft_id'],owner='alice',expected=1)
    manager.activate_draft(entry['draft_id'],owner='alice',expected=1,expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    result=manager.result('state',NetworkQuery(),manager.inventory()['devices'])
    assessment=assess_scenario([{'tool':'network.state','status':'success','data':result.data,'evidence_ids':[result.evidence[0].id]}],result.evidence)
    assert assessment['conclusion_status']=='conflicting_evidence'
    assert any('interface' in c for c in assessment['conflicts'])


def test_ocr_text_does_not_certify_visual_connection_types_or_absence():
    from llm.orchestration.verification import ocr_visual_errors
    documents=[{'text':'LAB-RI Cisco IOS-XE\nLAB-R2 Junos','extraction':'ocr'}]
    assert ocr_visual_errors('The illustration does not show actual physical connections, only logical connections.',documents)
    assert ocr_visual_errors('The illustration includes links between the devices.',documents)
    assert ocr_visual_errors('The illustration shows the network layout and connections between the devices.',documents)
    assert not ocr_visual_errors('The OCR text lists Cisco IOS-XE and Junos. Visual relationships have not been verified.',documents)
    assert not ocr_visual_errors('Logical connections are depicted.',documents,vision_available=True)


def test_uploaded_file_questions_do_not_silently_mix_scenario_documents(tmp_path):
    import base64,hashlib
    from uuid import uuid4
    from db.manager import DatabaseManager
    from llm.gateway import AIGateway
    from llm.gateway_models import TurnRequest
    from llm.gateway_store import ensure_schema
    from llm.gateway_documents import upload_attachment,build_context
    bundle=draft_bundle();raw=b'SCENARIO_DOC_ONLY'
    bundle['sources']['documents'].update(status='AVAILABLE',data={'files':[{'path':'docs/scenario.md','name':'Scenario.md'}]})
    bundle['assets']['docs/scenario.md']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    manager=ScenarioManager(tmp_path/'state.json');db._development_scenario=manager
    entry=manager.save_draft(bundle,owner='alice',expected=None);receipt=manager.validate_draft(entry['draft_id'],owner='alice',expected=1)
    manager.activate_draft(entry['draft_id'],owner='alice',expected=1,expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    gateway=AIGateway(db);cid=gateway.store.create('alice','floating')['id']
    async def exercise():
        await upload_attachment(db,cid,'alice','Uploaded.md',b'OWNED_UPLOAD_ONLY')
        docs,_,_=build_context(db,cid,{'username':'alice'},TurnRequest(request_id=uuid4(),prompt='Read this attached file.'))
        assert {d['source'] for d in docs}=={'Uploaded.md'}
        docs,_,_=build_context(db,cid,{'username':'alice'},TurnRequest(request_id=uuid4(),prompt='Read Scenario.md.'))
        assert {d['source'] for d in docs}=={'Scenario.md'}
    try:
        with patch.dict(os.environ,{'COGNISHIELD_DEV_WORKBENCH':'1','COGNISHIELD_DEV_SIMULATION':'0'}):asyncio.run(exercise())
    finally:db.close()


def test_material_word_does_not_discard_an_owned_document_followup():
    from llm.gateway_references import resolve_read
    previous={'context_coverage':{'routing':{'attachments':True},'files':{'selected_documents':[{'name':'Maintenance.md','origin':'simulated'}]}}}
    assert resolve_read('What protocol must stay unchanged in that document?',previous,{'devices':[]})=={'documents':True,'use_history':True}
    assert resolve_read('Explain that section in the open file.',previous,{'devices':[]}) is None
    assert resolve_read('In general, what does that protocol do?',previous,{'devices':[]}) is None
    assert resolve_read('Modify that document.',previous,{'devices':[]}) is None


def test_network_context_preserves_logical_source_filter_through_authorized_tools(tmp_path):
    from db.manager import DatabaseManager
    from llm.gateway import AIGateway
    from llm.gateway_store import ensure_schema
    from llm.gateway_network import network_context
    from llm.tools import ToolAuthorization
    from development.starter import starter_bundle
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    manager=ScenarioManager(tmp_path/'state.json');db._development_scenario=manager
    draft=manager.save_draft(starter_bundle(),owner='alice',expected=None)
    receipt=manager.validate_draft(draft['draft_id'],owner='alice',expected=1)
    manager.activate_draft(draft['draft_id'],owner='alice',expected=1,expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    gateway=AIGateway(db);cid=gateway.store.create('alice','floating')['id']
    auth=ToolAuthorization('alice','admin','floating',cid,frozenset({'network.state'}))
    async def exercise():
        context,_,_=await network_context(db,gateway.registry,auth,'Read LAB-R1 controller records.',
            domains_override=['state'],source_requests={'state':{'source_categories':['controller_state']}})
        rows=context[0]['data']['records']
        assert rows and {row['source_category'] for row in rows}=={'controller_state'}
    try:
        with patch.dict(os.environ,{'COGNISHIELD_DEV_WORKBENCH':'1','COGNISHIELD_DEV_SIMULATION':'0'}):asyncio.run(exercise())
    finally:db.close()
