"""Offline updated-verification replay of immutable18Gemini completions.

Only saved sources/answers are read. All provider, model and reader execution is
blocked. Baseline is reproduced from task-start source preimages, never rerun.
"""
import copy,hashlib,importlib.util,json,os,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
FROZEN=ROOT/'tmp/phase-g/iterations/20261102-evidence-reasoning-contract'
OUT=FROZEN/'release-checker-offline-repair'
sys.path.insert(0,str(ROOT/'backend'))

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def old_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
 sys.modules[name]=m;spec.loader.exec_module(m);return m

def main():
 from llm.orchestration.role_reasoning import parse_decision,preview
 from llm.orchestration.reasoning_contract import validate
 from llm.orchestration.investigation_support import compatible_claims,release_interpretation
 from llm.gateway_models import Evidence
 from llm.model_roles import validate_result
 from llm.orchestration.model import RoutingModel
 from llm.tools import ToolRegistry
 import httpx
 baseline=old_module('release_scope_baseline',OUT/'source-before/backend/llm/orchestration/investigation_support.py')
 old_contract=old_module('relationship_release_baseline',OUT/'source-before/backend/llm/orchestration/reasoning_contract.py')
 original_grade=load(FROZEN/'live-full-answer-review.json');spec=load(ROOT/'docs/evaluations/phase_g_evidence_reasoning_contract_v3.json')
 assert original_grade['registry_sha256']==sha(ROOT/'docs/evaluations/phase_g_evidence_reasoning_contract_v3.json')
 counters={'cloud_dispatches':0,'model_calls':0,'reader_calls':0}
 def prohibited(kind):
  def fail(*a,**kw):counters[kind]+=1;raise AssertionError('Offline replay forbids '+kind)
  return fail
 cases=[];head='**Unverified AI interpretation — synthetic development mode**\n\n'
 with patch.object(httpx.AsyncClient,'send',prohibited('cloud_dispatches')),patch.object(RoutingModel,'generate',prohibited('model_calls')),patch.object(ToolRegistry,'invoke',prohibited('reader_calls')):
  for grade in original_grade['cells']:
   identity=grade['case']+'-'+grade['arm'];sourcefile=FROZEN/'live-results'/(identity+'.json')
   assert sha(sourcefile)==grade['trace_sha256']
   saved=load(sourcefile);raw=saved['raw'];raw_answer=json.loads(raw)['answer']
   packet=json.loads(saved['model_messages'][-1]['content']);inputs=packet['reader_results'];snapshot=copy.deepcopy(packet)
   frozenfile=FROZEN/'frozen-v3'/grade['case']/'packet.json'
   fixture=load(frozenfile);state=load(ROOT/fixture['scenario_path']);scenario=state['scenarios'][state['selected']]
   inventory={'devices':[{**d,'interfaces':[p for p in scenario['interfaces'] if p['device_id']==d['id']]} for d in scenario['devices']]}
   # Original strict provider schema, not the future no-index interface.
   validate_result(raw,saved['model_schema'])
   parsed,aux=parse_decision(raw,independent_claims=True,grounded=grade['arm']!='off')
   assert parsed.answer==raw_answer
   before=copy.deepcopy(saved['decision']);before_review={'claim_compatibility':baseline.compatible_claims(before,inputs,inventory)}
   assert before_review==saved['typed_review'],'Original checker baseline no longer reproduced'
   old=baseline.release_interpretation(before,before_review)
   old=old_contract.release(old)
   assert head+old['answer']==saved['final_answer'],'Original released answer not reproduced'
   decision=copy.deepcopy(saved['decision'])
   # Preserve original auxiliary/core declarations, but recompute only current
   # release metadata against the unchanged admitted source view.
   if grade['arm']!='off':decision['reasoning_validation']=validate(decision,packet)
   review={'claim_compatibility':compatible_claims(decision,inputs,inventory)}
   updated=release_interpretation(decision,review)
   final,trace=preview(updated,'off',inputs,[Evidence.model_validate(e) for e in fixture['inputs']['evidence']],{},saved['model_messages'][-1]['content'])
   assert packet==snapshot and saved['raw']==raw
   preserved=raw_answer in final
   adequate=grade['raw_answer_field']=='ADEQUATE' and preserved
   repaired_grade='ADEQUATE' if adequate else grade['raw_answer_field']+'_RELEASED' if preserved else 'WITHHELD'
   # Filled statuses and disappearing flags cannot promote an incorrect raw
   # answer. Verify every recovered answer still contains all original prose.
   recovered=grade['final_released_answer']=='WITHHELD' and adequate
   newly_exposed=grade['final_released_answer']=='WITHHELD' and preserved and not adequate
   optional=[f for f in decision.get('reasoning_validation',{}).get('findings',[]) if f['kind']=='INVALID_RELATIONSHIP_REFERENCE']
   row={'case':grade['case'],'arm':grade['arm'],'surface':saved['surface'],
    'raw_answer_adequacy_frozen':grade['raw_answer_field'],'original_released_adequacy_frozen':grade['final_released_answer'],
    'original_reason_frozen':grade['reason'],'original_release_trace':saved['release_trace'],
    'original_final_answer':saved['final_answer'],'original_typed_review':saved['typed_review'],
    'repaired_release_trace':trace,'repaired_typed_review':review,'repaired_final_answer':final,
    'repaired_release_adequacy':repaired_grade,'raw_prose_preserved':preserved,
    'correct_answer_recovered':recovered,'newly_released_inadequate_prose':newly_exposed,
    'newly_suppressed_adequate_answer':grade['raw_answer_field']=='ADEQUATE' and not preserved and grade['final_released_answer']=='ADEQUATE',
    'invalid_optional_references':optional,'source_packet_sha256':hashlib.sha256(saved['model_messages'][-1]['content'].encode()).hexdigest(),
    'original_trace_sha256':sha(sourcefile),'raw_output_sha256':hashlib.sha256(raw.encode()).hexdigest(),
    'raw_output_unchanged':True,'evidence_unchanged':True,'source_question_oracle_unchanged':True,
    'generation':'Offline replay under updated verification, not a new model evaluation',
    'semantic_certified':False}
   save(OUT/'replay-cells'/(identity+'.json'),row);cases.append(row)
 assert all(x==0 for x in counters.values())
 scores={a:{'conditions':6,'raw_frozen':sum(c['raw_answer_adequacy_frozen']=='ADEQUATE' for c in cases if c['arm']==a),
  'original_released_frozen':sum(c['original_released_adequacy_frozen']=='ADEQUATE' for c in cases if c['arm']==a),
  'updated_verification_released_adequate':sum(c['repaired_release_adequacy']=='ADEQUATE' for c in cases if c['arm']==a)} for a in ['off','obligations','relationships']}
 report={'method':'Offline replay under updated verification; original raw prose/oracles/grades immutable. Source-derived independently checkable but implementation-assistant graded, not blinded.',
  'scores':scores,'cells':[{k:v for k,v in c.items() if k not in ['original_release_trace','repaired_release_trace','original_final_answer','repaired_final_answer','original_typed_review','repaired_typed_review']} for c in cases],
  'correct_answers_recovered':[c['case']+'-'+c['arm'] for c in cases if c['correct_answer_recovered']],
  'newly_released_inadequate_prose':[c['case']+'-'+c['arm'] for c in cases if c['newly_released_inadequate_prose']],
  'correct_answers_newly_suppressed':[c['case']+'-'+c['arm'] for c in cases if c['newly_suppressed_adequate_answer']],
  'guards':counters,'historical_raw_scores_unchanged':True,'no_model_quality_improvement_claim':True,
  'reasoning_contract_default':'off','promote':False,'formal_stage_closed':False}
 save(OUT/'replay-review.json',report)
 print(json.dumps({'scores':scores,'recovered':report['correct_answers_recovered'],'newly_exposed_inadequate':report['newly_released_inadequate_prose'],'newly_suppressed_correct':report['correct_answers_newly_suppressed'],'guards':counters},indent=2))

if __name__=='__main__':main()
