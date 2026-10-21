"""Passive published-knowledge inspection and bounded documentation retrieval."""
import json
from pathlib import Path
import re
from uuid import uuid4

from llm.gateway_models import Evidence, text_digest


def read_release(root):
    """Verify the existing V9 package without importing its mutable authoring store."""
    from hashlib import sha256
    pointer = json.loads((root / 'active.json').read_text(encoding='utf-8'))
    if not re.fullmatch('[a-f0-9]{32}', pointer.get('release_id', '')):
        raise ValueError('Invalid knowledge release identity')
    release = (root / pointer['release_id']).resolve()
    if not release.is_relative_to(root.resolve()):
        raise ValueError('Invalid knowledge release path')
    manifest_bytes = (release / 'manifest.json').read_bytes()
    if sha256(manifest_bytes).hexdigest() != pointer.get('manifest_sha256'):
        raise ValueError('Knowledge manifest integrity failed')
    manifest = json.loads(manifest_bytes)
    if manifest.get('format_version') != 1 or manifest.get('release_id') != pointer['release_id']:
        raise ValueError('Unsupported knowledge manifest')
    for name, expected in manifest['artifacts'].items():
        file = (release / name).resolve()
        if not file.is_relative_to(release) or sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError('Published knowledge artifact integrity failed')
    return release, manifest, pointer


def native_method_trust(release,manifest,operation_id,device):
    """Exact frozen or lifecycle-recorded publication authority, not certification."""
    info=manifest.get('cognishield_engineer_reviews')
    binding=next((b for b in manifest['template_bindings'] if b['operation_id']==operation_id and b['vendor']==device['vendor'] and b['platform']==device['platform'] and str(device['version']) in b['versions']),None)
    if not binding:return {'status':'UNAVAILABLE','certifications':{'vendor_semantics':'NOT_VERIFIED','device':'NOT_RUN','ansible':'NOT_RUN'}}
    from local_providers.knowledge_review import identity
    row=next((r for r in json.loads((release/info['artifact_path']).read_text())['bindings'] if r['identity']==identity(binding)),None) if info else None
    if row:
        # Activate can authorize an already-built immutable package. Its audit
        # stays in the existing authoring DB; immutable files are never rewritten.
        import sqlite3
        database=release.parents[2]/'storage/knowledge/catalog.sqlite3'
        if database.is_file():
            from local_providers.knowledge_review import latest_decision
            with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as connection:
                decision=latest_decision(connection,row['identity'],row['fingerprint'])
            if decision and decision.get('approval_action') in {'publish','activate'} and decision.get('release_target') in {manifest['release_id'],'next_compatible_immutable_release'}:
                row={**row,'approval':decision}
    approved=bool(row and row.get('approval') and row['approval']['decision']=='approve')
    return {'status':'ENGINEER_APPROVED_NOT_INDEPENDENTLY_CERTIFIED' if approved else 'LEGACY_PUBLISHED_NO_BOUND_SENIOR_ATTESTATION',
        'approved_by':row['approval']['approved_by'] if approved else None,
        'approved_at':row['approval']['approved_at'] if approved else None,
        'template_sha256':binding['template_sha256'],'release_id':manifest['release_id'],
        'assumptions':row['method']['assumptions'] if approved else [],'limitations':row['method']['limitations'] if approved else ['This inherited release has no content-bound senior approval record.'],
        'material_risks':row['method']['material_risks'] if approved else [],
        'certifications':row['certifications'] if approved else {'vendor_semantics':'NOT_VERIFIED','device':'NOT_RUN','ansible':'NOT_RUN'}}


def release_assessment(root=None):
    from local_providers.knowledge import knowledge_root
    root = root or knowledge_root() / 'storage/catalog_releases'
    if not (root / 'active.json').is_file():
        return {'status':'unavailable', 'message':'No active published release'}
    try:
        release, manifest, pointer = read_release(root)
        operations = json.loads((release / 'catalog/operations.json').read_text())
        variants = manifest.get('cognishield_playbooks', {}).get('variants', [])
        rows = []
        for operation in operations:
            for vendor, platform in [('cisco','iosxe'), ('huawei','vrp'), ('juniper','junos')]:
                bindings = [b for b in manifest['template_bindings'] if b['operation_id']==operation['operation_id'] and b['vendor']==vendor]
                support = operation.get('vendor_knowledge', {}).get(vendor, {})
                for binding in bindings or [{'platform':platform,'versions':[]}]:
                    matches = [v for v in variants if v['operation_id']==operation['operation_id'] and v['vendor']==vendor and v['platform']==binding['platform']]
                    rows.append({'operation_id':operation['operation_id'], 'vendor':vendor, 'platform':binding['platform'],
                        'versions':binding['versions'], 'native_status':'supported' if bindings and support.get('status')!='blocked_unverified' else 'unsupported',
                        'knowledge_approval':native_method_trust(release,manifest,operation['operation_id'],{'vendor':vendor,'platform':binding['platform'],'version':binding['versions'][0]}) if binding['versions'] else {'status':'UNAVAILABLE'},
                        'native_reason':support.get('reason') or ('Published catalog binding; device testing not established' if bindings else 'No reviewed published binding'),
                        'playbook_status':'published_requires_validation' if matches else 'unsupported',
                        'playbook_variants':matches, 'device_testing':'not_established', 'deployment_authorized':False})
        return {'status':'success', **pointer, 'operation_count':len(operations), 'binding_count':len(manifest['template_bindings']),
            'retrieval':{'mode':manifest['retrieval']['mode'], 'manifest_ready':manifest['retrieval'].get('ready',False), 'index_operability':'not_checked'},
            'coverage':rows}
    except (OSError, ValueError, KeyError) as exc:
        return {'status':'error', 'message':str(exc)}


