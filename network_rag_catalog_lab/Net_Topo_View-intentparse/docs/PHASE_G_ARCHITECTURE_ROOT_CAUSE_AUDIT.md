# Phase G — Architecture root-cause audit and generalized remediation design

Date: 2026-11-01, Asia/Kuala_Lumpur. Inspected HEAD: **8a7f86ce4e4d7c12d2e0565bfa53ab64f4ca756d**, including the existing uncommitted implementation. This is an audit and proposed design, not an implementation or a new Phase G qualification.

**Decision: retain the model-neutral role interface, existing LangGraph, authorization, accepted interface scope/source-policy repairs, and the repaired core/auxiliary validation boundary. Keep completeness, Approach A and the old harness OFF by default. Do not add another planner, agent or universal semantic verifier.**

Audit evidence: [new isolated audit directory](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit). Historical outputs and scores are unchanged. No live inference, application/browser actions, model changes or new cloud reservations were performed.

## 1. Executive diagnosis

### What is actually failing

The remaining failures have several distinct causes.

1. **Completed reasoning can be wrong with the necessary operands present.** In SS-BROAD, the model receives explicitly simulated observations, modeled forwarding failures and instructions separating them from physical measurements, then calls a down interface an established physical/operational cause. In SS-TIME it receives all running captures, the unapplied staged file, both operational observations and the applied event, yet assigns a running description to an unobserved time. RI08 preserves the correct owned context and zero-read constraint but gives an overconfident diagnostic discrimination rule. These are demonstrated interpretation errors. They do not establish that every difficult task exceeds the model's capability.

2. **Current verification does not certify the prose or complete task.** It checks declared source-bound assertions. A correct declared interface status does not validate an undeclared physical-cause sentence. The latest bad prose survives composition; it was not a correct answer overwritten by the gateway. The response is marked unverified, which avoids a certification claim but does not make an incorrect explanation adequate.

3. **Context organization is costly and partly redundant.** The latest broad reasoner inputs contain 56,393 then 60,874 characters, versus 5,881–9,032 in the inspected original successful integrations. Actual facts coexist with planning proposals, reader schemas, receipts, an identity index, an evidence ledger, a network map, artifact comparisons and previous-draft review. This is measured complexity, not proof that size caused the errors. There is no controlled representation experiment demonstrating that the added metadata improves reasoning.

4. **Whole-response JSON remains a separate reliability failure.** RI07 received HTTP 200 and finishReason STOP, but the candidate text contains unescaped quotes inside its answer string. Core JSON rejection is correct. It is neither a semantic contradiction nor evidence of timeout/token exhaustion. The separate native-schema request received generic HTTP 400 INVALID_ARGUMENT; its exact rejection cause is unknown.

5. **A current coverage-ledger defect is reproducible offline.** Source coverage associates each result with the last receipt for its reader family, rather than that result's actual query. A successful read followed by a failed read of the same family is reported as two failed reads. This can distort partial coverage and further-investigation decisions. It does not explain the selected historical physical-cause failure, whose supplementary syslog read completed.

6. **Historical architectural failures must not be presented as current.** Canonical interface scope and explicit state-only source policy are repaired. Invalid auxiliary declarations, unknown/paraphrased claims, validator exceptions and device-wide configuration binding no longer automatically become factual contradictions or destroy valid core answers. Offline current-code checks confirm those boundaries.

### Confidence and limits

“Confirmed” below means supported by a specific saved execution or current deterministic reproduction. “Hypothesis” means a plausible mechanism without an isolating experiment. No historical cohort was rerun or regraded. Source evidence and model-visible messages were compared offline; this is not a new direct-model comparison, blinded evaluation or acceptance run.

The most promising next step is a **small frozen-evidence reasoning/configuration comparison and a separately controlled evidence-layout comparison**, while making only the independently justified receipt-identity correction if subsequently authorized. Accumulating more prose validators is unlikely to fix the demonstrated reasoning mechanism.

### Formal stage status is unchanged

The latest retained ledger/checkpoint records G1–G3, G8–G10 and G12 as prior PASS; G4, G5, G6 and G11 remain FAILED; G7 remains BLOCKED at 113/141 native journeys; G0's missing historical baseline remains BLOCKED. This audit closes none of those stages and does not re-evaluate their prior acceptance.

## 2. Actual architecture map

### Real control flow

    Authenticated Floating / Studio request
      -> AIGateway.turn: owner, surface, history, scenario and consent envelope
      -> existing engine selection and RoutingModel
      -> understand_request
           approved model-neutral role path -> Gemini 3.1 IntentPlan
           ordinary/unapproved path -> existing local Qwen/Studio routing
      -> resolve_references
           canonical inventory/owned references; original source policy
      -> select_authorized_tools
      -> execute_tools
           existing registry, LangChain adapters, NetworkReader/V9/document services
      -> evaluate_evidence
           deterministic assessment; approved Gemini 3.5 decision
           optional post_draft review on the completeness experiment
           validated extra reads -> select/execute/evaluate again
      -> verify_facts
      -> compose_response
           preserve approved interpretation or scoped withholding/limitation
      -> END / existing Studio context branch
      -> gateway storage and response
      -> existing Markdown, source disclosures, Copy and handoff UI

Studio engineering branches remain authorize_engineering -> coordinate_engineering -> validate_engineering_result. V9 owns operation/schema/compatibility/rendering; exact-base proposals and user review own edits. Reasoner output does not authorize tools, saving, deployment or device execution.

Primary control sources: [gateway](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/gateway.py:116), [graph and conditional edges](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/engine.py:623), [routing model adapter](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/model.py:24), [registered network query](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/gateway_network.py:50).

### Roles, actual transport and budgets

| Role/boundary | Current implementation | Interpretation |
|---|---|---|
| Ordinary local | Explicit qwen2.5:1.5b; Ollama, temperature 0, context 8192, default 512 output tokens and 30-second local call bound | No automatic stronger-model selection. |
| Complex planner | gemini-3.1-flash-lite, Google generateContent, low thinking, default 2,048 output tokens | A proposal validated against the existing IntentPlan and registered capabilities. |
| Evidence reasoner | gemini-3.5-flash-lite, same provider adapter, low thinking, default 8,192 output tokens | Core decision plus advisory/outcome/auxiliary structures; not a new planner. |
| Google structured output | Role default validated_json: JSON MIME plus schema instruction, followed by strict JSONSchema and Pydantic validation | Does not activate native constrained schema grammar. json_schema is a separate selectable transport. |
| Ordinary approved request clock | Existing 120-second request-wide ceiling; planner stage reserves downstream time; bounded role calls | A per-call allowance is not another full request deadline. |
| Completeness investigation profile | Default OFF. When explicitly enabled, version 3 defaults to 360 seconds total, planner 90, reasoner 120, initial reads 90, supplemental reads 60, adequacy 5, 24 readers, 3 rounds and 5 role calls | These retained experiments do **not** establish the ordinary 120-second acceptance target. No profile was changed here. |
| Message bounds | Multi-model per-call 72,000 characters; evidence packet encoding bound 64,000; cumulative bounds and call counts also apply | Characters are not provider tokens. Oversized packets fail rather than silently discarding raw operands. |
| Cloud access | Exact owner/surface/request/history/scenario/role-settings consent; serialized provider access and persistent quota | Flags alone do not authorize remote transmission. Editor/attachment exclusions remain. |
| Cloud failures | Recorded timeout/quota/provider/core-contract categories; no hidden retry or silent model/transport switch | Provider noncompletion is not failed reasoning. |

Sources: [role definitions/profile/consent](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/model_roles.py:43), [provider transport](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/gemini_provider.py:177), [request authorization and clock](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/gemini_provider.py:281), [model budgets](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/model.py:24).

The current role registry explicitly retires Gemini 3.8 runtime support; older reports describing it as a rollback option are historical. No model was switched during this audit. An existing OpenAI socket has mocked protocol coverage; that is not live interoperability or permission to use it.

A fresh offline process loaded the existing root then backend environment files through lab_config and confirmed these role settings, hybrid=1, multi-model experiment=1, legacy interpret=0, outcomes=0, evidence harness=0 and completeness=0. The credential is loaded; its value is not recorded. This is a configuration-loading check, not inspection of a running backend: [effective offline configuration](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/effective-offline-config.json).

## 3. Boundary-by-boundary findings

### A — Original request, context and routing

