"""Resolve read references against server-recorded results, never assistant prose.

These guards refine retrieval scope, not engineering intent or permissions. Every
resolved request still passes through the existing authorized service registry.
"""
import re


def requested_program_artifact(prompt):
    """An explicit program output is not authorization for a V9 artifact.

    This constrains the requested artifact type, not network operations or
    their schemas. Existing-buffer requests retain the reviewed editing lane.
    """
    request=re.match(r'\s*(?:please\s+)?(?:(?:can|could|would)\s+you\s+)?(?:write|create|generate|produce|build|draft)\b(.+)',prompt,re.I|re.S)
    if not request:return False
    subject=request[1].split(';',1)[0][:240]
    if re.search(r'\b(?:active|current|open|unsaved|selected|existing|this|that)\s+(?:[\w-]+\s+){0,2}(?:file|buffer|code|script|program|function|document|template)\b|\b(?:editor|Monaco)\b',subject,re.I):return False
    language=re.search(r'\b(?:Python|JavaScript|TypeScript|Java|Rust|Ruby|PowerShell|Bash|SQL|JSON)\b|(?<!\w)C\+\+(?!\w)',subject,re.I)
    artifact=re.search(r'\b(?:function|script|program|class|module|snippet|code|example|query|object)\b',subject,re.I)
    return bool(language and artifact)


def requested_authoring_artifact(prompt):
    """Explicit output-language requests constrain workflow, not V9 operations."""
    request=re.match(r'\s*(?:please\s+)?(?:(?:can|could|would)\s+you\s+)?(?:prepare|draft|write|produce|build|generate|create)\b(.+)',prompt,re.I|re.S)
    if not request:return None
    object_text=request[1][:240]
    if re.match(r'\s*(?:(?:me|a|an|the|new|short)\s+)*(?:summary|explanation|comparison|report|notes?|analysis|guide|overview)\b',object_text,re.I):return None
    if re.search(r'\b(?:active|open|current|selected|unsaved)\s+(?:file|buffer|document|template|code)\b|\b(?:editor|existing file)\b',object_text,re.I):return None
    native=bool(re.search(r'\bnative\b|\bvendor\s+CLI\b',object_text,re.I))
    playbook=bool(re.search(r'\b(?:Ansible|playbook)\b',object_text,re.I))
    if native and playbook:return 'ambiguous'
    return 'native' if native else 'playbook' if playbook else None


def read_intent_text(prompt):
    """Exclude explicit effect/source prohibitions from source selection only.

    The original instruction still controls permissions, proposals and model
    answers. A prohibited configuration write is not a request to read configs.
    Positive clauses after punctuation/contrast remain available to the router.
    """
    return re.sub(r'\b(?:do not|don.t|never)\s+(?:generat\w*|creat\w*|modif\w*|edit\w*|chang\w*|sav\w*|overwrit\w*|deploy\w*|execut\w*|publish\w*|substitut\w*|infer|assume|use|read|consult|include|retrieve)\b'
        r'(?:(?!\b(?:but|instead|rather|then)\b)[^.!?;,\n]){0,300}', '',prompt,flags=re.I)


def read_only_request(prompt):
    """An information speech act cannot authorize an engineering proposal.

    Operation recognition remains V9-owned. This only distinguishes a request
    to explain an edit from a request to perform one, including compound asks.
    """
    text=read_intent_text(prompt)
    read=re.match(r'\s*(?:please\s+)?(?:(?:can|could|would)\s+you\s+)?(?:explain|describe|summari[sz]e|compare|contrast|read|show|tell|what|which|why|how|where|when)\b',text,re.I)
    effect=re.search(r'(?:[;.!]\s*|\b(?:then|and|but)\s+)(?:please\s+)?(?:replace|modify|edit|change|correct|fix|refactor|rename|add|remove|delete|generate|create|build|write|prepare|configure|enable|disable)\b',text,re.I)
    return bool(read and not effect)


