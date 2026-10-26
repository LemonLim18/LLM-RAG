"""Preserve explicit user clauses independently of model-written read hints.

This is an internal response contract, not an intent router or semantic grader.
Unsplit requests remain intact. Engineering effects still use existing services.
"""
from copy import deepcopy
import re
from typing import Literal
from pydantic import Field
from llm.gateway_models import StrictModel


def response_obligations(prompt,include_actions=False):
    # Split only explicit coordinated information speech acts. In particular,
    # "BGP and OSPF" and "forward and return" are not independent commands.
    verbs='explain|compare|identify|show|quote|list|describe|assess|check|verify|distinguish|report|answer|clarify'
    if include_actions:verbs+='|read|retrieve|recommend|suggest'
    action = r'(?:'+verbs+r')\b'
    separator=r'(?:\s*;\s*|\s+and\s+(?:then\s+)?|\s*,?\s+then\s+)'
    if include_actions:separator=r'(?:'+separator+r'|\.\s+)'
    parts = re.split(separator+r'(?=(?:please\s+)?'+action+r')', prompt, flags=re.I)
    if not 1 < len(parts) <= 8:
        return []
    return [{'id':'request-'+str(i+1),'text':part.strip()} for i,part in enumerate(parts)]


OutcomeAction = Literal['retrieve','explain','compare','diagnose','recommend_checks']


class OutcomeProposal(StrictModel):
    clause: str
    action: OutcomeAction
    need_indexes: list[int] = Field(default_factory=list,max_length=8)


class RequestedOutcome(StrictModel):
    id: str
    instruction: str
    action: OutcomeAction = 'explain'
    readers: list[str] = Field(default_factory=list,max_length=8)
    interpretation: Literal['request_bound','proposed','uninterpreted'] = 'uninterpreted'
    required_readers: list[str] = Field(default_factory=list,max_length=8)


class RequestedContract(StrictModel):
    # Immutable request text is the authority. The action is an interpretation,
    # not a permission, a rewritten instruction, or a semantic completion proof.
    original_request: str
    outcomes: list[RequestedOutcome] = Field(min_length=1,max_length=8)
    source_requests: dict = Field(default_factory=dict)

    @property
    def advice_only(self):
        return (any(o.action=='recommend_checks' for o in self.outcomes)
            and all(not o.readers and o.action in {'recommend_checks','explain'} for o in self.outcomes))

    def execution_queries(self,proposed):
        """A source proposal can supplement, never replace an original operand."""
        from copy import deepcopy
        queries=deepcopy(proposed)
        if self.advice_only:return {}
        for domain,scope in self.source_requests.items():
            query=queries.setdefault(domain,{})
            query.update({k:v for k,v in scope.items() if k!='source_scope' or v!='auto'})
            query.setdefault('source_scope',scope.get('source_scope','auto'))
            # A broad original read cannot be narrowed to a different record
            # kind/category by a later model source-selection proposal.
            if 'source_categories' not in scope:query.pop('source_categories',None)
            if 'record_kinds' not in scope:query.pop('record_kinds',None)
        return queries


def outcome_pilot_enabled():
    import os
    return os.getenv('COGNISHIELD_AI_OUTCOMES','0')=='1'


def requested_clauses(prompt):
    return response_obligations(prompt,include_actions=True) or [{'id':'request-1','text':prompt}]


def reader_for(domain):
    return {'inventory':'inventory.read','knowledge':'knowledge.search'}.get(domain,'network.'+domain)


def request_action(instruction):
    """Bind explicit speech acts, not network operations or diagnoses.

    This is a grammatical constraint on model proposals, shared by arbitrary
    subjects. Quoted/past recommendations and negative instructions are not
    requests to recommend. Implicit intent remains a model proposal.
    """
    from llm.gateway_references import read_intent_text
    text=read_intent_text(instruction).strip()
    # A discourse preface supplies context, not the main speech act. Resolve
    # the imperative after it while preserving the untouched original request.
    preface=re.match(r'^(?:given|based on|considering|regarding|with|in light of)\b[^;.!?\n]*,\s*(.+)$',text,re.I|re.S)
    if preface:text=preface[1]
    prefix=r'^\s*(?:please\s+)?(?:(?:can|could|would)\s+you\s+)?'
    if re.search(prefix+r'(?:recommend|suggest|advise)\b',text,re.I):return 'recommend_checks'
    # A modal question asks which prospective evidence to request, rather than
    # asking to execute the named reader. Do not match 'What did ... request?'.
    if re.search(r'^\s*(?:which|what)\b[^.!?]{0,180}\b(?:should|could|would)\b[^.!?]{0,80}\b(?:request|inspect|check|read|collect|retrieve)\b',text,re.I):return 'recommend_checks'
    for action,verbs in [('retrieve','read|retrieve|show|quote|list|display|fetch'),('compare','compare|contrast'),('explain','explain|describe|summarize|summarise|state')]:
        if re.search(prefix+r'(?:'+verbs+r')\b',text,re.I):return action
    return None