**Input/output:** authenticated TurnRequest, assistant surface, owned conversation/history, inventory metadata and prior investigation references become SemanticRoute and AgentState. The original prompt is retained; model plans and derived clauses are additional proposals.

**Authority:** backend ownership, capability registry and original-source restrictions remain above model decisions. Floating is read-only. Studio context/edit/generation uses existing guarded paths.

**References and time:** server-resolved canonical device/interface IDs; prior owned records are labeled prior, not refreshed merely by inclusion. History is selected by use_history and bounded to the retained user turns. Topic switching need not inherit engineering context.

**Verified repair:** the direct role path now restores canonical interface references; explicit source policy controls attribute resolution as well as planner checks. “Prefix” in a state-only request no longer forces inventory and rejects a correct state plan. Current offline tests exercise both surfaces, unknown/wrong-owner scope and source prohibition.

**Remaining limits:** clause extraction and bounded history are not a semantic proof that every desired result was captured. An advisory route is deterministically no-execution, but the approved role path can still depend on an initial planner completion before composing advice. A planner 503 can therefore stop a task whose desired no-read behavior is known. This is a reliability limitation, not evidence that a reader ran illegally.

Code: [request constraints/advisory contract](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/request_contract.py:13), [direct role and reference binding](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/engine.py:90), [gateway routing](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/gateway_routing.py). Tests: [accepted interface/source-policy regressions](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/tests/test_state_interface_scope.py).

### B — IntentPlan and Gemini 3.1 planning

**Input:** full original request, requested clauses, relevant owned user context, existing inventory/source metadata and registered reader schemas. **Output:** intent, desired response, goal, temporal scope and InformationNeed entries containing domain/question/necessity/source_scope/source_categories.

The model does not acquire authority to invent executable identities. Server reference resolution supplies targets; registered strict query schemas and source policy validate execution. No second planner is inserted after the direct model-neutral role plan.

**Required versus optional:** targeted direct-role plans can suppress optional needs; comprehensive mode retains them and reconciles coverage. In SS-BROAD the model proposed state, configuration, knowledge, topology and incidents. The server—not Gemini—added inventory, syslog and telemetry. The later syslog reference query was server-driven supplementation. Those are three different selection mechanisms.

**Observed model planning problem:** the broad plan chose published knowledge for a referenced review record; knowledge.search returned an access-port operation, which did not explain the operational review purpose. Actual syslog later supplied that purpose. More readers did not make this initial source choice correct.

**Representational limit:** source_queries merges needs by domain, widening incompatible temporal scopes to both and combining categories. InformationNeed has no per-need target/interface/VRF/time-query operands. Same-family outcomes for different entities or intervals can therefore require broader reads and later rebinding. This is a code-confirmed expressiveness limit; the selected traces do not prove it caused their physical/temporal overclaims. Do not invent a new independent outcome authority to solve it.

**Failure distinctions:** schema-invalid proposals fail before tools; known-source queries returning unavailable are evidence limitations; 503/timeouts are provider noncompletion. None should be scored as a completed reasoning error.

Code: [InformationNeed/source query merging](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/planning.py:19), [role proposal](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/planning.py:200), [coverage reconciliation](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py:58).

### C — Actual readers, parameters, filtering and receipts

The full path is IntentPlan -> authorized tool step -> network_context -> registry validation -> NetworkReader -> scenario/ordinary source -> filter/sort/limit -> ToolResult/evidence receipts.

**Preserved contracts:**

- Canonical interface IDs are passed through both context paths, checked against selected devices, and honored by state/telemetry. Unsupported reader scope, unknown IDs, wrong owner and live collection requests fail without widening.
- Interface filtering preserves whole typed relationships where slicing would destroy endpoint meaning. Deduplication removes exact identified repeats, not different authored/modeled observations, times or contradictions.
- Configuration source_scope distinguishes stored/current/historical artifacts. Planned topology does not become measured connectivity.
- Scenario revision, origin, timestamps, source status, totals and truncation are returned. Ordinary production sources do not silently become scenario data.
- Native configuration, V9 published knowledge, documents and exact scalar inventory use their existing authoritative services.
- Query bounds include eight devices, up to 64 canonical interfaces, result limit at most 100, registered categories and validated time filters.

**VRF:** records retain VRF and typed assertions can bind it, but NetworkQuery does not define an executable VRF filter. Extra fields are rejected by the strict contract. There is no evidence here that VRF silently disappears from the selected records; there is a capability gap for a narrowly scoped VRF read. Per-need target/time scope is similarly limited upstream. These should not be confused with the repaired interface loss.

**New confirmed receipt defect:** source_coverage searches the reversed query list by reader name for every result. It then uses the last result status as the family status. A successful network.syslog result followed by a failed network.syslog query becomes two QUERY_FAILED statuses. The successful evidence itself remains in results; the coverage interpretation is wrong.

[Offline counterexample](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/coverage-receipt-counterexample.json) proves the defect with the current function and a positive single-query control. The selected supplementary successes do not reproduce the failed-second-query condition; this is not their proven root cause.

No equivalent interface-scope-loss defect was established in another reader family. Configuration artifacts often have device-wide scope deliberately; a missing interface_id on such a record is not another owner's interface.

Code: [NetworkQuery](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/gateway_network.py:50), [scope/filter logic](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/gateway_network.py:147), [reader](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/gateway_network.py:179), [context adapter](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/gateway_network.py:507), [coverage join](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py:96).

### D — Retrieved evidence to model-visible context

The approved reasoner receives actual reader data and source receipts, not only the old short factual table. The packet retains original instruction, clauses, user context, planning proposal, current results, source metadata, owned advisory context and continuation. Enabled investigation metadata adds record index, evidence requirement ledger, source types, network map, artifact comparisons and prior-draft review.

**Offline delivery comparison:** for the inspected latest cases, non-inventory reader data in the captured reasoner packet equals the captured authorized-reader data. Inventory is intentionally projected into scoped metadata/network context; it is not a byte-identical full-inventory dump. All eight temporal source records and artifact comparison operands are present in both temporal outcomes. This proves delivery of those necessary facts, not universal completeness for every question.

| Saved execution | Reasoner input characters | Compact schema characters | Relevant delivery observation |
|---|---:|---:|---|
| MN-01 / MN-02 | 9,032 / 8,764 | 1,131 | Two readers; direct shutdown/state/probe relationship. |
| MN-03 | 5,881 | 1,131 | Two readers; explicit current/saved values and unavailable syslog. |
| SS-BROAD, first / revised | 56,393 / 60,874 | 3,548 | 34 then 35 typed records; relevant event arrives in real supplementary syslog read. |
| SS-TIME / SQ-TEMP | 31,975 / 32,289 | 3,536 | Same eight source-record values and comparisons; different surrounding planning/receipt/surface metadata. |
| RI08 | 10,701 | 3,514 | Zero fresh reads; 5,510 characters of explicit prior owned advisory context. |
| RI07 | 46,969 | 3,548 | Required inputs delivered; invalid whole response later fails parsing. |
| CVR-01, first / revised | 56,633 / 61,357 | 3,548 | Referenced event added and delivered to revised reasoning; final quality still not assured. |

Measured sections in revised SS-BROAD: reader_results 29,097 characters, investigation_context 8,649, record index 5,262, retrieval boundary 4,837, evidence ledger 3,992, sources 3,291 and planning proposal 2,984. Section totals use compact subobject serialization; the full input also includes instructions/formatting. These are character counts, not token estimates.

**Useful organization:** raw source IDs, canonical owners, directional flow structure, explicit origin, timestamps, running-only comparison pairs and source limits are available. **Weakness:** the model must reconcile multiple views of the same records and output their meaning again in prose/outcomes/claims. Some source-owned depends_on arrays are empty even on derived records; code cannot invent missing lineage. “Simulated” is an origin axis, not an alternative fact-kind to configuration or observation.

No silent truncation of these actual critical operands was found. Record-index/network-map summary limits are distinct from raw reader-result delivery; reader truncation is separately disclosed. Hard packet/input failures should remain explicit.

Code: [evidence packet](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:67), [metadata enrichment/deduplication](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/evidence_harness.py:87), [map/classification/comparisons](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py:119). Proof: [trace index](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/trace-index.json), [temporal operand comparison](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/temporal-operand-proof.json).

### E — Gemini 3.5 interpretation

The captured system and user messages explicitly distinguish source facts, prior context, simulated origin, saved/staged/current artifacts and uncertain physical causation. Errors persist in completed output:

