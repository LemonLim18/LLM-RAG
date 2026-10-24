"""Restart recovery reads the owned current V9 review without rerunning a model."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db.manager import DatabaseManager
from llm.gateway_store import ConversationStore, ensure_schema
from llm.gateway_api import router, gateway, require_ai_user
from local_providers import v9_studio


@pytest.fixture
def recovery(tmp_path, monkeypatch):
    db = DatabaseManager(str(tmp_path / 'recovery.db'))
    db.initialize(); ensure_schema(db); v9_studio.ensure_schema(db)
    store = ConversationStore(db)
    cid = store.create('owner', 'studio')['id']
    task = dict(intent_id='task-1', category='ospf', operation_id='set_ospf_router_id',
                parameters={'process_id': 44, 'router_id': '198.51.100.44'}, parameter_provenance={},
                target_devices=[], issues=[], status='clarification', request_text='Set the recorded router ID')
    output = dict(plan=dict(tasks=[task], status='clarification', issues=[]),
                  schema=dict(properties={}), schemas={'task-1': dict(properties={})}, release_id='published')
    data = [dict(hostname='R1', interfaces=[], scenario_revision='revision-one')]
    monkeypatch.setattr(v9_studio, 'inventory', lambda _: data)
    monkeypatch.setattr(v9_studio, 'worker', lambda *_: pytest.fail('Recovery must not invoke V9 or the model'))
    monkeypatch.setattr('llm.gateway_knowledge.read_release', lambda *_: (None, {}, {'release_id': 'published'}))
    with db._connect() as c:
        c.execute('INSERT INTO studio_v9_sessions(id,owner,prompt,body,inventory_hash,revision) VALUES (?,?,?,?,?,?)',
                  ('review-one', 'owner', 'Original request', json.dumps(output), v9_studio.digest(data), 7))
    store.begin(cid, 'owner', 'turn-one', 'hash', 'Original request')
    store.finish(cid, 'owner', 'turn-one', dict(answer='Review this interpretation', kind='generation_preview',
                 preview={'parsed_intent': {'_v9_session': 'review-one'}, 'session_revision': 1}, evidence=[]))
    app = FastAPI(); app.include_router(router)
    app.dependency_overrides[gateway] = lambda: SimpleNamespace(db=db, store=store)
    user = {'username': 'owner', 'role': 'engineer', 'user_id': 1}
    app.dependency_overrides[require_ai_user] = lambda: user
    with TestClient(app) as client:
        yield db, store, cid, output, data, user, client
    db.close()


def test_history_exposes_only_a_review_reference_and_read_restores_latest_revision(recovery):
    db, store, cid, output, data, user, client = recovery
    history = client.get('/api/v1/ai/conversations/' + cid).json()
    assert history['messages'][-1]['gatewayReviewRequestId'] == 'turn-one'
    before = store.get(cid, 'owner')['messages']
    result = client.get(f'/api/v1/ai/conversations/{cid}/turns/turn-one/review')
    assert result.status_code == 200
    restored = result.json()
    assert restored['preview']['session_revision'] == 7  # Stored turn contains stale revision1.
    assert restored['preview']['inventory_revision'] == 'revision-one'
    assert restored['preview']['tasks'][0]['parsed_intent']['parameters']['router_id'] == '198.51.100.44'
    assert restored['prompt'] == 'Original request' and restored['conversation'] == cid
    assert v9_studio.session(db, 'review-one', 'owner')['revision'] == 7
    assert store.get(cid, 'owner')['messages'] == before
    assert client.get('/api/v1/ai/conversations?assistant_kind=studio').json()['sessions'][0]['messages'][-1]['gatewayReviewRequestId'] == 'turn-one'


def test_recovery_rejects_other_owner_other_surface_and_stale_inventory(recovery):
    db, store, cid, output, data, user, client = recovery
    path = f'/api/v1/ai/conversations/{cid}/turns/turn-one/review'
    user['username'] = 'other'
    assert client.get(path).status_code == 404
    user['username'] = 'owner'
    floating = store.create('owner', 'floating')['id']
    assert client.get(f'/api/v1/ai/conversations/{floating}/turns/turn-one/review').status_code == 404
    assert client.get(f'/api/v1/ai/conversations/{cid}/turns/nonexistent/review').status_code == 404
    data[0]['scenario_revision'] = 'revision-two'
    assert client.get(path).status_code == 409
    assert v9_studio.session(db, 'review-one', 'owner')['revision'] == 7


def test_recovery_rejects_changed_release_and_auditor_and_does_not_expose_edit_proposals(recovery):
    db, store, cid, output, data, user, client = recovery
    path = f'/api/v1/ai/conversations/{cid}/turns/turn-one/review'
    user['role'] = 'auditor'
    assert client.get(path).status_code == 403
    user['role'] = 'engineer'
    output['release_id'] = 'old-release'
    with db._connect() as c:
        c.execute('UPDATE studio_v9_sessions SET body=? WHERE id=?', (json.dumps(output), 'review-one'))
    assert client.get(path).status_code == 409
    store.begin(cid, 'owner', 'edit-turn', 'edit-hash', 'Propose an edit')
    store.finish(cid, 'owner', 'edit-turn', dict(answer='Proposed', kind='edit_proposal', proposal={'original': 'private'}, evidence=[]))
    messages = client.get('/api/v1/ai/conversations/' + cid).json()['messages']
    assert 'gatewayReviewRequestId' not in messages[-1] and 'proposal' not in messages[-1]
    assert client.get(f'/api/v1/ai/conversations/{cid}/turns/edit-turn/review').status_code == 404


def test_restored_playbook_review_keeps_its_type_and_rechecks_published_support(recovery):
    db, store, cid, output, data, user, client = recovery
    with db._connect() as c:
        row = c.execute('SELECT result FROM ai_turns WHERE conversation_id=?', (cid,)).fetchone()
        result = json.loads(row[0]); result['preview']['output_kind'] = 'playbook'
        c.execute('UPDATE ai_turns SET result=? WHERE conversation_id=?', (json.dumps(result), cid))
    response = client.get(f'/api/v1/ai/conversations/{cid}/turns/turn-one/review')
    assert response.status_code == 200
    preview = response.json()['preview']
    assert preview['output_kind'] == 'playbook'
    assert preview['playbook_support']['status'] == 'unsupported'
