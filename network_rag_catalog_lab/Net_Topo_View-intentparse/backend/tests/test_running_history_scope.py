from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.investigation_support import artifact_comparisons

def artifact(id,hour,kind='running_configuration',device=1,vrf='blue'):
 return {'id':id,'kind':kind,'device_id':device,'vrf':vrf,
  'timestamp':f'2026-10-29T{hour:02d}:00:00Z','config_text':f'interface Ethernet1\n description {id}\n no shutdown\n'}

def compare(records):
 return artifact_comparisons([{'tool':'network.configuration','data':{'records':records}}],{'devices':[]})['comparisons']

def test_staged_file_does_not_erase_consecutive_running_comparison():
 pairs=compare([artifact('before',10),artifact('staged',11,'configuration_snapshot'),artifact('after',12),artifact('current',14)])
 running={(p['before']['id'],p['after']['id']) for p in pairs if p['comparison_kind']=='RUNNING_HISTORY'}
 assert running=={('before','after'),('after','current')}
 cross=[p for p in pairs if p['comparison_kind']=='CROSS_ARTIFACT']
 assert cross and all(p['temporal_support']=='ARTIFACT_DIFFERENCE_ONLY' for p in cross)
 assert all('staged' not in pair for pair in running)
 assert any('description before' in str(p['changes']) and 'description after' in str(p['changes']) for p in pairs)
 assert all(not p['related_recorded_event_ids'] for p in pairs),'No applied event may be manufactured'

def test_different_owner_or_vrf_never_forms_running_history():
 assert compare([artifact('a',10,device=1),artifact('b',11,device=2),artifact('c',12,vrf='red')])==[]

def test_one_running_capture_plus_saved_file_is_only_artifact_difference():
 pairs=compare([artifact('saved',10,'configuration_snapshot'),artifact('now',12)])
 assert len(pairs)==1 and pairs[0]['comparison_kind']=='CROSS_ARTIFACT'
 assert pairs[0]['temporal_support']=='ARTIFACT_DIFFERENCE_ONLY'

def test_equal_capture_instants_do_not_establish_ordered_transition():
 pairs=compare([artifact('a',10),artifact('b',10)])
 assert len(pairs)==1 and pairs[0]['temporal_support']=='UNORDERED_RUNNING_CAPTURES'
