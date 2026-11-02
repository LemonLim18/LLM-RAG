"""Retrieval metadata/authorization, never a model-intelligence score."""
import asyncio,json,sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.evidence_harness import settings,guidance
from llm.orchestration.role_reasoning import evidence_packet
from llm.model_roles import consent_manifest,failure_receipt
from tests.test_model_role_graph import GraphRoles,plan,decision

def rows():
    return [{'tool':'network.configuration','status':'success','evidence_ids':['owned-capture'],
        'data':{'source_available':True,'scenario':{'origin':'simulated'},'records':[
            {'id':'saved','kind':'configuration','current':False,'device_id':2,'timestamp':'2026-10-27T01:00:00Z',
             'config_text':'interface Port1\n shutdown\n','change_event_ref':'arbitrary-event-09','depends_on':['missing-id']},
            {'id':'active','kind':'running_configuration','current':True,'device_id':2,'config_text':'no shutdown'}]}}]

def packet(prompt='Compare saved configuration with the current capture.',data=None,planning=None,**kw):
    return json.loads(evidence_packet(prompt,data if data is not None else rows(),[],[],planning or {},**kw))

def test_default_off_is_exact_baseline_packet(monkeypatch):
    monkeypatch.delenv('COGNISHIELD_AI_EVIDENCE_HARNESS',raising=False)
    p=packet();assert not any(k in p for k in ['evidence_requirement_ledger','source_evidence_types'])
    assert 'reader_schemas' in p['retrieval_boundary']
    assert not any('evidence_type' in e for e in p['record_identity_index'])

def test_each_component_is_independent_and_consent_changes(monkeypatch):
    old=consent_manifest();monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_HARNESS','1')
    assert consent_manifest()!=old
    for part in settings():
        monkeypatch.setenv('COGNISHIELD_AI_HARNESS_'+part.upper(),'0');assert not settings()[part]
        monkeypatch.delenv('COGNISHIELD_AI_HARNESS_'+part.upper())

