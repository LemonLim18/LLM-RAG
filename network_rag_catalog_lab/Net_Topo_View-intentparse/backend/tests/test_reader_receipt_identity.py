"""Per-invocation coverage, independent of model inference."""
import asyncio,copy,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import ToolResult,Evidence
from llm.gateway_network import NetworkQuery,network_context
from llm.orchestration.adapters import AuthorizedTools
from llm.orchestration.investigation_support import source_coverage
from llm.tools import ToolRegistry,Capability,ToolAuthorization
from tests.test_state_interface_scope import scoped_environment

PLAN=[{'domain':'syslog','reader':'network.syslog','status':'CAPABILITY_READY_SOURCE_UNQUERIED'}]

def invocation(n,status='success',*,target='1',revision='revision-a',start=None,end=None,truncated=False):
    args={'device_refs':[target],'source_scope':'current','start':start,'end':end}
    receipt={'invocation_id':n,'tool':'network.syslog','parameters':args,'status':status,
             'invocation_status':'failed' if status=='error' else 'completed',
             'source_revisions':[revision],'truncated':truncated,'evidence_ids':['e-'+n],
             'record_refs':['record-'+n] if status=='success' else []}
    data={'records':[{'id':'record-'+n,'kind':'syslog_event','message':'Recorded'}],
          'scenario':{'source_revision':revision},'truncated':truncated}
    if status=='unavailable':data={'records':[],'source_available':False}
    elif status=='error':data=None
    return {'tool':'network.syslog','status':status,'data':data,'evidence_ids':receipt['evidence_ids'],
            'source_request':{'source_scope':'current'},'reader_receipt':receipt},receipt

def check(rows,receipts=()):
    return source_coverage(PLAN,rows,receipts)[0]

@pytest.mark.parametrize('order',[('success','error'),('error','success')])
def test_partial_success_survives_both_invocation_orders(order):
    values=[invocation(str(i),status) for i,status in enumerate(order)]
    result=check([v[0] for v in values],[v[1] for v in values])
    assert result['status']=='PARTIALLY_RETRIEVED'
    assert result['query_statuses']==['QUERIED_SUCCESSFULLY' if s=='success' else 'QUERY_FAILED' for s in order]
    assert len(result['queries'])==2 and all(q['receipt_binding']=='EXACT_INVOCATION' for q in result['queries'])

@pytest.mark.parametrize('changes',[{'target':'2'},{'start':'2026-10-31T01:00:00Z','end':'2026-10-31T02:00:00Z'},{'revision':'revision-b'}])
def test_separate_invocations_retain_targets_windows_and_revisions(changes):
    a,ra=invocation('a');b,rb=invocation('b',**changes)
    result=check([a,b],[ra,rb])
    assert result['status']=='QUERIED_SUCCESSFULLY' and len(result['queries'])==2
    assert [q['parameters'] for q in result['queries']]==[ra['parameters'],rb['parameters']]
    assert [q['source_revisions'] for q in result['queries']]==[ra['source_revisions'],rb['source_revisions']]
    assert result['queries'][0]['record_refs']==['record-a']

def test_identical_query_is_two_actual_invocations_not_two_independent_sources():
    a,ra=invocation('a');b,rb=invocation('b')
    result=check([a,b],[ra,rb])
    assert len(result['queries'])==2 and ra['parameters']==rb['parameters']
    assert [q['invocation_id'] for q in result['queries']]==['a','b']

def test_duplicate_exact_invocation_does_not_duplicate_coverage():
    a,ra=invocation('a');result=check([a,copy.deepcopy(a)],[ra,copy.deepcopy(ra)])
    assert len(result['queries'])==1 and result['query_statuses']==['QUERIED_SUCCESSFULLY']

@pytest.mark.parametrize('kind,expected',[('zero','QUERIED_ZERO_MATCHES'),('unavailable','SOURCE_UNAVAILABLE'),('partial','PARTIALLY_RETRIEVED')])
def test_zero_unavailable_and_truncation_remain_distinct(kind,expected):
    a,ra=invocation('a','unavailable' if kind=='unavailable' else 'success',truncated=kind=='partial')
    if kind=='zero':a['data']['records']=[];ra['record_refs']=[]
    result=check([a],[ra]);assert result['status']==expected
    assert result['queries'][0]['truncated']==(kind=='partial')

def test_historical_rows_never_borrow_latest_same_family_receipt():
    a,_=invocation('a');a.pop('reader_receipt')
    b,rb=invocation('b','error')
    result=check([a,b],[rb])
    assert result['query_statuses']==['QUERIED_SUCCESSFULLY','QUERY_FAILED']
    assert result['queries'][0]['invocation_id'] is None
    assert result['queries'][0]['receipt_binding']=='HISTORICAL_UNBOUND'
    assert result['status']=='PARTIALLY_RETRIEVED'

