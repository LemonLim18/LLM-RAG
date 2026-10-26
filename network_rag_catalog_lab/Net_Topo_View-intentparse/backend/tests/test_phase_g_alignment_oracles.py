"""Independent literal/arithmetic checks before inference; not model grading."""
from datetime import datetime
from decimal import Decimal
import ipaddress
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

SPEC=Path(__file__).resolve().parents[2]/'docs/evaluations/phase_g_alignment_holdout_v3.json'


def test_frozen_setup_and_role_expectations_match_actual_source_fields():
    spec=json.loads(SPEC.read_text(encoding='utf-8'))
    from scripts.evaluate_phase_f_registry import validate_registry
    validate_registry(spec)
    assert len(spec['quality_cases'])==30
    healthy=spec['network_fixtures']['healthy']
    assert [d['hostname'] for d in healthy['devices']]==['Spruce-Start','Willow-Relay','Granite-End']
    assert [d['management_ip'] for d in healthy['devices']]==['192.0.2.81','192.0.2.82','192.0.2.83']
    interfaces={i['id']:i for i in healthy['interfaces']}
    for link in healthy['planned_links']:
        a,b=(interfaces[link[k]] for k in ['src_interface_id','dst_interface_id'])
        assert a['device_id']==link['src_device_id'] and b['device_id']==link['dst_device_id']
        left,right=ipaddress.ip_interface(a['prefix']),ipaddress.ip_interface(b['prefix'])
        assert left.ip in right.network and right.ip in left.network
    down=spec['network_fixtures']['interface_down']['interfaces'][2]
    assert (down['device_id'],down['name'],down['admin_status'],down['oper_status'])==(1200,'ge-0/0/1.0','down','down')
    assert spec['network_fixtures']['return_route']['network']['tables'][2]['routes']==[]
    for variant in ['ospf_timer','conflict']:
        session=spec['network_fixtures'][variant]['network']['ospf'][0]
        assert (session['left']['hello_seconds'],session['right']['hello_seconds'])==(14,28)
        assert session['left']['dead_seconds']==session['right']['dead_seconds']==56
    peers=spec['network_fixtures']['bgp_as']['network']['bgp'][0]
    assert (peers['left']['local_as'],peers['left']['remote_as'])==(64641,64642)
    assert (peers['right']['local_as'],peers['right']['remote_as'])==(64642,64690)
    saved=healthy['records']['configuration'][1]['values']['config_text']
    assert 'autonomous-system 64641' in saved and 'router-id' not in saved


def test_measurement_expectations_use_independent_datetime_and_decimal_arithmetic():
    spec=json.loads(SPEC.read_text(encoding='utf-8'))
    scenario=spec['network_fixtures']['metrics']
    traffic,counter=scenario['network']['metrics']
    stamps=[datetime.fromisoformat(p['timestamp'].replace('Z','+00:00')) for p in counter['samples']]
    gaps=[(b-a).total_seconds() for a,b in zip(stamps,stamps[1:])]
    assert gaps==[40,40] and (stamps[-1]-stamps[0]).total_seconds()==80
    assert [p['value'] for p in traffic['samples']]==[11000000,13000000,15000000]
    assert Decimal(max(p['value'] for p in traffic['samples']))/Decimal(scenario['interfaces'][0]['speed_bps'])*100==50
    values=[Decimal(p['value']) for p in counter['samples']]
    assert values==[8,14,24] and (values[-1]-values[0])/Decimal(80)==Decimal('0.2')
    reset=spec['network_fixtures']['reset']['network']['metrics'][-1]
    assert [p['value'] for p in reset['samples']]==[2200,11,16]
    assert reset['samples'][1]['value']<reset['samples'][0]['value']<2**32


def test_document_and_editor_expectations_are_literal_not_inferred_state():
    spec=json.loads(SPEC.read_text(encoding='utf-8'))
    pages=spec['document_fixtures']['maintenance']['pages']
    assert all(s in pages[0] for s in ['February 9','05:15','05:50','relay engineering','No year'])
    assert 'hello 22 seconds and dead 88 seconds' in pages[1]
    assert all(s in pages[2] for s in ['64681','203.0.113.82','64682'])
    assert [d['text'] for d in spec['document_fixtures']['conflicting']]==[
        'Proposed OSPF dead interval: 84 seconds.','Proposed OSPF dead interval: 112 seconds.']
    text=spec['editor_fixtures']['routing']
    assert 'router-id 203.0.113.81' in text and 'router bgp 64681' in text
    assert 'neighbor 203.0.113.82 remote-as 64682' in text
    assert '! KEEP_BASELINES' in text and '! UNSAVED_QUALIFICATION' in text
    assert 'router-id' not in text.split('router bgp',1)[1]
