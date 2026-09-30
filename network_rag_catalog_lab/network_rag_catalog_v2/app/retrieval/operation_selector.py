import json
import re

from ..catalog import get_operation
from ..llm import llm


def _explicit_operation(prompt: str, candidates: list[dict]) -> str | None:
    matches = {}
    for candidate in candidates:
        metadata = get_operation(candidate["operation_id"])
        for phrase in [metadata["display_name"], *metadata.get("aliases", [])]:
            if re.search(rf"(?<![\w]){re.escape(phrase)}(?![\w])", prompt, re.I):
                matches[metadata["operation_id"]] = max(matches.get(metadata["operation_id"], 0), len(phrase))
    ranked = sorted(((score, operation) for operation, score in matches.items()), reverse=True)
    if ranked and (len(ranked) == 1 or ranked[0][0] > ranked[1][0]):
        return ranked[0][1]
    return None


def select_operation(prompt: str, category: str, candidates: list[dict]) -> str:
    explicit = _explicit_operation(prompt, candidates)
    if explicit:
        return explicit
    allowed = {item["operation_id"] for item in candidates}
    descriptions = [{"operation_id": item["operation_id"], "description": item["description"],
                     "vendor_support": item.get("vendor_support", {})} for item in candidates]
    system = ('Identify the requested network action by meaning, including paraphrases. '
              'Select the most specific matching action from the list. Missing parameters and device '
              'compatibility are checked later; they are not reasons to reject a matching action. '
              'Return only JSON {"operation_id":"one listed ID"}, or {"operation_id":null} '
              'when no listed action matches. Category: ' + category + '. Actions: ' + json.dumps(descriptions))
    for attempt in range(2):
        try:
            data = json.loads(llm.invoke([("system", system), ("human", prompt)]).content)
            operation = data.get("operation_id") if isinstance(data, dict) else None
            if isinstance(operation, str) and operation in allowed:
                return operation
        except (ValueError, TypeError, AttributeError):
            pass
        system += "\nInvalid prior selection. Use exactly an allowed ID or null."
    raise ValueError("Operation could not be resolved to an active catalog entry.")
