import json,re
from .llm import llm

def extract_parameters(prompt,schema):
    # From the schema dict, extract the required and properties fields to form a contract for the parameter extraction.
    contract={'required':schema.get('required',[]),'properties':schema.get('properties',{})}
    # The system prompt instructs the LLM to extract only the parameters that are explicitly stated or can be directly inferred from the user's request. Follow the JSON Schema contract, and return JSON object only. Do not invent missing required values.
    sys=f'''Extract only parameters stated or directly inferable from the request. Follow this JSON Schema contract:\n{json.dumps(contract,indent=2)}\nReturn JSON object only. Do not invent missing required values.'''
    raw=llm.invoke([('system',sys),('human',prompt)]).content.strip()
    # Here the LLM wil return the parameters in JSON format from the human prompt
    try:
        return json.loads(raw)
    except Exception:
    # Else, if the LLM returns a non-JSON response, try to extract the JSON object from the response using regex. If still cannot parse, raise an error.
        m=re.search(r'\{.*\}',raw,re.S)
        if m:
            return json.loads(m.group())
    raise ValueError(f'Cannot parse parameter JSON: {raw}')
