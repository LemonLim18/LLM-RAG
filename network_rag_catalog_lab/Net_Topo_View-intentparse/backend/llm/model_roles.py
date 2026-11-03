"""Role-based inference socket for the existing authorized intelligence gateway.

Adapters normalize transport, not tool authority. External dispatch also needs
the server-owned exact-request scope; configuration alone never grants consent.
"""
import asyncio,json,os,time
from dataclasses import dataclass,field
from typing import Literal
import httpx,jsonschema
from fastapi import HTTPException

Role=Literal['local_default','complex_planner','evidence_reasoner']
_openai_loop=None
_openai_limit=None

@dataclass(frozen=True)
class ModelRole:
    role:Role
    provider:str
    model:str
    output_tokens:int
    thinking:str|None=None
    structured:bool=True
    schema_mode:str='json_schema'

@dataclass(frozen=True)
class InferenceRequest:
    messages:list[dict]
    schema:dict|bool=False
    deadline:float=0

@dataclass
class InferenceResult:
    text:str
    model:str
    provider:str
    completion:str='completed'
    usage:dict=field(default_factory=dict)
    elapsed_ms:float=0

def experiment_enabled():return os.getenv('COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT','0')=='1'

def reasoner_interpretation_mode():
    selected=os.getenv('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT','off')
    if selected not in {'off','candidate'}:
        raise HTTPException(422,'Invalid reasoner interpretation experiment mode')
    return selected

def sourceclaim_timestamp_mode():
    selected=os.getenv('COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT','off')
    if selected not in {'off','candidate'}:
        raise HTTPException(422,'Invalid source-claim timestamp experiment mode')
    return selected

def answer_integrity_mode():
    """Isolated instruction experiment, never a role or authorization grant."""
    selected=os.getenv('COGNISHIELD_AI_REASONER_ANSWER_INTEGRITY','off')
    if selected not in {'off','candidate'}:
        raise HTTPException(422,'Invalid reasoner answer-integrity experiment mode')
    if selected=='candidate':
        config=role_config('evidence_reasoner')
        if (config.provider,config.model)!=('google','gemini-3.5-flash-lite'):
            raise HTTPException(422,'Answer-integrity candidate requires the Gemini 3.5 Flash-Lite reasoner')
        from llm.orchestration.reasoning_contract import mode as reasoning_mode
        if (reasoning_mode()!='off' or reasoner_interpretation_mode()!='off' or sourceclaim_timestamp_mode()!='off'
                or os.getenv('COGNISHIELD_AI_OUTCOMES','0')=='1'):
            raise HTTPException(422,'Answer-integrity candidate cannot be combined with earlier reasoning experiments')
    return selected

def investigation_profile():
    """Server-owned optional execution envelope, also bound into exact consent."""
    if os.getenv('COGNISHIELD_AI_COMPLETENESS','0')!='1':return {'enabled':False}
    def value(name,default,low,high):
        try:selected=float(os.getenv('COGNISHIELD_AI_INVESTIGATION_'+name,str(default)))
        except ValueError as exc:raise HTTPException(422,'Invalid investigation budget: '+name) from exc
        if not low<=selected<=high:raise HTTPException(422,'Investigation budget outside supported bounds: '+name)
        return selected
    return {'enabled':True,'version':3,'seconds':value('SECONDS',360,120,480),
        'planner_seconds':value('PLANNER_SECONDS',90,30,150),'reasoner_seconds':value('REASONER_SECONDS',120,30,180),
        'initial_read_seconds':value('INITIAL_READ_SECONDS',90,10,180),'supplement_read_seconds':value('SUPPLEMENT_READ_SECONDS',60,10,120),
        'adequacy_seconds':value('ADEQUACY_SECONDS',5,1,15),'max_readers':int(value('MAX_READERS',24,8,32)),
        'max_rounds':int(value('MAX_ROUNDS',3,1,4)),'max_role_calls':int(value('MAX_ROLE_CALLS',5,2,6))}

