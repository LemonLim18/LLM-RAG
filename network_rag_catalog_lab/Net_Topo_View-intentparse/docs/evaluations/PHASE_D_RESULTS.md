# Phase D execution ledger — 2026-10-18

**IN PROGRESS. Phase D is not complete.** Counts below describe this continuation,
not accumulated historical reruns. Raw records remain under ignored `tmp/phase-d/`.

| Stage | Current evidence | Gate |
| --- | --- | --- |
| D0 | Protected 52-file staged patch matches; active 44-operation/78-binding manifest/artifacts verify; ordinary SQLite integrity OK. Original 74-pass/one-failure baseline retained; exact-editor routing corrected. | Preservation verified with one existing conversation-table hash difference disclosed below |
| D1a | All 141 unique candidates/47 operations reconciled against actual template bodies, variables, schemas and published bindings in `phase_d_vendor_coverage.json`. | Static reconciliation only |
| D1b | Add/remove route repairs, Cisco IS-IS interface repairs and three reconstructed management operations pass bounded native fixtures. Candidate `27725812f27742ea95422fed1fd85e40`: 47 operations/81 bindings; 11 native runtime combinations pass and acceptance activation/rollback verifies. Nine editable references synchronized. | Full 141-candidate semantics/profile gate INCOMPLETE; no ordinary publication |
| D2 | Typed multivendor multihop/ECMP/VRF/ordered ACL/OSPF/BGP/metric calculations integrated into existing manager/readers; three new central examples and CLI/schema interface. | Focused modeled boundaries pass; complete requested conformance/event library INCOMPLETE |
| D3/D4 | Real qwen typed plans, bounded additional-read decision and guarded synthesis integrated behind independent opt-in flags. Model outputs/fallbacks retained separately. | Broad routing and independent synthesis quality targets NOT met |
| D5 | Shared Markdown, static Monaco code tokens, whole-answer/code Copy, responsive floating bounds and contextual reviewed handoff implemented. Browser light/night/mobile, stale evidence and unsent draft checks pass. | Copy browser round trip BLOCKED; normal external-mode browser parity NOT RUN |
| D6 | Immutable executions, 52 stable regression cases, separately identified fresh holdouts, 141-row matrix, JUnit/model/API/browser evidence retained. | Curated benchmark has disclosed fixture/rubric gaps; not complete final evaluation |
| D7 | Ordinary 5173/8000 composition restored; prior release retained; no automatic stage/commit. | Final release gate NOT READY |

## Preserved baseline

- Protected index SHA256: `d6aa68e47ae3b44449d1f832404ad925a373791b845ec064d067b8e8b028d7f8`.
- Ordinary active release: `0690966eb003499380e960a98d1e418f`.
- Manifest SHA256: `7111628327551dfa424cd11ea40c5a379544b69c2ffab154ed29c773727ad9c9`.
- D0 snapshot: `tmp/phase-d/20261018T003501.179393Z-D0-a2a639/manifest.json`.
- Original baseline failure: `tmp/phase-d/d0-regressions.xml`; correction: `d0-literal-rerun.xml`.

## Confirmed failures and corrections

1. No local services were listening. Fresh built-in browser capability succeeded;
   the page reported backend unavailable. Separate unsandboxed HTTP checks returned
   Windows connection refused on 5173/8000/11434. Starting existing Ollama required
   process permission; Vite required access outside the OneDrive filesystem sandbox.
   No dependency/model download was performed. The failed sandbox launcher left an
   owned backend process; that exact verified process tree was stopped before the
   standard app was restarted. No alternate port was opened.
2. An explicit unique-address request in the active editor unnecessarily required
   model classification. The existing exact-literal patch recognizer now supplies
   its reviewed-edit route before inference. Negated/explanatory requests are
   excluded. Proposal authorization and exact-base validation still run.
3. Model-only baseline captured at
   `tmp/phase-d/20261018T004904.837877Z-D0-model-retry-476471/`: arithmetic succeeded,
   but the adjacency explanation repeated ARP text and was not an adequate answer.
   Successful inference transport is not recorded as reasoning improvement.
4. Browser Copy clicked successfully and the page reported its Clipboard API
   resolved, but the automation virtual clipboard read returned empty and paste
   failed with “Browser Use virtual clipboard has no data to paste”. Utility tests
   prove exact arguments and rejection handling; they do not prove the browser
   clipboard round trip. Keep this browser case BLOCKED pending investigation.

## Knowledge repair evidence and publication boundary

