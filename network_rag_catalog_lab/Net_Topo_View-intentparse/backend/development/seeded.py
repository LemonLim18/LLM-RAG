"""Reproducible editable observations, without diagnoses or test oracles.

Extends the existing scenario definition, validators and readers. This is not a
protocol emulator. Expected results belong in evaluations, never this payload.
"""
import json
import random
from copy import deepcopy
from development.examples import protocol_observations

VARIANTS=('healthy','interface_down','return_route','acl','ospf_timer','bgp_as','conflict')


def seeded_scenario(seed:int,variant='healthy'):
    if not 0<=seed<=65535 or variant not in VARIANTS:raise ValueError('Unknown seed or observation variant')
    rng=random.Random(seed);value=protocol_observations()
    names=rng.sample(['Juniper','Maple','Cypress','Alder','Hazel','Pine','Willow','Spruce','Ash','Elm','Larch','Cedar'],3)
    names=[name+'-'+str(seed) for name in names]
    octet=1+seed%200;subnet=(seed//200)%200
    substitutions={'Branch-Aster':names[0],'Core-Birch':names[1],'Edge-Cedar':names[2]}
    for suffix in [1,2,5,6]:substitutions['10.44.0.'+str(suffix)]=f'10.{octet}.{subnet}.{suffix}'
    for suffix in [1,2,3]:substitutions['198.18.0.'+str(suffix)]=f'198.19.{seed%200}.{suffix}'
    # Apply to string leaves only. Numeric typed identities remain authoritative.
    def replace(item):
        if isinstance(item,dict):return {key:replace(child) for key,child in item.items()}
        if isinstance(item,list):return [replace(child) for child in item]
        if isinstance(item,str):
            for before,after in substitutions.items():item=item.replace(before,after)
        return item
    value=replace(value)
    backups=deepcopy(value['records']['running_configuration'])
    for record in backups:
        record.update(id='saved-'+str(record['device_id']),timestamp='2026-10-18T00:59:50Z',kind='configuration_snapshot',current=False)
    value['records']['configuration']=backups;value['availability']['configuration']=True
    value.update(id=f'GENERATED-{seed:05d}-{VARIANTS.index(variant):02d}',revision=1,title='Seeded three-vendor observations '+str(seed))
    # IDs/titles disclose no expected diagnosis to the model. Variant is a local
    # authoring input; validation still checks all ownership/address references.
    if variant=='interface_down':
        value['interfaces'][2].update(admin_status='down',oper_status='down')
        value['records']['running_configuration'][1]['values']['config_text']+='set interfaces ge-0/0/1 disable\n'
    elif variant=='return_route':value['network']['tables'][2]['routes']=[]
    elif variant=='acl':
        value['network']['policies']=[dict(id='reviewed-filter',interface_id=2,direction='ingress',default_action='permit',rules=[dict(id='scope-rule',source=value['network']['flows'][0]['source_address']+'/32',destination=value['network']['flows'][0]['destination_address']+'/32',action='deny')])]
        flow=value['network']['flows'][0]
        value['records']['running_configuration'][1]['values']['config_text']+=f"set firewall family inet filter reviewed-filter term scope-rule from source-address {flow['source_address']}/32\nset firewall family inet filter reviewed-filter term scope-rule from destination-address {flow['destination_address']}/32\nset firewall family inet filter reviewed-filter term scope-rule then discard\nset firewall family inet filter reviewed-filter term default then accept\nset interfaces ge-0/0/0 unit 0 family inet filter input reviewed-filter\n"
    elif variant in {'ospf_timer','conflict'}:
        value['network']['ospf'][0]['right']['hello_seconds']=20
        value['records']['running_configuration'][1]['values']['config_text']+='set protocols ospf area 0.0.0.0 interface ge-0/0/0.0 hello-interval 20\n'
        if variant=='ospf_timer':value['network']['ospf'][0]['observed_state']='Down'
    elif variant=='bgp_as':
        value['network']['bgp'][0]['right']['remote_as']=65100+seed%500
        address=value['network']['bgp'][0]['left']['address']
        value['records']['running_configuration'][2]['values']['config_text']=value['records']['running_configuration'][2]['values']['config_text'].replace(f'peer {address} as-number 65020',f'peer {address} as-number {65100+seed%500}')
        value['network']['bgp'][0]['observed_state']='Active'
    return value
