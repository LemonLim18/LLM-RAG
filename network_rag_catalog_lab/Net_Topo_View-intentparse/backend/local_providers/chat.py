"""Local inference adapter using the existing Ollama provider; never executes tools."""
import httpx
import os
from fastapi import HTTPException
from lab_config import LOCAL_OLLAMA_URL, LOCAL_OLLAMA_MODEL
from llm.provider import LLMMessage

async def runtime():
    try:
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            response=await client.get(LOCAL_OLLAMA_URL+'/api/tags')
            response.raise_for_status()
            models=[m['name'] for m in response.json().get('models',[]) if 'embed' not in m['name'].lower()]
        configured = os.getenv('COGNISHIELD_LOCAL_OLLAMA_MODEL', LOCAL_OLLAMA_MODEL)
        model=configured if configured!='auto' else (models[0] if models else '')
        available=model in models
        error=None if available else 'No configured chat model is installed in local Ollama.'
    except (httpx.HTTPError, ValueError, KeyError):
        models=[]; model=''; available=False; error='Cannot reach the configured local Ollama service.'
    return {'active_provider':'ollama','active_model':model,'active_base_url':LOCAL_OLLAMA_URL,
        'providers':[{'name':'ollama','label':'Local Ollama','base_url':LOCAL_OLLAMA_URL,'models':models,'available':available,'reachable':bool(models),'error':error}],
        'source':'real','scope':'process','execution_available':False}

async def generate(messages, structured=False):
    state = await runtime()
    if not state['providers'][0]['available']:
        raise HTTPException(503, state['providers'][0]['error'])
    payload = {'model': state['active_model'], 'messages': messages, 'stream': False,
               'options': {'temperature': 0.2, 'num_predict': 1800}}
    if structured:
        payload['format'] = 'json'
    try:
        # Local inference must bypass corporate/VM proxy environment settings.
        async with httpx.AsyncClient(timeout=180, trust_env=False) as client:
            response = await client.post(LOCAL_OLLAMA_URL + '/api/chat', json=payload)
            response.raise_for_status()
            content = response.json()['message']['content'].strip()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(502, 'Local Ollama inference failed. Check the configured endpoint and installed model; no artificial reply was substituted.') from exc
    if not content:
        raise HTTPException(502, 'Local Ollama returned an empty answer')
    return content, state['active_model']

async def answer(question, content, history):
    state=await runtime()
    if not state['providers'][0]['available']:
        raise HTTPException(503,state['providers'][0]['error'])
    messages=[LLMMessage(role='system',content='You are CogniShield network authoring assistant. Help explain and write configurations and Ansible files. Network observations in this lab are simulated. You have no execution tools: never claim that a command, save, approval or deployment happened. Return authored content for user review.')]
    messages.extend(LLMMessage(role=m['role'],content=m['content']) for m in history[-20:] if m.get('role') in {'user','assistant'} and isinstance(m.get('content'),str))
    messages.append(LLMMessage(role='user',content=question+ ('\n\nFile context:\n'+content if content else '')))
    content, model = await generate([{'role': m.role, 'content': m.content} for m in messages])
    return {'answer': content, 'model': model, 'source': 'real'}
