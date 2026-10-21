"""Scoped LangChain adapters. All invocations enter the existing typed registry."""
import asyncio
from fastapi import HTTPException
from langchain_core.tools import StructuredTool
from langsmith import tracing_context
from llm.gateway_network import READ_TOOLS


class AuthorizedTools:
    def __init__(self,registry,store,authorization,max_calls=8,names=READ_TOOLS,effects=frozenset({'read'})):
        self.registry=registry;self.store=store;self.authorization=authorization
        self.max_calls=max_calls;self.calls=0;self.results=[];self.tools={}
        for name in sorted(names & authorization.allowed_tools):
            cap=registry.capability(name)
            if not cap or cap.effect not in effects:continue
            async def invoke(selected=name,**arguments):
                if self.calls>=self.max_calls:raise HTTPException(429,'Agent tool-call budget exhausted')
                self.store.get(authorization.conversation_id,authorization.principal,authorization.assistant_kind)
                self.calls+=1
                # The closure contains server-created authorization. It is absent
                # from the model schema, state, tool arguments and checkpoint data.
                try:
                    result=await registry.invoke(selected,arguments,authorization)
                except (asyncio.TimeoutError,HTTPException,ValueError,RuntimeError) as exc:
                    if effects!=frozenset({'read'}) or isinstance(exc,HTTPException) and exc.status_code in {401,403}:raise
                    from llm.gateway_models import ToolResult
                    result=ToolResult(status='unavailable',message='Authorized reader timed out or is unavailable; no measurements were substituted.')
                # Projection/model state must not be able to mutate the record
                # against which its own claims will later be checked.
                self.results.append((selected,result.model_copy(deep=True)))
                return result
            self.tools[name]=StructuredTool.from_function(name=name.replace('.','_'),description='Authorized local '+cap.effect+': '+name,
                args_schema=cap.input_model,coroutine=invoke,infer_schema=False)

    async def invoke(self,name,arguments,authorization):
        if authorization!=self.authorization or name not in self.tools:
            raise HTTPException(403,'Agent tool is not authorized')
        with tracing_context(enabled=False):
            return await self.tools[name].ainvoke(arguments)