def role_config(role:Role):
    names={'local_default':('ollama',os.getenv('COGNISHIELD_LOCAL_OLLAMA_MODEL','qwen2.5:1.5b'),'LOCAL_DEFAULT',512,None),
        'complex_planner':('google','gemini-3.1-flash-lite','COMPLEX_PLANNER',2048,'low'),
        'evidence_reasoner':('google','gemini-3.5-flash-lite','REASONER',8192,'low')}
    if role not in names:raise HTTPException(422,'Unknown logical model role')
    provider,model,prefix,output,thinking=names[role]
    provider=os.getenv('COGNISHIELD_AI_'+prefix+'_PROVIDER',provider).lower()
    model=os.getenv('COGNISHIELD_AI_'+prefix+'_MODEL',model)
    thinking=os.getenv('COGNISHIELD_AI_'+prefix+'_THINKING',thinking or '') or None
    output=min(16384,max(128,int(os.getenv('COGNISHIELD_AI_'+prefix+'_OUTPUT_TOKENS',str(output)))))
    if provider not in {'ollama','google','openai'}:raise HTTPException(422,'Unsupported configured provider')
    if role=='local_default' and provider!='ollama':raise HTTPException(422,'Ordinary local tasks require the Ollama provider')
    if not model or model=='auto':raise HTTPException(422,'Model roles require an explicit model identity')
    # This retired transport is never a runtime rollback option.
    if model=='gemini-3.8-flash':raise HTTPException(422,'Gemini 3.8 runtime support is retired')
    if provider=='ollama' and thinking not in {None,'off'}:
        raise HTTPException(422,'This Ollama role adapter has no registered thinking control; set role THINKING=off')
    if provider=='google' and model not in {'gemini-3.1-flash-lite','gemini-3.5-flash-lite'}:
        raise HTTPException(422,'Google model capabilities have not been established for this model')
    if provider=='openai':
        # Published Structured Outputs support, not universal interchangeability.
        supported={'gpt-4.1','gpt-4.1-mini','gpt-4.1-nano','gpt-4o-2024-08-06','gpt-4o-mini'}
        if model not in supported:raise HTTPException(422,'OpenAI model structured-output capabilities are not registered')
        if thinking not in {None,'off'}:raise HTTPException(422,'This OpenAI model profile does not accept a thinking setting; set role THINKING=off')
        thinking=None
    schema_mode=os.getenv('COGNISHIELD_AI_'+prefix+'_SCHEMA_MODE','validated_json' if provider=='google' else 'json_schema')
    if schema_mode not in {'validated_json','json_schema'} or provider!='google' and schema_mode!='json_schema':
        raise HTTPException(422,'Unsupported provider schema mode')
    return ModelRole(role,provider,model,output,thinking,schema_mode=schema_mode)

def role_manifest():
    from dataclasses import asdict
    return {role:asdict(role_config(role)) for role in ['local_default','complex_planner','evidence_reasoner']}

def evidence_layout():
    """Experimental serialization only; source/policy authority is unchanged."""
    selected=os.getenv('COGNISHIELD_AI_EVIDENCE_LAYOUT','current')
    if selected not in {'current','canonical_v1'}:
        raise HTTPException(422,'Unknown experimental evidence layout')
    return selected


def provider_wire_mode():
    selected=os.getenv('COGNISHIELD_AI_PROVIDER_WIRE_SCHEMA','full')
    if selected not in {'full','core_v1'}:
        raise HTTPException(422,'Unknown experimental provider wire schema')
    return selected