def relational_read(prompt,response_kind='direct'):
    """Direct attribute projections cannot fulfill comparisons/explanations."""
    return response_kind in {'explanation','comparison','investigation'} or bool(re.search(
        r'\b(?:compar\w*|contrast\w*|distinguish\w*|explain\w*|interpret\w*|difference|significance|why)\b',prompt,re.I))


def previous_context_reference(previous):
    """Owner-bound intent/source identities, never prior assistant facts."""
    if not previous:return {}
    old=previous.get('context_coverage',{}).get('retrieval',{})
    result={}
    if old.get('domains'):
        try:
            scopes=source_scope_references(old.get('source_requests'))
            if any(domain not in {'inventory','topology','configuration','state','syslog','telemetry','incidents','knowledge'} for domain in old['domains']):raise ValueError('Unknown prior reader')
            result['read']={key:old.get(key,[])[:10] for key in ['domains','device_refs','interface_refs','attributes']}
            result['read']['source_requests']=scopes
        except (ValueError,TypeError):
            pass  # An obsolete/corrupt reference never becomes authority.
    proposal=previous.get('proposal') if previous.get('kind')=='edit_proposal' else None
    if proposal:
        result['engineering']={'kind':'edit_proposal','document_id':proposal.get('document_id'),
            'path':proposal.get('path'),'request_id':previous.get('request_id')}
    elif previous.get('kind')=='generation_preview':
        result['engineering']={'kind':'generation_preview','request_id':previous.get('request_id')}
    return result


def source_scope_references(value):
    """Bounded intent references only; no observations, SQL or permission state."""
    if not value:return {}
    if not isinstance(value,dict) or len(value)>8:raise ValueError('Invalid stored reader scope')
    from llm.gateway_network import NetworkQuery
    from development.source_registry import BY_KEY
    result={}
    for domain,query in value.items():
        if domain not in {'inventory','topology','configuration','state','syslog','telemetry','incidents','knowledge'} or not isinstance(query,dict):raise ValueError('Unknown stored reader scope')
        fields={'source_scope','source_categories','record_kinds','start','end','window_minutes'}
        if set(query)-fields:raise ValueError('Only source/time scope references may be retained')
        parsed=NetworkQuery.model_validate(query)
        tool={'inventory':'inventory.read','knowledge':'knowledge.search'}.get(domain,'network.'+domain)
        if any(not BY_KEY[key].supports(tool) for key in parsed.source_categories):raise ValueError('Stored source category does not match reader')
        # Keep old checkpoints compatible without manufacturing a 60-minute
        # window. Only explicitly supplied time bounds are durable intent.
        result[domain]=parsed.model_dump(mode='json',exclude_none=True,
            include={'source_scope','source_categories'} | (set(query)&fields))
    return result


def configuration_text_request(prompt):
    """A request to see a configuration needs literal text, not a paraphrase."""
    named_section=re.search(r'\b(?:stored|saved|running|current)\b.{0,80}\b(?:section|stanza|block|lines)\b',prompt,re.I)
    if not named_section and not re.search(r'\b(config|configuration|running-config|backup|snapshot)\b',prompt,re.I):return False
    if re.search(r'\b(explain|why|compare|difference|changed|debug|meaning|does|modify|generate|create)\b',prompt,re.I):return False
    return bool(re.search(r'^\s*(?:what (?:is|are)|show|quote|display|read|retrieve|give|print)\b',prompt,re.I))


def configuration_record_request(prompt):
    """Explicit saved/current command settings need configuration records.

    Merely asking for current protocol peers or interface state does not.
    This is a minimum source constraint, not operation recognition.
    """
    return bool(re.search(r'\b(?:stored|saved|running|current|backed.up)\b[^.;?!\n]{0,65}\b(?:settings|commands|configurations?|configs?|stanzas?|sections?)\b',read_intent_text(prompt),re.I))