- SS-BROAD correctly locates modeled stopping interfaces but promotes modeled operational failure to an established physical/operational cause.
- SS-TIME correctly identifies two running changes and the observation bracket, but invents the value of running state at the staged file's 02:00 time.
- RI08 gives two contextual proposed checks, yet treats error counters/down state as confirming a physical rather than routing cause.
- Later browser advice makes persistent line-rate utilization sufficient to identify capacity-driven queuing.

These are not timeouts and are not caused by the reasoner receiving only empty records. Complete operands do not make the interpretation logically deterministic; typed provenance and dependency organization may still improve usability. The measured good/bad temporal pair shows that the existing representation can support a correct qualified answer, not that its presentation is optimal or the model is inherently incapable.

### F — Draft, adequacy and real supplementary investigation

With completeness enabled, model decision answer is still reviewed. post_draft combines original clauses, source coverage, typed identity/reference dependencies, declared claim compatibility and source guidance. The server may propose a registered read even when Gemini does not volunteer need_more_evidence.

Actual CVR-01 and SS-BROAD traces prove:

1. Initial authorized readers return a configuration containing a referenced event/review ID.
2. The first reasoning call completes.
3. Server post-draft checks identify the unresolved source-owned reference.
4. A second authorized syslog query runs with that reference.
5. The returned event and receipt appear in the next reasoning packet.
6. A revised explanation incorporates the recorded purpose.

This is a working adaptive acquisition capability. It does not prove higher whole-task accuracy: the recorded matched claim-release cohort remains 1/2 adequate before and after, and the broad revised answer still overclaims physical cause.

Additional reads are bounded and validated using existing reader schemas, original source restrictions, canonical ownership, scope, time, duplicate-query coverage and remaining budgets. Advisory requests do not schedule them. Correction is now reserved for actual contradictions or rejected executable proposals; auxiliary/validator uncertainty alone does not consume a correction loop.

**Gaps:** family coverage and clause self-assessment do not establish semantic sufficiency. A successfully queried family can contain the wrong event or no decisive observation. A root cause may remain uncheckable even after every family was read. Typed reference guidance cannot resolve a free-text opaque reference absent from the authorized source contracts. The new receipt mismatch can additionally misreport partial read success.

Code: [evaluation/review loop](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/engine.py:309), [query validation](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:292), [post_draft](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py:407), [guidance](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/evidence_harness.py:128).

### G — Verification, correction, composition and UI

| Mechanism | Actual responsibility | What it does not establish |
|---|---|---|
| Strict core JSON/schema | Mandatory decision, answer, source and executable-query structure | Technical truth or completed user outcomes. |
| Source/record receipts and verify_records | Actual authorized identity, ownership/hash/record integrity | All cited prose follows from the record. |
| Evidence classes/authority guidance | Source compatibility, modeled/recorded/physical distinctions | A universal ranking that resolves conflicting current/historical facts. |
| Claim compatibility | Deterministic declared operand/owner/time/branch checks; explicit unsupported/uncheckable/error categories | Full natural-language meaning, unstated assumptions or all sentences. |
| Core/auxiliary split | Invalid claim metadata becomes diagnostics; valid core can survive | Malformed whole JSON can be recovered safely. |
| Contradiction correction/release | Bounded correction or withholding of known contradicted assertions; valid prose otherwise retained | An unverified preview is an adequate engineering explanation. |
| Outcome assessments | Model proposals, clause/source coverage hints | Nonempty clauses prove semantic completion. |
| UI | Render stored answer Markdown and source disclosures | Another reasoning or factual validation step. |

Current verdicts distinguish SUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE, NOT_MECHANICALLY_CHECKABLE, MODEL_CONTRACT_ERROR and VALIDATOR_ERROR. Only definite contradiction belongs in the factual correction gate. A device-wide configuration without an interface identity is not by itself a wrong-owner contradiction.

A valid declared down status is not evidence for a physical root cause. In SS-BROAD that causal sentence is not covered by the valid declaration. The current release decision is QUALIFIED_UNVERIFIED, semantic_certified=false, with unchanged prose. It therefore misses the user's accuracy requirement while correctly avoiding a semantic-certification claim.

The approved role path preserves model prose before ordinary/local synthesis; the latest selected completed answers are literal substrings of their released answers. An optional older semantic mode can run the existing local candidate verifier or factual fallback, but this was not the cause of the inspected role-path failures. UI displays the stored prose, not a hidden transformed interpretation.

Code: [core/auxiliary parse](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:39), [typed claim operands](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py:217), [release](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py:378), [compose](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/engine.py:451), [preview authority](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:367), [gateway release metadata](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/gateway.py:438), [Floating display](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/frontend/components/SharedInventoryChat.tsx:121), [Studio display](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/frontend/components/ansible/AnsibleChatPanel.tsx:4607), [shared Markdown](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/frontend/components/AssistantMarkdown.tsx:52).

### Existing coverage at each boundary

This audit reran only the 43 focused offline cases described in Section 12. Other named suites were inspected as existing coverage, not newly executed or credited as current model-quality passes.

| Boundary | Relevant existing evidence/tests | Limit |
|---|---|---|
| A/B | [model role graph tests](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/tests/test_model_role_graph.py), [state/source-policy tests](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/tests/test_state_interface_scope.py) | Mocked planning proves contract behavior, not Gemini understanding. |
| C | [scope tests](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/tests/test_state_interface_scope.py), [source tests](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/tests/test_completeness_sources.py) | Disposable actual readers and original API/browser evidence; not physical data collection. |
| D | [harness source tests](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/tests/test_evidence_harness_sources.py), this audit's exact trace/operand comparisons | Operand preservation does not measure attention or causal reasoning. |
| E | Original saved model outputs and source-grounded grading | No deterministic suite certifies general model reasoning; no inference rerun here. |
| F | [investigation tests](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/tests/test_completeness_investigation.py), actual CVR-01/SS-BROAD supplementary reads | Acquisition and safe bounds are independently distinguishable from adequate final explanation. |
| G | [claim-release tests](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/tests/test_claim_release_repair.py), [JSON transport tests](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/tests/test_core_json_transport.py), stored browser responses | Mocked transport does not establish native provider schema compatibility; exact typed checks do not certify prose. |

## 4. Mandatory forensic cases

### Case 1 — Broad simulated network investigation

Trace: [SS-BROAD](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261029-state-scope-repair/matched-repaired/SS-BROAD.json). Floating, 66.63 seconds, nine actual reader calls, two reasoner packets.

**Request:** “Investigate the Harbor to Meadow UDP/5514 problem from the registered sources. Explain forward and return stopping points and interface owners, compare saved with running configuration, and explain the referenced review record. Separate modeled blockers from an established physical cause.”

**Expected:** bind each failed direction to the correct Meadow interface, compare source artifacts, explain the actual review purpose and keep modeled blocking distinct from an unestablished physical mechanism.

**Actual source facts delivered:**

- port-7031: Meadow/device 703, Ethernet2/1/interface 7031, prefix 10.71.2.2/30, admin up, oper down, 01:00Z, authored-synthetic-observer.
- model-interface-7031: distinct declared modeled observation with the same owner/state. It is not deduplicated into independent physical corroboration.
- model-flow-service-71: derived modeled forwarding. Harbor 198.18.71.1 -> Meadow 198.18.71.3, UDP/5514, default VRF; forward failure at Meadow 703/7031 ingress, return failure at the same owner's egress. The record's assumptions/derivation are limited; depends_on is empty.
- Saved/running configuration artifacts remain separately identified.
- review-rx-729: supplementary synthetic syslog says to review receive-power margins before selecting a replacement optic. It is a review purpose, not a completed repair.
- Development receipts identify simulated origin and development-scenario authority. Published access-port knowledge was also returned but was not the operational review record.

**Unsupported raw and released sentence:** “The modeled blockers (derived forwarding assessment failures) stem directly from the established physical/operational cause: Meadow interface Ethernet2/1 being operationally down.”

**First divergence:** the plan's knowledge selection is the earliest source-relevance error. It was later compensated by actual syslog retrieval. The first proven failure responsible for the physical overclaim is **completed reasoner interpretation**, followed by incomplete prose-level release coverage.

**Verification detail:** one auxiliary down-status claim uses direction ingress, which is invalid for the schema's forward/return enum. This is an actual contract ambiguity between flow direction and port direction; the repaired core/auxiliary split correctly diagnoses it without destroying the core. The configuration claim is about the command, not the physical conclusion. Zero detected contradictions cannot certify the undeclared causal statement.

