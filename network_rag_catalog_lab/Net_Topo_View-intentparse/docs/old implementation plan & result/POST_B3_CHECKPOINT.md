# Post-B3 review checkpoint — 2026-10-17

This is a source checkpoint, not a commit or a new architecture milestone. The
starting index was empty. Existing work was retained; the curated index contains
the Phase B work below and its stabilization fixes (52 staged files). Review with `git diff --cached`.
No reset, automatic commit, publication or device operation was performed.

## Ownership of the accumulated changes

Phase A's shared gateway, V9 adapters, OCR/extraction, Monaco Jinja registration,
reference library and review UI already exist in baseline `90ea74d` and earlier
commits. They are retained. The following accumulated changes extend that baseline:

| Area | Source in the checkpoint | Purpose |
| --- | --- | --- |
| B1 foundation | `backend/llm/orchestration/{__init__,adapters,engine,model,state,verification}.py` | Shared typed LangGraph execution, existing-registry LangChain adapters, local model integration, bounded reads and factual release checks. Files also contain B2/B3 extensions. |
| B2 persistence and coordination | `backend/llm/orchestration/{investigation,memory}.py`, `backend/llm/gateway_references.py` | Owner/surface-bound SQLite checkpointing, reference resolution, existing network/document/published-knowledge coordination. |
| B3 engineering coordination | `backend/llm/orchestration/studio.py`, `backend/llm/{gateway,gateway_api,gateway_diagnostics,gateway_documents,gateway_routing,gateway_semantics,gateway_services}.py` | Actual-buffer context, guarded proposals, V9 dispatch, routing, diagnostics, compatibility retention of unresolved tasks and existing API contracts. |
| Readers and evidence | `backend/llm/{gateway_findings,gateway_knowledge,gateway_network,gateway_store,tools}.py`, `backend/local_providers/{knowledge_worker,v9_worker}.py` | Attribute-aware readers, complete-row context projection, provenance, published contract retrieval, authorization and strict partial review. No second RAG or sibling V9 edit. |
| Existing frontend integration | `frontend/components/SharedInventoryChat.tsx`, `frontend/components/ansible/{AnsibleChatPanel,NativeGenerationReview}.tsx`, `frontend/src/{App.tsx,services/api.ts}`, `frontend/views/AnsibleStudioView.tsx` | Restored attachments/launcher/layout, useful API errors, shared workflows, reviewed selections, explicit draft opening. |
| Stabilization | `frontend/components/ansible/{AnsibleFileTree.tsx,workspaceCreation.ts}`, `backend/llm/orchestration/editor_facts.py`; changes in `studio.py`, `gateway.py`, `gateway_documents.py`, `NativeGenerationReview.tsx` | Listed-folder creation resolution and expansion; literal CLI claim guard; exact whole-address patch anchors; accurate native validation scope and Cisco CIDR-route warning. |
| Dependencies/configuration | `.env.example`, `backend/requirements-{local.txt,local.lock.txt,agent-b1.lock.txt}` | Existing B1 pins and `langgraph_b3` example flag. B2/B3/stabilization add no dependencies. |
| Behavioral regressions | `backend/tests/test_{b1_agent,b2_agent,b3_studio,ai_intelligence,ai_review_network,shared_ai,studio_multi_review,editor_facts}.py`, `frontend/tests/workspaceCreation.test.cjs` | Exact records, authorization, checkpoint recovery, routing, documents, review, patch and file-tree regressions. |
| Local-model evaluations | `backend/scripts/evaluate_{b1_agent,b2_agent,b3_studio,shared_ai_behavior}.py` | Existing actual-model/application-route evaluation harnesses. Generated reports/databases remain excluded. |
| Handover | `docs/UI_RESTORATION_HANDOVER.md`, this file | Preserved chronology, actual outcomes, boundaries and next gates. |

The exact staged path list is available through `git diff --cached --name-only`;
the final local manifest and diff statistics are retained under ignored
`tmp/stabilization-20261017/`. The source package includes the previously untracked
orchestration package and evaluators, rather than leaving required imports out.

## Schema and dependency review

`gateway_store.ensure_schema` is the existing backup-before-migration mechanism.
Its B2 version `shared-ai-4-b2` adds `ai_agent_investigations` and
`ai_agent_checkpoints`. The earlier shared tables, assistant-kind column,
attachments/original bytes, evidence, handoff and inventory metadata remain in
that idempotent migration path. No new stabilization schema migration or SQL
file is needed. No tables were dropped and no test knowledge was migrated.
Checkpoint authority remains server-owned and separate from restored state.

Installed and lock-file versions verified now: LangGraph 1.2.15,
langgraph-checkpoint 4.3.0, langchain-core 1.6.11, langchain-ollama 1.1.0,
ollama 0.6.3 and websockets 16.1.1. B1's websockets pin replaced 17.2 for SDK
compatibility. No dependency installation, model download or lock regeneration
was performed in stabilization.

## Intentionally excluded from the index

- Tracked `.env`: existing local configuration, including its B3 engine selection;
  retained on disk. The safe engine-setting example is staged in `.env.example`.
- Tracked `backend/db/m0_2_m0_3_browser_smoke.db`: existing user/conversation/
  evidence/checkpoint data, retained locally and unstaged. Do not add it to a source commit.
- `tmp/`, including previous Phase A–B3 evidence, the one acceptance SQLite backup,
  temporary launcher, screenshots, audit reports and database fingerprints.
- Knowledge workspace/release artifacts, database backups/journals, virtual
  environments, node_modules, compiler caches and generated distributions.

These exclusions do not delete or discard anything. The two tracked local-state
files remain visibly dirty after source staging. The sibling V9 repository is
read-only; an existing unreadable sibling temporary directory may cause a Git
status warning, and was not altered.

## Engineering quality gate

Successful V9 contract validation/rendering does not establish valid device CLI,
playbook support, installed state or reachability. The browser exposed the active
Cisco `configure_static_route` template emitting `ip route 203.0.113.0/24 ...`.
IOS-XE documents separate prefix and mask arguments; the UI now explicitly warns
on this observed output shape. The immutable release was not patched or republished.
See [Cisco's IOS-XE basic routing reference](https://spg.xgslb-v3.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-routing/b-ip-routing/m_iri-iprouting.html).

An alternative `add_default_route` selection correctly remained blocked by an
unsupported/unreviewed resource-policy profile; fixture facts were not fabricated
to bypass it. BGP rendering, corrected remote AS, multi-task review and explicit
unsaved output opening succeeded. This is not a claim of universal native CLI or
Ansible support. All 64 previously unverified reference translations remain
unpublished.

Phase C requires an explicit user-approved scope, a separately reviewed correction
and publication of defective native bindings, verified output variants and
containment before enabling playbook validation, and realistic behavioral evidence
for any broader semantic claims. Live collectors, deployment, autonomous device
actions and broad editing remain outside this checkpoint. Phase C has not started.
