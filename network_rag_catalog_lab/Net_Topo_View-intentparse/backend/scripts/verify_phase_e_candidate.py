"""Read-only candidate/index and approval-gate checks using the V9 runtime.

Run with the configured V9 Python. No activation, new approval or device action.
"""
import argparse,json,os,sys
from pathlib import Path
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'backend/local_providers'),str(ROOT.parent/'network_rag_catalog_v2')]
os.environ['ANONYMIZED_TELEMETRY']='False'


def main(args):
    base=ROOT/('backend/knowledge_workspace' if args.ordinary else 'tmp/phase-d/acceptance-knowledge')
    from local_providers.v9_worker import protect_source
    protect_source(ROOT.parent/'network_rag_catalog_v2')
    from local_providers.knowledge_lifecycle import pointer_for,configure_embeddings,configure_native_contracts
    from local_providers.knowledge_review import assert_activation_authorized
    from app.knowledge.authority import authoring_store
    configure_native_contracts()
    releases=base/'storage/catalog_releases';before=(releases/'active.json').read_bytes();current=json.loads(before)
    pointer,snapshot=pointer_for(releases,args.release);_,previous=pointer_for(releases,current['release_id'])
    info=snapshot.manifest['cognishield_engineer_reviews'];reviews=snapshot.read_json(info['artifact_path'])['bindings']
    assert len(reviews)==141 and len(snapshot.manifest['template_bindings'])==141
    assert all(r['checks']['status']=='PASS' and all(p['wrong_profile_rejected'] and p['rendered_fixtures'] for p in r['runtime_checks']['profiles']) for r in reviews)
    # Re-execute the existing V9 renderer now; frozen build results alone do not
    # prove the current host still renders the active package identically.
    from local_providers.knowledge_lifecycle import guard_native_renderer
    from local_providers.knowledge_review import identity
    from app.knowledge.runtime import snapshot_scope
    render=guard_native_renderer();executed=0
    with snapshot_scope(snapshot):
        for binding in snapshot.manifest['template_bindings']:
            row=next(r for r in reviews if r['identity']==identity(binding))
            device={'hostname':'CONTROLLED-RUNTIME-READONLY','vendor':binding['vendor'],'platform':binding['platform'],'version':binding['versions'][0]}
            for fixture in row['method']['fixtures']:
                assert render(device,binding['operation_id'],fixture['parameters']).strip()==fixture['expected_output'].strip()
                executed+=1
    retrieval=snapshot.manifest['retrieval'];assert retrieval['mode']=='chroma' and retrieval['ready']
    configure_embeddings()
    import app.embeddings as module
    from langchain_chroma import Chroma
    from chromadb.config import Settings
    index=Path(retrieval['index_path']).resolve();assert index.is_relative_to(base.resolve())
    store=Chroma(collection_name=retrieval['collection'],persist_directory=str(index),embedding_function=module.embeddings,
        create_collection_if_not_exists=False,client_settings=Settings(anonymized_telemetry=False))
    actual=store.get(include=['documents','metadatas']);expected={r['id']:r for r in snapshot.read_json('retrieval_documents.json')}
    assert set(actual['ids'])==set(expected) and len(expected)==47
    for identity,text,metadata in zip(actual['ids'],actual['documents'],actual['metadatas']):
        assert text==expected[identity]['page_content'] and metadata==expected[identity]['metadata']
    retrieval_smoke=[]
    for query,operation in [('Configure a BGP neighbor with local AS, remote AS and neighbor IP','configure_bgp_neighbor'),
            ('Set the OSPF router ID for an existing OSPF process','set_ospf_router_id'),
            ('Configure an IPv4 static route with destination prefix and next hop','configure_static_route'),
            ('Apply an ACL to a device interface in a direction','apply_acl_to_interface'),
            ('Configure traffic policing with a rate and burst size','configure_policing')]:
        found=[doc.metadata.get('operation_id') for doc in store.similarity_search(query,k=5)]
        retrieval_smoke.append({'query':query,'expected_operation':operation,'retrieved_operations':found,'pass':operation in found})
    denied=None
    if info['approved']==0:
        with authoring_store(base)._connection() as connection:
            try:assert_activation_authorized(connection,snapshot,previous)
            except ValueError as exc:denied=str(exc)
            else:raise AssertionError('Unapproved candidate would activate')
    assert (releases/'active.json').read_bytes()==before
    result={'release':pointer,'bindings':141,'declared_profiles':sum(len(r['runtime_checks']['profiles']) for r in reviews),
        'positive_fixtures':sum(sum(c['kind']=='positive' for c in r['checks']['results']) for r in reviews),
        'negative_fixtures':sum(sum(c['kind']=='negative' for c in r['checks']['results']) for r in reviews),
        'chroma_index_documents_exact':47,'retrieval_smoke':retrieval_smoke,'engineer_authorizations':info['approved'],
        'authorization_actions':sorted({r['approval'].get('approval_action','explicit_review') for r in reviews if r.get('approval')}),
        'current_host_renders_executed':executed,'unapproved_activation_denied':denied,
        'active_unchanged':current,'runtime_scope':'Existing V9 snapshot binding and renderer, active or candidate as identified by pointer; not full Studio target-resolution or deployment'}
    dest=(ROOT/args.output).resolve() if args.output else ROOT/'tmp/phase-e'/('ordinary-' if args.ordinary else 'acceptance-')/(args.release+'-verified.json')
    if not dest.is_relative_to((ROOT/'tmp').resolve()):raise ValueError('Verification artifacts must remain under the ignored workspace tmp directory')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf-8') as file:json.dump(result,file,indent=2)
    print(json.dumps(result),flush=True)
    assert all(r['pass'] for r in retrieval_smoke),'Scoped retrieval smoke failed; original results retained'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('release');p.add_argument('--ordinary',action='store_true');p.add_argument('--output',help='New exclusive artifact path under workspace tmp; preserves earlier verification evidence');main(p.parse_args())
