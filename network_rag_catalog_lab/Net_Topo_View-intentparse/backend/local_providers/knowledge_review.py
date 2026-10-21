"""Engineer publication authority in the existing V9 authoring database.

Internet/device/Ansible certification never gates native publication here.
Publish/Activate record the authenticated engineer's decision directly. Chat tools
cannot call this module. Tests use isolated, explicitly named test reviewers.
"""
import json
from hashlib import sha256
from datetime import datetime, timezone
from uuid import uuid4

ACKNOWLEDGEMENT = 'I approve these exact native methods, scopes and disclosed risks for knowledge publication; this is not deployment or independent certification.'
TRUST = 'ENGINEER_APPROVED_NOT_INDEPENDENTLY_CERTIFIED'


def publication_decision(connection, row, actor, reason, releases, action, target):
    """No extra sign-off ceremony: the authorized Publish/Activate is approval.

    This records the actual account/action, never an invented independent human
    reviewer or vendor certification. Existing matching decisions stay intact.
    Called only by the senior-authorized lifecycle under its authoring lock.
    """
    if not actor or not reason.strip() or action not in {'publish','activate'}:
        raise ValueError('Authenticated publication actor, action and reason are required.')
    current=latest_decision(connection,row['identity'],row['fingerprint'])
    if current and current['decision']=='approve':return current
    if row.get('checks',{}).get('status')!='PASS':
        raise ValueError('Template/schema rendering checks failed for '+row['identity'])
    initialize(connection,releases)
    now=datetime.now(timezone.utc).isoformat();request='publication-'+uuid4().hex
    record={'id':uuid4().hex,'request_id':request,'identity':row['identity'],'fingerprint':row['fingerprint'],
        'decision':'approve','approved_by':actor,'approved_role':'admin',
        'approval_authority':'authenticated_engineer_publication_action','approval_action':action,
        'approved_at':now,'release_target':target,'reason':reason,
        'method':row.get('method'),'resolved_risks':[],
        'risk_disposition':'Disclosed as authored; publication authorization is not an independent technical risk assessment.',
        'trust_status':TRUST,'certifications':{'vendor_semantics':'NOT_VERIFIED','device':'NOT_RUN','ansible':'NOT_RUN'}}
    connection.execute('INSERT INTO cognishield_method_approvals VALUES (?,?,?,?,?,?,?)',
        (record['id'],request,row['identity'],row['fingerprint'],'approve',json.dumps(record),now))
    return record


def authorize_publication(service, base, releases, body, actor):
    """The existing authenticated Publish button approves this exact draft."""
    from app.knowledge.authoring_store import authoring_lock,AuthoringError
    with authoring_lock(base),service.store._connection() as connection:
        connection.execute('BEGIN IMMEDIATE');draft=service.store._snapshot(connection)
        if draft['revision']!=body['expected_revision']:raise AuthoringError('STALE_REVISION','Refresh the draft before publishing.')
        # Samples are a rendering check, not independent semantic goldens. Reuse
        # valid saved parameters; template authors own the resulting CLI text.
        before=draft
        prepare_publication_methods(service,connection,draft,releases)
        draft=service.store._snapshot(connection)
        if draft['revision']!=body['expected_revision']:
            service.store._audit(connection,before,draft,actor,body['reason'])
        report=review_status(service,connection,draft,checks=True)
        for row in report['rows']:
            if row['method'] is None:continue  # Unchanged inherited binding.
            publication_decision(connection,row,actor,body['reason'],releases,'publish','next_compatible_immutable_release')
        connection.commit()
        return draft['revision']


