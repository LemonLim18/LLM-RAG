"""
Google Gemini integrations in the existing provider domain.

The legacy provider uses google-genai. The experimental hybrid interpreter uses
stateless official REST, with server-approved synthetic requests, no remote
tools, and the shared gateway's existing planning/verification boundaries.
"""

import json
import logging
import os
import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException

from starlette.concurrency import run_in_threadpool

from llm.provider import LLMProvider, LLMMessage, LLMResponse, ToolCall

logger = logging.getLogger("llm.gemini")

# Experimental REST interpretation reuses this provider domain. No remote tools,
# SDK retries, cloud conversation store, or independent planner are introduced.
_hybrid_scope = ContextVar('gemini_hybrid_request', default=None)
_remote_loop = None
_remote_limit = None


def external_request_identity(owner, surface, identity, body, history):
    """Server-owned approval binds exact request AND owned history, not a client flag."""
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    return (owner, surface, identity, digest(body.model_dump_json()),
            digest(json.dumps(history, sort_keys=True, ensure_ascii=False)))


def current_hybrid_scope():
    return _hybrid_scope.get()


def cloud_model():
    selected = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
    if selected not in {'gemini-3.5-flash-lite', 'gemini-3.1-flash-lite'}:
        raise HTTPException(503, 'Select an explicitly supported cloud model; no automatic substitution')
    return selected


def scenario_approval_context(db):
    """Operator-approved sealed scenario bytes, including any activated source pack."""
    from local_providers.development import active_for
    manager = active_for(db)
    if manager is None:
        return None
    with manager.pin():
        scenario, context = manager.snapshot()
        bundle = manager.activated_bundle()
        fingerprint = hashlib.sha256(json.dumps({'scenario':scenario,'bundle':bundle},sort_keys=True).encode()).hexdigest()
    allowed = {v.strip() for v in os.getenv('COGNISHIELD_AI_HYBRID_SCENARIOS', '').split(',') if v.strip()}
    return {'eligible':fingerprint in allowed,'scenario_digest':fingerprint,
            'source_revision':context['source_revision'],'scenario_id':context['id']}


def hybrid_context(db):
    from lab_config import LOCAL_LAB
    context = scenario_approval_context(db) if LOCAL_LAB else None
    from llm.model_roles import experiment_enabled,role_manifest,consent_manifest
    roles=role_manifest() if experiment_enabled() else None
    envelope=consent_manifest() if roles else None
    return {'enabled':os.getenv('COGNISHIELD_AI_HYBRID','0')=='1' and LOCAL_LAB,
            'eligible':bool(context and context['eligible']),'model':roles['evidence_reasoner']['model'] if roles else cloud_model(),
            'planning_enabled':bool(roles) or os.getenv('COGNISHIELD_AI_HYBRID_INTERPRET','0')=='1',
            'planning_mode':'direct_complex_role' if roles else 'legacy_optional_refinement',
            'legacy_planning_refinement_enabled':os.getenv('COGNISHIELD_AI_HYBRID_INTERPRET','0')=='1',
            **(context or {}),'roles':roles,'multi_model':bool(roles),
            'experiment':envelope,
            'role_binding':hashlib.sha256(json.dumps(envelope,sort_keys=True).encode()).hexdigest(),
            'scope':'Exact owner-approved message/history, role models and consented investigation profile on an operator-approved synthetic revision; editor/uploads excluded'}


