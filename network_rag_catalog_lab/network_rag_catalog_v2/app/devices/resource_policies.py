"""Reviewed planned-resource checks. No topology discovery or implicit creation."""

import ipaddress


RESOURCE_FIELDS = {
    "default_route_v1": {"next_hop": "string", "preference": "integer"},
    "floating_route_v1": {"destination": "string", "next_hop": "string", "preference": "integer"},
    "ospf_enable_v1": {"process_id": "integer", "router_id": "string"},
    "ospf_router_id_v1": {"process_id": "integer", "router_id": "string"},
    "ospf_area_v1": {"process_id": "integer", "area": "string", "area_type": "string"},
    "ospf_interface_v1": {"process_id": "integer", "interface": "string", "area": "string"},
    "ospf_network_v1": {"process_id": "integer", "network_prefix": "string", "area": "string"},
    "ospf_passive_v1": {"process_id": "integer", "interface": "string", "passive": "boolean"},
    "ospf_redistribute_v1": {"process_id": "integer", "redistribution_source": "string", "route_policy": "string"},
    "acl_create_v1": {"acl_name": "string", "description": "string"},
    "acl_add_v1": {"acl_name": "string", "acl_rule_id": "integer"},
    "acl_modify_v1": {"acl_name": "string", "acl_rule_id": "integer"},
    "acl_delete_v1": {"acl_name": "string", "acl_rule_id": "integer"},
    "acl_attach_v1": {"acl_name": "string", "interface": "string", "direction": "string"},
    "qos_policy_v1": {"policy_name": "string", "policy_terms": "array"},
    "qos_classifier_v1": {"classifier_name": "string", "dscp_values": "array", "match_mode": "string"},
    "qos_dscp_v1": {"classifier_name": "string", "dscp_values": "array", "previous_dscp_values": "array"},
    "qos_scheduler_v1": {"policy_name": "string", "classifier_name": "string", "bandwidth_bps": "integer"},
    "qos_shaping_v1": {"policy_name": "string", "interface": "string", "rate_bps": "integer", "direction": "string"},
    "qos_policing_v1": {"policy_name": "string", "interface": "string", "rate_bps": "integer", "direction": "string", "burst_bytes": "integer", "exceed_action": "string"},
    "qos_attach_v1": {"policy_name": "string", "interface": "string", "direction": "string"},
}


def validate_resource_policy(policy, params, device):
    try:
        return _validate_resource_policy(policy, params, device)
    except (TypeError, ValueError, AttributeError, KeyError):
        return [{"type": "UNSUPPORTED_OPERATION", "field": "operation_id",
                 "message": f"{device.get('hostname', 'Device')}: malformed planned resource facts; review the source snapshot."}]


