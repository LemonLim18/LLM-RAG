# Inventory-context device resolution

## Flow and ownership

Each operation retains its original user-text clause. The planner cannot replace
it with catalog examples or move an unverified hostname from another operation.

`original clause -> device description -> evidence-backed constraints -> inventory matching -> selection or clarification`

- `app/devices/target_query.py` extracts names and descriptive attributes. Known
  inventory terms use deterministic extraction. For unresolved descriptions,
  the local LLM may propose field/value/evidence triples. Only literal evidence
  or centrally defined aliases are accepted; the LLM never selects device IDs.
- `app/devices/target_resolver.py` checks every constraint against inventory.
  Weighted scores rank suggestions only. They cannot override a contradiction.
- `data/inventory/attributes.json` defines stable attribute IDs, display labels,
  JSON field paths, weights, and aliases (for example Kuala Lumpur -> KL).
- `data/inventory/devices.json` owns the facts. New sites, vendors, roles, tags,
  and named interfaces are discovered without adding keyword branches in code.
- `PlannedTask.target_queries` stores descriptions, cardinality, unresolved
  words, and source evidence. `target_resolution` explains successful matches.
  Issues include candidate labels, matched attributes, and conflicting facts.

Registry paths can traverse lists (`interfaces.name`, `capabilities.features`).
Keep attribute IDs stable when changing labels or aliases. Alias mappings must
express real equivalents; never add a synonym merely to force a failed match.
Inventory/attribute edits do not require rebuilding the operation RAG index.

## Selection rules

| Request | Outcome with the sample inventory |
|---|---|
| Penang edge Juniper router | R3; every attribute matches |
| the KL core router | Ask R1 or R2 |
| KL core routers | R1 and R2, explicitly plural |
| one of the core routers | Ask R1 or R2 |
| Cisco R2 | Conflict; R2 is Huawei |
| Cisco router in Penang | Conflict; no device satisfies both attributes |
| Router 9 | Unknown identity; offer inventory candidates |
| London Cisco router | Unknown qualifier; ask without discarding London |
| router with management IP 10.0.0.12 | R2 |
| routers with management subnet 10.0.0.0/24 | All three sample routers |
| routers supporting IS-IS | R3 based on advertised capability |
| router running IOS-XE version 17.9 | R1; exact version match |

A singular description with multiple matches always asks. Multiple names or
explicit plural groups can select multiple devices. All selectors in a task
must resolve before validation completes. Bindings keep independent collection
state, but the entire request must validate before any binding renders.
Matching the name does not waive an incompatible site/vendor description.
Overlapping aliases use the longest phrase: `edge router 1` resolves to R3,
without accidentally treating its suffix `router 1` as R1 as well.

Device descriptor evidence is excluded from operation parameter extraction.
For example a router's stated management address is not permission to configure
that same address on a data interface. Interfaces are still cross-checked by
the existing per-device context validator after device selection.

## Conversation

Run from the V2 directory:

```powershell
..\..\.venv\Scripts\python.exe main.py "Create VLAN 20 on the KL core router" --interactive
```

The terminal asks only the active task's next field, showing descriptive device
choices. Answer `the Huawei one` to add the vendor constraint while retaining
KL/core. Answer `select 2` or `R2` to explicitly select that identity.
For a conflict, `Juniper` replaces a previously stated vendor, keeping the site.
A device reply never runs the operation-parameter extractor.

An explicit name or `select NUMBER` replaces that selector's previous description. This is
the user's correction, not an automatic override by the LLM. Descriptive replies
preserve other constraints, and cannot silently drop unknown words. When an
unrecognized qualifier cannot be corrected descriptively, choose the actual
device with `select NUMBER` or its hostname. Other unresolved selectors in the
logical task survive. A correction of a resolved per-device binding applies only
to that binding.

Sessions persist the queries and evidence. Older sessions without these fields
use their saved target references on the next validation. Old configurations are
discarded and revalidated on resume; this cannot certify prior extraction or
device syntax. Rerun the original prompt to apply current extraction rules.

## Bounds and checks

This is constrained natural-language interpretation, not unrestricted human
understanding. Unrecognized descriptions, exclusions (`except R2`), alternatives
(`Cisco or Juniper`), comparative versions, and complex shared-target sentences
can need clarification. State each operation and its target explicitly for
predictable multi-operation planning. Inventory must record a fact before it
can support selection; missing metadata is not inferred from general knowledge.
Version matching is exact. Management-subnet selection uses IP membership.
Capabilities are inventory claims, not live device discovery.

Tests in `tests/test_target_resolution.py` cover unique/ambiguous/plural/conflicting
selectors, alias collisions, unknown qualifiers, model failure/hallucinations,
multi-operation association, descriptive correction, session roundtrip, and
management-IP separation from operation parameters. Run the existing suite:

```powershell
..\..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
