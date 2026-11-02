"""Original requested fields survive independently of lexical state variants."""
import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.synthesis import interface_observations,synthesize
from llm.gateway_models import Evidence

def test_returned_typed_state_identity_is_not_reported_missing_for_plural_request():
    question='Using recorded state only, show Opal GigabitEthernet0/0/3 administrative and operational states, exact source-record IDs, source attribution and observation time. Do not read any other source or infer physical connectivity.'
    row={'kind':'interface_state','id':'independent:port-7','hostname':'Opal','interface':'GigabitEthernet0/0/3',
         'device_id':853,'interface_id':8532,'source':'recorded-observer','admin_status':'up','oper_status':'up','timestamp':'2026-11-01T10:00:00Z','current':True}
    context=[{'tool':'network.state','status':'success','source_request':{'source_scope':'observed','record_kinds':[]},
        'evidence_ids':['actual-receipt'],'data':{'records':[row],'scenario':{'origin':'simulated'}}}]
    evidence=[Evidence(id='actual-receipt',source='state',origin='simulated')]
    assert interface_observations(context,question,evidence)[0]['record_id']==row['id']
    class Model:
        async def generate(self,messages,**kwargs):
            assert row['id'] in messages[-1]['content']
            return json.dumps({'answer':'Opal GigabitEthernet0/0/3 administrative state up; operational state up; recorded2026-11-01T10:00:00Z. [S1]',
                               'sources':['S1'],'hypotheses':[]}),'test-local'
    answer,trace=asyncio.run(synthesize(Model(),'test-local',question,context,evidence,{},'fallback'))
    assert row['id'] in answer and 'recorded-observer' in answer
    assert 'unavailable' not in answer and trace['display_source_record_ids_added']

def test_unrelated_typed_records_never_become_interface_id_evidence():
    context=[{'tool':'network.state','status':'success','data':{'records':[{'id':'route-only','kind':'routing_table','routes':[]}]}}]
    assert interface_observations(context,'Show exact source-record IDs.',[])==[]
