"""Optional reviewed output variants; native V9 contracts remain authoritative."""
import asyncio
import json
import re

from fastapi import HTTPException
from jinja2 import StrictUndefined, meta
from jinja2.sandbox import SandboxedEnvironment
from pydantic import Field

from llm.gateway_models import StrictModel, text_digest


class PlaybookVariant(StrictModel):
    id: str = Field(pattern='^[a-z][a-z0-9_-]{0,79}$')
    operation_id: str = Field(min_length=1,max_length=100)
    operation_version: int = Field(ge=1)
    vendor: str = Field(pattern='^(cisco|juniper|huawei)$')
    platform: str = Field(min_length=1,max_length=50)
    versions: list[str] = Field(min_length=1,max_length=30)
    module_fqcns: list[str] = Field(min_length=1,max_length=20)
    connection_plugin: str = Field(min_length=1,max_length=150)
    platform_plugin: str = Field(min_length=1,max_length=150)
    dependencies: dict[str,str] = Field(min_length=1,max_length=30)
    template: str = Field(min_length=1,max_length=100000)
    fixture_parameters: dict
    fixture_host: str = Field(default='validation_target',pattern='^[a-zA-Z0-9_.-]+$')
    expected_fixture_yaml: str = Field(min_length=1,max_length=100000)
    compatibility_evidence: str = Field(min_length=20,max_length=100000)


def validate_variant(value, operations):
    """Draft checks do not imply lint, platform compatibility or device testing."""
    variant=PlaybookVariant.model_validate(value)
    operation=next((o for o in operations if o['operation_id']==variant.operation_id),None)
    if not operation or operation['version']!=variant.operation_version:
        raise ValueError('Variant must reference an existing operation and its exact current version')
    for name in [*variant.module_fqcns,variant.connection_plugin,variant.platform_plugin,*variant.dependencies]:
        if not re.fullmatch(r'[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,3}',name):
            raise ValueError('Use fully qualified module, plugin and collection names')
        if name.startswith('community.network.') or name=='community.network':
            raise ValueError('Deprecated community.network is read-only legacy reference material')
    if any(not re.fullmatch(r'\d+\.\d+\.\d+(?:[a-z0-9.+-]*)?',v) for v in variant.dependencies.values()):
        raise ValueError('Collection dependencies require exact pinned versions')
    if variant.vendor=='huawei' and not variant.platform_plugin.startswith(('huaweidatacom.','ansible.netcommon.','cognishield.')):
        raise ValueError('Huawei requires a reviewed explicit platform adapter')
    if re.search(r'\{%-?\s*(include|import|from|extends)\b|\blookup\s*\(|\bquery\s*\(|__[A-Za-z]',variant.template):
        raise ValueError('External template loading and runtime helpers are not permitted')
    env=SandboxedEnvironment(undefined=StrictUndefined,autoescape=False)
    parsed=env.parse(variant.template)
    allowed=set(variant.fixture_parameters)|{'target_host','native_configuration'}
    if meta.find_undeclared_variables(parsed)-allowed:
        raise ValueError('Template has undeclared inputs outside the operation fixture')
    return variant


def render_template(variant,parameters,host,native):
    import yaml
    output=SandboxedEnvironment(undefined=StrictUndefined,autoescape=False).from_string(variant.template).render(**parameters,target_host=host,native_configuration=native)
    play=yaml.safe_load(output)
    if not isinstance(play,list) or not play or any(not isinstance(p,dict) or p.get('hosts') not in [host,[host]] for p in play):
        raise ValueError('Playbooks must target exactly the resolved inventory hostname')
    from config_engine.safety import _scan_patterns, _DANGEROUS_PLAYBOOK_PATTERNS
    if _scan_patterns(output,_DANGEROUS_PLAYBOOK_PATTERNS):
        raise ValueError('Playbook failed structural safety checks')
    task_modules=[]
    for p in play:
        if set(p)-{'name','hosts','gather_facts','connection','vars','tasks','tags'}:
            raise ValueError('Use the reviewed task-only playbook subset')
        variables=p.get('vars') or {}
        if p.get('gather_facts') is not False or variables.get('ansible_connection',p.get('connection'))!=variant.connection_plugin or variables.get('ansible_network_os')!=variant.platform_plugin:
            raise ValueError('Playbook must declare the reviewed connection/platform plugins and disable fact gathering')
        for task in p.get('tasks',[]):
            if not isinstance(task,dict): raise ValueError('Invalid playbook task')
            keys=set(task)-{'name','when','register','changed_when','failed_when','loop','loop_control','vars','no_log','tags','notify'}
            if len(keys)!=1 or next(iter(keys)) not in variant.module_fqcns:
                raise ValueError('Task module is outside the reviewed variant module allowlist')
            task_modules.extend(keys)
    if not task_modules: raise ValueError('Playbook has no reviewed module tasks')
    return output


