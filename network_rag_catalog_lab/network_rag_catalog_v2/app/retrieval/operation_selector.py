import json
import re
from ..catalog import get_operation
from ..llm import llm


def _explicit_operation(prompt: str, candidates: list[dict]) -> str | None:
    """Prefer one unambiguous catalog phrase before asking a weak LLM."""
    matches: dict[str, int] = {}
    normalized_prompt = prompt.lower()
    for candidate in candidates:
        metadata = get_operation(candidate["operation_id"])
        phrases = [metadata["display_name"], *metadata.get("aliases", [])]
        for phrase in phrases:
            if re.search(rf"(?<![a-z0-9]){re.escape(phrase.lower())}(?![a-z0-9])", normalized_prompt):
                operation_id = candidate["operation_id"]
                matches[operation_id] = max(matches.get(operation_id, 0), len(phrase))
    if not matches:
        return None
    ranked = sorted(((score, operation_id) for operation_id, score in matches.items()), reverse=True)
    if len(ranked) == 1 or ranked[0][0] > ranked[1][0]:
        return ranked[0][1]
    return None


def select_operation(prompt: str, category: str, candidates: list[dict]) -> str:
    explicit = _explicit_operation(prompt, candidates)
    if explicit:
        return explicit
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
        if len(candidates) == 1:
            return candidates[0]["operation_id"]
        matches: dict[str, int] = {}
        for candidate in candidates:
            metadata = get_operation(candidate["operation_id"])
            phrases = [metadata["operation_id"], metadata["display_name"], *metadata.get("aliases", [])]
            phrase_lengths = [len(phrase) for phrase in phrases if phrase.lower() in prompt.lower()]
            if phrase_lengths:
                candidate_id = candidate["operation_id"]
                matches[candidate_id] = max(matches.get(candidate_id, 0), max(phrase_lengths))
            candidate_id = candidate["operation_id"]
            if operation.startswith(candidate_id) or candidate_id.startswith(operation):
                matches[candidate_id] = max(matches.get(candidate_id, 0), len(candidate_id))
        if matches:
            ranked = sorted(((score, candidate_id) for candidate_id, score in matches.items()), reverse=True)
            if len(ranked) == 1 or ranked[0][0] > ranked[1][0]:
                return ranked[0][1]
        raise ValueError(f"Invalid operation selection: {raw}")
    return operation
