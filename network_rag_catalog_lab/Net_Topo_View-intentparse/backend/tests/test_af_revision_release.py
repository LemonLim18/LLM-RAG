"""A failed generation cannot refresh an older draft to a new evidence set."""
import json,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import Evidence,ToolResult
from fastapi import HTTPException
from llm.orchestration.role_reasoning import evidence_packet
from tests.test_model_role_graph import GraphRoles,plan,decision
from uuid import uuid4

def test_evidence_binding_is_order_stable_and_revision_sensitive():
    from llm.orchestration.engine import evidence_fingerprint
    first={'tool':'network.state','status':'success','data':{'records':[{'id':'same-record','value':1}],'source_revision':'one'}}
    reordered={'data':first['data'],'status':'success','tool':'network.state'}
    assert evidence_fingerprint([first],[])==evidence_fingerprint([reordered],[])
    for changed in [
        {**first,'status':'unavailable'},
        {**first,'data':{**first['data'],'source_revision':'two'}},
        {**first,'data':{'records':[{'id':'same-record','value':2}],'source_revision':'one'}},
    ]:
        assert evidence_fingerprint([first],[])!=evidence_fingerprint([changed],[])

class EvidenceRevisionGraph(GraphRoles):
    async def test_new_supplementary_evidence_with_failed_reinterpretation_withholds_stale_absence(self):
        async def config(params,auth):
            rows=[] if params.source_categories==['config_changes'] else [{'id':'running-current','kind':'running_configuration','device_id':2,
                'config_text':'hostname R2','change_event_ref':'review-source-record'}]
            return ToolResult(status='success',data={'records':rows,'source_available':True},
                evidence=[Evidence(id=uuid4().hex,source='synthetic-config',origin='simulated')])
        async def logs(params,auth):
            # Real registered supplemental read, not a fabricated model result.
            return ToolResult(status='success',data={'records':[{'id':'review-source-record','kind':'syslog_event','device_id':2,
                'message':'A recorded label review; no completed physical repair.'}],
                'source_available':True},evidence=[Evidence(id=uuid4().hex,source='synthetic-syslog',origin='simulated')])
        self.g.registry._tools['network.configuration']['fn']=config
        self.g.registry._tools['network.syslog']['fn']=logs
        initial_plan=plan(['configuration']);initial_plan.update(investigation_breadth='targeted',desired_response='explanation')
        old='The authorized records do not contain the purpose of review-source-record. [S1]'
        def admission(*args,**kwargs):
            # Reproduce AF04's exact failure category after real evidence gain;
            # no dependency on display excerpt sizes or fabricated model JSON.
            if any(r['tool']=='network.syslog' for r in args[1]):
                raise HTTPException(413,'Relevant evidence exceeds the role input budget; no mandatory records were silently truncated. Narrow the requested scope.')
            return evidence_packet(*args,**kwargs)
        with patch.dict('os.environ',{'COGNISHIELD_AI_COMPLETENESS':'1'}),patch('llm.orchestration.role_reasoning.evidence_packet',admission):
            r,packets=await self.scoped('floating','Explain R2 current configuration and its source-owned review reference.',
                [initial_plan,decision(old)])
        assert len(packets)==2  # Second packet fails before any provider call.
        assert any('review-source-record' in json.dumps(row) and row['tool']=='network.syslog' for row in r.observations)
        assert old not in r.answer
        assert 'updated' in r.answer.lower() and 'withheld' in r.answer.lower()
        trace=r.context_coverage['agent']['investigation']
        assert trace['revision_failures'][0]['retained_valid_core']
        assert trace['revision_failures'][0]['retained_draft_release']=='WITHHELD_EVIDENCE_CHANGED'
        assert trace['drafts'][0]['draft']['answer']==old
