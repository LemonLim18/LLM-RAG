"""Experimental reference-only reasoning view. No IO, retrieval or planner.

All assertions concern declared scalar operands. Neither a relationship match
nor a populated outcome certifies the meaning/completeness of free-form prose.
"""
import json,os
from copy import deepcopy
from typing import Literal
from pydantic import Field
from fastapi import HTTPException
from llm.gateway_models import StrictModel

VERSION='evidence_reasoning_v1'

def mode():
    value=os.getenv('COGNISHIELD_AI_REASONING_CONTRACT','off')
    if value not in {'off','obligations','relationships'}:
        raise HTTPException(422,'Invalid experimental reasoning-contract mode')
    return value

class RelationshipAssertion(StrictModel):
    relationship_id:str=Field(max_length=80)
    value:str|float|bool|None
    authority:Literal['recorded','modeled','physical']

class GroundedOutcome(StrictModel):
    obligation_id:str=Field(max_length=40)
    conclusion:str=Field(min_length=1,max_length=1600)
    evidence_ids:list[str]=Field(default_factory=list,max_length=16)
    status:Literal['established','possible','unresolved']
    limitations:list[str]=Field(default_factory=list,max_length=6)
    assertions:list[RelationshipAssertion]=Field(default_factory=list,max_length=16)

def record_entries(packet):
    from llm.orchestration.investigation_support import walk,classify
    found=[]
    for i,row in enumerate(packet['reader_results']):
        for path,record in walk(row.get('data'),'/reader_results/'+str(i)+'/data'):
            found.append({'record':record,'path':path,'reader':row['tool'],
                'parents':row.get('evidence_ids',[]),'classes':classify(record,row['tool']),
                'row':i,'available':row.get('status')=='success' and
                    not (isinstance(row.get('data'),dict) and row['data'].get('source_available') is False)})
    return found

def ledger(packet):
    """Original clauses/spans, not a model's rewritten objective or new plan."""
    from llm.orchestration.request_contract import requested_clauses,original_sources
    entries=record_entries(packet);question=packet['original_user_instruction'];out=[];offset=0
    for clause in requested_clauses(question,detailed=True):
        start=question.find(clause['text'],offset)
        if start<0:raise ValueError('Original clause has no source span')
        offset=start+len(clause['text'])
        domains=original_sources(clause['text'],{'devices':[]})
        # Unknown clause-to-reader binding remains broad and explicitly marked.
        # It must not erase a preceding clause's independent evidence operands.
        candidates=[e for e in entries if not domains or e['reader'].removeprefix('network.') in domains or
            e['reader'] in {'inventory.read','knowledge.search'} and ('inventory' if e['reader']=='inventory.read' else 'knowledge') in domains]
        available=[e for e in candidates if e['available']]
        out.append({'obligation_id':clause['id'],'original_span':[start,offset],
            'requested_outcome':clause['text'],'source_requirements':domains,
            'reader_rows':sorted({e['row'] for e in candidates}),
            'scope_refs':['/reader_results/'+str(i)+'/reader_receipt/parameters' for i in sorted({e['row'] for e in candidates})],
            'evidence_ids':list(dict.fromkeys(x for e in candidates for x in e['parents'])),
            'evidence_availability':'records_admitted_not_semantic_sufficiency' if available else 'no_matching_admitted_record',
            'binding':'Explicit reader-family association only; otherwise shared request evidence. No inferred target or semantic completeness.'})
    return out

