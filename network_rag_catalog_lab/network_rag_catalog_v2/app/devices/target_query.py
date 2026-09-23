"""Extract evidence-backed device descriptions, independently of operation parameters."""

import json
import re

from ..config import DATA_DIR


def load_attributes() -> dict:
    return json.loads((DATA_DIR / "inventory" / "attributes.json").read_text(encoding="utf-8"))["attributes"]


def values_at(device: dict, path: str) -> list[str]:
    values = [device]
    for part in path.split("."):
        next_values = []
        for value in values:
            if isinstance(value, dict):
                item = value.get(part, [])
                next_values.extend(item if isinstance(item, list) else [item])
        values = next_values
    return [str(value) for value in values if isinstance(value, (str, int, float))]


def vocabulary(inventory: list[dict], attributes: dict) -> dict[str, dict[str, str]]:
    result = {}
    for field, spec in attributes.items():
        terms = {}
        for device in inventory:
            for path in spec["paths"]:
                for value in values_at(device, path):
                    terms[value.casefold()] = value
        for canonical, aliases in spec.get("aliases", {}).items():
            for alias in [canonical, *aliases]:
                terms[alias.casefold()] = canonical
        result[field] = terms
    return result


def _pattern(phrase: str) -> str:
    return rf"(?<![\w/-]){re.escape(phrase)}(?![\w/-])"


def _mask(text: str, start: int, end: int) -> str:
    return text[:start] + " " * (end - start) + text[end:]


def _unknown(text: str) -> list[str]:
    # Grammar only. Device characteristics belong in the inventory vocabulary.
    grammar = set("the a an in at on from with that is are has have of device devices one ones all both "
                  "running using located supporting supports capable enabled please use select choose "
                  "site role vendor platform location status tag tags feature features capability capabilities "
                  "version management ip address network subnet interface interfaces type named called".split())
    return [word for word in re.findall(r"[\w./-]+", text) if word.casefold() not in grammar]


def _llm_constraints(text: str, vocab: dict, allowed_fields: set[str]) -> list[dict]:
    """The model may label literal evidence, but cannot choose devices or invent aliases."""
    from ..llm import llm

    contract = {field: sorted(set(terms.values())) for field, terms in vocab.items() if field in allowed_fields}
    system = (
        "Extract explicit device attributes only. Do not select devices or infer unstated values. "
        "Return JSON {\"constraints\": [{\"field\": \"site\", \"value\": \"...\", \"evidence\": \"exact quote\"}]}. "
        "Evidence must quote the current message; value must be that literal or a listed inventory value. "
        "Unknown information stays absent. Inventory vocabulary: " + json.dumps(contract)
    )
    try:
        data = json.loads(llm.invoke([("system", system), ("human", text)]).content)
    except (ValueError, TypeError, AttributeError, OSError):
        return []
    except Exception:
        # Model connectivity failures must not remove deterministic constraints.
        return []
    if not isinstance(data, dict) or not isinstance(data.get("constraints"), list):
        return []
    return data["constraints"]


