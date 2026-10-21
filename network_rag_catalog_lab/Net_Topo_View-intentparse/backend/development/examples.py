"""Sanitized scenario-authoring example. Expected diagnoses live in tests only."""
def mixed_vendor_path():
    stamp='2026-10-18T01:00:00Z'
    device=lambda identity,name,vendor,version:dict(id=identity,hostname=name,management_ip='192.0.2.'+str(identity//100),vendor=vendor,os_version=version,role='router',site='Development')
    interface=lambda identity,owner,name,prefix:dict(id=identity,device_id=owner,name=name,prefix=prefix,admin_status='up',oper_status='up',vrf='default')
    route=lambda identity,prefix,interface,address:dict(id=identity,prefix=prefix,origin='static',preference=10,next_hops=[dict(interface_id=interface,address=address,resolved=True)])
    return dict(format_version=2,id='MIXED-PATH-001',revision=1,title='Three-vendor routed observation example',
        logical_time=stamp,model_scope='ipv4_observation',inventory_complete=True,
        devices=[device(1100,'Branch-Aster','cisco_xe','17.9'),device(1200,'Core-Birch','juniper_junos','23.4'),device(1300,'Edge-Cedar','huawei_vrp','8')],
        interfaces=[interface(1,1100,'GigabitEthernet0/1','10.44.0.1/30'),interface(2,1200,'ge-0/0/0.0','10.44.0.2/30'),
            interface(3,1200,'ge-0/0/1.0','10.44.0.5/30'),interface(4,1300,'GigabitEthernet0/0/1','10.44.0.6/30'),
            interface(5,1100,'Loopback0','198.18.0.1/32'),interface(6,1200,'lo0.0','198.18.0.2/32'),interface(7,1300,'LoopBack0','198.18.0.3/32')],
        planned_links=[dict(id=1,src_device_id=1100,src_interface_id=1,dst_device_id=1200,dst_interface_id=2),dict(id=2,src_device_id=1200,src_interface_id=3,dst_device_id=1300,dst_interface_id=4)],
        records={name:[] for name in ['state','telemetry','syslog','incidents','configuration','running_configuration','topology']},
        availability={name:name in {'state','topology'} for name in ['state','telemetry','syslog','incidents','configuration','running_configuration','topology']},
        network=dict(observed_at=stamp,policy_attachments_complete=True,
            tables=[dict(device_id=1100,complete=True,routes=[route('aster-cedar','198.18.0.3/32',1,'10.44.0.2')]),
                dict(device_id=1200,complete=True,routes=[route('birch-cedar','198.18.0.3/32',3,'10.44.0.6'),route('birch-aster','198.18.0.1/32',2,'10.44.0.1')]),
                dict(device_id=1300,complete=True,routes=[route('cedar-aster','198.18.0.1/32',4,'10.44.0.5')])],
            flows=[dict(id='branch-edge-icmp',source_device_id=1100,destination_device_id=1300,source_address='198.18.0.1',destination_address='198.18.0.3')]))


def protocol_observations():
    """Editable declared observations, not protocol emulation or expected answers."""
    s=mixed_vendor_path();s.update(id='PROTOCOL-MIXED-001',title='Three-vendor protocol and configuration observations')
    s['network']['ospf']=[dict(id='adjacency-aster-birch',
        left=dict(device_id=1100,interface_id=1,router_id='198.18.0.1',area='0.0.0.0',hello_seconds=10,dead_seconds=40,network_type='point_to_point',role='point_to_point'),
        right=dict(device_id=1200,interface_id=2,router_id='198.18.0.2',area='0.0.0.0',hello_seconds=10,dead_seconds=40,network_type='point_to_point',role='point_to_point'),observed_state='Full')]
    s['network']['bgp']=[dict(id='session-birch-cedar',
        left=dict(device_id=1200,address='10.44.0.5',local_as=65020,remote_as=65030,address_families=['ipv4_unicast']),
        right=dict(device_id=1300,address='10.44.0.6',local_as=65030,remote_as=65020,address_families=['ipv4_unicast']),
        observed_state='Established',transport_reachable=True,accepted_prefixes=['198.18.0.3/32'],rejected_prefixes=[],policy_observed=True)]
    configurations={1100:'hostname Branch-Aster\ninterface GigabitEthernet0/1\n ip address 10.44.0.1 255.255.255.252\n ip ospf network point-to-point\n ip ospf 20 area 0\nrouter ospf 20\n router-id 198.18.0.1\n',
        1200:'set system host-name Core-Birch\nset interfaces ge-0/0/0 unit 0 family inet address 10.44.0.2/30\nset protocols ospf area 0.0.0.0 interface ge-0/0/0.0 interface-type p2p\nset routing-options autonomous-system 65020\nset protocols bgp group CEDAR type external\nset protocols bgp group CEDAR peer-as 65030\nset protocols bgp group CEDAR neighbor 10.44.0.6\n',
        1300:'sysname Edge-Cedar\ninterface GigabitEthernet0/0/1\n ip address 10.44.0.6 255.255.255.252\nquit\nbgp 65030\n peer 10.44.0.5 as-number 65020\n'}
    for did,config in configurations.items():
        s['records']['running_configuration'].append(dict(id='active-'+str(did),device_id=did,timestamp=s['logical_time'],kind='running_configuration',source='scenario_author',current=True,values={'config_text':config}))
    s['availability']['running_configuration']=True
    return s


def performance_observations():
    s=protocol_observations();s.update(id='PERFORMANCE-MIXED-001',title='Directional traffic and counter sampling')
    s['interfaces'][2]['speed_bps']=1000000000
    times=['2026-10-18T00:59:40Z','2026-10-18T00:59:50Z',s['logical_time']]
    for identity,metric,unit,values in [('core-out','out_bps','bps',[920000000,950000000,940000000]),('core-drops','discards','count',[20,25,32])]:
        s['network'].setdefault('metrics',[]).append(dict(id=identity,device_id=1200,interface_id=3,metric=metric,unit=unit,sampling_seconds=10,samples=[dict(timestamp=t,value=v) for t,v in zip(times,values)]))
    s['availability']['telemetry']=True
    return s
