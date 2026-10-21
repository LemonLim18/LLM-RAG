# Assistant UI restoration and multi-operation review

Updated 2026-10-16. This supplements, and does not replace, the detailed A0–A5 plan and earlier handovers.

## Standard local application

Run `./run_local.ps1` from the repository root. It uses the existing backend virtual environment and Node/Vite installation, starts frontend **5173** and backend **8000**, refuses occupied or leftover legacy development ports, and stops its owned server processes together. Vite uses `strictPort`; it will not silently move to another port. No dependencies or models are installed by this launcher.

The ordinary `.env` selects the ordinary SQLite database `backend/db/m0_2_m0_3_browser_smoke.db` and ordinary published knowledge. Inherited acceptance-workspace overrides are removed by the launcher. The local Ollama endpoint remains `127.0.0.1:11434`; the model service must be running. Refresh the assistant/model list after starting it.

At most one temporary acceptance application is allowed. Reuse the existing `tmp/shared-ai-9bn22lf5` explicitly with `backend/scripts/serve_ai_lab.py --workspace tmp/shared-ai-9bn22lf5`; its fixed backend is 8001 and its frontend is 5174. No implicit creation of more workspaces. Stop this pair after testing. Its code is the same checkout as the standard app; its SQLite, fixtures and knowledge are never merged into ordinary data. The old 5175/5176/8002 instructions in historical handovers are superseded.

## Restored interaction

Reference: `generation process.pdf`, Figures 77–81, and the original ZIP's `PlaybookStudioOverlay.tsx`, `AnsibleChatPanel.tsx` and `FloatingInventoryOverlay.tsx`. Read-only reference extracts/renders are under `tmp/prototype-reference`.

- Floating assistant: draggable launcher and panel, one conversation surface, welcome prompts, separate saved history, expandable network context, model refresh, send/cancel and source disclosures. Inventory browsing remains usable without Ollama.
- Both assistants: shared Markdown renderer with paragraphs, nested lists, horizontally scrollable tables, language-labelled code blocks and copy controls. Raw HTML is not rendered. New Studio evidence is collapsed separately from prose.
- Studio: interpretation disclosure, operation/target selectors, schema status table, editable parameter controls, published-template inspection, explicit confirmation, side-by-side template/output, then explicit opening of unsaved documents. No yellow full-width playbook warning. Missing variants are shown with a native-output choice.
- Corrections retain the other operations, use revision checks, and update the stored review snapshot for reopening. Controls are disabled during validation to avoid dropping concurrent edits. Accept opens buffers; Save remains separate.

## Multi-operation behavior

Shared Studio opts into the existing V9 multi-task pipeline; legacy endpoints retain their contract. V9 continues to resolve operations, schemas, targets, compatibility, task conflicts and published templates. Requests are bounded to 24 operation/device bindings. Every task must resolve before any output is returned; no unsupported or incomplete task is silently omitted.

Native output returns one unsaved document per operation/device binding. Genuine playbook output renders separately reviewed variants, preserves host scopes and order, rejects conflicting dependency pins, and validates the combined YAML through the existing contained validator. The ordinary release has **no published playbook variants**, and a verified contained Ansible worker is still absent. Consequently **verified** combined playbook generation is not enabled in this environment; composition behavior is unit-tested with a mocked validator and is not reported as real Ansible validation. No direct LLM or deprecated Huawei fallback was introduced.

Ordinary R1/R2 remain recorded as Cisco IOS 16.2.3 / 12.12.11. These do not match the verified IOS-XE binding. The review correctly reports compatibility unavailable; it does not relabel the devices or invent templates.

## Verification and data integrity

- Focused regression: **25 tests and 3 subtests passed**, including multi-task preservation, exact revision checks, whole-request rejection, native availability, combined-output validation gates, shared authentication, isolation and variants. Only the inherited Starlette/httpx deprecation warning remains.
- Read-only real V9: Cisco IOS-XE 17.9, Juniper Junos 23.4 and Huawei VRP 8 generated three native VLAN configurations from ordinary published templates. A mixed create/delete/create request asked for the Juniper VLAN name, then returned all three outputs after a scoped correction without changing the other task parameters. These explicit prompts took V9's deterministic path (zero model calls); this does not establish general language-model planning accuracy. Evidence: `multi-v9-supported.json`, `multi-operation-live.json`, `multi-operation-corrected.json`.
- Ordinary browser: floating inventory response after local Ollama recovery; inventory fallback during outage; two-operation Studio review and compatibility rejection; desktop and narrow layout inspection. The installed 1.5B model can be verbose and make unsupported prose claims; presentation and prompting improve readability but do not prove factual accuracy. No live telemetry or connectivity capability is claimed.
- Two test import-path failures inserted a sample inventory device (IDs 3, then 4) and two empty test conversations into ordinary SQLite. These exact records were backed up, guarded by identity/dependency checks, and removed; cleanup audit records remain. API tests now explicitly pin application, inventory and authentication database paths and assert the actual inventory path before mutation. A logical before/after database digest confirmed the corrected regression run left ordinary data unchanged. R1/R2 and their facts were preserved. Cleanup backups remain under `tmp/prototype-reference`.
- Ordinary published release remains `0690966eb003499380e960a98d1e418f` (44 operations, 78 bindings). Isolated M4 knowledge remains separate. No publication, isolated knowledge promotion, dependency installation, sibling V9 modification or device execution.

## Remaining boundaries

Verified playbook variants and contained validation are still prerequisites for combined Ansible enablement. The original restoration scope did not include broad native editing or Floating expansion. The subsequently authorized expansion below supersedes those exclusions. Cross-file editing, ML and network-device execution remain excluded. Preserve separate conversation ownership, backend authorization, Monaco revision checks/undo and explicit saving.


## Expanded assistant and authoritative review completion

The user's subsequent request authorizes general guarded document editing, Floating read-only investigations, and editable vendor references. These additions use the same local gateway, provider, ownership checks and typed tool boundary. LangGraph was not added: the current bounded read-and-answer flow does not need durable agent orchestration.

### Authoritative review and drafts

- `gateway_review.py` exposes the active published operation schemas and compatible template choices. Category removal removes its tasks; adding or replacing an operation rebuilds its parameter controls. Structured arrays/objects have individual add/remove controls. Template switches within published support change the operation/schema when necessary. Removed fields cannot silently survive in the submitted parameters.
- Every correction submits the complete reviewed selection to the existing V9 adapter. V9 finalizes the explicit targets/operations/values without asking the model to reinterpret them. Old configurations and confirmations are discarded. Session, inventory, knowledge and template revisions are checked before returning output.
- `gateway_reference_drafts.py` supplies a separate, explicitly unvalidated authoring path. Native reference output is available across the reference vendors. Cisco and Juniper drafts can be composed into one YAML file with separate host-scoped plays in reviewed order. Missing tasks are never silently skipped. Huawei playbook output remains unavailable pending maintained, reviewed tooling; its native reference output remains independent.
- Draft preview and opening do not save, create a deployment job, approve a change or execute anything. The final button opens an unsaved buffer; Save is still explicit. Read-only reference templates have an **Edit a copy** path so guarded AI edits can operate on a new writable buffer.
- The reference library contains **141 files across 47 assessed operations and Cisco, Juniper and Huawei**: 77 published CLI copies, one explicitly labelled Cisco static-route adaptation using V9's existing address/netmask derivations, and 63 new manual-review translations. This is reference coverage, not verified runtime support. All templates parse as Jinja and match their index hashes; this does not validate device command semantics.
- The three management-security operations remain reference-only in the ordinary workspace. Runtime operation choices still come from its 44-operation published release. No isolated knowledge, required `lab_label`, schema or pointer was promoted.

### Assistant capabilities and evidence

Studio retains current unsaved Monaco text, selected code, explanation, attachments, general questions, V9 generation and exact-base edit proposals. General `.cfg`, `.conf`, `.txt` and `.log` edits now use the guarded patch path; the existing supported operation-aware adapter remains available. Native text edits are marked structurally unvalidated. YAML/Jinja/JSON/Python receive the existing appropriate parsing checks, and Ansible validation remains separately gated.

Floating Chat now has conversation-scoped attachments and deterministic routing for general conversation, inventory filtering/counts, planned topology/path queries, telemetry, syslog, incident/anomaly history, configuration captures, documentation and bounded multi-source synthesis. It receives no Monaco context or document proposal/write tools. Readers reuse existing SQLite, observation, documentation and collector services; the older mutable agent and remote fallback catalog are not imported.

Every source retains its evidence IDs, source revision, device references, timestamps, time range and origin. Simulated fixtures stay simulated; stored captures stay historical/stored; missing measurements are unavailable. The live metric reader uses the existing low-level collector query rather than legacy summaries that estimate CPU values. Measured zero is preserved; collector failure is not replaced by simulated values. Configuration capture access is owner-scoped (administrators may read all), bounded, and credential lines are removed.

`COGNISHIELD_AI_LIVE_READS=1` enables read-only use of the existing configured InfluxDB/crawler/received-log providers. The ordinary environment currently leaves this disabled. No live collector or device connectivity was established by this task. No collection, SSH or device operation is triggered. Historical time filtering is supported within the bounded available records; it is not an exhaustive telemetry archive query.

The current orchestration performs one bounded set of reads per answer. Durable multi-step investigations, model-driven retries, anomaly training/forecasting, F7 handoff, A6 and deployment remain future work. The local 1.5B model can still misread a prompt or make unsupported prose claims; manual review and source disclosures remain necessary. A browser explanation correctly described the actual unsaved static-route/BGP buffer but incorrectly called it read-only; the system instruction now explicitly distinguishes editability from unsaved state. No factual-accuracy guarantee is claimed.

### Verification for this expansion

The original restoration acceptance flow was completed and its temporary 5174/8001 pair stopped before the expansion. No further acceptance workspace was created.

- New routing checks use static routing, BGP and OSPF, not VLAN. The real V9 worker identified a missing BGP neighbor address; a correction and OSPF addition retained all three operations. Evidence: `tmp/prototype-reference/mixed-routing-review.json`, `mixed-routing-corrected.json`, and `mixed-reference-drafts.json`. The last file predates the reference-only static-route address/netmask adaptation; the browser preview verified that adaptation separately.
- Standard-port browser: corrected parsed targets and a missing destination; filled the BGP neighbor address; added OSPF with nested interface/area inputs; generated a three-operation draft; removed the OSPF category; regenerated a two-operation draft containing only static route and BGP; explicitly opened it in unsaved Monaco. The corrected route uses `203.0.113.0 255.255.255.0 192.0.2.1`. An explanation read the actual unsaved buffer without a new edit or configuration job.
- Affected shared/multi-review/network suite: **30 passed**. After final source-provenance fixes and additional draft composition checks, the expansion-only suite `test_ai_review_network.py`: **12 passed**, followed by the new citation-projection check (**1 passed**, 12 deselected). These are overlapping runs; 13 expansion-specific tests have passed. New tests cover measured zero versus collector failure, absent fixtures, exact incident IDs, ownership, source labels, cross-vendor host/module preservation, concurrent review rejection and whole-request Huawei refusal.
- Final TypeScript/Vite build passed, **3953 modules**. Existing CSS `@property` and chunk-size warnings remain. Python parsing, all 141 reference hashes/Jinja parses, ordinary release artifact verification, SQLite integrity and foreign keys passed.
- Ordinary inventory remains exactly R1/R2 with IOS 16.2.3/12.12.11. Active release remains `0690966eb003499380e960a98d1e418f`, 78 published bindings. The reference library does not change that release. No dependencies installed, knowledge published, sibling V9 source modified or device execution performed.

The final floating browser check retrieved the recorded R1–R2 planned link and simulated R1 syslog, with two source records. The local model was repetitive and echoed opaque hashes. The final inference projection omits internal hashes (unless explicitly requested) and uses short S1/S2 citations; authoritative records retain their original IDs and revisions. Both UIs display the same source numbering. This reduces irrelevant model input; it is not a guarantee of model factual accuracy.

The ordinary app was restarted with the completed code on 5173/8000; local Ollama exposes qwen2.5:1.5b. Start it in future with root `run_local.ps1`. The final frontend build passed. Acceptance is complete for the implemented local scope: stop here, retain the documented live-collector/verified-playbook limitations, and do not repeat passing generation tests or expand scope automatically.


## Intelligent assistants, OCR and Monaco continuation — 2026-10-16

This section supersedes the earlier keyword-router and F7 deferral statements. It preserves earlier generation/review acceptance work; those tests were not repeated as proof of conversational intelligence. Shared gateway, V9 contracts, explicit proposal acceptance/save, ordinary SQLite and 5173/8000 remain authoritative.

### Confirmed faults and corrections

1. The original `generation process.pdf` attachment contained 11 pages but only 1,591 extracted characters, predominantly captions. Text inside UI screenshots was missing. The reconstructed model input also emphasized UUIDs/source metadata. This explains the evidence-ID answer; masking its output alone would not recover the document.
2. Image-heavy PDF pages now receive OCR even when captions already provide some text. The same shared pipeline handles PNG/JPEG/WebP and scanned PDFs. Original page numbers, extraction method/limitations and selected-context coverage remain separate. The original PDF now yields 18,496 characters. Its matched stored attachment was backed up, hash-checked against the user file, re-extracted and audited; other attachment rows and old conversation answers were not rewritten. Backup: `tmp/ai-intelligence-audit/before-pdf-reextract.db`.
3. Greetings and arithmetic previously received old editor/configuration/history context. Shared semantic workflow selection now combines installed local embeddings with structured chat classification for uncertain cases. It selects context and capabilities, never V9 operations or permission grants. General turns omit unrelated editor/files/network/history. Document turns receive readable filename/page/line headings and actual extracted text. Requested pages narrow the context; long documents retain explicit coverage limits.
4. Real 1.5B-model evaluation found correct source selection could still produce false diagnoses from unavailable data. `gateway_findings.py` now releases deterministic missing-record results when all requested operational readers return no records. It cannot turn absent measurements into connectivity failure or absent snapshots into denied access. Inventory-only responses also render stored facts directly. Cases with actual observations still use model synthesis and retain a factual-accuracy limitation.
5. An installed OCR model appeared first in Ollama's model list and became the automatic chat selection. OCR-only names/configuration are now excluded from chat and general vision Q&A; the shared chat runtime selects the installed conversational model. LightOnOCR is an optional OCR backend, not a semantic diagram reader.

### Components and boundaries

- `frontend/src/monacoLanguages.ts` centralizes language selection/registration. Studio, diff previews, Template Studio, Knowledge Engineering and onboarding use it. Jinja expressions, filters, strings, nested expressions, comments, control/raw blocks and mixed YAML/native text are covered. Python/JSON and other language modes remain registered. `.j2`, `.jinja`, `.jinja2` and detected mixed templates select Jinja. No buffer edits/saves are performed by language selection.
- `gateway_routing.py` / `gateway_semantics.py` select relevant context using the shared Ollama/embedding provider. Greetings, arithmetic, conceptual networking, documents, active-buffer editing, generation and operational readers have distinct routes. Paraphrase examples guide workflow classification only. Ambiguous low-confidence matches fall back to structured classification; invalid routing cannot invoke an action. V9 still owns recognition, schema extraction, compatibility and rendering.
- `document_extract_worker.py`, `document_ocr.py` and `windows_ocr.ps1` extend the existing extraction service. No parallel document store or external OCR service was added. Page limits: 24 OCR attempts, 90-second scheduling budget, bounded child processes; maximum image size 16M pixels, 10MiB uploaded binary, 1MiB extracted UTF-8. Model response context is bounded to 10,000 characters; partial coverage is explicit. The OCR process boundaries and resource limits are **not a demonstrated hostile-input security sandbox**. No Ansible containment claim is made.
- `gateway_vision.py` is an optional adapter for an installed vision-capable conversational model. At most three selected page images are supplied; absence/failure remains unavailable. OCR text alone does not establish arrows, spatial relationships or topology connectivity. No general diagram understanding was verified.
- `gateway_handoff.py` provides explicit owned Floating → Studio preparation/review/acceptance, source timestamps/device references, immutable recorded observations, stale-inventory warning and idempotent acceptance. Studio gets a separate conversation and draft input, never an automatically submitted turn. Imported observations remain untrusted historical context. Ownership, evidence existence, device existence and configuration snapshot ownership are checked again before use. Older turns without stored observation payloads are identified as such; an assistant summary is never substituted for evidence.
- `TurnResponse.observations` retains bounded, redacted server-produced network payloads alongside evidence metadata for subsequent review/handoff. This field is not accepted in client turn requests. Context authorization remains enforced by the typed registry. No knowledge publishing or execution capability was granted to either chat.

### Local dependencies and model results

Existing document interpreter: `COGNISHIELD_DOCUMENT_PYTHON`, with pypdf/Pillow. PDF page rendering: local Poppler `pdftoppm` or `COGNISHIELD_PDF_RENDERER`. Default OCR: installed Windows.Media.Ocr language packs. The PowerShell helper uses a process-only `RemoteSigned` policy; no machine policy was changed. No dependencies or models were installed by this implementation.