def documentation_context(prompt):
    from lab_config import BACKEND_DIR
    from local_providers.knowledge import knowledge_root
    terms = set(re.findall(r'[a-z0-9_]{3,}', prompt.lower())) - set('the this that what why how and for from with current document buffer file code comment explain quote does function only unsaved please change modify configuration configure'.split())
    if not terms:
        return [], []
    candidates = []
    root = knowledge_root() / 'storage/catalog_releases'
    if (root / 'active.json').is_file():
        release, _, pointer = read_release(root)
        source = release / 'retrieval_documents.json'
        if source.is_file():
            for row in json.loads(source.read_text()):
                text = row['page_content']
                candidates.append(('published:'+row['id'], text, pointer['release_id'], 'published_operation_documentation'))
    # Read-only reference library; no global vector-store/cloud initialization.
    reference_root = (BACKEND_DIR / 'ansible/reference').resolve()
    for source in sorted(reference_root.rglob('reference.md')):
        if source.resolve().is_relative_to(reference_root) and not source.is_symlink() and source.stat().st_size < 100000:
            candidates.append((source.relative_to(BACKEND_DIR).as_posix(), source.read_text(encoding='utf-8'), None, 'reference_only'))
    # Literal catalog identities come from the active published documents. An
    # exact method request must not pull unrelated operations that share prose.
    exact={row[0] for row in candidates if row[0].startswith('published:') and
        re.search(r'(?<![\w])'+re.escape(row[0].removeprefix('published:'))+r'(?![\w])',prompt,re.I)}
    named=re.search(r'\b(?:published|catalog)\s+([a-z][a-z0-9]*_[a-z0-9_]+)\s+(?:method|operation)\b',prompt,re.I)
    if named and 'published:'+named[1].lower() not in exact:return [],[]
    retrieval_mode='bounded_lexical'
    if not exact and re.search(r'\b(published|catalog)\b',prompt,re.I) and any(row[0].startswith('published:') for row in candidates):
        from local_providers.knowledge import invoke
        found=invoke('published_search',{'release_id':pointer['release_id'],'query':prompt[:4000],'limit':3},'ai-read-only')['data']
        if found.get('release_id')!=pointer['release_id']:raise ValueError('Published retrieval release changed')
        order=['published:'+hit['operation_id'] for hit in found['hits']]
        candidates=sorted([row for row in candidates if row[0] in order],key=lambda row:order.index(row[0]))
        retrieval_mode='existing_v9_published_index'
    if exact:candidates=[row for row in candidates if row[0] in exact]
    scored = candidates if retrieval_mode=='existing_v9_published_index' else sorted(candidates, key=lambda row:len(terms & set(re.findall(r'[a-z0-9_]{3,}', row[1].lower()))), reverse=True)
    contexts, evidence = [], []
    for source, content, revision, authority in scored[:3]:
        matches=terms.intersection(re.findall(r'[a-z0-9_]{3,}', content.lower()))
        if source not in exact and retrieval_mode!='existing_v9_published_index' and len(matches)<2 and not matches.intersection({'ospf','vlan','bgp','merged','replaced','junos','iosxe','vrp','netconf','ansible'}):
            continue
        identity = uuid4().hex
        contexts.append({'source':source, 'evidence_id':identity, 'text':content[:6000], 'retrieval':retrieval_mode, 'truncated':len(content)>6000})
        evidence.append(Evidence(id=identity, source=source, origin='stored', source_revision=revision or text_digest(content), authority=authority))
    if contexts and re.search(r'\b(published|operation requirements|parameter requirements)\b',prompt,re.I):
        published=[e for e in evidence if e.authority=='published_operation_documentation']
        identities=list(dict.fromkeys(e.source.removeprefix('published:') for e in published))
        if identities:
            from local_providers.knowledge import invoke
            requirements=invoke('published_requirements',{'release_id':published[0].source_revision,'operation_ids':identities},'ai-read-only')['data']
            contexts=[c for c in contexts if c['source'].startswith('published:')]
            evidence=published
            # Prioritize the exact contract over repetitive retrieval prose. The
            # old 14KB projection was discarded by a three-source context budget.
            for item in contexts:
                item['truncated']=item['truncated'] or len(item['text'])>800
                item['text']=item['text'][:800]
            contexts[0]['published_requirements']=requirements
    return contexts, evidence
