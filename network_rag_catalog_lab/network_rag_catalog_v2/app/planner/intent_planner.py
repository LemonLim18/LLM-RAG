import json
import re
from ..catalog import load_operations
from ..llm import llm
from ..planner.models import OperationIntent


def _known_operation_words() -> str:
    return "\n".join(f"- {x['operation_id']}: {x['name']} — {x['description']}" for x in load_operations())


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise ValueError(f"Intent planner returned non-JSON output: {raw}")
        return json.loads(match.group(0))


def _fallback_plan(prompt: str) -> list[OperationIntent]:
    """Small deterministic fallback for common conjunctions in the learning lab.

    It is deliberately conservative: it only splits when an explicit operation
    keyword appears after a conjunction. Ambiguous text is kept as one intent so
    the normal pipeline can reject/clarify it rather than inventing work.
    """
    operation_terms = [
        "create vlan", "configure vlan", "configure ospf", "enable ospf",
        "configure bgp", "bgp neighbor", "configure isis", "enable is-is",
        "static route", "configure static route", "configure interface ip",
        "assign ip", "configure ip address", "set ip address",
    ]
    lower = prompt.lower()
    positions = []
    for term in operation_terms:
        start = 0
        while True:
            i = lower.find(term, start)
            if i < 0:
                break
            positions.append((i, term))
            start = i + len(term)
    positions.sort()
    if len(positions) <= 1:
        return [OperationIntent("intent-1", prompt.strip(), [])]

    # Use operation starts as conservative boundaries. The first intent begins
    # at the beginning of the request; later intents begin at their operation
    # keyword. This works well for "... and configure OSPF ..." style requests.
    intents = []
    for idx, (start, _) in enumerate(positions):
        if idx == 0:
            text = prompt[:positions[1][0]] if len(positions) > 1 else prompt
        else:
            end = positions[idx + 1][0] if idx + 1 < len(positions) else len(prompt)
            text = prompt[start:end].strip(" ,; and")
        if text:
            intents.append(OperationIntent(f"intent-{idx + 1}", text, []))
    return intents or [OperationIntent("intent-1", prompt.strip(), [])]


# list[OperationIntent] should return a list of OperationIntent objects
def plan_intents(prompt: str) -> list[OperationIntent]:
    # List of known operations from the catalog
    operations = _known_operation_words()
    system = f"""You are the planning layer of a network automation system.
Split the user's request into independent network operation intents.
Do not execute anything. Do not invent operations, devices, or parameter values.
One intent should represent one logical operation, even if it targets multiple devices.
Preserve the exact natural-language operation text because a downstream system will
perform operation retrieval and schema-based parameter extraction.

Known operation catalog:
{operations}

Return JSON only in this exact shape:
{{
  "intents": [
    {{
      "intent_id": "intent-1",
      "request_text": "...",
      "target_refs": ["R1", "core router 1"]
    }}
  ]
}}

Rules:
- Split requests containing multiple independent operations.
- target_refs contains only device references explicitly associated with that intent.
- If no target is stated, return an empty target_refs list; do not guess.
- Do not choose a final operation_id unless it is obvious; request_text remains authoritative.
- Do not merge two different operations merely because they target the same device.
"""
    try:
        raw = llm.invoke([("system", system), ("human", prompt)]).content.strip()
        # Parse the json into a dictionary
        data = _parse_json(raw)
        # Extract the intents from the dictionary and create raw intent objects, each containing an intent_id, request_text, and target_refs.
        raw_intents = data.get("intents", [])
        intents = []
        for i, item in enumerate(raw_intents, 1):
            text = str(item.get("request_text", "")).strip()
            if not text:
                continue
            refs = item.get("target_refs", [])
            if isinstance(refs, str):
                refs = re.split(r"\s*(?:,|\band\b|&)\s*", refs, flags=re.I)
            refs = [str(x).strip() for x in refs if str(x).strip()]
            # Create a clean OperationIntent object from the raw_intents and append it into the clean intent list
            intents.append(OperationIntent(str(item.get("intent_id") or f"intent-{i}"), text, refs))

        # If the small local LLM collapsed an obviously multi-operation request
        # into one intent, prefer the conservative deterministic splitter.
        if intents and len(intents) == 1 and len(_fallback_plan(prompt)) > 1:
            return _fallback_plan(prompt)
        if intents:
            return intents
    except Exception as exc:
        print(f"[planner] LLM planning failed, using conservative fallback: {exc}")
    return _fallback_plan(prompt)