def prepare_publication_methods(service,connection,draft,releases):
    from local_providers.knowledge_lifecycle import render_preview
    service._validate(draft['catalogs'],draft['sources'],complete=True)
    stored=specs(connection);initialize(connection,releases);changed=False
    from app.knowledge.runtime import active_snapshot
    previous=active_snapshot(releases)
    inherited={identity(b):b for b in previous.manifest['template_bindings']} if previous else {}
    for binding in draft['catalogs']['template_bindings']:
        key=identity(binding);method=stored.get(key)
        old=inherited.get(key)
        if method is None and old:
            schema=fingerprint(draft,binding,None)[1]['schema']
            effect=next(o['description'] for o in draft['catalogs']['operations'] if o['operation_id']==binding['operation_id'])
            if old['template_sha256']==sha256(draft['sources'][binding['template_path']]).hexdigest() and old['input_contract']==binding['input_contract'] and previous.schema(binding['operation_id'],binding['vendor'])==schema and previous.service.get_operation(binding['operation_id']).description==effect:continue
        if method and check_method(service,draft,binding,method,catalog_validated=True)['status']=='PASS':continue
        schema=fingerprint(draft,binding,method)[1]['schema']
        candidates=[f['parameters'] for f in (method or {}).get('fixtures',[])]
        candidates.extend(schema.get('examples',[]))
        if not candidates:candidates=[schema_sample(schema)]
        fixtures=[]
        for parameters in candidates:
            output=render_preview(service,{'expected_revision':draft['revision'],'path':binding['template_path'],
                'content':draft['sources'][binding['template_path']].decode(),'parameters':parameters},
                draft=draft,_catalog_validated=True,_schema=schema)['data']['configuration']
            if not output.strip():raise ValueError('Template rendered empty: '+key)
            fixtures.append({'parameters':parameters,'expected_output':output})
        method={**(method or {}),'assumptions':(method or {}).get('assumptions',[]),
            'limitations':(method or {}).get('limitations',['Engineer-authored method; independent vendor/device certification not established.']),
            'material_risks':(method or {}).get('material_risks',[]),'fixtures':fixtures,
            'invalid_inputs':[fixtures[0]['parameters']|{'__unknown_input':True}]}
        checks=check_method(service,draft,binding,method,catalog_validated=True)
        if checks['status']!='PASS':raise ValueError('Schema/render checks failed for '+key+': '+json.dumps(checks['errors']))
        connection.execute('INSERT INTO cognishield_method_specs VALUES (?,?) ON CONFLICT(identity) DO UPDATE SET body=excluded.body',
            (key,json.dumps(method,sort_keys=True)));changed=True
    if changed:connection.execute('UPDATE authoring_state SET generation=generation+1 WHERE singleton=1')


def schema_sample(schema,field=''):
    """Bounded representative inputs; schema defaults/examples take priority.

    This is not intent extraction or invented device data. It is only a local
    compilation sample. Unrepresentable constraints ask for a schema example.
    """
    from jsonschema import Draft202012Validator,FormatChecker
    validator=Draft202012Validator(schema,format_checker=FormatChecker())
    options=[]
    for field in ['const','default']:
        if field in schema:options.append(schema[field])
    options+=schema.get('examples',[])+schema.get('enum',[])
    kind=schema.get('type','string')
    if kind=='object':
        properties=schema.get('properties',{})
        options.append({k:schema_sample(v,k) for k,v in properties.items() if k in schema.get('required',[]) or 'default' in v})
    elif kind=='array':options.append([schema_sample(schema.get('items',{}),field) for _ in range(max(1,min(10,schema.get('minItems',1))))])
    elif kind in {'integer','number'}:options.extend([schema.get('minimum',1),1,10,100])
    elif kind=='boolean':options.extend([False,True])
    else:
        if any(k in field for k in ['destination','network','prefix']):options.append('192.0.2.0/24')
        options+=['192.0.2.1','192.0.2.0/24','255.255.255.0','GigabitEthernet0/1','ge-0/0/0','EXAMPLE','Uplink','test','0','1','a'*max(1,min(256,schema.get('minLength',1)))]
    for value in options:
        if validator.is_valid(value):return value
    raise ValueError('Add a representative examples/default value to this schema field for the rendering check: '+json.dumps(schema)[:300])


def authorize_activation(connection,snapshot,actor,reason,releases):
    """Authorize the selected immutable pack, never the latest mutable draft."""
    info=snapshot.manifest.get('cognishield_engineer_reviews')
    if not info:return  # Legacy immutable packages retain their recorded authority.
    for row in snapshot.read_json(info['artifact_path'])['bindings']:
        if row.get('method') is None:continue  # Existing legacy compatibility checked below.
        publication_decision(connection,row,actor,reason,releases,'activate',snapshot.release_id)


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def identity(binding):
    return ':'.join([binding['operation_id'],binding['vendor'],binding['platform'],json.dumps(sorted(binding['versions']),separators=(',',':'))])


def table_exists(connection,name):
    return bool(connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone())


