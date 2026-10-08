"""Opt-in live probe: calls local models/retrieval and saves ONE normal V9 session.

Run explicitly with the project venv; not collected by unittest discovery.
No ingestion, publication, device execution or session refresh is performed.
"""
from contextlib import ExitStack
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from app.config import OLLAMA_EMBED_MODEL, OLLAMA_LLM_MODEL, SESSIONS_DIR, runtime_mode
from app.embeddings import embeddings
from app.llm import llm
from app.knowledge.runtime import snapshot_scope
from app.retrieval.operation_retriever import retrieve_operation_candidates
from app.vectorstore import get_vectorstore
from app.workbench.api import create_app


def main():
    print('CONFIG', json.dumps({'runtime': runtime_mode(), 'llm': OLLAMA_LLM_MODEL,
          'embeddings': OLLAMA_EMBED_MODEL, 'ollama_host': os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434')}), flush=True)
    tags = httpx.get('http://127.0.0.1:11434/api/tags', timeout=10).json()
    print('INSTALLED', [model['name'] for model in tags['models']], flush=True)
    print('INFERENCE', repr(llm.invoke('Reply with exactly OK.').content), flush=True)
    print('EMBEDDING_DIMENSIONS', len(embeddings.embed_query('Iteration 4 readiness probe')), flush=True)
    with snapshot_scope():
        index = get_vectorstore()
        print('INDEX_RECORDS', len(index.get(include=[])['ids']), flush=True)
        print('SEMANTIC_RESULTS', [doc.metadata.get('operation_id') for doc in index.similarity_search('create VLAN', k=2)], flush=True)

    # Spies delegate every call to the REAL configured implementations.
    model_spy = Mock(wraps=llm)
    embedding_spy = Mock(wraps=embeddings)
    retrieval_results = []
    def tracked_retrieval(*args, **kwargs):
        candidates = retrieve_operation_candidates(*args, **kwargs)
        retrieval_results.append([item['operation_id'] for item in candidates])
        return candidates

    with ExitStack() as stack:
        for target in ('app.llm.llm', 'app.planner.intent_planner.llm',
                       'app.parameters.parameter_extractor.llm', 'app.retrieval.category_classifier.llm',
                       'app.retrieval.operation_selector.llm'):
            stack.enter_context(patch(target, model_spy))
        stack.enter_context(patch('app.vectorstore.embeddings', embedding_spy))
        stack.enter_context(patch('app.pipeline.retrieve_operation_candidates', tracked_retrieval))
        client = stack.enter_context(TestClient(create_app()))
        response = client.post('/api/v1/planning/sessions', json={
            'prompt': 'Please provision a VLAN numbered 321 named AUDIT on R1.',
            'mode': 'local_v9', 'client_request_id': str(uuid4()),
        })
    print('HTTP_STATUS', response.status_code, flush=True)
    response.raise_for_status()
    session = response.json()['session']
    saved = json.loads((Path(SESSIONS_DIR) / f"{session['session_id']}.json").read_text(encoding='utf-8'))
    assert saved == session, 'Returned and saved session differ'
    print('SESSION', session['session_id'], session['status'], flush=True)
    print('ACTUAL_MODEL_CALLS', model_spy.invoke.call_count, flush=True)
    print('ACTUAL_RETRIEVAL_RESULTS', retrieval_results, flush=True)
    print('ACTUAL_QUERY_EMBEDDINGS', embedding_spy.embed_query.call_count, flush=True)
    print('TASKS', json.dumps([{'id': task['intent_id'], 'operation': task['operation_id'],
          'device': task['device_id'], 'status': task['status'], 'feedback': task['feedback'],
          'issues': [issue['type'] for issue in task['issues']]} for task in session['plan']['tasks']]), flush=True)
    print('PENDING_QUESTIONS', len(session['pending_questions']), flush=True)


if __name__ == '__main__':
    main()