**Confidence:** high for delivery, interpretation error and unchanged release. Medium that mixed views or missing dependency lineage contribute. Low that another hierarchy label alone would fix it: the model already saw explicit simulated-versus-physical boundaries. No physical measurements were omitted and then secretly assumed available.

### Case 2 — Spruce temporal binding

Traces: [failed SS-TIME](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261029-state-scope-repair/matched-repaired/SS-TIME.json), [qualified accurate SQ-TEMP](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261029-state-scope-repair/quality-control/SQ-TEMP.json). Same original request; Floating and Studio respectively.

The user asks for actual running changes, staged differences, the strongest operational transition bracket and whether the MTU event establishes its time/cause.

| Source record | What it actually establishes |
|---|---|
| spruce-running-a, 01:00 | Running description WAN-A, MTU 1500, no shutdown. |
| spruce-staged-b, 02:00 | Unapplied staged description STAGED-ONLY, MTU 9216, shutdown. It does not sample running state at 02:00. |
| spruce-running-c, 03:00 | Running description WAN-B, MTU 1500, no shutdown. |
| spruce-state-before, 03:50 | Operational up at that observation. |
| spruce-mtu-event, 04:20 | Recorded applied MTU 1500 -> 9000 event, not an exact operational transition/physical cause. |
| spruce-state-after, 04:50 | Operational down at that observation. |
| spruce-running-now, 05:00 | Running description WAN-B, MTU 9000, no shutdown. |
| spruce-counter, 05:00 | rx_discards 42, rx/tx errors 0, sent_packets 2000, lost_packets 0, for the same device/interface. This point sample does not establish the preceding down transition's physical mechanism. |

All eight retrieved records are retained in the operand proof. The observation pair brackets at least one up-to-down transition between observations, not uninterrupted state or a unique exact change.

**Failure:** SS-TIME says the staged file differed from “the running configuration at that time and subsequently” with WAN-B/MTU1500/9000. WAN-B is observed at 03:00, not established at staged time 02:00. Most of the answer—including the transition bracket—is otherwise qualified.

**Positive control:** SQ-TEMP states the three actual running samples separately, compares staged to running, and withholds exact transition time and physical cause.

**Independent offline check:** all eight record dictionaries, ID sets, artifact-comparison values, original instruction and system messages match. Full model inputs are not identical: planner text, receipts and surface differ. This is evidence against missing operands, not a randomized proof of model stochasticity or a causal effect of packet layout.

**First proven failure:** unsupported temporal binding in model prose. The claim checker did not certify or refute every implicit time binding. A clearer running-only timeline plus a separate staged artifact view is a reasonable experiment; adding another keyword guard is not justified.

### Case 3 — Contextual no-read advice

Trace: [RI08](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261029-reliable-investigation/enhanced-v1/RI-08.json). Studio, 8.18 seconds, zero readers.

**Request:** “Without reading anything new or taking action, suggest two read-only checks that would distinguish an interface issue from routing for the device we just reviewed. Explain what each check would resolve and what remains unknown.”

The planner chooses answer/explanation. The reasoner receives the previous owned goal “Show Transit current configuration,” the actual current-702 configuration, three named interfaces, prior source receipts and explicit advice/no-execution restrictions. It receives no new error counters or utilization measurements.

The answer proposes interface counters/state and routing/protocol checks, but says a down interface or rapidly rising errors “confirms an interface or layer-1/layer-2 physical link issue rather than a control-plane routing failure.” A down state/error pattern does not uniquely distinguish that cause or exclude routing interaction.

**Important distinction:** the model did not claim that it had actually retrieved CRC samples. The error is an unsupported conditional diagnostic rule, not fabricated retrieval. Generic route/protocol advice remains useful but does not cure that overclaim.

The later [saved browser acceptance](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261029-state-scope-repair/browser-acceptance.json) shows the same broader class: Studio makes zero reads and says persistent line-rate utilization “indicates link-capacity-driven queuing,” despite also acknowledging counter limitations. A busy link alone does not prove the particular queue/drop mechanism. Floating's corresponding browser advisory is a 503 noncompletion, not another bad reasoning answer.

**First failure:** technical interpretation of what a proposed observation would establish. Context and no-read enforcement work. Another source read would violate the task; the remedy cannot be automatic collection. Typed existing-source facts can constrain present claims but cannot mechanically validate all generic network advice.

### Case 4 — RI07 malformed whole-response JSON

Trace: [RI07](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261029-reliable-investigation/enhanced-v1/RI-07.json); [authorized native-schema probe](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261029-state-scope-repair/native-schema-authorized.json); [offline schema diagnostic](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/schema-offline-comparison.json).

**Observed:** HTTP 200, finishReason STOP, promptTokenCount 17,830, candidatesTokenCount 2,362, totalTokenCount 20,192. The provider response envelope parses. Its candidate text does not: an answer string contains unescaped quotes around down and planned_link_reference. Local json.loads reports line 3, column 411, position 436.

**Original request:** “Compare Harbor Ethernet0/1 documented adjacency, reported link state and interface observation. Compute the loss from the recorded interface sample, and distinguish that measured sample from modeled forwarding branch results. Explain the scope of any apparent disagreement.” Expected behavior includes the requested calculation and source-scope distinction in a valid core response. The released response instead reports interpretation unavailable and infers no conclusion. That safe limitation is not task completion.

The adapter joins returned text parts and strips surrounding whitespace. The same malformed candidate is already present in the saved provider body. No evidence shows application JSON damage. It did not hit the 8,192 output allowance, and no MAX_TOKENS finish is recorded.

**First failure:** generated whole-response contract at the model/provider-output boundary. The application correctly rejects it; no technical answer should be credited. Malformed claims are not the only problem: the answer string itself breaks core JSON.

**Native probe:** HTTP 400 INVALID_ARGUMENT before a usable generation, with no detailed rejected-field diagnostic. Do not infer that all native schema is unsupported or that a particular keyword caused this response.

**Offline simplification:** current full schema serializes to 3,894 bytes; a candidate wire-core schema is 2,101 bytes after applying the already implemented auxiliary split, dropping server-only extension metadata and unreachable SourceClaim definitions. Both schemas are valid locally. Representative quoted-valid, wrong-decision, wrong-source-type, invalid-query and bad-auxiliary core cases retain the same core acceptance decisions. The original malformed JSON fails both. This proves only a simpler locally valid candidate, not native provider acceptance or improved generation.

### Case 5 — Historical false rejection and correction loops

Sources: [claim-release repair report](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_CLAIM_VERIFICATION_RELEASE_REPAIR.md), [retained repaired offline replay](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261029-claim-release-repair/forensic-repaired-replay.json), [current focused checks](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/focused-contracts-v2.xml).

Historical defects included:
- CF-01 valid event-purpose paraphrase treated as contradiction after a real supplementary event read.
- CF-03 valid core rejected because auxiliary declarations were malformed.
- CF-04 unknown/unavailable source operands treated as contradiction.
- CF-05 device-wide configuration treated as the wrong interface.
- Peer/event wording or validator failures causing unwanted correction/withholding.

For example, CF-03 explicitly requested state-only explanation of installed routes versus failed TCP/9443 forwarding, exact failing owner/direction, return comparison and BGP-health limits, excluding configuration. CF-04 requested inventory/planned topology only, exact same-spelled port ownership/prefix/VRF and operational limits. CF-05 requested actual Transit running-history versus staged-file comparison, applied-event timing and no staged-as-running inference. The repaired replay tests those actual saved cores against their original source scopes; it is not a newly generated answer to a simpler task.

**Current behavior verified:** paraphrases become NOT_MECHANICALLY_CHECKABLE; missing operands become INSUFFICIENT_EVIDENCE; validator exceptions become VALIDATOR_ERROR; valid cores survive bad auxiliaries without coercion; definite wrong-owner/value/branch assertions still contradict. A failed revision does not erase a valid earlier core merely because uncertainty remains. Carry-forward checks prevent dropping a declaration from hiding an unchanged known false assertion.

The historical replay retains CF-01's revised prose and purpose with a qualification, not semantic certification. CF-03 retains its valid core. Truly malformed whole cores such as CF-07 still reject. Current positive/negative tests also exercise safe sentence withholding versus retaining unrelated supported prose.

