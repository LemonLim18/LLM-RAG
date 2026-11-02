"""Bounded source-owned supplementary views preserve authoritative graph rows."""
import copy,json,sys,unittest
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from llm.gateway_models import Evidence
from llm.orchestration.role_reasoning import evidence_packet
from llm.orchestration.investigation_support import evidence_envelope

def expand_metadata(packet):
    def resolve(value):
        if isinstance(value,dict) and set(value)=={'metadata_ref'}:
            target=packet
            for token in value['metadata_ref'][2:].split('/'):
                token=token.replace('~1','/').replace('~0','~')
                target=target[int(token)] if isinstance(target,list) else target[token]
            return resolve(target)
        if isinstance(value,dict):return {k:resolve(v) for k,v in value.items()}
        if isinstance(value,list):return [resolve(v) for v in value]
        return value
    return resolve(packet)

@pytest.fixture(autouse=True)
def profile(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_COMPLETENESS','1')
    monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_LAYOUT','current')

def operands(count=90):
    question='Explain Edge current running configuration and the exact purpose of its source-owned review reference. State what remains unproved about repair completion.'
    def event(i):return {'id':'heartbeat-'+str(i),'kind':'syslog_event','device_id':17,'interface_id':1702,'source':'observer-a','timestamp':'2026-11-01T08:00:00Z','message':'Periodic health notification without a change-review association. '*12}
    ref={'id':'review:opaque-17','kind':'syslog_event','device_id':17,'interface_id':1702,'source':'change-journal','timestamp':'2026-11-01T06:30:00Z','message':'Review requested for an incorrect circuit description; no repair completion is stated.'}
    params={'device_refs':['17'],'query':question,'limit':100,'source_scope':'historical','live':False,'window_minutes':60,'source_categories':['syslog'],'record_kinds':[],'interface_refs':[],'start':None,'end':None}
    def row(tool,records,identity,args):return {'tool':tool,'status':'success','message':'','evidence_ids':[identity],
       'data':{'records':records,'source_available':True,'truncated':False,'scenario':{'origin':'simulated','source_revision':'fixture-one'}},
       'reader_receipt':{'invocation_id':identity,'tool':tool,'parameters':args,'status':'success','truncated':False}}
    rows=[row('network.configuration',[{'id':'running-17','kind':'running_configuration','device_id':17,'config_text':'interface ge-0/0/5.0\n description CIRCUIT\n','change_event_ref':ref['id']}],'c',{}),
          row('network.syslog',[event(i) for i in range(8)],'s1',{**params,'limit':8}),
          row('network.syslog',[*[event(i) for i in range(count)],ref],'s2',params)]
    return {'request':question,'results':rows,'evidence':[Evidence(id=i,source='synthetic-'+i,origin='simulated') for i in ['c','s1','s2']],
        'history':[],'planning':{},'continuation':{'initiator':'server_post_draft','requested':[{'reader':'network.syslog','parameters':params,'gap':ref['id']}]},
        'retrieval':{'executed_queries':[r['reader_receipt'] for r in rows],'investigation_context':{'evidence_envelopes':evidence_envelope(rows),'network':{},'artifact_history':{},'previous_review':{},'previous_draft':'A prior draft did not have the referenced review.'}}}

def test_oversized_dependency_read_reaches_revised_model_input_without_changing_graph():
    args=operands();original=copy.deepcopy(args)
    text=evidence_packet(**args);packet=json.loads(text)
    assert len(text)<=64000
    records=packet['reader_results'][2]['data']['records']
    assert records[-1]==original['results'][2]['data']['records'][-1]
    assert 'ge-0/0/5.0' in text and 'ge-0/0.5' not in text
    assert packet['reader_results'][0]['data']==original['results'][0]['data']
    assert expand_metadata(packet)['reader_results'][1]['data']==original['results'][1]['data']
    assert packet['evidence_delivery']['version']=='dependency_view_v3'
    assert packet['evidence_delivery']['not_delivered_records']
    assert args==original

def test_material_source_overflow_still_fails_closed_without_truncation():
    args=operands();args['results'][0]['data']['records'][0]['config_text']='configuration-operand '*5000
    original=copy.deepcopy(args)
    with pytest.raises(HTTPException) as error:evidence_packet(**args)
    assert error.value.status_code==413 and args==original

def test_small_packet_keeps_all_records_and_uses_no_dependency_selection():
    args=operands(1);packet=json.loads(evidence_packet(**args))
    assert 'evidence_delivery' not in packet
    assert packet['reader_results'][2]['data']==args['results'][2]['data']

@pytest.mark.parametrize('mutation',['model_gap','wrong_owner','unreferenced','unavailable','failed','wrong_parameters','no_read','state_only'])
def test_unproven_or_prohibited_projection_does_not_make_large_evidence_fit(mutation):
    args=operands()
    if mutation=='model_gap':args['continuation']['initiator']='model'
    if mutation=='wrong_owner':args['results'][2]['data']['records'][-1]['device_id']=18
    if mutation=='unreferenced':args['results'][0]['data']['records'][0].pop('change_event_ref')
    if mutation=='unavailable':args['results'][2]['data']['source_available']=False
    if mutation=='failed':args['results'][2]['status']='error'
    if mutation=='wrong_parameters':args['continuation']['requested'][0]['parameters']={**args['continuation']['requested'][0]['parameters'],'limit':99}
    if mutation=='no_read':args['request']='Recommend checks only. Do not read or collect anything.'
    if mutation=='state_only':args['request']='Using state only, explain Edge. Do not read any other sources.'
    original=copy.deepcopy(args)
    with pytest.raises(HTTPException) as failure:evidence_packet(**args)
    assert failure.value.status_code==413 and original==args

def test_conflicting_versions_distinct_sources_and_dependency_chain_are_kept():
    args=operands();second=args['results'][2]['data']['records'];base=copy.deepcopy(second[-1])
    second.extend([{**base,'source':'second-journal','message':'Same reference with conflicting purpose.'},
        {'id':'followup-review','kind':'syslog_event','device_id':17,'depends_on':[base['id']],'timestamp':'2026-11-01T07:00:00Z','message':'Completion is unknown, not a completed repair.'}])
    packet=json.loads(evidence_packet(**args));records=packet['reader_results'][2]['data']['records']
    assert records[-3:]==second[-3:]
    assert 'conflicting purpose' in json.dumps(packet)

def test_multiple_typed_references_and_truncated_receipts_survive():
    args=operands();first=args['results'][0]['data']['records'][0]
    first['depends_on']=['second-reference']
    args['results'][2]['data']['records'].append({'id':'second-reference','kind':'syslog_event','device_id':17,'timestamp':'2026-10-20T01:00:00Z','message':'A historical recorded dependency.'})
    args['continuation']['requested'].append({**copy.deepcopy(args['continuation']['requested'][0]),'gap':'second-reference'})
    args['results'][2]['data']['truncated']=True;args['results'][2]['reader_receipt']['truncated']=True
    packet=json.loads(evidence_packet(**args))
    assert packet['reader_results'][2]['data']['truncated'] is True
    assert packet['reader_results'][2]['data']['records'][-1]['id']=='second-reference'
    assert packet['reader_results'][2]['data']['records'][-2]['id']=='review:opaque-17'

def test_original_saved_temporal_and_nested_directional_operands_are_unchanged():
    args=operands();args['results'][0]['data']['records'].extend([
        {'id':'staged','kind':'configuration_snapshot','device_id':17,'applied':False,'timestamp':'2026-10-31T04:00:00Z','config_text':'router bgp 65117\n'},
        {'id':'flow','kind':'forwarding_assessment','device_id':17,'forward':{'vrf':'blue','branches':[{'device_id':17,'interface':'ge-0/0/5.0','result':'delivered'}]},'return':{'vrf':'blue','destination':'198.18.117.1','result':'unknown'}}])
    original=copy.deepcopy(args)
    packet=json.loads(evidence_packet(**args));assert packet['reader_results'][0]['data']==original['results'][0]['data']

def test_consent_records_delivery_version_only_in_experimental_profile(monkeypatch):
    from llm.model_roles import consent_manifest
    assert consent_manifest()['evidence_delivery']=='dependency_view_v3'
    monkeypatch.setenv('COGNISHIELD_AI_COMPLETENESS','0')
    assert 'evidence_delivery' not in consent_manifest()

def test_metadata_references_are_exact_and_do_not_rewrite_record_payloads():
    from llm.orchestration.role_reasoning import reference_repeated_metadata
    args=operands(1)
    packet={'reader_results':copy.deepcopy(args['results']),'retrieval_boundary':copy.deepcopy(args['retrieval']),
        'evidence_delivery':{},'evidence_requirement_ledger':{}}
    original=copy.deepcopy(packet)
    reference_repeated_metadata(packet)
    restored=expand_metadata(packet)
    assert restored['reader_results']==original['reader_results']
    assert restored['retrieval_boundary']==original['retrieval_boundary']
    for row,before in zip(packet['reader_results'],original['reader_results']):assert row['data']['records']==before['data']['records']

class ReaderTransport(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from tests.test_b1_agent import B1Tests
        B1Tests.setUp(self)

    async def test_completeness_retains_actual_syslog_body_before_packet_selection(self):
        from llm.gateway_models import ToolResult
        from llm.gateway_network import network_context,READ_TOOLS
        from llm.orchestration.adapters import AuthorizedTools
        from llm.tools import ToolAuthorization
        from unittest.mock import patch
        rows=[{'id':'r-'+str(i),'kind':'syslog_event','device_id':2,'message':'Exact recorded operand. '*50} for i in range(90)]
        async def source(params,auth):return ToolResult(status='success',data={'records':copy.deepcopy(rows),'truncated':False,'source_available':True},evidence=[Evidence(id='read-exact',source='synthetic',origin='simulated',device_refs=['2'])])
        self.g.registry._tools['network.syslog']['fn']=source
        auth=ToolAuthorization('alice','engineer','floating',self.cid,READ_TOOLS)
        with patch.dict('os.environ',{'COGNISHIELD_AI_COMPLETENESS':'1'}):
            tools=AuthorizedTools(self.g.registry,self.g.store,auth)
            context,_,_=await network_context(self.db,tools,auth,'Read R2 syslog.',domains_override=['syslog'],validated_parameters={'syslog':{'device_refs':['2'],'limit':100}})
        assert context[0]['data']['records']==rows
        assert context[0]['data']['truncated'] is False
        assert tools.results[0][1].data['records']==rows
