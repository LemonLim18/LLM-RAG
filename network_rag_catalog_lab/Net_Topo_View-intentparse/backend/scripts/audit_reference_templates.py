"""Read every reference against the verified ordinary release; never publish or activate."""
import json
from pathlib import Path
import sys
from hashlib import sha256
from collections import Counter
from jinja2 import Environment, meta

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from llm.gateway_knowledge import read_release

SOURCES={
 'junos_ospf':'https://www.juniper.net/documentation/us/en/software/junos/ospf/topics/topic-map/configuring-ospf-areas.html',
 'junos_policer':'https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/statement/policer-edit-firewall.html',
 'huawei_ansible':'https://docs.ansible.com/projects/ansible/latest/network/user_guide/platform_ce.html',
}
# Concrete semantic differences found in the existing translations. These are
# publication blockers, not guessed replacement commands or device certification.
ISSUES={
 ('juniper','modify_vlan'):'Junos identifies VLAN configuration by name; vlan_id alone does not resolve the existing VLAN name.',
 ('juniper','rename_vlan'):'Requires existing Junos VLAN name; the native VLAN-ID operation cannot infer it.',
 ('huawei','modify_vlan'):'IOS state active/suspend translation has no verified VRP implementation in this repository.',
 ('juniper','enable_ospf_process'):'Sets a global router ID only; does not establish OSPF area/interface membership or an IOS-like process.',
 ('juniper','advertise_network'):'Requires interface resolution from the network prefix; ospf_interface is an additional unverified input.',
 ('juniper','configure_passive_interface'):'Requires ospf_area context that is absent from the base operation contract.',
 ('juniper','configure_ospf_redistribution'):'Policy scope, source protocol and external metric semantics need a separate vendor contract.',
 ('huawei','configure_ospf_redistribution'):'References route-policy without creating/verifying it and lacks protocol-specific process mapping.',
 ('juniper','create_acl'):'An empty interface-specific filter does not implement the full ACL semantics; default action and attachment must be reviewed.',
 ('huawei','create_qos_policy'):'References traffic behaviors without defining/verifying their bandwidth actions.',
 ('juniper','create_qos_policy'):'Forwarding-class/queue definitions and scheduler-map attachment are dependencies, not inferred inputs.',
 ('juniper','configure_policing'):'Creates a policer but does not attach it; ignores requested exceed_action and direction.',
 ('huawei','configure_policing'):'Creates a behavior without classifier/policy/interface attachment; action mapping requires validation.',
 ('juniper','configure_shaping'):'Junos shaping is egress; a generic direction parameter cannot imply ingress shaping support.',
 ('huawei','configure_shaping'):'Direction tokens, units and qos lr availability require a VRP platform contract.',
 ('juniper','apply_qos_policy_to_interface'):'Scheduler map attachment is egress; requested ingress policy cannot be silently translated.',
 ('juniper','configure_exec_timeout'):'Junos login-class timeout uses minutes; IOS seconds and class membership need explicit handling.',
 ('juniper','configure_login_lockout'):'Disconnect attempts and lockout duration do not reproduce the IOS failure-window policy.',
 ('huawei','configure_login_lockout'):'Placeholder reviewed_aaa_lockout_commands is not an implementation of lockout semantics.',
 ('juniper','configure_port_channel'):'Aggregate device allocation and membership prerequisites are not established.',
 ('huawei','configure_port_channel'):'Hard-coded lacp-static ignores the requested LACP mode; aggregate ID mapping requires a contract.',
}


def audit():
    release,manifest,pointer=read_release(ROOT/'backend/knowledge_workspace/storage/catalog_releases')
    rows=json.loads((ROOT/'backend/ansible/reference/operation_drafts/index.json').read_text(encoding='utf-8'))['templates']
    env=Environment(); result=[]
    for row in rows:
        path=ROOT/'backend/ansible'/row['path']; text=path.read_text(encoding='utf-8')
        variables=sorted(meta.find_undeclared_variables(env.parse(text)))
        binding=next((b for b in manifest['template_bindings'] if b['operation_id']==row['operation_id'] and b['vendor']==row['vendor']),None)
        contract=row.get('input_contract') or {}
        declared=set(contract.get('fields',[]))|set(contract.get('derived',{}))|set(contract.get('optional_defaults',{}))
        undeclared=sorted(set(variables)-declared)
        blockers=[]; issue=ISSUES.get((row['vendor'],row['operation_id']))
        if issue: blockers.append(issue)
        if not contract: blockers.append('No reviewed vendor input contract, compatibility profile or validation evidence accompanies this draft.')
        elif undeclared: blockers.append('Unmapped template inputs: '+', '.join(undeclared))
        copied=bool(binding and row['source']=='published_cli_copy' and text.split('\n',1)[1].rstrip()==(release/binding['artifact_path']).read_text(encoding='utf-8').rstrip())
        if row['source']=='published_cli_adaptation': blockers.append('Reference-only static-route adaptation differs from active binding; requires a reviewed contract/version update.')
        if sha256(path.read_bytes()).hexdigest()!=row['sha256']: blockers.append('Reference digest differs from index.')
        if row['operation_id'] not in manifest['schemas']: blockers.append('Operation is absent from the ordinary release; isolated test knowledge is not adopted.')
        result.append({**{key:row[key] for key in ['operation_id','vendor','path','source']},
            'jinja_parse':'passed','hash_matches':sha256(path.read_bytes()).hexdigest()==row['sha256'],
            'published_copy_matches':copied,'template_variables':variables,'unmapped_inputs':undeclared,
            'runtime_native':'existing_published_binding' if binding else 'unsupported',
            'platform':binding['platform'] if binding else None,'versions':binding['versions'] if binding else [],
            'reference_review':'retained_published_copy' if copied and not blockers else 'requires_engineering_review',
            'publication_blockers':blockers,'semantic_certification':'not_established_by_this_audit',
            'ansible_variant':'unsupported_no_verified_variant','device_testing':'not_run',
            'sources':[SOURCES['junos_policer']] if row['vendor']=='juniper' and row['operation_id']=='configure_policing' else [SOURCES['junos_ospf']] if row['vendor']=='juniper' and 'ospf' in row['operation_id'] else []})
    return {'ordinary_release':pointer['release_id'],'operation_count':len({r['operation_id'] for r in result}),
        'template_count':len(result),'summary':dict(Counter(r['reference_review'] for r in result)),
        'publication':'Not performed: reference copies already exist in the ordinary release; remaining translations/adaptation lack verified contracts and semantic evidence.',
        'no_device_execution':True,'templates':result}


if __name__=='__main__':
    result=audit(); destination=ROOT/'docs/shared_ai_coverage/reference_template_audit.json'
    destination.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in result.items() if key!='templates'}))
