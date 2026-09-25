# V2 Revision Notes

Revision: context-aware network operation collection and clarification.
Recorded: 2026-09-25. Scope: the current local LLM-RAG core.

## Plans Used

Both plans guided this revision:

- [implementation.md](../implementation.md): primary plan for validation,
  clarification state, operation/device bindings, context lookup and rendering.
- [Revised context-aware resolution plan](../revised_implementation_plan_context_aware_network_intent_resolution.md):
  secondary guide for inventory-backed device descriptions, candidate explanations
  and independent intent/device state.

Where the proposals differ, the primary plan takes precedence. A relevance score
never overrides contradictory inventory attributes. The secondary document remains
a design proposal; its aspirational claims are not proof of implementation quality.

The shared core workflow is implemented. Full fulfilment of every production-level
ambition, perfect prompt understanding and correctness on real devices are not established.

## What Changed

| Area | Revision |
|---|---|
| Answer acceptance | Parse the active field, normalize, validate, then update state. Invalid parameter replies preserve previously accepted values. |
| Reported parser bugs | Reject netmasks as host addresses; keep interface slash notation out of prefix extraction; match complete interface names instead of substrings. |
| Partial parameters | Preserve incomplete nested records, such as an OSPF interface whose area is missing. Ask for each nested field separately. |
| Operation/device mapping | Represent each resolved operation/device binding independently, retain source text evidence, and support clear shared-target clauses. |
| Uncertainty | Keep unsupported actions and ambiguous values unresolved. Use bounded model repair and require confirmation of model-proposed operations. |
| Planned context | Add approved local lookups, typed records, dependency scoping and source revisions. Offer recorded configuration values for confirmation. |
| Conversation | Add structured questions, typed options, custom input, stable identities, answer history and explicit corrections. |
| Persistence | Resume saved sessions, migrate older records, reject stale answers and revalidate after source changes. |
| Rendering | Complete bindings wait for the whole request to validate. A rendering failure publishes no partial configurations. |
| Vendor requirements | Require an explicit Juniper BGP peer group; remove the hidden group-name fallback. Add a lab platform/release allowlist. |

The inventory description resolver and central catalog were retained and extended.
The existing 12 operations remain: two each for VLAN, OSPF, BGP, IS-IS, static
routing and interface IPv4. This revision did not add another operation category.

## Current Capabilities

| Scenario | Supported behavior |
|---|---|
| `Create VLAN 20 on the Penang edge Juniper router` | Resolve the description against inventory attributes to R3, retaining matching evidence. |
| `Create VLAN 20 on the KL core router` | Ask which matching device; `the Huawei one` refines the description to R2. |
| `Create VLAN 20 on Cisco R2` | Detect the vendor mismatch and ask for correction. |
| `Create VLAN 20 and configure OSPF on R1 and R2` | Create four independent operation/device bindings. |
| `Create VLAN 20 and configure OSPF on R1; create VLAN 30 on R2` | Bind the first two operations to R1 and the last to R2. |
| `Configure OSPF process 100 on R1 using Ethernet1/1 and Loopback0` | Preserve both interface records and ask for their missing areas separately. |
| Missing required parameter | Search approved, scoped context; offer valid choices when available, otherwise request input. |
| Unknown interface such as `Ethernet1/10` on R1 | Reject it and offer inventory choices; never silently change it to `Ethernet1/1`. |
| Conflicting changes to the same recorded resource | Block rendering until corrected or explicitly confirmed in their listed order. |

All intents are processed before the clarification conversation starts. Operation
and target questions precede dependent parameter questions. Each displayed question
identifies the operation, device and exact field being answered.

## Terminal Usage

From the `network_rag_catalog_v2` directory, use the existing environment:

```powershell
..\..\.venv\Scripts\python.exe main.py "Configure OSPF on R1 and R3" --interactive
..\..\.venv\Scripts\python.exe main.py --resume SESSION_ID --interactive
..\..\.venv\Scripts\python.exe main.py --resume SESSION_ID --edit TASK_ID vlan_id 30
```

- `select 1`: select an offered option; `select 1,2`: select several where allowed.
- `1` or `value 1`: enter the literal value 1, not option 1.
- Enter `100` for an integer question, rather than `process 100`.
- `more` and `filter TEXT`: navigate larger option sets.
- `edit TASK_ID FIELD_PATH VALUE`: explicitly correct an earlier field.
- Nested paths include `interfaces[0].area`.
- `quit`: leave the session available for later resume.
- `confirm order`: explicitly resolve a pending cross-task ordering confirmation.

Custom input is always available, but cannot bypass schema or inventory checks.
Choosing a device/interface does not edit inventory. Correcting an accepted value
rechecks the request and invalidates affected outputs or context decisions.

## Important Notes

- `validated` means a binding has completed collection. `rendered` means its
  configuration was published with the complete request. Request/session `ready`
  means a rendered preview, not execution or proof of network correctness.
- The LLM interprets and proposes. Catalogs, schemas, inventory and validators
  govern accepted operations, device facts, values and template selection.
- Planned sample records are not live device state. A single suggested configuration
  value still requires confirmation. Intended assignments can be overridden only
  where permitted and explicitly confirmed; authoritative facts cannot.
- Source changes trigger revalidation and can require reconfirmation. Device-group
  membership changes cannot silently reuse a previously completed plan.
- Stable machine IDs should remain stable. Change display names, aliases and
  wording through the catalog. Required fields/types/ranges belong in schemas.
- Future UI clients can reuse `session.next_question`, `ClarificationAnswer`,
  `apply_answer()` and `apply_correction()`. The terminal is currently the interface.

## Verification and Remaining Limits

The previous implementation verification recorded **62 passing automated tests**,
a successful terminal smoke check and a clean `git diff --check`. Tests cover real
deterministic parsing/validation and use simulated model responses for reproducible
failure and hallucination cases. This documentation update does not constitute a
new test run.

Complex language, pronouns, exclusions and unusual per-device assignments can still
require clarification. A weak model is not proven equivalent to a strong model.
Live-model accuracy and latency still need evaluation against realistic prompts.

Template smoke tests demonstrate rendering, not command acceptance by real network
operating systems. Existing lab templates still need vendor/release validation.
Conflict detection uses declared resource keys; it is not network simulation.

There is no website, external database/tool integration, Ansible execution, topology
discovery or business-level intent engine in this revision. JSON persistence also
does not provide a multi-user service's concurrency or authentication controls.

Next priorities within the current scope are to evaluate the installed local model,
turn failed conversations into regression cases, and validate templates for the
specific lab devices before expanding integrations.

## Where to Continue

- [Technical behavior and API contract](CONTEXT_AWARE_REVISION.md)
- [AI handoff and module map](AI_HANDOFF.md)
- [Terminal test prompts](TEST_PROMPTS.md)
- [Catalog and context governance](CATALOG_GOVERNANCE.md)
- [Device-resolution details](DEVICE_RESOLUTION.md)

The central data files are `data/catalog/{operations,parameters,context_rules,
template_support}.json`, `data/inventory/{devices,attributes}.json`, and
`data/planned/parameters.json`. Sessions are stored under `storage/sessions/`.
