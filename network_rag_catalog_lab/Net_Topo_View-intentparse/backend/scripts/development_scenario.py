"""Local authoring and authenticated control of the existing scenario manager.

No credentials are minted or logged. Mutating server commands require an existing
admin bearer token in COGNISHIELD_DEV_TOKEN and the server's explicit dev flag.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from local_providers.development import Scenario


def local_path(value):
    path=Path(value).resolve()
    allowed=[ROOT/'backend/development/scenarios',ROOT/'backend/development/schemas',ROOT/'tmp/phase-d',ROOT/'tmp/phase-e',ROOT/'tmp/phase-f',ROOT/'tmp/phase-g']
    if not any(path.is_relative_to(root.resolve()) for root in allowed):raise ValueError('Scenario output must stay inside backend/development or the Phase D/E audit directories')
    return path


async def main(args):
    if args.command in {'bundle-create','bundle-clone'}:
        from development.starter import starter_bundle
        from development.bundles import compile_bundle,load_bundle
        import base64
        import hashlib
        value=load_bundle(local_path(args.directory)) if args.command=='bundle-clone' else starter_bundle(args.variant)
        value['manifest'].update(scenario_id=args.id,scenario_revision=1)
        if getattr(args,'linked_configs',False):
            for category in ['running_configs','config_snapshots']:
                for row in value['sources'][category]['data']['records']:
                    raw=row['values'].pop('config_text').encode('utf-8')
                    relative='configs/'+category+'/'+str(row['device_id'])+'.cfg'
                    value['assets'][relative]=raw.decode('utf-8')
                    row['values']['config_file']=relative
        compile_bundle(value)
        target=local_path(args.output)
        if target.exists():raise ValueError('New scenario folder must not already exist')
        target.mkdir(parents=True)
        hashes={}
        for key,source in value['sources'].items():
            raw=json.dumps(source,indent=2).encode('utf-8')
            relative=value['manifest']['source_files'][key]
            path=target/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            hashes[key]=hashlib.sha256(raw).hexdigest()
        for relative,asset in value['assets'].items():
            path=target/relative;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(asset.encode() if isinstance(asset,str) else base64.b64decode(asset['base64'],validate=True))
        # Preserve the author's optional integrity-lock policy. Ordinary editable
        # starters have no locks; cloning must not silently freeze all24 files.
        value['manifest']['source_hashes']={key:hashes[key] for key in value['manifest'].get('source_hashes',{})}
        (target/'manifest.json').write_text(json.dumps(value['manifest'],indent=2),encoding='utf-8')
        print(json.dumps({'created':str(target),'sources':24,'activated':False}));return
    if args.command=='bundle-export':
        from development.bundles import load_bundle,compile_bundle
        value=load_bundle(local_path(args.directory));compile_bundle(value)
        target=local_path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
        print(json.dumps({'exported':str(target),'sources':24,'activated':False}));return
    if args.command=='bundle-diff':
        from development.bundles import load_bundle
        import difflib,hashlib
        before=load_bundle(local_path(args.before));after=load_bundle(local_path(args.after))
        changes=[]
        for key,left,right in [('manifest',before['manifest'],after['manifest']),
                *[(key,before['sources'][key],after['sources'][key]) for key in before['sources']]]:
            if left==right:continue
            lines=list(difflib.unified_diff(json.dumps(left,sort_keys=True,indent=2).splitlines(),json.dumps(right,sort_keys=True,indent=2).splitlines(),fromfile='before/'+key,tofile='after/'+key,lineterm=''))
            changes.append({'section':key,'diff':'\n'.join(lines[:2000]),'truncated':len(lines)>2000})
        # Binary assets are compared by digest, never expanded into a huge diff.
        assets=[]
        for name in sorted(set(before['assets'])|set(after['assets'])):
            left=before['assets'].get(name);right=after['assets'].get(name)
            if left!=right:
                fingerprint=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest() if value is not None else None
                assets.append({'path':name,'before_digest':fingerprint(left),'after_digest':fingerprint(right)})
        result={'changed':bool(changes or assets),'sections':changes,'assets':assets,'activated':False}
        if args.output:
            target=local_path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
            print(json.dumps({'report':str(target),'changed':result['changed'],'activated':False}))
        else:print(json.dumps(result,indent=2))
        return
    if args.command=='bundle-validate':
        from development.bundles import load_bundle,compile_bundle
        bundle=load_bundle(local_path(args.directory));scenario=compile_bundle(bundle)
        print(json.dumps({'valid':True,'scenario':scenario['id'],'sources':len(scenario['source_statuses']),'statuses':scenario['source_statuses'],'activated':False}));return
    if args.command=='schema':
        print(json.dumps(Scenario.model_json_schema(),indent=2));return
    if args.command=='validate':
        scenario=Scenario.model_validate_json(Path(args.file).read_text(encoding='utf-8'))
        print(json.dumps({'valid':True,'id':scenario.id,'revision':scenario.revision,'format_version':scenario.format_version}));return
    if args.command=='bundle-import':
        from development.bundles import load_bundle
        bundle=load_bundle(local_path(args.directory))
        import httpx
        token=os.getenv('COGNISHIELD_DEV_TOKEN')
        if not token:raise ValueError('Use an existing authenticated admin token in COGNISHIELD_DEV_TOKEN')
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',headers={'Authorization':'Bearer '+token},trust_env=False) as client:
            response=await client.post('/api/v1/development-network/workbench/drafts',json={'bundle':bundle});response.raise_for_status();draft=response.json()
            response=await client.post('/api/v1/development-network/workbench/drafts/'+draft['draft_id']+'/validate',json={'expected_revision':draft['draft_revision']});response.raise_for_status()
            print(json.dumps({'draft_id':draft['draft_id'],'draft_revision':draft['draft_revision'],'validation':response.json(),'activated':False}))
        return
    if args.command=='create':
        from development.examples import mixed_vendor_path
        if args.seed is not None:
            if args.base:raise ValueError('Select a base file or seed, not both')
            from development.seeded import seeded_scenario
            value=seeded_scenario(args.seed,args.variant)
        else:value=Scenario.model_validate_json(Path(args.base).read_text(encoding='utf-8')).model_dump() if args.base else mixed_vendor_path()
        value.update(id=args.id,revision=1)
        validated=Scenario.model_validate(value);target=local_path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x',encoding='utf-8') as stream:stream.write(validated.model_dump_json(indent=2))
        print(json.dumps({'created':str(target),'id':args.id,'activated':False}));return
    import httpx
    token=os.getenv('COGNISHIELD_DEV_TOKEN')
    if not token:raise ValueError('Set COGNISHIELD_DEV_TOKEN to your existing authenticated developer token; no new credential is created')
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',headers={'Authorization':'Bearer '+token},trust_env=False,timeout=240) as client:
        async def call(method,path,body=None):
            result=await client.request(method,path,json=body);result.raise_for_status();return result.json()
        current=await call('GET','/api/v1/development-network')
        if not current.get('enabled'):raise ValueError('Development simulation is disabled; CLI cannot enable it')
        revision=args.expected_revision or current['context']['source_revision']
        if args.command=='list':result={'catalog':current['catalog'],'context':current['context']}
        elif args.command=='show':result=current
        elif args.command=='export':
            target=local_path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('x',encoding='utf-8') as stream:json.dump(current['scenario'],stream,indent=2)
            result={'exported':str(target),'context':current['context']}
        elif args.command in {'activate','reset','import'}:
            body={'action':{'activate':'select','reset':'reset','import':'import'}[args.command],'expected_revision':revision}
            if args.command=='import':body['definition']=Scenario.model_validate_json(Path(args.file).read_text(encoding='utf-8')).model_dump()
            else:body['scenario_id']=args.id
            result=await call('PUT','/api/v1/development-network',body)
        elif args.command=='apply-event':
            body=json.loads(Path(args.file).read_text(encoding='utf-8'));body['expected_revision']=revision
            result=await call('POST','/api/v1/development-network/interface-event',body)
        elif args.command=='evaluate':
            from phase_d_audit import Run,source_manifest,digest
            run=Run('scenario-evaluation','real_model_full_agent',{'scenario':current['context'],'source_digest':digest(json.dumps(source_manifest(),sort_keys=True).encode()),'model':args.model})
            from uuid import uuid4
            conversation=await call('POST','/api/v1/ai/conversations',{'assistant_kind':'floating'})
            import time
            started=time.monotonic()
            result=await call('POST','/api/v1/ai/conversations/'+conversation['id']+'/turns',{'request_id':str(uuid4()),'prompt':args.prompt,'model':args.model})
            run.record('D-SCENARIO-EXPLORATORY','NOT RUN',expected='Independent expected-output grading required; transport is not a behavioral pass',actual=result,prompt=args.prompt,latency_ms=round((time.monotonic()-started)*1000,2))
            result={'run':str(run.path),'response':result}
        else:raise ValueError('Unknown command')
        print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('bundle-create');p.add_argument('--id',required=True);p.add_argument('--output',required=True);p.add_argument('--variant',choices=['healthy','acl','conflict'],default='healthy');p.add_argument('--linked-configs',action='store_true')
    for name in ['bundle-validate','bundle-import']:
        p=sub.add_parser(name);p.add_argument('directory')
    for name in ['bundle-clone','bundle-export']:
        p=sub.add_parser(name);p.add_argument('directory');p.add_argument('--output',required=True)
        if name=='bundle-clone':p.add_argument('--id',required=True)
    p=sub.add_parser('bundle-diff');p.add_argument('before');p.add_argument('after');p.add_argument('--output')
    sub.add_parser('schema');p=sub.add_parser('validate');p.add_argument('file')
    p=sub.add_parser('create');p.add_argument('--from',dest='base');p.add_argument('--seed',type=int);p.add_argument('--variant',choices=['healthy','interface_down','return_route','acl','ospf_timer','bgp_as','conflict'],default='healthy');p.add_argument('--id',required=True);p.add_argument('--output',required=True)
    for name in ['list','show','activate','reset','import','export','apply-event','evaluate']:
        p=sub.add_parser(name);p.add_argument('--expected-revision')
        if name in ['activate','reset']:p.add_argument('id')
        if name in ['import','apply-event']:p.add_argument('file')
        if name=='export':p.add_argument('--output',required=True)
        if name=='evaluate':p.add_argument('--prompt',required=True);p.add_argument('--model',default='qwen2.5:1.5b')
    asyncio.run(main(parser.parse_args()))