def _validate_resource_policy(policy, params, device):
    from .operation_policies import PROFILES
    issues = []

    def reject(field, message, kind="DEVICE_CONTEXT"):
        issues.append({"type": kind, "field": field, "message": f"{device['hostname']}: {message}", "device": device["hostname"]})

    caps = device.get("capabilities", {})
    vendor = device.get("vendor")
    profile = (device.get("platform"), str(device.get("version")), device.get("model_family"))
    if (profile != PROFILES.get(vendor) or policy not in caps.get("validated_policies", [])
            or not device.get("source_refs")):
        reject("operation_id", "Unsupported or unreviewed resource-policy profile.", "UNSUPPORTED_OPERATION")
        return issues
    # Schema errors remain answerable by the schema validator, not Python exceptions.
    types = {"string": str, "integer": int, "boolean": bool, "array": list}
    if any(field in params and type(params[field]) is not types[kind] for field, kind in RESOURCE_FIELDS[policy].items()):
        return issues
    facts = device.get("resources")
    if not isinstance(facts, dict) or facts.get("complete") is not True or not facts.get("source_ref"):
        reject("operation_id", "A complete, source-referenced planned resource snapshot is required.", "UNSUPPORTED_OPERATION")
        return issues
    if (policy.endswith("route_v1") or policy.startswith("ospf_")) and facts.get("routing_context") != "default":
        reject("operation_id", "These routing contracts require an explicitly recorded default routing context.", "UNSUPPORTED_OPERATION")
        return issues

    def records(key, identity="name"):
        rows = facts.get(key)
        identity_type = int if identity == "process_id" else str
        if (not isinstance(rows, list) or any(not isinstance(row, dict) or type(row.get(identity)) is not identity_type for row in rows)
                or len({row[identity] for row in rows}) != len(rows)):
            reject("operation_id", f"Missing, malformed or duplicate {key} facts.", "UNSUPPORTED_OPERATION")
            return {}
        return {row[identity]: row for row in rows}

    interfaces = {item["name"]: item for item in device.get("interfaces", [])}
    interface = interfaces.get(params.get("interface"))
    if vendor in {"huawei", "juniper"}:
        from .vendor_policies import validate_native_resource
        issues.extend(validate_native_resource(policy, params, device))
        if policy.startswith("qos_") or (vendor == "juniper" and policy.startswith("ospf_")):
            return issues

    def binding(kind, desired):
        if interface is None or desired is None:
            return
        existing = interface.get(kind)
        direction = params.get("direction")
        if direction is None:
            return
        if not isinstance(existing, dict) or direction not in existing:
            reject("interface", f"Current {kind} attachment facts must explicitly record this direction.")
        elif existing[direction] not in (None, desired):
            reject("interface", "Replacing a different existing attachment requires a separately reviewed change.")

    def routed_port():
        if interface and (interface.get("switchport_mode") != "routed" or interface.get("enabled") is not True
                          or not interface.get("ip_addresses") or interface.get("routing_context") != "default"):
            reject("interface", "An enabled, addressed interface in the recorded default routing context is required.")

    if policy in {"default_route_v1", "floating_route_v1"}:
        routes = records("routes", "id")
        destination = params.get("destination", "0.0.0.0/0")
        next_hop = params.get("next_hop")
        if next_hop:
            try:
                hop = ipaddress.IPv4Address(next_hop)
                local = [ipaddress.IPv4Interface(value) for item in interfaces.values()
                         if item.get("enabled") is True and item.get("switchport_mode") == "routed"
                         and item.get("routing_context") == "default"
                         for value in item.get("ip_addresses", [])]
                if not any(hop in item.network and hop != item.ip and (item.network.prefixlen >= 31 or hop not in (item.network.network_address, item.network.broadcast_address)) for item in local):
                    reject("next_hop", "No enabled planned directly connected subnet proves this next hop; recursive next hops are outside scope.")
                if any(hop == item.ip for item in local):
                    reject("next_hop", "The next hop is a local interface address.")
            except (ValueError, TypeError):
                reject("next_hop", "Invalid next-hop or planned interface addressing.")
        relevant = [row for row in routes.values() if row.get("destination") == destination]
        if policy == "floating_route_v1" and "destination" in params:
            primary = [row for row in relevant if row.get("primary") is True and type(row.get("preference")) is int]
            if not primary:
                reject("destination", "No confirmed primary route establishes the claimed backup relationship.")
            elif type(params.get("preference")) is int and params["preference"] <= max(row["preference"] for row in primary):
                reject("preference", "A floating route needs a strictly higher preference than the recorded primary route.")
            if next_hop and any(row.get("next_hop") == next_hop for row in primary):
                reject("next_hop", "A backup next hop must differ from the recorded primary.")
        return issues

    if policy.startswith("ospf_"):
        processes = records("ospf_processes", "process_id")
        process = processes.get(params.get("process_id"))
        if policy != "ospf_enable_v1" and "process_id" in params and not process:
            reject("process_id", "Select an existing planned OSPF process; same-request creation is not assumed.")
        if policy == "ospf_enable_v1" and process:
            reject("process_id", "This creation operation requires an unused process ID.")
        if params.get("router_id") and any(row.get("router_id") == params["router_id"] and identity != params.get("process_id") for identity, row in processes.items()):
            reject("router_id", "Router ID collides with another planned process.")
        if policy == "ospf_area_v1" and params.get("area") in ("0", "0.0.0.0"):
            reject("area", "The backbone cannot be a stub area.")
        if policy == "ospf_area_v1" and process and params.get("area") in process.get("areas", {}):
            reject("area", "Area creation cannot silently change an existing area's type.")
        if policy in {"ospf_interface_v1", "ospf_network_v1"} and process and "area" in params and params["area"] not in process.get("areas", {}):
            reject("area", "Select an area explicitly present in this process's planned context.")
        if policy in {"ospf_interface_v1", "ospf_passive_v1"}:
            routed_port()
            if interface and policy == "ospf_interface_v1" and "ospf" not in interface:
                reject("interface", "The current OSPF membership must be explicitly recorded.")
            if interface and policy == "ospf_interface_v1" and all(field in params for field in ("process_id", "area")) and interface.get("ospf") not in (None, {"process_id": params["process_id"], "area": params["area"]}):
                reject("interface", "The interface belongs to a different OSPF process or area.")
            if interface and policy == "ospf_passive_v1" and (not isinstance(interface.get("ospf"), dict) or interface["ospf"].get("process_id") != params.get("process_id")):
                reject("interface", "Passive state needs confirmed membership in the selected process.")
        if policy == "ospf_network_v1" and all(field in params for field in ("network_prefix", "process_id", "area")):
            try:
                prefix = ipaddress.IPv4Network(params["network_prefix"], strict=True)
                selected = [item for item in interfaces.values() if item.get("routing_context") == "default" and any(ipaddress.IPv4Interface(value).ip in prefix for value in item.get("ip_addresses", []))]
                if not selected or any(item.get("switchport_mode") != "routed" or item.get("enabled") is not True or "ospf" not in item or item["ospf"] not in (None, {"process_id": params.get("process_id"), "area": params.get("area")}) for item in selected):
                    reject("network_prefix", "The network selector must match known enabled routed interfaces without conflicting OSPF membership.")
            except (ValueError, TypeError):
                reject("network_prefix", "Invalid network selector or planned address facts.")
        if policy == "ospf_redistribute_v1":
            policies = records("route_policies")
            selected = policies.get(params.get("route_policy"))
            if "route_policy" in params and (not selected or selected.get("bounded") is not True
                    or selected.get("default_action") != "deny" or not selected.get("allowed_prefixes")
                    or params.get("redistribution_source") not in selected.get("sources", [])):
                reject("route_policy", "Redistribution requires a reviewed bounded, default-deny policy for this source.")
            if selected:
                try:
                    prefixes = selected.get("allowed_prefixes", [])
                    if not isinstance(prefixes, list) or not prefixes or any(ipaddress.IPv4Network(value, strict=True).prefixlen == 0 for value in prefixes):
                        raise ValueError
                except (ValueError, TypeError):
                    reject("route_policy", "The policy must contain canonical, limiting IPv4 prefixes, not a default/permit-all selector.")
        return issues

    if policy.startswith("acl_"):
        acls = records("acls")
        acl = acls.get(params.get("acl_name"))
        if policy == "acl_create_v1":
            if acl:
                reject("acl_name", "An ACL with this name already exists.")
            return issues
        if "acl_name" in params and (not acl or acl.get("family") != "ipv4_extended"):
            reject("acl_name", "Select a confirmed named extended IPv4 ACL.")
        if acl:
            rows = acl.get("rules")
            if not isinstance(rows, list) or any(not isinstance(row, dict) or type(row.get("acl_rule_id")) is not int for row in rows) or len({row["acl_rule_id"] for row in rows}) != len(rows):
                reject("acl_name", "ACL rule facts are incomplete or duplicated.")
            else:
                existing = next((row for row in rows if row["acl_rule_id"] == params.get("acl_rule_id")), None)
                if policy == "acl_add_v1" and existing:
                    reject("acl_rule_id", "The rule ID already exists; use explicit full replacement.")
                if policy in {"acl_modify_v1", "acl_delete_v1"} and "acl_rule_id" in params and (not existing or existing.get("kind") != "ace"):
                    reject("acl_rule_id", "Select an existing ACE, not an absent rule or remark.")
        if policy == "acl_attach_v1":
            if acl and not any(row.get("kind") == "ace" for row in acl.get("rules", []) if isinstance(row, dict)):
                reject("acl_name", "Do not attach an empty or remark-only ACL.")
            routed_port()
            binding("acl_bindings", params.get("acl_name"))
        return issues

    classifiers = records("classifiers")
    policies = records("qos_policies")
    classifier = classifiers.get(params.get("classifier_name"))
    qos_policy = policies.get(params.get("policy_name"))
    if policy == "qos_classifier_v1":
        if classifier:
            reject("classifier_name", "Classifier already exists; use the DSCP replacement operation.")
    elif policy == "qos_dscp_v1":
        if "classifier_name" in params and (not classifier or classifier.get("match_mode") != "any" or classifier.get("match_type") != "dscp"):
            reject("classifier_name", "Only an existing DSCP-only match-any classifier may be replaced.")
        if classifier and classifier.get("attachments") != []:
            reject("classifier_name", "Classifier must be confirmed detached from live attachments before replacement.")
        if classifier and "previous_dscp_values" in params and params["previous_dscp_values"] != classifier.get("dscp_values"):
            reject("previous_dscp_values", "Confirm the exact existing DSCP list from the planned classifier.")
    elif policy == "qos_policy_v1":
        if qos_policy:
            reject("policy_name", "Creating a policy cannot overwrite an existing policy.")
        terms = params.get("policy_terms", [])
        if isinstance(terms, list):
            for index, term in enumerate(terms):
                if isinstance(term, dict):
                    identity = term.get("classifier_name")
                    match = classifiers.get(identity) if isinstance(identity, str) else None
                    if not match or match.get("match_type") != "dscp" or match.get("match_mode") != "any":
                        reject(f"policy_terms[{index}].classifier_name", "Select a confirmed DSCP-only match-any classifier.")
            if len(terms) + 1 > caps.get("qos_queue_count", 0):
                reject("policy_terms", "Policy terms plus class-default exceed the recorded queue capacity.")
    elif policy == "qos_scheduler_v1":
        if "policy_name" in params and (not qos_policy or qos_policy.get("kind") != "bandwidth"):
            reject("policy_name", "Select an existing absolute-bandwidth policy.")
        if qos_policy and params.get("classifier_name") not in qos_policy.get("classes", {}):
            reject("classifier_name", "Select an existing class in this policy.")
        if classifier is None and "classifier_name" in params:
            reject("classifier_name", "The policy references an unknown classifier.")
        if qos_policy and qos_policy.get("attachments") != []:
            reject("policy_name", "Edit only detached policies; attached-policy impacts require separate review.")
    elif policy in {"qos_shaping_v1", "qos_policing_v1"}:
        if qos_policy:
            reject("policy_name", "Use an unused explicit policy name; this operation creates and attaches a dedicated treatment.")
        if interface:
            allowed = interface.get("qos_directions", [])
            if params.get("direction") not in allowed:
                reject("direction", "This interface does not support the requested QoS direction.")
            binding("qos_bindings", params.get("policy_name"))
            if type(params.get("rate_bps")) is int and params["rate_bps"] > interface.get("speed_mbps", 0) * 1000000:
                reject("rate_bps", "Rate exceeds recorded port capacity.")
    elif policy == "qos_attach_v1":
        if "policy_name" in params and (not qos_policy or qos_policy.get("kind") != "bandwidth"):
            reject("policy_name", "Select a confirmed complete absolute-bandwidth policy.")
        if interface:
            binding("qos_bindings", params.get("policy_name"))
            if params.get("direction") not in interface.get("qos_directions", []):
                reject("direction", "Unsupported QoS direction for this interface.")
            classes = qos_policy.get("classes", {}) if qos_policy else {}
            if not isinstance(classes, dict) or any(type(value) is not int for value in classes.values()):
                reject("policy_name", "Policy class bandwidth facts are incomplete.")
            elif sum(classes.values()) > interface.get("speed_mbps", 0) * 1000000:
                reject("policy_name", "Policy bandwidth exceeds recorded interface capacity.")
            if isinstance(classes, dict) and any(name not in classifiers or classifiers[name].get("match_type") != "dscp" for name in classes):
                reject("policy_name", "Policy classifier references are absent or incompatible.")
            if len(classes) + 1 > caps.get("qos_queue_count", 0):
                reject("policy_name", "Policy exceeds recorded queue capacity.")
    return issues