def initialize(connection, releases):
    """Called only inside a revision-checked authoring write transaction."""
    connection.execute('CREATE TABLE IF NOT EXISTS cognishield_method_specs (identity TEXT PRIMARY KEY,body TEXT NOT NULL)')
    connection.execute('CREATE TABLE IF NOT EXISTS cognishield_method_approvals (id TEXT PRIMARY KEY,request_id TEXT NOT NULL,identity TEXT NOT NULL,fingerprint TEXT NOT NULL,decision TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(request_id,identity))')
    connection.execute('CREATE TABLE IF NOT EXISTS cognishield_review_policy (singleton INTEGER PRIMARY KEY CHECK(singleton=1),body TEXT NOT NULL)')
    if not connection.execute('SELECT 1 FROM cognishield_review_policy').fetchone():
        from app.knowledge.runtime import active_pointer
        current=active_pointer(releases);known={current['release_id']} if current else set()
        if table_exists(connection,'cognishield_release_events'):
            for release,previous in connection.execute('SELECT release_id,previous_release FROM cognishield_release_events'):
                known.update(x for x in [release,previous] if x)
        connection.execute('INSERT INTO cognishield_review_policy VALUES (1,?)',(json.dumps({'version':1,'legacy_rollback_releases':sorted(known)}),))


def specs(connection):
    return {key:json.loads(body) for key,body in connection.execute('SELECT identity,body FROM cognishield_method_specs')} if table_exists(connection,'cognishield_method_specs') else {}


def fingerprint(draft,binding,method):
    from app.knowledge.document_repository import DocumentKnowledgeRepository
    from app.knowledge.services import KnowledgeService
    from app.knowledge.schema_compiler import compile_schema
    from app.parameters.schema_loader import _apply_vendor_requirements
    service=KnowledgeService(DocumentKnowledgeRepository(draft['catalogs']))
    schema=_apply_vendor_requirements(compile_schema(service,binding['operation_id']),[{'vendor':binding['vendor']}])
    operation=next(o for o in draft['catalogs']['operations'] if o['operation_id']==binding['operation_id'])
    # Unrelated operation-version bumps/path changes do not invalidate identical
    # content/scope/contracts. Material schema, method or source edits always do.
    payload={'identity':identity(binding),'scope':{**{k:binding[k] for k in ['operation_id','vendor','platform']},'versions':sorted(binding['versions'])},'template_sha256':sha256(draft['sources'][binding['template_path']]).hexdigest(),
        'schema':schema,'input_contract':binding['input_contract'],'effect':operation['description'],'method':method}
    return digest(payload),payload


def latest_decision(connection,key,hash_value):
    if not table_exists(connection,'cognishield_method_approvals'):return None
    row=connection.execute('SELECT body FROM cognishield_method_approvals WHERE identity=? AND fingerprint=? ORDER BY rowid DESC LIMIT 1',(key,hash_value)).fetchone()
    return json.loads(row[0]) if row else None


def check_method(service,draft,binding,method,*,catalog_validated=False):
    from local_providers.knowledge_lifecycle import render_preview
    if not method or not method.get('fixtures'):return {'status':'NOT_RUN','errors':['A concrete reviewed method and positive/negative fixtures are required.']}
    results=[];errors=[]
    schema=fingerprint(draft,binding,method)[1]['schema']
    body={'expected_revision':draft['revision'],'path':binding['template_path'],'content':draft['sources'][binding['template_path']].decode()}
    for fixture in method['fixtures']:
        try:
            output=render_preview(service,body|{'parameters':fixture['parameters']},draft=draft,_catalog_validated=catalog_validated,_schema=schema)['data']['configuration']
            passed=bool(output.strip()) and output.strip()==fixture['expected_output'].strip()
            results.append({'kind':'positive','passed':passed,'parameters':fixture['parameters'],'configuration':output})
            if not passed:errors.append('Rendered output differs from the supplied review fixture.')
        except (ValueError,KeyError,TypeError) as exc:errors.append(str(exc)[:500])
        except Exception as exc:errors.append(type(exc).__name__+': '+str(exc)[:500])
    if not method.get('invalid_inputs'):errors.append('At least one negative input fixture is required.')
    invalids=list(method.get('invalid_inputs',[]))
    if method['fixtures']:
        # Table-driven schema/security negatives are derived from the exact
        # compiled contract, not vendor certification. Never call an otherwise
        # valid input a negative merely because a test author expected rejection.
        from copy import deepcopy
        from jsonschema import Draft202012Validator,FormatChecker
        validator=Draft202012Validator(schema,format_checker=FormatChecker())
        sample=method['fixtures'][0]['parameters']
        candidates=[]
        for field in schema.get('required',[]):
            missing=deepcopy(sample);missing.pop(field,None);candidates.append(missing)
        for field,rule in schema.get('properties',{}).items():
            candidates.append(sample|{field:{'unexpected':'object'}})
            if rule.get('type')=='string':candidates.append(sample|{field:'bad\nshutdown; injected'})
            if 'minimum' in rule:candidates.append(sample|{field:rule['minimum']-1})
            if 'maximum' in rule:candidates.append(sample|{field:rule['maximum']+1})
        invalids.extend(v for v in candidates[:100] if not validator.is_valid(v))
    for invalid in invalids:
        try:render_preview(service,body|{'parameters':invalid},draft=draft,_catalog_validated=catalog_validated,_schema=schema)
        except Exception as exc:
            # Infrastructure failures are not invalid-input passes.
            from jsonschema import ValidationError
            passed=isinstance(exc,(ValueError,ValidationError))
            results.append({'kind':'negative','passed':passed,'error':str(exc)[:500]})
            if not passed:errors.append('Negative fixture failed outside parameter validation.')
        else:errors.append('An input designated invalid was accepted.')
    return {'status':'PASS' if not errors else 'FAIL','errors':errors,'results':results}


