"""Optional local vision through the shared provider. No remote URLs or downloads."""
import asyncio
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import httpx
from lab_config import LOCAL_OLLAMA_URL
from llm.validation_process import bounded_process


def normalize_images(rows, pages):
    executable=os.getenv('COGNISHIELD_DOCUMENT_PYTHON',__import__('sys').executable)
    renderer=os.getenv('COGNISHIELD_PDF_RENDERER') or shutil.which('pdftoppm')
    images=[]; labels=[]
    with tempfile.TemporaryDirectory(prefix='cognishield-vision-') as directory:
        root=Path(directory)
        for row in rows:
            if not row['original_bytes']: continue
            suffix=Path(row['name']).suffix.lower()
            if suffix not in {'.pdf','.png','.jpg','.jpeg','.webp'}: continue
            selected=pages or [1]
            if suffix!='.pdf': selected=[1]
            for page in selected[:3]:
                if len(images)>=3: break
                raster=root/'image.png'
                if suffix=='.pdf':
                    if not renderer: continue
                    (root/'document.pdf').write_bytes(row['original_bytes'])
                    result=bounded_process([renderer,'-f',str(page),'-l',str(page),'-scale-to','1600','-singlefile','-png',str(root/'document.pdf'),str(root/'image')],'',timeout=15)
                    if result.returncode: continue
                else:
                    result=bounded_process([executable,'-I','-B',str(Path(__file__).with_name('document_extract_worker.py'))],json.dumps({'data':base64.b64encode(row['original_bytes']).decode('ascii'),'image_path':str(raster)}),timeout=20)
                    if not json.loads(result.stdout).get('ok'): continue
                if raster.is_file() and raster.stat().st_size<3*1024*1024:
                    images.append(base64.b64encode(raster.read_bytes()).decode('ascii'))
                    labels.append(row['name']+' page '+str(page))
    return images,labels


async def vision_context(db, conversation, owner, body, documents=None):
    selected=os.getenv('COGNISHIELD_VISION_MODEL') or body.model
    if not selected: return [],[],None
    from local_providers.chat import is_document_only_model
    if is_document_only_model(selected): return [],[],None
    # Only use the existing local endpoint and a model advertising vision.
    try:
        async with httpx.AsyncClient(timeout=5,trust_env=False) as client:
            response=await client.post(LOCAL_OLLAMA_URL+'/api/show',json={'model':selected})
            response.raise_for_status()
            if 'vision' not in response.json().get('capabilities',[]): return [],[],None
        with db._connect() as connection:
            rows=[dict(row) for row in connection.execute('SELECT id,name,original_bytes,segments FROM ai_attachments WHERE conversation_id=? AND owner=? ORDER BY rowid DESC LIMIT 5',(conversation,owner))]
        if body.attachment_ids: rows=[row for row in rows if row['id'] in {str(value) for value in body.attachment_ids}]
        if documents is not None:rows=[row for row in rows if row['name'] in {d['source'] for d in documents}]
        from llm.gateway_documents import requested_document_pages
        available={part['page'] for row in rows for part in json.loads(row['segments']) if part.get('page') is not None}
        selected_pages=sorted({d['page'] for d in documents if d.get('page') is not None}) if documents is not None else requested_document_pages(body.prompt,available)
        pages=[page for page in selected_pages if page in available and 0<page<=200]
        images,labels=await asyncio.to_thread(normalize_images,rows,pages)
        return images,labels,selected
    except (httpx.HTTPError,ValueError,OSError,RuntimeError,subprocess.TimeoutExpired):
        return [],[],None
