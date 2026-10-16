"""Hosting conveniences around V9's publisher and verified immutable snapshots."""
import json
import os
import re
import shutil
from hashlib import sha256
from pathlib import Path
from uuid import uuid4


def configure_embeddings():
    from langchain_ollama import OllamaEmbeddings
    import app.config as config
    import app.embeddings as module
    config.OLLAMA_EMBED_MODEL = os.getenv('COGNISHIELD_KNOWLEDGE_EMBED_MODEL', 'nomic-embed-text')
    module.embeddings = OllamaEmbeddings(model=config.OLLAMA_EMBED_MODEL,
        base_url=os.getenv('COGNISHIELD_LOCAL_OLLAMA_URL', 'http://127.0.0.1:11434'),
        client_kwargs={'timeout': 120, 'trust_env': False})


def pointer_for(root, identity):
    from app.knowledge.runtime import KnowledgeSnapshot
    if not re.fullmatch(r'[a-f0-9]{32}', identity):
        raise ValueError('Invalid release identity.')
    pointer = {'release_id': identity, 'manifest_sha256': sha256((root / identity / 'manifest.json').read_bytes()).hexdigest()}
    return pointer, KnowledgeSnapshot(root, pointer)


def release_rows(root):
    from app.knowledge.runtime import active_pointer
    active = active_pointer(root)
    rows = []
    for folder in root.iterdir():
        if not re.fullmatch(r'[a-f0-9]{32}', folder.name):
            continue
        _, snapshot = pointer_for(root, folder.name)
        m = snapshot.manifest
        rows.append({'release_id': folder.name, 'status': 'Active' if active and active['release_id']==folder.name else 'Available',
            'published_at': m['created_at'], 'published_by': m['actor'], 'reason': m['reason'],
            'authoring_revision': m['authoring_revision'], 'retrieval': m['retrieval'],
            'objects': len(m['schemas']) + len(m['template_bindings'])})
    return sorted(rows, key=lambda row: row['published_at'], reverse=True)


def build(base, releases, body, actor):
    """Let V9 publish in a private staging root; promote only its verified package."""
    from app.knowledge.publication import publish, _publication_lock
    from app.knowledge.runtime import active_pointer
    from app.knowledge.authoring_store import AuthoringError
    configure_embeddings()
    before = active_pointer(releases)
    if (before or {}).get('release_id') != body['expected_release']:
        raise AuthoringError('STALE_REVISION', 'Active release changed; refresh before building.')
    staging = base / ('.b-' + uuid4().hex[:6])
    staging.mkdir()
    try:
        # The previous immutable package is required for V9's version-change checks.
        if before:
            _, old = pointer_for(releases, before['release_id'])
            shutil.copytree(old.root, staging / old.release_id)
            (staging / 'active.json').write_text(json.dumps(before), encoding='utf-8')
        snapshot = publish(base_dir=base, releases_dir=staging, mode=body.get('mode', 'chroma'),
            expected_release=body['expected_release'], expected_revision=body['expected_revision'],
            actor=actor, reason=body['reason'])
        snapshot = freeze_playbook_variants(base, staging, snapshot, body['expected_revision'])
        with _publication_lock(releases):
            if active_pointer(releases) != before:
                raise AuthoringError('STALE_REVISION', 'Active release changed during build; package was not promoted.')
            snapshot.root.rename(releases / snapshot.release_id)
        return snapshot.release_id
    finally:
        # Only our unique staging directory, within this workspace, is removed.
        if staging.resolve().parent == base.resolve() and staging.name.startswith('.b-'):
            shutil.rmtree(staging)


