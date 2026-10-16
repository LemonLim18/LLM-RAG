"""Build editable reference files, never runtime knowledge or published bindings.

Published CLI is retained, with explicitly labelled reference-only adaptations. New vendor translations are drafts
for manual engineering review and cannot enable verified generation.
"""
import json
from pathlib import Path
import sys
from hashlib import sha256

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))

JUNIPER={
 'modify_vlan':'{% if vlan_status == "suspend" %}deactivate{% else %}activate{% endif %} vlans {{ vlan_id }}',
 'rename_vlan':'rename vlans {{ old_vlan_name }} to {{ new_vlan_name }}',
 'configure_access_port':'set interfaces {{ interface }} unit 0 family ethernet-switching interface-mode access\nset interfaces {{ interface }} unit 0 family ethernet-switching vlan members {{ vlan_id }}',
 'configure_trunk_port':'set interfaces {{ interface }} unit 0 family ethernet-switching interface-mode trunk\n{% for vlan in allowed_vlans %}set interfaces {{ interface }} unit 0 family ethernet-switching vlan members {{ vlan }}\n{% endfor %}{% if native_vlan is defined %}set interfaces {{ interface }} native-vlan-id {{ native_vlan }}{% endif %}',
 'configure_loopback_interface':'set interfaces {{ interface }} unit 0 family inet address {{ address }}/{{ prefix_length }}\n{% if description is defined %}set interfaces {{ interface }} description "{{ description }}"{% endif %}',
 'configure_port_channel':'{% for member in member_interfaces %}set interfaces {{ member }} ether-options 802.3ad {{ aggregate_interface }}\n{% endfor %}set interfaces {{ aggregate_interface }} aggregated-ether-options lacp {{ lacp_mode }}',
 'enable_ospf_process':'set routing-options router-id {{ router_id }}\n{# Junos OSPF does not use an IOS process ID. Select a routing instance if needed. #}',
 'set_ospf_router_id':'set routing-options router-id {{ router_id }}',
 'create_ospf_area':'set protocols ospf area {{ area }} {{ area_type }}',
 'assign_interface_to_ospf_area':'set protocols ospf area {{ area }} interface {{ interface }}',
 'advertise_network':'{# Junos advertises connected interfaces via OSPF interface membership, not an IOS network statement. Resolve the supplied network_prefix to an interface. #}\nset protocols ospf area {{ area }} interface {{ ospf_interface }}',
 'configure_passive_interface':'{% if passive %}set{% else %}delete{% endif %} protocols ospf area {{ ospf_area }} interface {{ interface }} passive',
 'configure_ospf_redistribution':'set policy-options policy-statement {{ route_policy }} term EXPORT from protocol {{ "direct" if redistribution_source == "connected" else redistribution_source }}\nset policy-options policy-statement {{ route_policy }} term EXPORT then metric {{ ospf_metric }}\nset policy-options policy-statement {{ route_policy }} term EXPORT then external type {{ metric_type }}\nset policy-options policy-statement {{ route_policy }} term EXPORT then accept\nset protocols ospf export {{ route_policy }}',
 'create_acl':'set firewall family inet filter {{ acl_name }} interface-specific\n{# Review default term and stateless/stateful policy requirements before adding rules. #}',
 'add_acl_rule':'set firewall family inet filter {{ acl_name }} term RULE_{{ acl_rule_id }} from source-address {{ source_prefix }}\nset firewall family inet filter {{ acl_name }} term RULE_{{ acl_rule_id }} from destination-address {{ destination_prefix }}\n{% if ip_protocol != "ip" %}set firewall family inet filter {{ acl_name }} term RULE_{{ acl_rule_id }} from protocol {{ ip_protocol }}\n{% endif %}{% if source_port is defined and source_port is not none %}set firewall family inet filter {{ acl_name }} term RULE_{{ acl_rule_id }} from source-port {{ source_port }}\n{% endif %}{% if destination_port is defined and destination_port is not none %}set firewall family inet filter {{ acl_name }} term RULE_{{ acl_rule_id }} from destination-port {{ destination_port }}\n{% endif %}set firewall family inet filter {{ acl_name }} term RULE_{{ acl_rule_id }} then {{ "accept" if acl_action == "permit" else "discard" }}',
 'delete_acl_rule':'delete firewall family inet filter {{ acl_name }} term RULE_{{ acl_rule_id }}',
 'apply_acl_to_interface':'set interfaces {{ interface }} unit 0 family inet filter {{ "input" if direction in ["in","input","inbound"] else "output" }} {{ acl_name }}',
 'create_qos_policy':'{% for term in policy_terms %}set class-of-service schedulers {{ policy_name }}_{{ term.classifier_name }} transmit-rate {{ term.bandwidth_bps }}\nset class-of-service scheduler-maps {{ policy_name }} forwarding-class {{ term.classifier_name }} scheduler {{ policy_name }}_{{ term.classifier_name }}\n{% endfor %}',
 'create_classifier':'{% for dscp in dscp_values %}set class-of-service classifiers dscp {{ classifier_name }} forwarding-class {{ forwarding_class }} loss-priority low code-points {{ dscp }}\n{% endfor %}',
 'classify_by_dscp':'{% for dscp in previous_dscp_values %}delete class-of-service classifiers dscp {{ classifier_name }} forwarding-class {{ forwarding_class }} loss-priority low code-points {{ dscp }}\n{% endfor %}{% for dscp in dscp_values %}set class-of-service classifiers dscp {{ classifier_name }} forwarding-class {{ forwarding_class }} loss-priority low code-points {{ dscp }}\n{% endfor %}',
 'configure_scheduler':'set class-of-service schedulers {{ policy_name }}_{{ classifier_name }} transmit-rate {{ bandwidth_bps }}\nset class-of-service scheduler-maps {{ policy_name }} forwarding-class {{ classifier_name }} scheduler {{ policy_name }}_{{ classifier_name }}',
 'configure_shaping':'set class-of-service interfaces {{ interface }} shaping-rate {{ rate_bps }}\n{# Confirm egress direction and platform shaping support. #}',
 'configure_policing':'set firewall policer {{ policy_name }} if-exceeding bandwidth-limit {{ rate_bps }}\nset firewall policer {{ policy_name }} if-exceeding burst-size-limit {{ burst_bytes }}\nset firewall policer {{ policy_name }} then discard\n{# Attach via a reviewed firewall filter; review exceed_action and direction. #}',
 'apply_qos_policy_to_interface':'set class-of-service interfaces {{ interface }} scheduler-map {{ policy_name }}\n{# Scheduler maps are an egress concept; verify requested direction. #}',
 'configure_login_banner':'set system login message "{{ login_banner_text }}"',
 'configure_exec_timeout':'set system login class {{ login_class }} idle-timeout {{ exec_timeout_minutes }}\n{# Junos class timeout is in minutes; IOS seconds require an explicit policy decision. #}',
 'configure_login_lockout':'set system login retry-options tries-before-disconnect {{ login_failure_attempts }}\nset system login retry-options lockout-period {{ lockout_minutes }}\n{# Review seconds-to-minutes policy and failure-window semantics. #}',
}
HUAWEI={
 'modify_vlan':'vlan {{ vlan_id }}\n state {{ "suspend" if vlan_status == "suspend" else "active" }}\nquit',
 'rename_vlan':'vlan {{ vlan_id }}\n name {{ new_vlan_name }}\nquit',
 'configure_access_port':'interface {{ interface }}\n port link-type access\n port default vlan {{ vlan_id }}\nquit',
 'configure_trunk_port':'interface {{ interface }}\n port link-type trunk\n port trunk allow-pass vlan {{ allowed_vlans | join(" ") }}\n{% if native_vlan is defined %} port trunk pvid vlan {{ native_vlan }}\n{% endif %}quit',
 'configure_loopback_interface':'interface {{ interface }}\n ip address {{ address }} {{ netmask }}\n{% if description is defined %} description {{ description }}\n{% endif %}quit',
 'configure_port_channel':'interface {{ aggregate_interface }}\n mode lacp-static\nquit\n{% for member in member_interfaces %}interface {{ member }}\n eth-trunk {{ aggregate_id }}\nquit\n{% endfor %}{# Verify VRP LACP mode and aggregate numbering. #}',
 'add_default_route':'ip route-static 0.0.0.0 0.0.0.0 {{ next_hop }}{% if preference is defined %} preference {{ preference }}{% endif %}',
 'add_floating_static_route':'ip route-static {{ destination_address }} {{ destination_netmask }} {{ next_hop }} preference {{ preference }}',
 'enable_ospf_process':'ospf {{ process_id }} router-id {{ router_id }}\nquit',
 'set_ospf_router_id':'ospf {{ process_id }} router-id {{ router_id }}\nquit',
 'create_ospf_area':'ospf {{ process_id }}\n area {{ area }}\n  {{ area_type }}\n quit\nquit',
 'assign_interface_to_ospf_area':'interface {{ interface }}\n ospf enable {{ process_id }} area {{ area }}\nquit',
 'advertise_network':'ospf {{ process_id }}\n area {{ area }}\n  network {{ network_address }} {{ network_wildcard }}\n quit\nquit',
 'configure_passive_interface':'ospf {{ process_id }}\n {% if not passive %}undo {% endif %}silent-interface {{ interface }}\nquit',
 'configure_ospf_redistribution':'ospf {{ process_id }}\n import-route {{ "direct" if redistribution_source == "connected" else redistribution_source }} cost {{ ospf_metric }} type {{ metric_type }} route-policy {{ route_policy }}\nquit',
 'create_acl':'acl name {{ acl_name }} advance\n description {{ description }}\nquit',
 'add_acl_rule':'acl name {{ acl_name }} advance\n rule {{ acl_rule_id }} {{ acl_action }} {{ ip_protocol }} source {{ source_address }} {{ source_wildcard }} destination {{ acl_destination_address }} {{ acl_destination_wildcard }}{% if source_port is defined and source_port is not none %} source-port eq {{ source_port }}{% endif %}{% if destination_port is defined and destination_port is not none %} destination-port eq {{ destination_port }}{% endif %}\nquit',
 'delete_acl_rule':'acl name {{ acl_name }} advance\n undo rule {{ acl_rule_id }}\nquit',
 'apply_acl_to_interface':'interface {{ interface }}\n traffic-filter {{ "inbound" if direction in ["in","input","inbound"] else "outbound" }} acl name {{ acl_name }}\nquit',
 'create_qos_policy':'traffic policy {{ policy_name }}\n{% for term in policy_terms %} classifier {{ term.classifier_name }} behavior {{ term.classifier_name }}\n{% endfor %}quit\n{# Create/review referenced traffic behaviors and bandwidth actions separately. #}',
 'create_classifier':'traffic classifier {{ classifier_name }} operator {{ "and" if match_mode == "all" else "or" }}\n if-match dscp {{ dscp_values | join(" ") }}\nquit',
 'classify_by_dscp':'traffic classifier {{ classifier_name }}\n{% for dscp in previous_dscp_values %} undo if-match dscp {{ dscp }}\n{% endfor %} if-match dscp {{ dscp_values | join(" ") }}\nquit',
 'configure_scheduler':'traffic behavior {{ classifier_name }}\n queue af bandwidth {{ bandwidth_kbps }}\nquit\ntraffic policy {{ policy_name }}\n classifier {{ classifier_name }} behavior {{ classifier_name }}\nquit',
 'configure_shaping':'interface {{ interface }}\n qos lr {{ direction }} cir {{ rate_kbps }}\nquit\n{# VRP command and rate units vary; review interface/platform syntax. #}',
 'configure_policing':'traffic behavior {{ policy_name }}\n car cir {{ rate_kbps }} cbs {{ burst_bytes }} green pass red {{ exceed_action }}\nquit\n{# Review classifier attachment and policy direction. #}',
 'apply_qos_policy_to_interface':'interface {{ interface }}\n traffic-policy {{ policy_name }} {{ "inbound" if direction in ["in","input","inbound"] else "outbound" }}\nquit',
 'configure_login_banner':'header login information %{{ login_banner_text }}%',
 'configure_exec_timeout':'user-interface vty 0 4\n idle-timeout {{ exec_timeout_minutes }} {{ exec_timeout_seconds | default(0) }}\nquit',
 'configure_login_lockout':'user-interface vty 0 4\n authentication-mode aaa\nquit\n{# VRP login-failure lockout is AAA/domain/platform dependent. Fill the reviewed AAA policy; IOS failure-window semantics do not translate directly. #}\n{{ reviewed_aaa_lockout_commands }}',
}
for variants in [JUNIPER,HUAWEI]:
    variants['configure_trunk_allowed_vlans']=variants['configure_trunk_port']
    variants['modify_acl_rule']=variants['delete_acl_rule']+'\n'+variants['add_acl_rule']