def review_status(service,connection,draft,*,checks=False):
    methods=specs(connection);rows=[]
    # Validate this exact immutable in-memory snapshot once, not 141 times.
    # No client can supply this flag, and all fixtures still use V9 parameter
    # validation, safe derivations and StrictUndefined rendering individually.
    if checks:service._validate(draft['catalogs'],draft['sources'],complete=True)
    for binding in draft['catalogs']['template_bindings']:
        key=identity(binding);method=methods.get(key)
        value,content=fingerprint(draft,binding,method)
        decision=latest_decision(connection,key,value)
        approved=bool(decision and decision['decision']=='approve')
        rows.append({'identity':key,'binding':binding,'fingerprint':value,'template_sha256':content['template_sha256'],
            'schema':content['schema'],'template_content':draft['sources'][binding['template_path']].decode(),'method':method,'approval':decision,'approved':approved,
            'trust_status':TRUST if approved else 'DRAFT_NOT_PUBLISHED',
            'certifications':{'vendor_semantics':'NOT_VERIFIED','device':'NOT_RUN','ansible':'NOT_RUN'},
            'checks':check_method(service,draft,binding,method,catalog_validated=True) if checks else None})
    return {'revision':draft['revision'],'acknowledgement':ACKNOWLEDGEMENT,'rows':rows,
        'counts':{'bindings':len(rows),'approved':sum(r['approved'] for r in rows),'pending':sum(not r['approved'] for r in rows)}}


def save_method(service,connection,draft,body,actor,releases):
    from app.knowledge.authoring_store import AuthoringError
    if draft['revision']!=body['expected_revision']:raise AuthoringError('STALE_REVISION','Refresh before changing the reviewed method.')
    binding=next((b for b in draft['catalogs']['template_bindings'] if identity(b)==body['identity']),None)
    if not binding:raise ValueError('Unknown exact binding scope.')
    result=check_method(service,draft,binding,body['method'])
    if result['status']!='PASS':raise ValueError('Method fixture validation failed: '+json.dumps(result['errors']))
    initialize(connection,releases)
    connection.execute('INSERT INTO cognishield_method_specs VALUES (?,?) ON CONFLICT(identity) DO UPDATE SET body=excluded.body',(body['identity'],json.dumps(body['method'],sort_keys=True)))
    connection.execute('UPDATE authoring_state SET generation=generation+1 WHERE singleton=1')
    after=service.store._snapshot(connection)
    audit=service.store._audit(connection,draft,after,actor,body['reason'])
    return {'ok':True,'revision':after['revision'],'data':{'audit_id':audit,'checks':result,'approval_created':False}}


