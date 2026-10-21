"""Editable protocol observations reuse existing simulator contracts/readers."""
from copy import deepcopy
from pathlib import Path
import asyncio,sys
from unittest.mock import patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from development.starter import starter_bundle
from development.bundles import compile_bundle
from local_providers.development import ScenarioManager


def test_authored_protocol_parameters_use_existing_validation():
    bundle=starter_bundle();compile_bundle(bundle)
    for endpoint,field,value in [('left','router_id','invalid'),('right','device_id',99999),
            ('right','interface_id',1),('left','hello_seconds',-1)]:
        broken=deepcopy(bundle);broken['sources']['protocol_state']['data']['records'][0]['values'][endpoint][field]=value
        with pytest.raises(ValueError):compile_bundle(broken)
    for field,value in [('local_as',0),('remote_as',4294967296),('address','invalid')]:
        broken=deepcopy(bundle);broken['sources']['protocol_state']['data']['records'][1]['values']['left'][field]=value
        with pytest.raises(ValueError):compile_bundle(broken)
    broken=deepcopy(bundle);broken['sources']['protocol_state']['data']['records'][0]['device_id']=1300
    with pytest.raises(ValueError):compile_bundle(broken)


def test_protocol_schema_reuses_session_constraints_and_conflicts_remain_visible():
    from jsonschema import Draft202012Validator
    from development.bundles import source_schema
    from llm.orchestration.synthesis import protocol_observations,check_candidate
    from llm.gateway_models import Evidence
    bundle=starter_bundle();schema=source_schema('protocol_state')
    assert not list(Draft202012Validator(schema).iter_errors(bundle['sources']['protocol_state']))
    bundle['sources']['protocol_state']['data']['records'][1]['values']['left']['local_as']=0
    assert list(Draft202012Validator(schema).iter_errors(bundle['sources']['protocol_state']))
    peers=[{'device_id':1,'hostname':'Oak','router_id':'192.0.2.1'},{'device_id':2,'hostname':'Pine','router_id':'192.0.2.2'}]
    rows=[{'kind':kind,'protocol':'OSPF','peer_parameters':peers,'observed_state':state,'timestamp':'2026-10-19T01:00:00Z'}
        for kind,state in [('protocol_assessment','Full'),('protocol_observation','Init')]]
    context=[{'tool':'network.state','status':'success','scope_devices':[{'id':1,'hostname':'Oak'}],'data':{'records':rows}}]
    facts=protocol_observations(context,'Which OSPF neighbors were observed for Oak?',{})
    assert len(facts)==2 and all(fact['conflicting_states']==['Full','Init'] for fact in facts)
    evidence=[Evidence(id='e',source='Protocol observations',origin='simulated')]
    assert check_candidate('Oak has a healthy Full adjacency with Pine. [S1]',context,evidence,{},'Which OSPF neighbors were observed for Oak?')
    assert not check_candidate('The protocol observations conflict: one reports Full and the other Init for the same endpoints/time. [S1]',context,evidence,{},'Which OSPF neighbors were observed for Oak?')


def test_edited_observation_is_distinct_from_simulator_and_readable_from_either_endpoint(tmp_path):
    from db.manager import DatabaseManager
    from llm.gateway import AIGateway
    from llm.gateway_store import ensure_schema
    from llm.tools import ToolAuthorization
    from llm.orchestration.synthesis import protocol_observations
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False);db._development_scenario=manager
    bundle=starter_bundle();bundle['sources']['protocol_state']['data']['records'][0]['values'].update(observed_state='Init')
    try:
        draft=manager.save_draft(bundle,owner='alice',expected=None);receipt=manager.validate_draft(draft['draft_id'],owner='alice',expected=1)
        manager.activate_draft(draft['draft_id'],owner='alice',expected=1,expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
        gateway=AIGateway(db);cid=gateway.store.create('alice','floating')['id']
        auth=ToolAuthorization('alice','admin','floating',cid,frozenset({'network.state'}))
        with patch.dict('os.environ',{'COGNISHIELD_DEV_WORKBENCH':'1'}):
            result=asyncio.run(gateway.registry.invoke('network.state',{'device_refs':['LAB-R2'],'source_categories':['protocol_state']},auth))
        ospf=next(row for row in result.data['records'] if row['protocol']=='OSPF')
        assert ospf['observed_state']=='Init' and ospf['peer_parameters'][0]['hostname']=='LAB-R1'
        assert ospf['peer_parameters'][1]['hostname']=='LAB-R2'
        assert manager.snapshot()[0]['network']['ospf'][0]['observed_state']=='Full'
        context=[{'tool':'network.state','status':'success','scope_devices':[{'id':1200,'hostname':'LAB-R2'}],
            'evidence_ids':[result.evidence[0].id],'data':result.data}]
        facts=protocol_observations(context,'Which OSPF neighbors were observed for LAB-R2?',{result.evidence[0].id:'S1'})
        assert len(facts)==1 and facts[0]['neighbor']['device']=='LAB-R1' and facts[0]['local']['device']=='LAB-R2'
        assert facts[0]['observed_state']=='Init' and result.evidence[0].origin=='simulated'
    finally:db.close()
