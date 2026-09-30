"""Native VRP/Junos context checks; absence of planned facts never grants permission."""

import ipaddress


def validate_native_resource(policy, params, device):
    issues = []
    vendor, facts = device["vendor"], device["resources"]
    interfaces = {row["name"]: row for row in device["interfaces"]}
    port = interfaces.get(params.get("interface"))

    def reject(field, message):
        issues.append({"type": "DEVICE_CONTEXT", "field": field,
                       "message": f"{device['hostname']}: {message}", "device": device["hostname"]})

    def records(key):
        rows = facts.get(key)
        if (not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get("name"), str) for row in rows)
                or len({row["name"] for row in rows}) != len(rows)):
            reject("operation_id", f"Complete, unique {key} inventory facts are required.")
            return {}
        return {row["name"]: row for row in rows}

    def routed(item, field="interface"):
        if item is not None and (item.get("enabled") is not True or item.get("switchport_mode") != "routed"
                or not item.get("ip_addresses") or item.get("routing_context") != "default"):
            reject(field, "Select an enabled, addressed interface in the default routing instance.")

    def logical_unit():
        if port and "logical_unit" in params and (params["logical_unit"] not in port.get("logical_units", [])
                or port.get("encapsulation") != "inet"):
            reject("logical_unit", "Select a recorded inet logical unit on this interface.")

    def attachment(key, desired, direction=None):
        if port is None:
            return
        direction = direction or params.get("direction")
        current = port.get(key)
        if not isinstance(current, dict) or direction not in current:
            reject("interface", f"Explicit {key} facts are required for {direction}.")
        elif current[direction] not in (None, desired):
            reject("interface", "This would overwrite another planned attachment; review that change separately.")

    if vendor == "juniper" and policy.startswith("ospf_"):
        ospf = facts.get("ospf_default")
        if not isinstance(ospf, dict) or not isinstance(ospf.get("areas"), dict):
            reject("operation_id", "Record the default-instance OSPF areas, router ID and export policies.")
            return issues
        area = params.get("area")
        if policy == "ospf_area_v1" and area is not None:
            if area in ("0", "0.0.0.0") or area in ospf["areas"]:
                reject("area", "Use a new non-backbone stub area; changing an existing area's type is not implicit.")
        if policy in {"ospf_interface_v1", "ospf_network_v1", "ospf_passive_v1"} and area is not None and area not in ospf["areas"]:
            reject("area", "Select a recorded area in the default OSPF instance.")
        if policy in {"ospf_enable_v1", "ospf_interface_v1", "ospf_passive_v1"}:
            routed(port)
            if port and (port.get("logical_units") != [0] or port.get("encapsulation") != "inet"):
                reject("interface", "This OSPF contract selects the recorded inet unit 0.")
            if port and "area" in params:
                membership = port.get("ospf")
                if "ospf" not in port or (membership is not None and membership != {"area": area}):
                    reject("interface", "OSPF membership is unknown or belongs to another area.")
                if policy == "ospf_passive_v1" and membership != {"area": area}:
                    reject("interface", "Passive state requires confirmed membership in this area.")
        if policy == "ospf_network_v1" and "network_prefix" in params:
            network = ipaddress.IPv4Network(params["network_prefix"], strict=True)
            matching = {name for name, row in interfaces.items()
                        if any(ipaddress.IPv4Interface(address).ip in network for address in row.get("ip_addresses", []))}
            if not matching:
                reject("network_prefix", "No planned interface has an address inside this network.")
            if "network_interfaces" in params:
                if set(params["network_interfaces"]) != matching:
                    reject("network_interfaces", "Confirm exactly the inventory interfaces selected by this network prefix.")
                for name in params["network_interfaces"]:
                    row = interfaces.get(name)
                    if not row:
                        reject("network_interfaces", "An interface is absent from this device.")
                        continue
                    routed(row, "network_interfaces")
                    if row.get("logical_units") != [0] or row.get("encapsulation") != "inet" or "ospf" not in row or row["ospf"] not in (None, {"area": area}):
                        reject("network_interfaces", "Select known inet unit 0 interfaces without conflicting OSPF membership.")
        if policy == "ospf_redistribute_v1":
            policies = records("route_policies")
            selected = policies.get(params.get("route_policy"))
            if "route_policy" in params and (not selected or selected.get("bounded") is not True
                    or selected.get("default_action") != "deny" or not selected.get("allowed_prefixes")
                    or params.get("redistribution_source") not in selected.get("sources", [])):
                reject("route_policy", "Select a bounded default-deny policy for the requested source.")
            if selected and any(ipaddress.IPv4Network(p, strict=True).prefixlen == 0 for p in selected.get("allowed_prefixes", [])):
                reject("route_policy", "A default-route/permit-all selector is not a bounded export policy.")
            if "export_policy_name" in params and params["export_policy_name"] in policies:
                reject("export_policy_name", "Use an unused wrapper policy name; existing policies are not overwritten.")
            if ospf.get("export_policies") != []:
                reject("operation_id", "This initial export contract requires explicitly empty OSPF export attachments.")
        return issues

    if policy.startswith("acl_"):
        acl = next((row for row in facts.get("acls", []) if row.get("name") == params.get("acl_name")), None)
        if vendor == "juniper" and acl and policy != "acl_create_v1":
            rows = acl.get("rules", [])
            if acl.get("term_naming") != "rule-id" or any(row.get("term_name") != f"rule-{row['acl_rule_id']}" for row in rows):
                reject("acl_name", "Numeric rule IDs must have an authoritative rule-N term-name mapping.")
            if policy in {"acl_add_v1", "acl_modify_v1"} and "acl_rule_id" in params and "next_rule_id" in params:
                following = sorted(row["acl_rule_id"] for row in rows if row["acl_rule_id"] > params["acl_rule_id"])
                if params["next_rule_id"] != (following[0] if following else 0):
                    reject("next_rule_id", "Confirm the next higher existing term ID, or 0 when appending at the end.")
            if policy == "acl_attach_v1":
                logical_unit()
        if vendor == "huawei" and policy == "acl_attach_v1" and acl and acl.get("unmatched_action") != "permit":
            reject("acl_name", "Record and confirm Huawei traffic-filter's unmatched permit behavior.")
        return issues

    if not policy.startswith("qos_"):
        return issues
    classifiers, policies = records("classifiers"), records("qos_policies")
    classifier = classifiers.get(params.get("classifier_name"))
    selected_policy = policies.get(params.get("policy_name"))
    schedulers = records("schedulers") if vendor == "juniper" else {}
    behaviors = records("traffic_behaviors") if vendor == "huawei" else {}

    def classifier_exists(name, field):
        item = classifiers.get(name)
        if not item or item.get("match_type") != "dscp" or item.get("match_mode") != "any":
            reject(field, "Select a confirmed DSCP-only match-any classifier.")
        return item

    if policy == "qos_classifier_v1" and classifier:
        reject("classifier_name", "Classifier already exists; use explicit DSCP replacement.")
    if policy == "qos_dscp_v1" and "classifier_name" in params:
        classifier_exists(params["classifier_name"], "classifier_name")
        if classifier:
            if classifier.get("attachments") != []:
                reject("classifier_name", "Edit only a confirmed detached classifier.")
            if "previous_dscp_values" in params and params["previous_dscp_values"] != classifier.get("dscp_values"):
                reject("previous_dscp_values", "Confirm the exact existing DSCP list.")
            if vendor == "juniper":
                for field in ("forwarding_class", "loss_priority"):
                    if field in params and params[field] != classifier.get(field):
                        reject(field, "Replacement must select the recorded forwarding-class/loss-priority bucket.")
    if "forwarding_class" in params and params["forwarding_class"] not in facts.get("forwarding_classes", []):
        reject("forwarding_class", "Choose an existing forwarding class.")
    if policy == "qos_policy_v1":
        if selected_policy:
            reject("policy_name", "A policy with this name already exists.")
        seen = set()
        for i, term in enumerate(params.get("policy_terms", [])):
            if not isinstance(term, dict):
                continue
            if vendor == "huawei":
                if "classifier_name" in term:
                    classifier_exists(term["classifier_name"], f"policy_terms[{i}].classifier_name")
                if "behavior_name" in term and not behaviors.get(term["behavior_name"], {}).get("actions"):
                    reject(f"policy_terms[{i}].behavior_name", "Select a confirmed behavior with explicit actions.")
            else:
                fc = term.get("forwarding_class")
                if fc in seen:
                    reject("policy_terms", "Each forwarding class may occur only once.")
                seen.add(fc)
                if fc is not None and fc not in facts.get("forwarding_classes", []):
                    reject(f"policy_terms[{i}].forwarding_class", "Choose an existing forwarding class.")
                if "scheduler_name" in term and term["scheduler_name"] not in schedulers:
                    reject(f"policy_terms[{i}].scheduler_name", "Select an existing scheduler.")
    if policy == "qos_scheduler_v1":
        if vendor == "huawei" and port:
            if "queue_id" in params and params["queue_id"] not in port.get("wrr_queues", []):
                reject("queue_id", "Select a queue explicitly recorded as WRR-capable on this interface.")
        if vendor == "juniper":
            scheduler = schedulers.get(params.get("scheduler_name"))
            if scheduler and scheduler.get("attachments") != []:
                reject("scheduler_name", "Edit only a detached scheduler; attached-policy impacts require review.")
    if policy in {"qos_shaping_v1", "qos_policing_v1", "qos_attach_v1"} and port:
        if params.get("direction") is not None and params["direction"] not in port.get("qos_directions", []):
            reject("direction", "Unsupported QoS direction on this interface.")
        if type(params.get("rate_bps")) is int and params["rate_bps"] > port.get("speed_mbps", 0) * 1000000:
            reject("rate_bps", "Rate exceeds the recorded port speed.")
    if policy == "qos_shaping_v1" and port:
        if "shaping_rate_bps" not in port or port["shaping_rate_bps"] not in (None, params.get("rate_bps")):
            reject("interface", "Confirm an unshaped interface or the same existing shaping rate.")
    if policy == "qos_policing_v1":
        if selected_policy or params.get("policy_name") in facts.get("policer_names", []):
            reject("policy_name", "Use an unused policer/policy name.")
        if vendor == "huawei":
            if "classifier_name" in params:
                classifier_exists(params["classifier_name"], "classifier_name")
            if params.get("behavior_name") in behaviors:
                reject("behavior_name", "Use an unused traffic-behavior name.")
            attachment("qos_bindings", params.get("policy_name"))
        else:
            routed(port)
            logical_unit()
            attachment("policer_bindings", params.get("policy_name"))
    if policy == "qos_attach_v1":
        kind = "mqc" if vendor == "huawei" else "scheduler_map"
        if "policy_name" in params and (not selected_policy or selected_policy.get("kind") != kind):
            reject("policy_name", f"Select a confirmed complete {kind} policy.")
        attachment("qos_bindings", params.get("policy_name"))
        if vendor == "juniper" and selected_policy:
            terms = selected_policy.get("terms", [])
            if not terms or any(t.get("scheduler_name") not in schedulers or t.get("forwarding_class") not in facts.get("forwarding_classes", []) for t in terms):
                reject("policy_name", "Scheduler map references are incomplete.")
            elif port and sum(schedulers[t["scheduler_name"]]["bandwidth_bps"] for t in terms) > port.get("speed_mbps", 0) * 1000000:
                reject("policy_name", "Scheduled bandwidth exceeds port capacity.")
        if vendor == "huawei" and selected_policy:
            terms = selected_policy.get("terms", [])
            if not terms or any(t.get("classifier_name") not in classifiers or not behaviors.get(t.get("behavior_name"), {}).get("actions") for t in terms):
                reject("policy_name", "Classifier/behavior references are incomplete.")
        if vendor == "juniper" and "classifier_name" in params:
            classifier_exists(params["classifier_name"], "classifier_name")
            attachment("classifier_bindings", params["classifier_name"], "ingress")
            if port and port.get("logical_units") != [0]:
                reject("interface", "DSCP classifier attachment requires the recorded logical unit 0.")
    return issues
