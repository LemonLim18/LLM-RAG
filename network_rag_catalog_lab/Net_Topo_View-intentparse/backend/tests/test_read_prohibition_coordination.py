"""Separate prohibited reading from adjacent prohibited engineering actions."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.request_contract import reader_constraints,advisory_contract

@pytest.mark.parametrize('tail',['Do not collect live data or change anything.','Do not read syslog or modify anything.','Do not read configuration and deploy anything.'])
def test_nonread_anything_does_not_become_a_universal_reader_ban(tail):
    p=reader_constraints('Investigate stored network evidence. '+tail)
    assert p['denied']!={'inventory','topology','configuration','state','syslog','telemetry','incidents','knowledge'}
    if 'syslog' in tail:assert 'syslog' in p['denied']
    if 'configuration' in tail:assert 'configuration' in p['denied']

@pytest.mark.parametrize('tail',['Do not read anything.','Do not read or collect anything.','Do not read, collect, test, modify or generate anything.'])
def test_coordinated_no_read_still_denies_every_reader(tail):
    p=reader_constraints('Recommend a passive observation check. '+tail)
    assert p['denied']=={'inventory','topology','configuration','state','syslog','telemetry','incidents','knowledge'}

def test_instrumental_context_preface_does_not_erase_advisory_speech_act():
    p='Using our earlier edge-port context, recommend two passive evidence checks. Explain their limits. Do not read, collect, test, modify or generate anything.'
    c=advisory_contract(p);assert c and c.advice_only and c.original_request==p

def test_instrumental_preface_does_not_turn_real_read_into_advice():
    assert advisory_contract('Using that device context, read recorded state and then recommend a check.') is None