**Conclusion:** those earlier false-rejection mechanisms are already corrected. Do not reinstate broad “uncertain means false” enforcement to solve the later prose errors. The new two-case matched live report remains 1/2 versus 1/2 adequate; fixing false suppression did not establish improved causal reasoning.

### Case 6 — Original successful model-neutral integrations

Sources: [MN-01 Floating](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261026-model-neutral/functional-v3/MN-01.json), [MN-02 Studio](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261026-model-neutral/functional-v3/MN-02.json), [MN-03 comparison](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261026-model-neutral/functional-v3/MN-03.json).

**MN-01/02 request:** investigate R1-to-R2 communication from recorded interface state and current configuration. The actual plan asks for state/configuration, not every source family. network.state supplies exact R1 port 9112/GigabitEthernet0/1 admin-down/oper-down, the peer up, and a failed synthetic direct-link ICMP result with interface_ids/link_ids. network.configuration supplies R1 shutdown and R2 no shutdown. The reasoner explains the disabled local link within explicitly synthetic mode. Both raw answers survive final release. The observation does not prove a physical cable fault.

**MN-03 request:** compare current and saved R1 CLI, inspect syslog and explain unknowns. Actual configuration has current shutdown versus saved no shutdown. Syslog explicitly returns source_available false. The model explains the textual change, says no operational logs were retrieved, and withholds the administrative reason/event history. Its correct explanation survives composition.

**Concrete differences from later failures:**
- Two selected readers rather than seven/eight initial families; required evidence directly matches requested outcomes.
- 5.9–9.0K-character packets rather than 32–61K; original core schema about 1.1K characters rather than 3.5K.
- No need to resolve an inspection-reference dependency, interleaved staged/running timeline, two distinct direction axes or a generic hypothetical diagnostic rule.
- Source limitations are explicit values, not facts inferred from absence.
- Early successful templates still use the same fundamental role/registry/graph integration.

These are useful positive controls showing the architecture can preserve good prose and source limitations. They are not a matched experiment proving that fewer readers, a smaller schema or older code caused better accuracy. Scores are not compared across unrelated cohorts.

## 5. Already fixed versus still open

| Finding | Current status | Evidence / action |
|---|---|---|
| Interface 7031 lost across state adapter/reader | FIXED, retained | Current scoped-reader tests and prior actual browser/API proofs. |
| State-only plan rejected due inferred inventory | FIXED, retained | Current original-policy regressions; no source prohibition weakened. |
| Whole-device configuration falsely bound to another port | FIXED for inspected mechanism | Device-wide missing port is uncheckable; explicit conflicting owner remains contradiction. |
| Invalid auxiliary declarations destroy valid core | FIXED | Current core/auxiliary positive/negative tests. |
| Unchecked event/unknown peer/validator exception enters correction loop | FIXED for inspected mechanism | Distinct verdicts and repaired historical replay. |
| Server-driven post-draft reference acquisition absent | IMPLEMENTED AND DEMONSTRATED | Actual supplemental syslog read and revised packet; not a whole-task pass. |
| Model promoted simulated blocking to physical cause | OPEN | Completed bad prose despite source distinctions, unchanged final answer. |
| Model assigned running state to unobserved staged time | OPEN | Same source operands support a separate good answer. |
| Advisory diagnosis overstated from generic counters/utilization | OPEN | No reads/context correct; conditional technical reasoning wrong. |
| Whole JSON malformed | OPEN reliability issue | Strict rejection correct; native transport not established for actual full schema. |
| Coverage uses last same-reader receipt for every result | CURRENT DEFECT, reproduced offline | Success then failure reported twice as failure; no correction implemented. |
| General semantic task completion from outcome/claim metadata | NOT ESTABLISHED | Structural coverage does not prove fulfilled explanation. |
| Per-need entity/time/VRF query expressiveness | CONFIRMED LIMITATION; causal impact unisolated | Current schemas/merge behavior; defer broad changes absent a concrete failing read. |
| Broader causal quality / 120-second acceptance | NOT QUALIFIED | No fresh benchmark or ordinary-budget experiment in this audit. |

## 6. Model, framework, provider and evaluation limitations

### What exact calculations can establish

Existing authorized structured readers and deterministic calculations can establish identity/membership, prefix compatibility, matching route/next-hop facts, modeled branch/VRF/direction outcomes within declared assumptions, observed state values, literal configuration differences, timestamps and observation brackets. Correct declared operands can be checked against those records.

They do not establish that a simulated outcome occurred physically, identify an optic/cable cause from oper down, prove an applied MTU change caused an outage, infer uninterrupted state between samples, or validate every generic diagnostic recommendation. Independent incidents derived from the same observation do not constitute independent corroboration. Missing depends_on lineage must remain unknown.

### Model limitation supported, not overgeneralized

There are completed technical interpretation errors despite complete task-specific operands and explicit boundaries. RI08 is particularly useful: no retrieval expansion or missing current counter sample is needed to explain why the stated hypothetical conclusion is overstrong. The temporal positive control shows success is possible under existing instructions. Whether a clearer packet or different reasoning effort reliably improves success remains untested.

### Provider and contract limitations

RI07 is completed malformed candidate content. A 503, timeout or native-schema 400 produced no comparable technical reasoning result. They must remain separate denominators: attempted requests, completed outputs, valid cores and adequate answers.

At audit date Google's Generate Content thinking documentation lists minimal/low/medium/high support for Gemini 3.5 and 3.1 Flash-Lite. A future low-versus-medium comparison is technically supported; higher effort is not a demonstrated fix. Output allowance also covers thought tokens, so finish reasons and usage must be retained. [Official thinking controls](https://ai.google.dev/gemini-api/docs/generate-content/thinking?hl=en).

Current official structured-output documentation supports JSON Schema for these models and describes a subset of schema features. It does not turn schema-valid values into technical truth. Its REST examples now use responseFormat.text.schema; the API reference describes legacy schema fields. The application's saved probe used responseJsonSchema. This warrants a small explicit adapter compatibility test, not a claim that deprecation or any single field explains the historical 400. [Official structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output?hl=en), [Generate Content reference](https://ai.google.dev/api/generate-content).

### Evaluation limitations

- An unnecessary reader, successful source read, valid JSON and correct answer are different outcomes.
- The old parameter-loss reference 1/4 versus initial repaired 0/4 is not proof that scope preservation reduces reasoning quality.
- The temporal pair has identical operands, not identical full prompts.
- A provider failure has no reasoning score; a safe fallback has no model-written causal credit.
- Original MN demonstrations and later independent holdouts have different prompts, sources, settings and schemas. Their scores cannot isolate an architectural effect.
- This audit is implementation-assistant analysis with source-checkable evidence, not independent blinded grading.

## 7. Architectural complexity assessment

| Existing mechanism | Value and overlap | Recommendation |
|---|---|---|
| Original prompt + requested clauses + IntentPlan | Preserves authority and proposed task decomposition; repeated descriptions can drift | Retain original authority; simplify repeated serialization experimentally. Do not add another outcome planner. |
| Required/optional needs and completeness coverage | Useful distinction; model breadth and server breadth select different extra sources | Retain recorded selected_by attribution. Consolidate the execution view, not permission checks. |
| Original source policy at routing/execution/supplement boundaries | Repeated enforcement protects separate entry points; same helper is used | Retain defense at each seam. Do not remove it as mere duplication. |
| Legacy Approach A outcome tracking | Separate experimental authority risk; historical inadequate results | Keep OFF; no redesign in this audit. |
| Source-family coverage | Useful for unread/failed/truncated status, but cannot prove semantic sufficiency | Repair per-query identity later; retain success and failure separately. |
| Clause evidence ledger | Helps disclose missing sources; relation can be unresolved/unknown | Retain as diagnostics; consolidate duplicate coverage views. |
| Reader hints and server supplementation | Real capability beyond voluntary need_more; must respect no-read/source restrictions | Retain bounded source-owned dependency acquisition; do not expand to speculative live tests. |
| Raw records + record index + network map | Helps navigation and topology ownership; multiple copies raise context | Experiment with one canonical fact payload plus lightweight pointers, keeping every necessary operand. |
| Two source/evidence class vocabularies | One emphasizes origin/time; another operational/event/config kind; not a total authority ordering | Consolidate orthogonal axes in current envelope. Do not rank simulated configuration against physical syslog as if one axis settles relevance. |
| Artifact comparisons | Running-only pairs fix interleaved staged artifacts; cross-artifact diff useful | Retain identity/time limitations; present running timeline separately from staged/saved comparisons. |
| Outcome self-assessment + answer + remaining requirements | Can expose gaps; model can repeat an incomplete conclusion in all three | Retain as proposals; measure semantic completeness externally. Nonempty is not acceptance. |
| Auxiliary claims | Some typed contradictions reliably caught; requires restating prose/facts and semantic axes | Narrow to reliable operand assertions; independently diagnose the rest. Do not use as universal answer certification. |
| Claim matrix and correction | Useful for exact contradiction; historically overbroad bucket caused false suppression | Retain repaired verdict split; no return to strict uncertain=contradiction behavior. |
| Local legacy synthesis verifier vs approved-role preview | Different supported paths; old checks must not silently replace good role output | Preserve explicit mode/trace. Consolidate reporting; no evidence to delete ordinary local protection. |
| Several budget/coverage metadata views | Experimental profile can differ from legacy summary fields | One authoritative runtime receipt in reporting; retain backward-compatible fields labeled by profile. No proven causal role in the selected bad answers. |