def relationships(packet):
    """Index exact scalar fields already present. No invented causal edges."""
    facts=[];series={};bindings=[]
    fields={'device_id':'device_identity','interface_id':'interface_identity','vrf':'vrf_membership',
        'admin_status':'interface_admin_state','oper_status':'interface_oper_state',
        'observed_state':'protocol_observation','neighbor_state':'protocol_observation',
        'session_state':'protocol_observation','state':'recorded_state','status':'disposition_or_recorded_status',
        'applied':'application_status','verification_status':'verification_status',
        'timestamp':'source_timestamp','observed_at':'observed_at','captured_at':'captured_at',
        'recorded_at':'recorded_at','saved_at':'saved_at','effective_at':'effective_at',
        'source_device_id':'flow_source','destination_device_id':'flow_destination',
        'interface_role':'interface_role','action':'route_or_policy_action','next_hop':'next_hop',
        'prefix':'recorded_prefix','reason':'recorded_disposition_reason','configuration_state':'configuration_state'}
    for entry in record_entries(packet):
        if not entry['available']:continue
        record=entry['record'];classes=entry['classes']
        authority='modeled' if 'derived_analysis' in classes else 'recorded'
        base={k:record[k] for k in ['device_id','interface_id','vrf','timestamp'] if k in record}
        binding=len(bindings)
        bindings.append({'record_id':str(record['id']),'evidence_ids':entry['parents'],
            'record_path':entry['path'],'authority':authority,'scope':base})
        def add(kind,value,path,scope):
            if type(value) not in {str,int,float,bool,type(None)}:return
            facts.append({'id':'R'+str(len(facts)+1),'relationship':kind,'value':value,
                'record_index':binding,'value_path':path[len(entry['path']):],
                'inherits_record_scope':not bool(scope.get('direction')),
                'scope':{k:v for k,v in scope.items() if k in {'device_id','interface_id','vrf','direction','interface_role','source_device_id','destination_device_id'} and (scope.get('direction') or base.get(k)!=v)}})
        def visit(value,path,scope):
            if isinstance(value,dict):
                scope={**scope,**{k:value[k] for k in ['device_id','interface_id','vrf','timestamp'] if k in value}}
                if isinstance(value.get('scope'),dict):scope={**scope,**value['scope']}
                for key,item in value.items():
                    child=path+'/'+str(key).replace('~','~0').replace('/','~1')
                    local={**scope,**({'direction':key} if key in {'forward','return'} else {}),
                        **({'interface_role':key} if key in {'ingress','egress','destination_ingress'} else {})}
                    if key in {'forward','return'}:
                        # Record ownership is provenance, not necessarily this
                        # direction's source or a failed-hop owner.
                        local={k:v for k,v in local.items() if k not in {'device_id','interface_id'}}
                    if key in fields:add(fields[key],item,child,scope)
                    visit(item,child,local)
            elif isinstance(value,list):
                for i,item in enumerate(value):visit(item,path+'/'+str(i),scope)
        visit(record,entry['path'],base)
        if 'running_configuration' in classes or 'saved_configuration' in classes:
            add('configuration_representation',classes[0],entry['path']+'/kind',base)
            facts[-1].update(value_path=None,value_origin='Existing investigation_support.classify(record, reader)')
        # Sample-pair bounds establish recorded endpoints only, not continuity,
        # activation, exact transition or cause. Conflicts remain in raw records.
        if record.get('timestamp') and record.get('kind') in {'interface_state','running_configuration'}:
            key=tuple(str(record.get(k)) for k in ['kind','device_id','interface_id','vrf'])
            series.setdefault(key,[]).append({'record_path':entry['path'],'timestamp':record['timestamp']})
    return {'source_records':bindings,'facts':facts,'sample_groups':[{'scope_key':list(k),'samples':v,'between_samples':'not_established_by_sample_pair'}
        for k,v in series.items() if len(v)>1],
        'semantics':{'source_timestamp':'Meaning is determined by original record class; never assume timestamp means effective_at.',
            'running_configuration':'Captured content, not uninterrupted state or exact activation time.',
            'saved_configuration':'Artifact content; applied is unknown unless explicitly recorded. Staged alone does not mean definitely unapplied.',
            'modeled':'Existing deterministic result, not physical/live measurement. Directions and VRFs remain independent.',
            'causation':'No causal relationship inferred from timestamp proximity, route presence or co-occurrence.',
            'assertions':'Scalar operand checks only. Correct values do not certify an arbitrary conclusion.',
            'references':'record_index refers to source_records; inherit its scope only when inherits_record_scope=true. Directional scopes do not inherit the originating record owner. value_path is relative to record_path.'}}

def attach(packet,selected):
    result=deepcopy(packet);obligations=ledger(result)
    result['requested_clauses']=[{'id':o['obligation_id'],'text':o['requested_outcome']} for o in obligations]
    result['reasoning_contract']={'version':VERSION,'mode':selected,'obligations':obligations,
        'authority':'Original spans are authoritative; evidence associations are references, not semantic sufficiency or model authority.'}
    if selected=='relationships':
        view=relationships(result);result['reasoning_contract']['relationships']=view
        # Metadata is optional navigation. Raw source operands are never evicted
        # to make an index fit. Explicitly report unadmitted metadata instead.
        if len(json.dumps(result,ensure_ascii=False,default=str,separators=(',',':')))>64000:
            result['reasoning_contract']['relationships']={'facts':[],
                'not_admitted':'Relationship metadata exceeds remaining budget; all admitted raw records retained.',
                'candidate_fact_count':len(view['facts'])}
    return result

