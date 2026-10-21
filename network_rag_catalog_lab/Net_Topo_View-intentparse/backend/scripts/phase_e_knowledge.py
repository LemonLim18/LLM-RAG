"""Resumable 141-row V9 authoring queue. This tool never creates human approvals.

Default target is the one acceptance workspace. --ordinary replays exact API
authoring changes (not a database/release copy). Activation stays separately gated.
"""
import argparse,asyncio,json,os,sys
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(Path(__file__).resolve().parent)]
from phase_d_audit import Run
from phase_e_methods import EXTRA_FIELDS,template,fixture,limitations


async def execute(args):
    target=ROOT/('backend/knowledge_workspace' if args.ordinary else 'tmp/phase-d/acceptance-knowledge')
    if not target.exists():raise ValueError('Existing workspace is required; no implicit initialization/copy')
    os.environ['COGNISHIELD_KNOWLEDGE_ROOT']=str(target)
    if args.action=='seed-management':
        from phase_d_knowledge import author_management
        await author_management(target);return
    from local_providers.knowledge import router
    from auth.auth import create_access_token
    from fastapi import FastAPI
    import httpx
    from jinja2 import Environment,meta
    sys.path.insert(1,str(ROOT.parent/'network_rag_catalog_v2'))
    from local_providers.knowledge_lifecycle import configure_native_contracts
    configure_native_contracts()
    from app.knowledge.rule_registry import TEMPLATE_DERIVATIONS
    from app.parameters.normalizer import normalize_key
    from local_providers.knowledge_review import identity
    app=FastAPI();app.include_router(router,prefix='/api/v1')
    index=json.loads((ROOT/'backend/ansible/reference/operation_drafts/index.json').read_text())['templates']
    if args.start_at and args.start_at not in {r['operation_id'] for r in index}:raise ValueError('Unknown resume operation')
    scope=[r for r in index if (not args.operation or r['operation_id']==args.operation) and (not args.vendor or r['vendor']==args.vendor) and (not args.start_at or r['operation_id']>=args.start_at)]
    if not scope:raise ValueError('Unknown operation/vendor scope; nothing was silently skipped')
    mode='ordinary-authoring' if args.ordinary else 'acceptance-authoring'
    run=Run('E2-'+args.action+'-'+mode,'unit_deterministic',phase='phase-e')
    from scripts.phase_d_audit import source_manifest,digest
    (run.path/'scope.json').write_text(json.dumps({'target':str(target),'action':args.action,'rows':[[r['operation_id'],r['vendor']] for r in scope],'source_digest':digest(json.dumps(source_manifest(),sort_keys=True).encode()),'approval_created':False},indent=2))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://authoring',headers={'Authorization':'Bearer '+create_access_token(1,'codex-programmatic-author','engineer')},timeout=300) as client:
        async def call(method,path,body=None):
            response=await client.request(method,'/api/v1/knowledge'+path,json=body)
            if response.status_code!=200:
                run.record('E-AUTHORING-API','FAIL',expected='Existing revision-checked V9 authoring API succeeds',actual=response.json(),path=path)
                response.raise_for_status()
            return response.json()
        initial=await call('GET','');old_release=initial['data']['active_release']['release_id']
        if args.action in {'build','report'}:
            if args.action=='build':
                built=await call('POST','/build',{'mode':'chroma','expected_revision':initial['revision'],'expected_release':old_release,'reason':'Phase E structurally checked inactive candidate; zero human approvals inferred, no activation'})
                run.record('E-CANDIDATE-BUILD','PASS',expected='Immutable Chroma-indexed candidate; active pointer unchanged; approval still required',actual=built)
                print(json.dumps({'run':str(run.path),'candidate':built,'active_unchanged':old_release}),flush=True)
            report=await call('GET','/reviews?checks=true')
            (run.path/'review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            final=await call('GET','');assert final['data']['active_release']['release_id']==old_release
            print(json.dumps({'run':str(run.path),'counts':report['data']['counts'],'structural_pass':sum(r['checks']['status']=='PASS' for r in report['data']['rows']),'active':old_release}),flush=True)
            return
        if args.action=='contracts':
          for op in sorted({r['operation_id'] for r in scope}):
            state=await call('GET','');catalogs=state['data']['catalogs'];operation=next((o for o in catalogs['operations'] if o['operation_id']==op),None)
            if not operation:raise ValueError('Run seed-management before preparing all 47 operations')
            rows=[r for r in scope if r['operation_id']==op];changes=[]
            mappings=[deepcopy(r) for r in catalogs['operation_parameters'] if r['operation_id']==op]
            rules=[deepcopy(r) for r in catalogs['operation_rules'] if r['operation_id']==op]
            bindings=[deepcopy(r) for r in catalogs['template_bindings'] if r['operation_id']==op]
            fields={r['field_path'] for r in mappings if '.' not in r['field_path'] and '[]' not in r['field_path']}
            root_rule=next(r for r in rules if r['field_path']=='')['keywords'];vendor_required=root_rule.setdefault('x-required-by-vendor',{})
            for row in rows:
              content=template(ROOT,row);variables=meta.find_undeclared_variables(Environment().parse(content))
              missing=variables-fields-set(TEMPLATE_DERIVATIONS)
              for field in sorted(missing):
                if field not in EXTRA_FIELDS:raise ValueError(f'Unresolved input {op}/{row["vendor"]}/{field}; define its real contract')
                kind,keywords=EXTRA_FIELDS[field]
                members={p['parameter_id'] for p in catalogs['category_parameters'] if p['category_id']==operation['category_id']}
                candidates=[p for p in catalogs['parameters'] if normalize_key(field) in {normalize_key(s) for s in [p['parameter_id'],p.get('display_name',''),*p.get('aliases',[])] if s}]
                definition=next((p for p in candidates if p['parameter_id'] in members),next(iter(candidates),None))
                parameter_id=definition['parameter_id'] if definition else field
                if definition is None:
                    changes.append({'entity':'parameter','action':'create','entity_id':field,'values':{'display_name':field.replace('_',' '),'value_type':kind,'description':'Explicit vendor realization input; no invented target-state value.'}})
                    catalogs['parameters'].append({'parameter_id':field})
                if not any(p['category_id']==operation['category_id'] and p['parameter_id']==parameter_id for p in catalogs['category_parameters']):
                    changes.append({'entity':'membership','action':'assign','values':{'category_id':operation['category_id'],'parameter_id':parameter_id}})
                    catalogs['category_parameters'].append({'category_id':operation['category_id'],'parameter_id':parameter_id})
                if field not in fields:
                    position=max([r['position'] for r in mappings if '.' not in r['field_path']],default=-1)+1
                    mappings.append({'operation_id':op,'operation_version':operation['version']+1,'category_id':operation['category_id'],'parameter_id':parameter_id,'field_path':field,'position':position,'required':False,'required_order':None})
                    rules.append({'operation_id':op,'operation_version':operation['version']+1,'field_path':field,'keywords':keywords});fields.add(field)
                vendor_required.setdefault(row['vendor'],[])
                if field not in vendor_required[row['vendor']]:vendor_required[row['vendor']].append(field)
              if (row['vendor']=='juniper' and op in {'configure_isis_interface','disable_isis_interface'}) or (row['vendor']=='huawei' and op=='disable_isis_interface'):
                if 'process_name' not in vendor_required.setdefault(row['vendor'],[]):vendor_required[row['vendor']].append('process_name')
              if row['vendor']=='juniper' and op in {'create_vlan','delete_vlan','modify_vlan'}:
                if 'name' not in fields:
                    name_rule=EXTRA_FIELDS['name'][1];mappings.append({'operation_id':op,'operation_version':operation['version']+1,'category_id':operation['category_id'],'parameter_id':'name','field_path':'name','position':len(fields),'required':False,'required_order':None});rules.append({'operation_id':op,'operation_version':operation['version']+1,'field_path':'name','keywords':name_rule});fields.add('name')
                if 'name' not in vendor_required.setdefault('juniper',[]):vendor_required['juniper'].append('name')
            if op=='configure_port_channel':next(r for r in rules if r['field_path']=='aggregate_interface')['keywords']['pattern']='^(?:Port-channel(?:[1-9]|[1-9][0-9]|1[01][0-9]|12[0-8])|ae[0-9]+|Eth-Trunk[0-9]+)$'
            if op=='configure_loopback_interface':
                interface_rule=next(r for r in rules if r['field_path']=='interface')['keywords']
                interface_rule['pattern']='^(?:Loopback[0-9]+|LoopBack[0-9]+|lo[0-9]+(?:\\.[0-9]+)?)$'
            required={r['field_path'] for r in mappings if r['required'] and '.' not in r['field_path']}
            for binding in bindings:
                row=next((r for r in rows if r['vendor']==binding['vendor']),None)
                content=template(ROOT,row) if row else state['data']['templates'][binding['template_path']]
                variables=meta.find_undeclared_variables(Environment().parse(content))
                binding['input_contract']={'fields':sorted(fields),'optional_defaults':{f:None for f in fields-required-set(vendor_required.get(binding['vendor'],[]))},'derived':{name:handler for name,(handler,source) in TEMPLATE_DERIVATIONS.items() if name in variables and source in fields}}
            contract={'version':operation['version']+1,'mappings':mappings,'rules':rules,'templates':bindings}
            for records in [mappings,rules,bindings]:
                for record in records:record['operation_version']=contract['version']
            def stable(value):
                if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in {'operation_version','version'}}
                if isinstance(value,list):return [stable(v) for v in value]
                return value
            prior={'mappings':[r for r in state['data']['catalogs']['operation_parameters'] if r['operation_id']==op],'rules':[r for r in state['data']['catalogs']['operation_rules'] if r['operation_id']==op],'templates':[r for r in state['data']['catalogs']['template_bindings'] if r['operation_id']==op]}
            if changes or stable(contract)!=stable(prior):
                changes.append({'entity':'contract','action':'replace','entity_id':op,'values':contract})
                await call('POST','/edit',{'expected_revision':state['revision'],'reason':'Phase E vendor-specific native inputs and registered derivations; human approval remains pending','changes':changes})
            for row in rows:
                state=await call('GET','');binding=next((b for b in state['data']['catalogs']['template_bindings'] if b['operation_id']==op and b['vendor']==row['vendor']),None);content=template(ROOT,row)
                if binding and state['data']['templates'][binding['template_path']]==content:continue
                body={'expected_revision':state['revision'],'reason':'Phase E native authoring proposal; not a senior approval','path':binding['template_path'] if binding else '','content':content}
                if binding is None:body.update(operation_id=op,vendor=row['vendor'],platform={'cisco':'iosxe','juniper':'junos','huawei':'vrp'}[row['vendor']],versions=[{'cisco':'17.9','juniper':'23.4','huawei':'8'}[row['vendor']]])
                await call('PUT','/template',body)
            state=await call('GET','');current=next(o for o in state['data']['catalogs']['operations'] if o['operation_id']==op)
            knowledge=deepcopy(current.get('vendor_knowledge',{}))
            for row in rows:knowledge[row['vendor']]={'status':'generation_supported','reason':'Native method proposal; publication requires exact senior-engineer sign-off and structural gates.','requirements':['Review existing state/prerequisites and declared method limitations.']}
            if knowledge!=current.get('vendor_knowledge',{}):await call('POST','/edit',{'expected_revision':state['revision'],'reason':'Declare precise native proposal availability in authoring; active runtime remains unchanged','changes':[{'entity':'operation','action':'update','entity_id':op,'values':{'vendor_knowledge':knowledge}}]})
            run.record('E-CONTRACT-'+op,'PASS',expected='Scoped source and contracts saved through existing authoring API; no active change',actual={'vendors':[r['vendor'] for r in rows]})
            print(json.dumps({'operation':op,'status':'authored','approval_created':False}),flush=True)
        else:
          state=await call('GET','');review=await call('GET','/reviews?checks=true' if args.only_unprepared else '/reviews');fixtures=json.loads((ROOT.parent/'network_rag_catalog_v2/tests/fixtures/vendor_runtime_cases.json').read_text())
          for row in scope:
            r=next(r for r in review['data']['rows'] if r['binding']['operation_id']==row['operation_id'] and r['binding']['vendor']==row['vendor']);op=row['operation_id'];vendor=row['vendor']
            if args.only_unprepared and r['checks']['status']=='PASS':continue
            existing=next((f['parameters'] for f in fixtures if f['operation_id']==op and f['vendor']==vendor),next((f['parameters'] for f in fixtures if f['operation_id']==op),{}))
            values=fixture(r['schema'],vendor,op,existing)
            state=await call('GET','')
            rendered=await call('POST','/render',{'expected_revision':state['revision'],'path':r['binding']['template_path'],'content':r['template_content'],'parameters':values})
            assumptions,limits,risks=limitations(op,vendor)
            limits+=['Golden output is a generated review proposal, not an independently certified expected configuration.']
            method={'assumptions':assumptions,'limitations':limits,'material_risks':risks,'fixtures':[{'parameters':values,'expected_output':rendered['data']['configuration']}],'invalid_inputs':[{},values|{'__unknown_input':True}]}
            if op=='remove_static_route' and vendor=='juniper':
                # Independently specified inverse scope: remove the exact
                # qualified object created when a per-next-hop preference exists.
                method['fixtures'].append({'parameters':values|{'next_hop_kind':'qualified-next-hop'},
                    'expected_output':'delete routing-options static route '+values['destination']+' qualified-next-hop '+values['next_hop']})
            if 'rate_kbps' in r['binding']['input_contract'].get('derived',{}):method['invalid_inputs'].append(values|{'rate_bps':values['rate_bps']+1})
            if r['method']!=method:await call('PUT','/review-method',{'expected_revision':state['revision'],'identity':r['identity'],'method':method,'reason':'Record exact review proposal and reproducible application fixtures; no human sign-off inferred'})
            run.record('E-RENDER-'+op+'-'+vendor,'PASS',expected='Actual V9 preview is nonempty and exact fixture/invalid-input checks pass; awaiting human approval',actual={'identity':r['identity'],'parameters':values,'configuration':rendered['data']['configuration'],'approval_created':False})
            print(json.dumps({'operation':op,'vendor':vendor,'status':'reviewable','approval_created':False}),flush=True)
        final=await call('GET','');assert final['data']['active_release']['release_id']==old_release
    print(json.dumps({'run':str(run.path),'rows':len(scope),'ordinary_active_changed':False,'approvals_created':0}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['seed-management','contracts','methods','report','build']);parser.add_argument('--ordinary',action='store_true');parser.add_argument('--only-unprepared',action='store_true');parser.add_argument('--operation');parser.add_argument('--start-at');parser.add_argument('--vendor',choices=['cisco','juniper','huawei'])
    asyncio.run(execute(parser.parse_args()))