A larger hierarchy alone is unlikely to cure the broad overclaim: explicit provenance and “not physical measurements” guidance already exist. A single linear authority rank is also wrong for questions comparing intent, saved config, applied events and current observations—each source is authoritative for a different proposition.

## 8. Proposed generalized corrections — design only

### P1 — Test reasoning configuration before expanding semantic constraints

**Mechanism:** completed wrong causal/time/advisory reasoning despite delivered operands. **Change:** none initially; use the existing role interface for a separately authorized frozen-packet experiment. Compare current low thinking with supported medium, same question, full evidence, schema, output allowance and deadline. An alternative registered capable model is a later explicit-authorized arm only; no automatic switch.

**Generalization:** isolates interpretation from routing across physical attribution, time binding, incomplete evidence and advice. It tests the suspected bottleneck rather than adding guards for each protocol.

**Counterexample:** more thinking can produce longer rationalizations, exhaust output/deadline or reduce availability. A simple factual positive control may get worse.

**Tests:** freeze eight source-grounded packets before inference, including two already-correct/safely-limited controls and unseen identity/time variants. Keep completed wrong answers, provider errors, JSON failures and partial answers separate. Grade full outcomes, ownership, scope and causation, not claim count.

**Cost/risk:** no production code initially; up to sixteen future cloud attempts for two arms, quota-reserved and sequential; no extra reader calls. Medium effort/latency may rise. No new source/data permissions. Record remaining request-wide deadline; do not silently use the 360-second experiment as 120-second acceptance.

**Rollback:** evaluation-only settings bound into consent; no runtime default change. Do not retain the alternative without independent quality evidence.

### P2 — Make the existing evidence packet clearer and smaller, preserving operands

**Mechanism:** multiple factual/authority/plan copies and a mixed staged/running/event timeline create unnecessary relationship-resolution work. Measured size is confirmed; accuracy impact is a hypothesis.

**Change existing components:** evidence_packet, evidence_harness.enrich and investigation_support views. Retain one canonical source-owned record payload; derived indexes reference it. Keep original instruction and original source policy once. Preserve meaningful origin, fact kind, owner, valid/event time, capture/retrieval time and dependency/assumption references as distinct axes. Present per-device/per-interface running samples as a timeline; present staged/saved artifacts separately. Preserve direction/branch endpoints exactly.

**Illustrative existing-packet shape, not a new service:**

    original_request
    original_constraints
    source_records[id] = unchanged authorized record + receipt reference
    views.relationships = references to actual endpoint/branch records
    views.timeline = running samples + observations + events, with artifact kind
    views.artifact_comparisons = explicit operand IDs, never invented continuity
    pending_dependencies = actual source references or unknown
    previous_draft_review = only changes needed for this next round

Unknown dependency/time fields remain unknown. Origin simulated does not prevent a supported conclusion within the scenario; it prevents presenting that conclusion as a physical measurement.

**Generalization:** reduces duplicate interpretation across vendors/protocols; stable operand references and time axes serve routing, configurations, incidents and multi-source questions.

**Counterexample:** aggressive pruning can remove a contradictory observation or device-wide routing context. A “summary” can silently replace authoritative CLI. Do not replace raw evidence with model summaries or slice typed flows into incomplete endpoints.

**Tests:** zero-loss comparison of required raw operands; conflicting/time-separated observations preserved; every view points to actual records; unrelated metadata reduction measured separately. A/B the same frozen packets with unchanged reasoner settings before applying to gateway. No expectation rewrite after inference.

**Cost/risk:** medium change within existing modules, likely lower context cost, no additional calls/readers, moderate regression risk around missing relationships. Authorization/receipt validation unchanged.

**Rollback:** isolated packet-format experiment bound into existing consent/trace; retain old serializer and raw packet hashes until independent acceptance. Not a new default or mandatory metadata layer.

### P3 — Simplify the provider wire schema while retaining strict application core

**Mechanism:** RI07 invalid quoted prose; current schema includes auxiliary structures whose validity is not core authority; actual native full-schema compatibility unknown.

**Change:** use model_roles.response_validation_schema as the single core projection, remove only unused auxiliary definitions/server extensions for the provider wire representation, and keep application core validation unchanged. Test the official model/transport representation with tiny/core/full-schema controls as a separate adapter capability check. Never silently downgrade/retry modes after 400.

Clarify in the existing SourceClaim schema that direction means flow direction, and port ingress/egress is a different source-owned field; do not coerce ingress into forward. This directly addresses the observed auxiliary ambiguity in SS-BROAD.

**Generalization:** separates useful optional diagnostics from required executable control; applies across models and all quoted CLI/prose.

**Counterexample:** dropping query/outcome constraints would admit executable garbage; accepting malformed whole JSON could alter meaning or tool requests. A smaller schema alone cannot repair erroneous causal prose.

**Tests:** retained strict bad-decision, unknown-source, malformed JSON and invalid-query controls; quoted CLI/embedded JSON, bad auxiliaries with valid core, non-STOP responses, native 400 with no hidden retry. Offline 3,894-to-2,101-byte candidate already preserves the tested core decisions, but live compatibility is NOT RUN.

**Cost/risk:** small adapter/schema-serialization change; lower schema context, no second reasoner or normal-call increase. A separately authorized compatibility probe costs a few calls. Moderate transport regression risk; no tool/source permission changes.

**Rollback:** explicit per-model schema_mode and consent fingerprint; retain validated_json/current parser. No regex/partial JSON salvage, no schema weakening and no production activation from local-schema tests.

### P4 — Repair coverage by actual result/query identity

**Mechanism:** last same-family receipt applied to every result; later failure erases earlier successful coverage metadata.

**Change:** preserve/join existing query identity and invocation receipt on each result, using actual tool execution identity rather than reader family alone. Summarize all per-query outcomes without replacing successes.

    for result in results:
        receipt = actual_receipt_for(result)
        query_status = status_from(result, receipt)
        retain query identity, result refs, truncation, source status
    family = aggregate(query_statuses, preserving partial success and failures)

This design uses existing ToolStep/query_identity/receipt structures; no new store or planner.

**Generalization:** any repeated reader family, narrowed supplement, new interval, or partial source failure.

**Counterexample:** joining only on tool+parameters can conflate two identical retries with different source revisions. Bind the actual invocation and revision; do not invent IDs for historical results.

**Tests:** success->failure, failure->success, two successes with different scopes, zero matches, source unavailable, truncation, repeated same query at a new revision, and old results without receipt identity. A limitation on one query must not erase available facts from another.

**Cost/risk:** small local change, zero extra reader/model calls, negligible latency/token cost. Low/moderate reporting/replanning regression risk. Permission checks unchanged.

**Rollback:** previous aggregation available in an isolated comparison; do not replace historical evidence/regrade. This is the clearest small implementation candidate, but its likely whole-task improvement is narrower than P1/P2.

### P5 — Keep exact checks; stop treating coverage as semantic certification

**Mechanism:** declared-operand checks cannot see an undeclared physical/time/advisory conclusion; broad old enforcement caused false rejections.

**Change:** retain strict core, actual citation identity, owner/VRF/direction/branch/value checks and repaired verdicts. Treat evidence classes/matrix primarily as reasoning guidance and diagnostic metadata, with blocking reserved for definite typed contradictions. Keep model interpretation, factual projection and fallback disposition separate at final release. Do not label an answer “verified” because some claims pass.