def original_sources(instruction,inventory):
    """Reuse existing source identity/scope parsers on one original clause."""
    from llm.gateway_network import route_network,explicit_configuration_scope,explicit_topology_scope
    from development.source_registry import BY_KEY,explicit_read_sources,reader_domains
    from llm.gateway_references import read_intent_text
    text=read_intent_text(instruction)
    if not text or request_action(text)=='recommend_checks':return {}
    if re.search(r'\b(?:attached|uploaded|editor|buffer|open file|pdf)\b',text,re.I):return {}
    domains,query=route_network(text,inventory or {'devices':[]},expand_investigation=False)
    keys=explicit_read_sources(text,BY_KEY)
    domains=[d for d in domains if d!='inventory']
    domains=list(dict.fromkeys(domains+reader_domains(keys,domains)))
    config_scope=explicit_configuration_scope(text)
    # A qualified device capture/text comparison can lack the word 'config'.
    # Infer this alias only when no other explicit reader owns that text.
    if not domains and query.get('device_refs') and config_scope!='auto' and re.search(r'\b(?:text|commands?|captures?)\b',text,re.I):domains=['configuration']
    scopes={}
    for domain in domains:
        scope=explicit_configuration_scope(text) if domain=='configuration' else explicit_topology_scope(text) if domain=='topology' else 'auto'
        scopes[domain]={'source_scope':scope}
        categories=[key for key in keys if BY_KEY[key].supports(reader_for(domain))]
        if categories:scopes[domain]['source_categories']=categories
    return scopes


def requested_contract(prompt,proposals=(),needs=(),source_requests=None,inventory=None):
    clauses=requested_clauses(prompt)
    proposed=[p if isinstance(p,OutcomeProposal) else OutcomeProposal.model_validate(p) for p in proposals]
    ids=[p.clause for p in proposed]
    # A partial/malformed interpretation cannot erase an original user clause.
    valid=len(ids)==len(set(ids)) and set(ids)=={c['id'] for c in clauses}
    # Resolve whole-request entity/relationship dependencies before splitting:
    # a later clause may name a direction without repeating its devices. Future
    # checks are deliberately excluded from this executable minimum.
    required_scopes=({} if any(request_action(c['text'])=='recommend_checks' for c in clauses)
        else original_sources(prompt,inventory))
    outcomes=[]
    for clause in clauses:
        choice=next((p for p in proposed if p.clause==clause['id']),None) if valid else None
        indexes=choice.need_indexes if choice else list(range(len(needs)))
        if any(type(i) is not int or i<0 or i>=len(needs) for i in indexes):
            raise ValueError('Outcome refers to an absent information need')
        # Missing associations remain broad and visible, never silently empty.
        if choice and choice.action!='recommend_checks' and not indexes:indexes=list(range(len(needs)))
        action=request_action(clause['text'])
        scopes=original_sources(clause['text'],inventory)
        required=list(map(reader_for,scopes))
        for domain,scope in scopes.items():
            old=required_scopes.get(domain)
            if old and old.get('source_scope')!=scope['source_scope']:scope={**scope,'source_scope':'both'}
            if old and old.get('source_categories') and scope.get('source_categories'):
                scope={**scope,'source_categories':list(dict.fromkeys(old['source_categories']+scope['source_categories']))}
            elif old:scope={k:v for k,v in scope.items() if k!='source_categories'}
            required_scopes[domain]=scope
        selected_action=action or (choice.action if choice else 'explain')
        readers=[] if selected_action=='recommend_checks' else required or list(dict.fromkeys(
            [reader_for(needs[i]['domain']) for i in indexes]+list(map(reader_for,required_scopes))))
        interpreted='request_bound' if action else 'proposed' if choice else 'uninterpreted'
        if selected_action=='retrieve' and not readers:interpreted='uninterpreted'
        outcomes.append(RequestedOutcome(id=clause['id'],instruction=clause['text'],
            action=selected_action,readers=readers,required_readers=required,interpretation=interpreted))
    # An explanation of a coordinated request can depend on preceding reads.
    # It cannot acquire a different reader just because a model guessed one.
    if any(o.action=='recommend_checks' for o in outcomes) and not required_scopes:
        for outcome in outcomes:
            if outcome.action=='explain':outcome.readers=[]
    contract=RequestedContract(original_request=prompt,outcomes=outcomes,source_requests=required_scopes)
    if source_requests:
        # Source scopes supplied by the caller are proposals too. Keep the
        # original requirements while retaining compatible query metadata.
        resolved=contract.execution_queries(source_requests)
        contract.source_requests={domain:resolved[domain] for domain in required_scopes}
    return contract