def approve_hybrid_request(db, store, user, identity, body, expected_revision):
    """Called only by the authenticated owner API, never a model-facing tool."""
    from auth.auth import normalize_role
    conversation = store.get(identity,user['username'])
    if normalize_role(user.get('role')) not in {'engineer','admin'}:
        raise HTTPException(403,'Synthetic cloud approval requires an engineer or administrator')
    context = hybrid_context(db)
    if not context['enabled'] or not context['eligible']:
        raise HTTPException(403,'Cloud approval requires an operator-approved active development scenario')
    if context['source_revision'] != expected_revision:
        raise HTTPException(409,'Scenario changed; inspect it before approving this message')
    if body.editor is not None or body.related_editors or body.attachment_ids:
        raise HTTPException(403,'Editor buffers and uploaded files cannot be approved for synthetic cloud inference')
    with db._connect() as c:
        if c.execute('SELECT 1 FROM ai_attachments WHERE conversation_id=? AND owner=? LIMIT 1',
                     (identity,user['username'])).fetchone():
            raise HTTPException(403,'Use a separate conversation without uploaded files')
        for row in c.execute("SELECT result FROM ai_turns WHERE conversation_id=? AND state='completed'",(identity,)):
            prior = json.loads(row[0]); coverage = prior.get('context_coverage',{})
            environment = coverage.get('environment',{})
            if (environment.get('origin')!='simulated' or prior.get('kind') in {'edit_proposal','generation_preview'}
                    or any(e.get('origin')!='simulated' and e.get('authority')!='published_operation_documentation' for e in prior.get('evidence',[]))):
                raise HTTPException(403,'History contains non-synthetic or engineering context; use a separate synthetic conversation')
    history = store.history(identity,user)
    stamp = external_request_identity(user['username'],conversation['assistant_kind'],identity,body,history)
    approvals = getattr(db,'_ai_external_approvals',{})
    approvals = {k:v for k,v in approvals.items() if v['expires']>time.monotonic()} if isinstance(approvals,dict) else {}
    if len(approvals)>=128:raise HTTPException(429,'Pending cloud approval limit reached')
    approvals[stamp] = {'expires':time.monotonic()+120,'scenario_digest':context['scenario_digest'],
                        'source_revision':context['source_revision'],'role_binding':context['role_binding']}
    db._ai_external_approvals = approvals
    return {'approved':True,'expires_in_seconds':120,'model':context['model'],'roles':context['roles'],
            'scope':'This exact message and reviewed owned history only; no execution authority'}


_quota_lock = __import__('threading').RLock()


def _quota_update(selected, reservation=None, identity=None, actual=None, provider='google'):
    """Small shared runtime ledger; no prompts/credentials, no application DB writes.

    One backend worker is expected; an OS file lock also prevents lost updates
    across overlapping workers. Busy/corrupt storage fails closed.
    """
    from pathlib import Path
    from uuid import uuid4
    from lab_config import PROJECT_DIR
    path = Path(os.getenv('COGNISHIELD_AI_HYBRID_USAGE',str(PROJECT_DIR/'tmp/ai-cloud-usage.json')))
    path.parent.mkdir(parents=True,exist_ok=True)
    with _quota_lock, path.with_suffix('.lock').open('a+b') as lock:
        try:
            lock.seek(0,2)
            if lock.tell()==0:lock.write(b'0');lock.flush()
            lock.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            try:
                now=time.time()
                rows=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
                rows=[row for row in rows if now-row['at']<86400]
                if identity:
                    for row in rows:
                        if row['id']==identity and type(actual) is int and actual>=0:row['input']=actual
                else:
                    current=[row for row in rows if row['model']==selected and row.get('provider','google')==provider]
                    shared=[row for row in rows if row.get('provider','google')==provider]
                    rpm=min(15,max(1,int(os.getenv('COGNISHIELD_AI_HYBRID_RPM','15'))))
                    tpm=min(150000,max(1,int(os.getenv('COGNISHIELD_AI_HYBRID_INPUT_TPM','150000'))))
                    rpd=min(500,max(1,int(os.getenv('COGNISHIELD_AI_HYBRID_RPD','500'))))
                    if len(current)>=rpd or len(shared)>=rpd or reservation>tpm:raise HTTPException(429,'Cloud quota ceiling reached; no request was dispatched')
                    recent=[row for row in shared if now-row['at']<61]
                    if len(recent)>=rpm or sum(row['input'] for row in recent)+reservation>tpm:
                        return None,max(.1,61-(now-min(row['at'] for row in recent)))
                    identity=uuid4().hex
                    rows.append({'id':identity,'provider':provider,'account_scope':'configured-project','model':selected,'at':now,'input':reservation})
                temporary=path.with_suffix('.'+uuid4().hex+'.tmp')
                temporary.write_text(json.dumps(rows),encoding='utf-8');os.replace(temporary,path)
                return identity,0
            finally:
                lock.seek(0)
                if os.name=='nt':msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
        except HTTPException:
            raise
        except (OSError,ValueError,TypeError,KeyError) as exc:
            raise HTTPException(503,'Cloud quota ledger is unavailable; no new request authorized') from exc


