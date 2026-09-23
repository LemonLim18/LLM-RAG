import json
import re
from difflib import SequenceMatcher
from ..config import INVENTORY_FILE


class TargetResolutionError(ValueError):
    def __init__(self, code: str, reference: str, message: str, suggestions: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.reference = reference
        self.suggestions = suggestions or []


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
    generic_tokens = {"device", "devices", "router", "routers", "switch", "switches", "firewall", "firewalls"}
    meaningful_tokens = query_tokens - generic_tokens
    if not meaningful_tokens:
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
        if (
            query in {_norm(plural_role), _norm(plural_vendor)}
            or meaningful_tokens <= device_tokens
        ):
            matches.append(device)
    return matches


def _suggest_devices(ref: str, inventory: list[dict], limit: int = 3) -> list[str]:
    query = _norm(ref)
    scored: dict[str, float] = {}
    for device in inventory:
        best = 0.0
        for candidate in _index_device(device):
            ratio = SequenceMatcher(None, query, candidate).ratio()
            query_tokens = set(query.split())
            candidate_tokens = set(candidate.split())
            overlap = len(query_tokens & candidate_tokens) / max(1, len(query_tokens | candidate_tokens))
            best = max(best, ratio, overlap)
        scored[device["hostname"]] = best
    return [hostname for hostname, _ in sorted(scored.items(), key=lambda item: item[1], reverse=True)[:limit]]


def find_explicit_target_references(text: str, inventory: list[dict] | None = None) -> list[str]:
    """Find only inventory aliases literally present in text; never fuzzy guess."""
    inventory = inventory or load_inventory()
    normalized = _norm(text)
    matches = []
    for device in inventory:
        for candidate in _index_device(device):
            if candidate and re.search(rf"(?<![a-z0-9]){re.escape(candidate)}(?![a-z0-9])", normalized):
                matches.append(device["hostname"])
                break
    return list(dict.fromkeys(matches))


def find_explicit_group_references(text: str, inventory: list[dict] | None = None) -> list[str]:
    """Find supported inventory group phrases literally present in user text."""
    inventory = inventory or load_inventory()
    normalized = _norm(text)
    groups = set()
    for device in inventory:
        role = _norm(str(device.get("role", "")))
        vendor = _norm(str(device.get("vendor", "")))
        site = _norm(str(device.get("site", "")))
        location = _norm(str(device.get("location", "")))
        if role:
            groups.add(f"{role} routers")
        if vendor:
            groups.add(f"{vendor} routers")
        if site and role:
            groups.add(f"{site} {role} routers")
        if location and role:
            groups.add(f"{location} {role} routers")
    return [
        group
        for group in sorted(groups)
        if re.search(rf"(?<![a-z0-9]){re.escape(group)}(?![a-z0-9])", normalized)
    ]


def find_user_target_candidates(text: str) -> list[str]:
    """Find explicit device-shaped references, including unknown inventory names.

    This is intentionally a narrow parser. It preserves ``Router 9`` or ``R9``
    long enough for the resolver to offer authoritative suggestions, but it does
    not treat arbitrary capitalized words as devices.
    """
    candidates = []
    patterns = (
        r"\b(?:core\s+|edge\s+)?(?:router|switch|firewall)\s+\d+\b",
        r"\b(?:r|sw|fw)\d+\b",
    )
    for pattern in patterns:
        candidates.extend(match.group(0) for match in re.finditer(pattern, text, re.I))
    return list(dict.fromkeys(candidates))


def resolve_targets(target_refs: list[str], inventory: list[dict] | None = None) -> list[dict]:
    # Preserve the public API while using the same authority as the pipeline.
    from .target_resolver import resolve_intent_targets
    return resolve_intent_targets(target_refs, inventory)
