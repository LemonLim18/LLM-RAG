"""Prior reader metadata must not select the next independent workflow."""
import asyncio,json,os,sys
from pathlib import Path
from unittest.mock import AsyncMock,patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_routing import select_context

INVENTORY={'devices':[{'id':61,'hostname':'Edge-Olive','aliases':[],
 'interfaces':[{'id':611,'name':'Ethernet1/1'},{'id':612,'name':'Ethernet1/2'}]},
 {'id':62,'hostname':'Edge-Cedar','aliases':[],'interfaces':[]}]}
PREVIOUS={'context_coverage':{'retrieval':{'domains':['state'],'device_refs':['61'],
 'interface_refs':['611'],'attributes':[],'entities':[{'device_id':'61','interface_id':'611'}]}}}
HISTORY=[{'role':'user','content':'Investigate Edge-Olive Ethernet1/1 using available records.'}]

@pytest.mark.parametrize('surface',['floating','studio'])
@pytest.mark.parametrize('domains',[['state'],['state','configuration']])
def test_explicit_state_policy_controls_attributes_without_widening(surface,domains):
 prompt='Use state only to compare Edge-Olive Ethernet1/1 observations, including prefix and source. Do not read other sources.'
 proposed={'intent':'answer','information_needs':[{'domain':d,'question':'Requested observations'} for d in domains]}
 model=AsyncMock(return_value=(json.dumps(proposed),'mocked-source-selection'))
 with patch.dict(os.environ,COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_EVIDENCE_REFINE='0',COGNISHIELD_AI_OUTCOMES='0'):
  route=asyncio.run(select_context(prompt,'test',surface,None,[],[],None,INVENTORY,model))
 assert route.network_domains==['state'] and route.interface_refs==['611']
 if domains==['state']:
  assert route.planning['mode']=='validated_model_plan'
 else:
  assert route.planning['mode']!='validated_model_plan'

@pytest.mark.parametrize('wording',['address','addresses','IP address','IP addresses'])
def test_address_attribute_uses_both_number_forms(wording):
 from llm.gateway_references import attributes
 assert 'addresses' in attributes(wording)
 assert 'management_address' in attributes('management '+wording)

@pytest.mark.parametrize('surface',['floating','studio'])
@pytest.mark.parametrize('wording',['What is 18 plus 24?','Explain the difference between a queue and a stack.',
 'Give a short Python example that reverses a string.'])
def test_conversation_confidence_gate_still_runs_with_owned_network_history(surface,wording):
 model=AsyncMock(return_value=(json.dumps({'intent':'answer','information_needs':[
  {'domain':'telemetry','question':'unrelated request interpreted as measurements'}]}),'recorded-model-failure'))
 with patch.dict(os.environ,COGNISHIELD_AI_PLANNING='1'),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value={'intent':'answer','domains':[]})):
  route=asyncio.run(select_context(wording,'test',surface,None,[],HISTORY,PREVIOUS,INVENTORY,model))
 assert route.intent=='answer' and not route.network_domains and not route.use_history
 model.assert_not_awaited()

@pytest.mark.parametrize('surface',['floating','studio'])
def test_uncertain_unbound_turn_uses_existing_workflow_classifier_before_information_plan(surface):
 schemas=[]
 async def generate(messages,structured,**kwargs):
  schemas.append(structured)
  if 'information_needs' in structured['properties']:
   return json.dumps({'intent':'answer','information_needs':[{'domain':'telemetry','question':'irrelevant'}]}),'test'
  return json.dumps({'intent':'answer','use_history':False}),'test'
 with patch.dict(os.environ,COGNISHIELD_AI_PLANNING='1'),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
  route=asyncio.run(select_context('Explain a binary search algorithm.','test',surface,None,[],HISTORY,PREVIOUS,INVENTORY,generate))
 assert not route.network_domains and not route.use_history
 assert len(schemas)==1 and 'information_needs' not in schemas[0]['properties']

@pytest.mark.parametrize('surface',['floating','studio'])
def test_actual_other_interface_reference_is_retained(surface):
 with patch.dict(os.environ,COGNISHIELD_AI_PLANNING='1'):
  route=asyncio.run(select_context('What is the other interface IP address?','test',surface,None,[],HISTORY,PREVIOUS,INVENTORY,
   AsyncMock(side_effect=AssertionError('The owned exact reference must resolve without a planner'))))
 assert route.use_history and route.device_refs==['61'] and route.interface_refs==['612']
 assert route.network_domains==['inventory']

@pytest.mark.parametrize('surface',['floating','studio'])
def test_missing_reference_never_becomes_an_unscoped_reader(surface):
 route=asyncio.run(select_context('What is its address?','test',surface,None,[],[],None,INVENTORY,
  AsyncMock(side_effect=AssertionError('A missing reference must clarify before inference'))))
 assert route.intent=='clarify' and not route.network_domains

@pytest.mark.parametrize('surface',['floating','studio'])
def test_new_explicit_inventory_scope_does_not_reuse_previous_device(surface):
 model=AsyncMock(return_value=(json.dumps({'intent':'answer','information_needs':[{'domain':'inventory','question':'recorded device list'}]}),'test'))
 with patch.dict(os.environ,COGNISHIELD_AI_PLANNING='1'),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
  route=asyncio.run(select_context('List the devices recorded in our inventory.','test',surface,None,[],HISTORY,PREVIOUS,INVENTORY,model))
 assert route.network_domains==['inventory'] and route.device_refs==[] and not route.use_history
