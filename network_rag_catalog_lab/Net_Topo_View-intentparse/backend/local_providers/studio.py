"""Local infrastructure for the original Studio preview and generation services."""
import os
from fastapi import HTTPException
from lab_config import LOCAL_OLLAMA_URL, LOCAL_OLLAMA_MODEL
from llm.ollama_provider import OllamaProvider
from ansible.builder import PlaybookBuilder
from local_providers.authoring import AuthoringStore

def provider(model=None):
    selected = model or os.getenv('COGNISHIELD_LOCAL_OLLAMA_MODEL', LOCAL_OLLAMA_MODEL)
    if not selected or selected == 'auto':
        import httpx
        try:
            with httpx.Client(trust_env=False, timeout=5) as client:
                response = client.get(LOCAL_OLLAMA_URL + '/api/tags')
                response.raise_for_status()
                selected = next(m['name'] for m in response.json()['models'] if 'embed' not in m['name'].lower())
        except (httpx.HTTPError, KeyError, StopIteration, ValueError) as exc:
            raise HTTPException(503, 'No installed local Ollama chat model is reachable') from exc
    return OllamaProvider(base_url=LOCAL_OLLAMA_URL, model=selected, timeout=180)

class LocalBuilder(PlaybookBuilder):
    def _lint_issues(self, yaml_text):
        # Structural, inventory and safety validators still run in the base class.
        # Do not launch the Linux-oriented Ansible controller in native local mode.
        return []

def canonical_path(path):
    if path.startswith('generated/'):
        from ansible.api import _generated_virtual_to_real
        return _generated_virtual_to_real(path) or ('playbooks/' + path)
    return path

def save_artifact(db, path, content):
    store = AuthoringStore(db)
    path = canonical_path(path)
    try:
        store.read('ansible', path)
        operation = 'save'
    except FileNotFoundError:
        operation = 'create'
    return store.mutate('ansible', path, content, 'studio-generator', operation)

def read_artifact(db, path):
    try:
        return AuthoringStore(db).read('ansible', canonical_path(path))
    except FileNotFoundError:
        return None

def initialize(db):
    from ansible import api
    # Provider selection is deferred to the request so startup needs no model connection.
    api.setup_ansible(LocalBuilder(OllamaProvider(base_url=LOCAL_OLLAMA_URL, model=LOCAL_OLLAMA_MODEL)), None, None, db)