async def render_playbook(output,task):
    from llm.gateway_knowledge import read_release
    from local_providers.knowledge import knowledge_root
    from llm.gateway_validation import validate_ansible
    release,manifest,pointer=read_release(knowledge_root()/'storage/catalog_releases')
    if pointer['release_id']!=output['release_id']:
        raise HTTPException(409,'Knowledge changed; start a fresh preview')
    device=task['target_devices'][0]
    matches=[v for v in manifest.get('cognishield_playbooks',{}).get('variants',[]) if
        v['operation_id']==task['operation_id'] and v['vendor']==device['vendor'] and v['platform']==device['platform'] and device['version'] in v['versions']]
    if len(matches)!=1:
        raise HTTPException(422,'No unique verified Ansible variant exists for this operation/device version. Native generation remains independent.')
    metadata=matches[0]
    file=(release/metadata['artifact_path']).resolve()
    if not file.is_relative_to(release) or metadata['artifact_path'] not in manifest['artifacts']:
        raise HTTPException(422,'Playbook variant is not integrity registered')
    variant=PlaybookVariant.model_validate(json.loads(file.read_text()))
    content=render_template(variant,task['parameters'],device['hostname'],task['configs'][0]['configuration'])
    report=await asyncio.to_thread(validate_ansible,content, {'module':variant.module_fqcns,
        'connection':[variant.connection_plugin], 'cliconf' if variant.connection_plugin.endswith('network_cli') else 'netconf':[variant.platform_plugin]})
    if report['status']!='passed' or any(report.get('dependencies',{}).get(k)!=v for k,v in variant.dependencies.items()):
        raise HTTPException(422,{'message':'Ansible output is unavailable until pinned syntax/lint validation passes','validation':report})
    return content,{**report,'scope':'syntax_lint_and_reviewed_fixture','compatibility_evidence_sha256':text_digest(variant.compatibility_evidence),
        'required_plugins':{'module':variant.module_fqcns,'connection':[variant.connection_plugin], 'cliconf' if variant.connection_plugin.endswith('network_cli') else 'netconf':[variant.platform_plugin]},
        'knowledge_release':pointer['release_id'],'device_testing':'not_run','deployment_authorized':False}


async def combine_playbooks(drafts):
    """Preserve each reviewed play's host, variables and task order; validate the whole result."""
    import yaml
    from llm.gateway_validation import validate_ansible
    plays, dependencies, plugins = [], {}, {}
    for draft in drafts:
        value=yaml.safe_load(draft['content'])
        if not isinstance(value,list) or not value:
            raise HTTPException(422,'Every output variant must contain a nonempty play list')
        plays.extend(value)
        report=draft['validation']
        if report.get('status')!='passed': raise HTTPException(422,'An unvalidated variant cannot be combined')
        for key,version in report.get('dependencies',{}).items():
            if key in dependencies and dependencies[key]!=version:
                raise HTTPException(422,'The selected variants require incompatible pinned collection versions')
            dependencies[key]=version
        for kind,names in report.get('required_plugins',{}).items():
            plugins[kind]=sorted(set(plugins.get(kind,[]))|set(names))
    content=yaml.safe_dump(plays,sort_keys=False,allow_unicode=True)
    report=await asyncio.to_thread(validate_ansible,content,plugins)
    if report.get('status')!='passed' or any(report.get('dependencies',{}).get(k)!=v for k,v in dependencies.items()):
        raise HTTPException(422,{'message':'The combined playbook did not pass pinned syntax/lint validation','validation':report})
    return content,{**report,'scope':'combined_syntax_lint','required_plugins':plugins,'device_testing':'not_run','deployment_authorized':False}
