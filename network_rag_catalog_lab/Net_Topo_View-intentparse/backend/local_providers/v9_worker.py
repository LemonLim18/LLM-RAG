"""Read-only V9 process boundary. Input/output are JSON; no application storage."""
import json
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True


def protect_source(root):
    root = Path(root).resolve()
    def protect(event, args):
        paths = []
        if event == 'open':
            path, mode, flags = args
            if (flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                paths = [path]
        elif event in {'os.remove', 'os.rmdir', 'os.mkdir', 'os.rename', 'os.replace', 'os.chmod', 'os.utime', 'os.link', 'os.symlink'}:
            paths = args[:2] if event in {'os.rename', 'os.replace', 'os.link', 'os.symlink'} else args[:1]
        for path in paths:
            if isinstance(path, (str, bytes)) and Path(os.fsdecode(path)).resolve().is_relative_to(root):
                raise PermissionError('V9 sibling is read-only')
    sys.addaudithook(protect)
    sys.path.insert(0, str(root))


def main(payload):
    root = Path(payload['root']).resolve()
    protect_source(root)
    os.environ['NETWORK_RAG_RUNTIME'] = 'published'
    with tempfile.TemporaryDirectory(prefix='cognishield-v9-context-') as folder:
        context = Path(folder)
        (context / 'inventory').mkdir()
        (context / 'planned').mkdir()
        (context / 'inventory/devices.json').write_text(json.dumps(payload['inventory']), encoding='utf-8')
        (context / 'inventory/attributes.json').write_bytes((root / 'data/inventory/attributes.json').read_bytes())
        (context / 'planned/parameters.json').write_text('{"records":[]}', encoding='utf-8')
        import app.config as config
        if payload.get('releases'):
            config.CATALOG_RELEASES_DIR = Path(payload['releases'])
        config.DATA_DIR = context
        config.INVENTORY_FILE = context / 'inventory/devices.json'
        # Published schemas/templates stay in their immutable release. Only the
        # request's inventory/context is projected from CogniShield SQLite.
        from app.knowledge.runtime import active_snapshot, snapshot_scope
        snapshot = active_snapshot()
        if snapshot is None:
            raise ValueError('An active published V9 release is required; no source fallback.')
        from langchain_ollama import ChatOllama
        import app.llm as model_module
        engine = ChatOllama(model=payload['model'], base_url=payload['ollama_url'], temperature=0,
                            client_kwargs={'timeout': 45.0, 'trust_env': False})
        model_calls = {'succeeded':0, 'failed':0}
        class ObservedModel:
            temperature = 0
            def bind(self, **kwargs):
                bound = engine.bind(**kwargs)
                class Bound:
                    def invoke(self, *args, **values):
                        try:
                            response = bound.invoke(*args, **values)
                            model_calls['succeeded'] += 1
                            return response
                        except Exception:
                            model_calls['failed'] += 1
                            raise
                return Bound()
            def invoke(self, *args, **kwargs):
                try:
                    response = engine.invoke(*args, **kwargs)
                    model_calls['succeeded'] += 1
                    return response
                except Exception:
                    model_calls['failed'] += 1
                    raise
        model_module.llm = ObservedModel()
        # Configure V9's existing retriever only against the published owned index.
        from knowledge_lifecycle import configure_embeddings
        configure_embeddings()
        from app import pipeline
        if snapshot.manifest['retrieval']['mode'] == 'chroma':
            index = Path(snapshot.manifest['retrieval']['index_path']).resolve()
            if not payload.get('releases') or not index.is_relative_to(Path(payload['releases']).resolve().parent.parent):
                raise ValueError('Runtime retrieval requires a CogniShield-owned published index.')
        from app.planner.models import ExecutionPlan, PlannedTask, OperationIntent
        with snapshot_scope(snapshot):
            if payload.get('action') == 'reference_render':
                if payload['release_id']!=snapshot.release_id: raise ValueError('Published source changed. Reopen the review.')
                from jinja2 import StrictUndefined, meta
                from jinja2.sandbox import SandboxedEnvironment
                from app.templates.renderer import _prepare_context
                from app.knowledge.rule_registry import TEMPLATE_DERIVATIONS
                from app.parameters.validator import validate_parameter_result
                environment=SandboxedEnvironment(undefined=StrictUndefined,trim_blocks=False,lstrip_blocks=True)
                rendered=[]
                for item in payload['templates']:
                    params=item['parameters'];schema=snapshot.schema(item['operation_id'],item['device']['vendor'])
                    result=validate_parameter_result(params,schema)
                    if not result.valid: raise ValueError(item['operation_id']+': '+ '; '.join(issue.message for issue in result.issues))
                    contract=item['input_contract'] or {'optional_defaults':{key:None for key in schema.get('properties',{}) if key not in schema.get('required',[])},
                        'derived':{key:spec[0] for key,spec in TEMPLATE_DERIVATIONS.items() if spec[1] in params}}
                    context=_prepare_context(params,contract)
                    variables=meta.find_undeclared_variables(environment.parse(item['template']))
                    extra=item.get('extra',{})
                    if set(extra).intersection(context): raise ValueError('Reference-only values cannot override reviewed operation parameters.')
                    if set(extra)-variables: raise ValueError('Unrecognized reference-only input.')
                    context.update(extra)
                    missing=sorted(variables-set(context))
                    if missing: raise ValueError(item['operation_id']+' needs manual reference values: '+', '.join(missing))
                    content=environment.from_string(item['template']).render(**context).strip()+'\n'
                    if len(content)>100000: raise ValueError('Reference output limit exceeded.')
                    rendered.append({'task_id':item['task_id'],'operation_id':item['operation_id'],'device':item['device'],'content':content})
                snapshot.assert_active()
                return {'documents':rendered,'release_id':snapshot.release_id,'validation_scope':'unvalidated_reference_draft'}
            if payload.get('action') == 'document_edit':
                from app import document_edits
                from app.parameters.validator import validate_parameter_result
                from app.devices.context_validator import validate_device_context
                device = next((d for d in payload['inventory'] if d['id']==payload['device_id']), None)
                if not device or device['vendor']!='cisco' or device['platform']!='iosxe':
                    raise ValueError('This reviewed operation-aware editor supports IOS-XE VLAN rename only; no general native rewrite was substituted.')
                schema = snapshot.schema('rename_vlan','cisco')
                interpreted = document_edits.interpret(payload['prompt'],schema,device,payload['content'])
                if interpreted.outcome!='edit' or interpreted.operation_id!='rename_vlan':
                    raise ValueError('State one existing VLAN ID and its new name; other native edits require a verified adapter.')
                params = {k:getattr(interpreted,k) for k in ('vlan_id','new_vlan_name')}
                if not validate_parameter_result(params,schema).valid:
                    raise ValueError('VLAN rename parameters do not satisfy the published schema. Specify the VLAN ID and exact new name.')
                if not all(document_edits.literal(v,payload['prompt']) for v in params.values()):
                    raise ValueError('VLAN rename values must match the instruction exactly. Quote the new name without trailing punctuation, for example: rename VLAN 100 to "ENGINEERING".')
                if interpreted.target and interpreted.target not in {device['hostname'],device['id']}:
                    raise ValueError('The edit instruction targets a different or ambiguous device.')
                if validate_device_context('rename_vlan','vlan',params,[device]):
                    raise ValueError('V9 device context rejects this edit.')
                proposed, old = document_edits.proposed_text(payload['content'],params,device)
                if interpreted.current_vlan_name and interpreted.current_vlan_name!=old:
                    raise ValueError('The requested old name does not match the current buffer.')
                snapshot.assert_active()
                return {'proposed_content':proposed,'release_id':snapshot.release_id,'model':payload['model'],
                    'validation':'bounded_operation_only','operation_id':'rename_vlan','parameters':params}
            if payload.get('plan'):
                raw = dict(payload['plan'])
                raw['tasks'] = [PlannedTask(**task) for task in raw['tasks']]
                raw['intents'] = [OperationIntent(**intent) for intent in raw['intents']]
                plan = ExecutionPlan(**raw)
                if plan.knowledge_snapshot_id != snapshot.release_id:
                    raise ValueError('Published release changed. Start a fresh preview.')
            else:
                plan = pipeline.run(payload['prompt'], verbose=False)
            if payload.get('selection') is not None:
                if not payload.get('allow_multi') or not payload.get('plan'):
                    raise ValueError('Selections require an existing shared review.')
                entries=payload['selection']
                if len(entries)>24: raise ValueError('At most 24 operation/device bindings are allowed.')
                from uuid import uuid4
                identities=set(); tasks=[]; intents=[]
                for entry in entries:
                    operation=snapshot.service.get_operation(entry['operation_id'])
                    identity=entry.get('task_id') or 'review-'+uuid4().hex
                    if identity in identities: raise ValueError('Duplicate review task identity.')
                    identities.add(identity)
                    host=entry.get('target_host','')
                    devices=[d for d in payload['inventory'] if d['hostname']==host]
                    if host and len(devices)!=1: raise ValueError('Choose an existing inventory target.')
                    template=entry.get('template_id')
                    if template:
                        if not devices or snapshot.binding(devices[0],operation.operation_id)['artifact_path']!=template:
                            raise ValueError('The selected published template does not match the operation and target.')
                    parameters=entry.get('parameters',{})
                    task=pipeline._finalize_task(intent_id=identity,request_text='Explicit review: '+operation.operation_id,
                        category=operation.category_id,operation_id=operation.operation_id,parameters=parameters,
                        parameter_provenance={k:'review_user' for k in parameters},target_refs=[host] if host else [])
                    tasks.append(task)
                    intents.append(OperationIntent(identity,task.request_text,target_refs=[host] if host else []))
                plan.tasks=tasks; plan.intents=intents
                # Confirmations and artifacts are rebuilt by V9, never accepted from the client.
                payload['hosts']=[]; payload['corrections']={}; payload['task_id']=None
            multi = bool(payload.get('allow_multi'))
            if not multi and len(plan.tasks) != 1:
                raise ValueError('This legacy endpoint supports one operation and one target; use shared Studio for the complete request.')
            if (not plan.tasks and payload.get('selection') is None) or len(plan.tasks) > 24:
                raise ValueError('Review between 1 and 24 operation/device bindings per request.')
            task_id = payload.get('task_id')
            selected = next((t for t in plan.tasks if t.intent_id == task_id), None) if task_id else (plan.tasks[0] if len(plan.tasks) == 1 else None)
            if (payload.get('hosts') or payload.get('corrections')) and selected is None:
                raise ValueError('Select a task before correcting its target or parameters.')
            if task_id and selected is None:
                raise ValueError('This task no longer exists in the reviewed plan.')
            if selected:
                index = plan.tasks.index(selected)
                if payload.get('hosts') and sorted(payload['hosts']) != sorted(d['hostname'] for d in selected.target_devices):
                    selected = pipeline.correct_task(selected, 'target_refs', ', '.join(payload['hosts']))
                    if selected.feedback: raise ValueError(selected.feedback)
                for path, value in payload.get('corrections', {}).items():
                    selected = pipeline.correct_task(selected, path, json.dumps(value) if not isinstance(value, str) else value)
                    if selected.feedback: raise ValueError(selected.feedback)
                plan.tasks[index] = selected
            pipeline.refresh_plan(plan)
            if payload.get('confirm_order'):
                pipeline.confirm_order(plan)
            if len(plan.tasks) > 24:
                raise ValueError('The request resolves to more than 24 bindings. Narrow its scope.')
            if not multi and len(plan.tasks) != 1:
                raise ValueError('Multiple target bindings require shared Studio review.')
            schemas, metadata, references = {}, {}, {}
            for task in plan.tasks:
                targets = task.target_devices
                schemas[task.intent_id] = snapshot.schema(task.operation_id, targets[0]['vendor'] if targets else None) if task.operation_id else {'properties': {}}
                if targets and task.operation_id:
                    try:
                        binding = snapshot.binding(targets[0], task.operation_id)
                        source = (snapshot.root / binding['artifact_path']).read_text(encoding='utf-8')
                        from artifact_metadata import artifact_metadata
                        metadata[task.intent_id] = artifact_metadata(source)
                        references[task.intent_id] = {'path': binding['artifact_path'], 'content': source, 'release_id': snapshot.release_id}
                    except (ValueError, KeyError, FileNotFoundError):
                        pass  # V9 retains the unsupported-binding issue; never invent a template.
            snapshot.assert_active()
            first = plan.tasks[0].intent_id if plan.tasks else ''
            return {'artifact_metadata': metadata.get(first), 'task_artifacts': metadata, 'task_references': references,
                    'plan': pipeline.plan_to_dict(plan), 'schema': schemas.get(first, {'properties':{}}), 'schemas': schemas, 'allow_multi': multi,
                    'release_id': snapshot.release_id, 'manifest_sha256': snapshot._manifest_hash, 'retrieval': snapshot.manifest['retrieval'], 'model_calls':model_calls}



if __name__ == '__main__':
    try:
        print(json.dumps({'ok': True, **main(json.load(sys.stdin))}))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
