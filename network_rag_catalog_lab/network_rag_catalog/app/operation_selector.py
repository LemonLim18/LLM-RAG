import json
import re

from .llm import llm


def select_operation(prompt, category, candidates):
    if not candidates:
        raise ValueError("No operation candidates were retrieved.")

    allowed = [x["operation_id"] for x in candidates]

    listing = "\n".join(
        f"{i + 1}. {x['operation_id']} — {x['description']}"
        for i, x in enumerate(candidates)
    )

    system_prompt = f"""
You are a network operation selector.

Your ONLY job is to select one operation from the candidate list.

Category:
{category}

Candidate operations:
{listing}

IMPORTANT RULES:

1. You MUST choose an operation_id EXACTLY as written in the candidate list.
2. NEVER create a new operation_id.
3. NEVER modify an operation_id.
4. NEVER include the user's parameters in the operation_id.
5. NEVER include device names, interface names, IP addresses, VLAN IDs,
   process IDs, AS numbers, or areas in the operation_id.
6. Return JSON only.
7. The operation_id must be one of these exact values:

{json.dumps(allowed)}

Example:

If the candidate is:
configure_ospf

Then the answer must be exactly:

{{"operation_id":"configure_ospf"}}
"""

    raw = llm.invoke([
        ("system", system_prompt),
        ("human", prompt)
    ]).content.strip()

    # Try normal JSON first
    try:
        result = json.loads(raw)
        operation_id = result["operation_id"].strip()
    except Exception:
        # Fallback: find a valid operation ID directly in the response
        operation_id = None

        for candidate in allowed:
            if candidate in raw:
                operation_id = candidate
                break

        if operation_id is None:
            raise ValueError(
                f"Invalid operation selection: {raw}"
            )

    if operation_id not in allowed:
        raise ValueError(
            f"Invalid operation selection: {raw}"
        )

    return operation_id