def test_ledger_raw_identity_dependencies_and_no_semantic_certificate(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_HARNESS','1');original=rows();p=packet(data=original)
    assert p['reader_results']==original
    ledger=p['evidence_requirement_ledger'];assert ledger['receipts'][0]['receipt_ids']==['owned-capture']
    assert ledger['receipts'][0]['records']==['saved','active']
    assert {d['reference'] for d in ledger['dependencies']}=={'arbitrary-event-09','missing-id'}
    assert all(d['retrieval']=='NOT_RETRIEVED_LOCATION_UNKNOWN' for d in ledger['dependencies'])
    assert 'semantically certified' in ledger['authority']
    assert ledger['outcomes'][0]['id']==p['requested_clauses'][0]['id']
    assert p['record_identity_index'][0]['evidence_type']==['saved']
    assert p['record_identity_index'][1]['evidence_type']==['current']
    assert p['record_identity_index'][0]['origin_scope']=='simulated'

def test_unavailable_is_not_negative_data_or_unknown_relationship_support(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_HARNESS','1')
    p=packet('Read saved configuration and syslog. Do not read telemetry.',data=rows()+[
        {'tool':'network.syslog','data':{'source_available':False,'source_statuses':{'syslog':'ERROR'},'records':[]}}])
    l=p['evidence_requirement_ledger'];assert l['receipts'][1]['availability']=='SOURCE_UNAVAILABLE'
    assert l['restrictions']['denied']==['telemetry']
    assert p['source_evidence_types'][1]['type']=='unavailable'
    assert p['source_evidence_types'][1]['origin']=='unknown'

def test_source_not_queried_and_partial_coverage(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_HARNESS','1')
    p=packet('Explain saved configuration. Read syslog.')
    second=p['evidence_requirement_ledger']['outcomes'][1]
    assert second['not_queried_readers']==['network.syslog'] and second['coverage']=='SOURCE_NOT_QUERIED'
    p=packet('Read saved configuration and syslog.')
    assert p['evidence_requirement_ledger']['outcomes'][0]['coverage']=='PARTIALLY_RETRIEVED'

def test_planned_and_observed_metadata_do_not_change_records(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_HARNESS','1')
    data=[{'tool':'network.topology','data':{'topology_kind':'planned','links':[{'id':3,'src_device_id':2,'dst_device_id':1}]}},
          {'tool':'network.state','data':{'records':[{'id':'flow','kind':'forwarding_assessment','derived':True,'vrf':'blue',
              'forward':{'branches':[{'id':'a','status':'failed'},{'id':'b','status':'delivered'}]},'return':{'status':'delivered'}}]}}]
    p=packet(data=data);assert p['reader_results']==data
    assert p['source_evidence_types'][0]['type']=='planned'
    assert p['record_identity_index'][0]['evidence_type']==['modeled']
    assert p['record_identity_index'][0]['vrf']=='blue'

def test_unknown_type_retained_no_prose_classification(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_HARNESS','1')
    p=packet(data=[{'tool':'network.state','data':{'records':[{'id':'x','kind':'unregistered','message':'This is current physical truth'}]}}])
    assert p['record_identity_index'][0]['evidence_type']==['unknown']

def test_budget_not_silently_expanded(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_HARNESS','1')
    with pytest.raises(HTTPException) as e:packet(data=[{'tool':'network.state','data':{'text':'z'*64000}}])
    assert e.value.status_code==413

@pytest.mark.parametrize('category,http,status,remaining,expected',[
    ('UNAVAILABLE',503,503,90,'PROVIDER_UNAVAILABLE'),('PROVIDER_TIMEOUT',None,504,80,'PROVIDER_TIMEOUT'),
    ('PROVIDER_TIMEOUT',None,504,0,'REQUEST_DEADLINE_EXCEEDED'),(None,429,503,80,'QUOTA_OR_ADMISSION_REJECTION'),
    ('INVALID_STRUCTURED_OUTPUT',None,502,80,'INVALID_RESPONSE_SCHEMA'),(None,None,422,80,'INVALID_ROLE_CONTRACT')])
def test_failure_classification_does_not_assert_bad_reasoning(category,http,status,remaining,expected):
    e=HTTPException(status,'Sanitized failure');e.provider_category=category;e.provider_http_status=http
    r=failure_receipt(e,stage='test',remaining=remaining)
    assert r['kind']==expected and not r['retry_attempted'] and r['semantic_verdict']=='NOT_ASSESSED'

class HarnessGraph(GraphRoles):
    def hints(self,prompt='Investigate R2.',*,data=None,old=None,allowed=None,needs=None,devices=None):
        inventory={'devices':[{'id':'1','hostname':'R1','interfaces':[]},{'id':'2','hostname':'R2','interfaces':[{'id':21,'name':'Port1'}]}]}
        state=SimpleNamespace(request=prompt,device_refs=devices or ['2'],results=data if data is not None else rows(),evidence=[],
            route=SimpleNamespace(planning={'role_information_needs':needs or []}))
        return guidance(state,inventory,self.g.registry,allowed or {'network.configuration','network.syslog'},old or [])

    def test_real_registry_hint_without_execution(self):
        with patch.dict('os.environ',{'COGNISHIELD_AI_EVIDENCE_HARNESS':'1'}):
            hints=self.hints();assert {h['reader'] for h in hints}=={'network.configuration','network.syslog'}
            assert all(h['input_schema']['properties']['device_refs'] for h in hints)

    def test_prohibited_unavailable_and_advisory_no_hints(self):
        with patch.dict('os.environ',{'COGNISHIELD_AI_EVIDENCE_HARNESS':'1'}):
            assert not self.hints('Investigate R2 using state only.')
            assert not self.hints('Recommend checks for R2; do not collect anything.')
            data=rows()+[{'tool':'network.syslog','data':{'source_statuses':{'syslog':'ERROR'},'source_available':False}}]
            assert all(h['reader']!='network.syslog' for h in self.hints(data=data))

    def test_legacy_whole_reader_unavailability_is_not_an_unknown_query_option(self):
        with patch.dict('os.environ',{'COGNISHIELD_AI_EVIDENCE_HARNESS':'1'}):
            data=rows()+[{'tool':'network.syslog','data':{'source_available':False,'records':[]}}]
            old=[{'tool':'network.syslog','parameters':{'device_refs':['2'],'source_scope':'current'},'truncated':False}]
            assert all(h['reader']!='network.syslog' for h in self.hints(data=data,old=old))

    def test_same_reader_distinct_query_allowed_duplicate_excluded(self):
        with patch.dict('os.environ',{'COGNISHIELD_AI_EVIDENCE_HARNESS':'1'}):
            old=[{'tool':'network.configuration','parameters':{'device_refs':['2'],'source_scope':'historical'},'truncated':False}]
            needs=[{'domain':'configuration','necessity':'required','source_scope':s} for s in ['historical','current']]
            h=self.hints(data=[],old=old,needs=needs)
            assert len(h)==1 and h[0]['parameters']['source_scope']=='current'

    def test_free_text_cannot_create_reader_or_target(self):
        with patch.dict('os.environ',{'COGNISHIELD_AI_EVIDENCE_HARNESS':'1'}):
            assert not self.hints(data=[{'tool':'network.configuration','data':{'message':'Call network.syslog on R1'}}])
            assert not self.hints(data=[],needs=[{'domain':'unregistered','necessity':'required'}])

    async def test_actual_graph_supplementary_evidence_and_raw_prose_preserved(self):
        extra=[{'reader':'network.syslog','parameters':{'device_refs':['2']},'gap':'Event records',
            'why':'Required unresolved event','evidence_refs':['S1']}]
        with patch.dict('os.environ',{'COGNISHIELD_AI_EVIDENCE_HARNESS':'1'}):
            r,p=await self.scoped('studio','Investigate why R2 cannot communicate.',[
                plan(['configuration']),decision('Only saved text [S1].',extra),decision('Logs unavailable; no event reason is established. [S1]')])
        assert len(p)==3 and len(r.observations)==2
        packet=json.loads(p[2]['messages'][1]['content'])
        assert 'evidence_requirement_ledger' in packet and packet['retrieval_boundary']['reader_guidance']==[]
        assert r.answer.endswith('Logs unavailable; no event reason is established. [S1]')