def validate(decision,packet):
    """Structural completeness and declared scalar agreement; no prose grader."""
    contract=packet['reasoning_contract'];expected={o['obligation_id']:o for o in contract['obligations']}
    entries=record_entries(packet);sources={s['id'] for s in packet['sources'] if s.get('id')}
    labels={'S'+str(i+1):s.get('id') for i,s in enumerate(packet['sources'])}
    sources.update(labels)
    sources.update(str(e['record']['id']) for e in entries)
    facts={f['id']:f for f in contract.get('relationships',{}).get('facts',[])}
    bindings=contract.get('relationships',{}).get('source_records',[])
    findings=[];seen=set();conflicts=[]
    for item in decision.get('outcomes',[]):
        oid=item['obligation_id']
        if oid in seen or oid not in expected:
            findings.append({'kind':'INVALID_OBLIGATION_ID','obligation_id':oid});continue
        seen.add(oid)
        invalid=set(item['evidence_ids'])-sources
        if invalid:findings.append({'kind':'INVALID_EVIDENCE_REFERENCE','obligation_id':oid,'references':sorted(invalid)})
        if item['status']=='established' and not item['evidence_ids']:
            findings.append({'kind':'UNSUPPORTED_INFERENCE','obligation_id':oid,'reason':'Established declaration has no admitted evidence reference; prose not assessed'})
        for assertion in item.get('assertions',[]):
            fact=facts.get(assertion['relationship_id'])
            if fact is None:
                findings.append({'kind':'INVALID_RELATIONSHIP_REFERENCE','obligation_id':oid,'reference':assertion['relationship_id'],
                    'assertion':deepcopy(assertion),'verification':'UNVERIFIED_OPTIONAL_METADATA',
                    'substantive_verdict':'NOT_MECHANICALLY_CHECKABLE',
                    'reason':'No admitted relationship resolves this hint. No factual credit; independent authoritative typed-claim checks still apply.'});continue
            binding=bindings[fact['record_index']]
            resolved={labels.get(ref,ref) for ref in item['evidence_ids']}
            if not resolved & {binding['record_id'],*binding['evidence_ids']}:
                findings.append({'kind':'INCORRECT_EVIDENCE_BINDING','obligation_id':oid,'reference':fact['id']});continue
            value=assertion['value'];actual=fact['value']
            same=(type(value) is type(actual) and value==actual) or (type(value) in {int,float} and type(actual) in {int,float} and value==actual)
            if not same or assertion['authority']!=binding['authority']:
                finding={'kind':'CONTRADICTED_DETERMINISTIC_FACT','obligation_id':oid,'reference':fact['id'],
                    'declared':assertion,'actual':{**fact,'source':binding},'statement':item['conclusion']}
                findings.append(finding);conflicts.append(finding)
    for oid in sorted(set(expected)-seen):
        findings.append({'kind':'MISSING_OBLIGATION','obligation_id':oid,
            'evidence_availability':expected[oid]['evidence_availability'],'reason':'Model omitted an outcome; not evidence unavailability'})
    return {'version':VERSION,'findings':findings,'conflicts':conflicts,
        'coverage_complete':set(expected)==seen and not any(f['kind']=='INVALID_OBLIGATION_ID' for f in findings),
        'semantic_certified':False,'authority':'Exact references/declared operands and identifier coverage only; causal reasoning and prose completeness unverified.'}

def release(decision):
    """Reuse the existing bounded contradiction policy; never regenerate here."""
    review=decision.get('reasoning_validation')
    if review is None:return decision
    from llm.orchestration.investigation_support import release_interpretation
    conflicts=[{'claim':{'statement':f['statement']},'verdict':'CONTRADICTED'} for f in review['conflicts']]
    invalid_navigation=[f for f in review['findings'] if f['kind']=='INVALID_RELATIONSHIP_REFERENCE']
    errors=[f for f in review['findings'] if f['kind'] in {'INVALID_OBLIGATION_ID','INVALID_EVIDENCE_REFERENCE','INCORRECT_EVIDENCE_BINDING'}]
    if errors:
        return {**decision,'answer':'The interpretation has invalid obligation or source bindings and is withheld. Authorized records remain inspectable; no evidence-unavailable or causal conclusion was inferred.',
            'reasoning_release':{'disposition':'WITHHELD_INVALID_BINDING','model_prose_released':False,'semantic_certified':False}}
    result=release_interpretation(decision,{'claim_compatibility':{'conflicts':conflicts}}) if conflicts else dict(decision)
    if review['findings'] and not conflicts:
        notes=[]
        if not review['coverage_complete']:notes.append('The model omitted requested outcome entries; this is not a missing-source finding.')
        if any(f['kind']=='UNSUPPORTED_INFERENCE' for f in review['findings']):notes.append('Some established declarations lack admitted evidence references; their interpretation is unverified.')
        if invalid_navigation:notes.append('Some optional relationship references were invalid. Their assertions are unverified and provide no factual verification credit; retained model prose remains unverified.')
        result['answer']+='\n\n**Answer limitations:** '+' '.join(notes)+' No semantic completion is certified.'
    result['reasoning_release']={'disposition':result.get('release_decision',{}).get('disposition','PARTIAL' if review['findings'] else 'QUALIFIED'),
        'model_prose_released':result.get('release_decision',{}).get('disposition')!='WITHHELD','semantic_certified':False,
        'optional_metadata_status':'INVALID_UNVERIFIED' if invalid_navigation else 'NO_INVALID_OPTIONAL_REFERENCES'}
    return result
