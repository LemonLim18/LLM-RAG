import json
import re
from ..llm import llm


def extract_parameters(prompt: str, schema: dict) -> dict:
    contract = {"required": schema.get("required", []), "properties": schema.get("properties", {})}
    system = f"""Extract only parameters stated or directly inferable from the request.
Follow this JSON Schema contract:
{json.dumps(contract, indent=2)}
Return one JSON object only.
Do not invent missing required values.
Do not add fields outside the contract."""
    raw = llm.invoke([("system", system), ("human", prompt)]).content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if match:
            return json.loads(match.group(0))
    raise ValueError(f"Cannot parse parameter JSON: {raw}")
