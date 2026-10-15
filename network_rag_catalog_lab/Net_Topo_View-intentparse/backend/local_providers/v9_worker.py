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
            if payload.get('plan'):
                raw = dict(payload['plan'])
                raw['tasks'] = [PlannedTask(**task) for task in raw['tasks']]
                raw['intents'] = [OperationIntent(**intent) for intent in raw['intents']]
                plan = ExecutionPlan(**raw)
                if plan.knowledge_snapshot_id != snapshot.release_id:
                    raise ValueError('Published release changed. Start a fresh preview.')
            else:
                plan = pipeline.run(payload['prompt'], verbose=False)
            if len(plan.tasks) != 1:
                raise ValueError('Studio currently supports one operation and one target per reviewed job; no tasks were discarded.')
            task = plan.tasks[0]
            if payload.get('hosts') and sorted(payload['hosts']) != sorted(d['hostname'] for d in task.target_devices):
                task = pipeline.correct_task(task, 'target_refs', ', '.join(payload['hosts']))
                if task.feedback:
                    raise ValueError(task.feedback)
            for path, value in payload.get('corrections', {}).items():
                task = pipeline.correct_task(task, path, json.dumps(value) if not isinstance(value, str) else value)
                if task.feedback:
                    raise ValueError(task.feedback)
            plan.tasks = [task]
            pipeline.refresh_plan(plan)
            if len(plan.tasks) != 1:
                raise ValueError('Multiple target bindings are not supported by this first Studio milestone.')
            for device in plan.tasks[0].target_devices:
                if device['vendor'] != 'cisco' or device['platform'] != 'iosxe':
                    raise ValueError('This Studio Ansible output adapter supports Cisco IOS-XE only.')
            if not plan.tasks[0].operation_id:
                raise ValueError(plan.tasks[0].feedback or 'V9 could not resolve a published operation.')
            schema = snapshot.schema(plan.tasks[0].operation_id, 'cisco')
            metadata = None
            task = plan.tasks[0]
            if task.configs:
                binding = snapshot.binding(task.target_devices[0], task.operation_id)
                from artifact_metadata import artifact_metadata
                metadata = artifact_metadata((snapshot.root / binding['artifact_path']).read_text(encoding='utf-8'))
            return {'artifact_metadata': metadata, 'plan': pipeline.plan_to_dict(plan), 'schema': schema,
                    'release_id': snapshot.release_id, 'manifest_sha256': snapshot._manifest_hash, 'retrieval': snapshot.manifest['retrieval'], 'model_calls':model_calls}


if __name__ == '__main__':
    try:
        print(json.dumps({'ok': True, **main(json.load(sys.stdin))}))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