def approve(service,connection,draft,body,actor,releases):
    from app.knowledge.authoring_store import AuthoringError
    if draft['revision']!=body['expected_revision']:raise AuthoringError('STALE_REVISION','Knowledge changed; review the current content before signing.')
    if body['acknowledgement']!=ACKNOWLEDGEMENT:raise ValueError('Explicit publication acknowledgement is required.')
    initialize(connection,releases);methods=specs(connection);records=[]
    service._validate(draft['catalogs'],draft['sources'],complete=True)
    for selection in body['decisions']:
        binding=next((b for b in draft['catalogs']['template_bindings'] if identity(b)==selection['identity']),None)
        if not binding:raise ValueError('Unknown binding scope.')
        method=methods.get(selection['identity']);value,_=fingerprint(draft,binding,method)
        if value!=selection['fingerprint']:raise AuthoringError('STALE_REVISION','Reviewed source, contract or scope changed.')
        if selection['decision']=='approve':
            if check_method(service,draft,binding,method,catalog_validated=True)['status']!='PASS':raise ValueError('Mandatory application/render checks do not pass.')
            risks=set(method.get('material_risks',[]))
            if set(selection['resolved_risks'])!=risks:raise ValueError('Explicit resolution of every disclosed material risk is required.')
        existing=connection.execute('SELECT body FROM cognishield_method_approvals WHERE request_id=? AND identity=?',(body['request_id'],selection['identity'])).fetchone()
        if existing:
            record=json.loads(existing[0])
            if record['fingerprint']!=value or record['decision']!=selection['decision'] or record['approved_by']!=actor:raise ValueError('Review request identity was reused with different content.')
        else:
            record={'id':uuid4().hex,'request_id':body['request_id'],'identity':selection['identity'],'fingerprint':value,'decision':selection['decision'],
                'approved_by':actor,'approved_role':'admin','approval_authority':'authenticated_senior_knowledge_reviewer',
                'approved_at':datetime.now(timezone.utc).isoformat(),'authoring_revision':draft['revision'],
                'release_target':'next_compatible_immutable_release','reason':body['reason'],'method':method,
                'resolved_risks':selection['resolved_risks'],'trust_status':TRUST,'certifications':{'vendor_semantics':'NOT_VERIFIED','device':'NOT_RUN','ansible':'NOT_RUN'}}
            connection.execute('INSERT INTO cognishield_method_approvals VALUES (?,?,?,?,?,?,?)',(record['id'],body['request_id'],selection['identity'],value,selection['decision'],json.dumps(record),record['approved_at']))
        records.append(record)
    return {'ok':True,'revision':draft['revision'],'data':{'decisions':records,'authority':'authenticated_senior_knowledge_reviewer'}}