def attributes(prompt):
    result=[]
    for name,pattern in [('interfaces',r'\b(interfaces?|ports?)\b'),
        ('management_address',r'\b(?:management|mgmt)\s+(?:IPs?|addresses?)\b'),
        ('prefixes',r'\b(subnets?|prefixes|prefix|masks?)\b'),
        ('addresses',r'\b(ip|ips|addresses?|addressing)\b'),('vendor',r'\bvendors?\b'),
        ('model',r'\bmodels?\b'),('os_version',r'\b(versions?|os|firmware)\b|\b(?:software|operating system)\s+release\b'),
        ('role',r'\broles?\b'),('site',r'\b(sites?|locations?)\b'),('status',r'\bstatus\b')]:
        # A peer's protocol role is not the device's inventory role. Keep
        # explicit device-role questions available without letting a protocol
        # comparison become an exact inventory-only lookup.
        wording=re.sub(r'\b(?:peer|neighbou?r|protocol)\s+(?:operational\s+)?roles?\b','',prompt,flags=re.I) if name=='role' else prompt
        if re.search(pattern,wording,re.I):result.append(name)
    return result


def published_knowledge_read(prompt,inventory):
    """An explicit catalog question is a published read, never generation.

    V9 still resolves the operation and supplies its actual contract. This only
    selects the existing source capability, with no prompt-specific operation ID.
    """
    from development.source_registry import explicit_read_sources,BY_KEY,reader_domains
    explicit=explicit_read_sources(prompt,(inventory or {}).get('logical_source_categories',[]))
    scenario_reference='knowledge' in explicit
    wording=read_intent_text(prompt)
    if re.search(r'\b(generate|create|edit|modify|apply|deploy|publish)\b',wording,re.I):return None
    # A method located in the supplied document is a document subject. An
    # explicit comparison with the published catalog still reads both sources.
    if (not re.search(r'\b(?:compar\w*|contrast\w*|against)\b',wording,re.I)
            and re.search(r'\b(?:method|operation|schema|contract)\s+(?:(?:shown|described)\s+)?(?:in|inside|from)\s+(?:(?:the|my|this)\s+)?(?:open|active|unsaved)\s+(?:file|buffer|document)\b',wording,re.I)):
        return None
    catalog_read=bool(re.search(r'\b(published|catalog)\b',prompt,re.I)
        and re.search(r'\b(what|which|explain|describe|compare|list|show|require\w*)\b',prompt,re.I))
    catalog_subject=bool(re.search(r'\b(knowledge|operations?|methods?|schemas?|contracts?|parameters?|fields?|requirements?|inputs?)\b',prompt,re.I))
    if catalog_read and not catalog_subject:
        # A qualified immutable catalog identifier is a source identity even
        # when its requested attribute is not in a keyword list. This does not
        # recognize operations or render: V9's existing reader does that.
        from local_providers.knowledge import knowledge_root
        from llm.gateway_knowledge import read_release
        try:
            _,manifest,_=read_release(knowledge_root()/'storage/catalog_releases')
            catalog_subject=any(re.search(r'(?<![\w-])'+re.escape(binding['operation_id'])+r'(?![\w-])',prompt,re.I)
                for binding in manifest['template_bindings'])
        except (OSError,ValueError,KeyError):
            catalog_subject=False
    if not scenario_reference and not (catalog_read and catalog_subject):return None
    from llm.gateway_network import route_network
    _,query=route_network(prompt,inventory or {'devices':[]})
    domains=['knowledge']
    if query.get('device_refs') and re.search(r'\b(stored|saved|current|running|backups?)\b',prompt,re.I):domains.append('configuration')
    result={'network_domains':domains,'device_refs':query.get('device_refs',[]),'network_request':prompt}
    if scenario_reference:
        # Shared by both ordinary routing and B2/B3 contextual routing. Binding
        # here prevents an early context path from dropping the source filter.
        result['network_domains']=list(dict.fromkeys(domains+reader_domains(explicit,domains)))
        result['source_requests']={domain:{'source_categories':[key for key in explicit if BY_KEY[key].supports('knowledge.search' if domain=='knowledge' else 'network.'+domain)]} for domain in result['network_domains']}
    return result