def main():
    from llm.gateway_knowledge import read_release
    from jinja2 import Environment, meta
    release,manifest,pointer=read_release(ROOT/'backend/knowledge_workspace/storage/catalog_releases')
    operations=json.loads((release/'catalog/operations.json').read_text(encoding='utf-8'))
    # Management operations stay reference-only; do not copy isolated release data.
    extra=[('configure_login_banner','Login banner'),('configure_exec_timeout','Session idle timeout'),('configure_login_lockout','Login failure lockout')]
    for name,label in extra:
        if not any(op['operation_id']==name for op in operations): operations.append({'operation_id':name,'category_id':'management_plane_security','display_name':label})
    cisco_extra={'configure_login_banner':'banner login %{{ login_banner_text }}%',
        'configure_exec_timeout':'line vty 0 4\n exec-timeout {{ exec_timeout_minutes }} {{ exec_timeout_seconds | default(0) }}',
        'configure_login_lockout':'login block-for {{ login_block_seconds }} attempts {{ login_failure_attempts }} within {{ login_failure_window_seconds }}'}
    target=ROOT/'backend/ansible/reference/operation_drafts'
    rows=[]; env=Environment()
    for operation in operations:
        op=operation['operation_id']; category=operation['category_id']
        for vendor in ['cisco','juniper','huawei']:
            binding=next((b for b in manifest['template_bindings'] if b['operation_id']==op and b['vendor']==vendor),None)
            content=(release/binding['artifact_path']).read_text(encoding='utf-8') if binding else {'juniper':JUNIPER,'huawei':HUAWEI,'cisco':cisco_extra}[vendor][op]
            adapted=vendor=='cisco' and op=='configure_static_route'
            if adapted: content=content.replace('{{ destination }}','{{ destination_address }} {{ destination_mask }}')
            contract=json.loads(json.dumps(binding['input_contract'])) if binding else None
            if adapted: contract['derived'].update(destination_address='destination_address_v1',destination_mask='destination_mask_v1')
            path=target/category/op/(vendor+'.j2');path.parent.mkdir(parents=True,exist_ok=True)
            header='{# Editable reference draft: '+vendor+' / '+op+'. Verify syntax, dependencies and device suitability before use. #}\n'
            path.write_text(header+content+'\n',encoding='utf-8')
            variables=sorted(meta.find_undeclared_variables(env.parse(content)))
            rows.append({'operation_id':op,'category_id':category,'label':operation['display_name'],'vendor':vendor,
                'path':path.relative_to(ROOT/'backend/ansible').as_posix(),'variables':variables,
                'sha256':sha256(path.read_bytes()).hexdigest(),'status':'reference_draft',
                'source':'published_cli_adaptation' if adapted else 'published_cli_copy' if binding else 'new_translation_draft',
                'source_release':pointer['release_id'] if binding else None,
                'source_binding':binding['artifact_path'] if binding else None,
                'input_contract':contract,
                'verified_runtime_support':bool(binding),'version_certification':False})
    (target/'index.json').write_text(json.dumps({'format_version':1,'purpose':'Editable references; not a runtime operation catalog or publication.',
        'ordinary_release':pointer['release_id'],'operation_count':len(operations),'templates':rows},indent=2),encoding='utf-8')
    print(json.dumps({'operation_count':len(operations),'vendor_templates':len(rows),'published_copies':sum(r['source']=='published_cli_copy' for r in rows),'new_translation_drafts':sum(r['source']=='new_translation_draft' for r in rows),'published':False}))


if __name__=='__main__': main()
