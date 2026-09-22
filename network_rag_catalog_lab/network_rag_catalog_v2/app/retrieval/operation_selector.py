import json
import re
from ..llm import llm


def select_operation(prompt: str, category: str, candidates: list[dict]) -> str:
    listing = "\n".join(f"- {x['operation_id']}: {x['description']}" for x in candidates)
    system = f"""The category is {category}. Choose exactly one operation from these retrieved candidates:
{listing}
Return JSON only: {{"operation_id":"..."}}.
Never invent an operation."""
    raw = llm.invoke([("system", system), ("human", prompt)]).content.strip()
    try:
        operation = json.loads(raw)["operation_id"]
    except Exception:
        m = re.search(r'"operation_id"\s*:\s*"([^"]+)"', raw, re.I)
        operation = m.group(1) if m else ""
    allowed = {x["operation_id"] for x in candidates}
    if operation not in allowed:
        raise ValueError(f"Invalid operation selection: {raw}")
    return operation