def freeze_playbook_variants(base, releases, snapshot, expected_revision):
    """Optional owned extension, finalized only in unpublished staging packages."""
    import yaml
    from app.knowledge.authority import authoring_store
    from app.knowledge.authoring_store import authoring_lock
    from app.knowledge.runtime import KnowledgeSnapshot
    from llm.gateway_playbooks import validate_variant, render_template
    from llm.gateway_validation import validate_ansible
    with authoring_lock(base):
        draft=authoring_store(base).snapshot()
        if draft['revision']!=expected_revision:
            raise ValueError('Authoring changed during build; package was not promoted')
        sources={k:v for k,v in draft['sources'].items() if k.startswith('cognishield/playbooks/')}
        if not sources: return snapshot
        manifest=snapshot.manifest
        variants=[]
        for raw in sources.values():
            variant=validate_variant(json.loads(raw),draft['catalogs']['operations'])
            eligible=[b for b in manifest['template_bindings'] if b['operation_id']==variant.operation_id and b['vendor']==variant.vendor and b['platform']==variant.platform and set(variant.versions)<=set(b['versions'])]
            if len(eligible)!=1: raise ValueError('Playbook variant requires one exact reviewed native binding')
            from jinja2.sandbox import SandboxedEnvironment
            from jinja2 import StrictUndefined
            binding=eligible[0]
            from jsonschema import Draft202012Validator, FormatChecker
            Draft202012Validator(snapshot.schema(variant.operation_id,variant.vendor),format_checker=FormatChecker()).validate(variant.fixture_parameters)
            native=SandboxedEnvironment(undefined=StrictUndefined).from_string((snapshot.root/binding['artifact_path']).read_text()).render(**{**binding['input_contract'].get('optional_defaults',{}),**variant.fixture_parameters})
            rendered=render_template(variant,variant.fixture_parameters,variant.fixture_host,native)
            if yaml.safe_load(rendered)!=yaml.safe_load(variant.expected_fixture_yaml):
                raise ValueError('Rendered playbook differs from the reviewed platform fixture')
            report=validate_ansible(rendered, {'module':variant.module_fqcns, 'connection':[variant.connection_plugin],
                'cliconf' if variant.connection_plugin.endswith('network_cli') else 'netconf':[variant.platform_plugin]})
            if report['status']!='passed' or any(report.get('dependencies',{}).get(k)!=v for k,v in variant.dependencies.items()):
                raise ValueError('Playbook publication requires contained syntax/lint validation with matching pinned dependencies')
            artifact='studio/playbooks/'+variant.id+'.json'
            target=snapshot.root/artifact;target.parent.mkdir(parents=True,exist_ok=True)
            data=variant.model_dump_json().encode('utf-8');target.write_bytes(data)
            manifest['artifacts'][artifact]=sha256(data).hexdigest()
            variants.append({'id':variant.id,'operation_id':variant.operation_id,'operation_version':variant.operation_version,
                'vendor':variant.vendor,'platform':variant.platform,'versions':variant.versions,'artifact_path':artifact,
                'compatibility':'reviewed_offline_fixture','device_testing':'not_run','validation':report})
        manifest['cognishield_playbooks']={'format_version':1,'variants':variants}
        (snapshot.root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        pointer={'release_id':snapshot.release_id,'manifest_sha256':sha256((snapshot.root/'manifest.json').read_bytes()).hexdigest()}
        verified=KnowledgeSnapshot(releases,pointer)
        (releases/'active.json').write_text(json.dumps(pointer),encoding='utf-8')
        return verified


def activate(base, releases, body, actor):
    from app.knowledge.publication import _publication_lock
    from app.knowledge.runtime import active_pointer
    from app.knowledge.authoring_store import AuthoringError, authoring_lock
    from app.knowledge.authority import authoring_store
    with _publication_lock(releases), authoring_lock(base):
        previous = active_pointer(releases)
        if (previous or {}).get('release_id') != body['expected_release']:
            raise AuthoringError('STALE_REVISION', 'Active release changed; refresh before activation.')
        pointer, snapshot = pointer_for(releases, body['release_id'])
        retrieval = snapshot.manifest['retrieval']
        if retrieval['mode'] == 'chroma':
            # Verify the actual index as well as the frozen release files before switching.
            configure_embeddings()
            from langchain_chroma import Chroma
            import app.embeddings as module
            index = Path(retrieval['index_path']).resolve()
            if not index.is_relative_to(base.resolve()):
                raise ValueError('Retrieval index must belong to this knowledge workspace.')
            vs = Chroma(collection_name=retrieval['collection'], persist_directory=str(index),
                embedding_function=module.embeddings, create_collection_if_not_exists=False)
            stored = vs.get(include=['documents', 'metadatas'])
            expected = {r['id']:r for r in snapshot.read_json('retrieval_documents.json')}
            if set(stored['ids']) != set(expected):
                raise ValueError('Release retrieval index is incomplete.')
            for identity, text, metadata in zip(stored['ids'], stored['documents'], stored['metadatas']):
                if text != expected[identity]['page_content'] or metadata != expected[identity]['metadata']:
                    raise ValueError('Release retrieval index integrity failed.')
        # Persist an intent record first; active.json is the sole runtime authority.
        # A crash leaves an inspectable intent, never a partially written pointer.
        store = authoring_store(base)
        with store._connection() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS cognishield_release_events (id INTEGER PRIMARY KEY, release_id TEXT NOT NULL, previous_release TEXT, actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
            connection.execute('INSERT INTO cognishield_release_events(release_id,previous_release,actor,reason) VALUES (?,?,?,?)',
                (snapshot.release_id, (previous or {}).get('release_id'), actor, body['reason']))
        temporary = releases / ('.active-' + uuid4().hex + '.tmp')
        temporary.write_text(json.dumps(pointer), encoding='utf-8')
        temporary.replace(releases / 'active.json')
    return snapshot.release_id


def validate_preset(parameter):
    """Presets are copied explicitly to operation rules, not implicit global policy."""
    from jsonschema import Draft202012Validator, FormatChecker
    preset = parameter.get('cognishield_preset')
    if preset is None:
        return
    allowed = {'minimum','maximum','minLength','maxLength','pattern','format','enum','default','minItems','maxItems','uniqueItems'}
    if not isinstance(preset, dict) or set(preset) - allowed:
        raise ValueError('Unsupported reusable parameter preset keyword.')
    for keys, types in [({'minimum','maximum'},{'number','integer'}),({'minLength','maxLength','pattern','format'},{'string'}),({'minItems','maxItems','uniqueItems'},{'array'})]:
        if keys.intersection(preset) and parameter['value_type'] not in types:
            raise ValueError('Preset constraints do not apply to this parameter type.')
    if 'format' in preset and preset['format'] not in FormatChecker.checkers:
        raise ValueError('Unsupported parameter format.')
    schema = {'type': parameter['value_type'], **preset}
    Draft202012Validator.check_schema(schema)
    for low, high in [('minimum','maximum'),('minLength','maxLength'),('minItems','maxItems')]:
        if low in preset and high in preset and preset[low] > preset[high]:
            raise ValueError(f'{low} must not exceed {high}.')
    if 'pattern' in preset:
        re.compile(preset['pattern'])
    if 'default' in preset:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(preset['default'])


def render_preview(service, body):
    from app.knowledge.schema_compiler import compile_schema
    from app.knowledge.document_repository import DocumentKnowledgeRepository
    from app.knowledge.services import KnowledgeService
    from jsonschema import Draft202012Validator, FormatChecker
    from jinja2.sandbox import SandboxedEnvironment
    from jinja2 import StrictUndefined
    draft = service.store.snapshot()
    if draft['revision'] != body['expected_revision']:
        raise ValueError('Authoring changed; refresh the preview.')
    binding = next((b for b in draft['catalogs']['template_bindings'] if b['template_path']==body['path']), None)
    if binding is None:
        raise ValueError('Select a saved template variant.')
    knowledge = KnowledgeService(DocumentKnowledgeRepository(draft['catalogs']))
    schema = compile_schema(knowledge, binding['operation_id'])
    from app.parameters.schema_loader import _apply_vendor_requirements
    schema = _apply_vendor_requirements(schema, [{'vendor':binding['vendor']}])
    values = body['parameters']
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(values)
    sources = {**draft['sources'], body['path']:body['content'].encode('utf-8')}
    service._validate(draft['catalogs'], sources, complete=True)
    if binding['input_contract'].get('derived'):
        raise ValueError('This variant requires runtime-derived inventory context; preview it through Studio.')
    context = {**binding['input_contract'].get('optional_defaults',{}), **values}
    output = SandboxedEnvironment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True).from_string(body['content']).render(**context)
    return {'ok':True, 'revision':draft['revision'], 'data':{'configuration':output,'schema':schema,'output_format':'native_cli'}}