def consent_manifest():
    """Bind the execution envelope as well as model identities to owner consent."""
    from llm.orchestration.evidence_harness import settings
    from llm.orchestration.reasoning_contract import mode as reasoning_mode,VERSION
    profile=investigation_profile()
    interpretation={}
    if reasoner_interpretation_mode()=='candidate':
        from llm.orchestration.role_reasoning import TEMPORAL_INTERPRETATION_CANDIDATE
        import hashlib
        interpretation={'reasoner_interpretation_experiment':{'version':'temporal_evidence_v1','mode':'candidate',
            'instruction_delta':TEMPORAL_INTERPRETATION_CANDIDATE,
            'instruction_sha256':hashlib.sha256(TEMPORAL_INTERPRETATION_CANDIDATE.encode()).hexdigest()}}
    if sourceclaim_timestamp_mode()=='candidate':
        from llm.orchestration.role_reasoning import SOURCECLAIM_TIMESTAMP_DESCRIPTION
        import hashlib
        interpretation['sourceclaim_timestamp_experiment']={'version':'source_record_time_v1','mode':'candidate',
            'schema_pointer':'/$defs/SourceClaim/properties/timestamp/description',
            'description':SOURCECLAIM_TIMESTAMP_DESCRIPTION,
            'description_sha256':hashlib.sha256(SOURCECLAIM_TIMESTAMP_DESCRIPTION.encode()).hexdigest()}
    if answer_integrity_mode()=='candidate':
        from llm.orchestration.role_reasoning import ANSWER_INTEGRITY_CANDIDATE
        import hashlib
        interpretation['reasoner_answer_integrity']={'version':'source_grounded_answer_integrity_v1','mode':'candidate',
            'instruction_delta':ANSWER_INTEGRITY_CANDIDATE,
            'instruction_sha256':hashlib.sha256(ANSWER_INTEGRITY_CANDIDATE.encode()).hexdigest()}
    return {'roles':role_manifest(),'semantic_mode':semantic_mode(),'reasoning_contract':'source_claims_v3' if profile['enabled'] else 'outcome_assessment_v1',
        **interpretation,
        **({'reasoning_enhancement':{'version':VERSION,'mode':reasoning_mode()}} if reasoning_mode()!='off' else {}),
        'investigation_profile':profile,'evidence_layout':evidence_layout(),
        **({'evidence_delivery':'dependency_view_v3'} if profile['enabled'] else {}),
        'provider_wire_schema':provider_wire_mode(),'google_native_schema_transport':'responseFormat_v1',
        'evidence_harness':{'version':1,**settings()},
        'supplementary_round':os.getenv('COGNISHIELD_AI_EVIDENCE_REFINE','1')=='1',
        'max_role_calls':profile['max_role_calls'] if profile['enabled'] else min(3,max(1,int(os.getenv('COGNISHIELD_AI_MULTI_MODEL_CALLS','3'))))}

def semantic_mode():
    selected=os.getenv('COGNISHIELD_AI_EXPERIMENT_SEMANTIC_VERIFIER','off')
    if selected not in {'off','report_only','enforced'}:raise HTTPException(422,'Invalid experimental verifier mode')
    return selected

def failure_receipt(exc,*,stage,remaining):
    """Execution classification only. Completed prose needs external grading."""
    category=getattr(exc,'provider_category',None);http=getattr(exc,'provider_http_status',None)
    if remaining<=0:kind='REQUEST_DEADLINE_EXCEEDED'
    elif category=='ROLE_CALL_LIMIT':kind='REQUEST_CALL_LIMIT'
    elif category=='REQUEST_BUDGET_RESERVATION_EXHAUSTED':kind=category
    elif http==429 or getattr(exc,'status_code',None)==429:kind='QUOTA_OR_ADMISSION_REJECTION'
    elif http in {500,502,503,504}:kind='PROVIDER_UNAVAILABLE'
    elif category=='PROVIDER_TIMEOUT':kind='PROVIDER_TIMEOUT' if getattr(exc,'provider_dispatched',True) else 'ADMISSION_TIMEOUT'
    elif category=='INVALID_STRUCTURED_OUTPUT':kind='INVALID_RESPONSE_SCHEMA'
    elif category:kind=category
    elif isinstance(exc,ValueError) or getattr(exc,'status_code',None)==422:kind='INVALID_ROLE_CONTRACT'
    elif getattr(exc,'status_code',None)==504:kind='INFERENCE_DEADLINE_EXCEEDED'
    else:kind='EXECUTION_ERROR'
    return {'kind':kind,'stage':stage,'provider_http_status':http,'provider_category':category,
        'remaining_seconds':round(max(0,remaining),3),'dispatched':getattr(exc,'provider_dispatched',None),
        'retry_attempted':False,'semantic_verdict':'NOT_ASSESSED'}

