from .inventory import resolve_targets, load_inventory


def resolve_intent_targets(target_refs: list[str]) -> list[dict]:
    return resolve_targets(target_refs, load_inventory())
