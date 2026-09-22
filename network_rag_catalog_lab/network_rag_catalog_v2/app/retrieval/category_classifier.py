import json
import re
from ..catalog import category_for_text, load_categories
from ..llm import llm


def classify_category(prompt: str) -> str:
    cats = load_categories()
    valid = {x["category_id"] for x in cats}
    deterministic = category_for_text(prompt)
    if deterministic:
        return deterministic
    listing = "\n".join(
        f"- {x['category_id']} ({x['display_name']}): {x['description']}" for x in cats
    )
    msg = f"""Classify this network operation into exactly one known category.
Known categories:
{listing}
Return JSON only: {{"category":"<category_id>"}}
Never invent a category."""
    raw = llm.invoke([("system", msg), ("human", prompt)]).content.strip()
    try:
        category = json.loads(raw)["category"].lower()
    except Exception:
        m = re.search(r'"category"\s*:\s*"([^"]+)"', raw, re.I)
        category = m.group(1).lower() if m else ""
    if category in valid:
        return category
    raise ValueError(f"Cannot classify category. LLM returned: {raw}")