async def interpret_rest(messages, schema, *, timeout, model=None, thinking=None, output_tokens=None, schema_mode='json_schema'):
    """Correct per-model transport; stateless, schema validated, no retries/tools."""
    global _remote_loop, _remote_limit
    key=os.getenv('GEMINI_API_KEY','')
    if not key:raise HTTPException(503,'Gemini credential is not configured')
    selected=model or cloud_model()
    if selected not in {'gemini-3.5-flash-lite','gemini-3.1-flash-lite'}:
        raise HTTPException(503,'Unsupported cloud model; no automatic fallback')
    system='\n\n'.join(m['content'] for m in messages if m['role']=='system')
    rest=[m for m in messages if m['role']!='system']
    if not rest or any(m['role'] not in {'user','assistant'} for m in rest) or rest[-1]['role']!='user':
        raise HTTPException(422,'Cloud interpretation requires supported roles and a final user turn')
    thinking=thinking or os.getenv('COGNISHIELD_AI_HYBRID_THINKING','low')
    permitted={'minimal','low','medium','high'}
    if thinking not in permitted:raise HTTPException(422,'Unsupported thinking setting for selected cloud model')
    allowance=min(16384,max(128,int(output_tokens or os.getenv('COGNISHIELD_AI_HYBRID_OUTPUT_TOKENS','8192'))))
    endpoint='https://generativelanguage.googleapis.com/v1beta/models/'+selected+':generateContent'
    body={'contents':[{'role':'model' if m['role']=='assistant' else 'user','parts':[{'text':m['content']}]} for m in rest],
          'generationConfig':{'thinkingConfig':{'thinkingLevel':thinking},'maxOutputTokens':allowance}}
    if system:body['systemInstruction']={'parts':[{'text':system}]}
    if schema_mode not in {'json_schema','validated_json'}:raise HTTPException(422,'Unsupported Google schema mode')
    if schema:
        if isinstance(schema,dict):
            from llm.model_roles import provider_wire_schema
            wire_schema=provider_wire_schema(schema)
            if schema_mode=='json_schema':
                # Explicit native mode uses the current official REST format.
                # No automatic switch/retry follows a provider rejection.
                body['generationConfig']['responseFormat']={'text':{'mimeType':'APPLICATION_JSON','schema':wire_schema}}
            else:
                # Explicit capability fallback for complex grammars rejected
                # with400. Same schema, validated below; no automatic retry.
                body['generationConfig']['responseMimeType']='application/json'
                # Keep the current full instruction unless the separately
                # consented core-wire experiment is explicitly selected.
                from llm.model_roles import provider_wire_mode
                instruction='Return only JSON satisfying this exact application schema: '+json.dumps(wire_schema if provider_wire_mode()=='core_v1' else schema)
                body.setdefault('systemInstruction',{'parts':[]})['parts'].append({'text':instruction})
        else:body['generationConfig']['responseMimeType']='application/json'
    loop=asyncio.get_running_loop()
    if _remote_loop is not loop:_remote_loop,_remote_limit=loop,asyncio.Semaphore(1)
    started=time.monotonic();receipt=None;dispatched=False;usage={}
    try:
        async with asyncio.timeout(timeout):
            async with _remote_limit:
                while True:
                    receipt,wait=_quota_update(selected,reservation=len(json.dumps(body,ensure_ascii=False).encode('utf-8')))
                    if receipt:break
                    if wait+5>=timeout-(time.monotonic()-started):
                        raise HTTPException(429,'Cloud pacing exceeds the remaining request budget; no request dispatched')
                    await asyncio.sleep(wait)
                async with httpx.AsyncClient(trust_env=False,timeout=httpx.Timeout(max(.1,timeout-(time.monotonic()-started)),connect=min(10,timeout))) as client:
                    dispatched=True
                    response=await client.post(endpoint,headers={'x-goog-api-key':key},json=body)
                    try:data=response.json()
                    except ValueError:
                        # A proxy's HTML error page is still an HTTP failure,
                        # not a completed model answer or malformed schema.
                        if response.is_success:
                            error=HTTPException(502,'Gemini returned an invalid provider response')
                            error.provider_category='INVALID_PROVIDER_RESPONSE';raise error
                        data={}
                    if not isinstance(data,dict):
                        if response.is_success:
                            error=HTTPException(502,'Gemini returned an invalid provider response')
                            error.provider_category='INVALID_PROVIDER_RESPONSE';raise error
                        data={}
        if not response.is_success:
            failure=data.get('error') or {};status=failure.get('status') or failure.get('code') or 'HTTP_'+str(response.status_code)
            error=HTTPException(503,'Gemini provider failure: '+str(status).replace(key,'[REDACTED]')[:100])
            error.provider_category=str(status).replace(key,'[REDACTED]')[:100];error.provider_http_status=response.status_code
            raise error
        candidate=(data.get('candidates') or [{}])[0];raw=data.get('usageMetadata') or {}
        usage={'total_input_tokens':raw.get('promptTokenCount'),'total_output_tokens':raw.get('candidatesTokenCount'),
               'total_thought_tokens':raw.get('thoughtsTokenCount',0),'total_tokens':raw.get('totalTokenCount'),
               'thought_tokens_reported':'thoughtsTokenCount' in raw,
               'model_version':data.get('modelVersion'),'finish_reason':candidate.get('finishReason'),'transport':'generateContent','schema_mode':schema_mode}
        answer=''.join(p.get('text','') for p in candidate.get('content',{}).get('parts',[]) if not p.get('thought')).strip()
        complete=candidate.get('finishReason')=='STOP'
        if not complete or not answer:
            error=HTTPException(502,'Gemini returned an incomplete generation; no conclusion was inferred');error.provider_category='INCOMPLETE_GENERATION';raise error
        if isinstance(schema,dict):
            try:
                import jsonschema
                from llm.model_roles import response_validation_schema
                jsonschema.validate(json.loads(answer),response_validation_schema(schema))
            except (ValueError,jsonschema.ValidationError) as exc:
                error=HTTPException(502,'Cloud output failed the unchanged application JSON schema');error.provider_category='INVALID_STRUCTURED_OUTPUT'
                error.raw_output=answer;error.validation_diagnostic=str(exc)[:600];raise error from exc
        return answer,selected,usage
    except (asyncio.TimeoutError,httpx.TimeoutException) as exc:
        error=HTTPException(504,'Gemini provider timeout; no semantic verdict was inferred')
        error.provider_category='PROVIDER_TIMEOUT';error.provider_dispatched=dispatched;error.provider_usage=usage;raise error from exc
    except httpx.HTTPError as exc:
        error=HTTPException(503,'Gemini connectivity failure; no semantic verdict was inferred')
        error.provider_category='CONNECTIVITY_FAILURE';error.provider_dispatched=dispatched;error.provider_usage=usage;raise error from exc
    except HTTPException as exc:
        exc.provider_dispatched=dispatched;exc.provider_usage=usage
        raise
    except (ValueError,KeyError,TypeError,AttributeError) as exc:
        error=HTTPException(502,'Gemini returned an invalid provider response')
        error.provider_category='INVALID_PROVIDER_RESPONSE';error.provider_dispatched=dispatched;error.provider_usage=usage;raise error from exc
    finally:
        if receipt:
            try:_quota_update(selected,identity=receipt,actual=usage.get('total_input_tokens'))
            except HTTPException:
                # Admission already persisted a conservative reservation.
                # Failed usage reconciliation must not replace a real401/429
                # (or a completed response) with an unrelated ledger error.
                # Future admission still requires the same working ledger.
                usage['quota_accounting']='conservative reservation retained; usage update unavailable'
                logger.warning('Cloud usage update unavailable; original admission reservation retained')