def freeze_reviews(base,releases,snapshot,expected_revision):
    from app.knowledge.authoring_store import authoring_lock
    from app.knowledge.authority import authoring_snapshot_unlocked,authoring_store
    from app.knowledge.management import KnowledgeManagementService
    from app.knowledge.runtime import KnowledgeSnapshot
    with authoring_lock(base):
        draft=authoring_snapshot_unlocked(base)
        if draft['revision']!=expected_revision:raise ValueError('Authoring changed before approval freezing.')
        with authoring_store(base)._connection() as connection:
            report=review_status(KnowledgeManagementService(base),connection,draft,checks=False)
        records=[]
        service=KnowledgeManagementService(base)
        service._validate(draft['catalogs'],draft['sources'],complete=True)
        from local_providers.knowledge_lifecycle import guard_native_renderer
        from app.knowledge.runtime import snapshot_scope
        render=guard_native_renderer()
        for row in report['rows']:
            record={k:row[k] for k in ['identity','fingerprint','template_sha256','trust_status','approval','method','certifications']}
            binding=next(b for b in draft['catalogs']['template_bindings'] if identity(b)==row['identity'])
            checks=check_method(service,draft,binding,row['method'],catalog_validated=True)
            record['checks']=checks
            profile_checks=[]
            for version in binding['versions']:
                device={'hostname':'CONTROLLED-REVIEW-FIXTURE','vendor':binding['vendor'],'platform':binding['platform'],'version':version}
                with snapshot_scope(snapshot):
                    selected=snapshot.binding(device,binding['operation_id'])
                    if selected['template_sha256']!=row['template_sha256']:raise ValueError('Compiled binding differs from reviewed source.')
                    for fixture in (row['method'] or {}).get('fixtures',[]):
                        output=render(device,binding['operation_id'],fixture['parameters'])
                        if output.strip()!=fixture['expected_output'].strip():raise ValueError('Published V9 renderer differs from the exact reviewed fixture.')
                    for invalid in [device|{'version':'UNSUPPORTED'},device|{'platform':'UNSUPPORTED'}]:
                        try:snapshot.binding(invalid,binding['operation_id'])
                        except ValueError:pass
                        else:raise ValueError('Incompatible runtime profile was accepted.')
                profile_checks.append({'version':version,'binding':'PASS','rendered_fixtures':len((row['method'] or {}).get('fixtures',[])),'wrong_profile_rejected':True})
            record['runtime_checks']={'scope':'Existing V9 binding and renderer in unpublished compiler staging; not target-resolution/Studio acceptance or active runtime approval','profiles':profile_checks}
            if row['approved']:
                if checks['status']!='PASS':raise ValueError('Previously approved binding no longer passes runtime structural checks.')
            records.append(record)
        raw=json.dumps({'format_version':1,'authority':'engineer_approval','bindings':records},indent=2).encode()
        path='cognishield/engineer_reviews.json';target=snapshot.root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        manifest=snapshot.manifest;manifest['artifacts'][path]=sha256(raw).hexdigest();manifest['cognishield_engineer_reviews']={'artifact_path':path,'approved':sum(r['approval'] is not None and r['approval']['decision']=='approve' for r in records),'bindings':len(records)}
        (snapshot.root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        pointer={'release_id':snapshot.release_id,'manifest_sha256':sha256((snapshot.root/'manifest.json').read_bytes()).hexdigest()}
        verified=KnowledgeSnapshot(releases,pointer)
        (releases/'active.json').write_text(json.dumps(pointer),encoding='utf-8')
        return verified


def assert_activation_authorized(connection,snapshot,previous):
    """Unchanged inherited bindings remain available; new methods require lifecycle authority.

    Historical known-good rollback is allowed without inventing retroactive
    approval. Its legacy label remains explicit.
    """
    if table_exists(connection,'cognishield_review_policy'):
        policy=json.loads(connection.execute('SELECT body FROM cognishield_review_policy WHERE singleton=1').fetchone()[0])
        if snapshot.release_id in policy['legacy_rollback_releases']:return
    if previous and snapshot.release_id==previous.release_id:return
    info=snapshot.manifest.get('cognishield_engineer_reviews')
    records={r['identity']:r for r in snapshot.read_json(info['artifact_path'])['bindings']} if info else {}
    old={identity(b):b for b in previous.manifest['template_bindings']} if previous else {}
    old_info=previous.manifest.get('cognishield_engineer_reviews') if previous else None
    old_records={r['identity']:r for r in previous.read_json(old_info['artifact_path'])['bindings']} if old_info else {}
    pending=[]
    for binding in snapshot.manifest['template_bindings']:
        key=identity(binding);prior=old.get(key);record=records.get(key)
        inherited=prior and prior['template_sha256']==binding['template_sha256'] and prior['input_contract']==binding['input_contract'] and previous.schema(binding['operation_id'],binding['vendor'])==snapshot.schema(binding['operation_id'],binding['vendor']) and previous.service.get_operation(binding['operation_id']).description==snapshot.service.get_operation(binding['operation_id']).description
        if record and record.get('approval'):
            current=latest_decision(connection,key,record['fingerprint'])
            explicit_activation=current and current.get('approval_action')=='activate' and current.get('release_target')==snapshot.release_id
            if (current!=record['approval'] and not explicit_activation) or current['decision']!='approve':pending.append(key);continue
        if inherited:
            old_review=old_records.get(key)
            if old_review and old_review.get('approval') and (not record or record['fingerprint']!=old_review['fingerprint']):pending.append(key)
            continue
        expected=digest({'identity':key,'scope':{**{k:binding[k] for k in ['operation_id','vendor','platform']},'versions':sorted(binding['versions'])},'template_sha256':binding['template_sha256'],
            'schema':snapshot.schema(binding['operation_id'],binding['vendor']),'input_contract':binding['input_contract'],'effect':snapshot.service.get_operation(binding['operation_id']).description,'method':record.get('method')}) if record else None
        current=latest_decision(connection,key,record['fingerprint']) if record else None
        # A built package may precede the engineer's Activate action. Its exact
        # authorization is appended to SQLite, without rewriting immutable files.
        activation=current and current.get('approval_action')=='activate' and current.get('release_target')==snapshot.release_id
        approved=(current if activation else record.get('approval') or current) if record else None
        if not record or record['fingerprint']!=expected or not approved or approved['decision']!='approve' or approved['fingerprint']!=record['fingerprint'] or record.get('checks',{}).get('status')!='PASS':pending.append(key)
        elif current!=approved:pending.append(key)
    if pending:raise ValueError('Publication authority or structural checks are invalid for '+str(len(pending))+' changed binding(s): '+', '.join(pending[:12]))
