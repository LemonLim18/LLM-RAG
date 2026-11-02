"""Scoped LangChain adapters. All invocations enter the existing typed registry."""
import asyncio
from copy import deepcopy
from uuid import uuid4
from fastapi import HTTPException
from langchain_core.tools import StructuredTool
from langsmith import tracing_context
from llm.gateway_network import READ_TOOLS


def _record_refs(value):
    """Source-owned record identities only; no inferred observations."""
    if isinstance(value,dict):
        if 'id' in value and ('kind' in value or 'config_text' in value):
            yield str(value['id'])
        for item in value.values():yield from _record_refs(item)
    elif isinstance(value,list):
        for item in value:yield from _record_refs(item)


class AuthorizedTools:
    def __init__(self,registry,store,authorization,max_calls=8,names=READ_TOOLS,effects=frozenset({'read'})):
        self.registry=registry;self.store=store;self.authorization=authorization
        self.max_calls=max_calls;self.calls=0;self.results=[];self.tools={};self.requests=[]
        self.stage_deadline=None
        for name in sorted(names & authorization.allowed_tools):
            cap=registry.capability(name)
            if not cap or cap.effect not in effects:continue
            async def invoke(selected=name,**arguments):
                if self.calls>=self.max_calls:raise HTTPException(429,'Agent tool-call budget exhausted')
                self.store.get(authorization.conversation_id,authorization.principal,authorization.assistant_kind)
                self.calls+=1
                invocation_id=uuid4().hex
                # The closure contains server-created authorization. It is absent
                # from the model schema, state, tool arguments and checkpoint data.
                error_kind=None
                try:
                    if self.stage_deadline is None:result=await registry.invoke(selected,arguments,authorization)
                    else:
                        seconds=max(.001,self.stage_deadline-__import__('time').monotonic())
                        result=await asyncio.wait_for(registry.invoke(selected,arguments,authorization),timeout=seconds)
                except (asyncio.TimeoutError,HTTPException,ValueError,RuntimeError) as exc:
                    if effects!=frozenset({'read'}) or isinstance(exc,HTTPException) and exc.status_code in {401,403}:raise
                    error_kind='READER_TIMEOUT' if isinstance(exc,asyncio.TimeoutError) else 'INVALID_READER_PARAMETERS' if isinstance(exc,ValueError) else 'READER_FAILURE'
                    from llm.gateway_models import ToolResult
                    result=ToolResult(status='unavailable',message='Authorized reader timed out or is unavailable; no measurements were substituted.')
                # Projection/model state must not be able to mutate the record
                # against which its own claims will later be checked.
                scenario=result.data.get('scenario',{}) if isinstance(result.data,dict) else {}
                receipt={'invocation_id':invocation_id,'tool':selected,'parameters':deepcopy(arguments),
                    'status':result.status,'invocation_status':'failed' if error_kind else 'completed','error_kind':error_kind,
                    'truncated':bool(isinstance(result.data,dict) and result.data.get('truncated') or
                        isinstance(result.data,list) and any(isinstance(d,dict) and d.get('retrieval_coverage',{}).get('truncated') for d in result.data)),
                    'source_revisions':list(dict.fromkeys(v for v in [
                        *(e.source_revision for e in result.evidence),scenario.get('source_revision')] if v)),
                    'evidence_ids':[e.id for e in result.evidence],
                    'record_refs':list(dict.fromkeys(_record_refs(result.data)))}
                result._invocation_receipt=deepcopy(receipt)
                self.results.append((selected,result.model_copy(deep=True)))
                self.requests.append(receipt)
                return result
            self.tools[name]=StructuredTool.from_function(name=name.replace('.','_'),description='Authorized local '+cap.effect+': '+name,
                args_schema=cap.input_model,coroutine=invoke,infer_schema=False)

    async def invoke(self,name,arguments,authorization):
        if authorization!=self.authorization or name not in self.tools:
            raise HTTPException(403,'Agent tool is not authorized')
        with tracing_context(enabled=False):
            return await self.tools[name].ainvoke(arguments)
