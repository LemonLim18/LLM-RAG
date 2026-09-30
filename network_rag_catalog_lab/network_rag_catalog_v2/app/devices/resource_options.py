"""Suggestions from device-scoped planned facts, never automatic intent defaults."""


def resource_options(policy, device, path, params, revision):
    if not policy:
        return []
    resources = device.get("resources", {})
    if not isinstance(resources, dict):
        return []

    def records(key):
        values = resources.get(key, [])
        return [row for row in values if isinstance(row, dict)] if isinstance(values, list) else []
    fields = {"acl_name": ("acls", "name"), "classifier_name": ("classifiers", "name"),
              "policy_name": ("qos_policies", "name"), "route_policy": ("route_policies", "name"),
              "process_id": ("ospf_processes", "process_id")}
    fields.update({"behavior_name": ("traffic_behaviors", "name"), "scheduler_name": ("schedulers", "name")})
    rows = []
    if path == "current_vlan_name":
        rows = [row.get("name") for row in device.get("vlans", []) if row.get("vlan_id") == params.get("vlan_id")]
    elif path == "forwarding_class":
        rows = resources.get("forwarding_classes", [])
    elif path == "area" and device.get("vendor") == "juniper":
        rows = list(resources.get("ospf_default", {}).get("areas", {}))
    elif path == "next_rule_id":
        ids = sorted(rule["acl_rule_id"] for acl in records("acls") if acl.get("name") == params.get("acl_name")
                     for rule in acl.get("rules", []) if rule["acl_rule_id"] > params.get("acl_rule_id", -1))
        rows = [ids[0] if ids else 0]
    elif path in fields and isinstance(resources, dict):
        collection, identity = fields[path]
        rows = [row.get(identity) for row in records(collection)]
    elif path == "previous_dscp_values" and isinstance(resources, dict):
        rows = [row.get("dscp_values") for row in records("classifiers") if row.get("name") == params.get("classifier_name")]
    elif path == "acl_rule_id" and isinstance(resources, dict):
        rows = [rule.get("acl_rule_id") for acl in records("acls") if acl.get("name") == params.get("acl_name") and isinstance(acl.get("rules"), list)
                for rule in acl["rules"] if isinstance(rule, dict) and rule.get("kind") == "ace"]
    elif path in {"vlan_id", "native_vlan", "allowed_vlans"}:
        rows = [row.get("vlan_id") for row in device.get("vlans", []) if isinstance(row, dict)]
        if path == "allowed_vlans":
            rows = [[value] for value in rows if value is not None]
    return [{"value": value, "label": str(value), "kind": "fact",
             "source_ref": f"inventory:{device['id']}:{path}:{value}", "source_revision": revision,
             "explanation": "Confirm this device-scoped planned resource."}
            for value in rows if value is not None]
