"""Read-only local runtime diagnostics. Does not import/start the app lifespan."""
import asyncio
import json
from llm.gateway_diagnostics import diagnose

if __name__=='__main__':
    print(json.dumps(asyncio.run(diagnose()),indent=2))
