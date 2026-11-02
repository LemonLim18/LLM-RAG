"""Zero-cloud replay of preserved packets; metadata quality, not reasoning."""
import json,sys,os,statistics
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from llm.orchestration.role_reasoning import evidence_packet
from llm.orchestration.evidence_harness import guidance
from llm.gateway_services import registry_for,inventory_snapshot
from llm.gateway_store import ensure_schema
from db.manager import DatabaseManager
from local_providers.development import ScenarioManager
A=ROOT/'tmp/phase-g/iterations/20261027-evidence-harness'
OLD=ROOT/'tmp/phase-g/iterations/20261026-intelligence-improvement'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
spec=load(ROOT/'docs/evaluations/phase_g_intelligence_improvement_holdout_v1.json');items=[];providers=[]
for path in sorted((OLD/'holdout-v1').glob('MNI-??.json')):
    d=load(path)
    for p in d['model_packets']:
        if p['purpose']=='routing':
            w=d['wires_without_headers'][0] if d['wires_without_headers'] else {}
            providers.append({'id':d['id'],'status':w.get('http_status','TIMEOUT'),'seconds':p['seconds'],
                'model_input_chars':sum(len(m['content']) for m in p['messages']),'schema_chars':len(json.dumps(p['schema'])),
                'provider_error':w.get('response',{}).get('error'),'settings':w.get('body',{}).get('generationConfig')})
        if p['purpose']!='synthesis' or 'raw' not in p:continue
        original=json.loads(p['messages'][1]['content'])
        class Source:
            def __init__(self,value):self.value={k:v for k,v in value.items() if k!='label'}
            def model_dump(self,**kw):return self.value
        evidence=[Source(v) for v in original['sources']]
        case=next(c for c in spec['cases'] if c['id']==d['id'])
        os.environ['COGNISHIELD_DEV_SIMULATION']='1'
        db=DatabaseManager(str(A/(d['id']+'-offline.db')));db.initialize();ensure_schema(db)
        m=ScenarioManager(A/(d['id']+'-offline-scenario.json'));db._development_scenario=m
        if case['scenario'] not in m._read()['scenarios']:
            m.change('import',m.snapshot()[1]['source_revision'],spec['fixtures'][case['scenario']])
        registry=registry_for(db);inventory=inventory_snapshot(db)
        retrieval={k:v for k,v in original['retrieval_boundary'].items() if k not in {'source_restrictions','advisory_only','reader_schemas','rule'}}
        state=SimpleNamespace(request=original['original_user_instruction'],device_refs=original['planning_proposal_not_authority'].get('resolved_device_refs',[]),
            results=original['reader_results'],evidence=evidence,route=SimpleNamespace(planning=original['planning_proposal_not_authority']))
        args=(state.request,state.results,evidence,original['owned_user_context'],state.route.planning)
        with patch.dict(os.environ,{'COGNISHIELD_AI_EVIDENCE_HARNESS':'0'}):control=json.loads(evidence_packet(*args,retrieval=retrieval))
        with patch.dict(os.environ,{'COGNISHIELD_AI_EVIDENCE_HARNESS':'1'}):
            hints=guidance(state,inventory,registry,{'network.state','network.configuration','network.syslog','network.topology','network.telemetry'},retrieval.get('executed_queries',[]))
            enhanced=json.loads(evidence_packet(*args,retrieval={**retrieval,'reader_guidance':hints}))
        assert control==original,'Control packet drifted from preserved input'
        assert enhanced['reader_results']==control['reader_results'] and enhanced['sources']==control['sources']
        row={'id':d['id'],'control_chars':len(json.dumps(control,ensure_ascii=False)),'enhanced_chars':len(json.dumps(enhanced,ensure_ascii=False)),
            'raw_records_equal':True,'source_identities_equal':True,'ledger':enhanced['evidence_requirement_ledger'],
            'hints':enhanced['retrieval_boundary']['reader_guidance'],'guidance_schema_chars':len(json.dumps(enhanced['retrieval_boundary']['guidance_schemas'])),
            'index_chars_before':len(json.dumps(control['record_identity_index'])),'index_chars_after':len(json.dumps(enhanced['record_identity_index']))}
        items.append(row);db.close()
def summary(rows):
    return {'n':len(rows),'input_chars_min':min(r['model_input_chars'] for r in rows),'input_chars_max':max(r['model_input_chars'] for r in rows),
        'seconds_median':statistics.median(r['seconds'] for r in rows),'seconds_max':max(r['seconds'] for r in rows)}
result={'cloud_calls':0,'packets':items,'provider_traces':providers,'provider_groups':{str(s):summary([r for r in providers if r['status']==s]) for s in {r['status'] for r in providers}},
    'findings':'Sequential concurrency1; same planning schema/settings. Similar size ranges contain both successful and503responses; cannot establish input-size or schema causation. Timeout35s is the existing planning reservation, not120s request exhaustion. No retry justified by paired recovery evidence; preserve3call ceiling and final/supplementary budget. Metadata visibility is not improved reasoning.'}
with (A/'offline-final.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps({'offline_packets':len(items),'cloud_calls':0,'sizes':[(r['id'],r['control_chars'],r['enhanced_chars']) for r in items],'provider_groups':result['provider_groups']}))
