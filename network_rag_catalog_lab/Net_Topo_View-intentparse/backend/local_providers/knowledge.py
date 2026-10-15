"""Authenticated adapter to the existing V9 knowledge services."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from auth.rbac import require_any, require_engineer, require_admin
from lab_config import PROJECT_DIR

router = APIRouter(prefix='/knowledge', tags=['Knowledge Engineering'])


def knowledge_root():
    path = Path(os.getenv('COGNISHIELD_KNOWLEDGE_ROOT', str(PROJECT_DIR / 'backend/knowledge_workspace'))).resolve()
    if not path.is_relative_to(PROJECT_DIR.resolve()):
        raise HTTPException(503, 'Knowledge workspace must remain inside CogniShield.')
    return path


def invoke(action, body, actor):
    root = Path(os.getenv('COGNISHIELD_V9_ROOT', str(PROJECT_DIR.parent / 'network_rag_catalog_v2'))).resolve()
    python = Path(os.getenv('COGNISHIELD_V9_PYTHON', str(PROJECT_DIR.parents[1] / '.venv/Scripts/python.exe')))
    payload = dict(root=str(root), base=str(knowledge_root()), action=action, body=body, actor=actor)
    try:
        result = subprocess.run([str(python), '-B', str(Path(__file__).with_name('knowledge_worker.py'))],
            input=json.dumps(payload), capture_output=True, text=True, encoding='utf-8', timeout=300,
            cwd=PROJECT_DIR, env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'})
        output = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(503, 'V9 knowledge service unavailable; no fallback used.') from exc
    if not output.get('ok'):
        issues = output.get('issues', [])
        code = 409 if any(i.get('code') in {'STALE_REVISION', 'AUTHORING_BUSY'} for i in issues) else 422
        raise HTTPException(code, {'message': 'V9 rejected the knowledge change.', 'issues': issues})
    return output


class Change(BaseModel):
    expected_revision: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)
    changes: list[dict] = Field(min_length=1, max_length=100)


class TemplateEdit(BaseModel):
    expected_revision: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)
    path: str
    content: str = Field(max_length=200000)
    operation_id: str | None = None
    vendor: str | None = None
    platform: str | None = None
    versions: list[str] | None = None


class Publication(BaseModel):
    mode: Literal["chroma", "offline"] = "chroma"
    expected_revision: str = Field(min_length=1)
    expected_release: str | None
    reason: str = Field(min_length=1, max_length=1000)


class Initialize(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


@router.get('')
async def inspect(user=Depends(require_any)):
    return await asyncio.to_thread(invoke, 'inspect', {}, user['username'])


@router.post('/initialize')
async def initialize(body: Initialize, user=Depends(require_admin)):
    return await asyncio.to_thread(invoke, 'initialize', body.model_dump(), user['username'])


@router.post('/edit')
async def edit(body: Change, user=Depends(require_engineer)):
    return await asyncio.to_thread(invoke, 'edit', body.model_dump(), user['username'])


@router.put('/template')
async def template(body: TemplateEdit, user=Depends(require_engineer)):
    return await asyncio.to_thread(invoke, 'template', body.model_dump(), user['username'])


@router.post('/validate')
async def validate(user=Depends(require_engineer)):
    return await asyncio.to_thread(invoke, 'validate', {}, user['username'])


@router.get('/schema/{operation_id}')
async def schema(operation_id: str, user=Depends(require_any)):
    return await asyncio.to_thread(invoke, 'schema', {'operation_id': operation_id}, user['username'])


@router.post('/publish')
async def publish(body: Publication, user=Depends(require_admin)):
    return await asyncio.to_thread(invoke, 'publish', body.model_dump(), user['username'])

class Activation(BaseModel):
    release_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    expected_release: str | None
    reason: str = Field(min_length=1, max_length=1000)

class RenderPreview(BaseModel):
    expected_revision: str
    path: str
    content: str = Field(max_length=200000)
    parameters: dict

@router.post('/build')
async def build_release(body: Publication, user=Depends(require_engineer)):
    return await asyncio.to_thread(invoke, 'build', body.model_dump(), user['username'])

@router.post('/activate')
async def activate_release(body: Activation, user=Depends(require_admin)):
    return await asyncio.to_thread(invoke, 'activate', body.model_dump(), user['username'])

@router.get('/releases/{release_id}')
async def release_details(release_id: str, user=Depends(require_any)):
    return await asyncio.to_thread(invoke, 'release', {'release_id':release_id}, user['username'])

@router.post('/render')
async def render_template(body: RenderPreview, user=Depends(require_engineer)):
    return await asyncio.to_thread(invoke, 'render', body.model_dump(), user['username'])