def outcome_evidence(contract,context,evidence):
    """Associate only actual reader receipts; absence is not network failure."""
    labels={e.id:'S'+str(i+1) for i,e in enumerate(evidence)}
    rows=[]
    for outcome in contract.outcomes:
        matched=[r for r in context if r['tool'] in outcome.readers]
        rows.append({'id':outcome.id,'instruction':outcome.instruction,'action':outcome.action,
            'readers':[{'tool':r['tool'],'status':r['status'],
                'sources':[labels[x] for x in r.get('evidence_ids',[]) if x in labels]} for r in matched],
            'required_readers':outcome.required_readers,
            'missing_readers':[r for r in outcome.readers if r not in {m['tool'] for m in matched}],
            'coverage':'reader receipts only; semantic evidence sufficiency requires review'})
    return rows


def outcome_results(contract,context,evidence,synthesis):
    receipts=outcome_evidence(contract,context,evidence)
    responses={p['id']:p for a in synthesis.get('attempts',[]) for p in (a.get('response_contract') or {}).get('responses',[])}
    accepted=synthesis.get('status') in {'literal_checks_passed','repaired_literal_checks_passed','advisory_proposed','outcome_reconstructed','outcome_source_fallback'}
    projected={p['id'] for p in synthesis.get('outcome_projection',[])}
    for row in receipts:
        part=responses.get(row['id']) if accepted else None
        failed=bool(row['missing_readers'] or any(r['status']!='success' for r in row['readers']))
        row.update(disposition=('limited' if failed else 'response_proposed') if part else
            'response_proposed' if accepted and len(receipts)==1 else 'limited' if failed else 'unfulfilled',
            answer_origin='model' if accepted else 'verified_fallback',
            semantic_completion='NOT_CERTIFIED',fallback=not accepted)
        if row['id'] in projected:
            row.update(answer_origin='verified_reader_projection',fallback=True,
                disposition='limited' if failed else 'records_delivered')
        if row['id'] in synthesis.get('outcome_fallback_rendered',[]) and row['action']=='retrieve' and not failed:
            row['disposition']='records_delivered'
    return receipts


def outcome_support_errors(contract,response_contract,context,evidence):
    """Check operand identity/citation coverage, never arbitrary prose truth."""
    if not response_contract:return []
    byid={part['id']:part for part in response_contract['responses']}
    receipts=outcome_evidence(contract,context,evidence);errors=[]
    for row in receipts:
        part=byid.get(row['id'])
        if part is None:errors.append('No response for original outcome '+row['id']);continue
        cited=set(part.get('sources',[]))|set(re.findall(r'\[(S\d+)\]',part['answer']))
        for reader in row['required_readers']:
            matched=[r for r in row['readers'] if r['tool']==reader]
            if not matched:errors.append('Missing required reader '+reader+' for '+row['id'])
            offered={label for r in matched for label in r['sources']}
            if offered and not cited.intersection(offered):errors.append('Outcome '+row['id']+' lacks its own '+reader+' source support')
    return errors


