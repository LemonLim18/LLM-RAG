"""LangChain model adapter using CogniShield's existing local model discovery."""
import asyncio
import os
import time
import httpx
from fastapi import HTTPException
from langchain_ollama import ChatOllama
from ollama import ResponseError
from langsmith import tracing_context
from local_providers.chat import runtime


async def chat_model(model=None, structured=False):
    state=await runtime()
    provider=state['providers'][0]
    selected=model or state['active_model']
    if selected not in provider['models']:
        raise HTTPException(503,'An installed conversational Ollama model is required; OCR and embedding models are excluded')
    return ChatOllama(model=selected,base_url=state['active_base_url'],temperature=0,
        num_ctx=8192,num_predict=512,format=('json' if structured is True else structured or ''),
        client_kwargs={'trust_env':False,'timeout':30},disable_streaming=True),selected


class RoutingModel:
    def __init__(self):
        self.calls=0;self.purposes={};self.input_characters=0
        self.inference_trace=[]
        evaluation=any(os.getenv(key,'0')=='1' for key in ['COGNISHIELD_AI_PLANNING','COGNISHIELD_AI_SYNTHESIS'])
        self.stage_limits={'routing':2,'retrieval':1,'synthesis':1,'repair':1} if evaluation else {'routing':3,'retrieval':1,'synthesis':1,'repair':0}
        self.max_calls=5 if evaluation else 3
        self.stage_limits['model_only']=1  # Isolated evaluation arm, no tools.
        self.max_input_characters=90000

    def available(self,purpose):
        return self.calls<self.max_calls and self.purposes.get(purpose,0)<self.stage_limits.get(purpose,0)

    async def generate(self,messages,structured=False,model=None,purpose='routing'):
        if not self.available(purpose):raise HTTPException(429,'Agent model-inference stage/shared budget exhausted')
        characters=sum(len(m['content']) for m in messages)
        if characters>32000:raise HTTPException(429,'Agent single-inference context budget exhausted')
        if self.input_characters+characters>self.max_input_characters:raise HTTPException(429,'Agent model input budget exhausted')
        client,selected=await chat_model(model,structured)
        self.calls+=1
        self.input_characters+=characters
        self.purposes[purpose]=self.purposes.get(purpose,0)+1
        started=time.monotonic()
        try:
            # Never require or inherit external tracing for local user context.
            with tracing_context(enabled=False):
                response=await asyncio.wait_for(client.ainvoke([(m['role'],m['content']) for m in messages]),timeout=30)
        except (asyncio.TimeoutError,httpx.HTTPError,ConnectionError,RuntimeError,ValueError,ResponseError) as exc:
            self.inference_trace.append({'purpose':purpose,'model':selected,'status':'provider_error',
                'error_type':type(exc).__name__,'elapsed_ms':round((time.monotonic()-started)*1000,2)})
            raise HTTPException(503,'Local routing model is unavailable or timed out; no tool action was inferred') from exc
        metadata=getattr(response,'response_metadata',{}) or {}
        usage=getattr(response,'usage_metadata',{}) or {}
        counts={}
        for name,raw in [('input_tokens',usage.get('input_tokens',metadata.get('prompt_eval_count'))),
                         ('output_tokens',usage.get('output_tokens',metadata.get('eval_count')))]:
            counts[name]=raw if type(raw) is int and raw>=0 else None
        reason=metadata.get('done_reason')
        self.inference_trace.append({'purpose':purpose,'model':selected,'status':'completed',
            'done_reason':reason[:80] if isinstance(reason,str) else None,**counts,
            'elapsed_ms':round((time.monotonic()-started)*1000,2)})
        if not isinstance(response.content,str) or not response.content.strip():
            raise HTTPException(503,'Local routing model returned no usable structured decision')
        return response.content.strip(),selected