class HybridRequest:
    """Ephemeral server authorization and one request-wide clock; never checkpointed."""
    def __init__(self, started, outcomes=1):
        from llm.model_roles import investigation_profile
        self.investigation_profile=investigation_profile()
        self.deadline = started + (self.investigation_profile['seconds'] if self.investigation_profile['enabled'] else min(120, max(1, float(os.getenv('COGNISHIELD_AI_HYBRID_SECONDS', '120')))))
        self.outcomes = outcomes
        self.remote_calls = 0
        self.max_remote_calls = min(2, max(1, int(os.getenv('COGNISHIELD_AI_HYBRID_CALLS', '1'))))
        self.trace = []
        self.synthesis_allowed = False
        self.last_synthesis_remote = False
        self.remote_disabled = False
        self.usage = []
        self.db = None
        self.approved_scenario = None
        self.multi_model=False
        self.role_binding=None
        self.role_calls=0

    @classmethod
    def create(cls, db, store, user, surface, identity, body, started):
        approvals = getattr(db, '_ai_external_approvals', {})
        if not approvals or body.editor is not None or body.related_editors or body.attachment_ids:
            return None
        from auth.auth import normalize_role
        if normalize_role(user.get('role')) not in {'engineer','admin'}:
            return None
        history = store.history(identity, user)
        bound = external_request_identity(user['username'], surface, identity, body, history)
        approval = approvals.get(bound) if isinstance(approvals,dict) else None
        if not approval or approval['expires'] <= time.monotonic():
            return None
        context = scenario_approval_context(db)
        if (not context or not context['eligible'] or
                any(context[k] != approval[k] for k in ['scenario_digest','source_revision'])):
            return None
        effective=hybrid_context(db)
        if approval.get('role_binding')!=effective['role_binding'] or not effective['enabled']:return None
        with db._connect() as connection:
            if connection.execute('SELECT 1 FROM ai_attachments WHERE conversation_id=? AND owner=? LIMIT 1',
                                  (identity, user['username'])).fetchone():
                return None
        from llm.orchestration.request_contract import response_obligations
        approvals.pop(bound, None)
        scope = cls(started, len(response_obligations(body.prompt,include_actions=True)))
        scope.db, scope.approved_scenario = db, context
        scope.role_binding=effective['role_binding']
        if effective['multi_model']:
            from llm.gateway_services import inventory_snapshot
            from llm.gateway_network import route_network
            from llm.gateway_references import previous_context_reference,requested_authoring_artifact,relational_read
            from llm.gateway_network import explicit_configuration_scope
            from llm.orchestration.request_contract import advisory_contract
            from llm.orchestration.investigation import is_investigation
            domains,query=route_network(body.prompt,inventory_snapshot(db),expand_investigation=False)
            prior=previous_context_reference(store.last_result(identity,user['username'])).get('read')
            scoped=bool(query.get('device_refs') or prior)
            comparison=relational_read(body.prompt) and (explicit_configuration_scope(body.prompt)=='both' or len(query.get('device_refs',[]))>1
                or bool(__import__('re').search(r'\b(?:compare|contrast)\w*\b',body.prompt,__import__('re').I)))
            complex_request=bool(scoped and (is_investigation(body.prompt) or advisory_contract(body.prompt)
                or comparison or len(set(domains)-{'inventory'})>1 or scope.outcomes>1 or scope.investigation_profile['enabled']))
            scope.multi_model=complex_request and not requested_authoring_artifact(body.prompt)
            if scope.multi_model:scope.max_remote_calls=scope.investigation_profile['max_role_calls'] if scope.investigation_profile['enabled'] else min(3,max(1,int(os.getenv('COGNISHIELD_AI_MULTI_MODEL_CALLS','3'))))
        return scope

    def assert_current_roles(self):
        current=hybrid_context(self.db) if self.db else None
        if not current or not current['enabled'] or not current['eligible'] or current['role_binding']!=self.role_binding or any(
            current[k]!=self.approved_scenario[k] for k in ['scenario_digest','source_revision']):
            raise HTTPException(403,'Cloud model consent or source revision changed; approve the current request again')

    async def generate_role(self,role,messages,schema):
        from llm.model_roles import infer,InferenceRequest,role_config,failure_receipt
        self.assert_current_roles()
        if self.investigation_profile['enabled'] and self.remaining()<5:
            error=HTTPException(504,'Investigation request deadline/reservation exhausted; no call dispatched')
            error.provider_category='REQUEST_DEADLINE_EXCEEDED' if self.remaining()<=0 else 'REQUEST_BUDGET_RESERVATION_EXHAUSTED'
            raise error
        if self.investigation_profile['enabled'] and self.role_calls>=self.max_remote_calls:
            error=HTTPException(429,'Investigation role-call ceiling exhausted; no provider quota claim')
            error.provider_category='ROLE_CALL_LIMIT';raise error
        if self.remote_disabled or self.role_calls>=self.max_remote_calls or self.remaining()<5:
            raise HTTPException(429,'Shared role call/deadline budget exhausted')
        self.role_calls+=1
        if role_config(role).provider!='ollama':self.remote_calls+=1
        started=time.monotonic()
        # Planning reserves time for tools and the final reasoner. All calls
        # share this one monotonic request clock; no per-call reset to120s.
        profile=self.investigation_profile
        if profile['enabled']:
            stage=profile['planner_seconds'] if role=='complex_planner' else profile['reasoner_seconds']
            reserve=30 if role=='complex_planner' else 2
            deadline=min(self.deadline-reserve,time.monotonic()+stage)
        else:deadline=min(self.deadline-2,time.monotonic()+min(35,self.remaining()-35)) if role=='complex_planner' else self.deadline-2
        try:
            result=await infer(role,InferenceRequest(messages,schema,deadline),authorization=self)
            self.usage.append(result.usage)
            self.trace.append({'role':role,'provider':result.provider,'model':result.model,'status':result.completion,'elapsed_ms':result.elapsed_ms,'usage':result.usage})
            return result.text,result.model
        except HTTPException as exc:
            if getattr(exc,'provider_http_status',None) in {401,402,403,404,429}:self.remote_disabled=True
            self.trace.append({'role':role,'status':'provider_error','http_status':exc.status_code,
                'provider_http_status':getattr(exc,'provider_http_status',None),'category':getattr(exc,'provider_category','PROVIDER_ERROR'),
                'failure':failure_receipt(exc,stage=role,remaining=self.remaining()),
                'elapsed_ms':round((time.monotonic()-started)*1000,2)})
            raise

    @contextmanager
    def activate(self):
        token = _hybrid_scope.set(self)
        try:
            yield self
        finally:
            _hybrid_scope.reset(token)

    def remaining(self):
        return max(0, self.deadline - time.monotonic())

    def budget(self, purpose):
        # Cloud waits, local planning, readers and finalization share the same deadline.
        reserve = 45 if purpose == 'routing' else 2
        return max(0, min(30 if purpose == 'routing' else 90, self.remaining() - reserve))

    def may_interpret_plan(self, raw):
        if self.multi_model:return False  # The role planner already ran first.
        if (os.getenv('COGNISHIELD_AI_HYBRID_INTERPRET', '0') != '1'
                or self.max_remote_calls < 2 or self.remote_calls):
            return False
        try:
            plan = json.loads(raw)
        except ValueError:
            return False
        needs = plan.get('information_needs') or []
        return (plan.get('intent') in {'answer', 'explain'} and bool(needs)
                and any(n.get('domain') != 'inventory' for n in needs)
                and (len(needs) > 1 or self.outcomes > 1))

    def prepare_synthesis(self, results, evidence, planning, assessment):
        # Exact source verification/authorization remains in the existing graph.
        ids = {e.id: e for e in evidence}
        eligible = bool(results and evidence)
        for result in results:
            refs = [ids.get(i) for i in result.get('evidence_ids', [])]
            eligible = eligible and bool(refs) and all(e is not None and
                (e.origin == 'simulated' or result['tool'] == 'knowledge.search'
                 and e.authority == 'published_operation_documentation') for e in refs)
        proposed = planning.get('proposed', {})
        complex_task = (len({r['tool'] for r in results}) > 1 or self.outcomes > 1
                        or proposed.get('desired_response') in {'comparison', 'investigation'}
                        or proposed.get('intent') == 'explain'
                           and len(proposed.get('information_needs') or []) > 1)
        self.synthesis_allowed = bool(eligible and complex_task)
        if self.db:
            current = scenario_approval_context(self.db)
            self.synthesis_allowed = self.synthesis_allowed and bool(current and current['eligible'] and
                all(current[k] == self.approved_scenario[k] for k in ['scenario_digest','source_revision']))

    def prepare_advisory(self, context):
        # Existing Approach A already selects the no-reader advisory path.
        # This changes its provider dispatch only, not its plan or permissions.
        current=scenario_approval_context(self.db) if self.db else None
        self.synthesis_allowed=bool(current and current['eligible'] and self.approved_scenario and
            all(current[k]==self.approved_scenario[k] for k in ['scenario_digest','source_revision']) and
            context.get('devices') and context.get('authorized_readers'))

    async def generate(self, messages, schema, purpose):
        if purpose == 'synthesis':
            self.last_synthesis_remote = True
        if self.remote_disabled:
            raise HTTPException(503, 'Gemini is unavailable for this request; no provider retry or local causal substitution')
        seconds = self.budget(purpose)
        if self.remote_calls >= self.max_remote_calls or seconds < 5:
            raise HTTPException(429, 'Hybrid inference budget exhausted; no further remote call was made')
        self.remote_calls += 1
        started = time.monotonic()
        try:
            answer, model, usage = await interpret_rest(messages, schema, timeout=seconds)
            self.usage.append(usage)
            self.trace.append({'purpose': purpose, 'provider': 'gemini', 'model': model, 'status': 'completed',
                               'elapsed_ms': round((time.monotonic() - started) * 1000, 2), 'usage': usage})
            return answer, model
        except HTTPException as exc:
            if getattr(exc, 'provider_http_status', None) in {401, 402, 403, 404, 429}:
                self.remote_disabled = True
            self.trace.append({'purpose': purpose, 'provider': 'gemini', 'status': 'provider_error',
                               'http_status': exc.status_code,
                               'provider_http_status': getattr(exc, 'provider_http_status', None),
                               'category': getattr(exc, 'provider_category', 'TIMEOUT' if exc.status_code == 504 else 'PROVIDER_ERROR'),
                               'dispatched':getattr(exc,'provider_dispatched',False),
                               'usage':getattr(exc,'provider_usage',{}),
                               'elapsed_ms': round((time.monotonic() - started) * 1000, 2)})
            raise

    def public_stats(self):
        return {'mode': 'experimental_hybrid', 'model':__import__('llm.model_roles',fromlist=['role_config']).role_config('evidence_reasoner').model if self.multi_model else cloud_model(),
                'multi_model':self.multi_model,'roles':__import__('llm.model_roles',fromlist=['role_manifest']).role_manifest() if self.multi_model else None,
                'authorization': 'exact owner-approved request/history and operator-approved synthetic revision',
                'remote_calls': self.remote_calls, 'role_calls':self.role_calls,'maximum_remote_calls': self.max_remote_calls,
                'provider_disabled_for_request': self.remote_disabled,
                'remaining_seconds': round(self.remaining(), 3), 'trace': self.trace,
                'scope': 'Provider interpretation is not root-cause certification; no remote tools or cloud conversation state.'}

