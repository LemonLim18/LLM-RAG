import json,re
from .llm import llm

def extract_parameters(prompt,schema):
    contract={'required':schema.get('required',[]),'properties':schema.get('properties',{})}
    sys=f'''Extract only parameters stated or directly inferable from the request. Follow this JSON Schema contract:\n{json.dumps(contract,indent=2)}\nReturn JSON object only. Do not invent missing required values.'''
    raw=llm.invoke([('system',sys),('human',prompt)]).content.strip()
    try:return json.loads(raw)
    except Exception:
        m=re.search(r'\{.*\}',raw,re.S)
        if m:return json.loads(m.group())
    raise ValueError(f'Cannot parse parameter JSON: {raw}')
