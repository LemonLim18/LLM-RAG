"""Shared bounded agent graph. Existing readers and engineering services retain authority."""
import asyncio
import re
import time
import os
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


DOMAIN_TO_TOOL={'inventory':'inventory.read','knowledge':'knowledge.search',**{d:'network.'+d for d in ['topology','configuration','syslog','telemetry','incidents','state']}}


async def run(service,identity,user,kind,body,auth,history,attachments,previous,inventory,timeout=120,b2=False,b3=False):
    if kind!='floating' and not (b3 and kind=='studio'):raise HTTPException(403,'This orchestration version does not authorize Studio')
    if (auth.principal!=user['username'] or auth.assistant_kind!=kind or auth.conversation_id!=identity):
        raise HTTPException(403,'Agent authorization is not bound to this owner and conversation')
    model=RoutingModel()
    tools=AuthorizedTools(service.registry,service.store,auth)
    engineering_tools=AuthorizedTools(service.registry,service.store,auth,max_calls=1,
        names=frozenset({'v9.preview','document.propose'}),effects=frozenset({'propose'})) if b3 and kind=='studio' else None
    started=time.monotonic()
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
        route=None
        if b3 and kind=='studio':
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
        if b2 and inventory.get('scenario') and route.planning.get('mode')!='validated_model_plan' and not any(query.get('source_categories') for query in route.source_requests.values()):
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
            elif not route.network_domains and not route.use_attachments:memory={'status':'running'}
        return update(state,'understand_request',route=route,context_references={
            'previous_request':previous.get('request_id') if previous and route.use_history else None,
            'user_history':[m['content'][:2000] for m in history[-6:] if m['role']=='user'] if route.use_history else [],
            'attachment_names':[item['name'] for item in attachments] if route.use_attachments else []},memory=memory)

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
            values.update(memory={**state.memory,'device_refs':selected,'domains':route.network_domains},pending_domains=initial_domains(route,route.network_request or body.prompt))
        return update(state,'resolve_references',**values)

    async def select(state):
        already={item['tool'] for item in state.results}
        domains=[d for d in (state.pending_domains if b2 else state.route.network_domains) if DOMAIN_TO_TOOL[d] not in already]
        plan=[ToolStep(tool=DOMAIN_TO_TOOL[d],domain=d) for d in domains]
        if len(plan)+tools.calls>tools.max_calls:raise HTTPException(429,'Agent tool-call budget exhausted')
        if any(step.tool not in tools.tools for step in plan):raise HTTPException(403,'Tool plan is not authorized')
        return update(state,'select_authorized_tools',plan=plan)

    async def execute(state):
        contexts,evidence,coverage=await network_context(service.db,tools,auth,state.route.network_request or body.prompt,
            domains_override=[step.domain for step in state.plan],device_refs_override=state.device_refs or None,
            source_requests=state.route.source_requests,interface_refs_override=state.interface_refs)
        return update(state,'execute_tools',results=state.results+contexts,evidence=state.evidence+evidence,
            coverage=coverage,rounds=state.rounds+1)

    async def evaluate(state):
        if b2:
            from llm.orchestration.investigation import assess,additional_domains
            from llm.orchestration.verification import assessment_context
            assessment=assess(assessment_context(state.results,tools.results),state.evidence)
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
        if b2:return 'select_authorized_tools' if state.pending_domains and state.rounds<3 else 'verify_facts'
        read={item['tool'] for item in state.results}
        return 'select_authorized_tools' if state.rounds<2 and any(DOMAIN_TO_TOOL[d] not in read for d in state.route.network_domains) else 'verify_facts'

    async def verify(state):
        validation=verify_records(state.results,state.evidence,tools.results)
        if b2:
            from llm.orchestration.verification import verify_documents
            validation=verify_documents(validation,state.results,tools.results)
        return update(state,'verify_facts',validation=validation)

    async def compose(state):
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
        from llm.gateway_references import relational_read
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
        if b2 and (factual or published_explanation) and not exact_inventory and not exact_configuration and validation.get('status')=='verified' and os.getenv('COGNISHIELD_AI_SYNTHESIS','0')=='1' and not re.search(r'\b(show|quote|display)\b.*\b(?:configuration|config|logs|records)\b',body.prompt,re.I):
            from llm.orchestration.synthesis import synthesize
            from llm.orchestration.verification import assessment_context
            # The composer builds its own bounded case file. Feed its projector
            # actual scoped reads, so display trimming cannot remove the decisive
            # trace before relevance selection or source-grounded verification.
            synthesis_context=assessment_context(state.results,tools.results)
            from llm.gateway_network import route_network
            from development.source_registry import explicit_read_sources,BY_KEY,reader_domains
            explicit_domains=set(route_network(body.prompt,inventory,expand_investigation=False)[0])-{'inventory'}
            named_sources=explicit_read_sources(body.prompt,BY_KEY)
            explicit_domains.update(reader_domains(named_sources,state.route.network_domains))
            required_readers={('inventory.read' if domain=='inventory' else 'knowledge.search' if domain=='knowledge' else 'network.'+domain) for domain in explicit_domains}
            answer,synthesis=await synthesize(model,body.model,body.prompt,synthesis_context,state.evidence,state.assessment,answer,
                investigation=is_investigation(state.request) or state.route.use_history and is_investigation(state.memory.get('goal','')),
                objectives=state.route.planning.get('proposed',{}).get('information_needs',[]),
                reference_requests=state.context_references.get('user_history',[]),required_readers=required_readers)
            validation={**validation,'synthesis':synthesis}
        values={'answer':answer,'validation':validation}
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
                config=saver.config() if saver else {'recursion_limit':20},**({'durability':'sync'} if saver else {})),timeout=timeout)
    except BaseException as exc:
        if saver:saver.mark('cancelled' if isinstance(exc,asyncio.CancelledError) else 'interrupted')
        raise
    final=AgentState.model_validate(value)
    sizes=sum(len(__import__('json').dumps(item,default=str)) for item in final.results)
    coverage={'complete':not any(isinstance(item.get('data'),dict) and item['data'].get('truncated') for item in final.results),
        'included_characters':sizes,'domains':[item['tool'] for item in final.results],
        'agent':{'engine':'langgraph_b3' if b3 else 'langgraph_b2' if b2 else 'langgraph_b1','nodes':final.trace,'rounds':final.rounds,
        'tool_calls':tools.calls,'routing_model_calls':model.purposes.get('routing',0),'model_calls':model.calls,'model_call_breakdown':model.purposes,'elapsed_ms':round((time.monotonic()-started)*1000,2),
        'tool_call_mode':'validated_plan','planning':final.route.planning,'inference_diagnostics':getattr(model,'inference_trace',[]),
        'checkpointing':restore_status,'verification':final.validation,'limitations':final.limitations,
        **({'assessment':final.assessment,'recovery':'fresh authorized reads; no pending-tool replay','restored_status':saver.restored_status,
        'document_refs':final.memory.get('documents',[]),
        'budgets':{'rounds':3,'tools':8,'model_calls':model.max_calls,'model_stages':model.stage_limits,'input_characters':model.max_input_characters,'maximum_output_tokens_per_call':512,'wall_seconds':timeout,'concurrency':1}} if b2 else {})}}
    from llm.orchestration.investigation import is_investigation
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