def response_validation_schema(schema):
    """Only server-declared auxiliary claims have independent validation.

    Decision, answer, source references, outcome and executable-query schemas
    remain mandatory. This does not recover invalid JSON or coerce identifiers.
    """
    if not isinstance(schema,dict) or schema.get('x-auxiliary-fields')!=['claims']:return schema
    schema=json.loads(json.dumps(schema))
    schema['properties']['claims']={}
    schema['required']=[key for key in schema.get('required',[]) if key!='claims']
    return schema


def provider_wire_schema(schema):
    """Provider serialization only; original core validation is unchanged.

    The existing server-declared auxiliary split is the only relaxation.
    Core constraints and all reachable local definitions remain intact.
    """
    if not isinstance(schema,dict):return schema
    wire=json.loads(json.dumps(response_validation_schema(schema) if provider_wire_mode()=='core_v1' else schema))
    wire.pop('x-auxiliary-fields',None)  # Server control, not provider schema.
    if provider_wire_mode()!='core_v1':return wire
    definitions=wire.pop('$defs',{})
    def refs(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key in {'$ref','$dynamicRef'} and isinstance(item,str) and item.startswith('#/$defs/'):
                    yield item.split('/')[2].replace('~1','/').replace('~0','~')
                else:yield from refs(item)
        elif isinstance(value,list):
            for item in value:yield from refs(item)
    required=set(refs(wire));pending=list(required)
    while pending:
        for name in refs(definitions.get(pending.pop(),{})):
            if name not in required:required.add(name);pending.append(name)
    retained={key:value for key,value in definitions.items() if key in required}
    if retained:wire['$defs']=retained
    return wire


def validate_result(text,schema):
    if not isinstance(text,str) or not text.strip():raise HTTPException(502,'Provider returned no final text')
    if schema:
        try:
            parsed=json.loads(text)
            if isinstance(schema,dict):jsonschema.validate(parsed,response_validation_schema(schema))
        except (ValueError,jsonschema.ValidationError) as exc:
            error=HTTPException(502,'Provider output failed the unchanged application core schema');error.provider_category='INVALID_STRUCTURED_OUTPUT'
            error.raw_output=text;error.validation_diagnostic=str(exc)[:600];raise error from exc

async def infer(role:Role,request:InferenceRequest,*,authorization=None):
    config=role_config(role);remaining=request.deadline-time.monotonic()
    if remaining<=0:raise HTTPException(504,'Request-wide inference deadline exhausted')
    if not request.messages or any(m.get('role') not in {'system','user','assistant'} or not isinstance(m.get('content'),str) for m in request.messages):
        raise HTTPException(422,'Unsupported inference message contract')
    if config.provider!='ollama':
        if authorization is None:raise HTTPException(403,'External role requires server-owned exact synthetic consent')
        authorization.assert_current_roles()
    started=time.monotonic()
    if config.provider=='google':
        from llm.gemini_provider import interpret_rest
        text,model,usage=await interpret_rest(request.messages,request.schema,timeout=remaining,model=config.model,thinking=config.thinking,output_tokens=config.output_tokens,schema_mode=config.schema_mode)
    elif config.provider=='ollama':
        from llm.orchestration.model import chat_model
        from langsmith import tracing_context
        client,model=await chat_model(config.model,request.schema,output_tokens=config.output_tokens)
        with tracing_context(enabled=False):response=await asyncio.wait_for(client.ainvoke([(m['role'],m['content']) for m in request.messages]),min(30,remaining))
        text=response.content;meta=response.response_metadata or {};raw=response.usage_metadata or {}
        usage={'total_input_tokens':raw.get('input_tokens'),'total_output_tokens':raw.get('output_tokens'),
            'total_tokens':raw.get('total_tokens'),'finish_reason':meta.get('done_reason'),'transport':'ollama'}
        if meta.get('done_reason') not in {None,'stop'}:raise HTTPException(502,'Local role generation did not complete')
    else:text,model,usage=await _openai(config,request,remaining)
    validate_result(text,request.schema)
    return InferenceResult(text,model,config.provider,usage=usage,elapsed_ms=round((time.monotonic()-started)*1000,2))

async def _openai(config,request,seconds):
    """Opt-in stateless Responses adapter. No SDK retries or live key assumed."""
    global _openai_loop,_openai_limit
    key=os.getenv('OPENAI_API_KEY','')
    if not key:raise HTTPException(503,'OpenAI credential is not configured; no request dispatched')
    body={'model':config.model,'store':False,'input':request.messages,'max_output_tokens':config.output_tokens}
    if request.schema:
        if not isinstance(request.schema,dict):raise HTTPException(422,'OpenAI structured role requires an explicit JSON schema')
        body['text']={'format':{'type':'json_schema','name':'role_response','strict':True,'schema':request.schema}}
    from llm.gemini_provider import _quota_update
    receipt=None;started=time.monotonic();usage={}
    loop=asyncio.get_running_loop()
    if _openai_loop is not loop:_openai_loop,_openai_limit=loop,asyncio.Semaphore(1)
    try:
        async with asyncio.timeout(seconds),_openai_limit:
            while not receipt:
                receipt,wait=_quota_update(config.model,reservation=len(json.dumps(body).encode()),provider='openai')
                if not receipt:
                    if wait+3>=seconds-(time.monotonic()-started):raise HTTPException(429,'OpenAI pacing exceeds remaining request deadline')
                    await asyncio.sleep(wait)
            async with httpx.AsyncClient(trust_env=False,timeout=max(.1,seconds-(time.monotonic()-started))) as client:
                response=await client.post('https://api.openai.com/v1/responses',headers={'Authorization':'Bearer '+key},json=body)
                try:data=response.json()
                except ValueError:
                    if response.is_success:raise
                    data={}
            if not response.is_success:
                error=HTTPException(503,'OpenAI provider HTTP '+str(response.status_code));error.provider_http_status=response.status_code
                error.provider_category={400:'REQUEST_CONTRACT',401:'AUTHENTICATION',403:'PERMISSION',404:'MODEL_UNAVAILABLE',429:'QUOTA',500:'PROVIDER_ERROR',503:'PROVIDER_UNAVAILABLE'}.get(response.status_code,'HTTP_ERROR');raise error
            raw=data.get('usage') or {};usage={'total_input_tokens':raw.get('input_tokens'),'total_output_tokens':raw.get('output_tokens'),'total_tokens':raw.get('total_tokens'),'finish_reason':data.get('status'),'transport':'responses'}
            if data.get('status')!='completed':
                error=HTTPException(502,'OpenAI generation incomplete');error.provider_category='INCOMPLETE_GENERATION';raise error
            content=[part for output in data.get('output',[]) if output.get('type')=='message' for part in output.get('content',[])]
            if any(p.get('type')=='refusal' for p in content):
                error=HTTPException(502,'OpenAI declined the request');error.provider_category='MODEL_REFUSAL';raise error
            return ''.join(p.get('text','') for p in content if p.get('type')=='output_text'),config.model,usage
    except (asyncio.TimeoutError,httpx.TimeoutException) as exc:
        error=HTTPException(504,'OpenAI request timed out');error.provider_category='PROVIDER_TIMEOUT';raise error from exc
    except httpx.HTTPError as exc:
        error=HTTPException(503,'OpenAI connectivity failed');error.provider_category='CONNECTIVITY_FAILURE';raise error from exc
    except (ValueError,TypeError,AttributeError) as exc:
        error=HTTPException(502,'OpenAI returned an invalid provider response');error.provider_category='INVALID_PROVIDER_RESPONSE';raise error from exc
    finally:
        if receipt:
            try:_quota_update(config.model,identity=receipt,actual=usage.get('total_input_tokens'),provider='openai')
            except HTTPException:usage['quota_accounting']='Conservative reservation retained'
