# Hardcoded versus data-driven behavior

This is a static inventory of meaningful domain choices, not a proposal to refactor. “Engine invariant” means deliberate safety/control logic; “domain knowledge” means a new operation/vendor may require Python review. Search patterns given here before adding a field; there may be smaller local cases not exhaustively enumerated.

| Location | Hardcoded decision and why it exists | Verdict / if moved or removed |
|---|---|---|
| `config.py` | Ollama model names, Chroma collection, runtime modes | Deployment setting; configurable, but changing embedding model requires index rebuild |
| `planner.intent_planner:_fallback_plan/_ambiguous_scope` | `;`, `and`, `then`, action verbs, pronouns/negation regex; bounded planner repair | Domain-sensitive grammar; a catalog-driven grammar could reduce drift, but removing loses multi-clause fallback |
| `retrieval.category_classifier:classify_category` | One category per clause; catalog phrases then LLM | Engine shape; wrong category can exclude correct operation |
| `pipeline._process_intent` | Top `3` candidates and semantic `OPERATION_PROPOSAL` | Tuning + safety invariant; configurable top-k could help recall |
| `target_query:parse_description/extract_target_queries` | Device introducers, labels, `R1/SW1/FW1`, plural cues, interface exclusions | Domain grammar; attributes/aliases already data-driven in `attributes.json`; moving all parser logic to data needs a safe grammar interpreter |
| `target_resolver:resolve_queries` | All constraints must match; `many` bypasses ambiguity, top 3 suggestions | Safety invariant; never replace with best-score-only selection |
| `normalizer:_deterministic_values/explicit_alternatives` | Named fields (`vlan_id`, `process_id`, `address`, `interfaces`, etc.) and network regexes | Domain knowledge; useful weak-model fallback, but every new parameter may need a reviewed parser or structured literal evidence |
| `normalizer:prefix_length_from_text` | IPv4/CIDR/netmask forms, range 0-32 | Protocol-specific primitive; keep deterministic or register a reviewed parser |
| `evidence:_read_literal/grounded_scalar` | JSON/quoted/primitive-list evidence grammar | Mostly engine invariant; recognizes explicit values only, may reject valid prose |
| `validator:_network_value_issues/_safe_string_issues/_unique_interface_issues` | IPv4 fields, OSPF area, unsafe punctuation, duplicate interface names | Network safety knowledge behind mandatory handlers; catalog cannot remove them; new formats need code review |
| `rule_registry` | Allowed validation/normalizer/derivation handler IDs and DSCP/mask/wildcard/Huawei calculations | Code-reviewed extension point; do not permit arbitrary imports from catalog |
| `fields.parse_answer` | Prefix, integer, boolean, JSON collection, special `interfaces` parse | Field-scoped parsing invariant plus network exception; extend carefully |
| `context_validator` | Specific interface field names and capability feature comparison | Domain logic; schema could mark interface fields, but current explicit handling avoids accidental non-interface normalization |
| `operation_policies` | Policy IDs, exact Cisco/Huawei/Juniper reviewed profiles, loopback patterns, L2/VLAN/LAG constraints | Hardware-domain policy. Data names the policy, Python enforces it. Removing permits unsupported configs |
| `resource_policies`, `vendor_policies` | ACL/QoS/route resource shape, vendor attachment semantics | Vendor/domain safety; catalog context may select policies but not implement arbitrary semantics |
| `questions.build_questions` | Operation->target->parameter priority, schema enum/inventory/planned option assembly | Engine control plus some field exceptions (`address`, `prefix_length`, `interfaces[]`) |
| `context.parameter_options/context_conflicts` | Planned record kinds `fact/candidate/intended_assignment`, override rules | Safety invariant; data scopes permitted lookups and values |
| `template_selector` | Files-mode directory convention, published binding path | Mode-specific architecture; an all-binding design could unify them but would change direct lab behavior |
| `renderer._prepare_context` | Legacy optional keys; derivation registry | Compatibility debt; contracts are cleaner in published mode |
| `file_runtime.file_documents` | Hardcoded vendor list in `unimplemented_vendors` (`cisco/huawei/juniper`) | Domain list that could derive from inventory/support; current available templates are discovered dynamically |
| `publication.validate_bindings` | Standalone templates, exact contract fields, version bump, indexed-before-active | Governance safety invariant; complexity justified for published mode, unnecessary for a tiny file-only prototype |
| `knowledge.pack_review/pack_promote` | Pack format, six-domain promotion order, non-overwrite policy | Expansion/governance complexity, not needed for a single manually edited operation |

The central catalog does **not** make the whole system data-driven. It centralizes stable names, aliases, types and mappings, while parser regexes, policy implementations, validation handler semantics and some vendor profile assumptions remain in Python. The cost of moving them all to editable data would be a rule language with its own validator and security model; simpler reviewed handlers are defensible until changes become frequent.