def resolve_read(prompt, previous, inventory):
    from llm.gateway_network import route_network
    domains,query=route_network(prompt,inventory)
    refs=query.get('device_refs',[])
    attrs=attributes(prompt)
    material=bool(re.search(r'\b(pdf|document|attachments?|uploaded|attached|screenshot|page\s+\d+|open file|active|editor|buffer|template)\b',prompt,re.I))
    write=bool(requested_authoring_artifact(prompt) or re.search(r'\b(generate|create|configure|change|modify|edit|replace|refactor|add|remove|delete|set|enable|disable)\b',prompt,re.I))
    read=bool(re.search(r'\b(what|where|which|show|quote|list|read|retrieve|tell|inspect|give|display|check|fetch|get|find|identify|determine|assess|evaluate|why|explain|describe|details|information|records|are|is|do|does|can|how many|investigate|diagnose|troubleshoot)\b',prompt,re.I))
    dependent=bool(re.search(r'\b(its|their|that|those|these|they|them|first|second|third|last|other|same|previous|sure|certain|verify|again|instead|it)\b|\bwhich are\b',prompt,re.I))
    old=(previous or {}).get('context_coverage',{}).get('retrieval',{})
    old_route=(previous or {}).get('context_coverage',{}).get('routing',{})
    from development.source_registry import explicit_read_sources,BY_KEY,reader_domains
    explicit_sources=explicit_read_sources(prompt,inventory.get('logical_source_categories',[]))
    explicit_network_source=bool(explicit_sources)
    if re.search(r'\b(in general|unrelated question|forget (?:about )?the previous)\b',prompt,re.I):return None
    # Resolve a read-only document follow-up before the generic material guard.
    # Previously "that document" always escaped this resolver and the small
    # classifier asked for an already-known document again.
    editor_reference=bool(re.search(r'\b(editor|buffer|open file|active document|selected code)\b',prompt,re.I))
    if read and dependent and not write and not refs and old_route.get('attachments') and not editor_reference and not explicit_network_source and (material or not old.get('domains')):
        return {'documents':True,'use_history':True}
    if material or write:return None
    excluded=[ref for ref in refs if re.search(r'\b(?:not|instead of)\s+(?:(?:the\s+)?(?:device|router|switch)\s+)?[`\"\']?'+re.escape(str(ref))+r'(?![\w-])',prompt,re.I)]
    correction=bool(excluded or len(refs)==1 and re.search(r'\b(i meant|instead|actually)\b',prompt,re.I))
    if refs and correction:
        corrected=[ref for ref in refs if ref not in excluded]
        if excluded and not corrected:return {'question':'Which recorded device should I read instead?'}
        chosen=domains if domains and domains!=['inventory'] else ['inventory'] if attrs else old.get('domains') or ['inventory']
        return {'domains':chosen,'device_refs':corrected,'interface_refs':[],
            'attributes':attrs or old.get('attributes',[]),'use_history':bool(old.get('domains'))}
    named_ports=[(d,i) for d in inventory['devices'] for i in d['interfaces']
        if re.search(r'(?<![\w/])'+re.escape(i['name'])+r'(?![\w/])',prompt,re.I)
        and (not refs or d['hostname'] in refs)]
    if named_ports:
        if len(named_ports)>1:return {'question':'That interface name appears on multiple devices. Which device do you mean?'}
        d,i=named_ports[0]
        # Resolving an exact interface binds the entity, not the information
        # source. A counter/configuration/state request must not become an
        # inventory lookup merely because it names a recorded port.
        selected=reader_domains([key for key in explicit_sources if BY_KEY[key].tool.startswith('network.')],domains)
        if not selected:
            # Ordinary inventory has no scenario category catalogue. Retain
            # the resolved reader domain instead of substituting inventory
            # merely because the entity is a named interface.
            selected=[domain for domain in domains if domain!='inventory']
            if 'telemetry' in selected and set(attrs)-{'interfaces','status'}:
                selected=['inventory',*selected]
        source_domains=[domain for domain in selected if any(BY_KEY[key].supports('network.'+domain) for key in explicit_sources)]
        return {'domains':selected or ['inventory'],'device_refs':[str(d['id'])],'interface_refs':[str(i['id'])],
            'attributes':attrs or ['interfaces'],'use_history':False,
            **({'source_requests':{domain:{'source_categories':[key for key in explicit_sources
                if BY_KEY[key].supports('network.'+domain)]} for domain in source_domains}} if source_domains else {})}
    if refs and re.search(r'\b(?:GigabitEthernet|FastEthernet|Loopback|Ethernet|Gi|Eth|Lo)\d+[\w/.:-]*',prompt,re.I):
        return {'question':'That interface is not recorded for the selected device. Which stored interface do you mean?'}
    if dependent and not refs and old.get('domains'):
        entities=old.get('entities',[])
        ordinal=re.search(r'\b(first|second|third|last)\b',prompt,re.I)
        selected=None
        if ordinal:
            index={'first':0,'second':1,'third':2,'last':-1}[ordinal[1].lower()]
            if not entities or index>=len(entities):
                return {'question':'That item is not present in the previous result. Which device or interface do you mean?'}
            selected=[entities[index]]
        elif re.search(r'\bother\b',prompt,re.I):
            if 'interface' in prompt.lower() or old.get('interface_refs'):
                remaining=[{'device_id':str(d['id']),'interface_id':str(i['id'])} for d in inventory['devices']
                    if str(d['id']) in old.get('device_refs',[]) for i in d['interfaces'] if str(i['id']) not in old.get('interface_refs',[])]
                if len(remaining)!=1:return {'question':'Which other stored interface do you mean?'}
                selected=remaining
            else:
                remaining=[d for d in inventory['devices'] if str(d['id']) not in old.get('device_refs',[])]
                if len(remaining)!=1:return {'question':'Which other device do you mean?'}
                selected=[{'device_id':str(remaining[0]['id'])}]
        elif re.search(r'\b(those|these|they|them|their)\b',prompt,re.I):
            # Plural references retain the owned list. Asking about "those
            # ports" is not an ambiguous request to select a single interface.
            selected=entities
        elif attrs or re.search(r'\b(it|its)\b',prompt,re.I):
            if len(entities)>1:return {'question':'Which device or interface in the previous result do you mean?'}
            selected=entities
        selected=selected if selected is not None else entities
        refs=list(dict.fromkeys(str(e['device_id']) for e in selected)) or old.get('device_refs',[])
        interfaces=[str(e['interface_id']) for e in selected if e.get('interface_id') is not None]
        ifaces=interfaces or old.get('interface_refs',[])
        # Explicit new attributes/domains replace the old question; a confirmation
        # repeats exactly the last read, with fresh authorization and source data.
        provenance=bool(re.search(r'\b(taken from|come from|came from|guessed|assumed|invented|source of|derived from|based on)\b',prompt,re.I))
        same_source=bool(re.search(r'\bsame\s+(?:(?:authored|recorded|selected|previous)\s+)?(?:sources?|observations?|data)\b',prompt,re.I))
        comparison=bool(re.search(r'\b(?:compar\w*|contrast\w*|reconcil\w*)\b',prompt,re.I))
        chosen=old['domains'] if provenance or same_source else domains if domains and domains!=['inventory'] else ['inventory'] if attrs else old['domains']
        if comparison:
            # A comparison has two operands. Old source references supply its
            # first operand, not cached observations or assistant-written facts.
            chosen=list(dict.fromkeys(old['domains']+chosen))
        selected_attrs=attrs or old.get('attributes',[])
        if provenance:selected_attrs=list(dict.fromkeys(selected_attrs+['provenance']))
        return {'domains':chosen,'device_refs':refs,'interface_refs':ifaces,
                'attributes':selected_attrs,'use_history':True,
                **({'comparison_domains':old['domains']} if comparison else {}),
                'source_requests':{domain:query for domain,query in source_scope_references(old.get('source_requests')).items() if domain in chosen}}
    # Unresolved document follow-ups reuse only document context, never network
    # subjects from older turns. The router decides their semantic explanation.
    if dependent and not refs and old_route.get('attachments') and not explicit_network_source:
        return {'documents':True}
    if dependent and not refs and not old:
        entity_reference=re.search(r'\b(?:its|their|(?:that|this|those|these|previous|same|other)\s+(?:devices?|routers?|switches?|interfaces?|ports?))\b',prompt,re.I)
        if entity_reference or not domains and re.search(r'\b(first|second|third)\b',prompt,re.I):
            return {'question':'Which device, interface or document do you mean?'}
    if refs and old.get('domains') and re.search(r'\bwhat about\b',prompt,re.I) and not attrs and domains==['inventory']:
        return {'domains':old['domains'],'device_refs':refs,'interface_refs':[], 'attributes':old.get('attributes',[]),'use_history':True}
    # A named saved/current capture is an information request even without a
    # leading verb ("R2's stored configuration, please"). It cannot become new CLI.
    if refs and 'configuration' in domains and re.search(r'\b(stored|saved|running|history|captures?|snapshots?|backups?)\b',prompt,re.I):
        return {'domains':domains,'device_refs':refs,'interface_refs':[], 'attributes':attrs,'use_history':False}
    if (read or attrs) and not material and refs:
        if attrs:domains=list(dict.fromkeys(['inventory']+[d for d in domains if d!='inventory']))
        if not domains:domains=['inventory']
        return {'domains':domains,'device_refs':refs,'interface_refs':[], 'attributes':attrs,'use_history':False}
    # An attribute noun alone ("why can an interface lose carrier?") does not
    # identify this user's inventory. Leave unscoped concepts to conversation.
    if read and domains and not refs and re.search(r'\b(stored|recorded|saved|our|my|inventory|planned|live)\b',prompt,re.I):
        return {'domains':domains,'device_refs':[],'interface_refs':[],'attributes':attrs,'use_history':False}
    return None


