"""Deterministic normalization for values explicitly present in user text."""

import ipaddress
import re
from typing import Any

from ..catalog import get_parameter


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def canonicalize_parameter_keys(raw_params: dict, schema: dict) -> dict:
    """Map catalog aliases such as ``netmask`` to the schema's stable ID."""
    properties = schema.get("properties", {})
    aliases: dict[str, str] = {}
    for field in properties:
        aliases[normalize_key(field)] = field
        try:
            for alias in get_parameter(field).get("aliases", []):
                aliases[normalize_key(alias)] = field
        except KeyError:
            pass

    canonical: dict = {}
    for key, value in raw_params.items():
        field = aliases.get(normalize_key(str(key)))
        if field and field not in canonical:
            canonical[field] = value
    return canonical


def prefix_length_from_text(text: str, *, allow_bare_netmask: bool = False) -> int | None:
    """Return a prefix only when CIDR, prefix, or netmask is explicit in text."""
    # A slash in an interface name (for example Ethernet1/1) is not CIDR.
    # Accept a bare /24 only when it is the complete clarification response.
    cidr_match = re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}/(\d{1,2})(?!\d)", text)
    bare_match = re.fullmatch(r"\s*/(\d{1,2})\s*", text)
    for match in (cidr_match, bare_match):
        if not match:
            continue
        value = int(match.group(1))
        if 0 <= value <= 32:
            return value

    match = re.search(r"\b(?:prefix(?:\s+length)?|cidr)\s*(?:of|is|=|:)?\s*(\d{1,2})\b", text, re.I)
    if match:
        value = int(match.group(1))
        if 0 <= value <= 32:
            return value

    match = re.search(r"\b(?:netmask|subnet mask)\s*(?:is|=|:)?\s*(\d{1,3}(?:\.\d{1,3}){3})\b", text, re.I)
    if not match and allow_bare_netmask:
        match = re.fullmatch(r"\s*(\d{1,3}(?:\.\d{1,3}){3})\s*", text)
    if not match:
        return None
    try:
        return ipaddress.IPv4Network(f"0.0.0.0/{match.group(1)}").prefixlen
    except ValueError:
        return None


def normalize_value(field: str, value: Any, schema: dict, prompt: str) -> tuple[Any, str | None]:
    """Normalize only a value whose source is the current user text."""
    if value is None:
        return None, None

    if field == "prefix_length":
        explicit_prefix = prefix_length_from_text(prompt)
        if explicit_prefix is None:
            return None, None
        try:
            candidate = int(value)
        except (TypeError, ValueError):
            candidate = explicit_prefix
        if candidate != explicit_prefix:
            return None, None
        source = "derived_from_user_netmask" if "mask" in prompt.lower() else "user"
        return explicit_prefix, source

    if field in {"address", "neighbor_ip", "next_hop", "router_id"}:
        try:
            # A model often places ``192.0.2.1/24`` in ``address``. The prefix
            # is handled independently, so canonicalize the host address here.
            normalized = str(ipaddress.ip_interface(str(value).strip()).ip)
        except ValueError:
            return value, "user"
        return normalized, "user"

    if schema.get("type") == "integer" and isinstance(value, str) and value.strip().isdigit():
        return int(value.strip()), "user"
    return value, "user"


