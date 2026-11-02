"""Strict core/provider wire and independent direction axes. No live API."""
import asyncio,copy,json,sys
from pathlib import Path
from unittest.mock import patch
import httpx,jsonschema,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.model_roles import provider_wire_schema,provider_wire_mode,validate_result,consent_manifest
from llm.orchestration.role_reasoning import EvidenceDecision,SourceClaim,parse_decision
from llm.gemini_provider import interpret_rest

def schema():
    value=EvidenceDecision.model_json_schema();value['x-auxiliary-fields']=['claims'];return value
@pytest.mark.parametrize('wire_mode',['full','core_v1'])
@pytest.mark.parametrize('kind',['quoted','cli','embedded_json','bad_json','bad_decision','bad_source_type','bad_query','invalid_auxiliary'])
def test_wire_projection_never_weakens_original_core(monkeypatch,wire_mode,kind):
    monkeypatch.setenv('COGNISHIELD_AI_PROVIDER_WIRE_SCHEMA',wire_mode)
    original=schema();before=copy.deepcopy(original);wire=provider_wire_schema(original)
    assert original==before and 'x-auxiliary-fields' not in wire
    jsonschema.Draft202012Validator.check_schema(wire)
    data={'decision':'answer','answer':'Recorded "down".','sources':['actual-source'],'additional_reads':[],'claims':[]}
    if kind=='cli':data['answer']='interface Ethernet1\n description "quoted & literal \\\\ path"\n!'
    if kind=='embedded_json':data['answer']='Example literal: '+json.dumps({'state':'down','nested':{'value':3}})
    if kind=='bad_decision':data['decision']='execute'
    if kind=='bad_source_type':data['sources']=[123]
    if kind=='bad_query':data['additional_reads']=[{'reader':'unregistered','parameters':{},'gap':4}]
    if kind=='invalid_auxiliary':data['claims']={'direction':'ingress'}
    raw=json.dumps(data) if kind!='bad_json' else '{"decision":"answer","answer":"status: "down"","sources":[]}'
    if kind in {'bad_json','bad_decision','bad_source_type','bad_query'}:
        with pytest.raises(Exception):validate_result(raw,original)
    else:
        validate_result(raw,original)
        core,aux=parse_decision(raw,True)
        assert core.answer==data['answer']
        if kind=='invalid_auxiliary':assert aux['status']=='MODEL_CONTRACT_ERROR'

def test_core_wire_removes_only_unreachable_auxiliary_definitions(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_PROVIDER_WIRE_SCHEMA','core_v1')
    original=schema();wire=provider_wire_schema(original)
    assert 'SourceClaim' not in wire.get('$defs',{})
    assert 'SupplementaryRead' in wire['$defs'] and 'OutcomeAssessment' in wire['$defs']
    for field in ['decision','answer','sources','additional_reads','outcome_assessments']:
        assert wire['properties'][field]==original['properties'][field]
    assert wire['properties']['claims']=={}
    assert wire['additionalProperties'] is False
    assert wire['required']==[k for k in original['required'] if k!='claims']

def test_auxiliary_claim_definition_cannot_relax_core_decision(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_PROVIDER_WIRE_SCHEMA','core_v1')
    original=schema();original['x-auxiliary-fields']=['decision']
    wire=provider_wire_schema(original)
    assert wire['properties']['decision']==original['properties']['decision']
    with pytest.raises(Exception):validate_result('{"decision":"execute","answer":"bad"}',original)

def test_independent_axes_are_explicit_without_coercion():
    a=SourceClaim(statement='The forward branch stops at an ingress port.',category='simulated_forwarding',
       record_refs=['actual-flow'],direction='forward',field='direction',value='ingress',scope='modeled')
    assert a.direction=='forward' and a.value=='ingress'
    with pytest.raises(ValueError):SourceClaim(statement='Port is down',category='interface_oper_status',direction='ingress')
    assert 'ingress/egress' in SourceClaim.model_json_schema()['properties']['direction']['description']

def test_wire_and_layout_settings_are_consent_bound(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_PROVIDER_WIRE_SCHEMA','full');a=consent_manifest()
    monkeypatch.setenv('COGNISHIELD_AI_PROVIDER_WIRE_SCHEMA','core_v1')
    assert consent_manifest()!=a
    monkeypatch.setenv('COGNISHIELD_AI_PROVIDER_WIRE_SCHEMA','unsupported')
    with pytest.raises(Exception):provider_wire_mode()

@pytest.mark.parametrize('status,finish,category',[(400,'STOP','INVALID_ARGUMENT'),(503,'STOP','UNAVAILABLE'),(200,'MAX_TOKENS','INCOMPLETE_GENERATION')])
def test_provider_errors_remain_noncompletion_without_retry(monkeypatch,tmp_path,status,finish,category):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-test-key')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_USAGE',str(tmp_path/'quota.json'))
    calls=[]
    async def send(client,request,*args,**kwargs):
        calls.append(json.loads(request.content))
        data={'error':{'status':category}} if status!=200 else {'candidates':[{'finishReason':finish,'content':{'parts':[{'text':'{"decision":"answer"'}]}}]}
        return httpx.Response(status,request=request,json=data)
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(Exception) as exc:
        asyncio.run(interpret_rest([{'role':'user','content':'Synthetic'}],schema(),timeout=3,model='gemini-3.5-flash-lite',schema_mode='json_schema'))
    assert len(calls)==1 and getattr(exc.value,'provider_category')==category
    body=calls[0]['generationConfig']
    assert body['responseFormat']['text']['mimeType']=='APPLICATION_JSON'
    assert 'responseJsonSchema' not in body and 'responseMimeType' not in body