def parse_description(text: str, inventory: list[dict], *, allow_llm: bool = False) -> dict:
    attributes = load_attributes()
    vocab = vocabulary(inventory, attributes)
    remaining = text
    constraints = []

    def add(field: str, value: str, match, source: str = "user_literal") -> None:
        nonlocal remaining
        constraints.append({"field": field, "value": value, "evidence": text[match.start():match.end()],
                            "start": match.start(), "end": match.end(), "source_text": text, "source": source})
        remaining = _mask(remaining, match.start(), match.end())

    # Consume complete identities first: "edge router 1" must not also match
    # "router 1" and accidentally select R1 alongside R3.
    for term in sorted(vocab["name"], key=len, reverse=True):
        for match in list(re.finditer(_pattern(term), remaining, re.I)):
            add("name", vocab["name"][term], match)
    for match in list(re.finditer(r"\b(?:(?:router|switch|firewall)\s+\d+|(?:r|sw|fw)\d+)\b", remaining, re.I)):
        add("name", match.group(), match)

    explicit_patterns = {
        "version": r"\bversion\s*[:=]?\s*([\w.-]+)",
        "management_ip": r"\bmanagement\s+(?:(?:ip|address|network|subnet)\s+)*(\d+(?:\.\d+){3}(?:/\d+)?)",
    }
    for field, pattern in explicit_patterns.items():
        for match in list(re.finditer(pattern, remaining, re.I)):
            add(field, match.group(1), match)

    # Attribute labels bind their value to that field, even if the value is
    # unknown or happens to name another attribute ("site Cisco").
    for field in ("site", "role", "vendor", "platform", "location", "status", "tags", "features"):
        label = field.rstrip("s") if field in {"tags", "features"} else field
        terms = "|".join(re.escape(term) for term in sorted(vocab[field], key=len, reverse=True))
        value_pattern = rf"(?:{terms})(?![\w/-])|[\w./-]+" if terms else r"[\w./-]+"
        pattern = rf"\b{label}(?:\s+(?:is\s+)?|\s*[:=]\s*)({value_pattern})"
        for match in list(re.finditer(pattern, remaining, re.I)):
            value = match.group(1)
            add(field, vocab[field].get(value.casefold(), value), match)

    hits = []
    for field, terms in vocab.items():
        if field == "name" or attributes[field].get("explicit_only"):
            continue
        for term, canonical in terms.items():
            for match in re.finditer(_pattern(term), remaining, re.I):
                hits.append((field, canonical, match))
    # Prefer complete attribute phrases; registry order breaks duplicate tag/role ties.
    for field, canonical, match in sorted(hits, key=lambda hit: -(hit[2].end() - hit[2].start())):
        if remaining[match.start():match.end()].strip():
            if remaining[match.start():match.end()] == text[match.start():match.end()]:
                add(field, canonical, match)

    if allow_llm and _unknown(remaining):
        proposals = _llm_constraints(text, vocab, set(attributes))
        for proposal in proposals:
            if not isinstance(proposal, dict):
                continue
            field, value, evidence = (proposal.get(key) for key in ("field", "value", "evidence"))
            if not isinstance(field, str) or field not in attributes or not isinstance(value, str) or not isinstance(evidence, str) or not evidence.strip():
                continue
            match = re.search(_pattern(evidence), remaining, re.I)
            canonical = vocab[field].get(evidence.casefold(), evidence)
            if match and value.casefold() == canonical.casefold():
                add(field, canonical, match, "llm_grounded_literal")

    plural = bool(re.search(r"\b(all|both|routers|switches|firewalls|devices)\b", text, re.I))
    if re.search(r"\b(one|a|an)\b", text, re.I):
        plural = False
    return {
        "text": text, "constraints": constraints, "cardinality": "many" if plural else "one",
        "unresolved": _unknown(remaining),
    }


def extract_target_queries(text: str, inventory: list[dict], *, reply: bool = False, allow_llm: bool = False) -> list[dict]:
    """Keep selectors within an operation's original user-text clause."""
    if reply:
        scope = text.strip()
    else:
        vocab = vocabulary(inventory, load_attributes())
        names = list(vocab["name"])

        def device_hint(value: str) -> bool:
            return bool(re.search(r"\b(router|routers|switch|switches|firewall|firewalls|device|devices|r\d+|sw\d+|fw\d+)\b", value, re.I)) or any(
                re.search(_pattern(term), value, re.I)
                for field in ("name", "site", "role", "vendor", "platform", "location", "tags") for term in vocab[field]
            )

        # Use the earliest target-bearing segment, but skip "on Ethernet1/1"
        # before a later "on R1". Keep trailing site/vendor qualifiers together.
        starts = list(re.finditer(r"\b(?:on|at|against|for)\s+", text, re.I))
        scope = ""
        for index, match in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
            if device_hint(text[match.end():end]):
                scope = text[match.end():]
                break
        if not scope:
            # A trailing inventory identity also covers "configure R1".
            hits = [match for name in names for match in re.finditer(_pattern(name), text, re.I)]
            if hits:
                # Without a clear clause boundary, preserve qualifiers instead
                # of reducing "Cisco R2" to R2 and losing the contradiction.
                scope = text
            else:
                return []
        # Parameter clauses are not device descriptors. A router's interface
        # is a selector only when explicitly introduced with "with/has".
        scope = re.split(r"\b(?:using|via|through)\b|\bon\s+(?=(?:Ethernet|Eth|GigabitEthernet|GE|ge-|Loopback|Lo)\d)", scope, maxsplit=1, flags=re.I)[0]
    scope = scope.strip(" .;")
    # Explicit alternatives are ambiguous, never an implicit union.
    parts = re.split(r"\s+and\s+|\s*&\s*|,\s*(?!\d)", scope, flags=re.I)
    if len(parts) > 1 and not all(re.search(r"\b(?:router|routers|device|devices|r\d+|sw\d+|fw\d+)\b", part, re.I) for part in parts):
        parts = [scope]
    return [parse_description(part, inventory, allow_llm=allow_llm) for part in parts if part.strip()]


def parameter_request(text: str, queries: list[dict]) -> str:
    """Device identity facts must not masquerade as operation parameter values."""
    result = text
    for query in queries:
        offset = text.find(query["text"])
        if offset < 0:
            continue
        for constraint in query["constraints"]:
            # An explicitly named interface may legitimately serve both roles.
            if constraint["field"] != "interface":
                result = _mask(result, offset + constraint["start"], offset + constraint["end"])
    return result