For the existing output contract, assess whether a small conclusion-to-operand association improves visibility in an evaluation; reuse existing claims/outcome assessments rather than adding another mandatory schema or second model verifier. This association cannot certify prose and should not become a production blocking gate without evidence.

**Generalization:** preserves good explanations while preventing exact contradictory facts from inheriting source success; avoids one validator per technology.

**Counterexample:** letting uncheckable interpretations through with a disclaimer still releases wrong advice. Conversely, withholding every uncertain causal explanation would reject valid within-scenario diagnoses and useful qualified advice. This tradeoff cannot be solved by renaming a release status.

**Tests:** supported scenario diagnosis retained, physical-cause overclaim not certified, unknown event paraphrase qualified, exact wrong branch/owner rejected, undeclared conclusion tracked as uncertified, prior-known false assertion cannot disappear by dropping a declaration. Full-answer human/source-oracle review remains necessary.

**Cost/risk:** retain current checks now; small reporting consolidation possible later, no added inference, moderate UX/release-policy risk. No new authority. Production behavior change should wait for P1/P2 results.

**Rollback:** report-only evaluation of any additional association; existing repaired release policy remains the baseline. No universal semantic-verification claim.

### P6 — Defer broader planning/query redesign until a concrete dependency loss is isolated

**Mechanism:** same-family merging and no per-need entity/time/VRF operand can over-broaden evidence, but this did not explain the selected complete-evidence errors.

**Possible existing-component change:** when independently reproduced, carry distinct scoped ToolStep parameters through the current IntentPlan/AgentState rather than merging incompatible needs. Use the original request as authority and existing registered schemas. Never add a competing planner or reactivate Approach A as an assumed solution.

**Counterexample:** splitting compatible reads creates duplicates, raises latency and makes quota/coverage worse; invented target scopes may exclude legitimate shared context.

**Tests:** different devices/time ranges in one source family; compatible same-scope merge retained; forbidden source remains forbidden; scope cannot be widened by an optional model need.

**Cost/risk:** moderate cross-cutting schema/control risk; may increase reader calls. Defer until actual necessity is established; isolated flag/consent version if later authorized.

## 9. Risk and tradeoff assessment

| Choice | Benefit | Risk / evidence limit |
|---|---|---|
| Retain model-driven prose | Can answer comparisons and advise naturally; original MN controls demonstrate value | Completed semantic errors remain; raw prose is not certified by valid JSON. |
| Add deterministic checks only for exact operands | Reliable negative checks, authorization and identity without technology-wide prose parsing | Cannot certify generic physical causation or every task outcome. |
| Expand class/claim hierarchy | May make distinctions inspectable | More duplicated schema/output; clear labels already failed to prevent overclaim. No established adequacy gain. |
| Canonical evidence layout | May reduce relationship ambiguity and context cost | Pruning can hide contradiction; requires same-evidence A/B, not intuition. |
| More supplementary reads | Can resolve a real source-owned reference after an answer draft | Not useful for unavailable physical data or no-read advice; can add irrelevant evidence and another bad inference. |
| Higher reasoning effort | Supported API experiment, no architecture expansion | Accuracy benefit unknown; higher thought/output use and deadline risk. |
| Smaller native wire contract | May reduce malformed output with strict core retained | Full provider compatibility unknown; generic 400 must not trigger unsafe fallback parsing. |
| Stronger release withholding | Protects known contradictory typed facts | Cannot reliably catch undeclared prose without false suppression; old broad gate already demonstrated that failure. |

Quota remains the shared 15 RPM / conservative 150K input TPM / 500 RPD ledger; this audit adds no model reservations. Future experiments must reserve headroom, record actual usage and separate complete-task latency from model time. No automatic physical collection or private-data transmission is proposed.

## 10. Ranked implementation sequence — requires new authorization

Ranked by likely contribution to accurate, complete tasks, not number of passing tests:

| Rank | Candidate | Evidence strength | Expected correctness / completeness effect | Effort/risk | Recommendation |
|---|---|---|---|---|---|
| 1 | P1 frozen-packet reasoning configuration comparison | Strong completed-error evidence; no configuration effect yet | Directly tests the interpretation bottleneck without retrieval confounding | Low implementation; bounded cloud/latency cost | EXPERIMENT FIRST |
| 2 | P2 canonical evidence organization | Strong measured duplication and timeline complexity; causal benefit hypothetical | Could improve association and reduce noise while retaining all outcomes | Medium, operand-loss risk | EXPERIMENT FIRST |
| 3 | P3 wire-core/native compatibility and direction-axis clarity | Actual malformed candidate + generic native 400 + invalid ingress declaration | Improves reliable completion; no guaranteed semantic uplift | Small/moderate provider risk | BOUNDED EXPERIMENT, then integrate if proven |
| 4 | P4 receipt/query coverage identity | Confirmed current deterministic counterexample | Improves partial coverage/recovery; not a cure for completed wrong reasoning | Small, low call overhead | IMPLEMENT in next authorized small repair |
| 5 | P5 narrowed typed checks and honest release authority | Historical false rejection fixed; current unverified bad prose remains | Preserves correct answers and exact safety; no universal completion assurance | Retain now; reporting change small | RETAIN; test any extra association report-only |
| 6 | P6 per-need scope changes | Confirmed schema limitation; selected causal impact absent | Could improve genuinely distinct same-reader tasks | Moderate cross-cutting risk | DEFER pending a concrete reproduction |

**Small independent milestones:**

1. Freeze independent source-grounded expectations and contract controls. Implement only P4 if authorized; close its reporting gate without claiming a reasoning gate.
2. Evaluate P1 on unchanged packets and P3 on explicit small/core/full transport controls. Keep settings/transport experiments separate.
3. Evaluate P2 only against the unchanged P1 baseline setting using identical facts. Promote neither packet nor thinking configuration unless adequacy improves without critical scope/identity errors.
4. Integrate only the winning bounded change into the existing graph and run the small gateway/browser program below. Keep all default-off experiments and original Phase G gates unchanged until their own criteria pass.

Do not add Approach B, another planner, another verifier, generic network CLI parser, unlimited investigation, automated live testing or new RAG. Do not repeatedly tune exposed prompts. Do not activate higher effort/native transport solely from offline schema validity.

## 11. Four-layer acceptance program

This is a future program; no new live evaluation was performed in this audit.

### Layer 1 — Deterministic contracts

Use disposable databases and unchanged source contracts:

- Correct device/interface membership, source-only restrictions, unknown/wrong-owner scope and live-read denial.
- Preserve distinct authored/model/conflicting/time-separated observations; deduplicate only exact repeats.
- Per-query receipt coverage controls from P4, with both success orders and partial/unavailable/truncated cases.
- Running-only comparisons plus staged artifact identity, UTC-equivalent timestamps, separate event/capture/retrieval time.
- Strict whole JSON and core schema; optional auxiliary failures; exact source receipt references.
- Known wrong operand/owner/branch contradicts; unsupported event paraphrase and validator exceptions do not.
- No inference, authorization mutation or quota reservation in these contract tests.

Pass means all required positive/negative contracts hold. It earns no reasoning score.

### Layer 2 — Frozen-evidence reasoning

Freeze eight independent packets and complete-answer criteria before inference:

1. Supported simulated interface blockade with an explicitly unknown physical mechanism.
2. Identical route presence but a failed forward branch and a delivered return branch.
3. Interleaved running/staged/history with an applied event inside an observation bracket.
4. Zero-read advice with current owned configuration but no fresh counters.
5. Available configuration with unavailable syslog and independently requested explanation/limitations.
6. Published operation requirements versus saved CLI, without protocol/compatibility proof.
7. Healthy scoped multi-hop positive control.
8. Conflicting observations/insufficient evidence where useful uncertainty is the complete answer.

These are conditions for a new registry, not renamed exposed prompts. Use different relationships/ground truths and source-oracle checks. Independently check device/port/direction/time expectations before freezing; if no external grader is available, label implementation-assistant grading honestly.

Compare configurations one factor at a time. P1 two arms means sixteen attempts, sequential and consented; P2 is a later separately approved comparison, not a hidden extra arm. Provider noncompletion stays a provider outcome. Report accuracy among all attempts and among completed valid model outputs; never discard failures from the main denominator.

Require no critical wrong ownership/direction/physical/temporal conclusions, preserve positive controls, and show a meaningful paired adequacy improvement before integration. This small diagnostic does not replace the original formal G5/G6 cohort or thresholds.

### Layer 3 — Full authenticated gateway

