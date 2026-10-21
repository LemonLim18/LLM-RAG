"""Authoring recipes and review fixtures; never used as a runtime renderer.

Templates are saved through V9. Preview-derived golden outputs are explicitly
proposals for a human review, not independent semantic/device certification.
"""
import re
from pathlib import Path

EXTRA_FIELDS={
 'next_hop_kind':('string',{'enum':['next-hop','qualified-next-hop']}),
 'native_vlan':('integer',{'minimum':1,'maximum':4094}),
 'old_vlan_name':('string',{'minLength':1,'maxLength':32,'pattern':'^[A-Za-z][A-Za-z0-9_-]*$'}),
 'ospf_interface':('string',{'minLength':1,'maxLength':64,'pattern':'^[A-Za-z][A-Za-z0-9/.-]*$'}),
 'ospf_area':('string',{'pattern':'^[0-9.]+$'}),
 'forwarding_class':('string',{'minLength':1,'maxLength':32,'pattern':'^[A-Za-z][A-Za-z0-9_-]*$'}),
 'login_class':('string',{'minLength':1,'maxLength':32,'pattern':'^[A-Za-z][A-Za-z0-9_-]*$'}),
 'name':('string',{'minLength':1,'maxLength':32,'pattern':'^[A-Za-z][A-Za-z0-9_-]*$'})}


def template(root,row):
    """Preserve existing native bodies except explicit, auditable family fixes."""
    op,v=row['operation_id'],row['vendor']
    content=(root/'backend/ansible'/row['path']).read_text(encoding='utf-8')
    content=re.sub(r'^\{#.*?#\}\s*','',content,count=1,flags=re.S)
    # Only registered V9 derivatives are bound. Exact rate conversions reject a
    # nonintegral native unit instead of silently rounding a requested rate.
    content=content.replace('destination_netmask','destination_mask')
    content=re.sub(r'\bbandwidth_kbps\b','((bandwidth_bps // 1000) if bandwidth_bps % 1000 == 0 else (1 // 0))',content)
    content=re.sub(r'\brate_kbps\b','((rate_bps // 1000) if rate_bps % 1000 == 0 else (1 // 0))',content)
    content=content.replace('{{ aggregate_id }}','{{ aggregate_interface.removeprefix("Eth-Trunk") }}')
    # Optional defaults are None in V9. "is defined" alone must not emit None
    # or turn an absent admin_up into an unrequested shutdown.
    content=re.sub(r'\b([A-Za-z_]\w*) is defined',r'\1 is defined and \1 is not none',content)
    if v=='juniper':
        if op=='configure_static_route':content='set routing-options static route {{ destination }} {% if preference is defined and preference is not none %}qualified-next-hop {{ next_hop }} preference {{ preference }}{% else %}next-hop {{ next_hop }}{% endif %}\n'
        if op=='remove_static_route':content='delete routing-options static route {{ destination }} {{ next_hop_kind }} {{ next_hop }}\n'
        if op=='modify_vlan':content='{% if vlan_status == "suspend" %}deactivate{% else %}activate{% endif %} vlans {{ name }}\n'
        if op=='configure_ospf_redistribution':content=content.replace('then external type','then external type')+'\nset policy-options policy-statement {{ route_policy }} term DEFAULT_REJECT then reject\n'
        if op=='configure_policing':content='set firewall policer {{ policy_name }} if-exceeding bandwidth-limit {{ rate_bps }}\nset firewall policer {{ policy_name }} if-exceeding burst-size-limit {{ burst_bytes }}\nset firewall policer {{ policy_name }} then {{ {"drop":"discard"}[exceed_action] }}\nset firewall family inet filter {{ policy_name }} term POLICE then policer {{ policy_name }}\nset firewall family inet filter {{ policy_name }} term POLICE then accept\nset interfaces {{ interface.split(".")[0] }} unit {{ interface.split(".")[1] if "." in interface else "0" }} family inet filter {{ {"ingress":"input","egress":"output"}[direction] }} {{ policy_name }}\n'
        if op in {'apply_qos_policy_to_interface','configure_shaping'}:
            content='{% if direction != "egress" %}{{ {"egress": ""}[direction] }}{% endif %}\n'+content
        if op=='configure_exec_timeout':content='set system login class {{ login_class }} idle-timeout {{ exec_timeout_minutes + (1 if exec_timeout_seconds is not none and exec_timeout_seconds > 0 else 0) }}\n'
        if op=='configure_login_banner':content='set system login message {{ login_banner_text | tojson }}\n'
        if op=='configure_login_lockout':content='set system login retry-options tries-before-disconnect {{ login_failure_attempts }}\nset system login retry-options lockout-period {{ (login_block_seconds + 59) // 60 }}\nset system login retry-options minimum-time {{ login_failure_window_seconds }}\n'
        if op in {'configure_isis_interface','disable_isis_interface'}:
            prefix='{% set prefix = "" if process_name == "default" else "routing-instances " ~ process_name ~ " " %}'
            if op=='disable_isis_interface':content=prefix+'delete {{ prefix }}protocols isis interface {{ interface }}\n'
            else:content=prefix+'set interfaces {{ interface.split(".")[0] }} unit {{ interface.split(".")[1] if "." in interface else (1 // 0) }} family iso\nset {{ prefix }}protocols isis interface {{ interface }}\n{% if level == "level-1" %}set {{ prefix }}protocols isis interface {{ interface }} level 2 disable\n{% elif level == "level-2" %}set {{ prefix }}protocols isis interface {{ interface }} level 1 disable\n{% else %}delete {{ prefix }}protocols isis interface {{ interface }} level 1 disable\ndelete {{ prefix }}protocols isis interface {{ interface }} level 2 disable\n{% endif %}'
        if op in {'configure_interface_ip','remove_interface_ip','configure_loopback_interface'}:
            content=content.replace('interfaces {{ interface }} unit 0','interfaces {{ interface.split(".")[0] }} unit {{ interface.split(".")[1] if "." in interface else "0" }} unit_REMOVED')
            content=content.replace(' unit_REMOVED','')
        if op in {'add_acl_rule','modify_acl_rule'}:content+='\n{% if log %}set firewall family inet filter {{ acl_name }} term RULE_{{ acl_rule_id }} then log\n{% endif %}'
    if v=='huawei':
        if op=='configure_login_banner':content='header login information #\n{{ login_banner_text }}\n#\n'
        if op=='configure_login_lockout':content='aaa\n local-aaa-user wrong-password retry-interval {{ (login_failure_window_seconds + 59) // 60 }} retry-time {{ login_failure_attempts }} block-time {{ (login_block_seconds + 59) // 60 }}\n quit\n'
        if op=='configure_exec_timeout':content='user-interface vty 0 4\n idle-timeout {{ exec_timeout_minutes }} {{ exec_timeout_seconds if exec_timeout_seconds is not none else 0 }}\n quit\n'
        if op in {'configure_isis_interface','disable_isis_interface'}:
            attach='isis enable' if op=='configure_isis_interface' else 'undo isis enable'
            content='interface {{ interface }}\n '+attach+' {{ process_name if process_name.isdigit() and 1 <= (process_name | int) <= 65535 else (1 // 0) }}\n'+(' isis circuit-level {{ level }}\n' if op=='configure_isis_interface' else '')+' quit\n'
        if op=='configure_port_channel':content=content.replace('mode lacp-static','mode {{ {"active":"lacp-static"}[lacp_mode] }}')
        if op=='configure_policing':content='traffic behavior {{ policy_name }}\n car cir {{ rate_kbps }} cbs {{ burst_bytes }} green pass red {{ {"drop":"discard","transmit":"pass"}[exceed_action] }}\n quit\ntraffic policy {{ policy_name }}\n classifier {{ policy_name }} behavior {{ policy_name }}\n quit\ninterface {{ interface }}\n traffic-policy {{ policy_name }} {{ {"ingress":"inbound","egress":"outbound"}[direction] }}\n quit\n'
        # ACL logging belongs only to the rule statement in the source template.
        # Never append it to every context exit (including an undo statement).
    return '{# Native authoring proposal; senior approval and declared caveats required. Not vendor/device/Ansible certified. #}\n'+content.strip()+'\n'


