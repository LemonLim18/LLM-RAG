import json
import re
from difflib import SequenceMatcher
from ..config import INVENTORY_FILE


def load_inventory() -> list[dict]:
    return json.loads(INVENTORY_FILE.read_text())


def _norm(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _index_device(device: dict) -> list[str]:
    values = [device.get("hostname", ""), device.get("display_name", "")]
    values += device.get("aliases", [])
    return [_norm(str(v)) for v in values if v]


def _group_match(ref: str, inventory: list[dict]) -> list[dict]:
    query = _norm(ref)
    query_tokens = set(query.split())
    if not query_tokens:
        return []

    matches = []
    for device in inventory:
        group_values = [
            device.get("role", ""),
            device.get("site", ""),
            device.get("location", ""),
            device.get("vendor", ""),
            device.get("platform", ""),
        ]
        group_values += device.get("tags", [])
        device_tokens = set()
        for value in group_values:
            device_tokens.update(_norm(str(value)).split())

        plural_role = f"{device.get('role', '').lower()} routers"
        plural_vendor = f"{device.get('vendor', '').lower()} routers"
        if query in {_norm(plural_role), _norm(plural_vendor)} or query_tokens <= device_tokens:
            matches.append(device)
    return matches


def resolve_targets(target_refs: list[str], inventory: list[dict] | None = None) -> list[dict]:
    inventory = inventory or load_inventory()
    if not target_refs:
        raise ValueError("No target device was specified. Please name one or more target devices.")

    resolved = []
    for ref in target_refs:
        query = _norm(ref)
        if not query:
            continue
        exact = [d for d in inventory if query in _index_device(d)]
        if len(exact) == 1:
            resolved.append(exact[0])
            continue
        if len(exact) > 1:
            names = ", ".join(d["hostname"] for d in exact)
            raise ValueError(f"Ambiguous target '{ref}'. Matching devices: {names}")

        group = _group_match(ref, inventory)
        if group:
            resolved.extend(group)
            continue

        scored = []
        q_tokens = set(query.split())
        for d in inventory:
            for candidate in _index_device(d):
                ratio = SequenceMatcher(None, query, candidate).ratio()
                c_tokens = set(candidate.split())
                token_score = len(q_tokens & c_tokens) / max(1, len(q_tokens | c_tokens))
                score = max(ratio, token_score)
                scored.append((score, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored or scored[0][0] < 0.62:
            known = ", ".join(d["hostname"] for d in inventory)
            raise KeyError(f"Cannot resolve target '{ref}'. Known devices: {known}")
        best_score = scored[0][0]
        tied = [d for score, d in scored if score >= best_score - 0.03]
        unique = {d["hostname"]: d for d in tied}
        if len(unique) > 1:
            names = ", ".join(unique)
            raise ValueError(f"Ambiguous target '{ref}'. Possible devices: {names}")
        resolved.append(scored[0][1])

    # De-duplicate while preserving user order.
    result = []
    seen = set()
    for d in resolved:
        if d["hostname"] not in seen:
            result.append(d)
            seen.add(d["hostname"])
    return result
