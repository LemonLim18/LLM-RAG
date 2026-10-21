"""Actual shared graph/registry/SQLite Studio flows; model injections explicit."""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock,patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests import test_b1_agent as baseline
from llm.gateway import AIGateway
from llm.gateway_models import TurnRequest,ToolResult,Evidence
from llm.gateway_routing import SemanticRoute
from fastapi import HTTPException

BUFFER='hostname B3LAB\n! UNSAVED_B3\nrouter ospf 10\n router-id 192.0.2.1\n network 10.1.0.0 0.0.0.255 area 0\nrouter bgp 65000\n neighbor 192.0.2.2 remote-as 65001\n! PRESERVE_B3\n'


class B3Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        baseline.B1Tests.setUp(self)
        # These are baseline B3 workflow tests. Local .env feature choices must
        # not silently change their mocked inference/round-count expectations.
        self.b3=patch.dict(os.environ,{'COGNISHIELD_AI_ENGINE':'langgraph_b3','COGNISHIELD_AI_PLANNING':'0','COGNISHIELD_AI_SYNTHESIS':'0'})
        self.b3.start();self.addCleanup(self.b3.stop)
        self.cid=self.g.store.create('alice','studio')['id']
        self.editor=dict(document_id='b3doc',path='playbooks/b3.cfg',content=BUFFER,language='plaintext',
            model_id='monaco-b3',model_version=7,buffer_epoch=2,saved_revision=0,is_dirty=True,read_only=False)
    ask=baseline.B1Tests.ask

    async def test_as_question_focuses_model_on_actual_bgp_commands_not_unrelated_sections(self):
        answer='Local AS: 65000. Neighbor 192.0.2.2 remote AS: 65001. The local AS identifies this router’s AS; remote AS identifies the peer’s expected AS.'
        with patch('local_providers.chat.generate',AsyncMock(return_value=(answer,'test'))) as model:
            result=await self.ask('Use the active draft to explain its local and remote AS settings.',editor=self.editor)
        self.assertEqual(result.answer,answer)
        messages=model.await_args.args[0]
        payload='\n'.join(m['content'] for m in messages)
        self.assertIn('router bgp 65000',payload)
        self.assertIn('neighbor 192.0.2.2 remote-as 65001',payload)
        self.assertNotIn('router ospf 10',payload)
        self.assertNotIn('UNSAVED_B3',payload)
        self.assertEqual(result.context_coverage['editor_focus']['kind'],'bgp_as_commands')
        self.assertFalse(result.context_coverage['editor_verification']['literal_claims_reconstructed'])
        self.assertEqual(result.evidence[0].source,self.editor['path'])

    async def test_compound_as_and_ospf_request_keeps_both_actual_sections(self):
        with patch('local_providers.chat.generate',AsyncMock(return_value=('Local AS: 65000; OSPF router ID: 192.0.2.1.','test'))) as model:
            await self.ask('Explain local and remote AS settings and compare the OSPF section.',editor=self.editor)
        payload='\n'.join(m['content'] for m in model.await_args.args[0])
        self.assertIn('router ospf 10',payload)
        self.assertIn('router bgp 65000',payload)

    async def propose(self,address='192.0.2.44',prompt='Change the BGP neighbor address in the open file to 192.0.2.44'):
        patch_text=json.dumps({'replacements':[{'old_text':'neighbor 192.0.2.2 remote-as 65001','new_text':'neighbor '+address+' remote-as 65001'}]})
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='edit',use_editor=True,use_history=True))),patch('local_providers.chat.generate',AsyncMock(return_value=(patch_text,'test'))):
            return await self.ask(prompt,editor=self.editor)

    async def test_actual_buffer_context_explanation_no_proposal(self):
        with patch('local_providers.chat.generate',AsyncMock(return_value=('UNSAVED_B3: OSPF 10 and BGP 65000.','test'))) as model:
            result=await self.ask('Explain the active unsaved configuration and quote its marker. Do not modify it.',editor=self.editor)
        self.assertEqual(result.status,'success',result.answer);self.assertIn('UNSAVED_B3',result.answer)
        self.assertIn('read_studio_context',result.context_coverage['agent']['nodes'])
        self.assertEqual(result.context_coverage['agent']['engineering_calls'],0)
        self.assertIn('router bgp 65000',str(model.call_args.args));self.assertIsNone(result.proposal)

    async def test_leave_buffer_untouched_overrides_model_edit_decision_before_engineering(self):
        wrong=SemanticRoute(intent='edit',use_editor=True,use_history=True)
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=wrong)),\
             patch('local_providers.chat.generate',AsyncMock(return_value=('The buffer contains OSPF process 10 and BGP local AS 65000.','test'))):
            result=await self.ask('Walk through the routing stanzas in my unsaved editor; leave it untouched.',editor=self.editor)
        self.assertEqual(result.status,'success')
        self.assertIsNone(result.proposal)
        self.assertIsNone(result.preview)
        self.assertEqual(result.context_coverage['agent']['engineering_calls'],0)
        self.assertNotIn('authorize_engineering',result.context_coverage['agent']['nodes'])
        self.assertEqual(result.context_coverage['routing']['intent'],'explain')
        self.assertEqual(result.context_coverage['agent']['planning']['explicit_effect_constraint']['proposed_intent'],'edit')

    async def test_highlight_reference_requires_an_actual_selection(self):
        model=AsyncMock()
        with patch('local_providers.chat.generate',model):
            result=await self.ask('What does the highlighted block in the active buffer accomplish?',editor=self.editor)
        self.assertEqual(result.kind,'clarification')
        self.assertEqual(result.status,'clarification_required')
        self.assertFalse(result.evidence)
        self.assertIsNone(result.proposal)
        self.assertFalse(result.context_coverage['files']['selection_available'])
        model.assert_not_awaited()

    async def test_selected_editor_edits_require_the_actual_selection_before_proposing(self):
        for prompt in ['Correct only the indentation in my selected editor code.',
                       'Explain the selected Python block. Do not modify it.',
                       'Rename the variable in the selected Python block, keeping the rest untouched.']:
            with patch('local_providers.chat.generate',AsyncMock(return_value=('{"replacements":[]}','test'))) as model:
                result=await self.ask(prompt,editor=self.editor)
            self.assertEqual(result.kind,'clarification')
            self.assertIsNone(result.proposal);self.assertIsNone(result.preview)
            self.assertIn('select',result.answer.lower())
            self.assertFalse(result.context_coverage['files']['selection_available'])
            self.assertEqual(result.context_coverage['agent']['engineering_calls'],0)
            model.assert_not_awaited()

    async def test_rename_with_a_real_selection_still_requires_the_new_name(self):
        editor={**self.editor,'content':'def total(values):\n    result = sum(values)\n    return result\n',
            'selection':{'text':'    result = sum(values)','start_line':2,'end_line':2},'path':'playbooks/test.py','language':'python'}
        with patch('local_providers.chat.generate',AsyncMock()) as model:
            result=await self.ask('Rename the variable in the selected Python block, keeping the rest untouched.',editor=editor)
        self.assertEqual(result.kind,'clarification');self.assertIn('new name',result.answer)
        self.assertIsNone(result.proposal)
        self.assertTrue(result.context_coverage['files']['rename_target_required'])
        self.assertTrue(result.context_coverage['files']['selection_available'])
        model.assert_not_awaited()

    async def test_unspecified_issue_does_not_invent_a_router_id_fix(self):
        with patch('local_providers.chat.generate',AsyncMock()) as model:
            result=await self.ask('Fix the BGP issue in this unsaved file; ask if you need my intended value.',editor=self.editor)
        self.assertEqual(result.kind,'clarification')
        self.assertTrue(result.context_coverage['files']['intended_correction_required'])
        self.assertIsNone(result.proposal);self.assertIsNone(result.preview)
        self.assertIn('value',result.answer)
        model.assert_not_awaited()
        from llm.gateway_documents import editor_issue_question
        from types import SimpleNamespace
        self.assertIsNone(editor_issue_question('Fix the BGP issue by setting the neighbor address to 192.0.2.7; ask if needed.',SimpleNamespace()))

    async def test_propose_changing_without_accept_or_save_is_a_real_review_proposal(self):
        with patch('local_providers.chat.generate',AsyncMock()) as model:
            proposed=await self.ask('Propose changing the active BGP neighbor address to 192.0.2.71; do not accept or save.',editor=self.editor)
        self.assertEqual(proposed.kind,'edit_proposal')
        self.assertEqual(proposed.proposal['suggested'],BUFFER.replace('192.0.2.2 remote-as','192.0.2.71 remote-as'))
        model.assert_not_awaited()
        with patch('local_providers.chat.generate',AsyncMock()) as explanation_model:
            explained=await self.ask('Explain the edit you just proposed, without applying another change.',editor=self.editor)
        self.assertIsNone(explained.proposal);self.assertIsNone(explained.preview)
        self.assertIn('192.0.2.71',explained.answer)
        self.assertIn('current buffer still matches the original',explained.answer)
        explanation_model.assert_not_awaited()

    async def test_ambient_open_file_does_not_turn_arithmetic_into_an_editor_read(self):
        with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}),\
             patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value={'intent':'answer','domains':[],'score':0.9,'margin':0.2})),\
             patch('local_providers.chat.generate',AsyncMock(return_value=('Seven squared is 49.','test'))) as model:
            result=await self.ask('With a code file open, tell me what seven squared is.',editor=self.editor)
        self.assertEqual(result.answer,'Seven squared is 49.')
        self.assertFalse(result.context_coverage['routing']['editor'])
        self.assertFalse(result.evidence)
        self.assertNotIn('UNSAVED_B3',str(model.call_args.args))
        with patch('local_providers.chat.generate',AsyncMock(return_value=('This buffer includes UNSAVED_B3 and OSPF process 10.','test'))) as model:
            explained=await self.ask('With a code file open, explain the actual current buffer.',editor=self.editor)
        self.assertTrue(explained.context_coverage['routing']['editor'])
        self.assertIn('UNSAVED_B3',str(model.call_args.args))

    async def test_comment_insertion_uses_unique_heading_and_rejects_unmarked_or_misplaced_prose(self):
        bad=json.dumps({'comment':'BGP router ID is 192.0.2.99.'})
        good=json.dumps({'comment':'BGP neighbor with remote AS 65001'})
        with patch('local_providers.chat.generate',AsyncMock(side_effect=[(bad,'test'),(good,'test')])) as model:
            result=await self.ask('Add a short explanation comment above BGP in the active file.',editor=self.editor)
        self.assertEqual(result.kind,'edit_proposal')
        self.assertEqual(result.proposal['original'],BUFFER)
        self.assertEqual(result.proposal['suggested'],BUFFER.replace('router bgp 65000','! BGP neighbor with remote AS 65001\nrouter bgp 65000'))
        self.assertEqual(result.proposal['validation']['model_patch_attempts'],2)
        self.assertEqual(model.call_args_list[0].kwargs['max_output_tokens'],256)
        self.assertEqual(result.proposal['validation']['proposal_method'],'model_authored_comment_exact_insert')
        first_context=str(model.call_args_list[0].args)
        self.assertNotIn('UNSAVED_B3',first_context)
        self.assertIn('neighbor 192.0.2.2 remote-as 65001',first_context)

    async def test_marker_explanation_cannot_infer_storage_state_from_a_comment(self):
        wrong='The marker comment indicates that the configuration is not saved to the configuration database.'
        with patch('local_providers.chat.generate',AsyncMock(return_value=(wrong,'test'))):
            result=await self.ask('Explain the marker comment found in this open document.',editor=self.editor)
        self.assertEqual(result.status,'success')
        self.assertIsNone(result.proposal);self.assertIsNone(result.preview)
        self.assertIn('does not establish',result.answer)
        self.assertIn('UNSAVED_B3',result.answer)
        self.assertNotIn('router bgp',result.answer)
        self.assertEqual(result.context_coverage['editor_verification']['original_answer'],wrong)
        self.assertFalse(result.context_coverage['editor_verification']['model_synthesis'])

    async def test_comparison_of_current_buffer_overrides_unrelated_general_concept_hint(self):
        with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}),\
             patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value={'intent':'answer','domains':[],'score':0.8,'margin':0.09})),\
             patch('local_providers.chat.generate',AsyncMock(return_value=('OSPF process 10 has router ID 192.0.2.1; BGP local AS 65000 has neighbor 192.0.2.2, remote AS 65001.','test'))) as model:
            result=await self.ask('Compare BGP and OSPF sections in the actual current buffer.',editor=self.editor)
        self.assertTrue(result.context_coverage['routing']['editor'])
        self.assertIn('read_studio_context',result.context_coverage['agent']['nodes'])
        self.assertIn('router bgp 65000',str(model.call_args.args))
        self.assertIsNone(result.proposal);self.assertIsNone(result.preview)

    async def test_comparison_cannot_claim_a_missing_bgp_router_id_command_is_present(self):
        from llm.orchestration.studio import verify_editor_router_ids
        docs=[{'source':self.editor['path'],'text':BUFFER,'start_line':1}]
        wrong='The OSPF section specifies the OSPF router-id, while the BGP section specifies the BGP router-id and neighbor configuration.'
        answer,changed=verify_editor_router_ids(wrong,docs,self.editor['path'],question='Compare the actual current buffer sections.')
        self.assertTrue(changed)
        self.assertIn('No explicit router ID appears in this shown BGP section',answer)
        correct='OSPF explicitly configures router ID 192.0.2.1; the BGP section has a neighbor and local AS, but no explicit BGP router-id command.'
        self.assertEqual(verify_editor_router_ids(correct,docs,self.editor['path']),(correct,False))

    async def test_explanation_cannot_move_ospf_router_id_into_bgp(self):
        wrong='BGP configuration:\n- Router ID: 192.0.2.1\nOSPF configuration:\n- Router ID: 192.0.2.1'
        with patch('local_providers.chat.generate',AsyncMock(return_value=(wrong,'test'))):
            result=await self.ask('Explain the active unsaved configuration. Do not modify it.',editor=self.editor)
        self.assertIn('No explicit router ID appears in this shown BGP section',result.answer)
        self.assertIn('router-id 192.0.2.1',result.answer)
        self.assertIn('neighbor 192.0.2.2 remote-as 65001',result.answer)
        self.assertTrue(result.context_coverage['editor_verification']['router_id_scope_reconstructed'])
        self.assertEqual(result.context_coverage['editor_verification']['original_answer'],wrong)
        self.assertFalse(result.context_coverage['editor_verification']['model_synthesis'])
        self.assertIsNone(result.proposal)

    async def test_correct_router_id_scope_and_general_explanation_preserved(self):
        from llm.orchestration.studio import verify_editor_router_ids
        docs=[{'source':self.editor['path'],'text':BUFFER,'start_line':1}]
        correct='OSPF configuration:\n- Router ID: 192.0.2.1\nBGP configuration:\n- Neighbor: 192.0.2.2'
        self.assertEqual(verify_editor_router_ids(correct,docs,self.editor['path']),(correct,False))
        # An explicitly configured BGP ID is valid evidence in its own stanza.
        docs[0]['text']=BUFFER.replace('router bgp 65000','router bgp 65000\n bgp router-id 192.0.2.5')
        answer='BGP router ID: 192.0.2.5'
        self.assertEqual(verify_editor_router_ids(answer,docs,self.editor['path']),(answer,False))

    async def test_explanation_rejects_as_as_router_id_and_wrong_ospf_prefix(self):
        from llm.orchestration.studio import verify_editor_router_ids
        docs=[{'source':self.editor['path'],'text':BUFFER,'start_line':1}]
        for answer in ['BGP router ID: 65000','It configures the BGP router-id to 65000.','OSPF network: 10.1.0.0/16','The unsaved configuration is not currently active on the device.']:
            corrected,replaced=verify_editor_router_ids(answer,docs,self.editor['path'])
            self.assertTrue(replaced,answer)
            self.assertIn('network 10.1.0.0 0.0.0.255 area 0',corrected)
            self.assertIn('current device state is not established',corrected)
        answer='OSPF uses 10.1.0.0/24 with router ID 192.0.2.1.'
        self.assertEqual(verify_editor_router_ids(answer,docs,self.editor['path']),(answer,False))

    async def test_proposal_followup_explanation_correction_and_no_save(self):
        result=await self.propose();self.assertEqual(result.kind,'edit_proposal',result.answer)
        proposed=result.proposal
        self.assertEqual(proposed['original'],BUFFER)
        self.assertIn('192.0.2.44',proposed['suggested']);self.assertIn('router ospf 10\n router-id 192.0.2.1',proposed['suggested'])
        self.assertEqual(result.context_coverage['agent']['engineering_calls'],1)
        self.assertIn('validate_engineering_result',result.context_coverage['agent']['nodes'])
        with patch.object(self.g.registry,'invoke',AsyncMock(side_effect=AssertionError('explanation must not invoke tools'))),patch('local_providers.chat.generate',AsyncMock(side_effect=AssertionError('exact diff needs no model'))):
            explanation=await self.ask('Explain your modification',editor=self.editor)
        self.assertIn('remain a proposal',explanation.answer);self.assertIn('192.0.2.44',explanation.answer);self.assertIsNone(explanation.proposal)
        self.g=AIGateway(self.db)
        patch_text=json.dumps({'replacements':[{'old_text':'neighbor 192.0.2.2 remote-as 65001','new_text':'neighbor 192.0.2.55 remote-as 65001'}]})
        with patch('local_providers.chat.generate',AsyncMock(return_value=(patch_text,'test'))) as model:
            correction=await self.ask('Change that address instead to 192.0.2.55; keep the original OSPF section.',editor=self.editor)
        self.assertEqual(correction.kind,'edit_proposal',correction.answer)
        self.assertIn('192.0.2.55',correction.proposal['suggested']);self.assertEqual(correction.proposal['original'],BUFFER)
        model.assert_not_awaited()
        self.assertEqual(correction.proposal['validation']['proposal_method'],'exact_user_literal')
        with self.db._connect() as c:
            self.assertFalse(c.execute("SELECT 1 FROM authoring_revisions WHERE path='playbooks/b3.cfg'").fetchone())
            checkpoints=''.join(r[0] for r in c.execute('SELECT body FROM ai_agent_checkpoints'))
            self.assertNotIn('router bgp 65000',checkpoints);self.assertNotIn('UNSAVED_B3',checkpoints)

    async def test_literal_address_is_not_confused_with_longer_address_prefix(self):
        self.editor['content']=BUFFER.replace('router-id 192.0.2.1','router-id 192.0.2.20')
        with patch('local_providers.chat.generate',AsyncMock(side_effect=AssertionError('Unique literal needs no model patch'))):
            result=await self.ask('In the active file replace BGP neighbor 192.0.2.2 with 192.0.2.44. Preserve every other line.',editor=self.editor)
        self.assertEqual(result.kind,'edit_proposal',result.answer)
        self.assertEqual(result.proposal['suggested'],self.editor['content'].replace('neighbor 192.0.2.2 ','neighbor 192.0.2.44 '))
        self.assertIn('router-id 192.0.2.20',result.proposal['suggested'])
        self.assertEqual(result.proposal['validation']['proposal_method'],'exact_user_literal')

    async def test_general_question_drops_editor_and_engineering_history(self):
        await self.propose()
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='answer'))),patch('local_providers.chat.generate',AsyncMock(return_value=('2','test'))) as model:
            result=await self.ask('How much is 1+1?',editor=self.editor)
        self.assertNotIn('UNSAVED_B3',str(model.call_args.args));self.assertNotIn('192.0.2.44',str(model.call_args.args))
        self.assertFalse(result.context_coverage['routing']['editor']);self.assertEqual(result.context_coverage['agent']['engineering_calls'],0)

    async def test_generation_graph_calls_existing_v9_once_and_replays_no_actions(self):
        from llm.gateway_v9 import preview
        data={'parsed_intent':{'action':'configure_ospf','_v9_session':'test-review'},'tasks':[{'operation':'configure_ospf'},{'operation':'configure_bgp_neighbor'}],'output_kind':'native'}
        route=SemanticRoute(intent='generate_native')
        body=TurnRequest(request_id=uuid4(),prompt='Generate native OSPF and BGP on TEST-EDGE')
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch('llm.gateway_v9.preview',AsyncMock(return_value=data)) as v9:
            first=await self.g.turn(self.cid,self.user,body)
            second=await self.g.turn(self.cid,self.user,body)
        self.assertEqual(first.kind,'generation_preview',first.answer);self.assertEqual(first,second)
        self.assertEqual(v9.await_count,1);self.assertEqual(first.preview['tasks'],data['tasks'])
        self.assertIn('plan_configuration',first.context_coverage['agent']['nodes'])

    async def test_denied_edit_readonly_and_invalid_patch(self):
        route=SemanticRoute(intent='edit',use_editor=True)
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)):
            denied=await self.ask('Modify this file',editor=self.editor,user={'username':'alice','role':'auditor'})
        self.assertEqual(denied.status,'denied');self.assertIsNone(denied.proposal)
        self.editor['read_only']=True
        readonly=await self.propose();self.assertEqual(readonly.status,'denied')
        self.editor['read_only']=False
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch('local_providers.chat.generate',AsyncMock(return_value=('{"replacements":[{"old_text":"absent","new_text":"x"}]}','test'))):
            invalid=await self.ask('Change this file',editor=self.editor)
        self.assertEqual(invalid.status,'unavailable');self.assertIsNone(invalid.proposal)

    async def test_no_edit_when_explicitly_explanation_only(self):
        route=SemanticRoute(intent='edit',use_editor=True)
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch.object(self.g.registry,'invoke',AsyncMock(side_effect=AssertionError('must constrain before tool'))),patch('local_providers.chat.generate',AsyncMock(return_value=('BGP is configured.','test'))):
            result=await self.ask('Explain only; do not modify the file',editor=self.editor)
        self.assertEqual(result.kind,'answer');self.assertIsNone(result.proposal)

    async def test_floating_preserves_b2_reads_and_cannot_propose(self):
        floating=self.g.store.create('alice','floating')['id']
        result=await self.ask('Investigate R2 connectivity',identity=floating)
        self.assertEqual(result.context_coverage['agent']['verification']['status'],'verified')
        self.assertEqual(result.context_coverage['agent']['rounds'],2)
        route=SemanticRoute(intent='edit')
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch.object(self.g.registry,'invoke',AsyncMock(side_effect=AssertionError('Floating must not invoke proposal'))):
            result=await self.ask('Modify the file',identity=floating)
        self.assertEqual(result.kind,'clarification')

    async def test_stored_configuration_published_comparison_no_generation(self):
        docs=[{'source':'published:configure_ospf','text':'OSPF schema','published_requirements':{'operations':[{'operation_id':'configure_ospf','description':'OSPF','schema':{'required':['interfaces']},'profiles':[]}]}}]
        with patch('llm.gateway_knowledge.documentation_context',return_value=(docs,[Evidence(id='doc',source='published:configure_ospf',origin='stored')])):
            result=await self.ask("Explain published OSPF operation requirements and compare them with R2's stored configuration.",editor=self.editor)
        self.assertIn('OWNED_CONFIG',result.answer);self.assertIn('`interfaces`',result.answer)
        self.assertIsNone(result.preview);self.assertEqual(result.context_coverage['agent']['engineering_calls'],0)
        self.assertFalse(result.context_coverage['routing']['editor'])

    async def test_stale_revision_before_and_during_inference(self):
        self.editor['saved_revision']=99
        stale=await self.propose();self.assertEqual(stale.status,'unavailable');self.assertIn('revision changed',stale.answer)
        self.editor['saved_revision']=0
        from local_providers.authoring import AuthoringStore
        original=AuthoringStore.latest;inferred=False
        def changed(store,*args,**kwargs):
            return {'revision':1} if inferred else original(store,*args,**kwargs)
        async def generate(*args,**kwargs):
            nonlocal inferred
            inferred=True
            return json.dumps({'replacements':[{'old_text':'192.0.2.2','new_text':'192.0.2.44'}]}),'test'
        with patch.object(AuthoringStore,'latest',changed),patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='edit',use_editor=True))),patch('local_providers.chat.generate',generate):
            result=await self.ask('Change the BGP neighbor address in the open file',editor=self.editor)
        self.assertEqual(result.status,'unavailable');self.assertIsNone(result.proposal)
        self.assertIn('during inference',result.answer)

    async def test_bounded_patch_repair_uses_the_same_exact_guard(self):
        bad=json.dumps({'replacements':[{'old_text':'BGP neighbor 192.0.2.2','new_text':'BGP neighbor 192.0.2.44'}]})
        good=json.dumps({'replacements':[{'old_text':'192.0.2.2','new_text':'192.0.2.44'}]})
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='edit',use_editor=True))),patch('local_providers.chat.generate',AsyncMock(side_effect=[(bad,'test'),(good,'test')])) as model:
            result=await self.ask('Replace the BGP neighbor address in the open file',editor=self.editor)
        self.assertEqual(result.kind,'edit_proposal',result.answer);self.assertEqual(model.await_count,2)
        self.assertEqual(result.proposal['validation']['model_patch_attempts'],2)
        self.assertEqual(result.proposal['original'],BUFFER);self.assertIn('router ospf 10',result.proposal['suggested'])

    async def test_scoped_preservation_does_not_cancel_the_requested_edit(self):
        result=await self.propose(prompt='Change the BGP neighbor to 192.0.2.44, but do not modify the OSPF section.')
        self.assertEqual(result.kind,'edit_proposal',result.answer)

    async def test_model_failure_and_unavailable_playbook_variant(self):
        route=SemanticRoute(intent='edit',use_editor=True)
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch('local_providers.chat.generate',AsyncMock(side_effect=HTTPException(503,'Ollama offline'))):
            result=await self.ask('Modify the open BGP neighbor',editor=self.editor)
        self.assertEqual(result.status,'unavailable');self.assertIsNone(result.proposal)
        data={'parsed_intent':{'action':'configure_ospf'},'playbook_support':{'status':'unsupported'},'output_kind':'playbook'}
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='generate_playbook'))),patch('llm.gateway_v9.preview',AsyncMock(return_value=data)) as v9:
            result=await self.ask('Generate an Ansible OSPF playbook')
        self.assertEqual(v9.call_args.args[4],'playbook');self.assertEqual(result.preview['playbook_support']['status'],'unsupported')
        self.assertIsNone(result.proposal)

    def test_literal_edit_avoids_address_prefixes_and_ambiguous_occurrences(self):
        from llm.gateway_documents import literal_address_patch
        editor={**self.editor,'content':'neighbor 192.0.2.20 remote-as 65001\n'}
        request=TurnRequest(request_id=uuid4(),prompt='Replace 192.0.2.2 with 192.0.2.44',editor=editor)
        self.assertIsNone(literal_address_patch(request))
        editor={**self.editor,'content':'neighbor 192.0.2.2 remote-as 65001\nrouter-id 192.0.2.2\n'}
        request=TurnRequest(request_id=uuid4(),prompt='Replace 192.0.2.2 with 192.0.2.44',editor=editor)
        self.assertIsNone(literal_address_patch(request))

    async def test_wrong_requested_address_is_not_released_as_a_proposal(self):
        patch_text=json.dumps({'replacements':[{'old_text':'192.0.2.2','new_text':'192.0.2.44'}]})
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='edit',use_editor=True))),patch('local_providers.chat.generate',AsyncMock(return_value=(patch_text,'test'))):
            result=await self.ask('Change the neighbor address to 192.0.2.55',editor=self.editor)
        self.assertEqual(result.status,'unavailable');self.assertIsNone(result.proposal)

    async def test_selected_snippet_and_changed_document_explanation(self):
        self.editor['selection']={'text':'neighbor 192.0.2.2 remote-as 65001','start_line':7,'end_line':7}
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='explain',use_editor=True))),patch('local_providers.chat.generate',AsyncMock(return_value=('The selected neighbor uses remote AS 65001.','test'))) as model:
            result=await self.ask('Why does this selected line have remote-as?',editor=self.editor)
        self.assertTrue(result.context_coverage['files']['selection_included'])
        self.assertIn('Selected lines',str(model.call_args.args))
        await self.propose()
        self.editor['document_id']='other-document'
        result=await self.ask('Explain your modification',editor=self.editor)
        self.assertEqual(result.kind,'clarification');self.assertIsNone(result.proposal)

    async def test_v9_template_and_parameter_rejections_do_not_trigger_fallback(self):
        for reason in ['No declared template compatibility','remote_as must be at least 1']:
            with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='generate_native'))),patch('llm.gateway_v9.preview',AsyncMock(side_effect=HTTPException(422,reason))) as v9,patch('local_providers.chat.generate',AsyncMock(side_effect=AssertionError('must not substitute model-generated configuration'))):
                result=await self.ask('Generate BGP and static routing on TEST-EDGE')
            self.assertEqual(v9.await_count,1);self.assertEqual(result.status,'unavailable')
            self.assertIn(reason,result.answer);self.assertIsNone(result.preview)
        with self.db._connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM jobs').fetchone()[0],0)

    async def test_malformed_model_patch_does_not_change_a_file(self):
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='edit',use_editor=True))),patch('local_providers.chat.generate',AsyncMock(return_value=('not a patch','test'))) as model:
            result=await self.ask('Refactor the open configuration',editor=self.editor)
        self.assertEqual(result.status,'unavailable');self.assertIsNone(result.proposal)
        self.assertEqual(model.await_count,1)


if __name__=='__main__':unittest.main()
