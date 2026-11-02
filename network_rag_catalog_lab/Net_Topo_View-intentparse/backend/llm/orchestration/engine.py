"""Shared bounded agent graph. Existing readers and engineering services retain authority."""
import asyncio
import re
import time
import os
import hashlib
from uuid import UUID
from fastapi import HTTPException
from langgraph.graph import StateGraph,START,END
from langsmith import tracing_context
from llm.gateway_models import ToolResult
from llm.gateway_network import network_context,route_network
from llm.gateway_references import retrieval_state,attributes
from llm.gateway_routing import select_context,SemanticRoute
from llm.orchestration.state import AgentState,ToolStep
from llm.orchestration.adapters import AuthorizedTools
from llm.orchestration.model import RoutingModel
from llm.orchestration.verification import verify_records,release_answer
from development.source_registry import SOURCES


def required_synthesis_readers(prompt,inventory,domains):
    """User-named sources, not every auxiliary reader proposed by a model."""
    from development.source_registry import explicit_read_sources,BY_KEY,reader_domains
    from llm.gateway_references import read_intent_text
    explicit=set(route_network(prompt,inventory,expand_investigation=False)[0])-{'inventory','topology'}
    # A route/path relationship can be established by a forwarding assessment;
    # it does not itself ask to consult the topology source. Named registry
    # sources (observed links, planned links, etc.) still require their reader.
    if re.search(r'\btopolog(?:y|ies)\b',read_intent_text(prompt),re.I):explicit.add('topology')
    explicit.update(reader_domains(explicit_read_sources(prompt,BY_KEY),domains))
    return {('inventory.read' if d=='inventory' else 'knowledge.search' if d=='knowledge' else 'network.'+d) for d in explicit}


DOMAIN_TO_TOOL={'inventory':'inventory.read','knowledge':'knowledge.search',**{d:'network.'+d for d in ['topology','configuration','syslog','telemetry','incidents','state']}}


def evidence_fingerprint(results,evidence):
    """Bind a completed draft to actual server evidence, not a prose verdict."""
    import json
    value={'results':results,'evidence':[e.model_dump(mode='json') for e in evidence]}
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()