Cisco IOS-XE 17.9 explicitly documents separate destination and mask arguments:
[Cisco 17.9 static-route command form](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/rtng/b_179_rtng_9300_cg/configuring_bidirectional_forwarding_detection.html).
Junos uses a destination prefix and next-hop statement:
[Junos static routing reference](https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/statement/static-edit-routing-options.html).
Huawei's command syntax separately accepts a destination and mask/mask length:
[Huawei ip route-static command](https://info.support.huawei.com/hedex/api/pages/EDOC1100277644/AEM10221/04/resources/command/yunshan/IPV4ADDROUTENHISPRIVTABLE%28STATICRTOM%29.html).
Huawei exact platform conformance is still a separate unmet check. These sources
do not certify all 141 candidates, every command variant, or physical devices.

The 141-row matrix deliberately does not convert the 77 retained published copies
into Phase D semantic passes. Candidate counts, existing publication and verified
native support remain separate. No immutable release is edited in place.

## Verified continuation and durable checkpoint

### Knowledge authoring and candidate runtime

All mutations used the existing authenticated `/knowledge/edit`, `/template`,
`/validate`, `/render`, `/build` and `/activate` services against the **one**
`tmp/phase-d/acceptance-knowledge` workspace. No ordinary database, release or
pointer was copied back. The three management operations were reconstructed with
fresh ordinary-compatible contracts, not migrated with the isolated VLAN v3 or
required `lab_label` contract.

- Cisco/Huawei route add **and exact removal** now derive separate IPv4 address
  and mask through V9's existing allowlisted handlers. Juniper retains CIDR.
  Independent /24, /0 and /32 outputs: **18 positives and 30 invalid-input cases**.
- Cisco IS-IS attaches an interface to an existing process and configures its
  circuit type separately; level-2 maps to `level-2-only`. Three positive levels,
  one disable and six missing/injection cases pass. This does not provision a
  NET, establish an adjacency or certify a physical platform.
- Cisco login banner, VTY **0 through 4 only** idle timeout and login lockout:
  **three positive and 14 negative authoring previews** pass. Other VTY ranges,
  authentication, transport and recovery/quiet-mode exemptions remain outside
  these operations. [Cisco hardening reference](https://sec.cloudapps.cisco.com/security/center/resources/IOS_XE_hardening).
- `render_preview` now uses the same validated pure input derivations as runtime.
  Candidate building exposed a non-reentrant authoring-lock deadlock in
  `freeze_playbook_variants`; it now reads the snapshot through the existing
  unlocked helper while retaining the outer authoring lock. Original
  `AUTHORING_BUSY` failure and corrected build are archived.

Latest candidate run:
`tmp/phase-d/20261018T055223.211182Z-D1b-route-candidate-478e2c/`.
Candidate **27725812f27742ea95422fed1fd85e40**, 47 operations, 81 bindings.
Six route combinations plus two Cisco IS-IS and three management operations
passed actual V9 finalization/schema/compatibility/render checks with explicit
review selections. The first expanded runtime attempt correctly rejected a
route-only fixture's unsupported IS-IS capability and unrecorded interface.
The rerun used an explicitly declared acceptance device and its recorded
`Ethernet1/1`; no R1/R2 identity or compatibility check was changed. Activation
and rollback happened only in acceptance. The source candidate remains offline
retrieval (`ready: false`), not a verified ordinary release.

The matrix distinguishes **11 native runtime fixture passes**, **nine repaired
editable references**, and **zero full Phase D semantic/profile certifications**.
Ansible validation, dependencies and Huawei maintained-tooling gates are separate.
Concrete remaining examples include Huawei numeric IS-IS process identity and
unqualified attachment, Junos logical-interface/family-ISO/NET prerequisites,
Junos VLAN-name resolution, policer attachment and redistribution-policy semantics.
The remaining 130 combinations have not passed this native runtime fixture ladder.
They must not be reported as unsupported everywhere merely because this work
has not verified them, or as validated because their Jinja parses.

Reproduction, acceptance workspace only:

```powershell
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/phase_d_knowledge.py repair-routes
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/phase_d_knowledge.py repair-isis-cisco
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/phase_d_knowledge.py author-management
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/phase_d_knowledge.py test-route-candidate
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/phase_d_knowledge.py sync-reviewed-references
.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/phase_d_knowledge.py audit
```

### Central scenario model

Reuse: `local_providers/development.py` owns the same atomic state and revisions;
`NetworkReader`, inventory/V9 adapters, monitoring and authorized graph tools
consume its projections. New `development/network_model.py` validates exact IPv4
route tables, recursion, VRFs/leaks, ordered stateless ACL attachments, scoped
forward/return flows, OSPF/BGP observations and timestamped metric series.
Calculations are bounded to 32 hops/16 branches, with partial/truncated paths
remaining unknown. OSPF 2-Way/DROther, unknown MTU-ignore/area authentication,
BGP Idle versus Established/zero accepted routes, counter resets and missing
samples have explicit qualified outcomes. High utilization/drop correlation
does not uniquely establish congestion causation.

Definitions: `backend/development/scenarios/`; schema:
`backend/development/scenario.schema.json`; selected default state:
`tmp/development-network/state.json`; acceptance state:
`tmp/phase-d/acceptance-scenario.json`. New mixed-vendor examples are
`MIXED-PATH-001`, `PROTOCOL-MIXED-001`, `PERFORMANCE-MIXED-001`.
See [scenario authoring](../development/SCENARIO_AUTHORING.md) for the existing
developer UI and authenticated import/edit/activate/reset/export/evaluate CLI.
No scenario rows are inserted into ordinary inventory. Arbitrary protocol
state machines, IPv6/NAT/stateful firewalling, all vendor transition edits and
independent device conformance remain unverified.

### Model planning, synthesis and evaluation

`orchestration/planning.py` adds typed information needs/source scopes to the
existing graph. Identity resolution, capabilities and permissions stay
server-controlled. One conditional additional model plan may retrieve only
remaining authorized readers. Existing budgets remain three inference calls,
eight tools and 120 seconds. A validated plan is no longer silently expanded
into every legacy investigation source. No new model registry or RAG exists.

`orchestration/synthesis.py` projects actual source content with human source
labels; internal IDs, revision/oracle labels and permissions are excluded.
Exact address/interface/name/AS-role/route values, citations, source availability,
simulated versus physical claims and narrow unsupported certainty are checked.
Rejected/malformed/timed-out synthesis returns verified existing records or the
bounded assessment. These guards are deliberately **not** a universal parser or
proof that arbitrary cited prose is correct.

Confirmed retrieval bug: `Core-Birch` and `Edge-Cedar` were also interpreted as
role filters, erasing explicitly selected devices. Explicit references now take
precedence over incidental role/vendor/status words. The original empty browser
reply and corrected actual interface/address table are preserved.
Confirmed routing bug: a small classifier could choose attachment reading when
no document existed. Its decision schema now excludes unavailable context modes,
filters corresponding examples, and rejects an inconsistent response safely.
General conversations use the existing semantic confidence gate before rich
inventory metadata is considered. No greeting receives old editor configuration.

Actual installed `qwen2.5:1.5b`/Ollama 0.40.2 participated in planning, additional
retrieval decisions and synthesis. CPU inference sometimes timed out at 30 seconds,
repeated text, omitted citations, invented routes or overclaimed operational
health. Examples were rejected; a fallback is not an LLM reasoning success.
M0 wrongly required matching OSPF router IDs; an M1 answer invented a route;
M2 selected useful configuration/state readers but its prose still overclaimed.
The adaptive case used routing/retrieval/synthesis **one call each**, retrieved
configuration and unavailable syslog, and proposed **no** additional reads. It
does not establish intelligent adaptive retrieval merely because three calls ran.

Historical identical 52-case source-selection runs: candidate **14/52**, legacy
**19/52**; after conversation-context correction candidate **19/52**. These are
exact-set routing results, not answer/task-completion scores, and are below the
predeclared 90% target. The rubric incorrectly requires redundant inventory for
some self-resolving readers; several general concepts are scored as forced local
reads; contextual cases lack earlier proposal/investigation fixtures. Security
routing is before authorization, so a proposed denied action is not execution.
These flaws are disclosed, not silently rescored. All 52 have now been observed;
their historical HOLDOUT IDs no longer prove unseen generalization. Separately
declared fresh holdouts are evaluated without tuning their evaluated revision.
Matched fresh evaluation: candidate **6/8**, baseline **6/8**. Candidate used
seven chat-model calls/26,564 ms total; baseline two calls/5,902 ms. Both missed
the recorded-topology paraphrase and published-OSPF-input request. This is no
demonstrated improvement and does not satisfy the 90% routing gate. Curated
review: [execution review](phase_d_execution_review.json), including raw artifact
locations and the distinction between implementation-agent review and external
blinded human grading.
The 85% answer-adequacy gate and full M0/M1/M2/M3 benchmark remain incomplete.

Both new paths default **off**: `COGNISHIELD_AI_PLANNING=0` and
`COGNISHIELD_AI_SYNTHESIS=0`. Existing B3 remains the ordinary engine. Re-enable
for controlled evaluation only; neither flag grants engineering permissions.

### UI and focused verification

Shared safe GFM Markdown and static Monaco token spans render headings, bold,
inline code, code fences and tables in both assistants; no raw HTML execution or
extra Monaco editor instances. Whole response Copy retains exact Markdown;
per-code Copy retains exact code; rejection is announced. Floating handoff is now
the contextual **Review in Ansible Studio** action, with owned eligibility,
freshness checks, explicit review and a separate unsent Studio draft. Escape,
focus containment/return and cancelled async responses are guarded. The floating
panel clamps to a CSS 391-pixel viewport and preserves drag access.

- Final affected regression: **121 methods + 34 subtests**, zero failures,
  `tmp/phase-d/final-affected-regressions.xml` (32.95 seconds). Earlier 103-method,
  44-method and 50-method runs overlap and are not added to this total. The first
  context-availability regression exposed legacy/B3 test import-order leakage;
  per-test engine pinning fixed it without relaxing assertions. Both original
  failure and corrected result remain in `context-availability-*.xml`.
- TypeScript `tsc -b frontend`: PASS. Seven Node utility/workspace tests: PASS.
  Production Vite build: PASS, existing chunk-size and DaisyUI `@property`
  optimization warnings retained. No dependency/model installation.
- Actual browser: syntax colors/night/light, exact unsaved OSPF/BGP values and
  markers, recorded interface correction, narrow screen, reviewed unsent handoff,
  stale-source rejection and restored ordinary mode verified. No proposal was
  accepted/saved and no device action occurred.
- Browser Copy API resolved and UI reported Copied; automation clipboard read
  was empty and paste returned `Browser Use virtual clipboard has no data to
  paste`. Exact unit writes/rejection handling pass; real browser round trip is
  **BLOCKED**, not accepted or declared a proven product defect.
- Normal external-service mode rendering is wired to the common component, but
  unavailable external services prevented its full browser acceptance.

Raw proof: `tmp/phase-d/d5-browser/` and timestamped `D5-browser-handoff` run.
Original failures, corrected reruns and candidate outputs are retained, not
overwritten. The local acceptance harness initially stopped on Windows uvicorn
reload/CTRL-C propagation; removing harness reload restored the same 5173/8000
pair. That was not a browser-permission failure. Fresh browser access succeeded.

### Preservation, recovery and remaining gates

Ordinary runtime was restored with `backend/scripts/dev_local.py` on 5173/8000,
development authority disabled. Browser confirms the original unsaved marker and
installed conversational model selection. No acceptance request was submitted
after returning to ordinary data. The 13 new acceptance conversation identities
are absent from ordinary SQLite; ordinary conversation count remains 16 with no
new conversation since baseline. One existing `ansible_chat_sessions` table hash
changed during ordinary UI activity; the baseline contains table hashes, not
row-level before-images, so a timestamp-only explanation cannot be independently
proved. All other table fingerprints, including inventory, interfaces,
configuration snapshots, turns/evidence and checkpoints, match D0; integrity OK,
zero foreign-key errors. This discrepancy is retained, not reset or hidden.

Preservation record: `tmp/phase-d/preservation-final.json`; isolation record:
`conversation-isolation-final.json`; source changes: `source-delta.json`.
Protected index hash remains `d6aa68e47ae3b44449d1f832404ad925a373791b845ec064d067b8e8b028d7f8`.
The original 52-file stage is unchanged; Phase C/D remain unstaged/untracked.
No ordinary authoring before-image was captured in D0; final authoring hashes
are recorded without claiming an unavailable historical comparison.

Rollback: leave new planning/synthesis flags off; disable development simulation
and restart the existing launcher. Existing B2/B1/legacy engine options remain.
Use only existing knowledge activation service for candidate rollback; never
edit immutable artifacts or copy acceptance SQLite/pointers into ordinary data.
UI rollback must be a reviewed scoped source patch preserving prior staged work;
do not blindly reset or restore a database over newer conversations.

**Next safe work:** finish independent vendor/profile semantics and contracts for
the remaining matrix rows, review the unknown profile prerequisites, then expand
the scenario conformance/event cases. Repair the evaluation fixtures/rubric
explicitly with original results retained, and complete fresh reasoning and
browser Copy acceptance. Only then reconsider default model flags and ordinary
knowledge publication. User authorization exists; missing correctness evidence,
not missing permission, prevents final activation. Phase D remains INCOMPLETE.
