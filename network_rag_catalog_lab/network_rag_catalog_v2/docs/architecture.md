# Architecture Notes — v2

## The abstraction change

The original lab implicitly modeled:

```text
Request = one operation + one target
```

The revised model is:

```text
Request = many operation intents
Intent  = one logical operation + zero or more target references
Target  = human reference -> canonical inventory device
```

This is the key change. Everything below the planner can now remain mostly single-operation focused while the planner orchestrates repeated execution of that pipeline.

## Why not make the LLM generate the whole playbook?

Because the system needs several deterministic boundaries.

The LLM is good at interpreting language, but the application should remain authoritative about:

- which operations exist;
- which parameters are legal;
- which devices actually exist;
- which vendor/platform/version a device uses;
- which template is allowed;
- whether parameters pass schema validation.

Therefore the LLM is an interpreter/orchestrator, not the source of truth.

## Planner contract

The planner returns:

```json
{
  "intents": [
    {
      "intent_id": "intent-1",
      "request_text": "Create VLAN 100 named STAFF on R1 and R2",
      "target_refs": ["R1", "R2"]
    }
  ]
}
```

Notice that the planner does not need to decide that the operation is `create_vlan`. That remains the job of the existing category + retrieval + operation-selection pipeline.

This prevents the planner from becoming a giant monolithic LLM prompt that must understand every operation and every schema.

## Target resolution

Target resolution is intentionally a separate step:

```text
"core router 1"
       |
       v
normalize
       |
exact hostname/display name/alias match
       |
optional conservative fuzzy candidate matching
       |
canonical R1
       |
full inventory record
```

If two devices are plausible, the system should not choose one silently.

## Multi-device execution

A logical operation can target multiple devices:

```text
create_vlan
   |
   +-- R1 -> Cisco IOS-XE -> Cisco Jinja
   +-- R2 -> Huawei VRP    -> Huawei Jinja
```

The parameters are shared at the logical-operation level, while rendering is performed separately for each device.

## Multi-vendor execution

Vendor is not an LLM decision:

```text
user target
   -> target resolver
   -> inventory
   -> vendor/platform/version
   -> template registry
```

This prevents a language model from accidentally choosing a Cisco template for a Huawei device.

## RAG boundary

ChromaDB stores one semantic document per catalog operation. It answers:

> "Which known operation does this request most resemble?"

It does not answer:

> "What is the current IP address of R1?"

or:

> "What is the CPU usage right now?"

Those should come from authoritative tools/APIs. The same principle should be used later for NetBox, CLI/Netmiko, InfluxDB and syslog.

## Validation boundary

LLM output is treated as untrusted. Extraction keeps only values grounded in the user's request and required-but-missing parameters become `null`. The deterministic validator then decides whether the task is renderable or requires clarification.

```text
parameter extraction
       |
       v
grounding/completeness validation
       |
   +---+---+
   |       |
missing  complete
   |       |
clarify  context validation
           |
        template rendering
```

No template should render on the missing branch.

## Inventory shape

The local JSON inventory is a stand-in for future authoritative sources. Records now include:

- stable internal IDs and external source references;
- NetBox-like role, site, platform and status fields;
- Ansible connection variables;
- monitoring labels suitable for InfluxDB-style tags;
- device capabilities;
- interface records with aliases, roles and neighbor hints.

Future adapters should translate NetBox/PostgreSQL/Redis/API records into this same in-memory shape, so the planner, resolver, validator and renderer do not need to care where facts came from.

## Future approval layer

The next architectural layer should consume `ExecutionPlan`:

```text
ExecutionPlan
   |
   +-- compatibility checks
   +-- config diff
   +-- policy/security validation
   +-- human approval
   |
   v
Ansible inventory + playbook
   |
   v
execution
   |
   v
post-change verification
```

The important point is that execution is downstream of planning/rendering, not mixed into the LLM call.