After a Layer 2 candidate passes, run a small balanced set through both actual surfaces using disposable authorized synthetic contexts:

- Restricted state/interface read.
- Broad investigation with a real source-owned event dependency.
- Same-family partial success/failed supplemental query.
- Advisory no-read with owned context.
- Running versus staged temporal comparison.
- Ordinary topic switch after investigation.

Capture original request, plan and source policy, approved/executed query identity, actual results, exact reasoner messages/settings, raw output, supplementary reasons, compatibility/release disposition and final answer. Verify source record equality before attributing a quality difference to the model.

A real second read is not success unless the added evidence improves the requested result. A correct raw answer replaced or distorted at release is a composition defect. False verifier rejection is distinct from model failure.

### Layer 4 — Actual browser behavior

Fresh capability check, then existing authenticated controls on both Floating and Studio; no API substitution for browser proof. Verify exact consent, relevant source disclosure, context/topic switch, source exclusions, no-read behavior, raw prose preservation, Copy and protected editor non-modification. Do not reset profiles or buffers. Tool initialization, permissions and application connectivity must be reported separately if blocked.

### Measurements and stopping rules

For every layer/case separately record: workflow correctness, actual source coverage, necessary model-visible operands, device/interface/VRF/direction attribution, temporal/origin correctness, causal reasoning, original-outcome completeness, useful final explanation, unsupported claims, false verifier conflicts, schema failure, provider noncompletion, safe fallback, supplementation benefit, reader/cloud counts, tokens and request-wide latency.

Do not aggregate deterministic/fallback passes into model-written adequate answers. Preserve original failures beside diagnostic reruns. A new broad qualification is justified only after small improvements replicate; the existing G5 threshold remains at least 26/30 adequate with its independent causal/release-safety conditions, not a lower pilot threshold.

## 12. Direct answers, preservation and handover

### Q1–Q10

| Question | Evidence-backed answer |
|---|---|
| Q1: Principal remaining cause? | Multiple: completed interpretation errors, incomplete prose verification, complex packet/output contracts and provider noncompletion. The accepted scope/policy defects are fixed; the current receipt-ledger bug affects partial coverage. No defensible single percentage attribution is available. |
| Q2: How know evidence reached Gemini? | Captured authorized results equal non-inventory reader payloads in exact captured model messages; source/origin/owner/time fields are visible. All eight Spruce records and comparisons match across good/bad outcomes; SS-BROAD includes both explicit simulated labels and the actual event. This proves relevant operand delivery, not universal absence of ambiguity. |
| Q3: Helpful packet or too much context? | Both. Relationship/timeline/source structures help inspection, but 32–61K packets repeat plans/records/indexes/ledgers/views. Noise/attention impact is plausible and unmeasured; test canonical organization with identical raw facts. |
| Q4: Does the hierarchy improve reasoning? | No isolated improvement has been demonstrated. It supplies context and typed compatibility diagnostics. Source kind, origin and time need orthogonal treatment; another total rank would not establish physical causation. |
| Q5: Strict matrix or smaller checks? | Retain strict exact operand/identity contradictions. Keep unsupported/uncheckable/error verdicts non-contradictory. Use broad class compatibility as guidance/diagnostics, not universal prose certification. Current repaired behavior is the safer baseline. |
| Q6: Does post-draft investigation improve task accuracy? | It demonstrably retrieves and delivers a missing referenced event after an answer draft. The inspected cohorts do not demonstrate whole-task accuracy uplift; later prose can remain wrong. Preserve the acquisition capability without claiming quality acceptance. |
| Q7: What fits existing contracts/graph? | Receipt-query joins, packet deduplication/orthogonal source axes, timeline operand views, smaller provider wire schema, direction-axis clarity and trace consolidation. None requires another planner, verifier, store or graph framework. |
| Q8: What warrants a reasoning-model experiment? | Unsupported physical attribution, temporal value-at-time inference and generic advisory discrimination despite complete relevant inputs. More source reads cannot solve no-read advice or supply unavailable physical measurements. Test supported thinking settings before adding more constraints. |
| Q9: Is JSON too complex? | Complexity is measured; causality is not. RI07's core answer string was malformed. A locally valid 2,101-byte core-wire candidate versus 3,894 bytes is available; native-schema compatibility and accuracy remain untested. Keep strict whole JSON/core validation. |
| Q10: Smallest useful generalized direction? | Retain current role/graph/permissions and fixed boundaries; test reasoning effort and clearer canonical evidence separately; repair receipt identity; simplify provider wire representation only after explicit controls; retain narrow exact checks and honest unverified/fallback labels. |

### Files and evidence inspected

Authoritative reports reviewed: [model-neutral architecture](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_MODEL_NEUTRAL_MULTI_MODEL_ARCHITECTURE.md), [model-neutral continuation](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_MODEL_NEUTRAL_CONTINUATION.md), [independent G4–G6 qualification](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_MULTI_MODEL_G4_G6_QUALIFICATION.md), [intelligence improvement](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_MULTI_MODEL_INTELLIGENCE_IMPROVEMENT.md), [evidence harness](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_EVIDENCE_AWARE_HARNESS_ENGINEERING.md), [completeness investigation](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_COMPLETENESS_FIRST_EVIDENCE_INVESTIGATION.md), [claim-release repair](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_CLAIM_VERIFICATION_RELEASE_REPAIR.md), [scope/quality repair](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_STATE_SCOPE_AND_QUALITY_REPAIR.md), and [latest continuation](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_CONTINUATION_CHECKPOINT.md). The mandatory files and selected original traces were present.

Code reviewed includes the gateway/routing/reference paths, query/reader/adapters, scenario filtering, model roles/provider/authorization/quota, planning/state/model/graph, request contract, harness, investigation support, role reasoning, factual verification and existing response renderers. Module references above identify the actual relevant seams; no sibling V9 source or immutable knowledge was edited.

### Diagnostics performed

- [inspect_traces.py](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/inspect_traces.py) -> [trace-index.json](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/trace-index.json): saved model messages, exact source-delivery comparisons, schemas, outcomes/claims, released prose inclusion and graph traces.
- [offline_diagnostics.py](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/offline_diagnostics.py): temporal operand equality, whole-JSON/provider-envelope inspection, offline core-schema simplification and receipt-coverage counterexample. No inference or original-output modification.
- **43 focused tests PASS** in [focused-contracts-v2.xml](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/focused-contracts-v2.xml): 19 interface/source-policy cases, 15 mocked JSON-transport cases and nine pure claim-release cases. Counts are not added to historical overlapping suites.
- The retained [first diagnostic run](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/focused-contracts.log) had 23 harness failures and 20 passes because the audit's network-denial guard also blocked Windows asyncio's internal socketpair. The second run allows only creation of that internal self-pipe; application network connects remain denied, HTTP responses are mocked, and all 43 pass. No application code was changed to make this pass.
- Official public API documentation was read to check proposed thinking/schema compatibility. No authenticated model/API inference was performed.

### Protected state and limits

The [before manifest](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/preservation-before.json) records HEAD/index, 41 ordinary SQLite table hashes, 607 source/test/frontend/registry/historical-file hashes, 1,923 knowledge-storage files, credential/root environment hashes and quota ledger hash. The [final preservation receipt](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261101-architecture-root-cause-audit/preservation-after.json) records the comparison and any explicitly documented limit. No key values are included.

No browser was opened or controlled in this audit, so there is no new browser acceptance or new protected-buffer hash claim. Avoiding application/browser writes preserves existing buffers without pretending to have reverified their contents. Historical browser artifacts were read, not rerun.

Final preservation is **PASS**: unchanged HEAD/index, all 41 ordinary tables, all 607 protected files, all 1,923 knowledge files, the nine selected original traces, both environment files and quota ledger. Active release 7a14a351e52b49aeb87f65d1192f0937 still contains 341 intact artifacts. The credential remains ignored and no credential exposure was found in the new report/audit artifacts.

Only this requested report and new ignored audit/diagnostic artifacts are added. No source, tests, settings, scenarios, historical scores, role assignments, consent, quota, ordinary tables or releases were changed; no services were started; no commits/staging/publication/deployment/device actions occurred. Accepted repairs remain intact.

**Continuation decision:** audit complete; implementation not authorized by this brief. Keep all experimental defaults unchanged. The next authorization should select the small P4 contract repair and/or the P1 frozen-evidence experiment, rather than another broad Phase G optimization cycle. Do not implement the proposed design until explicitly authorized.

