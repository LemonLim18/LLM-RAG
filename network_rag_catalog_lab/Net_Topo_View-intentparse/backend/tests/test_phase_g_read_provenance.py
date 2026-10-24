"""Projection/retrieval integrity, independent of model prose and routing."""
import asyncio
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import Evidence,ToolResult
from llm.gateway_network import network_context
from llm.orchestration.verification import verify_documents


def test_evidence_assisted_evaluation_recovers_authorized_records_but_preserves_reader_bounds():
    from llm.orchestration.verification import assessment_context
    original=ToolResult(status='success',message='The reader returned only its bounded time window.',
        data={'records':[{'device':'Cedar','admin_state':'up'},
            {'device':'Cedar','admin_state':'down'}],'truncated':True},
        evidence=[Evidence(id='read-state',source='state-window',origin='stored')])
    display={'tool':'network.state','status':'success','data':{'records':original.data['records'][:1]},
        'evidence_ids':['read-state']}
    recovered=assessment_context([display],[('network.state',original)])
    assert recovered[0]['data']==original.data and recovered[0]['status']=='success'
    assert len(display['data']['records'])==1  # Do not rewrite display/provenance checks.
    assert assessment_context([{**display,'evidence_ids':['other-owner-read']}],
        [('network.state',original)])[0]['data']==display['data']


def document_result(identity,text,status='success'):
    return ToolResult(status=status,data=[{'source':'published:configure_ospf','evidence_id':identity,
        'text':text,'published_requirements':{'operations':[{'operation_id':'configure_ospf',
        'schema':{'required':['process_id'],'properties':{'process_id':{'type':'integer'}}},
        'description':'Published source description. '*600,'profiles':[]}]}}],
        evidence=[Evidence(id=identity,source='published:configure_ospf',origin='stored',source_revision='immutable-release')])


def test_large_typed_published_contract_survives_multisource_projection():
    original=document_result('first','Actual source text. '*500)
    registry=SimpleNamespace(invoke=AsyncMock(side_effect=[original.model_copy(deep=True),ToolResult(status='success',data={'records':[]})]))
    with patch('llm.gateway_services.inventory_snapshot',return_value={'devices':[]}):
        context,_,_=asyncio.run(network_context(None,registry,None,'Compare published OSPF with saved configuration',
            domains_override=['knowledge','configuration'],device_refs_override=[]))
    assert context[0]['data']==original.data
    assert verify_documents({'status':'verified'},context,[('knowledge.search',original),
        ('network.configuration',ToolResult(status='success',data={'records':[]}))])['status']=='verified'


def test_each_read_is_bound_to_its_actual_evidence_not_last_tool_name():
    first=document_result('first','Earlier authoritative source')
    second=document_result('second','Later authoritative source')
    context=[{'tool':'knowledge.search','status':r.status,'message':r.message,'data':deepcopy(r.data),
        'evidence_ids':[r.evidence[0].id]} for r in [first,second]]
    authoritative=[('knowledge.search',first),('knowledge.search',second)]
    assert verify_documents({'status':'verified'},context,authoritative)['status']=='verified'
    context[0]['data'][0]['text']='Invented model content'
    assert verify_documents({'status':'verified'},context,authoritative)['status']=='failed'


def test_unknown_evidence_and_status_mutation_cannot_borrow_another_read():
    original=document_result('first','Source')
    item={'tool':'knowledge.search','status':'success','message':'','data':deepcopy(original.data),'evidence_ids':['unknown']}
    assert verify_documents({'status':'verified'},[item],[('knowledge.search',original)])['status']=='failed'
    item['evidence_ids']=['first'];item['status']='unavailable'
    assert verify_documents({'status':'verified'},[item],[('knowledge.search',original)])['status']=='failed'


def test_adaptive_gap_selection_accepts_typed_document_lists_without_raw_content():
    import json
    from llm.orchestration.planning import additional_reads
    generate=AsyncMock(return_value=(json.dumps({'information_needs':[],
        'reason':'No additional offered source resolves the remaining gap.'}),'configured-model'))
    results=[{'tool':'knowledge.search','status':'success','data':document_result('first','PRIVATE-CONTRACT-TEXT').data},
        {'tool':'network.configuration','status':'unavailable','data':None}]
    queries,_=asyncio.run(additional_reads('Compare requirements with saved state',{'syslog'},
        {'gaps':['A source is unavailable'],'conflicts':[]},results,'configured-model',generate))
    assert queries=={}
    packet=json.loads(generate.call_args.args[0][-1]['content'])
    assert packet['reads'][0]['documents']==1 and packet['reads'][0]['records']==0
    assert packet['reads'][1]['records']==0
    assert 'PRIVATE-CONTRACT-TEXT' not in json.dumps(packet)


def test_mixed_document_and_network_evidence_can_render_record_disclosure():
    from llm.gateway_findings import network_answer
    original=document_result('first','Authoritative documentation text')
    context=[{'tool':'knowledge.search','status':'success','data':original.data,'evidence_ids':['first']},
        {'tool':'network.configuration','status':'success','data':{'records':[
            {'hostname':'Cedar','config_text':'hostname Cedar\n','current':False}]},'evidence_ids':[]}]
    answer=network_answer(context,original.evidence)
    assert 'hostname Cedar' in answer
    assert 'configure_ospf' in answer


def test_claim_verification_accepts_mixed_published_and_recorded_as_roles():
    from llm.orchestration.synthesis import check_candidate
    original=document_result('first','Published BGP contract')
    context=[{'tool':'knowledge.search','status':'success','data':original.data},
        {'tool':'network.state','status':'success','data':{'records':[
            {'hostname':'Cedar','local_as':65000,'remote_as':65001}]}}]
    assert not check_candidate('Cedar local AS is 65000 and remote AS is 65001.',context,[],{},'Explain local and remote AS roles.')