The user-installed `maternion/LightOnOCR-2:1b` advertises image input. Set `COGNISHIELD_OCR_MODEL` to opt in; it uses the existing local Ollama provider with one normalized image/page, no tools, bounded output and 30-second inference timeout. The actual local PNG trial **timed out after 30.29 seconds** without usable text, so this optional backend is not certified and is not enabled in ordinary `.env`. Windows OCR remains the working default. The [LightOn model card](https://huggingface.co/lightonai/LightOnOCR-2-1B) and [Ollama package](https://ollama.com/maternion/LightOnOCR-2:1b) describe document-to-text OCR; their vision capability label is not proof of conversational diagram reasoning. Chat remains `qwen2.5:1.5b`, semantic matching uses `nomic-embed-text:latest`. No LangChain/LangGraph rewrite was introduced.

### Verification and limits

Evidence directory: `tmp/ai-intelligence-audit`. Intermediate failed evaluations remain there with their corrected successors; do not count failed earlier outputs as passing results.

- Focused gateway/shared-network suite: **40 passed** after missing-observation and handoff corrections. A subsequent OCR/chat-separation regression plus affected intelligence cases: **12 passed** (overlapping; 41 unique tests across the three files). Existing PDF-focused suite: **2 passed** in the preceding continuation.
- Real OCR: PNG, JPEG, WebP and scanned PDF retained the fixture's OSPF/BGP values; the real mixed-content 11-page PDF produced 18,496 characters. Failure/oversize cases and missing vision capability were covered. This is representative extraction verification, not universal OCR accuracy.
- Real chat: both surfaces produced content-based PDF summaries; arithmetic returned 2 without document evidence. An OSPF buffer edit produced a reviewable exact-base proposal retaining BGP/unrelated text. A prior chat timeout and overly terse summaries are recorded; model quality is not equivalent to Codex.
- Real semantic evaluation selected inventory, multi-source investigation, configuration-history follow-up, attachments, arithmetic, conceptual OSPF/BGP and playbook-generation workflows. Mock behavioral cases check actual V9/proposal boundaries rather than treating API success as task success. The final empty-observation release guard is tested independently of model prose.
- Monaco's actual Monarch tokenizer checks passed for comments, filters, nested expressions, strings, control/raw blocks and extension selection. TypeScript passed. Production Vite build passed with 3,985 modules; existing CSS `@property` and bundle-size warnings remain.
- Browser access was initially disabled, then restored during final continuation. Studio visibly highlights the existing unsaved BGP Jinja template and answers “1 + 1” with 2, without citing the old configuration. Evidence: `studio-jinja-browser.png`. Old erroneous chat messages remain historical records.
- Ordinary R1/R2 inventory and the ordinary knowledge pointer are preserved. No extra app workspace was created. Only standard frontend/backend ports are used. No deployment, device test, publication or sibling V9 edit occurred.

### 141-template publication assessment — not fully verified or published

`docs/shared_ai_coverage/reference_template_audit.json` contains an individual record for every one of the 141 reference files across all 47 assessed operations and three vendors. Checks include Jinja parsing, index hashes, template variables/input mappings, active-binding identity and platform/version coverage. **77** retain unchanged published CLI copies; **64** require engineering review (63 translations plus the static-route adaptation). Existing publication is not new semantic certification.

Concrete blockers include Junos VLAN-name resolution, OSPF process/area/interface differences, unbound policing/QoS dependencies, timeout/lockout semantics, a Huawei lockout placeholder and LACP mode mappings. Several drafts lack vendor-specific input contracts. Jinja parsing cannot establish command correctness, device compatibility or genuine Ansible support. Therefore the requested blanket publication of all 141 has **not** been performed. Publishing these as fully verified would misrepresent the observed defects. Ordinary release remains `0690966eb003499380e960a98d1e418f` (44 operations/78 bindings); isolated 47-operation test knowledge is not promoted. Reviewed maintained Huawei playbook tooling and contained Ansible validation remain unavailable, independently of native support.

Remaining work requires reviewed vendor contracts/semantic evidence for the unsupported translations, a verified general vision model for diagrams, and actual configured collectors for live-network claims. Resource bounds are implemented for extraction, but OS-level decoder containment is not certified. Durable investigation orchestration, ML/A6 and device execution remain outside this implementation. Do not repeatedly run completed generation tests to claim these gaps are solved.


## Resumed intelligence repairs and next milestone — 2026-10-16

### Recovery and confirmed starting state

This continuation resumed the existing application at commit `90ea74d`. The initial tracked working tree was clean: the earlier OCR, Jinja, gateway, handoff and model-selection work was already committed on disk. Nothing was reset or reconstructed from the interrupted log. The previous sections and audit files are retained as historical evidence, including failed intermediate answers. The ordinary source database was opened read-only for inspection; behavioral evaluation used disposable SQLite backups with closed backup connections. No separate app workspace/listeners were created.

The old conversational failure was reproduced through `AIGateway.turn`, using the actual R1/R2 records and installed local models. `What are R2's interfaces?` selected `network.topology`; the model returned duplicated link endpoints, omitting the management interface and correcting the stored interface spelling without evidence. `Are you sure?` lost the subject; ordinal/address follow-ups broadened to both devices. Baseline: `tmp/ai-intelligence-audit/resume-baseline.json`. Its one-off temporary-copy cleanup initially failed with a Windows open-file error; subsequent evaluation closes the backup connections explicitly and does not write ordinary data.

### Corrections made in this continuation

- `gateway_references.py` refines concrete read scopes using actual inventory and the preceding **server-produced** result. It records ordered device/interface references and requested attributes, rechecks ownership, and rereads through the authorized registry. Confirmation, ordinal selection, singular pronouns and “what about R2?” retain only the relevant subject. Ambiguous pronouns and unknown interfaces ask for clarification. A new general turn ends that retrieval context. No model-written device name or previous assistant claim establishes a source fact.
- `gateway_routing.py` retains semantic embedding/structured-model routing and adds narrow source/context guards for explicit network reads and active-buffer explanations. These guards select resources, not V9 operations. Concrete requests for interfaces/IPs, saved configs and plural syslogs cannot silently turn into topology, upload reading or generation. Additional semantic examples cover those read intents.
- `gateway_network.py` resolves exact device IDs/hostnames/aliases consistently, preserves requested scope even if a live reader has no observations, and scopes inventory evidence to returned devices. The plural `syslogs` and bare `configs` forms now reach the corresponding readers. No SQLite inventory value is relabelled or corrected. R2's second interface is actually stored as `GigabiEthernet0/1`; that spelling is preserved.
- `gateway_findings.py` renders requested factual attributes and authorized source records directly. Interface questions include the full stored interface inventory, addresses and types; topology links are explicitly a separate view. Captures retain timestamps and simulated/stored provenance. Syslogs, measurements and incidents display actual record values. Operational absence cannot become a fault or authorization failure. Oversized/truncated context is reported as partial instead of “no records.” Multi-source output is a bounded evidence summary, not an autonomous root-cause diagnosis.
- `gateway_store.py` retrieves the last completed owned result for reference resolution without introducing a new memory database. A cached network answer cannot be reused after a recorded role change. Existing separate histories, typed permissions and handoff checks remain in place.
- `gateway.py` uses the requested attributes and source scope, preserves explicit active/unsaved buffer explanations, and appends human-readable file/page references and OCR uncertainty independently of model wording. The final PDF-summary instruction from the interrupted session is present and was exercised with the actual model. Guarded proposals, exact-base/version checks and explicit saving were retained.
- `backend/scripts/evaluate_shared_ai_behavior.py` is an opt-in local behavioral evaluator. It snapshots existing SQLite, reuses the existing PDF extraction records, invokes the real shared gateway/provider/readers without router/model/tool mocks, compares returned values and tool selections, and writes an evidence report. It does not start app copies, run generation suites or create device jobs. Run deliberately with `--documents` for the slower PDF/editor cases; it is not an automatic inference dependency.

### Verification run now (distinct from earlier sessions)

Final focused command:

`backend/.venv-m0/Scripts/python.exe -B -m pytest backend/tests/test_ai_intelligence.py backend/tests/test_shared_ai.py backend/tests/test_ai_review_network.py backend/tests/test_shared_ai_pdf.py -q -p no:cacheprovider`

**47 passed in 6.76s**, with one inherited Starlette/httpx deprecation warning. Intermediate runs found two obsolete model-call assertions in existing tests after factual inventory rendering stopped requiring a model; the tests now check the actual returned facts and credential exclusion. New regressions cover source rereads after an interface changes in the disposable DB, exact/unknown/ambiguous interface references, cached-role changes, explicit active-buffer explanation, and saved-config/plural-syslog routing with an unrelated upload present. Existing focused cases cover owner/surface isolation, Floating write denial, real-buffer proposal guards, revision-checked saving, handoff ownership/idempotency/no automatic turn, OCR errors and model separation. No unrelated V9 generation suite was rerun.

Actual-model/source evaluation: **30/30 cases passed**, plus **2/2 multi-source investigations**, through both Floating and Studio shared-gateway paths. Evidence:

- `tmp/ai-intelligence-audit/resume-behavior-verified.json` and `.log`: full prompts, answers, tool choices and context coverage, using the ordinary SQLite snapshot and installed `qwen2.5:1.5b`/embedding service.
- `tmp/ai-intelligence-audit/resume-investigations.json`: both surfaces invoked inventory, planned topology, telemetry, syslog, incident and configuration readers; retained simulated provenance; made no verified-root-cause claim.
- `resume-behavior-final.json` / `resume-behavior-first.json` retain earlier evaluation failures. In particular, a real active-buffer explanation initially became a generic definition; the explicit context guard corrected it. The final answer quotes the actual unsaved marker, and the actual OSPF edit proposal changes only `192.0.2.9` to `192.0.2.44`, preserving the unrelated BGP section.

The R2 checks compared actual stored values: `GigabitEthernet0/0` → `192.168.1.251`; `GigabiEthernet0/1` → `10.1.1.2`. “Are you sure?” rereads these rows; “the first one” narrows the ordered result; “its IP” returns that interface's address. Stored config follow-ups switch R1 → R2 without switching the subject to inventory. Page 4/5 PDF answers use real extracted contents, carry server-produced page references and disclose OCR uncertainty. Greetings/arithmetic exclude prior document/editor/network context. Missing live measurements remain unavailable.

TypeScript validation **passed** (`D:/node-js/node.exe node_modules/typescript/bin/tsc -b` in frontend). No frontend source was changed in this continuation, so the earlier successful production build/tokenizer evidence was retained rather than repeated. Final whitespace check passed with the repository's CRLF files accounted for. Ordinary SQLite integrity is **OK**, R1/R2 and addresses remain unchanged, and the ordinary active release remains `0690966eb003499380e960a98d1e418f`. The standard app was restarted with the updated backend: frontend **5173**, backend **8000**, both HTTP **200**. No alternative CogniShield listeners were present before restart. Browser UI automation was attempted once and is currently disabled in Work settings; fresh UI clicks/Accept/Reject/Undo were not claimed. Prior UI acceptance evidence remains historical; current backend proposal/save regressions pass.

### Remaining limitations and current tree

The local 1.5B model is still a limited general-knowledge/summary model. An intermediate OSPF-versus-BGP answer contained incorrect protocol claims; a PDF follow-up also described layout beyond what OCR establishes. Direct network facts now bypass that prose reconstruction, but arbitrary general-knowledge answers and free document paraphrases are **not semantically certified**. The final PDF cases establish readable content, correct source pages and disclosed OCR limits, not perfect summarization or diagram understanding. No claim of Codex-equivalent intelligence is made.

LightOnOCR remains optional and disabled in ordinary `.env`; its earlier 30.29-second timeout is not a successful OCR result. Only the installed conversational model is offered for chat. Windows OCR remains the working default; no dependencies, models or policies were changed now. Extraction resource limits are not verified hostile-input containment. No live collector, device reachability or real-device test was established. The 64 unreviewed references and Huawei playbook/contained validation limits remain as documented; no template publication, sibling V9 changes, data migration or execution occurred.

At this checkpoint, tracked changes are confined to shared gateway/routing/findings/network/history modules, two focused test files and this handover. New untracked source files are `backend/llm/gateway_references.py` and `backend/scripts/evaluate_shared_ai_behavior.py`. Audit artifacts stay under ignored `tmp/ai-intelligence-audit/`. The ordinary DB, frontend and provider/OCR/vision implementations have no new diff from this continuation. No automatic commit was made.

### Next milestone: bounded LangGraph investigations with LangChain adapters — plan only

**Starting decision:** retain the corrected direct read/document/editor paths. Add orchestration only for explicitly requested multi-step investigations where iterative source selection, resumable state and evidence checks provide measurable value. Do not migrate the app to another agent platform.

Environment assessment now: the application's `backend/.venv-m0` interpreter is Python 3.14 with Pydantic 2.14.0; `langchain`, `langchain-core`, `langchain-ollama`, `langgraph` and checkpoint packages are **not installed there**. Earlier reports of installed framework versions concern a different interpreter and are not app readiness evidence. The first implementation step must select/test a compatible pinned package set against this interpreter and existing dependencies, without altering the protected sibling V9 environment. Nothing was installed for this design.

| Capability | Reuse and proposed module boundary | Regression gate |
|---|---|---|
| 1. Semantic intent | Keep `gateway_routing.py`, `gateway_semantics.py` and the reference guards; optional `llm/orchestration/plan.py` validates a typed investigation plan with goals, scoped readers and clarification needs. | Paraphrased reads, topic switches and ambiguous references select appropriate sources; no accidental write. |
| 2. Tool selection/calling | `llm/orchestration/adapters.py` exposes LangChain tools whose only implementation is `ToolRegistry.invoke` with server-created authorization. No direct raw SQL, shell, HTTP or old mutable-agent tools. | Forged tool names/roles/scope, empty allowlists, retries and resumed calls cannot bypass authorization; zero model-generated observations. |
| 3. Context-aware RAG | Adapt existing `build_context`, `documentation_context` and V9 published retrieval into scoped retrievers. Preserve attachment owner/conversation, document pages, hashes and namespace authority. Benchmark any indexing change first. | Relevant passages improve retrieval over current lexical selection; real citations, bounded coverage and draft/published separation survive. No attachment automatically enters knowledge. |
| 4. Structured memory | Reuse `ConversationStore`, recorded retrieval entities, evidence and handoff records. `llm/orchestration/state.py` holds investigation goals, open questions, evidence references/revisions, budgets and status. | Restart/resume retains the correct subject; users/surfaces never share memory. Model summaries remain untrusted and cannot replace records. |
| 5. Multi-step workflows | `llm/orchestration/investigation.py` uses a bounded LangGraph: plan → authorized reads → assess gaps → at most one additional read round → verify → answer/clarify. | Maximum 2 read rounds, 8 total calls, 4 concurrent readers, 120-second investigation budget inside existing turn timeout; cancellation/timeouts/partial results release honest output. No open-ended loop. |
| 6. Grounding verification | Extend `gateway_findings.py` with `llm/orchestration/verify.py`: exact device/interface/address/value assertions must match source records; separate observation, inference and unavailable evidence. A model critic is advisory only. | Corrupted, stale, simulated, missing or mismatched evidence cannot establish a current measurement or root cause. Unsupported claims are removed or released as unavailable. |
| 7. Context awareness | Keep gateway context building and actual Monaco snapshots/revisions. The initial graph has network context only; document passages enter only when authorized/relevant. Studio proposals remain in the existing service/UI review path. | Floating cannot acquire Monaco/proposal/save capabilities; Studio unsaved buffers, Accept/Reject, Undo and explicit Save continue unchanged. |

Initial scope: read-only investigation of one named device, optionally its planned peers, using the existing inventory/topology/telemetry/syslog/incidents/configuration services. Example: “Investigate R1's reported packet loss using available records for this time range.” Read missing sources honestly, retain original timestamps/units/provenance, distinguish historical simulation from live observations, identify evidence gaps, and return a reviewable finding. No automatic remediation/generation, collection, device commands, new live collectors, ML, multi-target engineering or knowledge publication. Existing explicit handoff remains a separate user action.

LangChain's Ollama integration supports model/tool adapters, but model tool-calling support must be tested for the selected local model rather than inferred from package presence. Prefer a thin adapter over the existing `LLMProvider` so model resolution, cancellation, limits and OCR exclusion remain shared; adopt `ChatOllama` only if an equivalence test demonstrates value without a parallel provider configuration. See the [official ChatOllama integration](https://docs.langchain.com/oss/python/integrations/chat/ollama).

Checkpoint ownership is separate from authoritative conversations/evidence/approvals. Use a local persistent checkpointer behind a server-side mapping keyed by owner, assistant kind, conversation and investigation ID, with retention, backup and schema-version policy. Never accept a client-provided framework thread ID as authorization. Recheck current access, conversation binding and source revisions before resume/cache use. Do not put credentials/raw attachment binaries into checkpoints. LangGraph distinguishes per-thread checkpoints from cross-thread stores, and in-memory checkpoints do not survive restarts; see [official persistence documentation](https://docs.langchain.com/oss/python/langgraph/persistence).

Human clarification may interrupt the graph; review/approval remains in CogniShield's existing records. Resumed nodes can restart from their beginning, so any future persistence/handoff side effect needs an idempotency key and a fresh authorization check. Keep application-level input validation even if framework interrupt schemas are available; current documentation requires LangGraph >=1.2.12 for typed `response_schema`. See [official interrupt semantics](https://docs.langchain.com/oss/python/langgraph/interrupts). Cloud tracing and hosted services are not required.

Implement in three reviewable steps: (1) pinned compatibility spike and adapter equivalence tests without changing default routing; (2) feature-flagged single-device read-only graph, local checkpointing and restart/cancellation/authorization tests; (3) scoped retrieval and claim checks with a measured real-model evaluation against this continuation's R1/R2 baseline. Adoption requires all current focused regressions plus evidence that adaptive reads improve task completion without degrading exact values, isolation, latency or unavailable-data handling. Retain a deterministic fallback and disable the graph on incompatible/missing dependencies. **This milestone was assessed and planned only; no framework code, packages or checkpoint schema were introduced.**


## Phase B1 — shared LangChain/LangGraph read-only vertical slice — 2026-10-16

### Implemented and enabled

B1 is now enabled in the existing ordinary app with `COGNISHIELD_AI_ENGINE=langgraph_b1`. Frontend/backend remain **5173/8000**. The existing `/api/v1/ai/conversations/{id}/turns` API, `TurnRequest`/`TurnResponse`, conversation repository and request idempotency are retained. An authenticated Floating interface question has traversed all seven graph nodes, invoked the original inventory capability through a LangChain adapter, returned actual R2 interface/address records and passed exact-value verification. This is a working vertical slice, not only a dependency or graph-construction exercise.

The pre-existing uncommitted Phase A changes were preserved. Before B1 changes, the Phase A focused suite was rerun: **47 passed in 6.68s**. Existing extraction, OCR, Jinja and guarded editing were inspected, not rebuilt. No sibling V9 source, active knowledge or templates were edited or published.

### Actual execution paths and scope

In local-lab mode, `App.tsx` selects `SharedInventoryChat`; it sends `aiApi.turn` to the authenticated shared API. `backend.py` selects `local_app`, whose lifespan owns the existing SQLite manager and whose router creates `AIGateway`. After normal owner/request checks, Floating requests optionally enter B1; the gateway remains responsible for persistence, cancellation and response delivery. Non-network turns leave the graph after understanding/reference resolution and use the existing conversation/document service. The document pipeline is shared, including stored OCR context, page references and coverage caveats.

Local Studio also calls this shared API, but **B1 does not route Studio engineering actions into the graph**. Its existing current-Monaco snapshot, V9 preview/revalidation, exact-base proposals, Accept/Reject/Undo and explicit Save paths are preserved. B1 tests cover delegation to `v9.preview` and Floating refusal to invoke engineering tools. The normal-mode frontend still uses `FloatingInventoryOverlay` and the older Studio endpoints; `integrated_backend` registers `llm.api` at `/api/v1/llm/chat`. B1 does not wire local SQLite adapters into normal remote integrations or import the older mutable `NetworkAgent` into the shared gateway. Normal-mode remote services were not started/tested as part of this local milestone.

### Modules and authority boundaries

- `llm/orchestration/state.py`: Pydantic state for request/intent, owner/surface/conversation, resolved device/interface references, relevant prior-context references, authorized plan, typed provenance, results/observations, validation, final answer, limits, rounds and node trace. Authorization and provider/DB clients are never model-generated or checkpointed state.
- `llm/orchestration/engine.py`: actual `StateGraph` with **understand_request → resolve_references → select_authorized_tools → execute_tools → evaluate_evidence → verify_facts → compose_response**. Conditional edges skip tools for conversation/documents and allow one additional inventory read when an operational source is unavailable and checking the recorded subject is relevant. Limits: **2 read rounds, 8 tool calls, 120 seconds overall, recursion limit 20**. There is no arbitrary tool loop, native command execution or persistent graph replay endpoint.
- `llm/orchestration/adapters.py`: LangChain `StructuredTool` adapters over the **same** inventory/device-interface, configuration, topology, syslog, telemetry, incidents and documentation capabilities. The implementation always calls the original `ToolRegistry.invoke`, rechecks owned conversation access and enforces a read-only allowlist, typed input/output validation, role/resource permissions, availability and timeout. The adapter cannot call `execute`, accept a client role, or expose proposal/write/publication capabilities. Invocation count is bounded; unavailable readers never become invented measurements.
- `llm/orchestration/model.py`: `ChatOllama` uses the existing `local_providers.chat.runtime()` endpoint, model discovery and per-request selected conversational model. Embedding/OCR models remain excluded; no second registry/configuration is introduced. Structured classification uses the existing route schema and receives a 30-second model deadline; empty/refused/malformed/provider-error responses fail safely. Native model tool calls are not trusted in B1. LangSmith tracing is explicitly disabled around graph, tools and model operations; installed tracing libraries do not require cloud services or credentials.
- `llm/orchestration/verification.py`: matches exact scalar values with their record identities against independently copied authorized tool snapshots, including hostnames, interface names/addresses, configuration text, topology path/nodes and non-truncated inventory counts. It checks source identity/metadata and tool association separately. Mutable graph/projection objects cannot change their own verification source. Requested query ranges and verified inventory-scope projections are distinguished from original source metadata. A fluent but incorrect candidate answer is reconstructed from validated records; invalid retrieved facts are withheld with status unavailable and no invalid observations/evidence exposed. This verifies recorded values, not device safety or an inferred root cause. Documentation verification is provenance-only; free model paraphrases are not certified.
- `gateway.py`, `gateway_routing.py`, `tools.py` and `gateway_diagnostics.py`: thin integration, injectable LangChain classification backend, read-only capability metadata and passive engine diagnostics. Existing `gateway_network.network_context`, `NetworkReader`, `gateway_findings.network_answer`, `gateway_references`, retrieval helpers, evidence contracts and SQLite history remain the source/service implementation. They are reused rather than cloned.

The LangGraph run has no checkpointer in B1. Immediate conversational memory still comes from owner-bound SQLite turns and Phase A's recorded retrieval entities. No new checkpoint tables, graph-based approval store or migration was introduced. Durable restarts/replay remain B2 work. Failed/cancelled graph runs cannot create engineering proposals; the graph contains only readers. Cached requests continue returning the original response without executing the graph again.

### Dependency and model compatibility findings

The active app interpreter is Python **3.14.0** with Pydantic **2.14.0**. Installed and pinned:

- `langgraph==1.2.15`, `langchain-core==1.6.11`, `langchain-ollama==1.1.0`, `ollama==0.6.3`.
- `langgraph-checkpoint==4.3.0`, `langgraph-prebuilt==1.1.1`, `langgraph-sdk==0.4.7` and other resolved transitive packages are pinned in `backend/requirements-agent-b1.lock.txt`. LangChain Core supplies the tool/model abstractions; the monolithic high-level agent package is unnecessary for this explicit graph.
- The newest compatible SDK requires WebSockets `<17`; the first resolver run correctly rejected the existing `17.2` pin. The only existing runtime pin changed is **websockets 17.2 → 16.1.1**. All other existing local pins were constrained during resolution. The local requirements/lock include the B1 additions. `pip check` passes. Python 3.14 wheels were available; no compiler stack, LLM weights, Ansible tooling or network drivers were installed. A pip warning left an ignored temporary old WebSockets directory while the prior server had the package loaded; the replacement package and subsequent WebSocket tests pass.

The installed `qwen2.5:1.5b` advertises completion/tools. A real native-tool probe chose `inventory_read` but emitted **`device_name` instead of the declared `device_id`**; that call would fail strict input validation and was never executed. The no-tool greeting probe behaved correctly and the structured JSON classifier produced valid JSON. See `tmp/ai-intelligence-audit/b1-model-probe.json`. B1 therefore uses validated routing plans and deterministic authorized execution, not native tool-call trust. Existing `nomic-embed-text:latest` remains the semantic embedding model. LightOnOCR stays excluded from conversational/tool selection and was not enabled or downloaded.

The small model still makes semantic classification errors even with valid JSON. Real fallback probes misclassified nonverbal requests for a stored configuration or link details. Narrow shared reference guards now bind those explicit recorded resources to readers; the failures remain in `b1-structured-model-live.json` and `b1-structured-topology-live.json` as pre-correction evidence. They are not counted as successful model reasoning. Ambiguous broader interpretation remains a limitation, not solved by importing frameworks.

### Verification and measured comparison

**Current focused regression evidence:** combined B1 + affected Phase A suite: **68 passed in 10.17s**. After adding provider-error mapping and independent immutable source snapshots, the final B1-specific suite passed **23 tests in 4.80s**. Together with the 47 retained Phase A cases this covers **70 unique focused tests across the final runs**, with overlap rather than additive repeated-run counts. The combined command uses `test_b1_agent.py`, `test_ai_intelligence.py`, `test_shared_ai.py`, `test_ai_review_network.py` and `test_shared_ai_pdf.py`. Intermediate failures exposed an incorrectly targeted mock for the new engine import and an overly narrow unknown-device evaluator assertion; those test issues were corrected. No unrelated native-generation suite was repeated.

New tests exercise the real graph/registry/controlled SQLite readers, actual response contract, API idempotency, user/surface separation, unknown devices, changed-source rereads, ordinal/IP follow-ups, configuration ownership/provenance, missing data, one conditional additional read, tool budgets/deadlines, denial/empty allowlists/strict arguments, malformed/refused/timeout decisions, documentation adapter provenance, existing document delegation, Studio V9 boundaries and rollback. Fabricated addresses, counts, graph paths and provenance cannot pass merely by carrying a valid source citation. Unit-injected model/tool failures establish control-flow guarantees, not local-model intelligence.

Real local-model/source comparison: `backend/scripts/evaluate_b1_agent.py` uses identical read-only backups of ordinary SQLite, unchanged observation fixtures, actual gateway calls and actual Ollama HTTP requests. HTTP calls are counted without substituting responses. `tmp/ai-intelligence-audit/b1-comparison.json` and `b1-comparison-final.log` retain per-case routing/tools/origins/answers/latency/counts. After correcting shared semantic examples for the broad “our setup” paraphrase, both paths passed **11/11** representative cases. The initial miss remains in `b1-comparison-initial.json`; improvement on that paraphrase belongs to the shared router, not LangGraph itself. The legacy unknown-device answer was already a correct explicit absence result; the evaluator was adjusted to accept that wording rather than create a false B1 advantage.

| Same 11-case sample | Legacy | LangGraph B1 |
|---|---:|---:|
| Correct routing/tool/value checks | 11/11 | 11/11 |
| Median latency, all cases | 31.77 ms | 43.54 ms |
| Median warmed factual cases | 27.45 ms | 41.65 ms |
| Chat / embedding requests | 1 / 2 | 1 / 2 |
| Authorized reader calls | 15 | 15 |

These are single local samples, not a statistical speed benchmark. B1's first import cost about 1.13s; warmed graph checks add overhead. B1 avoids a reader for a clearly unknown device, and adds a bounded inventory check for unavailable scoped telemetry. No general answer-quality or speed improvement is claimed; its demonstrated additions are explicit orchestration, enforceable limits and source-value verification.

Live standard-server proof: `b1-http-runtime.json` records **three authenticated HTTP turns** in Floating conversation `154d5574ad714712bcde83206430d2e6`, using existing local JWT authentication with engineer permissions and no retained token. The actual API returned verified R2 interfaces and the first-interface address, then reread it on “Are you sure?”. This deliberately created one new, retained, reviewable verification conversation in ordinary history; existing conversations/inventory/configurations were not overwritten. No jobs or knowledge releases were created. The final runtime check added two verified nonverbal capture/link requests in the same conversation (five verification turns total); `b1-runtime-final.json` records those answers and both working WebSocket endpoints after the final source-snapshot fix.

`b1-document-live.json` confirms a real B1 Floating PDF question delegates to the existing extraction/answer service: page 4's actual content, human page citation and OCR/layout limitation appear; no network tool is called. This does not establish visual diagram interpretation. Existing Studio current-buffer/V9/proposal/save behavior is covered by affected regressions, not re-described as newly implemented graph functionality.

TypeScript validation passed. Existing local topology `/ws` and telemetry `/api/telemetry` WebSockets connected successfully under WebSockets 16.1.1, returning `initial_topology` and `local_lab` / `live_telemetry:false`. Frontend 5173 and backend 8000 returned HTTP 200. Browser UI clicking was not required for backend changes; no new browser acceptance/visual redesign is claimed. Ordinary active knowledge remains `0690966eb003499380e960a98d1e418f`; the 64 unreviewed references remain unpublished and isolated knowledge stays separate.

### Rollback and remaining B2/B3

Set **`COGNISHIELD_AI_ENGINE=legacy`** in the existing root `.env`, then restart root `run_local.ps1`. No schema rollback, conversation copying or package uninstall is needed to disable graph execution. B1 dependencies may remain installed. A missing B1 import falls back to the existing gateway with an explicit diagnostic; denied/model/runtime failures do not silently re-execute engineering actions. Unknown engine configuration fails unavailable. The flag/engine choice is server configuration, not a frontend profile. Full dependency rollback is a separate environment operation; do not casually reinstall old WebSockets while the server is running.

**B2:** reviewed/pinned durable checkpointing with owner/surface/server-generated thread mapping, authorization/revision rechecks on resume, retention/cancellation/replay tests; richer scoped documentation/file retrieval and claim verification; adaptive multi-source investigation planning beyond B1's one bounded inventory follow-up. Compare against these real R1/R2/evidence baselines before adoption.

**B3:** extend the shared graph/context coordination to Studio explanations and authorized engineering proposals, richer structured conversational memory, and optional multimodal coordination. Keep V9 operation/schema/compatibility/rendering authority, existing Monaco review/undo/save, and explicit Floating → Studio handoff. A framework interrupt must never become an approval or permission grant. No broad multi-file editing, general vision certification, live collector deployment, device execution, autonomous remediation or knowledge publication is included in B1.

No automatic commit was made. The prior Phase A dirty work is retained; B1 adds the orchestration package, pinned dependency file, evaluator and focused tests, with narrow edits to gateway/routing/registry/diagnostics/configuration. The ordinary DB diff is the explicitly described verification conversation, not a data migration or test inventory insertion.


## Phase B2 — persistent read-only investigations and existing knowledge coordination — 2026-10-17

### Completion and retained boundaries

B2 is implemented and enabled in the ordinary local application with `COGNISHIELD_AI_ENGINE=langgraph_b2`. The existing B1 graph, LangChain adapters, gateway API, SQLite conversations, Ollama registry, document/OCR pipeline and V9 adapter remain in place. Studio generation, clarification, current unsaved Monaco explanation, proposals, Accept/Reject/Undo and explicit saving retain their existing paths. No Studio engineering action was migrated into the graph. Normal-mode remote adapters retain their established paths; this milestone verifies local-lab composition only.

The first action was inspection of the dirty tree, B1 source and handover. The existing 70 affected B1/Phase A tests passed before B2 edits. Prior uncommitted work was preserved. No source reset, automatic commit, model download, dependency installation, sibling V9 modification, knowledge publication, network collection, device testing or deployment occurred. This is a bounded investigation assistant, not a claim of general Codex-equivalent reasoning or verified live-network awareness.

### Reused and extended execution flow

- `backend/llm/orchestration/engine.py`: extends the same seven-node B1 graph behind a server configuration flag. B1 remains selectable. Understand → resolve → select authorized tools → execute → evaluate actual gaps/conflicts → conditionally retrieve more → verify → compose. Direct lookups use one round; a broad investigation initially inspects inventory, topology and saved configuration, then consults existing operational readers when evidence is incomplete. Explicit multi-source requests can retrieve their named sources immediately. No unrestricted autonomous loop or native tool-call trust was added.
- `orchestration/investigation.py`: contextual investigation references, read-only published-requirements/document coordination, evidence-gap assessment, conservative cross-source conclusions and deterministic published-contract presentation. Historical/simulated records and missing fresh observations cannot establish a current fault. Explicit saved Cisco-style interface/address pairs are compared with inventory, and conflicting metric values at the same device/field/timestamp are flagged. These checks are deliberately limited; they are not a complete vendor parser, configuration validator or root-cause proof.
- `orchestration/adapters.py`, `model.py`, `state.py`, `verification.py`: reuse the existing registry and immutable tool snapshots, adding bounded state, recoverable reader failures, a three-routing-inference ceiling, source availability/content checks and document/network answer separation. Exact network facts are reconstructed from verified records, not accepted merely because model prose contains a citation. Documentation prose is not certified as an engineering conclusion.
- `gateway_references.py`: “other interface” stays on the previous device; explicit corrections such as “Actually I meant R1, not R2” replace the subject. General-topic exclusions leave old network scope behind. These shared reference fixes also benefit B1/legacy; they are not attributed solely to graph orchestration.
- `gateway.py`: thin B2 selection using the existing turn API and response envelope; server-owned remembered document IDs narrow the existing document reader, which rechecks ownership. Mixed document/network answers release their network portion from validated records and label document interpretation separately. Uploaded prose cannot become an operational observation. A narrow exact-token guard withholds invented network tokens in the document interpretation; it does not certify all natural-language claims.
- `gateway_diagnostics.py`, root `.env` and `.env.example`: explicit B2 engine, checkpointing and budget diagnostics. Standard ports remain frontend **5173** / backend **8000**.

Limits: at most **3 retrieval rounds**, **8 authorized reader calls**, sequential reader execution, **3 routing model calls**, **120 seconds** per graph run and recursion limit 35. Existing registry tool timeouts and the gateway's outer 240-second turn limit remain. General/document synthesis stays on the existing provider path and is not counted as a graph routing call. A slow local model can still delay these answers. Timeouts/denials do not trigger automatic engineering retries or device actions.

### Durable memory, checkpoint storage and recovery

`orchestration/memory.py` implements the installed `BaseCheckpointSaver` API using JSON-only records in the same conversation database. No additional checkpointer package or second database is introduced. This uses LangGraph's existing checkpoint contract ([reference](https://reference.langchain.com/python/langgraph/checkpoints)); application ownership and recovery rules remain outside model control.

The additive migration `shared-ai-4-b2` in `gateway_store.py` creates:

- `ai_agent_investigations`: server-generated investigation/thread ID bound to authenticated owner, assistant surface and conversation; current request, schema version, status and update time.
- `ai_agent_checkpoints`: node-boundary checkpoint records keyed by that server-owned thread, per-turn namespace and checkpoint ID. Only the validated memory channel and minimal framework control metadata are durable.

Memory contains the user investigation goal, device/interface identities, ordered entity references, selected attachment IDs, domains/attributes, evidence IDs/revisions, turn reference and unresolved questions. Authorization objects, credentials, raw configurations, model-generated factual prose, document contents, uploaded binaries and tool clients/results are excluded. Goal text passes the existing credential-line redactor. Every save/load rechecks the owned conversation and mapping. Client requests cannot submit a thread/checkpoint ID. Unknown memory schema or invalid JSON resets orchestration memory without rewriting conversation history. Conversation deletion removes its checkpoints; access-triggered retention removes investigations older than **30 days**, and storage retains the most recent **32 checkpoints** per active conversation investigation.

Recovery semantics are intentionally **refresh from the saved goal/references**, using a fresh turn and fresh registry authorization/source reads. This is not byte-for-byte replay of pending framework tasks. Raw reader results and pending tool writes are not persisted or trusted. Completed request IDs still return the original idempotent response. Cancelled/failed requests require a fresh request ID. Ownership, current roles, exact entity resolution, attachment availability and newly retrieved source revisions are rechecked; changed revisions are disclosed on contextual rereads. Cancellation blocks later checkpoint/result writes and preserves an incomplete goal for an explicit continuation.

A graceful cancellation/timeout can resume immediately with a new turn. A hard process crash can leave the existing `ai_turns` five-minute running-turn lease; the next new turn is rejected until that lease expires, then existing stale-turn recovery cancels it. Immediate hard-crash cursor replay and multi-worker/distributed investigations are not implemented. Completed-conversation restart continuity is demonstrated on the actual standard backend; cancellation/timeout recovery is tested with controlled SQLite. No resume path stages proposals, generates configuration or transfers permissions.

The ordinary DB was backed up before migration:
`backend/db/backups/m0_2_m0_3_browser_smoke-before-shared-ai-4-b2-20261016T160352643126Z.db`.
Existing conversations/attachments were retained. Three B2 HTTP verification turns were deliberately added to the already retained B1 verification conversation `154d5574ad714712bcde83206430d2e6`; no test devices/configurations were inserted into ordinary data. Other behavioral evaluation used disposable SQLite backups with explicit path assertions and closed backup connections.

### Existing V9 and document retrieval coordination

No RAG pipeline, vector store, embedding index or catalog recognizer was built. `knowledge.search` still enters the existing authorized `NetworkReader` and `gateway_knowledge.documentation_context`. Its existing bounded published-document retrieval selects candidate references. For explicit published requirement questions, the adapter now calls a read-only `published_requirements` action in the **existing** `local_providers/knowledge_worker.py`:

- Opens V9's existing `active_snapshot`, `KnowledgeService.get_operation`, published schema artifacts and template-binding manifest.
- Checks release identity and the active pointer before returning; exits before constructing/migrating an authoring store.
- Returns exact base/nested required fields, vendor requirements and declared native profiles for the retrieved candidates. This explains contracts; it does not select a generation operation, validate inventory compatibility or render output.

The ordinary release's offline retrieval manifest is still not a verified Chroma service. The existing published-document lexical retrieval is identified honestly; no new Chroma index was created. Candidate requirements are not a claim that every related operation was exhaustively retrieved. V9 remains authoritative for engineering recognition, target/schema/compatibility validation and rendering.

A measured context-selection defect was repaired: the OSPF question retrieved about **14,649 characters** of repeated documentation/contracts, exceeding the per-source budget during a three-source investigation and discarding the structured contract. Keeping the authoritative contract plus 800-character prose excerpts per candidate preserves the required fields within the same context budget. The real end-to-end OSPF/configuration case now returns published `configure_ospf` requirements (including `interfaces[].name`, `interfaces[].area`, vendor `process_id`) and R2's actual simulated saved capture. It explicitly states that no OSPF text was found in the returned excerpts, which does not prove absence on the device or validate compatibility. No generation is invoked.

Uploaded PDFs/images still use the same owner-bound extraction records, Windows OCR and bounded document context selection. Remembered attachment IDs survive a new gateway instance; removing the selected attachment asks for clarification rather than silently substituting another document. No OCR was unnecessarily rerun and LightOnOCR was not enabled. Actual page 4 followed by “What about page 5?” reuses the selected PDF, supplies real page text/citations and discloses OCR/layout limits. The 1.5B model's follow-up summary is still broad and sometimes hedged; general diagram semantics and full document inference are not certified.

### Verification performed in this continuation

Final focused command:

`backend/.venv-m0/Scripts/python.exe -B -m pytest backend/tests/test_b2_agent.py backend/tests/test_b1_agent.py backend/tests/test_ai_intelligence.py backend/tests/test_shared_ai.py backend/tests/test_ai_review_network.py backend/tests/test_shared_ai_pdf.py -q -p no:cacheprovider`

**89 passed in 70.62s**. This includes 19 B2 cases plus 70 retained B1/Phase A cases. New cases use the real graph/registry/controlled SQLite, with explicitly injected model/failure cases: adaptive reads, exact R2/ordinal/other-interface values, explicit corrections, fresh source revisions, goal preservation after failed routing, timeout/cancel recovery, idempotency, concurrent-turn rejection, role/owner/surface/checkpoint isolation, invalid schemas/JSON/retention, selected-document continuity/removal, network/document grounding separation, and conflicting/stale/unavailable data. Existing cases preserve Studio V9/proposal/Monaco/save and handoff boundaries.

An intermediate loaded run exposed a genuine recovery edge: a checkpoint saved after understanding but before resolution could contain `R2` rather than canonical ID `2`. Resume now uniquely resolves either form against current inventory, and unresolved-device clarification clears active domains. The timeout fixture now allows graph initialization before the deliberately paused reader; the final full suite passes. This was not ignored as model error. Other intermediate failures were a missing import in the new document-memory branch and an initial test-module import; both were corrected before acceptance.

Actual installed-model/source comparison: `backend/scripts/evaluate_b2_agent.py`, report/log `tmp/ai-intelligence-audit/b2-comparison.{json,log}`. Uses identical ordinary SQLite backups, existing observation fixtures, actual published V9 access and real Ollama HTTP calls; responses were not mocked. Same 14 scenarios for each engine:

| Single local sample | B1 | B2 |
|---|---:|---:|
| Checked request/tool/value outcomes | 12/14 | 14/14 |
| Median latency across the sample | 92.78 ms | 188.28 ms |
| Authorized reader calls | 24 | 32 |
| Chat / embedding requests | 4 / 5 | 4 / 4 |

B1 missed the “other relevant information sources” cross-check and published OSPF-plus-stored-configuration coordination. B2 completed both. The generic investigation used two evidence-driven rounds in B2 versus B1's single six-reader sweep. The higher call count includes completion of sources B1 missed; it is not an efficiency gain. Warm R2 interface lookup was about 59ms B1 / 103ms B2 in this sample. Cold imports, local load and generated answer length differ. A general explanation took about 57 seconds in B2; no speed or general intelligence superiority is claimed. The model summaries are evaluated as content-based, cited answers, not automatically certified interpretations. No tested network answer released a confirmed live fault/root cause from the simulated records.

Additional evidence:

- `b2-http-before-restart.json`: actual authenticated standard-API investigation; B2, two rounds, six readers and 250 checked scalar values.
- `b2-http-after-restart.json`: backend PID changed **17252 → 12280**, same owned conversation, both evidence and cross-check follow-ups restored state, reread six sources and verified records without live-data claims. Tokens were not logged.
- `b2-document-followup.json`: actual local-model page 4 → page 5 continuation after reopening the database/gateway, same selected attachment, accurate source pages and OCR limitations.
- `b2-runtime-final.json`: final source refreshed on the standard launcher (backend PID 16920), frontend/backend HTTP 200, B2/checkpointing/budgets visible in authenticated diagnostics. No additional application workspace was created.
- `b2-retention.json`: ordinary SQLite integrity **OK**, no foreign-key errors; original R1/R2 management/interface records preserved, including stored `GigabiEthernet0/1`; active release/artifact hashes verify unchanged at `0690966eb003499380e960a98d1e418f`.

TypeScript validation passed. `pip check` reports no broken requirements; dependency versions are unchanged from B1 (`langgraph 1.2.15`, `langgraph-checkpoint 4.3.0`, `langchain-core 1.6.11`, `langchain-ollama 1.1.0`). Whitespace checks passed with CRLF accounted for. No unrelated generation suite, production rebuild, repeated OCR suite or fresh browser visual acceptance was claimed.

### Rollback, working tree and next boundary

Set `COGNISHIELD_AI_ENGINE=langgraph_b1` (B1 orchestration) or `legacy` (pre-graph gateway) in root `.env`, stop the current standard launcher and restart `run_local.ps1`. No table deletion, conversation copying, knowledge pointer change or dependency downgrade is required. Added checkpoint tables remain dormant under rollback; existing public requests/results remain readable. The ordinary migration backup is for explicit recovery, not automatic rollback over newer user conversations.

The tree remains intentionally uncommitted. Prior Phase A/B1 modifications and untracked files are preserved. B2 adds `orchestration/memory.py`, `orchestration/investigation.py`, `tests/test_b2_agent.py`, `scripts/evaluate_b2_agent.py` and narrow extensions to the existing graph/state/adapters/model/verification, shared gateway/store/references/knowledge/diagnostics, existing knowledge worker and engine configuration. The SQLite diff includes the additive checkpoint migration and the three described reviewable turns. Audit artifacts live under the existing ignored `tmp/ai-intelligence-audit/`. No sibling source changed; 64 unreviewed reference templates remain unpublished, and isolated knowledge remains isolated.

**Stop at B2. Recommended B3:** expose ephemeral Studio editor/selection context to the shared orchestration with existing revision/lock checks; route generation solely through V9 and proposals solely through authorized proposal services; retain explicit Monaco Accept/Reject/Undo/Save. Extend document/network interpretation and structured memory only with stronger claim-level evaluations. If richer native task resume or multi-worker execution is introduced, add leases/idempotency/source revalidation before enabling it. Keep graph checkpoints separate from engineering approvals and published knowledge. Do not begin multi-file editing, autonomous collection/remediation, publication, deployment, ML or device execution as part of this completed B2 milestone.


## Phase B3 — shared Studio orchestration and guarded engineering — 2026-10-17

### Implemented scope and execution

B3 is enabled with root `COGNISHIELD_AI_ENGINE=langgraph_b3`. Both local Floating and Studio requests now enter the same existing `llm/orchestration/engine.py` graph through the unchanged `/api/v1/ai/conversations/{id}/turns` API. B1/B2/legacy rollback modes remain available. The initial dirty tree and all earlier handover history were preserved. No framework, V9 RAG, document pipeline, frontend/editor implementation or knowledge store was replaced. No dependencies/models were installed or upgraded.

The frontend path was traced: local `AnsibleChatPanel` captures `getEditorSnapshot()` immediately before `aiApi.turn`; `PlaybookEditor` obtains the actual Monaco model value, selection, document/model identity, version, buffer epoch, saved revision and dirty/read-only state. These existing wire fields remain unchanged. A contextual Studio graph turn receives that ephemeral snapshot; ordinary greetings/questions do not pass its contents to the response model. Normal-mode legacy adapters retain their existing paths; this milestone verifies local-lab operation.

The shared graph retains B2's read-only understanding, source selection, bounded retrieval, assessment and verification nodes. Studio adds explicit guarded paths:

- Contextual explanation/document reading → `read_studio_context` → existing `build_context` → existing gateway response service. The graph hands its prepared context back internally so extraction is not performed twice. Editor text remains separate from recorded network facts; selected text and unsaved contents retain source/line metadata.
- Modification → `authorize_engineering` → `propose_document` → `validate_engineering_result` → existing exact-base proposal response. The graph can coordinate **one** separately authorized proposal capability per turn. It cannot invoke save, buffer replacement, deployment, publication or arbitrary commands.
- New configuration → `authorize_engineering` → `plan_configuration` → `validate_engineering_result` → existing V9 interpretation/review response. Category/operation recognition, device resolution, parameters, schema/vendor checks, templates and native rendering remain inside V9. Interactive engineer selections and render confirmation retain the existing API/UI path; the graph never automatically confirms or renders a preview.

Authoritative reviewed selections remain in existing V9 sessions, with their inventory/release/session revision checks. The graph cannot silently replace them. Native output and genuine Ansible variants retain separate contracts and availability gates. There is no generic model-generated configuration fallback when V9 rejects a request.

### Exact modifications and ownership

- `orchestration/engine.py`, `state.py`: extend the same typed graph to server-bound `studio` identity, ephemeral editor/document contexts and engineering result channels. Routing constraints are enforced **before** any engineering capability call. The gateway consumes internal context/result handoffs once and removes them from response metadata. Floating remains restricted to the read-only adapter.
- New `orchestration/studio.py`: document identity/digest references, owner-bound prior-engineering lookup, natural proposal follow-ups, exact previous-diff explanation and returned-proposal identity/base checks. “Explain your modification” creates no new proposal; it reports whether the current buffer matches the original, suggested text or a changed buffer. Matching suggested text does not prove acceptance or saving. A different document requires clarification.
- `orchestration/adapters.py`: same LangChain adapter now takes a server-selected name/effect scope. Read tools retain their existing scope/budget. A separate request-local adapter exposes only `document.propose` / `v9.preview`, effect `propose`, max one call, only in Studio. Registry authorization, typed input/output, ownership, current role, resource and availability checks remain mandatory. Engineering failures propagate; they are not retried as another tool or downgraded to a model answer.
- `orchestration/memory.py`, `gateway_store.py`: optional compatible memory fields record editor identity/revision/digest and a completed engineering request reference. `result_for` resolves that reference only within the owned conversation. Buffer/proposal contents remain in the existing authoritative turn record and are excluded from checkpoints. No new table or migration was needed beyond B2. Resuming memory cannot replay a pending engineering action or treat a checkpoint as approval; new engineering work requires a new authorized user turn. General topic changes clear irrelevant engineering references.
- `gateway_services.py`: proposal context is fetched by an internal server-selected request reference and checked against the current document. It is supplied as **context**, separately from the latest instruction. It cannot select another owner's turn or transfer permissions. The public `TurnRequest` contract has not acquired an approval/profile/checkpoint field.
- `gateway_documents.py`: preserves exact anchors, structural checks, saved-revision checks before/after inference, artifact locks and proposal-only results. Generic model patches receive clearer anchor-copy instructions and at most one compute-only repair after an exact-anchor failure. Repaired patches pass the identical guard; malformed JSON/refusals do not receive unlimited retries.
- For a precise single-address substitution, B3 can use an exact user-literal patch after workflow routing. It requires valid IPv4 values, an unambiguous current-buffer anchor (or unique selected text), and a single requested change. A contextual correction can resolve its old address from a same-document owned prior proposal only when the current buffer exactly matches that original or suggestion. Prefix matches such as `.2` inside `.20` and ambiguous duplicate occurrences are excluded. This is text editing, not a replacement network-operation catalog or device validator. Other edits remain model-assisted. The path returns the same reviewable proposal, checks locks/revisions, and runs existing structural/Ansible validation where applicable; it does not change the editor or save. Metadata explicitly identifies `exact_user_literal` and zero proposal-model attempts.
- `gateway.py`: B3 integration, internal handoff consumption, authorization metadata on proposal/preview responses, existing response contracts and truthful action-state wording. Global read-only instructions are distinguished from scoped preservation such as “change BGP, but do not modify the OSPF section.” An explicitly requested new address missing from a returned B3 proposal is rejected.
- `gateway_diagnostics.py`, `.env`, `.env.example`: shared B3 selection and visible limits. Existing framework/provider pins are unchanged.

Floating retains the B2 **120-second**, 3-round/8-reader/3-routing-model-call budget. Studio graph runs allow **210 seconds** to accommodate the existing V9 worker (180 seconds) within the gateway's 240-second outer deadline; Studio allows one engineering capability call. Generic patch generation can make at most two model attempts within that deadline. Existing syntax/lint/compatibility/device-test/deployment scopes remain separate. No OS sandbox, device safety or native configuration parser certification was added.

### Confirmed failures and corrections

The real `qwen2.5:1.5b` patch initially returned `old_text: "BGP neighbor 192.0.2.2"`, copying user wording. The actual buffer contains `neighbor 192.0.2.2 ...`; the existing exact-base guard correctly rejected it. A bounded model repair also failed in one observed run, adding an unrelated hostname replacement while retaining the bad anchor. Those failures are retained in the audit artifacts; generic patch quality is not claimed solved by prompting alone.

A later valid-anchor proposal reused `.44` after the user explicitly requested `.55`. Prior-proposal context was separated from the latest instruction, an explicit-new-address guard was added, and unambiguous literal substitutions now use deterministic text patches. The final edit/correction cases produce exactly the requested one-token differences while retaining the complete OSPF section and all other lines. These deterministic successes are not counted as proof of improved free-form LLM patch reasoning. Larger refactors and ambiguous edits remain dependent on model quality and review.

The real V9 multi-operation prompt split into static-routing and BGP tasks but initially left operation IDs unresolved and overinterpreted parts of target prose. Its active ordinary release still reports an offline retrieval index that is not ready. The system correctly returned clarification; it did not fabricate operations or bypass V9. An initial evaluator incorrectly resubmitted empty operation IDs and received HTTP 422. The completed evaluation explicitly selected `configure_static_route` / `configure_bgp_neighbor`, the compatible test target and reviewed parameters through the existing review API. V9 revalidated them and returned both native drafts after explicit rendering. This proves the clarification/review path, not reliable one-shot recognition by the small model.

One explanation identified the actual marker, OSPF router ID and BGP neighbor/remote AS but omitted local AS. The evaluator now checks concrete quoted source values rather than requiring an incidental prose format; source completeness and rich reasoning are still model limitations. An intermediate retained B2 timeout test failed because a new explicit default timeout duplicated the test wrapper's override; the gateway now only overrides the deadline for Studio, preserving the B1/B2 call contract.

### Focused verification performed now

Final combined affected suite:

`backend/.venv-m0/Scripts/python.exe -B -m pytest backend/tests/test_b3_studio.py backend/tests/test_b2_agent.py backend/tests/test_b1_agent.py backend/tests/test_ai_intelligence.py backend/tests/test_shared_ai.py backend/tests/test_ai_review_network.py backend/tests/test_shared_ai_pdf.py -q -p no:cacheprovider`

**104 passed in 96.66s.** Two subsequently added rejection cases passed separately (**2 passed in 1.84s**): V9 template/parameter failures propagate without generic-generation fallback, and malformed model patches yield no proposal. Thus **106 unique focused cases across the final runs**: the retained 89 plus 17 B3 cases, not repeated-run totals.

B3 tests use the actual graph, registry and controlled SQLite with explicitly identified model/failure injections. They check actual original/suggested values, OSPF preservation, selected-text inclusion, previous-proposal explanation/correction, ownership/surface isolation, topic changes, no saved revision, one-call/idempotency behavior, read-only/role denial, invalid/exact anchors, bounded repair, missing requested values, document switches, stale revisions before and during inference, V9 dispatch/output-kind separation, model failure and Floating B2 investigation behavior. Existing B1/B2 regressions retain checkpoint/restart/cancel/authorization/evidence guarantees. No unrelated generation suite or OCR suite was repeated.

Actual local-model/application-route evaluation is in `backend/scripts/evaluate_b3_studio.py`. It uses the real authenticated FastAPI routes, existing Ollama providers, actual published V9 subprocess and ordinary SQLite backups in disposable DBs. It starts no second application server. Transparent response recording does not substitute model output. The compatible `B3-EDGE` IOS-XE 17.9 target exists only in that disposable fixture; ordinary R1/R2 software identities were not altered.

Final real cases (nine checks across three focused reports):

| Evidence | Verified result | Example latency |
|---|---|---:|
| `b3-studio-explain-general-knowledge.json` | Unsaved BGP/OSPF source explanation with actual marker/router ID/neighbor | 14.22s |
| same report | Greeting/arithmetic with an open file excludes editor context | 5.54s |
| same report | Published OSPF contracts + R2 actual saved capture; no generation/editor leakage | 2.07s |
| `b3-studio-edit.json` | Exact `.2 → .44` BGP proposal; unrelated OSPF/code unchanged | 7.83s including routing/import overhead |
| same report | Previous proposal explained, zero engineering calls, no new edit | 0.18s |
| same report | “that address instead” produces `.55` from the actual unchanged buffer | 0.27s |
| `b3-studio-generation.json` | Two-operation V9 clarification | 59.02s |
| same report | Explicit engineer selection/parameter correction revalidated as ready | recorded outcome |
| same report | Explicit native rendering returns static-route + BGP drafts, `saved:false` | recorded outcome |

These are single local samples, not a speed benchmark or a claim of Codex-equivalent intelligence. Exact-address proposals bypass proposal-model inference deliberately; general explanation uses the local chat model and V9 planning uses its existing model bindings. Earlier failed records/logs remain under `tmp/ai-intelligence-audit/` (`b3-studio-live*`, `b3-studio-edit-before-followup-fix*`, `b3-studio-edit-bounded-model-failure.json`). Older `.model.json` files can describe those recorded failed generic model attempts; the final literal-path proposal metadata is the authority for zero proposal-model attempts. All final focused report checks passed after the stated corrections; the initial one-shot recognition and generic patch failures remain limitations.

`b3-validation-boundaries.json` separately verifies that the actual published BGP schema rejects `remote_as: 0` and the genuine playbook renderer returns **HTTP 422** for the missing reviewed IOS-XE BGP Ansible variant. This does not certify playbook support, WSL containment or any unreviewed template. Native rendering stays independent.

### Standard runtime, preservation and UI verification limit

The standard launcher was refreshed once for B3: backend PID **28100**, frontend **5173**, backend **8000**, both HTTP **200**. `b3-runtime-final.json` records actual authenticated HTTP calls on that running server:

- New owned Studio verification conversation `b6217f342ceb44c4a116941f0448eedc`: a BGP proposal, explanation with **zero** engineering calls, and corrected `.55` proposal. Every editor identity/revision and exact suggested buffer was checked. The body uses the existing Monaco snapshot contract; no actual buffer acceptance or save was performed by this API check.
- Existing Floating verification conversation `154d5574ad714712bcde83206430d2e6`: exact R2 interface/address reread through the shared B3 graph, including the stored spelling `GigabiEthernet0/1`, with verified source values.
- Diagnostics confirm shared B3/checkpointing and independent read/proposal budgets. Three Studio turns and one Floating turn were intentionally retained in ordinary reviewable history; no ordinary test device or configuration was inserted.

Fresh browser interaction was attempted through the computer-use capability. It returned **“Local browser use is disabled in Work settings.”** No alternate browser automation bypass was used. Therefore fresh UI clicking/Accept/Reject/Undo is **not claimed verified in this continuation**. The existing frontend snapshot capture, diff review, stale identity/content/version checks, undo stops and explicit revision-checked Save were inspected and retained unchanged. Earlier actual UI evidence remains historical; the current checks establish actual API/graph behavior with the same snapshot/response contracts. TypeScript validation passed, and whitespace checks passed with CRLF accounted for. No frontend rebuild was needed for backend-only source changes.

`b3-retention.json` verifies SQLite integrity **OK**, no foreign-key errors, unchanged ordinary R1/R2/interface values, **zero** saved authoring revisions for `playbooks/drafts/b3-standard-runtime.cfg`, and unchanged published release/artifact integrity at `0690966eb003499380e960a98d1e418f`. Isolated knowledge remains separate; 64 unreviewed references remain unpublished. No sibling V9 source changed, dependency installation, collection, SSH/device execution, autonomous deployment or knowledge publication occurred.

### Rollback and remaining improvements

Set root `COGNISHIELD_AI_ENGINE=langgraph_b2` and restart root `run_local.ps1` to retain B2 Floating investigations while returning Studio to its prior gateway path. `langgraph_b1` and `legacy` remain additional rollbacks. No checkpoint tables/history need deletion and no knowledge release or dependency downgrade is needed. Optional added memory fields are compatible with the existing schema and are not engineering approvals. A failed/cancelled engineering turn requires a new user request; it is never automatically replayed from a checkpoint.

The worktree remains uncommitted. All prior Phase A/B1/B2 tracked/untracked work is preserved. B3 adds `orchestration/studio.py`, `tests/test_b3_studio.py`, `scripts/evaluate_b3_studio.py` and the documented extensions to existing graph/state/adapters/memory, gateway/store/services/documents/diagnostics and engine configuration. The ordinary SQLite diff contains the described retained verification conversation/turns and checkpoint metadata, not a new knowledge release or inventory migration.

Stop at this B3 scope. Remaining improvements are stronger free-form edit-intent/semantic validation, broader compound editor/document/network-request evaluations, more capable installed chat/vision models if separately chosen, and fresh browser acceptance when browser access is enabled. Genuine playbook variants/contained Ansible validation, live collectors, multi-worker recovery, repository-wide multi-file edits, SSH/deployment, autonomous remediation, ML and knowledge publication are not implemented or enabled by B3.


## Actual browser acceptance and corrective follow-up — 2026-10-17

This continuation was explicitly requested to verify both assistants through @Browser and fix reproduced discrepancies. Browser access is now available. Used the existing in-app browser, standard ordinary 5173/8000 application, existing administrator session, real qwen2.5:1.5b/nomic model services, SQLite records, uploaded reference PDF and V9 review endpoints. No alternate application copy/server, dependency/model installation, publication or device execution was introduced. The original tab was retained; a fresh verification tab recovered from its stale connection-error page. The standard launcher was initially stopped, then refreshed for the affected backend changes.

### Reproduced defects and fixes

1. **PDF question crashed before retrieval.** `contextual_route` indexed `query['device_refs']`, but the existing network router legitimately returns `{}` or a query without device references for a document/general-knowledge question. The exact browser question, “What does page 4 of this PDF explain? Describe its actual content.” raised KeyError in `understand_request`; the UI reported “Failed to fetch.” Use optional device references in the existing B2 coordination branches. No document service or RAG rewrite. Existing document pipeline and selected-page follow-ups now complete through the actual browser.
2. **Editor explanation attributed facts to the wrong protocol.** Real model output assigned OSPF's `192.0.2.1` router ID to BGP. A second observed response called AS `65000` a BGP router ID, changed the OSPF wildcard network to `/16`, and inferred runtime activation from an unsaved marker. Extended `orchestration/studio.py` with a narrow literal CLI-section evidence guard: explicit router-ID attribution, simple OSPF wildcard/prefix paraphrases and selected unsupported runtime claims. On a detected violation reconstruct a concise outline from the exact supplied sections/line ranges, retaining the real commands and markers and disclosing that device state is unknown. General explanation remains model-assisted; this is not a complete semantic verifier, operation recognizer, compatibility validator or parser for all vendors. Gateway adds section-scope instructions and honest verification coverage metadata. Final browser answer correctly separates OSPF/BGP and makes no runtime claim. One intermediate negative test caught sentence-ending punctuation in ID comparison; trailing prose punctuation is now handled and final tests pass.
3. **Multi-operation review deadlocked on an unresolved sibling task.** The frontend sent the complete selection; the API required nonempty operation IDs even for untouched, already-unresolved server tasks. Correcting the static-route task produced 422, leaving dirty state that disabled switching to the unresolved BGP task. `gateway_api.ReviewSelection` now permits an empty operation ID only for the worker's strict retention path. `local_providers/v9_worker.retained_unresolved_task` accepts only the exact existing unresolved server identity with unchanged target/parameters and no template; new, altered, forged or downgraded resolved tasks are rejected. Other selected bindings still pass V9 finalization/refresh, revision checks and ready-to-render gates. No sibling V9 source changed. `NativeGenerationReview` serializes unresolved IDs consistently; generic API validation arrays now display useful field messages instead of only “Unprocessable Content.” Actual browser corrections, task switching, adding OSPF and removing it all passed.
4. **Telemetry context became an unreadable JSON fragment.** The shared context budget cut large result objects into strings; deterministic answer release could only say the telemetry was partial, even though measurements existed. Budget projection now retains whole authoritative rows, preserves source provenance, marks truncation and leaves the authorized result unchanged. Verification confirms projected values are a subset of the real tool output. Measurement presentation includes interface identity and compact latest returned rows (up to eight rows/seven source-labelled fields), rather than hundreds of scalar rows. No measurements or units are inferred. Simulated/stale labels and missing-live-data conclusions remain explicit.
5. **Floating UI state/reachability.** The draggable launcher kept old screen coordinates after a resize and could become unreachable. Clamp it on mount/resize. Distinguish pending model discovery from confirmed Ollama unavailability. Restore owner/conversation-bound attachment badges on open/refresh/selection (latest five, matching the turn limit) and retain them after sending, so users can see continuing file context. Routing still excludes irrelevant attachment contents from a network/general answer. Narrow Studio layouts now retain a usable editor minimum width with horizontal pane scrolling instead of compressing it to zero. Cancellation wording now says response cancelled rather than claiming every stopped explanation was generation.

### Actual browser outcomes

| Interaction | Observed result |
| --- | --- |
| Floating: “What interfaces does R2 have?” | Exactly `GigabitEthernet0/0 — 192.168.1.251` and stored spelling `GigabiEthernet0/1 — 10.1.1.2`; no invented ports. |
| “What is the IP address of the first one?” | Correct R2 `GigabitEthernet0/0` / `192.168.1.251`. |
| R1 latest available syslog | Actual simulated warning at `2026-10-10T15:10:00Z`; identified as simulated. |
| R1/R2 investigation | Authorized inventory/topology/configuration/telemetry/syslog/incidents; no current failure/root cause asserted. Original telemetry-loss failure and corrected output recorded separately. |
| Greeting/arithmetic after investigation, and Studio with code open | Natural `1 + 1 = 2`, no unrelated configuration in either new answer. |
| PDF upload via actual chooser | `generation process.pdf`, 11 pages, 18,496 extracted characters, existing local OCR. Page 4 describes intent/parameter/template review; page 5 describes interpretation/targets/vendor templates. Real page citations and OCR/layout/coverage limitations; no source-ID/UUID answer. Page-5 prose remains broad/hedged. |
| PDF → R2 stored configuration topic switch | Actual simulated saved R2 capture, not a document answer or configuration generation. |
| Studio active unsaved BGP/OSPF buffer | Exact marker/router commands reached the assistant; final guarded explanation uses real lines and does not invent a BGP router ID. |
| Studio `.2 → .44` edit | Actual inline diff; OSPF/unrelated lines unchanged. Reject preserved original; subsequent Accept changed only the buffer; keyboard Undo restored `.2`. No Save was clicked. |
| Static route + BGP generation request | V9 produced two tasks with unresolved/misparsed details; manual review repaired them. The small model's one-shot interpretation is still imperfect. No generic generation fallback. |
| Review corrections/add/remove | Static destination `203.0.113.0/24` and next hop retained; BGP fields loaded and remote AS corrected to `65001`; adding OSPF loaded Process Id/Router Id/Interfaces; removal restored BGP controls/values. |
| Compatibility/output safety | Ordinary R1 IOS `16.2.3` has no compatible published binding for these operations; explicit compatibility issue and Confirm & generate disabled. This browser run does not establish successful verified output rendering. Invalid `remote_as:0` was entered, but compatibility rejection preempted schema validation; do not count that UI attempt as a schema rejection proof. |
| Models and restored UI | Chat selector offers qwen only, not nomic or LightOnOCR; initial state says Checking local model. Attachment badge survives reopening/sending; resized launcher opens successfully. |

The first native typing attempt dropped automation keystrokes. It was cancelled and replaced using browser paste; the exact rendered buffer was verified before the successful edit/explanation checks. This is not counted as an application extraction defect. The verification buffer is an unsaved editable copy of README, named `playbooks/drafts/copy-1792198254966-README.md`; it contains native CLI despite its test-only `.md` extension. Existing user drafts were not overwritten.

### Focused verification and retained evidence

Final affected backend command: `backend/.venv-m0/Scripts/python.exe -B -m pytest backend/tests/test_b3_studio.py backend/tests/test_b2_agent.py backend/tests/test_ai_review_network.py backend/tests/test_studio_multi_review.py::PartialSelectionTests -q -p no:cacheprovider` — **55 passed, five subtests passed in 20.96s**. After the final concise measurement rendering change, affected network tests alone: **14 passed in 1.60s** (included within the 55, not additional unique cases). TypeScript `tsc -b frontend` and CRLF-aware `git diff --check` passed. A restricted initial pytest invocation stalled without results and was stopped; the documented successful runs used the authorized runtime outside that restriction. No unrelated generation/OCR suites were repeated.

Real browser evidence under ignored `tmp/ai-intelligence-audit/browser-20261017/`: PDF/review/explanation screenshots and DOM captures, final turn report and retention checks. Console errors were inspected during a transient frontend reconnect; none were returned then. An early file named `review-deadlock-before.dom.txt` was captured after HMR had already dismissed the modal; it is not proof of the failure. The failure is established by the actual browser 422/disabled controls and corresponding source/API validation contract; final review captures establish recovery.

Ordinary reviewable verification conversations intentionally retained: Floating interface/investigation `7496253c79b24323b42687202e84e070`, Floating PDF/topic switch `349dde951c444ac780a6be61901f9626`, Studio `a4b5b182-f066-401b-a8d9-72eda853d856`. The original PDF is attached only to its owned Floating conversation. Backend restart/refresh retained histories and active unsaved buffer. No existing inventory/configuration records were changed, no engineering artifact was saved, and no ordinary/isolated release was published. SQLite and active-release preservation results are in the retention artifact.

The worktree remains uncommitted, including all earlier B1/B2/B3 files. This continuation changes only the documented shared routing/grounding/network projection/partial review adapters, affected tests, and the existing frontend controls/layout. Engine remains `langgraph_b3`; existing B2/B1/legacy rollback flags remain available. Rolling back only the engine will not undo UI or reader fixes. No automatic commit.

Remaining limitations: small-model free-form semantics/refactoring are not certified; the new editor fact guard is deliberately narrow and vendor CLI outlines are not a full semantic parser. Ordinary R1/R2 platform compatibility and reviewed playbook availability remain unchanged/gated. Simulated historical observations do not prove live connectivity; no device action was attempted. The New File toolbar also targeted a non-existent drafts directory when an unsaved generated draft was selected; this non-AI file-creation issue was bypassed with Edit a copy and is not claimed fixed. No new framework milestone is started. Next work should be user-directed, prioritizing a stronger general editor/document claim verifier and the remaining file-creation UX issue, without weakening V9 or review boundaries.

Final runtime evidence: backend PID **9272**, standard 5173/8000 launcher left running. The final actual browser investigation completed two read rounds across six sources; gateway verification checked **375 scalar values** against authorized results. The compact measurement display includes the actual simulated CPU `26.0`, memory `44.0`, errors `2.0`, and original traffic values, keeping interface names distinct and explicitly omitting older/excess fields. The PDF badge remained visible after sending. A narrow-layout check confirmed the launcher inside the viewport and a 260px editor with a horizontal pane scrollport; the temporary viewport override was reset. No new generation was rendered. `retention.json` confirms SQLite integrity OK/no foreign-key errors, zero saved test-file revisions and unchanged ordinary release hash/44 operations/78 bindings.


## Post-B3 stabilization and engineering quality gate — 2026-10-17

This continues the preceding actual-browser acceptance; Phases A/B1/B2/B3 remain implemented. Inspected the initial empty Git index, tracked/untracked changes, additive schema code, dependency locks, previous audit records and mandatory repository instructions. No reset, commit, dependency/model installation, sibling V9 edit, knowledge publication, device operation or Phase C implementation occurred. The checkpoint inventory is in `docs/POST_B3_CHECKPOINT.md`.

### Confirmed defects and corrections in this continuation

1. **New File targeted a nonexistent unsaved-draft directory.** Reproduced in the actual toolbar with `playbooks/drafts/copy-1792198254966-README.md` selected: New File produced zero filename inputs. `workspaceCreation.ts` resolves against the existing authorized workspace listing, walks to a listed writable ancestor and falls back to listed `playbooks`; it does not guess directory identity from a dot in the name. `AnsibleFileTree` expands the entire creation branch, including the virtual Project group, and opens the successfully created file through its existing `onFileOpen` service. Existing create APIs still enforce role/path/overwrite restrictions. Browser verified the input with a collapsed Project and a missing draft directory, actual empty-file creation/opening, unsaved editing and explicit Save. No backend path validation was weakened.
2. **Literal address edit incorrectly counted substrings.** The mixed-category buffer contained BGP neighbor `192.0.2.2` and OSPF router ID `192.0.2.20`. The old `content.count(old)` treated the address as ambiguous and fell back to a model patch, which failed its exact anchor. The buffer was preserved. `gateway_documents.literal_address_patch` now finds whole-address matches and uses a unique complete source-line anchor; selection replacement also respects whole-address boundaries. Actual retry returned the exact `.2 → .44` proposal, preserving `.20`, interface address/mask, OSPF and static route. Reject, Accept and keyboard Undo all passed in Monaco. No direct buffer overwrite or automatic save was introduced.
3. **Broader, deliberately bounded editor evidence checks.** `orchestration/editor_facts.py` extends the existing Studio guard with selected literal IOS-style local AS, neighbor/remote-AS attribution, interface address/mask association, static-prefix/next-hop pairs and operational-state assertions. The previous OSPF/BGP router-ID and wildcard checks remain. Contradictions reconstruct numbered literal source commands; correct prose, advice, uncertainty and uncovered semantics remain model-assisted. A follow-up test caught the need to distinguish a literal mask argument from an interface address, and this was corrected before final testing. This is not a generic multi-vendor network parser, effective-policy validator or proof of reachability. Coverage metadata now states these limits explicitly, preserving the existing response field.
4. **A caution about missing live evidence hid stored records.** The exact browser investigation ending “Distinguish missing live evidence from a confirmed fault” set every NetworkQuery to `live:true`, selecting unavailable live collectors instead of the requested available records. `gateway_network.route_network` now excludes explicit absence/negative-live phrases when calculating this query modifier. Positive requests such as “Show R1 live telemetry and identify missing live evidence” remain live requests. Capability routing, authorization and provenance are unchanged. The same actual question after restart returned authorized planned topology, exact interfaces, saved captures, simulated telemetry/syslogs/incidents and an explicit unconfirmed-root-cause conclusion.
5. **Rendering scope and a published-template issue.** The preview now says “V9 contract validation passed” and discloses remaining CLI/device review. The actual Cisco static route output `ip route 203.0.113.0/24 10.1.1.1` exposed a published-template semantic issue. Cisco's IOS-XE reference specifies separate prefix/mask arguments: https://spg.xgslb-v3.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-routing/b-ip-routing/m_iri-iprouting.html . A narrowly scoped preview warning identifies that observed Cisco CIDR-route form. The immutable template/release was not changed, suppressed or republished. An alternative `add_default_route` selection was correctly rejected for an unsupported/unreviewed resource-policy profile; no fixture facts were invented to clear it. The published binding's platform match and successful rendering are not evidence of device-ready static-route syntax.

### Actual browser/application verification performed now

Used the existing IAB session and code on standard 5173/8000. Reproduced New File first on ordinary data, cancelling the input without creating a file. For mutating acceptance actions, stopped the ordinary launcher and used **one disposable SQLite backup** on those same ports, not another application copy or concurrent port pair. The existing controlled `B3-EDGE` fixture (IOS-XE 17.9/C9500) was inserted only in this backup. Its actual DB path was asserted before mutation. Root `.env`, ordinary R1/R2 identities, existing records and ordinary/isolated knowledge authority remained intact. Acceptance DB and evidence are retained under ignored `tmp/stabilization-20261017/`.

| Case | Actual outcome |
| --- | --- |
| Mixed interface/OSPF/BGP/static source explanation | Real qwen2.5:1.5b response exercised the guard; returned exact source commands, AS values, router ID, marker and source lines, with unknown device state. Model prose itself is not certified. |
| Editing mixed buffer | Initial substring defect reproduced and rejected safely; final whole-address retry succeeded with `exact_user_literal`, zero proposal-model attempts. Reject preserved `.2`; Accept changed only neighbor to `.44`; Undo restored `.2`. |
| Explicit persistence | Empty New File revision 1; exactly one explicit Save made revision 2 with 331 characters in acceptance DB. Native output drafts have **zero authoring revisions**, even after explicit opening in Monaco. Ordinary authoring data unchanged. |
| V9 clarification and correction | Real V9/Ollama split the request into two unresolved tasks, requiring manual operation/target correction; one-shot recognition remains imperfect. Static route and BGP schemas loaded dynamically. Compatible published templates 24/12 selected. `remote_as:0` rejected with “0 is less than the minimum of 1”; correction to `65001` revalidated. |
| Explicit native rendering/opening | Confirm & generate rendered two outputs; Confirm & open created two unsaved Monaco tabs. BGP contains `router bgp 65000` / `neighbor 192.0.2.2 remote-as 65001`. Static output has the documented syntax warning. No generic generation fallback, playbook claim or deployment. |
| Studio unrelated conversation | Real model answered `7 + 5 equals 12`, with editor/attachment/history excluded from that turn. |
| Floating exact facts and follow-up | Actual R2 `GigabitEthernet0/0 — 192.168.1.251`, stored spelling `GigabiEthernet0/1 — 10.1.1.2`; “first one” resolved to `.251`. No invented interface inventory from topology. |
| Floating investigation and restart | After the query-modifier correction: six authorized tools, one retrieval round, eight evidence sources, **304 scalar values verified**, stored/simulated origins, stale/truncated-data limits and no confirmed current fault/root cause. Server checkpoint restored after the controlled restart. |
| Owned PDF context | Existing extracted page 4 reached real qwen and the answer described interpretation/category/template/parameter controls, citing `generation process.pdf, page 4`. No UUID/source-ID list. OCR/layout/selected-context limitations shown. Wording such as “generate a network prompt” remains imprecise model interpretation; this is not comprehensive diagram understanding. |
| Isolation and permissions | Floating and Studio used separate owned conversations. General Studio turn contained no irrelevant context. Retained actual-registry/SQLite regressions cover role/surface/owner denial, checkpoint isolation, stale revisions, no unauthorized generation/editing, V9 errors and bounded calls. No broader permissions were granted. |

The V9 planning graph took **44.105s** in this sample. The final deterministic six-source investigation graph took **198.62ms**, excluding browser overhead; no chat synthesis call was needed for exact recorded facts. General/document/explanation turns used actual qwen2.5:1.5b; network semantic routing reused the existing local embedding provider and deterministic readers. Exact editing intentionally uses literal proposals. These are functional samples, not a latency benchmark or a claim of Codex-level intelligence. No new model was enabled, and OCR-only/embedding-only models remain excluded from conversational selection.

### Focused tests run in this continuation

- Initial affected suite: `pytest backend/tests/test_editor_facts.py backend/tests/test_b3_studio.py backend/tests/test_b2_agent.py backend/tests/test_ai_review_network.py backend/tests/test_studio_multi_review.py::PartialSelectionTests -q -p no:cacheprovider` — **58 passed, 20 subtests passed in 19.29s**.
- After final claim-mask and literal-anchor corrections: `pytest backend/tests/test_editor_facts.py backend/tests/test_b3_studio.py -q -p no:cacheprovider` — **24 passed, 19 subtests passed in 14.14s**.
- After the reproduced missing-live-scope correction: `pytest backend/tests/test_ai_review_network.py -q -p no:cacheprovider` — **15 passed in 1.37s**.
- These overlap: **60 unique backend test cases**, not 97 separate cases. No unrelated generation or OCR suite was rerun. An initial standalone new-test collection failed because its import path depended on another test; the test now establishes its backend import path and passes standalone.
- `node --test frontend/tests/workspaceCreation.test.cjs` — final **4 passed**, including virtual-group expansion. TypeScript `tsc -b frontend` and CRLF-aware `git diff --check` passed after final frontend changes.

Browser evidence includes `new-file-fixed.png`, `published-quality-warning.png`, the invalid-AS/preview/edit/undo/investigation DOM captures, `gateway-results.json`, `editor-persistence.json` and ordinary before/after fingerprints. Reused earlier Phase A–B3 test evidence is historical and is not counted as rerun now. Existing privacy-bearing SQLite, conversations, binaries and generated audits are excluded from the source checkpoint.

### Remaining gates and exact next milestone

The stabilization fixes and browser workflows above are implemented. The published Cisco static-route semantics issue is an explicit **remaining knowledge-quality gate**, requiring separately reviewed authoring and publication; this task did not authorize changing immutable knowledge. The alternative default-route resource-policy rejection, ordinary IOS-version compatibility, missing reviewed Ansible variants and contained validator remain gates. The literal fact guard is partial; broader CLI/vendor semantics, ACL policy meaning, unrestricted model refactoring and comprehensive visual interpretation remain uncertified. Historical/simulated data does not prove live connectivity.

Next milestone: review the curated source index and approve a source-only commit if desired, then explicitly scope a knowledge-quality correction of the defective published route binding and its regression before any Phase C enablement. Phase C requires separately approved objectives, verified output/compatibility evidence, appropriate containment and unchanged authorization/review boundaries. Do not begin autonomous operations, deployment, multi-file editing, framework redesign, another RAG system or automatic template publication. Existing `langgraph_b2`, `langgraph_b1` and `legacy` engine flags remain available for orchestration rollback; they do not undo source/UI fixes or migrate databases backwards. No commit was made.


Final restoration/checkpoint: the ordinary launcher is left running on **5173/8000**, backend PID **27496**. The one acceptance composition is stopped; its backup and reports are retained, not committed. Restored the original Studio/Floating selections and closed only the three acceptance-created editor tabs; the original unsaved `UNSAVED_BROWSER_MARKER` buffer remains intact. The final ordinary New File input was visible and cancelled, creating no ordinary file. Ordinary inventory/interfaces/configuration/authoring fingerprints match the pre-acceptance snapshot; SQLite integrity is OK with no foreign-key errors. The ordinary release pointer and manifest hash still identify `0690966eb003499380e960a98d1e418f` / `7111628327551dfa424cd11ea40c5a379544b69c2ffab154ed29c773727ad9c9`. React logged transient dependency-array-size warnings when the development hot-refresh replaced the TreeNode effect during editing; a deliberate final reload preserved the buffer and produced no new console errors. This was not an error in the final stable hook layout.

The curated **52-file source/test/configuration/documentation checkpoint is staged but uncommitted**. The working tree intentionally remains dirty only for local `.env` and the existing runtime SQLite database; neither is staged. Ignored audit/SQLite/knowledge artifacts remain local. The staged manifest and source patch are in `tmp/stabilization-20261017/`; `git diff --cached` is the review authority. All previous uncommitted source work and handover history are included, with no unrelated sibling changes. No automatic commit or Phase C work.


## Phase C1 — centralized development foundation — 2026-10-17

C1 minimal gate verified before C2. Phase C changes remain unstaged beside the preserved 52-file checkpoint. Explicit local-lab server flag `COGNISHIELD_DEV_SIMULATION=1` and server attachment are required; disabled by default. `COGNISHIELD_DEV_STATE` selects a workspace-local atomic JSON file (default `tmp/development-network/state.json`). No LLM/profile/upload can enable it, and production never falls back to scenarios.

New `local_providers/development.py`, six versioned definitions under `backend/development/scenarios/`, authenticated/admin `development_api.py` and `DevelopmentNetwork.tsx` provide central inspect/select/edit/duplicate/import/export/reset controls, logical time, revision/epoch checks, bounded source dependency DAGs, current running configuration and capture history. Modeled interface events update configuration, interface/link/probe/counter/event observations atomically. Bringing admin state up leaves recovery unknown until observed. Derived alerts retain their dependencies. Existing DatabaseManager dataclasses/read methods, inventory_snapshot, NetworkReader, JsonObservations monitoring and v9_studio inventory are adapted; ordinary inventory/configuration data is not copied or modified. Current configuration capture goes to scenario history, with existing snapshot UI projections. No new SQLite schema, production SoT, RAG index or device tool.

Focused verification: six C1 cases pass in 1.32s; affected C1/B3/network run **42 passed in 15.04s**, overlapping those six (not 48 unique). TypeScript passed. Initial failures found invalid UNKNOWN fixture dependencies, a legacy anonymous-viewing dependency that needed the existing strict require_ai_user check, and test-harness import/authorization mistakes. Failed summary retained in `tmp/phase-c/c1-initial-failures.json`; actual deterministic responses and reruns in JSONL/JUnit.

Actual browser acceptance on the same 5173/8000 code and single existing disposable database: selected FAULT-IFDOWN-001 in developer UI, actual Floating gateway returned R2 GigabitEthernet1/0/1 10.23.12.2, management 192.0.2.20 and Loopback0 198.51.100.2. Real qwen2.5:1.5b answered 7+5=12 without network tools. C1-007/C1-008 PASS in c1-browser-results.json; scenario-manager screenshot/DOM retained. Existing local embedding/model configuration reused; no install/download. The indicator labels development authority. Exact facts use authorized deterministic readers.

Permanent sanitized cases begin in `docs/evaluations/phase_c_cases.json`; ignored `tmp/phase-c/` retains timestamped execution evidence, failures, source revision, scenario identity/revision, actual responses/tools, outcomes and runtime distinctions. Ordinary SQLite, release artifacts, credentials and private transcripts are excluded. Initial network is bounded two-router development data, not a physical emulator; arbitrary protocol dynamics, multi-process writers and universal vendor event edits are not claimed. C2/C3 are not implied by C1. Next: same-session cascading V9 clarification, then scenario-aware hypotheses through the existing graph.


## Phase C2 — cascading V9 clarification — 2026-10-17

C2 API and actual-browser gate passed before C3. Conversation corrections now update the same owned V9 session using V9's catalog selection, parameter extraction and task finalization; no new recognizer/schema engine. A narrow assignment-wording adapter maps user field `to` phrasing into V9's field-scoped grammar, preserving explicitly quoted punctuation. Rejected V9 interface candidates remain inspectable and are presented as not recorded on the selected target. Reviewed selections remain authoritative; empty task sets are rejected. Scenario refresh clears prior device scopes/confirmations, re-resolves inventory, and atomically updates session inventory hash/revision. Rendering retains before/after source/revision checks.

The actual browser initially routed a named R2 network action into an unrelated README edit. It was rejected without accepting or saving. The graph now redirects that misclassification to V9 when the request names inventory and does not refer to the editor. Initial correction also lost description under V9's strict field grammar; the assignment adapter fixes that. Failed executions remain in tmp/phase-c. C2 fixtures revision 2 explicitly model the existing V9 C9300/IOS-XE 17.9 physical_interface_v1 profile with planned capability/source facts. These are modeled development assumptions, not hardware certification or ordinary inventory changes. Persisted scenarios are never silently upgraded: explicit Reset loads the bundled revision.

Actual HTTP/local-qwen run http-C2-20261017-150921-3b1ed7 verified target/interface correction, native rendering, stale confirmation 409, explicit rebase, shared-name identity rebinding, multi-operation correction, stale predecessor parameter rejection and incompatible vendor/platform blocking. Earlier harness records shared nested parameter references with later corrections (notably the missing-AS response); their recorded status/issues remain useful but those mutated parameter dictionaries are not reliable original response captures. The harness now deep-copies response/selection values. Original failed runs are preserved, not rewritten. No inflated rerun counts.

Actual browser c2-browser-results.json/DOM/screenshots: `Configure interface GigabitEthernet1/0/1 on R2` asks for operation; `Sorry, I meant R1. Set its description to Uplink` selects R1 and retains exactly Uplink while rejecting the R2 interface. Choosing recorded R1 GigabitEthernet0/1 and explicit confirmation renders description Uplink; explicit opening creates an unsaved Monaco tab. Adding BGP asks only remaining remote AS after other inputs; correction preserves the interface task. Replacing BGP with OSPF replaces its fields. Editing the centralized development vendor to Huawei UNKNOWN blocks published-template compatibility; no bypass. Reopening review after scenario change initially left Confirm enabled until backend rejection; it now checks scenario revision at mount and disables confirmation pending explicit revalidation. Developer Monaco uses the supported editContext:false option for its accessible input.

Focused runs now: affected Phase C/B3 **28 passed in 21.87s**; final Phase C/partial-selection **8 passed + five subtests in 3.97s**, plus new candidate-projection test **1 passed in 0.63s** (overlapping tests, not additive unique totals). TypeScript passed. A restricted-sandbox run failed accessing disposable temp directories and was rerun outside that restriction; its failure XML is retained separately. Fresh built-in browser check at localhost:5173 succeeded, followed by acceptance in existing signed-in 127.0.0.1 tab. No browser-access limitation remains at this checkpoint. Staged 52-file patch hash still matches baseline. All Phase C source remains unstaged/untracked. C3 starts only after this gate.


## Phase C3 — bounded evidence-driven investigation — 2026-10-17

C3 extends the existing B2/B3 graph after C2 acceptance. New orchestration/scenario_reasoning.py supplies typed hypotheses and exact prefix/complete-table calculations over existing authorized results. Existing investigation.py/engine.py coordinate conditional retrieval, reference resolution, assessment and release; state.py/gateway_routing.py/memory.py allow the existing network.state capability alongside other domains. Gateway factual verification remains the release gate. Owner-bound checkpoints retain references/open questions and always reauthorize/retrieve after restart; no raw result or scenario authority is restored as fact. There is no new RAG, model registry, SQL schema or side-effect tool.

Current, fresh scenario interface observations, explicit path/probe scope, running configuration and routes can establish a cause within the modeled network. Healthy scoped tests do not become universal health claims. Route absence is a complete-table fact with a strongly supported explanation, not proof of all forwarding behavior. Mixed revisions, stale/partial decisive state and conflicting observers prevent confirmation. Agreed prefixes remain usable when administrative observations disagree: the final conflict example keeps shutdown plausible while contradicting subnet/missing-route explanations for the successful directly connected test. Repeated derived incidents do not add independent causal votes. Missing decisive data retains useful hypotheses/next reads. Source assertions such as “interface is back up” cannot modify the scenario; changing the source revision triggers fresh assessment.

New findings are concise in Floating Chat, with existing source citations and a persisted, escaped Markdown Retrieved records disclosure. Studio reuses the same diagnosis and renders its recorded context below it; no editor write/generation was invoked by its investigation. The evidence projection now includes structured interface/routing/probe values. Current simulated running configuration and historical captures are labeled separately, including actual record timestamps; current-only queries do not silently substitute saved history, unavailable current sources stay unavailable, and configuration text is redacted. The manager/readers and existing capture workflow still share one revision. No ordinary data copy or device collection.

Actual-model HTTP results are in http-C3-20261017-152511-f67a0f/results.json: all six identical-prompt scenario expectations passed, followed by evidence/other-sources/routing-alternative/change-history/likely-cause/next-check/source-revision/R2-scope/topic-switch cases. Initial full investigations used seven tools/two rounds, roughly 206–1,425 ms HTTP; semantic local nomic embeddings and deterministic verified calculations supplied these results, with zero conversational synthesis calls. Actual qwen2.5:1.5b answered unrelated arithmetic with 12 in 6,883 ms using zero network tools. The staged B3 assessor remained unconfirmed on those identical records; this is an assessment comparison on matched returned data, not a full old-application latency benchmark.

Actual browser: healthy scoped success; shutdown on R1 GigabitEthernet0/1 with failed scoped test and confirmed simulated cause; conflict withholding diagnosis; UNKNOWN withholding failure/diagnosis and offering decisive checks; prior investigation restored through a controlled server restart; fresh evidence after scenario revision changes; full record disclosure; and Studio read-only investigation with the unsaved description buffer intact. Browser files include c3-browser-{healthy,shutdown-rerun,unknown,conflict-final,restart-followup,studio-investigation}.dom.txt and screenshots. The first c3-browser-shutdown capture actually remained HEALTHY because Reset used active state instead of the dropdown choice; its FAIL record is preserved. The control now resets the dropdown selection, with active-scenario indicator verified before the successful reruns.

Focused regression commands/results: C1/B2/B3/network/partial-review run **68 passed + five subtests in 28.32s**; final source-scope/network run **30 passed in 6.86s**; final C3 competing-hypothesis/edge/restart cases **six passed in 4.97s**. Deduplicated union is **72 backend methods**, counting the renamed C3-007/C3-014 missing-prefix case once, not summing reruns or counting six assertions as extra methods. TypeScript passed. Detailed original failures and subsequent corrections are retained in ignored XML/JSON. Failures included harness field paths/mock return types, the internal “Latest request” label accidentally triggering latest-only one-row filters, incomplete conflict alternatives, the dropdown reset mismatch, and restricted temporary-directory permissions. Retrieval now uses the neutral Follow-up label, staged investigation reads and a bounded structured-state allowance. No unrelated generation/OCR suite was repeated.

Permanent sanitized specifications: docs/evaluations/phase_c_cases.json. Curated scope/results/rollback: docs/evaluations/PHASE_C_RESULTS.md. Raw executions, failed results, screenshots, baseline source patch and preservation fingerprints remain ignored in tmp/phase-c. The evaluator records actual requests/responses, scenario revisions, code HEAD, model/tool counts and latency; new runs additionally fingerprint dirty source. Earlier runs identify HEAD and retained source changes but do not have that later source digest. No token/credential is recorded or staged.

Preservation checks now confirm ordinary inventory/interfaces/config_snapshots/authoring_revisions fingerprints unchanged, SQLite integrity OK/no foreign-key errors, ordinary active release 0690966eb003499380e960a98d1e418f / manifest SHA7111628327551dfa424cd11ea40c5a379544b69c2ffab154ed29c773727ad9c9 unchanged, and the original **52-file staged patch SHA256 d6aa68e47ae3b44449d1f832404ad925a373791b845ec064d067b8e8b028d7f8** unchanged. Phase C changes are unstaged/untracked; local .env/runtime DB remain excluded. No automatic commit, publication, dependency/model installation, sibling V9 modification or device action.

The completed scope is the bounded six-scenario observation model and declared two-ended paths. Arbitrary multi-hop/ECMP/VRF/ACL forwarding, recursive routes, protocol state-machine simulation, congestion causation and universal vendor semantics remain unsupported rather than asserted. OSPF/BGP/service-outage expansion requires reviewed typed observations and permanent cases. JSON persistence has one application writer; multi-process arbitration is not certified. Existing published Cisco CIDR static-route syntax remains a separately reviewed knowledge-quality gate. Verified Ansible variants/containment gates are unchanged.

Operational rollback: disable COGNISHIELD_DEV_SIMULATION and restart to return to ordinary sources without migration. The developer interface cannot enable the server flag. Default local scenario state is tmp/development-network/state.json; acceptance reused tmp/phase-c/browser-state.json and the single existing acceptance database on 5173/8000. B1/legacy engine options remove advanced investigation behavior; B2 also shares the new C3 assessment. Next milestone is user-directed review of the unstaged Phase C package and, if desired, separately scoped protocol/policy scenarios or knowledge-quality authoring. No autonomous operation or publication is implied.


### Final Phase C handoff quality gate

Final boundary inspection found that gateway_handoff.accept/history_context still looked up ordinary SQL device IDs, rejecting simulated 9101/9102 despite authorized scenario evidence. They now use the existing inventory_snapshot authority, check development-to-ordinary crossings and current source revisions, and withhold stale observation payloads even when preparation occurs after the original source turn became outdated. Authorized shared scenario configuration survives engineer projection; private ordinary snapshot filtering remains intact. No action/permission is transferred.

Focused new scenario handoff plus existing intelligence regressions: **17 passed in 4.61s**. Final shared-scenario/private-owner and stale-before-preparation checks: **two passed in 2.34s** each, overlapping. Final C3 hypothesis/edge cases: **six passed in 4.97s**. The final deduplicated affected union is **89 backend test methods plus the five separately reported subtests**, counting renamed/overlapping cases once. TypeScript remains passing. Original failures and all reruns remain retained.

Actual browser C3-018: prepared and reviewed R1's simulated current configuration evidence, explicitly opened it in a distinct Studio conversation, and verified the action remains an unsent draft. Read-only SQLite confirms **zero submitted engineering turns**; no file change/save/generation occurred. Evidence: c3-browser-handoff-{review,accepted}.dom.txt/.png and c3-handoff-browser-result.json. Current configuration reading also returned the actual shutdown text with timestamp and current simulated running label. Final conflict response kept shutdown plausible while rejecting subnet/missing-route alternatives using agreed facts. The visible original UNSAVED_BROWSER_MARKER buffer remained intact, and only the acceptance-generated description tab was closed.


Final restoration: ordinary launcher is running on **5173/8000**, backend PID **1076**. The single acceptance composition is stopped. Default development authority is disabled; enabling COGNISHIELD_DEV_SIMULATION=1 and restarting activates the central scenario panel. The original unsaved UNSAVED_BROWSER_MARKER buffer is intact, the acceptance output tab is closed, and no handoff request remains in the ordinary composer. All three checked acceptance-only conversation IDs are absent from ordinary SQLite. The final ordinary authority fingerprints/integrity and actual release manifest hash verify unchanged. The source-only 52-file index remains untouched; Phase C remains unstaged/untracked, with no automatic commit. One retained Vite websocket error belongs to the earlier controlled server reconnect, not a browser permission failure; the final ordinary page was deliberately reloaded and verified.


## Phase D execution started — 2026-10-18

Authoritative specification: CogniShield_Phase_D_Comprehensive_Implementation_Plan.md. Execution is IN PROGRESS, not complete. See evaluations/PHASE_D_RESULTS.md for actual stage gates, original failures, reruns and remaining work. D0 snapshot verifies the protected 52-file index hash, active release artifacts and ordinary SQLite integrity. No source was staged/committed and no ordinary knowledge was activated. Current work reuses existing V9 authoring, shared graph and Monaco renderer. Fresh browser capability succeeds; stopped local services were restarted on 5173/8000 and installed Ollama on 11434 without model downloads. Original raw failures remain under tmp/phase-d/.

## Phase D implementation checkpoint — 2026-10-18

**Phase D remains INCOMPLETE. This is an implemented, verified partial checkpoint,
not final acceptance.** Latest user explicitly authorizes validated knowledge
publication; the reason ordinary activation has not happened is missing semantic
evidence, not missing authorization. Preserve all previous staged/Phase C work.
Full stage ledger, commands, limitations and rollback:
[evaluations/PHASE_D_RESULTS.md](evaluations/PHASE_D_RESULTS.md).
Curated actual model/browser review:
[evaluations/phase_d_execution_review.json](evaluations/phase_d_execution_review.json).
All 141 rows: [coverage matrix](evaluations/phase_d_vendor_coverage.json).

### Implemented changes and integration

- **D0/D6:** `backend/scripts/phase_d_audit.py` captures the protected index,
  read-only table hashes/integrity, active release artifacts and audited source
  hashes; immutable timestamped JSONL/individual execution records preserve
  failures. `evaluate_phase_d.py` runs real model routing and authenticated shared
  gateway evaluations in one existing acceptance database. Permanent cases:
  `phase_d_cases.json`, 52 exposed regression prompts, eight fresh untuned prompts
  and explicit knowledge/UI cases. Source selection, model interpretation,
  deterministic calculations and synthesis quality are separate measurements.
- **D1:** `phase_d_knowledge.py` uses existing authenticated V9 authoring services
  against `tmp/phase-d/acceptance-knowledge`. Cisco/Huawei route add/remove now
  use existing address/mask derivations; root canonical-prefix validation rejects
  host bits and malformed inputs. Cisco IS-IS interface attachment/circuit type
  and context are corrected, with existing NET/process prerequisites explicit.
  The three management operations are reconstructed through authoring with six
  bounded parameters, category membership and Cisco IOS-XE 17.9 bindings. No
  isolated database/release/pointer or VLAN/lab_label contract was imported.
  Nine existing editable references are synchronized and still labeled drafts.
  Reference rebuilding now refuses to overwrite an existing reviewed index.
  `knowledge_lifecycle.py` preview reuses pure V9 derivations; its candidate
  playbook-freeze snapshot no longer re-enters its already-held authoring lock.
- **D2:** Existing central scenario manager/readers remain authoritative in
  explicitly enabled development mode. `development/network_model.py` adds
  typed bounded multihop/recursive-route, ECMP, VRF/leak, ordered IPv4 ACL,
  OSPF/BGP observation and metric/counter calculations. Unknown/partial/stale
  evidence remains qualified; healthy protocol state does not prove packet
  forwarding. `development/examples.py`, three new bundled JSON scenarios and
  regenerated schema provide multi-vendor fixtures. Existing monitoring and
  authorized network readers share those projections, without ordinary SQL
  inserts. Authenticated schema/CLI authoring extends the existing controls.
  Exact locations and limits: [scenario authoring](development/SCENARIO_AUTHORING.md).
- **D3/D4:** Existing LangGraph nodes coordinate new typed plans in
  `orchestration/planning.py`; the server resolves identities and enforces tools.
  One bounded model additional-read decision cannot select repeated/arbitrary
  tools or elevate permissions. Valid plans are not silently broadened into all
  legacy reads. `synthesis.py` projects actual content and human source labels,
  then checks selected exact facts, AS roles, routes, citations, availability,
  provenance and narrow unsupported certainty. Rejected/malformed/timed-out
  prose falls back and is not credited as model reasoning. `gateway_network.py`
  fixes explicit Core-Birch/Edge-Cedar names being erased by incidental role
  filters. `gateway_routing.py` keeps ordinary conversation ahead of rich network
  context and excludes nonexistent attachments/editor modes from classifier
  choices. No new RAG, model registry, SQLite reader or engineering renderer.
- **D5:** `AssistantMarkdown.tsx`, `assistantCode.ts` and shared CSS provide safe
  GFM, headings/bold/inline code/tables, static shared Monaco token colors and
  whole-answer/per-code Copy with honest errors. Both Floating implementations
  and Studio use it. Floating panel bounds adapt to viewport resizing. New
  `EngineeringHandoffAction.tsx` replaces the permanent form with contextual
  **Review in Ansible Studio**, eligibility/revision checking, focus/Escape and
  cancelled-async guards, reviewed transfer and an unsent separate Studio draft.
  Backend eligibility is additive; existing handoff acceptance/privacy/idempotency
  remain. Monaco Accept/Reject/Undo/exact-base/explicit Save are preserved.

### Actual verification in this continuation

Final affected backend run: **121 methods + 34 subtests passed in 32.95 seconds**,
`tmp/phase-d/final-affected-regressions.xml`. Includes Phase C, B2/B3, literal
editor facts, shared intelligence/network and new Phase D boundaries. Earlier
103/44/50-method reruns overlap and are not additional successes. The final
context-schema run exposed test engine settings leaking through module import
order; `test_ai_intelligence.py` now pins legacy/feature settings per fixture,
without weakening tool assertions. Original failure and corrected 50-method run
are retained. TypeScript passes. Seven Node copy/token/workspace utility tests
pass. Production build passes with existing chunk-size/DaisyUI optimizer warnings.
No dependency or model was downloaded/installed.

Knowledge: 18 exact route preview positives, 30 negatives; four IS-IS preview
positives, six negatives; three management positives, 14 negatives. Candidate
**27725812f27742ea95422fed1fd85e40**, **47 operations/81 bindings**, compiled through
the existing publisher. **11 native vendor/operation runtime combinations** pass
actual V9 schema/binding/finalization/render with explicit reviewed selections.
Acceptance-only activation and rollback verify; ordinary pointer remains
**0690966eb003499380e960a98d1e418f**, manifest SHA
**7111628327551dfa424cd11ea40c5a379544b69c2ffab154ed29c773727ad9c9**.
Latest native run:
`tmp/phase-d/20261018T055223.211182Z-D1b-route-candidate-478e2c/`.
An initial route-only fixture correctly failed IS-IS capability/interface checks;
the corrected explicit acceptance device uses recorded Ethernet1/1. No ordinary
R1/R2 change or validation bypass. These fixtures do not certify all profiles,
physical devices, genuine Ansible support or the remaining 130 combinations.

Model: actual installed **qwen2.5:1.5b**, Ollama **0.40.2**, CPU inference. Fresh
matched routing gives candidate **6/8**, baseline **6/8**; candidate seven model
calls/26,564 ms versus baseline two/5,902 ms. Both miss a topology paraphrase and
published OSPF inputs. Prior exposed 52-case exact-set scores were candidate
14/52, legacy 19/52, then candidate 19/52 after context correction. The rubric
has disclosed redundant-reader and missing-history fixture flaws; do not silently
reinterpret these as successes. All original 52 prompts are now regressions,
not unseen generalization. M0/M1/M2 representative trials show incorrect OSPF
router-ID requirements, invented routes, repeated/uncited prose and unsupported
health assertions. Guards reject the latter; safe fallback is not model synthesis
success. One real adaptive decision selected no extra evidence, not a successful
multi-step reasoning demonstration. 90% routing/85% answer gates remain unmet.
Both new planning/synthesis flags default **0**, preserving ordinary B3 behavior.

Browser capability was freshly verified and worked. Actual UI proves shared code
colors in light/night, CSS 391px panel bounds, actual interface/address correction,
literal unsaved OSPF/BGP explanation, explicit handoff into an unsent separate
Studio conversation (zero engineering turns), stale-evidence rejection and
keyboard/focus behavior. Copy's Clipboard API resolves and UI reports Copied,
but browser automation reads empty clipboard and cannot paste; round-trip case
remains **BLOCKED**, distinct from passing exact-write/denial unit tests. Full
external normal-mode browser parity is NOT RUN. Screenshots/DOMs:
`tmp/phase-d/d5-browser/`; original/corrected replies retained. A Windows uvicorn
reload terminated the acceptance harness once; fixed by removing harness reload,
not by changing browser permissions or opening another port.

### Preserved state and precise resumption

The standard ordinary composition is restored on **5173/8000**, backend PID
**2324**, via `backend/scripts/dev_local.py`. The single acceptance pair is
stopped. Ollama remains available on 11434; only qwen is offered as conversational
chat. Authenticated read-only final API checks: health 200, diagnostics 200,
anonymous diagnostics 401, ordinary R1/R2 inventory with no scenario overlay.
The developer status route returns a disabled-state envelope in ordinary mode;
its HTTP 200 does not mean simulation is enabled. Browser preserves the original
unsaved `UNSAVED_BROWSER_MARKER` buffer; no handoff composer was submitted after
switching back. Original stored replies are retained rather than rewritten.

Protected **52-file staged index** hash still
**d6aa68e47ae3b44449d1f832404ad925a373791b845ec064d067b8e8b028d7f8**.
No automatic stage/commit/reset. Phase C/D source is unstaged/untracked; local
`.env` and runtime DB remain excluded. Active ordinary knowledge artifacts,
inventory/interfaces/configuration and all other checked ordinary table hashes
match D0. **One existing ansible_chat_sessions table hash changed**, with 16 rows,
zero new ordinary conversations, and all 13 newly created acceptance conversations
absent. Baseline hashes cannot prove this was timestamp-only; retain this caveat
and do not restore a database over newer user history. Integrity OK/zero FK errors.
No tracked sibling V9 source was changed. Source digest covers the documented
code/evaluation subset, not private `.env`; scoped Git diffs remain authoritative.

Start with `tmp/phase-d/preservation-final.json`, `ordinary-runtime-final.json`,
`conversation-isolation-final.json`, `source-delta.json`, the coverage matrix and
execution review. Preserve failed run archives. Reuse
`tmp/stabilization-20261017/acceptance.db`, `tmp/phase-d/acceptance-knowledge` and
`tmp/phase-d/acceptance-scenario.json`; do not create more app variants or ports.

**Next safe milestone:** continue D1's remaining per-vendor contracts/semantics,
especially Huawei process identity, Junos logical-interface/NET/VLAN/policy
requirements; expand D2 conformance/event cases; repair the benchmark fixtures
explicitly while retaining old failures, then collect new untouched model
holdouts and complete Copy browser acceptance. Full semantic certification count
remains zero, despite 11 narrow native fixtures. Do not activate the acceptance
candidate in ordinary knowledge or enable new model paths by default until the
specified gates actually pass. Final D7 publication/runtime acceptance and Phase D
completion are **not achieved**. No device action, deployment, new model, competing
RAG or automatic publication occurred. Rollback controls and exact reproduction
commands are in PHASE_D_RESULTS.md.


---

## Phase E — revised engineer-authorized publication implementation — 2026-10-18

**IN PROGRESS.** This section supersedes the earlier Internet/vendor/device certification publication prerequisites, not historical results. The human senior's exact content/scope approval and mandatory V9 structural/runtime integrity gates remain. No real approval was inferred or fabricated.

All **47 × 3 = 141 native methods** have been reconstructed through the existing authoring API in ordinary and reused acceptance workspaces. No acceptance database/release/pointer was transplanted into ordinary. Contracts fix missing vendor inputs, alias collisions and availability, Junos named/logical constructs, Huawei IS-IS identity, optional None behavior, exact kbit/s derivation, preference-qualified next hops and explicit inverse-object scope. Best-effort limitations remain disclosed for actual engineering review; these are not vendor-certified translations.

The **ordinary inactive candidate `f72cf2ae1b66407b8a389c383e6634a8`** has manifest SHA **`3bb446f6a96f1375dd4b8466d45e80c3de276d26443615024b2fb033f3d7ad67`**, 142 positive fixtures / 1,638 specified+derived invalid-input fixtures, 141 profile lookups, wrong profile/version rejection, exact 47-document Chroma comparison and five actual retrieval smokes PASS. Acceptance candidate **`0537059c2330476aba8da06f76a71504`**, SHA **`5e97f30aefd1fac6697cf8cd61cabf2e5991c3cca1bf0a00641ec3ba23cc51ad`**, has 141 positives / 1,644 negatives because its retained contracts differ. Counts are not combined. Artifacts are in `tmp/phase-e/ordinary-/` and `acceptance-/`, including the trailing hyphens.

Both candidates have **0 real sign-offs and are inactive**. Ordinary active remains **`0690966eb003499380e960a98d1e418f`**, SHA `7111628327551dfa424cd11ea40c5a379544b69c2ffab154ed29c773727ad9c9`, 44 operations/78 inherited bindings/offline retrieval. Its old Cisco route defect is not concealed by corrected inactive draft results. Read-only activation guards reject 141 unsigned changes. Optional vendor semantics NOT_VERIFIED; device/Ansible NOT_RUN. Full positive branch/boundary conformance is not established by representative fixtures.

`knowledge_review.py` extends existing V9 authoring SQLite with exact method specifications and append-only auditable decisions. It binds source hash, schema, input contract, effect, scope, fixture outputs, assumptions, limitations and material risks. Strict authenticated admin is the project's senior role, not an LLM-selected capability. Existing exact approvals are reusable; material changes/revocations block activation. Frozen review artifacts enter new immutable manifests only during compiler staging. Existing published releases are unchanged. Pure code-owned exact rate derivations and shared native sandbox are used by preview and hosted V9 rendering. Full builds use a bounded 900-second worker budget.

Knowledge Engineering now offers themed batch review, operation/vendor/approval filtering, exact Jinja/schema/fixture inspection, risk resolution, rationale and acknowledgement. The refreshed browser bundle revision is `39d0d7613ac3d2c6fcc91fc159aabfe606d5272eff92ca902e9bcbc180b5fb95`. Actual browser showed 0 approved/141 ready, filtered Junos route removal to one row and confirmed submission disabled without human input. Final screenshot/bundle: `tmp/phase-e/e9-browser/final-review-ready.png`, `final-review-bundle.json`. No approval click. Native output and published-requirement evidence carry separate approval/certification labels.

Shared intelligence repairs cover explicit published requirements versus generation, requested source coverage, natural editor effects, protocol observation retrieval, typed goals/gaps and bounded per-stage inference/one reverified synthesis repair. Protocol fallbacks now explain actual observed state/differences/unknown prerequisites rather than returning only protocol names. Exact fact guards remain narrow, not a universal technical parser. New seeded mixed-vendor scenarios extend the existing manager, with seven variants and independent test expectations; no new SoT or RAG index.

Actual qwen first-run routing: **52/60 candidate (86.7%) versus 57/60 existing (95%)**. Source/edit repairs passed 12 scoped exposed-case reruns, which are not new holdouts. Real authenticated M0/M1/M2/M3 probes preserve overclaims, rejected prose and local-model timeouts. One earlier comparison overlapped scenario mutation and is explicitly invalid for affected quality/latency rows. Answer adequacy ≥85% is NOT established. New planning/synthesis defaults remain **0**; no stronger model was downloaded. Broader unfamiliar multi-turn reasoning and normal/external-mode parity remain incomplete.

Affected evidence: `final-affected-regressions.xml` **49 methods + 47 subtests PASS**, `final-boundaries.xml` **45 + 66 PASS**, `final-review-authority.xml` **10 + 14 PASS**, explicit-request and protocol-fallback regressions **44 + 22** each PASS. These overlap; do not add them. Real disposable V9/Chroma publish/index/activate/rollback uses explicitly TEST reviewer records, never ordinary human approval. TypeScript/production build pass after final filter changes; eight Node copy/workspace cases pass. Original fixture-version, import-scope, alias/vendor input, fixture-domain, build timeout and wrong-cwd failures remain archived.

Fresh browser access succeeded on 5173/8000. Whole Copy displayed success but virtual clipboard paste returned **`Browser Use virtual clipboard has no data to paste`**: browser clipboard acceptance BLOCKED, standard clipboard NOT RUN. The brief frontend `net::ERR_CONNECTION_REFUSED` during owned supervisor restart was resolved on the same 5173 port; it was not called disabled browser access. Original Monaco unsaved BGP neighbor and markers remain, no Save/deployment/device action.

Data preservation found an actual client defect: opening shared Studio could upsert cached history into the legacy session table. Shared mode now avoids the duplicate client cache/autosave; the gateway remains authoritative. A corrected actual Studio navigation left **all ordinary table fingerprints identical** (`readonly-browser-corrected.json`). Initial 16-row legacy history hash did change; there is no before-image proving timestamp-only, so no blind restoration was attempted. Inventory/interfaces/links/jobs/authoritative gateway-turn records remain unchanged. SQLite integrity OK/foreign keys 0. Protected **52-file staged patch SHA remains `d6aa68e47ae3b44449d1f832404ad925a373791b845ec064d067b8e8b028d7f8`**. All Phase E changes remain unstaged; runtime artifacts stay excluded, no automatic commit/reset or sibling V9 source edit.

**Next concrete gate:** the actual senior/admin reviews and signs the exact methods in Validation & Publication. Build a NEW immutable signed package through existing lifecycle after approval, then authenticate activation against current pointer, perform all 141 ordinary runtime/Studio journeys and retain legacy rollback. Current builder does not assemble partial approved cohorts. In parallel, independently review the source-equivalence/compound-edit rubric, freeze untouched evaluation, establish actual model quality, finish normal-mode/clipboard/browser and contained playbook gates. Native sign-off does not depend on optional external certification.

Read `docs/evaluations/PHASE_E_RESULTS.md`, `PHASE_E_IMPLEMENTATION_CHECKPOINT.md`, `PHASE_E_RELEASE_AND_RUNTIME_REPORT.md`, the 141-row coverage CSV/JSON and stage tracker before resuming. Do not repeat the completed 141 authoring queue or treat known-case reruns as new benchmark successes. **Phase E and 141/141 approved publication are not complete.**


## User-directed publication simplification and AI enablement — 2026-10-18

The user's latest instruction supersedes the earlier separate human per-method sign-off requirement. Publish/Activate themselves are the authenticated engineer decision. Preserve role checks and the audit trail; never invent an independent human reviewer or vendor/device certification. Do not reintroduce an extra GUI approval ceremony or semantic/public-document publication veto.

`knowledge_review.authorize_publication` now prepares representative render samples for new/changed bindings, validates them against existing V9 schema/render contracts, preserves matching approvals, and records the real authenticated Publish action. Samples are application operability checks, not independent semantic goldens. Changed author templates can refresh sample outputs; no semantic correctness claim is inferred. Untouched inherited bindings remain usable without retroactive fixtures. New uncommon field constraints may require an author-supplied schema example/default so the rendering check has valid inputs. Activate authorizes the selected exact built immutable package using the existing SQLite audit rather than mutating its artifacts. No chat tool gains publication, deployment or filesystem authority.

The optional inspection disclosure replaces the separate sign-off panel. Draft changes have maximum panel height 32rem, internal scroll area 24rem (browser measured384px over13534px content), sticky headers and keyboard scrolling. The authenticated GUI still offers Validate Draft, Build Release, Publish Release and Activate/rollback. The ordinary GUI Publish was invoked for the prepared141-method pack with release notes explicitly describing the user's delegation; it is recorded as an authenticated publication action, not a fictional independent senior review.

Both existing planning and grounded synthesis switches are1 in local `.env` and `.env.example`. Running backend diagnostics confirmed bothtrue, engine langgraph_b3, model qwen2.5:1.5b. OCR-only LightOnOCR and embedding-only nomic remain excluded from conversational model selection; no model download. The user chose enablement despite earlier measured quality limits; retain fallback/verification and honest reporting.

Focused actual isolated publication→activation→rollback→Studio consumption passed with no method/sign-off API calls (1 integration test,328.18s). New unit checks cover publication authorization/reuse, exact built-package activation, arbitrary engineer syntax, automatic render samples, stale/invalid/auth/sandbox checks and bounded ordered embedding batches (17 methods+14subtestsPASS). Baseline B3 tests now explicitly pin legacy flags in their test fixture so local user settings cannot alter mocked two-round expectations; corrected model/B3 boundary run32methods+7subtestsPASS. This test isolation does not disable features in the application. TypeScript and production build pass; existing CSS/chunk warnings remain.

Original failed runs are preserved: missing unit fixture authoring_state table; .env-sensitive legacy round expectation; a sandbox Ollama connection failure; and ordinary publication embedding timeout while the isolated integration test ran concurrently. Browser refresh initially reached a stale error data URL with ERR_CONNECTION_REFUSED. Fresh browser localhost access succeeded after restoring same5173/8000; existing Ollama11434 was already running and discovered once Windows allowed its process/install read. The later authorized connectivity check returned200 for allthree. No browser-disabled claim. Index embedding now batches at mostfour documents/request with the same existing model/index and timeout; no alternative RAG/provider.

See the final current publication outcome appended next and ignored `tmp/phase-e/simple-publication-browser/` plus `publication-action-*.xml`. Preserve the old active pointer until the ongoing GUI publication passes every structural/index/activation gate. No automatic Git stage/commit, user-history deletion, sibling source edit or device operation.


### Final outcome of the simplified workflow — 2026-10-18

## Current outcome — simplified engineer publication is working

The latest user instruction supersedes the separate sign-off process. **141/141 native vendor-operation bindings are now published and active** through the actual authenticated GUI **Publish Release** action. This is recorded as `authenticated_engineer_publication_action` by account `admin`, action `publish`, under the user's explicit delegation. It is not an invented independent human assessment or vendor certification.

- Active release: **`f0e33c357dd54988ba7e651d813c76a7`**.
- Manifest SHA: **`9b0cb20f114b3878e1055bbc9488f6afb9ce40e5560142942301882cc6096e9c`**.
- **47 operations / 141 bindings / 141 exact profiles; 142 positive and 1,638 invalid-input checks.** All142 positive fixtures were re-executed against the actual current V9 snapshot/renderer after activation. Exact47-document Chroma index comparison and five real retrieval smokes PASS. Ordinary R1/R2 identities were not changed.
- GUI shows **Active**, publisher admin and **0 draft changes**. Publication timestamp2026-10-18T13:26:33Z (21:26MYT). The old release `0690966eb003499380e960a98d1e418f` remains available for authenticated rollback. No immutable older artifact was edited.
- **Planning and synthesis are enabled** in `.env` and `.env.example`. Live diagnostics confirmed bothtrue, engine langgraph_b3 and existing chat model qwen2.5:1.5b. No stronger model downloaded. OCR-only and embedding-only models remain in their correct roles.
- No separate sign-off form. Publish/Activate audit the exact package and authenticated account. Public-document/vendor/device/Ansible certification does not gate native publication. Independent certification remains informational NOT_VERIFIED/NOT_RUN.
- Optional template-check inspection is collapsed. Draft Change Summary is capped at32rem, its scroll region24rem. Browser measured384px viewport /13,534px content and keyboard PageDown changed internal scrollTop to230.4px.
- Tests: **17 unit methods +14subtestsPASS** (`publication-action-unit-final.xml`); actual isolated author→Publish(no method/sign-off calls)→build→activate→rollback→Studio→restart **1PASS**,328.18s (`publication-action-live-integration.xml`); model/B3 affected boundaries **32methods+7subtestsPASS** (`publication-model-boundaries-corrected.xml`). Runs overlap earlier suites, never add them. TypeScript and production build PASS; existing CSS/chunk warnings remain.
- Original failure artifacts remain. The first ordinary GUI publish hit an embedding timeout during concurrent test publication; active pointer stayed unchanged. Bounded four-document embedding batches and a serial GUI retry succeeded. Schema/render checks and model time budgets were not weakened. The first unit fixture lacked authoring_state and the legacy B3 test depended on local flags; fixtures were corrected without disabling application features.
- Browser qwen smoke: greeting/arithmetic answered `1 + 1 is 2.`. A compound topology/interface comparison made1 actual planning call, rejected a source-incomplete model plan and used verified inventory/topology fallback. This is not credited as successful model synthesis. Earlier model-quality and clipboard/normal-mode limitations remain; user-requested enablement is not a rewritten benchmark pass.

Exact current runtime evidence: `tmp/phase-e/ordinary-/f0e33c357dd54988ba7e651d813c76a7-verified.json`; browser artifacts `tmp/phase-e/simple-publication-browser/`; final preservation snapshot is linked from the stage tracker. No device/SSH/deployment, automatic buffer Save, stage/commit or sibling V9 source change. All broader Phase E claims remain scoped to their actual tests; the latest publication/enablement/scroll requests are fulfilled.



### Fresh verification of the simplified workflow — 2026-10-19

The latest request was checked against the actual running source and GUI. Existing implementation already uses authenticated Publish/Activate as authorization, without a separate sign-off form or public-document/vendor-certification veto. No additional implementation change or duplicate publication was needed. The active release remains `f0e33c357dd54988ba7e651d813c76a7`: manifest hash intact, 47 operations/141 native bindings, Chroma retrieval ready. Live authenticated diagnostics report planning and synthesis enabled, engine langgraph_b3, existing qwen2.5:1.5b available.

Fresh built-in browser access succeeded. Initial localhost navigation timed out; inspecting that same tab then showed the login screen. Authenticated 127.0.0.1 navigation and GUI Validate Draft succeeded. Draft summary computed maximum height is 512px, its internal scrollport maximum 384px, overflow auto and keyboard focusable. Current draft has zero changes; the earlier populated-scroll browser evidence is retained rather than inserting test draft data.

Current focused application-environment run: `backend/tests/test_phase_e_review.py` **17 methods + 14 subtests PASS**. Initial sibling-environment runners failed on absent pytest/jose and discovery import scope; no dependency was installed. The protected 52-file staged patch hash is unchanged. No user records, template contents, release pointer or immutable artifacts were edited during this check. Sanitized evidence: `tmp/phase-e/simple-publication-recheck/verification-*.json`. Existing broader intelligence/Phase F work remains outstanding; this check does not claim completion of those milestones.


## Phase F verified corrections and current continuation — 2026-10-19

Phase F remains IN PROGRESS. The active ordinary immutable release is now `7a14a351e52b49aeb87f65d1192f0937`, manifest `bdb1cad94c4275081ce9b9aaaa3bbfadd9b38a73b201f67277aa1d7be69694b5`, created by the actual authenticated GUI Validate/Publish action. Four reproduced Cisco/Huawei OSPF and Huawei ACL statement/quit/logging defects were fixed through authoring;137 other source hashes unchanged. All150 current-host positive renders,1642 build negatives,141 profiles,47 exact index documents and5 retrieval smokes pass. Twelve additional corrected-family comparisons use independent expected statements. No separate sign-off or public/device certification gate. Prior immutable f0e33... remains, with its known defects.

Full exposed routing comparison passes60/60 candidate versus60/60 matched current legacy; historical52/60 versus57/60 remains separate. Candidate has19 validated model plans and one rejected-plan fallback. Fresh120 routing/30 quality/10 permission specifications are frozen but NOT RUN. Actual authenticated gateway probes use a disposable SQLite backup, real R1/R2 and qwen, with owner checks and no ordinary data changes.

Actual synthesis exposed dropped topology links, absent citations, normalization of R2’s recorded GigabiEthernet spelling and a flat attribution guard gap. Projection/citation constraints and scoped endpoint/live/hypothesis checks were repaired; original failed model outputs and unit failures are retained. A factual cited repair passes the corrected independent oracle, but required3 graph model calls/27.6s after truncated initial JSON. This is not a general quality or speed claim.49 affected tests+22 subtests pass; final5 source/oracle checks overlap.

The ordinary long-running backend has NOT yet been restarted to load the new planner/synthesis Python. Fresh ASGI public-gateway tests prove the source integration; normal browser intelligence acceptance still requires a controlled restart preserving original unsaved Monaco buffers. Publication GUI acceptance itself passed. Current full state, exact paths, raw results, known gaps and next actions are in `docs/PHASE_F_CONTINUATION_CHECKPOINT.md` and phase_f_stage_state.json. All ordinary app DB table fingerprints and protected52-file staged hash remain unchanged; no commit/stage, physical/device operation or sibling source edit. Broader F1 branches, F2 simulation, fresh F3/F4 evaluation and F5–F9 remain required.
## Current continuation pointer — 20 October23:04 MYT

This file was relocated with the older implementation history. Current PhaseF/G
work is recorded in `../PHASE_G_CONTINUATION_CHECKPOINT.md` and the PhaseG reports;
do not recreate or reset the former root-path file. Fresh browser access works;
standard5173/8000 loads final tested document/Studio fixes; ordinary sources are
active. Page-specific/relative PDF and explicit untouched-buffer browser checks
pass.075 false-premise prose still needs a truthful verified fallback, not model
success. Protected52 checkpoint, active7a14.../141 release and authoring unchanged.
Full PhaseF/G remains incomplete; next untouched frozen routing077, remaining24
source dual-edit/141Studio/multifile/quality gates remain open. No commit/stage.


## Verified resume pointer — 21 October08:05 MYT

Full PhaseF/G goal remains active. Latest bounded source/editor increment and raw
failure/correction evidence are in
`tmp/phase-g/iterations/20261020T151055.394247Z-G3-independent-observed-links-9ec323/`.
Read its increment-review.json and manual-frozen-078-084-review.json. Earlier
browser-disabled, pending topology-preview and077-next notes are historical.

Browser works: IAB2/tab1, bound phaseGResumeTab. Ordinary sources restored via GUI;
CUSTOM-1792537848716 draft3/revision2 retained. Exact original204LF editor digest
matched after actual marker and current-buffer comparison requests; never accept,
save or overwrite it. The standard app session84348/backend29120 uses5173/8000;
Ollama25504 untouched. This process includes the verified topology and079 fixes,
but the latest081–083 selection/rename and comment-scope guards are NOT loaded yet.
Reload only its owned launcher after the pending actual test is terminal.

Current pending actual-model evaluation: shell80792, frozen081–083 candidate,
root `tmp/phase-f/iterations/20261021T000253.877669Z-F3-frozen-routing-candidate-1f1899/`.
Inspect/poll this exact request before starting another. Unit90PASS plus16 guard/
evaluator checks pass.082 correction returned0 provider calls;083 earlier
020e44 still had a real selected line and guessed function rename (FAIL), before
the final rename prerequisite/scope guards. Do not repeat the inaccurate claim
that083 had no selection. New pending-input outcomes explicitly mean the edit is
NOT completed.081 must return a syntactically marked comment immediately above
BGP with every existing line preserved, or a truthful failure; inspect actual diff.
Then reload owned app and verify081 proposal/Reject and082/083 prerequisites in
the actual browser. Record red/green and complete the new preservation snapshot.

Next untouched frozen routing case085;084 is V9 preview, not rendered output.
Continue all24 source lanes and the full remaining F/G milestones afterward.
No publication, model download, device action, stage/commit or sibling edit.



## 21 October09:35 MYT — final081–083 actual edit acceptance and085 correction

The earlier081 timeout is terminal, not pending. Original1f1899 fails after185.5s;
0e9dbe bounded768-token attempts fail content/location checks;3fd083 toolPASS is
manualFAIL (empty ! plus blank line);170a0a correctly rejects that empty patch.
Actual focused comment generationaa2ea9 succeeds on the fixture, but the browser
with another actual AS pair exposed an AS-as-BGP-ID error. It was rejected and
retained as gui-comment-bgpid-first-red.json/png. Final8e7b13 and the actual
browser supply a useful BGP-neighbor/remote-AS explanation, inserted at the exact
unique heading with every existing byte preserved. Model authors the sentence;
existing exact-base code supplies CLI comment syntax/location. No model-derived
configuration renderer or operation recognizer was added. Comment request uses256
output tokens; general small patches768, larger2048. Only explicit unique IOS-style
BGP/OSPF heading insertions use this focus; arbitrary edits keep the normal patch
workflow and malformed-patch rejection. Native syntax/platform/device certification
remains unavailable and clearly labelled.

082 returns missing-selection clarification with0 provider calls.083 has a real
selected Python assignment, but no intended new symbol name; it returns that
specific prerequisite with0 provider calls. Neither is a completed edit. Selected
region boundaries, indentation-only text preservation and comment-only location
checks run before proposals; one bounded repair remains. Frozen evaluator now
records CLARIFICATION_REQUIRED_EDIT_NOT_COMPLETED separately from task success.
Actual browser proposal/Reject, missing selection and post-Reject full-buffer read
pass; received source digest is still the original204LF b4c9fe...93632. The buffer
was not accepted, overwritten or saved. Evidence:browser-edit-081-083-final-review.json
and manual-edit-081-083-final-review.json in the topology increment audit root.

085 originally substituted inventory interfaces for “Prepare a native static route
and an interface description”. An explicit requested artifact type now constrains
the workflow before the attribute lookup shortcut; V9 still identifies/validates
operations. Actual96bc26 preserves two target-bound tasks and asks for missing
parameters/operation confirmation.086 reaches genuine playbook-preview mode but
remains unresolved; neither is a rendered/confirmed generation journey.

Important new evaluation correction:96bc26 case087's unavailable routing result
was caused by trace_provider_response reading a LangChain HTTP stream before its
consumer. The underlying request returned200; ResponseNotRead came from the
instrumentation. This is NOT evidence of an Ollama outage or model timeout.
Tracing now leaves unread streams intact, records buffered chat replies, and
summarizes embedding dimensions without dumping vectors.42 evaluator/conversation
checks pass; original087 is being rerun with the corrected observer. Inspect its
current terminal before duplication. Next untouched frozen088, subject to087 repair.

Tests in this increment:89 routing/gateway regressions;90 edit-prerequisite/
shared tests;61 comment/exact-edit regressions;53 final comment-role checks+19
subtests;45 empty-comment/source checks;42 streaming observer/conversation checks.
These overlap: do not add them as unique successes. TypeScript0 and prior6 frontend
checks remain scoped. No broad model-quality score or all24/fullF/G completion.
Ordinary sources remain active; protected52 stage, active7a14.../141 release and
knowledge authoring match; ordinary business tables unchanged, integrityOK/FK0.
Current owned standard launcher3201/backend4904 at5173/8000 contains081–083 guards
but predates latest085 route correction. Ollama25504 remains. Browser2/tab1 works.
Reload only the owned app when ready, without changing ordinary inventory/release.

## Current pending-work pointer — 21 October09:40 MYT

Previous goal turn made concrete progress (not a wait or complete): independent
observed topology and source checks, actual GUI activation/both-assistant reads,
078–083 editor faults, actual browser first-red/fixed proposals and Reject tests.
Read goal-objective.md again and retain the full G0–G12 plus remainingF objective.

Standard app session75203/backend27876 at5173/8000 loads all latest code;
Ollama25504/11434 remains untouched. Current browser2/tab1/phaseGResumeTab works
and has original204LF Monaco buffer, ordinary sources active. Last request is087
ambiguity clarification browser acceptance, just submitted. Inspect its response.

Current actual frozen evaluation shell52687 covers087–090; poll the samehandle.
087 is terminal inside that batch with correct missing-correction clarification,
0 provider calls, NOT completed edit or model reasoning.088–090 remain pending.
Earlier59062/80426 and081-relatedhandles are all terminal. Do not restart them.

081 final useful model comment and original-byte preservation:8e7b13 real fixture
and actual browser final gui-comment-bgp-role-final.json/png. Bad local-AS-as-BGP-ID
comment was rejected, then fixed and retested.082/083 require actual selection/
intendednewname; known present Python selection must not be described as absent.
087 original real failure b9ed04 invented BGP router-ID correction; now asks for
observed issue and desired value before modification. Prior96bc26 unavailable087
was an evaluator ResponseNotRead error, not an Ollama timeout. Tracer is fixed;
42 then19 evaluator/guard checks pass.85 native two-task V9 preview preserves both
route+description and clarifies missing fields;86 playbook preview remains unresolved.
No generation/render completion is inferred from either preview.

Next: finish actual087browser, inspect088–090 allprose/diffs, fix genuine defects,
record manual review and update source-stage indexes. Then resume all24 JSON+GUI
source gates (inventory/planned topology/history etc), full141 journeys and other
remainingF/G gates; do not narrow the objective to these editor regressions.
Latest full integrity snapshot preservation-final-081-083.json:52 stagedSHA,
active7a14.../141 release, authoring and ordinary business tables unchanged;
only AI/conversation tables changed, integrityOK/FK0. No stage/commit/modelinstall/
device action or siblingV9edit. Full phase remains IN_PROGRESS.