def test_initial_broad_success_plus_narrow_supplement_failure_preserves_facts():
    a,ra=invocation('broad');ra['parameters']['limit']=8
    b,rb=invocation('narrow','error');rb['parameters'].update(limit=100,query='source-owned-event-reference')
    r=check([a,b],[ra,rb])
    assert r['queries'][0]['record_refs']==['record-broad']
    assert r['queries'][1]['parameters']['query']=='source-owned-event-reference'
    assert r['status']=='PARTIALLY_RETRIEVED'

def test_wrong_reader_receipt_cannot_bind_result():
    a,ra=invocation('a');bad={**ra,'tool':'network.state'}
    result=check([a],[bad])
    assert result['queries'][0]['receipt_binding']=='RECEIPT_MISMATCH'
    assert result['queries'][0]['status']=='QUERIED_SUCCESSFULLY'

def test_private_receipt_is_not_a_client_or_wire_field():
    value=ToolResult(status='success',data={'records':[]})
    assert '_invocation_receipt' not in value.model_dump()
    with pytest.raises(ValueError):ToolResult.model_validate({'status':'success','_invocation_receipt':{'invocation_id':'forged'}})

def test_actual_authorized_adapter_binds_each_result_and_preserves_copy():
    async def run():
        calls=0
        async def reader(query,authorization):
            nonlocal calls
            calls+=1
            if calls==2:raise HTTPException(503,'Synthetic source failure')
            return ToolResult(status='success',data={'records':[{'id':'actual-event','kind':'syslog_event','message':'Recorded'}],
                'scenario':{'source_revision':'source-rev-4'}},evidence=[
                Evidence(id='receipt-source',source='development.syslog',origin='simulated',source_revision='source-rev-4')])
        registry=ToolRegistry()
        registry.register_capability('network.syslog',reader,Capability(NetworkQuery,ToolResult,'read',frozenset({'floating'}),frozenset({'engineer'})))
        auth=ToolAuthorization('owned-principal','engineer','floating','owned-conversation',frozenset({'network.syslog'}))
        owner_checks=[]
        store=SimpleNamespace(get=lambda *args:owner_checks.append(args))
        tools=AuthorizedTools(registry,store,auth,max_calls=2,names=frozenset({'network.syslog'}))
        a=await tools.invoke('network.syslog',{'device_refs':['1']},auth)
        b=await tools.invoke('network.syslog',{'device_refs':['2']},auth)
        assert len(owner_checks)==2 and tools.calls==2
        assert a._invocation_receipt['invocation_id']!=b._invocation_receipt['invocation_id']
        assert a._invocation_receipt['record_refs']==['actual-event']
        assert a._invocation_receipt['source_revisions']==['source-rev-4']
        assert b._invocation_receipt['invocation_status']=='failed'
        assert b._invocation_receipt['parameters']['device_refs']==['2']
        assert tools.results[0][1]._invocation_receipt==a._invocation_receipt
        a.data['records'].clear()
        assert tools.results[0][1].data['records']
        assert '_invocation_receipt' not in a.model_dump()
        with pytest.raises(HTTPException):await tools.invoke('network.syslog',{},auth)
    asyncio.run(run())

@pytest.mark.parametrize('surface',['floating','studio'])
def test_real_context_row_carries_exact_scoped_invocation(scoped_environment,surface):
    from llm.gateway_services import registry_for
    db,_=scoped_environment
    async def run():
        auth=ToolAuthorization('scope-reader-owner','engineer',surface,'owned-test',frozenset({'network.state'}))
        tools=AuthorizedTools(registry_for(db),SimpleNamespace(get=lambda *args:None),auth,names=frozenset({'network.state'}))
        rows,_,_=await network_context(db,tools,auth,'Use recorded state only for Meadow Ethernet9/3.',
            domains_override=['state'],device_refs_override=['703'],interface_refs_override=['7031'],
            validated_parameters={'state':{'record_kinds':['interface_state']}})
        assert len(rows)==1 and rows[0]['reader_receipt']==tools.requests[0]
        receipt=rows[0]['reader_receipt']
        assert receipt['parameters']['interface_refs']==['7031']
        assert set(receipt['record_refs'])=={'port-7031','model-interface-7031'}
        assert receipt['source_revisions'] and receipt['evidence_ids']
        assert {r['interface_id'] for r in rows[0]['data']['records']}=={7031}
    asyncio.run(run())