def deterministic_values(prompt: str, schema: dict) -> dict[str, tuple[Any, str]]:
    """Small, explicit-value fallback for common network expressions.

    It is intentionally narrow: every value comes from a matched text span.
    This lets the pipeline stay useful when a lightweight local LLM returns
    malformed JSON or misses an obvious literal.
    """
    fields = schema.get("properties", {})
    values: dict[str, tuple[Any, str]] = {}

    def match(pattern: str, field: str, cast=lambda value: value) -> None:
        if field not in fields:
            return
        found = re.search(pattern, prompt, re.I)
        if found:
            values[field] = (cast(found.group(1)), "deterministic_user")

    match(r"\bvlan(?:\s+id)?\s+(\d+)\b", "vlan_id", int)
    match(r"\b(?:named|name)\s+[\"']?([A-Za-z0-9_.-]+)", "name")
    match(r"\b(?:ospf\s+)?process(?:\s+id)?\s+(\d+)\b", "process_id", int)
    match(r"\brouter[-\s]+id\s+(\d{1,3}(?:\.\d{1,3}){3})\b", "router_id")
    match(r"\blocal\s+(?:as|autonomous\s+system)\s+(\d+)\b", "local_as", int)
    match(r"\bremote\s+(?:as|autonomous\s+system)\s+(\d+)\b", "remote_as", int)
    match(r"\b(?:neighbor|peer)(?:\s+ip)?\s+(\d{1,3}(?:\.\d{1,3}){3})\b", "neighbor_ip")
    match(r"\b(?:peer|bgp)\s+group\s+([A-Za-z0-9_.-]+)", "peer_group")
    match(r"\b(?:isis|is-is)\s+process\s+([A-Za-z0-9_.-]+)", "process_name")
    if "level" in fields:
        level = re.search(r"\blevel[-\s]?(1-2|1|2)\b", prompt, re.I)
        if level:
            values["level"] = (f"level-{level.group(1)}", "deterministic_user")
    match(r"\barea\s+([0-9.]+)\b", "area")
    match(r"\b(?:destination(?:\s+prefix)?|route\s+to)\s+(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})\b", "destination")
    match(r"\b(?:via|through|next[-\s]?hop)\s+(\d{1,3}(?:\.\d{1,3}){3})\b", "next_hop")
    match(r"\b(?:preference|administrative\s+distance|metric)\s+(\d+)\b", "preference", int)
    match(r"\b(?:interface|on|from|using|to)\s+((?:GigabitEthernet|Gig|Ethernet|Eth|E|GE|ge-|Loopback|Lo|lo)\d[\w/.-]*)", "interface")

    if "address" in fields:
        found = list(re.finditer(r"\b(\d{1,3}(?:\.\d{1,3}){3})(?:/\d{1,2})?\b", prompt))
        addresses = [hit.group(1) for hit in found if not re.search(r"(?:netmask|subnet mask|management IP|router id)\s*$", prompt[:hit.start()], re.I)]
        if len(set(addresses)) == 1:
            values["address"] = (addresses[0], "deterministic_user")

    if "prefix_length" in fields:
        prefix = prefix_length_from_text(prompt)
        if prefix is not None:
            source = "derived_from_user_netmask" if "mask" in prompt.lower() else "deterministic_user"
            values["prefix_length"] = (prefix, source)

    if "admin_up" in fields:
        lower = prompt.lower()
        if any(term in lower for term in ("no shutdown", "enable", "enabled", "admin up")):
            values["admin_up"] = (True, "deterministic_user")
        elif any(term in lower for term in ("shutdown", "disable", "disabled", "admin down")):
            values["admin_up"] = (False, "deterministic_user")

    if "interfaces" in fields:
        hits = list(re.finditer(r"\b(?:GigabitEthernet|Gig|Ethernet|Eth|E|GE|ge-|Loopback|Lo)\d[\w/.-]*", prompt, re.I))
        areas = list(re.finditer(r"\barea\s+([0-9.]+)\b", prompt, re.I))
        items = []
        for index, hit in enumerate(hits):
            item = {"name": hit.group().rstrip(".")}
            end = hits[index + 1].start() if index + 1 < len(hits) else len(prompt)
            local = [area.group(1).rstrip(".") for area in areas if hit.end() <= area.start() < end]
            if len(local) == 1:
                item["area"] = local[0]
            elif len(areas) == 1 and len(hits) == 1:
                item["area"] = areas[0].group(1).rstrip(".")
            elif len(areas) == 1 and re.search(r"\b(?:both|all)\s+(?:in\s+)?area\b", prompt, re.I):
                item["area"] = areas[0].group(1).rstrip(".")
            if item not in items:
                items.append(item)
        if items:
            values["interfaces"] = (items, "deterministic_user")
    return values


def explicit_alternatives(prompt: str, schema: dict) -> dict:
    """Conflicting scalar alternatives stay candidates, never first-match values."""
    alternatives = {}
    for clause in re.split(r"\bor\b", prompt, flags=re.I):
        for field, (value, _) in deterministic_values(clause, schema).items():
            if not isinstance(value, (list, dict)):
                alternatives.setdefault(field, [])
                if value not in alternatives[field]:
                    alternatives[field].append(value)
    if "address" in schema.get("properties", {}):
        hits = list(re.finditer(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", prompt))
        addresses = [hit.group() for hit in hits if not re.search(r"(?:netmask|subnet mask|management IP|router id)\s*$", prompt[:hit.start()], re.I)]
        alternatives["address"] = list(dict.fromkeys(addresses))
    if "interface" in schema.get("properties", {}):
        names = re.findall(r"\b(?:GigabitEthernet|Gig|Ethernet|Eth|E|GE|ge-|Loopback|Lo)\d[\w/.-]*", prompt, re.I)
        alternatives["interface"] = list(dict.fromkeys(names))
    # Repeated labelled literals also conflict, even without an 'or'.
    for field in schema.get("properties", {}):
        try:
            aliases = get_parameter(field).get("aliases", [])
        except KeyError:
            continue
        kind = schema["properties"][field].get("type")
        pattern = "|".join(re.escape(alias) for alias in sorted(aliases, key=len, reverse=True))
        if pattern:
            value_pattern = r"-?\d+" if kind == "integer" else r"[A-Za-z0-9_./-]+"
            if kind not in {"integer", "string"} or field in {"address", "interface"}:
                continue
            hits = re.findall(rf"\b(?:{pattern})\s+({value_pattern})(?![\w./-])", prompt, re.I)
            short_or = re.search(rf"\b(?:{pattern})\s+({value_pattern})\s+or\s+({value_pattern})(?![\w./-])", prompt, re.I)
            if short_or:
                hits.extend(short_or.groups())
            for hit in hits:
                alternatives.setdefault(field, [])
                value = int(hit) if kind == "integer" else hit
                if value not in alternatives[field]:
                    alternatives[field].append(value)
    return {field: values for field, values in alternatives.items() if len(values) > 1}
