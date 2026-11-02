"""Canonical layout is lossless, optional, and not a second evidence authority."""
import copy,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.evidence_harness import canonical_packet
from llm.model_roles import evidence_layout,consent_manifest
from llm.orchestration.investigation_support import walk
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair'
def packet(case):
    frozen=json.loads((AUDIT/'frozen-v1'/case/'frozen-packet.json').read_text(encoding='utf-8'))
    return json.loads(frozen['messages'][1]['content'])
def resolve(tree,pointer):
    value=tree
    for part in pointer.lstrip('/').split('/'):
        part=part.replace('~1','/').replace('~0','~')
        value=value[int(part)] if isinstance(value,list) else value[part]
    return value

@pytest.mark.parametrize('case',['AGR-'+str(n).zfill(2) for n in range(1,9)])
def test_every_authorized_payload_and_identity_is_unchanged(case):
    old=packet(case);before=copy.deepcopy(old);new=canonical_packet(old)
    assert old==before
    for key in ['original_user_instruction','requested_clauses','owned_user_context','advisory_context','sources','evidence_type_boundaries','scope']:
        assert new[key]==old[key]
    assert len(new['source_records'])==len(old['reader_results'])
    for a,b in zip(old['reader_results'],new['source_records']):
        assert a['data']==b['payload']
        assert {k:v for k,v in a.items() if k!='data'}=={k:v for k,v in b.items() if k!='payload'}
    for item in new['record_index']:
        assert resolve(new,item['record_path'])['id']==item['id']
    for relation in new['relationship_view']['record_relationships']:
        for field in relation['fields']:resolve(new,relation['record_path']+'/'+field)
    for comparison in new['temporal_view']['artifact_comparisons'].get('comparisons',[]):
        assert resolve(new,comparison['before']['path'])['id']==comparison['before']['id']
        assert resolve(new,comparison['after']['path'])['id']==comparison['after']['id']
    assert new['claim_source_compatibility']==old.get('investigation_context',{}).get('claim_source_compatibility',{})
    assert new['source_types']==old.get('source_evidence_types',{})

def test_staged_event_and_running_timelines_never_conflate():
    p=canonical_packet(packet('AGR-03'));t=p['temporal_view']
    assert {x['record_id'] for x in t['staged_artifacts']}=={'basalt-unapplied-0305'}
    running={x['record_id'] for x in t['running_observations']}
    assert {'basalt-run-0210','basalt-run-0440','basalt-run-0530'}<=running
    assert 'basalt-unapplied-0305' not in running
    assert next(x for x in t['recorded_events'] if x['record_id']=='basalt-applied-0510')['timestamp']=='2026-10-31T05:10:00Z'
    assert {x['timestamp'] for x in t['operational_observations'] if x.get('interface_id')==2842}=={'2026-10-31T04:55:00Z','2026-10-31T06:50:00Z'}
    assert 'transition_time' not in t

def test_distinct_same_id_observations_not_merged_and_source_strings_not_rewritten():
    p=packet('AGR-08')
    a,b=p['reader_results'][0]['data']['records']
    b['id']=a['id']
    a['note']='/reader_results/0/data is literal source text'
    new=canonical_packet(p)
    r=new['source_records'][0]['payload']['records']
    assert len(r)==2 and r[0]['oper_status']!=r[1]['oper_status']
    assert r[0]['note']==a['note']
    assert len([x for x in new['record_index'] if x['id']==a['id']])==2

def test_no_reader_schema_pruning_can_remove_published_operation_schema():
    old=packet('AGR-06');new=canonical_packet(old)
    assert 'reader_schemas' not in new['retrieval_boundary']
    knowledge=next(r for r in new['source_records'] if r['tool']=='knowledge.search')
    schema=knowledge['payload'][0]['published_requirements']['operations'][0]['schema']
    assert schema==old['reader_results'][0]['data'][0]['published_requirements']['operations'][0]['schema']

def test_enabled_supplementary_tools_retain_actual_registered_schemas():
    old=packet('AGR-02');old['retrieval_boundary']['supplementary_permitted']=True
    frozen=json.loads((AUDIT/'frozen-v1/AGR-02/frozen-packet.json').read_text(encoding='utf-8'))
    # The one-shot frozen packet originally had no further query schemas.
    # Supply its actual registered contracts, never invented schema metadata.
    old['retrieval_boundary']['reader_schemas']=frozen['inputs']['planning']['authorized_reader_schemas']
    new=canonical_packet(old);boundary=new['retrieval_boundary']
    assert boundary['reader_schemas']==old['retrieval_boundary']['reader_schemas']
    assert new['original_source_constraints']==old['retrieval_boundary']['source_restrictions']

def test_default_and_consent_binding(monkeypatch):
    monkeypatch.delenv('COGNISHIELD_AI_EVIDENCE_LAYOUT',raising=False)
    assert evidence_layout()=='current'
    a=consent_manifest()
    monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_LAYOUT','canonical_v1')
    assert consent_manifest()!=a
    monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_LAYOUT','unknown')
    with pytest.raises(Exception):consent_manifest()