async def run(service,identity,user,kind,body,auth,history,attachments,previous,inventory,timeout=120,b2=False,b3=False):
    if kind!='floating' and not (b3 and kind=='studio'):raise HTTPException(403,'This orchestration version does not authorize Studio')
    if (auth.principal!=user['username'] or auth.assistant_kind!=kind or auth.conversation_id!=identity):
        raise HTTPException(403,'Agent authorization is not bound to this owner and conversation')
    model=RoutingModel()
    if getattr(model,'hybrid',None):
        timeout=min(timeout,model.hybrid.remaining())
    profile=getattr(getattr(model,'hybrid',None),'investigation_profile',{'enabled':False})
    completeness=bool(profile['enabled'] and getattr(getattr(model,'hybrid',None),'multi_model',False))
    if completeness:timeout=model.hybrid.remaining()
    tools=AuthorizedTools(service.registry,service.store,auth,max_calls=profile['max_readers'] if completeness else 8)
    engineering_tools=AuthorizedTools(service.registry,service.store,auth,max_calls=1,
        names=frozenset({'v9.preview','document.propose'}),effects=frozenset({'propose'})) if b3 and kind=='studio' else None
    started=time.monotonic()
    def retrieval_envelope(state):
        from llm.orchestration.evidence_harness import guidance,settings
        value={'executed_queries':tools.requests,'remaining_tool_calls':max(0,tools.max_calls-tools.calls),
            'remaining_seconds':round(model.hybrid.remaining(),3),'remaining_role_calls':model.hybrid.max_remote_calls-model.hybrid.role_calls}
        if completeness:
            from llm.orchestration.investigation_support import network_map,artifact_comparisons,evidence_envelope,COMPATIBILITY
            mode=state.route.planning.get('investigation',{}).get('breadth')
            value['supplementary_permitted']=state.rounds<profile['max_rounds'] and value['remaining_role_calls']>=2
            value['investigation_context']={'network':network_map(inventory,state.results,state.device_refs,mode=='comprehensive'),
                'artifact_history':artifact_comparisons(state.results,inventory),'evidence_envelopes':evidence_envelope(state.results),
                'claim_source_compatibility':{k:sorted(v) for k,v in COMPATIBILITY.items()},
                'previous_review':state.investigation.get('last_review'),
                'previous_draft':state.role_decision.get('answer')}
        if settings()['guidance']:
            permitted=state.rounds<(profile['max_rounds'] if completeness else 2) and value['remaining_role_calls']>=2 and value['remaining_tool_calls']>0 and value['remaining_seconds']>10
            value['reader_guidance']=guidance(state,inventory,service.registry,tools.tools,tools.requests)[:value['remaining_tool_calls']] if permitted else []
        return value
    saver=None;restore_status='disabled';saved_memory=None
    if b2:
        from llm.orchestration.memory import InvestigationSaver
        saver=InvestigationSaver(service.store,auth,str(body.request_id))
        saved_memory,restore_status=saver.load_memory()
    prior_engineering=None
    if b3 and kind=='studio':
        from llm.orchestration.studio import previous_engineering
        prior_engineering=previous_engineering(service,identity,user,saved_memory,previous)

    def update(state,node,**values):return {**values,'trace':state.trace+[node]}

    async def understand(state):
        from llm.gateway_routing import advisory_route
        role_preview=bool(getattr(getattr(model,'hybrid',None),'multi_model',False))
        route=None
        if role_preview:
            from llm.orchestration.planning import propose
            from llm.gateway_references import previous_context_reference,resolve_read,read_intent_text
            schemas=[{'reader':name,'parameters':service.registry.capability(name).input_model.model_json_schema()}
                for name in tools.tools if service.registry.capability(name) and service.registry.capability(name).effect=='read']
            role_inventory={**inventory,'authorized_reader_schemas':schemas}
            try:
                route=await propose(body.prompt,body.model,kind,None,[],history,role_inventory,model.generate,
                    read_only_request=True,previous_reference=previous_context_reference(previous))
            except ValueError as exc:
                from pydantic import ValidationError
                failure={'stage':'planning','category':'SCHEMA_INVALID_PLAN' if isinstance(exc,ValidationError) else 'POLICY_REJECTED_PLAN',
                    'code':'INVALID_READ_PLAN','message':'The proposed read plan was rejected; no reader was executed.',
                    'reason':'Planner output does not match the authorized JSON schema.' if isinstance(exc,ValidationError) else str(exc)[:400]}
                route=advisory_route(body.prompt,previous,inventory)
                if route is None:
                    rejected=HTTPException(422,detail=failure['message'])
                    rejected.planning_diagnostics=failure
                    raise rejected from exc
                route.planning['rejected_planner_proposal']=failure
            if route.intent not in {'answer','explain','clarify'} or route.use_editor or route.use_attachments:
                raise HTTPException(403,'Experimental interpretation can propose read-only workflows only')
            advice=advisory_route(body.prompt,previous,inventory)
            if advice:
                advice.planning['cloud_planner_proposal']=route.planning;route=advice
            else:
                resolved=resolve_read(read_intent_text(body.prompt),previous,inventory)
                if resolved and (resolved.get('use_history') or resolved.get('interface_refs') and route.network_domains and route.intent in {'answer','explain'}):
                    # The same server-resolved port binding applies to direct
                    # approved role planning and the ordinary local route.
                    # A model reader proposal cannot erase an exact subject.
                    route.planning['interface_scope_adjustment']={'model_device_refs':route.device_refs,
                        'model_interface_refs':route.interface_refs,'resolved_interface_refs':resolved['interface_refs']}
                    route.device_refs=resolved['device_refs'];route.interface_refs=resolved['interface_refs']
                    route.use_history=route.use_history or resolved.get('use_history',False)
                if resolved and re.search(r'\b(?:do not|don.t|never)\s+(?:read|query|consult|retrieve|collect)\s+(?:any\s+)?other\s+(?:sources|readers)\b',body.prompt,re.I):
                    from llm.orchestration.request_contract import reader_constraints
                    policy=reader_constraints(body.prompt)
                    # Identity attributes may make the reference resolver infer
                    # inventory. The original explicit source boundary, when
                    # present, remains authoritative over that inference.
                    expected=(policy['allowed']-policy['denied'] if policy['allowed'] is not None else set(resolved.get('domains',[])))
                    if set(route.network_domains)!=expected:
                        raise HTTPException(422,'Cloud plan violates the original exclusive source restriction')
            route.planning['role_mode']='direct_complex_planner'
            route.planning['authorized_reader_schemas']=schemas
            from llm.orchestration.request_contract import constrain_readers
            retained,receipt=constrain_readers(route.network_domains,body.prompt)
            if retained!=route.network_domains:
                route.planning['server_source_constraint']=receipt
                route.network_domains=retained
                route.source_requests={d:v for d,v in route.source_requests.items() if d in retained}
            if completeness:
                from llm.orchestration.investigation_support import reconcile
                route=reconcile(body.prompt,route,service.registry,tools.tools)
        else:route=advisory_route(body.prompt,previous,inventory)
        if route is None and b3 and kind=='studio':
            from llm.orchestration.studio import contextual_studio_route
            route=contextual_studio_route(body.prompt,body.editor,prior_engineering)
        if b2:
            from llm.orchestration.investigation import contextual_route
            if route is None and not (kind=='studio' and body.editor and re.search(r'\b(active|unsaved|selected|editor|open file|current file)\b',body.prompt,re.I)):
                route=contextual_route(body.prompt,saved_memory,previous,inventory)
        if route is None:
            route=await select_context(body.prompt,body.model,kind,body.editor if b3 and kind=='studio' else None,attachments,history,
                previous=previous,inventory=inventory,generate_fn=model.generate)
        if b3:
            # A named network resource does not authorize changing an unrelated
            # open document. V9 must clarify network actions in this scope.
            named_target=any(re.search(r'(?<![\w-])'+re.escape(d['hostname'])+r'(?![\w-])',body.prompt,re.I) for d in inventory['devices'])
            document_request=bool(re.search(r'\b(file|document|buffer|editor|selected|selection|open code|this code|current code|template)\b',body.prompt,re.I))
            if kind=='studio' and route.intent=='edit' and named_target and not document_request and re.search(r'\b(configure|enable|disable|set|change|remove|add)\b',body.prompt,re.I):
                route=SemanticRoute(intent='generate_playbook' if re.search(r'\bplaybook\b',body.prompt,re.I) else 'generate_native')
            from llm.gateway import constrain_route,Route
            constrained=constrain_route(Route(intent=route.intent,question=route.question),body.prompt)
            if constrained.intent!=route.intent:
                route.planning['explicit_effect_constraint']={'proposed_intent':route.intent,'allowed_intent':constrained.intent,
                    'authority':'latest user instruction; no engineering effect executed'}
            route.intent=constrained.intent;route.question=constrained.question
        from llm.orchestration.request_contract import outcome_pilot_enabled,requested_contract,requested_clauses
        if outcome_pilot_enabled() and route.intent in {'answer','explain'}:
            if route.requested_outcomes is None:
                route.requested_outcomes=requested_contract(body.prompt,needs=[{'domain':d} for d in route.network_domains],source_requests=route.source_requests,inventory=inventory)
            else:
                original={c['id']:c['text'] for c in requested_clauses(body.prompt)}
                contract=route.requested_outcomes
                if set(original)=={o.id for o in contract.outcomes}:
                    contract.original_request=body.prompt
                    for outcome in contract.outcomes:outcome.instruction=original[outcome.id]
                else:
                    route.requested_outcomes=requested_contract(body.prompt,needs=[{'domain':d} for d in route.network_domains],source_requests=route.source_requests,inventory=inventory)
            contract=route.requested_outcomes
            executable=contract.execution_queries({d:route.source_requests.get(d,{'source_scope':'auto'}) for d in route.network_domains})
            route.source_requests=executable;route.network_domains=list(executable)
            from llm.gateway_references import resolve_read,read_intent_text
            owned=resolve_read(read_intent_text(body.prompt),previous,inventory)
            if owned and owned.get('use_history') and not owned.get('question'):
                # Reference identity does not depend on the model remembering
                # its history flag. Do not restore old observations as facts.
                route.use_history=True;route.device_refs=owned['device_refs'];route.interface_refs=owned['interface_refs']
        if not role_preview and b2 and inventory.get('scenario') and route.planning.get('mode')!='validated_model_plan' and not any(query.get('source_categories') for query in route.source_requests.values()):
            from llm.orchestration.investigation import is_investigation
            if route.network_domains and (is_investigation(body.prompt) or route.use_history and is_investigation(saved_memory.goal) or re.search(r'\b(reachability|routing table|route table|adjacenc\w*|interface state)\b',body.prompt,re.I)):
                route.network_domains=list(dict.fromkeys(route.network_domains+['inventory','topology','state']))
        memory={}
        if b2:
            from llm.orchestration.memory import InvestigationMemory
            from llm.gateway_network import redact
            document_ids=[]
            if route.use_attachments:
                requested=[str(i) for i in body.attachment_ids]
                named=[a['id'] for a in attachments if a.get('id') and a['name'].casefold() in body.prompt.casefold()]
                from llm.gateway_documents import file_selection_hint
                if requested or file_selection_hint(attachments,body.prompt,previous)!='scenario':
                    requested=requested or named or saved_memory.documents or [a['id'] for a in attachments if a.get('id')]
                with service.db._connect() as c:
                    document_ids=[i for i in requested if c.execute('SELECT 1 FROM ai_attachments WHERE id=? AND conversation_id=? AND owner=?',(i,identity,user['username'])).fetchone()]
                if len(document_ids)!=len(requested):
                    route.intent='clarify';route.question='A referenced attachment is no longer available in this conversation. Which attached document should I read?'
                    route.network_domains=[]
            memory={**(saved_memory.model_dump() if route.use_history else InvestigationMemory().model_dump()),'goal':saved_memory.goal if route.use_history and saved_memory.goal else redact(body.prompt)[:2000],
                'device_refs':route.device_refs,'interface_refs':route.interface_refs,'domains':route.network_domains,'source_requests':route.source_requests,
                'attributes':route.attributes,'documents':document_ids[:5],'turn_ref':str(body.request_id),'status':'running'}
            if b3 and kind=='studio' and (route.use_editor or route.intent.startswith('generate_')):
                from llm.orchestration.studio import editor_reference
                memory['editor_ref']=editor_reference(body.editor) if route.use_editor else {}
            elif not route.network_domains and not route.use_attachments and not (route.requested_outcomes and route.use_history):memory={'status':'running'}
        return update(state,'understand_request',route=route,context_references={
            'previous_request':previous.get('request_id') if previous and route.use_history else None,
            'user_history':[m['content'][:2000] for m in history[-6:] if m['role']=='user'] if route.use_history else [],
            'attachment_names':[item['name'] for item in attachments] if route.use_attachments else [],
            **({'advisory':{'prior_user_goal':saved_memory.goal if route.use_history else '',
                **({'prior_authorized_records':(previous or {}).get('observations',[]) if route.use_history else [],
                    'prior_source_evidence':(previous or {}).get('evidence',[]) if route.use_history else [],
                    'prior_record_time_scope':'Previous owned turn; not a fresh read or current observation'} if role_preview else {}),
                'prior_readers':saved_memory.domains if route.use_history else [],
                'prior_read_receipts':[{key:row[key] for key in ['tool','status','evidence_ids'] if key in row}
                    for row in (previous or {}).get('observations',[]) if row.get('tool') in tools.tools]
                    if route.use_history else [],
                'open_questions':saved_memory.open_questions if route.use_history else [],
                'source_revisions':saved_memory.evidence_revisions if route.use_history else {},
                'devices':[d['hostname'] for d in inventory['devices'] if str(d['id']) in route.device_refs],
                'authorized_readers':sorted(tools.tools),
                'source_catalog':[{'source':s.key,'meaning':s.description or s.title,
                    'readers':{name:list(s.record_kinds(name)) for name in s.readers if name in tools.tools}}
                    for s in SOURCES
                    if any(name in tools.tools for name in s.readers)],
                'authority':'Owned references and previous read gaps only; no current observations or diagnosis'}}
                if b2 and route.requested_outcomes and not route.network_domains else {})},memory=memory)

    async def resolve(state):
        route=state.route.model_copy(deep=True)
        refs=route.device_refs or route_network(route.network_request or body.prompt,inventory)[1].get('device_refs',[])
        selected=[];missing=[]
        for ref in refs:
            matches=[d for d in inventory['devices'] if str(ref).casefold() in {str(d['id']),d['hostname'].casefold(),str(d['management_ip'] or '').casefold(),*[a.casefold() for a in d.get('aliases',[])]}]
            if len(matches)!=1:missing.append(ref)
            elif str(matches[0]['id']) not in selected:selected.append(str(matches[0]['id']))
        if missing and route.network_domains:
            route.intent='clarify';route.question='No unique stored device matches '+', '.join(missing)+'. Which recorded device do you mean?';route.network_domains=[]
        if route.network_domains:route.device_refs=selected;route.attributes=route.attributes or attributes(body.prompt)
        values={'route':route,'device_refs':selected,'interface_refs':route.interface_refs}
        if b2:
            from llm.orchestration.investigation import initial_domains
            values.update(memory={**state.memory,'device_refs':selected,'domains':route.network_domains},pending_domains=list(route.network_domains) if completeness else initial_domains(route,route.network_request or body.prompt))
        if state.route.requested_outcomes and state.route.requested_outcomes.advice_only:
            context={**state.context_references}
            context['advisory']={**context.get('advisory',{}),
                'devices':[d['hostname'] for d in inventory['devices'] if str(d['id']) in selected]}
            values['context_references']=context
        return update(state,'resolve_references',**values)

    async def select(state):
        already={item['tool'] for item in state.results}
        domains=[d for d in (state.pending_domains if b2 else state.route.network_domains) if DOMAIN_TO_TOOL[d] not in already]
        plan=[ToolStep(tool=DOMAIN_TO_TOOL[d],domain=d) for d in domains]
        if getattr(getattr(model,'hybrid',None),'multi_model',False) and state.rounds and (completeness or state.rounds==1):
            plan=[ToolStep(tool=q['reader'],domain=q['domain'],parameters=q['parameters']) for q in state.route.planning.get('supplementary_queries',[])]
        if len(plan)+tools.calls>tools.max_calls:raise HTTPException(429,'Agent tool-call budget exhausted')
        if any(step.tool not in tools.tools for step in plan):raise HTTPException(403,'Tool plan is not authorized')
        return update(state,'select_authorized_tools',plan=plan)

    async def execute(state):
        if completeness:
            contexts=[];sources=[];covered={};refs=list(state.device_refs)
            stage=profile['initial_read_seconds'] if not state.rounds else profile['supplement_read_seconds']
            tools.stage_deadline=min(model.hybrid.deadline,time.monotonic()+stage)
            steps=state.plan
            if not state.rounds and state.route.planning.get('investigation',{}).get('breadth')=='comprehensive':
                order={'inventory':0,'topology':1,'state':2,'configuration':3,'syslog':4,'telemetry':5,'incidents':6}
                steps=sorted(steps,key=lambda step:order.get(step.domain,7))
            omissions=[]
            for step in steps:
                if time.monotonic()>=tools.stage_deadline or tools.calls>=tools.max_calls:
                    omissions.append({'reader':step.tool,'status':'NOT_QUERIED_BUDGET'});continue
                parameters=step.parameters
                if parameters is None and not state.rounds and step.domain in {'syslog','telemetry','incidents','knowledge'} and state.route.planning.get('investigation',{}).get('breadth')=='comprehensive':
                    parameters={'device_refs':refs,'limit':1 if step.domain=='knowledge' else 8,**state.route.source_requests.get(step.domain,{})}
                if parameters is None and refs!=state.device_refs and step.domain!='inventory':
                    parameters={'device_refs':refs,**state.route.source_requests.get(step.domain,{})}
                rows,found,receipts=await network_context(service.db,tools,auth,state.route.network_request or body.prompt,
                    domains_override=[step.domain],device_refs_override=refs or None,source_requests=state.route.source_requests,
                    interface_refs_override=state.interface_refs,validated_parameters={step.domain:parameters} if parameters is not None else None)
                contexts.extend(rows);sources.extend(found);covered.update(receipts)
                if state.route.planning.get('investigation',{}).get('breadth')=='comprehensive':
                    aliases={str(v).casefold():str(d['id']) for d in inventory['devices'] for v in [d['id'],d['hostname'],*d.get('aliases',[])]}
                    def related(value,key=''):
                        if isinstance(value,dict):
                            for k,v in value.items():related(v,k)
                        elif isinstance(value,list):
                            for v in value:related(v,key)
                        elif key in {'device_id','src_device_id','dst_device_id','source_device_id','destination_device_id','graph_path','scope_device_refs'} and str(value).casefold() in aliases:
                            ref=aliases[str(value).casefold()]
                            if ref not in refs:refs.append(ref)
                    for row in rows:related(row.get('data'))
            tools.stage_deadline=None
            return update(state,'execute_tools',results=state.results+contexts,evidence=state.evidence+sources,
                coverage=covered,rounds=state.rounds+1,device_refs=refs,
                investigation={**state.investigation,'budget_omissions':state.investigation.get('budget_omissions',[])+omissions})
        if getattr(getattr(model,'hybrid',None),'multi_model',False) and state.rounds:
            contexts=[];evidence=[];coverage={}
            for step in state.plan:
                rows,sources,covered=await network_context(service.db,tools,auth,state.route.network_request or body.prompt,
                    domains_override=[step.domain],device_refs_override=state.device_refs or None,
                    source_requests=state.route.source_requests,interface_refs_override=state.interface_refs,
                    validated_parameters={step.domain:step.parameters})
                contexts.extend(rows);evidence.extend(sources);coverage.update(covered)
            return update(state,'execute_tools',results=state.results+contexts,evidence=state.evidence+evidence,coverage=coverage,rounds=state.rounds+1)
        contexts,evidence,coverage=await network_context(service.db,tools,auth,state.route.network_request or body.prompt,
            domains_override=[step.domain for step in state.plan],device_refs_override=state.device_refs or None,
            source_requests=state.route.source_requests,interface_refs_override=state.interface_refs,
            **({'validated_parameters':state.route.planning.get('supplementary_parameters',{})}
               if getattr(getattr(model,'hybrid',None),'multi_model',False) and state.rounds else {}))
        return update(state,'execute_tools',results=state.results+contexts,evidence=state.evidence+evidence,
            coverage=coverage,rounds=state.rounds+1)

    async def evaluate(state):
        if b2:
            from llm.orchestration.investigation import assess,additional_domains
            from llm.orchestration.verification import assessment_context
            assessment=assess(assessment_context(state.results,tools.results),state.evidence)
            if getattr(getattr(model,'hybrid',None),'multi_model',False):
                from llm.orchestration.role_reasoning import decide,validate_additional
                model.hybrid.assert_current_roles()
                current=assessment_context(state.results,tools.results)
                continuation=state.role_decision.get('supplementary_receipt')
                if completeness:
                    from llm.orchestration.investigation_support import post_draft
                    from llm.model_roles import failure_receipt
                    route=state.route.model_copy(deep=True);decision=state.role_decision;events=list(state.investigation.get('drafts',[]));review={}
                    async def review_draft(candidate):
                        started=time.monotonic()
                        fingerprint=hashlib.sha256(candidate.get('raw_output',candidate.get('answer','')).encode()).hexdigest()
                        try:
                            reviewed=await asyncio.wait_for(asyncio.to_thread(post_draft,state,candidate,inventory,service.registry,tools.tools,tools.requests),timeout=max(.001,min(profile['adequacy_seconds'],model.hybrid.remaining())))
                        except (asyncio.TimeoutError,ValueError,KeyError,TypeError,AttributeError) as exc:
                            reviewed={'state':'ADEQUACY_TIMEOUT' if isinstance(exc,asyncio.TimeoutError) else 'VALIDATOR_ERROR',
                                'claim_compatibility':{'conflicts':review.get('claim_compatibility',{}).get('conflicts',[]) if review.get('draft_fingerprint')==fingerprint else []},
                                'server_proposals':[],'unread_dependencies':[],'limitation':'Evidence review incomplete; no semantic verdict inferred: '+type(exc).__name__}
                        reviewed['elapsed_ms']=round((time.monotonic()-started)*1000,3)
                        reviewed['draft_fingerprint']=fingerprint
                        return reviewed
                    # Revisions with no extra source read stay in this same
                    # bounded graph node; no extra planner or review model.
                    while model.hybrid.role_calls<model.hybrid.max_remote_calls and model.hybrid.remaining()>5:
                        try:
                            decision=await decide(model,body.prompt,current,state.evidence,state.context_references.get('user_history',[]),route.planning,
                                continuation=continuation,retrieval=retrieval_envelope(state))
                            decision['consumed_evidence_fingerprint']=evidence_fingerprint(current,state.evidence)
                        except (HTTPException,ValueError) as exc:
                            # A valid earlier core survives failed correction on
                            # the SAME evidence. A failed generation cannot make
                            # it an interpretation of newly acquired records.
                            retained_core=bool(decision.get('raw_output'))
                            changed=retained_core and decision.get('consumed_evidence_fingerprint')!=evidence_fingerprint(current,state.evidence)
                            if retained_core and not changed:
                                review=await review_draft(decision)
                            failures=list(state.investigation.get('revision_failures',[]))
                            failures.append({'kind':'MODEL_CONTRACT_ERROR' if getattr(exc,'provider_category',None)=='INVALID_STRUCTURED_OUTPUT' or isinstance(exc,ValueError) else 'EXECUTION_FAILURE',
                                'raw_output':getattr(exc,'raw_output',None),'diagnostic':getattr(exc,'validation_diagnostic',None),
                                'evidence_delivery':getattr(exc,'evidence_delivery',None),
                                'retained_valid_core':retained_core,'semantic_verdict':'NOT_ASSESSED',
                                'retained_draft_release':'WITHHELD_EVIDENCE_CHANGED' if changed else 'RETAINED_SAME_EVIDENCE' if retained_core else 'NO_PRIOR_CORE'})
                            state.investigation={**state.investigation,'revision_failures':failures}
                            if changed:
                                decision={**decision,'unreleased_draft':decision['answer'],'unreleased_raw_output':decision['raw_output'],
                                    'raw_output':None,'core_validation':'UNAVAILABLE','claims':[],'sources':[],
                                    'outcome_assessments':[],'additional_reads':[],
                                    'answer':'Updated authorized source records were retrieved, but the updated interpretation could not be completed. The earlier interpretation is withheld because it used a different evidence set. Inspect the returned records; no current diagnosis or source-absence conclusion is established.'}
                                review={}
                            decision={**decision,'answer':decision.get('answer') or 'Interpretation unavailable; no conclusion was inferred.',
                                'provider_limitation':str(exc)[:400],'failure':failure_receipt(exc,stage='draft_interpretation',remaining=model.hybrid.remaining())}
                            break
                        review=await review_draft(decision)
                        proposals=decision.get('additional_reads',[]) if decision.get('decision')=='need_more_evidence' else []
                        initiated='model' if proposals else 'server_post_draft'
                        if not proposals:proposals=review['server_proposals']
                        queries,rejected=validate_additional({'additional_reads':proposals},state,inventory,service.registry,tools.tools,executed_queries=tools.requests)
                        remaining=state.rounds<profile['max_rounds'] and tools.calls<tools.max_calls and model.hybrid.role_calls<model.hybrid.max_remote_calls and model.hybrid.remaining()>15
                        queries=queries[:max(0,tools.max_calls-tools.calls)] if remaining else []
                        conflicts=review['claim_compatibility']['conflicts']
                        events.append({'draft':{k:v for k,v in decision.items() if k!='input_packet'},'adequacy':review,'initiator':initiated,'validated_queries':queries,'rejected_queries':rejected})
                        review['rejected_queries']=rejected
                        if queries:
                            route.planning['supplementary_queries']=queries
                            decision['supplementary_receipt']={'requested':proposals,'initiator':initiated,'rejected':rejected,'continuation_round':state.rounds}
                            return update(state,'evaluate_evidence',route=route,assessment=assessment,pending_domains=[q['domain'] for q in queries],
                                role_decision=decision,observations=state.results,investigation={**state.investigation,'last_review':review,'drafts':events})
                        if (conflicts or decision.get('decision')=='need_more_evidence' and rejected) and remaining:
                            state.investigation={**state.investigation,'last_review':review}
                            state.role_decision=decision
                            continuation={'reason':'Resolve actual source-bound contradictions or rejected executable queries only. Preserve already-consistent prose; correct auxiliary declarations rather than rewriting correct text. No extra planning.',
                                'conflicts':conflicts,'rejected_queries':rejected}
                            continue
                        break
                    return update(state,'evaluate_evidence',route=route,assessment=assessment,pending_domains=[],role_decision=decision,
                        observations=state.results,investigation={**state.investigation,'last_review':review,'drafts':events,
                            'status':'QUALIFIED_FINAL' if review.get('unread_dependencies') or decision.get('provider_limitation') else 'FINAL_PROPOSED',
                            'adequacy_authority':'Retrieval and declared typed operands only; unrestricted causal prose remains unverified.'})
                try:
                    decision=await decide(model,body.prompt,current,state.evidence,state.context_references.get('user_history',[]),state.route.planning,continuation=continuation,
                        retrieval=retrieval_envelope(state))
                except (HTTPException,ValueError) as exc:
                    from llm.model_roles import failure_receipt
                    decision={**state.role_decision,'answer':state.role_decision.get('answer') or 'Interpretation is unavailable. Authorized source records remain inspectable; no conclusion was inferred.',
                        'decision':'answer','additional_reads':[],'provider_limitation':str(exc)[:400],
                        'failure':failure_receipt(exc,stage='evidence_decision',remaining=model.hybrid.remaining())}
                route=state.route.model_copy(deep=True);more=[]
                if decision.get('decision')=='need_more_evidence' and state.rounds==1 and model.hybrid.remaining()>10:
                    queries,rejected=validate_additional(decision,state,inventory,service.registry,tools.tools,executed_queries=tools.requests)
                    more=[q['domain'] for q in queries];route.planning['supplementary_queries']=queries
                    decision['supplementary_receipt']={'requested':decision.get('additional_reads',[]),'rejected':rejected,'continuation_round':1,
                        'classification':'INVALID_READER_PROPOSAL' if rejected else 'AUTHORIZED_QUERIES'}
                    if not more:
                        try:decision=await decide(model,body.prompt,current,state.evidence,state.context_references.get('user_history',[]),route.planning,continuation=decision['supplementary_receipt'],
                            retrieval=retrieval_envelope(state))
                        except (HTTPException,ValueError) as exc:
                            from llm.model_roles import failure_receipt
                            decision.update(provider_limitation=str(exc)[:400],failure=failure_receipt(exc,stage='final_evidence_decision',remaining=model.hybrid.remaining()))
                return update(state,'evaluate_evidence',route=route,assessment=assessment,pending_domains=more,role_decision=decision,
                    observations=state.results,limitations=assessment.get('gaps',[])+assessment.get('warnings',[])+assessment.get('conflicts',[]))
            more=additional_domains(state,assessment) if state.rounds<3 else []
            route=state.route.model_copy(deep=True)
            if route.planning.get('additional_model_decision',{}).get('status')=='validated':
                more=[]  # Honor the bounded model plan; leave remaining gaps explicit.
            from llm.orchestration.investigation import is_investigation
            if os.getenv('COGNISHIELD_AI_PLANNING','0')=='1' and state.rounds==1 and model.available('retrieval') and is_investigation(state.request) and assessment.get('conclusion_status') not in {'confirmed_within_scenario','healthy_within_tested_scope'}:
                remaining=[d for d,t in DOMAIN_TO_TOOL.items() if t in tools.tools and not any(r['tool']==t for r in state.results)]
                if remaining:
                    from llm.orchestration.planning import additional_reads
                    try:
                        queries,decision=await additional_reads(body.prompt,remaining,assessment,state.results,body.model,model.generate)
                        more=list(queries);route.source_requests.update(queries)
                        route.planning['additional_model_decision']={'status':'validated',**decision}
                    except (ValueError,HTTPException) as exc:
                        route.planning['additional_model_decision']={'status':'invalid_fallback','reason':str(exc)[:500]}
            if len(more)+tools.calls>tools.max_calls:
                assessment['gaps'].append('Additional retrieval exceeded the eight-call budget')
                more=more[:max(0,tools.max_calls-tools.calls)]
            if state.route.use_attachments:
                # Uploaded material remains in the existing gateway document path;
                # its extraction/ownership/citations are not copied into the graph.
                assessment['warnings'].append('Uploaded document interpretation is separate from verified network records')
            return update(state,'evaluate_evidence',route=route,assessment=assessment,pending_domains=more,
                observations=state.results,limitations=assessment['gaps']+assessment['warnings']+assessment['conflicts'])
        # A missing operational source can warrant one inventory lookup to check
        # the subject, never an invented measurement or an unlimited retry loop.
        needs_subject=any(item['status']!='success' for item in state.results) and bool(state.device_refs)
        if needs_subject and state.rounds<2 and not any(item['tool']=='inventory.read' for item in state.results):
            route=state.route.model_copy(update={'network_domains':state.route.network_domains+['inventory']})
            return update(state,'evaluate_evidence',route=route,limitations=['Some requested sources were unavailable; checking recorded device context.'])
        return update(state,'evaluate_evidence',observations=state.results,
            limitations=state.limitations+(['Some requested evidence is unavailable.'] if any(item['status']!='success' for item in state.results) else []))

    def after_evaluate(state):
        if b2:return 'select_authorized_tools' if state.pending_domains and state.rounds<(profile['max_rounds'] if completeness else 3) else 'verify_facts'
        read={item['tool'] for item in state.results}
        return 'select_authorized_tools' if state.rounds<2 and any(DOMAIN_TO_TOOL[d] not in read for d in state.route.network_domains) else 'verify_facts'

    async def verify(state):
        validation=verify_records(state.results,state.evidence,tools.results)
        if b2:
            from llm.orchestration.verification import verify_documents
            validation=verify_documents(validation,state.results,tools.results)
        return update(state,'verify_facts',validation=validation)

    async def compose(state):
        contract=state.route.requested_outcomes
        if getattr(getattr(model,'hybrid',None),'multi_model',False):
            from llm.orchestration.role_reasoning import decide,preview
            from llm.model_roles import semantic_mode
            if state.validation.get('status')=='failed':
                return update(state,'compose_response',answer='The source receipts failed structural integrity validation. No interpretation was released.',
                    validation={**state.validation,'interpretation_status':'withheld_integrity_failure'},
                    memory={**state.memory,'status':'awaiting_response'})
            decision=state.role_decision
            if not state.results:
                try:decision=await decide(model,body.prompt,[],[],state.context_references.get('user_history',[]),state.route.planning,advisory=state.context_references.get('advisory',{}))
                except (HTTPException,ValueError) as exc:
                    from llm.model_roles import failure_receipt
                    decision={'answer':'Interpretation unavailable; no reader was executed.','provider_limitation':str(exc)[:400],
                        'failure':failure_receipt(exc,stage='advisory_composition',remaining=model.hybrid.remaining())}
            if completeness:
                if not state.results and decision.get('raw_output'):
                    from llm.orchestration.investigation_support import post_draft
                    review=post_draft(state,decision,inventory,service.registry,tools.tools,tools.requests)
                    state.investigation={**state.investigation,'last_review':review,'drafts':[{'draft':{k:v for k,v in decision.items() if k!='input_packet'},'adequacy':review,'initiator':'advisory_no_execution','validated_queries':[]}]}
                review=state.investigation.get('last_review') or {}
                from llm.orchestration.investigation_support import release_interpretation
                decision=release_interpretation(decision,review)
                coverage_limits=[r['reader']+': '+r['status'] for r in review.get('source_coverage',[]) if r['status'] not in {'QUERIED_SUCCESSFULLY','QUERIED_ZERO_MATCHES'}]
                coverage_limits.extend(r['reader']+': '+r['status'] for r in state.investigation.get('budget_omissions',[]))
                if coverage_limits:
                    decision=dict(decision);decision['answer']+='\n\n**Source coverage limitations:** '+'; '.join(dict.fromkeys(coverage_limits))+'. These limits do not prove that no event or fault occurred.'
                if review.get('unread_dependencies'):
                    decision=dict(decision);decision['answer']+='\n\n**Unresolved evidence:** '+', '.join(d['reference'] for d in review['unread_dependencies'])+'. These references were not established by the inspected records.'
            answer,synthesis=preview(decision,semantic_mode(),state.results,state.evidence,state.assessment,body.prompt)
            if completeness:synthesis['investigation']=state.investigation
            if decision.get('provider_limitation'):answer+='\n\n**Interpretation limitation:** '+decision['provider_limitation']
            return update(state,'compose_response',answer=answer,role_decision=decision,
                validation={**state.validation,'synthesis':synthesis,'interpretation_status':'unverified'},
                memory={**state.memory,'status':'awaiting_response'})
        if contract and not state.route.network_domains and not state.route.use_editor and not state.route.use_attachments:
            from llm.orchestration.synthesis import synthesize
            if contract.advice_only and getattr(model,'hybrid',None):
                model.hybrid.prepare_advisory(state.context_references.get('advisory',{}))
            answer,synthesis=await synthesize(model,body.model,body.prompt,[],[],{},
                'I could not fulfil the requested outcome within this turn. No evidence was collected and no action was performed.',
                requested_outcomes=contract,advisory_context=state.context_references.get('advisory',{}))
            from llm.orchestration.request_contract import outcome_results
            return update(state,'compose_response',answer=answer,validation={'status':'advisory_only' if contract.advice_only else 'response_proposed','synthesis':synthesis},
                outcome_results=outcome_results(contract,[],[],synthesis),memory={**state.memory,
                    **({'domains':saved_memory.domains,'source_requests':saved_memory.source_requests,
                        'open_questions':saved_memory.open_questions,'evidence_revisions':saved_memory.evidence_revisions}
                        if b2 and state.route.use_history else {}),'status':'awaiting_response'})
        factual=[item for item in state.results if item['tool']!='knowledge.search']
        answer,validation=release_answer('',factual,state.evidence,tools.results,state.route.attributes,state.interface_refs)
        if b2:
            validation=state.validation
            if validation.get('status')=='verified':
                from llm.orchestration.investigation import conclusion_text,knowledge_text,is_investigation
                knowledge=knowledge_text(state.results,state.evidence)
                if knowledge:answer=knowledge+'\n\n'+answer
                if is_investigation(state.request) or is_investigation(state.memory.get('goal','')):
                    explicit_records=re.search(r'\b(show|quote|display|read|check|list|retrieve)\b.{0,140}\b(configuration|config|interfaces|syslogs?|records|logs)\b',state.request,re.I)
                    summary=conclusion_text(state.assessment,state.results,state.evidence)
                    answer=(summary+'\n\n'+answer if explicit_records and not (state.assessment.get('development') and kind=='floating')
                        else (knowledge+'\n\n' if knowledge else '')+summary)
            else:answer='The returned evidence failed verification. No network conclusion was released.'
        if not factual:validation['scope']='Documentation provenance only; model paraphrases are not certified'
        from llm.gateway_references import relational_read,record_only_request
        exact_inventory=(state.route.network_domains==['inventory'] and bool(state.route.attributes or state.interface_refs)
            and not relational_read(body.prompt,state.route.planning.get('proposed',{}).get('desired_response','direct')))
        from llm.gateway_references import configuration_text_request
        exact_configuration=state.route.network_domains==['configuration'] and configuration_text_request(body.prompt)
        if exact_inventory and validation.get('status')=='verified':
            # Scenario assessment may contain unrelated hypotheses even for a
            # direct attribute lookup. Do not let that trigger prose which can
            # discard or contradict the verified record projection.
            validation={**validation,'answer_mode':'verified_inventory_attributes'}
        if exact_configuration and validation.get('status')=='verified':
            from llm.gateway_findings import network_answer
            answer=network_answer(factual,state.evidence,state.route.attributes,state.interface_refs,question=body.prompt)
            validation={**validation,'answer_mode':'verified_configuration_text'}
        published_explanation=(state.route.network_domains==['knowledge'] and any(e.authority=='published_operation_documentation' for e in state.evidence))
        if b2 and (factual or published_explanation) and not exact_inventory and not exact_configuration and validation.get('status')=='verified' and os.getenv('COGNISHIELD_AI_SYNTHESIS','0')=='1' and not record_only_request(body.prompt,state.route.planning.get('proposed',{}).get('desired_response','direct')):
            from llm.orchestration.synthesis import synthesize
            from llm.orchestration.verification import assessment_context
            # The composer builds its own bounded case file. Feed its projector
            # actual scoped reads, so display trimming cannot remove the decisive
            # trace before relevance selection or source-grounded verification.
            synthesis_context=assessment_context(state.results,tools.results)
            if getattr(model,'hybrid',None):
                model.hybrid.prepare_synthesis(state.results,state.evidence,state.route.planning,state.assessment)
            required_readers=required_synthesis_readers(body.prompt,inventory,state.route.network_domains)
            from llm.orchestration.request_contract import response_obligations
            answer,synthesis=await synthesize(model,body.model,body.prompt,synthesis_context,state.evidence,state.assessment,answer,
                investigation=is_investigation(state.request) or state.route.use_history and is_investigation(state.memory.get('goal','')),
                objectives=state.route.planning.get('proposed',{}).get('information_needs',[]),
                reference_requests=state.context_references.get('user_history',[]),required_readers=required_readers,
                user_obligations=response_obligations(body.prompt),requested_outcomes=contract)
            validation={**validation,'synthesis':synthesis}
        values={'answer':answer,'validation':validation}
        if contract:
            from llm.orchestration.request_contract import outcome_results
            values['outcome_results']=outcome_results(contract,state.results,state.evidence,validation.get('synthesis',{}))
        if b2:
            old=saved_memory.evidence_revisions
            revisions={e.source+'|'+','.join(e.device_refs):e.source_revision or '' for e in state.evidence}
            changed=[key for key in revisions if key in old and old[key]!=revisions[key]]
            memory={**state.memory,**retrieval_state(state.results,state.route.attributes,state.interface_refs,state.route.source_requests),
                'evidence_revisions':revisions,'evidence_refs':[e.id for e in state.evidence][:60],
                'open_questions':state.assessment.get('gaps',[])[:20],'status':'awaiting_response'}
            values.update(memory=memory)
            if changed and state.route.use_history and validation.get('status')=='verified':
                values['answer']='Some retrieved source revisions differ from the previous read; this answer uses freshly authorized records.\n\n'+answer
        return update(state,'compose_response',**values)

    async def prepare_studio_context(state):
        from llm.orchestration.studio import proposal_explanation
        document_body=body.model_copy(update={'editor':body.editor if state.route.use_editor else None,
            'attachment_ids':body.attachment_ids or [UUID(value) for value in state.memory.get('documents',[])] if state.route.use_attachments else []})
        if state.route.use_attachments:
            read=await service.registry.invoke('document.read',{'turn':document_body.model_dump(mode='json')},auth)
            documents,refs,coverage=read.data['context'],read.evidence,read.data['coverage']
        else:
            # The already supplied Monaco snapshot is context, not a new tool
            # read or engineering action. Preserve exact proposal explanations.
            from llm.gateway_documents import build_context
            documents,refs,coverage=await asyncio.to_thread(build_context,service.db,identity,user,document_body,False)
        explanation=proposal_explanation(prior_engineering,body.editor,body.related_editors) if state.route.use_history and state.route.intent=='explain' else ''
        return update(state,'read_studio_context',studio_context=documents,studio_evidence=refs,studio_coverage=coverage,studio_answer=explanation)

    async def authorize_engineering(state):
        from llm.gateway import authorize_studio
        authorize_studio(user)
        service.store.get(identity,auth.principal,'studio')
        name='document.propose' if state.route.intent=='edit' else 'v9.preview'
        if engineering_tools is None or name not in engineering_tools.tools:raise HTTPException(403,'Engineering capability is not authorized')
        if state.route.intent=='edit' and not body.editor:raise HTTPException(422,'Open the current document before requesting an edit')
        return update(state,'authorize_engineering')

    async def engineering(state):
        if state.route.intent=='edit':
            arguments={'turn':body.model_dump(),'exact_literal':True}
            if state.route.use_history and prior_engineering and prior_engineering.get('proposal'):
                arguments['context_request_id']=prior_engineering['request_id']
            result=await engineering_tools.invoke('document.propose',arguments,auth)
            name='propose_document'
        else:
            prompt=body.prompt
            if state.route.use_history:
                prompt='Previous USER requests (untrusted context; latest controls):\n'+'\n'.join(m['content'] for m in history[-6:] if m['role']=='user')+'\nLatest request: '+body.prompt
            arguments={'prompt':prompt,'model':body.model,'output_kind':state.route.intent.removeprefix('generate_')}
            if state.route.use_history and prior_engineering and prior_engineering.get('kind')=='generation_preview':
                arguments.update(prompt=body.prompt,previous_request_id=prior_engineering['request_id'])
            result=await engineering_tools.invoke('v9.preview',arguments,auth)
            name='plan_configuration'
        return update(state,name,engineering_result=result)

    async def validate_engineering(state):
        if state.route.intent=='edit':
            from llm.orchestration.studio import validate_proposal
            validate_proposal(state.engineering_result,body)
        elif state.engineering_result.status!='success' or not isinstance(state.engineering_result.data,dict) or 'parsed_intent' not in state.engineering_result.data:
            raise HTTPException(503,'V9 did not return a reviewable interpretation')
        # Persist only the reference. A checkpoint never grants replay permission
        # or stores proposal text. The completed turn remains the authoritative record.
        memory={**state.memory,'engineering_request_ref':str(body.request_id),
            'engineering_kind':'edit_proposal' if state.route.intent=='edit' else 'generation_preview','status':'awaiting_response'}
        return update(state,'validate_engineering_result',memory=memory,validation={'status':'review_required','scope':'Existing proposal/V9 contracts; no buffer change or saving'})

    def after_resolve(state):
        if getattr(getattr(model,'hybrid',None),'multi_model',False) and not state.route.network_domains and state.route.intent in {'answer','explain'}:return 'compose_response'
        if state.route.requested_outcomes and not state.route.network_domains and not state.route.use_editor and not state.route.use_attachments and state.route.intent in {'answer','explain'}:return 'compose_response'
        if b3 and kind=='studio' and (state.route.intent=='edit' or state.route.intent.startswith('generate_')):return 'authorize_engineering'
        if state.route.network_domains and (b2 or not state.route.use_attachments) and (b3 or not state.route.use_editor):return 'select_authorized_tools'
        if b3 and kind=='studio' and state.route.intent!='clarify' and (state.route.use_editor or state.route.use_attachments):return 'read_studio_context'
        return END

    graph=StateGraph(AgentState)
    for name,fn in [('understand_request',understand),('resolve_references',resolve),('select_authorized_tools',select),
        ('execute_tools',execute),('evaluate_evidence',evaluate),('verify_facts',verify),('compose_response',compose)]:graph.add_node(name,fn)
    if b3 and kind=='studio':
        for name,fn in [('authorize_engineering',authorize_engineering),('coordinate_engineering',engineering),('validate_engineering_result',validate_engineering),('read_studio_context',prepare_studio_context)]:graph.add_node(name,fn)
        graph.add_edge('authorize_engineering','coordinate_engineering');graph.add_edge('coordinate_engineering','validate_engineering_result');graph.add_edge('validate_engineering_result',END);graph.add_edge('read_studio_context',END)
    graph.add_edge(START,'understand_request');graph.add_edge('understand_request','resolve_references')
    graph.add_conditional_edges('resolve_references',after_resolve)
    graph.add_edge('select_authorized_tools','execute_tools');graph.add_edge('execute_tools','evaluate_evidence')
    graph.add_conditional_edges('evaluate_evidence',after_evaluate)
    graph.add_edge('verify_facts','compose_response')
    graph.add_conditional_edges('compose_response',lambda s:'read_studio_context' if b3 and kind=='studio' and (s.route.use_editor or s.route.use_attachments) else END)
    # No checkpoint/replay API in B1. Authoritative history remains in SQLite.
    # Graph state and external traces must never contain the authorization object.
    try:
        with tracing_context(enabled=False):
            value=await asyncio.wait_for(graph.compile(checkpointer=saver).ainvoke(AgentState(request=body.prompt,owner=user['username'],
                assistant=kind,conversation=identity,memory=saved_memory.model_dump() if b2 else {},context_references={'history_turns':len(history),'attachments':len(attachments)}),
                config=saver.config() if saver else {'recursion_limit':32 if completeness else 20},**({'durability':'sync'} if saver else {})),timeout=timeout)
    except BaseException as exc:
        if saver:saver.mark('cancelled' if isinstance(exc,asyncio.CancelledError) else 'interrupted')
        raise
    final=AgentState.model_validate(value)
    sizes=sum(len(__import__('json').dumps(item,default=str)) for item in final.results)
    coverage={'complete':not any(isinstance(item.get('data'),dict) and item['data'].get('truncated') for item in final.results),
        'included_characters':sizes,'domains':[item['tool'] for item in final.results],
        'agent':{'engine':'langgraph_b3' if b3 else 'langgraph_b2' if b2 else 'langgraph_b1','nodes':final.trace,'rounds':final.rounds,
        'tool_calls':tools.calls,'routing_model_calls':model.purposes.get('routing',0),'model_calls':model.calls,'model_call_breakdown':model.purposes,'elapsed_ms':round((time.monotonic()-started)*1000,2),
        'tool_call_mode':'validated_plan','investigation':final.investigation,'planning':final.route.planning,'inference_diagnostics':getattr(model,'inference_trace',[]),
        'checkpointing':restore_status,'verification':final.validation,'limitations':final.limitations,
        **({'requested_outcomes':final.route.requested_outcomes.model_dump(),'outcome_results':final.outcome_results}
            if final.route.requested_outcomes else {}),
        **({'assessment':final.assessment,'recovery':'fresh authorized reads; no pending-tool replay','restored_status':saver.restored_status,
        'document_refs':final.memory.get('documents',[]),
        'budgets':{'rounds':3,'tools':8,'model_calls':model.max_calls,'model_stages':model.stage_limits,'input_characters':model.max_input_characters,
        'maximum_output_tokens_per_call':min(8192,max(512,int(os.getenv('COGNISHIELD_AI_HYBRID_OUTPUT_TOKENS','8192')))) if getattr(model,'hybrid',None) else 512,
        **({'local_output_tokens':512,'gemini_output_tokens':min(8192,max(512,int(os.getenv('COGNISHIELD_AI_HYBRID_OUTPUT_TOKENS','8192')))),
            'shared_request_deadline':True} if getattr(model,'hybrid',None) else {}),
        'wall_seconds':timeout,'concurrency':1}} if b2 else {})}}
    from llm.orchestration.investigation import is_investigation
    if final.route.requested_outcomes and final.answer and not final.results:
        coverage['agent']['_outcome_answer']=final.answer
    if getattr(getattr(model,'hybrid',None),'multi_model',False):
        coverage['agent']['experimental_interpretation']=final.role_decision
        if not final.results:coverage['agent']['_outcome_answer']=final.answer
    if final.validation.get('status')=='verified' and (final.assessment.get('development') or is_investigation(final.request) or is_investigation(final.memory.get('goal',''))):
        from llm.gateway_findings import network_answer
        coverage['agent']['record_details']=network_answer(final.results,final.evidence,final.route.attributes,final.interface_refs)
    if b3 and kind=='studio':
        coverage['agent']['engineering_calls']=engineering_tools.calls
        coverage['agent']['_engineering_result']=final.engineering_result
        coverage['agent']['_studio_context']=(final.studio_context,final.studio_evidence,final.studio_coverage) if final.studio_context else None
        coverage['agent']['_studio_answer']=final.studio_answer
    if final.validation.get('status')=='failed':
        return final.route,([],[],coverage,final.answer),coverage['agent']
    return final.route,(final.results,final.evidence,coverage,final.answer) if final.results else None,coverage['agent']
