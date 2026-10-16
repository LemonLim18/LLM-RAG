"""Local OCR orchestration reusing the bounded extraction process boundary.

Each decoder/renderer/OCR process runs separately (one process per job). Resource
limits are not a full security sandbox: no document macros, external links or
document-specified commands are invoked. No models or packages are installed.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
import time

from llm.validation_process import bounded_process


async def ollama_ocr(raster, model, timeout=30):
    """Optional installed OCR model, using the same local provider and no tools."""
    import asyncio
    import base64
    import httpx
    from lab_config import LOCAL_OLLAMA_URL
    from llm.ollama_provider import OllamaProvider
    from llm.provider import LLMMessage
    async with httpx.AsyncClient(timeout=min(timeout,5),trust_env=False) as client:
        response=await client.post(LOCAL_OLLAMA_URL+'/api/show',json={'model':model})
        response.raise_for_status()
        if 'vision' not in response.json().get('capabilities',[]):
            raise ValueError('Configured OCR model does not advertise image input support')
    if raster.stat().st_size>8*1024*1024: raise ValueError('OCR image exceeds 8 MiB')
    provider=OllamaProvider(base_url=LOCAL_OLLAMA_URL,model=model,timeout=timeout,
                            max_output_tokens=4096,context_tokens=8192)
    result=await asyncio.wait_for(provider.generate([LLMMessage(role='user',content='',
        images=[base64.b64encode(raster.read_bytes()).decode('ascii')])],temperature=0),timeout=timeout)
    if not result.content.strip(): raise ValueError('OCR model returned no readable text')
    return {'ok':True,'text':result.content.strip(),'language':'model-detected','engine':model}


def complete_ocr(data, segments, executable, image=False):
    import base64
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='cognishield-ocr-') as directory:
        root=Path(directory)
        source=root/'document.pdf'
        if not image: source.write_bytes(data)
        renderer=os.getenv('COGNISHIELD_PDF_RENDERER') or shutil.which('pdftoppm')
        powershell=shutil.which('powershell.exe') if os.name=='nt' else None
        ocr_model=os.getenv('COGNISHIELD_OCR_MODEL','').strip()
        attempts=0
        for segment in segments:
            if not segment.get('needs_ocr'): continue
            segment['visual_understanding']='unavailable; OCR reads text, not diagram relationships'
            if not powershell and not ocr_model:
                segment['limitation']='Local Windows OCR is unavailable on this host'; continue
            if attempts>=24 or time.monotonic()-started>90:
                segment['limitation']='OCR processing limit reached (24 pages / 90 seconds)'; continue
            attempts+=1
            raster=root/'page.png'
            try:
                if image:
                    result=bounded_process([executable,'-I','-B',str(Path(__file__).with_name('document_extract_worker.py'))],
                        json.dumps({'data':base64.b64encode(data).decode('ascii'),'image_path':str(raster)}),timeout=20)
                    decoded=json.loads(result.stdout)
                    if not decoded.get('ok'): raise ValueError(decoded.get('error','Image decoding failed'))
                else:
                    if not renderer: raise ValueError('PDF OCR needs local Poppler pdftoppm; configure COGNISHIELD_PDF_RENDERER')
                    result=bounded_process([renderer,'-f',str(segment['page']),'-l',str(segment['page']),'-scale-to','2500',
                        '-singlefile','-png',str(source),str(root/'page')],'',timeout=15)
                    if result.returncode or not raster.exists(): raise ValueError('PDF page rendering failed')
                if ocr_model:
                    import asyncio
                    output=asyncio.run(ollama_ocr(raster,ocr_model,timeout=max(1,min(30,90-(time.monotonic()-started)))))
                else:
                    result=bounded_process([powershell,'-NoProfile','-NonInteractive','-ExecutionPolicy','RemoteSigned','-File',
                        str(Path(__file__).with_name('windows_ocr.ps1'))],json.dumps({'path':str(raster)}),timeout=15)
                    output=json.loads(result.stdout)
                if not output.get('ok'): raise ValueError(output.get('error','OCR failed'))
                text=output.get('text','').strip()
                if not text: raise ValueError('OCR found no readable text; visual interpretation is unavailable')
                segment['text'] += ('\n\nOCR text (may contain recognition errors):\n' if segment['text'] else '')+text
                segment['extraction']='direct_text_and_ocr' if segment['extraction']=='direct_text' else 'ocr'
                segment['ocr_language']=output.get('language')
                segment['ocr_engine']=output.get('engine','Windows.Media.Ocr')
                segment['needs_ocr']=False
                segment['limitation']='OCR can misread characters; non-text diagram semantics were not interpreted'
                if sum(len(s['text'].encode('utf-8')) for s in segments)>1000000:
                    raise ValueError('Extracted text exceeds 1 MiB')
            except Exception as exc:
                segment['limitation']=(str(exc) or ('OCR processing timed out' if isinstance(exc,TimeoutError) else 'OCR processing failed: '+type(exc).__name__))[:500]
    return segments
