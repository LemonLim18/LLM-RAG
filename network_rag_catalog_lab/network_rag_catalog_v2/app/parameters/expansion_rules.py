"""Bounded IPv4, ACL and QoS checks for explicitly opted-in expansion schemas."""

import ipaddress


def network_rules(params, schema):
    from .validator import ValidationIssue
    issues = []
    if params.get("classifier_name") == "class-default":
        issues.append(ValidationIssue("CONFLICT", "classifier_name", "The built-in class-default identity is not a user classifier."))
    for field in ("destination", "network_prefix", "source_prefix", "destination_prefix"):
        value = params.get(field)
        if value is None:
            continue
        try:
            network = ipaddress.IPv4Network(value, strict=True)
            if str(network) != value:
                raise ValueError("Use canonical IPv4 CIDR notation.")
        except (ValueError, TypeError):
            issues.append(ValidationIssue("NETWORK", field, "Use a canonical IPv4 network/prefix with no host bits."))
    for field in ("source_port", "destination_port"):
        if field in params and params.get("ip_protocol") not in {"tcp", "udp"}:
            issues.append(ValidationIssue("CONFLICT", field, "Ports require explicit TCP or UDP."))
    terms = params.get("policy_terms")
    if isinstance(terms, list):
        names = set()
        for index, term in enumerate(terms):
            if not isinstance(term, dict):
                continue
            name = term.get("classifier_name")
            if name == "class-default":
                issues.append(ValidationIssue("CONFLICT", f"policy_terms[{index}].classifier_name", "Use a named DSCP classifier, not class-default."))
            if isinstance(name, str):
                if name in names:
                    issues.append(ValidationIssue("CONFLICT", f"policy_terms[{index}].classifier_name", "Each classifier may occur once."))
                names.add(name)
    return issues