# ---------------------------------------------------------------------------
# Try to import google-genai SDK
# ---------------------------------------------------------------------------
try:
    from google import genai
    from google.genai import types as genai_types
    _HAS_GENAI = True
except ImportError:
    _HAS_GENAI = False
    logger.info("google-genai SDK not installed; legacy SDK provider unavailable, experimental REST transport is independent")


class GeminiProvider(LLMProvider):
    """
    LLM provider backed by Google Gemini.

    Configuration:
        - ``api_key``:  Gemini API key (or set ``GEMINI_API_KEY`` env var)
        - ``model``:    Model name (default ``gemini-2.5-flash``)
    """

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        if not _HAS_GENAI:
            raise ImportError(
                "google-genai SDK is required: pip install google-genai"
            )

        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._model = model or self.DEFAULT_MODEL
        # Initialize client. standard sync client.
        if self._api_key:
            self._client = genai.Client(api_key=self._api_key)
        else:
            logger.warning("No Gemini API Key provided.")
            self._client = None
            
        logger.info("GeminiProvider initialized (model=%s)", self._model)

    def model_name(self) -> str:
        return self._model

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """
        Call Gemini with the conversation history and optional tools.

        Uses native ``system_instruction`` and structured ``Content``
        objects instead of string concatenation so Gemini can leverage
        its built-in multi-turn support and reduce token overhead.
        """
        system_text, contents = self._build_contents(messages)

        gemini_tools = self._build_tools(tools) if tools else None

        try:
            config_kwargs: Dict[str, Any] = {"temperature": temperature}
            if system_text:
                config_kwargs["system_instruction"] = system_text
            if gemini_tools:
                config_kwargs["tools"] = gemini_tools

            config = genai_types.GenerateContentConfig(**config_kwargs)

            response = await run_in_threadpool(
                self._client.models.generate_content,
                model=self._model,
                contents=contents,
                config=config,
            )

            return self._parse_response(response)

        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return LLMResponse(
                content=f"Error calling Gemini API: {e}",
                finish_reason="error",
            )

    # ------------------------------------------------------------------
    # Message conversion
    # ------------------------------------------------------------------

    def _build_contents(
        self, messages: List[LLMMessage]
    ) -> tuple[str, list[genai_types.Content]]:
        """Convert LLMMessage list into Gemini-native structured objects.

        Returns ``(system_instruction_text, contents_list)`` where
        system messages are extracted into ``system_instruction`` (fed
        via ``GenerateContentConfig``) and user/assistant/tool messages
        become proper ``Content`` objects with the correct ``role``.
        """
        system_parts: List[str] = []
        contents: list[genai_types.Content] = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            elif msg.role == "user":
                contents.append(
                    genai_types.Content(
                        role="user",
                        parts=[genai_types.Part.from_text(text=msg.content)],
                    )
                )
            elif msg.role == "assistant":
                parts: list[genai_types.Part] = []
                if msg.content:
                    parts.append(genai_types.Part.from_text(text=msg.content))
                for tc in msg.tool_calls:
                    parts.append(
                        genai_types.Part.from_function_call(
                            name=tc.name,
                            args=tc.arguments,
                        )
                    )
                if parts:
                    contents.append(
                        genai_types.Content(role="model", parts=parts)
                    )
            elif msg.role == "tool":
                contents.append(
                    genai_types.Content(
                        role="user",
                        parts=[
                            genai_types.Part.from_function_response(
                                name=msg.name or "tool",
                                response={"result": msg.content},
                            )
                        ],
                    )
                )

        system_text = "\n\n".join(system_parts) if system_parts else ""
        return system_text, contents

    # ------------------------------------------------------------------
    # Tool declaration conversion
    # ------------------------------------------------------------------

    def _build_tools(self, tools: List[Dict]) -> List:
        """Convert our tool definitions to Gemini function declarations."""
        declarations = []
        for tool in tools:
            fn_decl = genai_types.FunctionDeclaration(
                name=tool["name"],
                description=tool.get("description", ""),
                parameters=tool.get("parameters"),
            )
            declarations.append(fn_decl)
        return [genai_types.Tool(function_declarations=declarations)]

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse Gemini response into our LLMResponse dataclass."""
        tool_calls: List[ToolCall] = []
        text_parts: List[str] = []

        try:
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        args = {}
                        if fc.args:
                            # Convert proto Map to dict
                            args = dict(fc.args)
                        tool_calls.append(ToolCall(
                            name=fc.name,
                            arguments=args,
                        ))
                    elif hasattr(part, "text") and part.text:
                        text_parts.append(part.text)
        except Exception as e:
            logger.warning("Error parsing Gemini response: %s", e)
            # Fallback: try .text property
            try:
                text_parts.append(response.text)
            except Exception:
                text_parts.append(str(response))

        content = "\n".join(text_parts)
        finish = "tool_calls" if tool_calls else "stop"

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish,
            raw=response,
        )