def retrieval_state(context, attrs, interface_refs, source_requests=None):
    scopes=dict(source_requests or {})
    for item in context:
        if item.get('source_request') is not None:
            domain=item['tool'].removeprefix('network.').replace('inventory.read','inventory').replace('knowledge.search','knowledge')
            scopes[domain]=item['source_request']
    inventory=next((item.get('data') or {} for item in context if item['tool']=='inventory.read'),{})
    entities=[]
    for device in inventory.get('devices',[]):
        if 'interfaces' in attrs or interface_refs:
            entities.extend({'device_id':str(device['id']),'interface_id':str(i['id'])} for i in device['interfaces']
                            if not interface_refs or str(i['id']) in interface_refs)
        else:entities.append({'device_id':str(device['id'])})
    if not entities:
        entities=[{'device_id':str(n['id'])} for item in context if item['tool']=='network.topology' for n in (item.get('data') or {}).get('nodes',[]) if isinstance(n,dict)]
    refs=list(dict.fromkeys(str(ref) for item in context for ref in item.get('device_refs',[])))
    return {'domains':[item['tool'].removeprefix('network.').replace('inventory.read','inventory').replace('knowledge.search','knowledge') for item in context],
        'device_refs':refs,'interface_refs':interface_refs,'attributes':attrs,'entities':entities,
        **({'source_requests':source_scope_references(scopes)} if scopes else {})}