def limitations(op,vendor):
    assumptions=['Engineer confirms the selected recorded target/profile and all existing objects named by this operation.','Rendering is a reviewed native proposal; no device state is changed.']
    limits=['No independent vendor/device certification is asserted. Genuine Ansible output is separately gated.']
    risks=[]
    if 'vlan' in op and vendor=='juniper':assumptions+=['Existing VLAN names must be supplied from the target configuration, not invented from IDs.']
    if 'ospf' in op or 'isis' in op or op=='advertise_network':assumptions+=['Existing protocol process/routing instance, addressed logical interface, and applicable area/NET prerequisites are confirmed.']
    if 'isis' in op:limits+=['Interface attachment only; NET provisioning, adjacency and end-to-end connectivity are not established.']
    if vendor=='juniper' and 'isis' in op:risks+=['process_name=default selects global IS-IS; any other name must be an existing routing instance. Existing unrelated interface family/NET state is not inferred.']
    if vendor=='juniper' and op=='remove_static_route':assumptions+=['next_hop_kind must match the recorded ordinary or preference-qualified next-hop object; no target-state type is inferred.']
    if vendor=='huawei' and 'isis' in op:limits+=['process_name must be a numeric process ID; arbitrary IOS tags are rejected during rendering.']
    if 'qos' in op or op in {'configure_policing','configure_shaping','configure_scheduler','create_classifier','classify_by_dscp'}:
        risks+=['Existing classifier/behavior/forwarding-class objects and policy attachment conflicts require explicit target review. Scheduler, shaping and policer scopes differ across vendors.']
        if vendor=='juniper':limits+=['Scheduler/shaper attachment supports egress only; policer realization supports discard exceed action.']
        if vendor=='huawei':limits+=['VRP rate units are integer kbit/s; nonintegral conversion is not an authorized approximation.']
    if 'acl' in op:risks+=['Stateless IPv4 policy only. Verify term/rule order, implicit deny, existing filter attachments and replacement effects.']
    if op=='configure_login_lockout':risks+=['Login policy can lock out management access. Confirm recovery access and the precise AAA/login scope. Failure-window and lockout granularity differ across platforms.']
    if op=='configure_login_lockout' and vendor=='juniper':risks+=['Junos minimum-time is a login attempt timing policy, not the IOS rolling failure-window algorithm; this is an explicit best-effort realization requiring reviewer acceptance.']
    if op=='modify_vlan' and vendor=='huawei':risks+=['VRP VLAN state command availability is not independently established for this profile; reviewer must explicitly resolve the proposed realization before approving.']
    if op=='configure_port_channel':risks+=['Review aggregate naming, existing bundle membership and platform LACP active/passive behavior; no silent conversion to manual bundling.']
    if op=='configure_port_channel' and vendor=='huawei':limits+=['This proposed VRP realization is active LACP only. Passive input is rejected rather than mapped silently to active/static behavior.']
    return assumptions,limits,risks