def project_read_outcomes(contract,parts,context,evidence):
    """Render read receipts per outcome; model prose cannot change availability.

    Interpretation stays model-written. This is the existing authoritative
    reader renderer, not a semantic grader, inferred diagnosis or new parser.
    """
    from llm.gateway_findings import network_answer
    from llm.orchestration.investigation import knowledge_text
    labels={e.id:'S'+str(i+1) for i,e in enumerate(evidence)}
    byid={o.id:o for o in contract.outcomes};result=[];replaced=[]
    for part in parts:
        outcome=byid[part['id']]
        selected=[r for r in context if r['tool'] in outcome.readers]
        failed=bool(selected and all(r['status']!='success' for r in selected))
        if selected and (outcome.action=='retrieve' or failed):
            factual=[r for r in selected if r['tool']!='knowledge.search']
            chunks=[network_answer(factual,evidence,question=outcome.instruction)] if factual else []
            docs=knowledge_text(selected,evidence)
            if docs:chunks.insert(0,docs)
            if failed:chunks.append('These readers returned no observations for this request. This is a retrieval limitation; it does not establish the absence, success, failure or current state of the underlying activity.')
            missing=set(outcome.required_readers)-{r['tool'] for r in selected}
            if missing:chunks.append('Required sources without a read receipt: '+', '.join(sorted(missing))+'.')
            citations=list(dict.fromkeys(labels[i] for r in selected for i in r.get('evidence_ids',[]) if i in labels))
            result.append({**part,'answer':'\n\n'.join(chunks),'sources':citations})
            replaced.append({'id':outcome.id,'origin':'verified_reader_projection','reason':'source_unavailable' if failed else 'requested_read'})
        else:result.append(part)
    return result,replaced


class ClauseResponse(StrictModel):
    id: str
    answer: str = Field(min_length=1,max_length=2400)
    sources: list[str] = Field(default_factory=list,max_length=8)


class CompoundResponse(StrictModel):
    responses: list[ClauseResponse] = Field(min_length=2,max_length=8)
    hypotheses: list[str] = Field(default_factory=list,max_length=3)
    operation_ids: list[str] = Field(default_factory=list,max_length=3)


def compound_schema(answer_schema,obligations):
    schema=CompoundResponse.model_json_schema()
    part=schema['$defs']['ClauseResponse']['properties']
    part['id']['enum']=[item['id'] for item in obligations]
    part['answer']=deepcopy(answer_schema['properties']['answer'])
    part['sources']=deepcopy(answer_schema['properties']['sources'])
    part['sources'].pop('minItems',None)  # A general-knowledge clause need not cite a local record.
    schema['$defs']['ClauseResponse']['required']=['id','answer','sources']
    schema['properties']['responses'].update(minItems=len(obligations),maxItems=len(obligations))
    schema['properties']['hypotheses']=deepcopy(answer_schema['properties']['hypotheses'])
    if 'operation_ids' in answer_schema['properties']:
        schema['properties']['operation_ids']=deepcopy(answer_schema['properties']['operation_ids'])
        schema['required'].append('operation_ids')
    else:
        schema['properties'].pop('operation_ids',None)
    return schema


def assemble_response(raw,obligations,draft_model):
    parsed=CompoundResponse.model_validate_json(raw)
    ids=[part.id for part in parsed.responses]
    expected=[item['id'] for item in obligations]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected):
        raise ValueError('Each original user clause needs exactly one response; missing, duplicate and invented clauses are invalid')
    ordered=[next(part for part in parsed.responses if part.id==key) for key in expected]
    if any(not part.answer.strip() for part in ordered):
        raise ValueError('A blank response cannot fulfill a user clause')
    for part in ordered:
        # A later factual paragraph cannot complete an unfinished earlier
        # clause. Literal code and introductions followed by data remain valid.
        # This checks structure, not semantic correctness or completeness.
        if re.search(r'\b(?:as follows|the following(?:\s+[\w-]+){0,3})\s*:\s*$',part.answer,re.I):
            raise ValueError('A response clause is an unfinished introduction without its promised content')
    if parsed.operation_ids and 'operation_ids' not in draft_model.model_fields:
        raise ValueError('Operation selection was not offered for this response')
    values={'answer':'\n\n'.join(part.answer for part in ordered),
        'sources':list(dict.fromkeys(source for part in ordered for source in part.sources)),
        'hypotheses':parsed.hypotheses}
    if 'operation_ids' in draft_model.model_fields:
        values['operation_ids']=parsed.operation_ids
    return draft_model(**values),{'obligations':obligations,'responses':[part.model_dump() for part in ordered],
        'coverage':'Structural user-clause coverage only; correctness and semantic completeness require separate verification'}
