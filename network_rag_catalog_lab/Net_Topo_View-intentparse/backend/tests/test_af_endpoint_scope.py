"""Recorded endpoint chains retain exact inventory identity; zero inference."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_network import route_network


def inventory(*names):
    return {'devices':[{'id':i+1,'hostname':name,'aliases':[],'management_ip':None}
                       for i,name in enumerate(names)]}


def refs(prompt,records):
    return route_network(prompt,records,expand_investigation=False)[1].get('device_refs',[])


@pytest.mark.parametrize('chain',[
    'Alder-to-Prism','ALDER-TO-prism','Alder-Prism','Alder→Prism',
    'Alder->Prism','Alder—Prism','Alder to Prism',
])
def test_known_joined_endpoints_keep_both_whole_names(chain):
    assert set(refs('Investigate the declared '+chain+' HTTPS incident comprehensively.',inventory('Alder','Prism')))=={'Alder','Prism'}


def test_joined_path_may_use_recorded_aliases():
    records=inventory('Copper-Edge','Slate-Core')
    records['devices'][0]['aliases']=['Origin-Alias']
    records['devices'][1]['aliases']=['Destination-Alias']
    assert refs('Investigate Origin-Alias-to-Destination-Alias forwarding.',records)==['Copper-Edge','Slate-Core']


def test_joined_endpoints_can_have_hyphenated_inventory_names():
    assert refs('Investigate Core-Alder-to-Edge-Prism.',inventory('Core-Alder','Edge-Prism'))==['Core-Alder','Edge-Prism']


def test_multiple_joined_hops_are_known_inventory_identities():
    assert refs('Trace Alder-to-Prism-to-Nacre.',inventory('Alder','Prism','Nacre'))==['Alder','Prism','Nacre']


@pytest.mark.parametrize('atomic',['Alder-Prism','Alder-to-Prism'])
def test_exact_atomic_hostname_is_not_split_into_separate_devices(atomic):
    assert refs('Investigate '+atomic+'.',inventory('Alder','Prism',atomic))==[atomic]


def test_exact_hyphenated_member_in_longer_path_stays_atomic():
    assert refs('Investigate Alder-to-Prism-to-Nacre.',inventory('Alder','Prism','Alder-to-Prism','Nacre'))==['Alder-to-Prism','Nacre']


def test_separator_to_is_not_a_third_inventory_target():
    assert refs('Investigate Alder-to-Prism.',inventory('Alder','Prism','to'))==['Alder','Prism']


@pytest.mark.parametrize('chain',[
    'Alder-to-Prism-extra','prefix-Alder-to-Prism','Alder-to-Unrecorded',
    'Unknown-to-Prism','Alder-to-PrismSuffix','Alder-to-Prism_to_unknown',
])
def test_unknown_or_longer_joined_identity_does_not_leak_partial_matches(chain):
    assert refs('Investigate '+chain+'.',inventory('Alder','Prism'))==[]


def test_short_inventory_prefix_does_not_capture_a_longer_hostname():
    assert refs('Investigate R1-backup.',inventory('R1','R1-backup'))==['R1-backup']
    assert refs('Investigate Alder-backup.',inventory('Alder'))==[]


def test_source_only_policy_words_and_no_read_words_are_not_hostname_rewrites():
    records=inventory('Alder','Prism','other-source')
    domains,query=route_network('Using state only, inspect Alder-to-Prism. Do not read other sources.',records,expand_investigation=False)
    assert query['device_refs']==['Alder','Prism']
    assert query['live'] is False
    assert 'configuration' not in domains


def test_non_network_prose_does_not_create_joined_targets():
    assert refs('Explain end-to-end encryption in general.',inventory('Alder','Prism'))==[]