def fixture(schema,vendor,op,existing):
    samples={'interface':{'cisco':'GigabitEthernet1/0/5','juniper':'ge-0/0/5','huawei':'GigabitEthernet0/0/5'}[vendor],
        'name':'STAFF','old_vlan_name':'STAFF','new_vlan_name':'ENGINEERING','vlan_id':240,'vlan_status':'active',
        'native_vlan':240,'allowed_vlans':[240,241],'description':'Reviewed uplink','process_id':200,'router_id':'192.0.2.200',
        'process_name':'default' if vendor=='juniper' else '100' if vendor=='huawei' else 'CAMPUS',
        'area':'0','ospf_area':'0','ospf_interface':'ge-0/0/5.0','forwarding_class':'expedited-forwarding','login_class':'network-operators',
        'login_banner_text':'Authorized access only','exec_timeout_minutes':5,'exec_timeout_seconds':0,
        'login_block_seconds':120,'login_failure_attempts':3,'login_failure_window_seconds':60,
        'level':'level-2','policy_name':'EDGE_QOS','classifier_name':'VOICE','dscp_values':[46],'previous_dscp_values':[40],
        'match_mode':'any','bandwidth_bps':20000000,'rate_bps':20000000,'burst_bytes':200000,'direction':'egress','exceed_action':'drop',
        'aggregate_interface':{'cisco':'Port-channel10','juniper':'ae10','huawei':'Eth-Trunk10'}[vendor],
        'member_interfaces':[{'cisco':'GigabitEthernet1/0/5','juniper':'ge-0/0/5','huawei':'GigabitEthernet0/0/5'}[vendor]],'lacp_mode':'active',
        'policy_terms':[{'classifier_name':'VOICE','bandwidth_bps':20000000}],'interfaces':[{'name':{'cisco':'GigabitEthernet1/0/5','juniper':'ge-0/0/5.0','huawei':'GigabitEthernet0/0/5'}[vendor],'area':'0'}],
        'address':'10.25.0.1','prefix_length':24,'admin_up':True,'next_hop':'192.0.2.2','next_hop_kind':'next-hop','preference':200,'destination':'10.50.0.0/16',
        'network_prefix':'10.25.0.0/24','redistribution_source':'connected','route_policy':'REVIEWED_EXPORT','ospf_metric':20,'metric_type':'2',
        'acl_name':'EDGE_FILTER','acl_rule_id':20,'acl_action':'permit','source_prefix':'10.1.0.0/16','destination_prefix':'10.2.0.0/16','ip_protocol':'tcp','destination_port':443,'log':False,'peer_group':'CEDAR','local_as':65020,'remote_as':65030,'neighbor_ip':'192.0.2.2','passive':True,'area_type':'stub'}
    values={k:v for k,v in existing.items() if k in schema['properties']}
    for field in schema.get('required',[]):
        if field in samples:values[field]=samples[field]
    for field in ['name','description','router_id','log','exec_timeout_seconds','peer_group']:
        if field in schema['properties'] and field in samples:values[field]=samples[field]
    if vendor=='juniper' and 'isis' in op:values['interface']='ge-0/0/5.0'
    if op=='configure_loopback_interface':values['interface']={'cisco':'Loopback10','juniper':'lo0.10','huawei':'LoopBack10'}[vendor]
    # Fixture authoring selects only an explicitly allowed enum. This never
    # coerces a real user's request or broadens the published schema.
    for field,rule in schema['properties'].items():
        if field in values and rule.get('enum') and values[field] not in rule['enum']:values[field]=rule['enum'][0]
    return values
