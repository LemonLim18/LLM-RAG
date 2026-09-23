# Implementation Plan: Context-Aware Clarification

**Status:** Proposed for review. This document does not authorize or implement code changes.

## Objective and Scope

Extend the existing V2 core so a weak local LLM can identify operations, associate
them with the correct devices, and extract schema-defined parameters. Deterministic
code must verify evidence, search permitted planned context, collect unresolved
questions, validate answers, and gate vendor-specific rendering.

Keep the current catalog, inventory, RAG, schemas, templates, and JSON sessions.
Implement the interaction in the terminal with structured data reusable by a
future website. External integrations, a website, execution, topology discovery,
and business-level intent interpretation remain outside this revision.

## Current State

| Area | Existing capability | Gap to address |
|---|---|---|
| Targets | Inventory attributes, aliases, conflict detection, suggestions, descriptive refinement | Shared targets across operations and complicated wording are not reliably associated |
| Extraction | Schema-guided LLM extraction, literal normalization, provenance labels | Literal presence does not prove correct field association; conflicting alternatives and partial nested values need explicit handling |
| Context | Device/interface and advertised-capability checks | No general lookup of planned operation parameter assignments |
| Clarification | Persisted tasks, one active terminal question, choices and typed replies | No complete typed question/answer contract or dependency-aware question queue |
| Validation | Required fields, schema types/ranges, IP formats, inventory alignment | Strict rejection can be bypassed; missing fields delay checking other supplied values |
| Rendering | Individual validated tasks render vendor templates | Requested behavior requires all tasks to validate before any rendering |

Two defects were reproduced during the preceding review:

- `resume_task()` merges extracted values before strict validation. An address
  reply of `255.255.255.0` can survive rejection and produce a ready task.
- `find_explicit_interface_names()` uses substring matching: `Ethernet1/10` can
  be interpreted as inventory interface `Ethernet1/1`.

The existing tests do not establish correctness for these paths. Add regression
coverage through the actual extraction and answer-validation flow.

## Required Behavior

1. Analyze every intent in the original request before starting user questions.
2. Preserve explicit operation-to-device relationships and partial parameters.
3. Check supplied values and consult permitted planned context for unresolved fields.
4. Queue missing, incomplete, ambiguous, invalid, and conflicting information.
5. Ask one actionable question at a time, with sourced options and custom input.
6. Accept only validated answers; preserve unrelated values and task state.
7. Revalidate the entire completed request, then render every applicable template.

Validated tasks may finish information gathering independently. They must not
render while another task is unresolved. This intentionally changes the current
per-task rendering behavior; it is not a claim of transactional device execution.

## 1. Repair the Validation Boundary

Use one answer path:

`candidate -> field-specific parsing -> normalization -> validation -> state update`

- Rejected answers never enter accepted parameters. Retain their rejection reason
  separately and leave previously valid values intact.
- Validate provided fields even when other required fields are missing. Run
  cross-field checks as soon as their dependencies are available.
- Match complete inventory interface names/aliases. Fuzzy matching offers choices
  only; it cannot select or silently replace an interface.
- Preserve partial array/object items. A known interface with an unknown OSPF
  area must remain available for the next question.
- Address one nested field at a time, retaining item identity when arrays change.
- Apply the same checks to option selections, custom answers, and LLM output.

Schemas remain authoritative for required flags, types, ranges, lengths, enums,
and formats. Central metadata supplies labels, aliases, normalization, and named
domain-validation rules without duplicating those constraints.

Numeric answers must satisfy the field's integer/range requirements. String
fields may legitimately contain digits or punctuation. IP/prefix validation must
respect the parameter's role and platform, including applicable /31 and /32
semantics; avoid blanket rules such as rejecting every zero-ending address.
Netmask conversion belongs only to a field that permits that normalization.

## 2. Make Operation-to-Device Bindings Explicit

Extend the existing plan to represent logical operations and their target bindings,
with references to supporting spans in the original prompt.

| User meaning | Required bindings |
|---|---|
| A, B, C on devices 1 and 2 | A -> {1,2}; B -> {1,2}; C -> {1,2} |
| A and B on device 1; C on device 2 | A -> {1}; B -> {1}; C -> {2} |

After target resolution, maintain parameters and validation independently for
each operation/device binding. Share values only where the user's instruction
explicitly applies them to all relevant bindings. Vendor requirements and
interface names remain device-specific.

Preserve operation order where stated. Unclear shared scope, pronouns, exclusions,
or conflicting operations require repair or clarification, not automatic copying
of the nearest device name. Confirm genuinely ambiguous mappings with the user.

## 3. Use Bounded LLM Stages

- **Planning:** identify all operations and proposed target relationships using
  the whole original request. Retain source evidence and unresolved associations.
- **Classification/extraction:** select an active catalog operation, then extract
  parameters using its schema, relevant source spans, and explicit shared context.
- **Focused repair:** when needed, allow one additional attempt for the failing
  stage, supplying its specific validation issues and original evidence.
- **Clarification:** unresolved meaning becomes a user question after the repair
  limit. Missing information cannot be invented to make the plan complete.

Keep deterministic shortcuts for unambiguous literal inputs. Do not use keyword
splitting or model confidence as proof of complex semantic relationships. A second
LLM pass is a recovery attempt, not an independent correctness guarantee.

Unsupported operations, invalid model responses, and service failures must have
explicit recoverable states. They must not crash away other tasks or silently
select the only retrieved operation. Question-free does not mean validated.

## 4. Add a Small Planned-Context Resolver

Declare approved context lookups in operation/parameter metadata, implemented by
a small registry of deterministic lookup functions. Scope every lookup by the
resolved device, operation, and dependent field values.

Initially use the existing inventory plus a local planned-parameter JSON dataset.
Records should contain a stable ID, device ID, operation/parameter scope, typed
value, source reference, revision, and whether the record is a fact, candidate,
or intended assignment. Validate these records before offering their values.

| Information | Treatment |
|---|---|
| Device vendor, platform, existing interface identity | Authoritative inventory facts; verify and record provenance |
| Eligible interfaces or recorded parameter alternatives | Present relevant choices for user confirmation |
| Recorded planned OSPF/BGP/address assignment | Present the scoped value and its source for confirmation |
| Unknown process ID, area, next hop, or address | Ask for input; do not manufacture a default |
| Conflicting user/context values | Explain the disagreement and request correction or an explicit permitted plan change |

The current inventory does not contain general OSPF/BGP/interface-address
assignments. Useful choices require explicit planned records; a database cannot
provide information it does not contain. Management addresses and unrelated
device values must never be repurposed as configuration parameters.

Distinguish an incorrect identity claim from an intentional configuration change.
For example, an unknown interface needs correction; changing a planned OSPF area
may be legitimate and needs explicit confirmation under the operation's rules.
Never silently overwrite either a valid user value or conflicting planned data.

## 5. Introduce Structured Questions and Answers

Extend the session model with these small records rather than encoding behavior
inside question strings:

| Record | Essential fields |
|---|---|
| Parameter candidate | Value, source/evidence, device/operation scope, validation outcome |
| Question | Stable ID, task/binding ID, device ID, nested field path/item ID, issue type, wording, expected schema, dependencies, revision |
| Option | Stable ID, typed value, label, source reference/revision, matching explanation |
| Answer | Question ID/revision, answer kind (`selection` or `custom`), selected IDs or raw input |

Offer single or multiple selection according to the field's schema. Keep option
identity separate from its numeric value: selecting option 1 must not be confused
with entering the literal value 1.

After analyzing all tasks, build the pending queue. Resolve operation/target
questions before dependent parameter questions. After an answer, refresh only
affected questions and validations, preserving the rest. Reject stale answers
when their question revision or source context has changed.

Support explicit correction of an earlier accepted field. Such corrections must
invalidate dependent questions/validation and any previously rendered artifacts.
Keep session history and sufficient provenance to explain every accepted value.

## 6. Terminal Interaction and Future UI Contract

Example presentation:

```text
Configure OSPF | R1
Which interface should participate?

1. Ethernet1/1 - inventory: inter-router interface
2. Loopback0   - inventory: loopback interface

Custom answer: [________________________]
```

The terminal uses explicit commands such as `select 1` or `value Ethernet1/1`.
A future website can display option controls and a custom-input box using the
same question data. When there are no relevant choices, show an input-only
question. Large candidate sets need filtering/pagination, not an unlimited dump.

Custom input is always available for the user to propose an answer, but it cannot
bypass inventory or schema rules. If none of the recorded interfaces are correct,
request a target correction or flag missing inventory data; do not invent an
interface or edit the source of truth as a side effect of answering.

## 7. Separate Collection, Validation, and Rendering

Refactor `_finalize_task()` so collecting/validating does not call Jinja.
Use explicit task states for collecting, needing clarification, validated,
rendered, and failed. The request can render only when every required binding is
validated and there are no unresolved questions or errors.

Before rendering, recheck full schemas, per-device context, supported templates,
and relevant cross-task conflicts. Recheck source/catalog revisions used during
collection; if they changed, revalidate affected decisions. Do not publish a
complete rendered plan if one template fails.

Keep vendor template selection deterministic. Existing templates are selected by
vendor/category/operation; platform/version compatibility needs explicit metadata
and template tests before claiming support for a particular device release.

## Implementation Order and Ownership

1. Fix acceptance and alias boundaries in `pipeline.py`, `parameters/validator.py`,
   `parameter_extractor.py`, and `devices/context_validator.py`.
2. Extend `planner/models.py` and planner output with bindings, candidate evidence,
   and typed question/answer state; support existing saved-session migration.
3. Add bounded planning/association repair and per-binding extraction.
4. Add the small context resolver, approved lookup metadata, and planned JSON data.
5. Update `clarification.py` and `main.py` for the dependency-aware queue and
   selection/custom-answer contract.
6. Separate whole-request validation/rendering, then update tests and handoff docs.

No new orchestration framework or database is required. Extend existing modules
where they own the behavior; introduce separate components only for context lookup
and shared question/candidate contracts.

## Acceptance Criteria

- Both operation/device mapping examples above produce the correct bindings.
- A missing target produces an inventory-backed question; descriptive refinement
  preserves valid constraints without modifying operation parameters.
- Missing interfaces offer scoped inventory choices; absent planned values produce
  input-only questions. Suggestions carry identifiable source evidence.
- Conflicting alternatives in the prompt are surfaced rather than taking the first.
- A known interface with a missing area retains its identity; separate interfaces
  can receive different areas without values leaking between devices or tasks.
- Invalid integers, out-of-range values, invalid addresses, and inventory mismatch
  leave accepted state unchanged and receive specific feedback.
- `255.255.255.0` cannot bypass address-field rejection, and `Ethernet1/10` cannot
  silently become `Ethernet1/1`; test the real parsing path, not an empty mock.
- Option selection and numeric custom values remain distinguishable. Custom input
  obeys the same domain rules and cannot invent inventory objects.
- Bounded LLM repair never supplies unsupported values or removes unresolved
  evidence; model/service failures retain recoverable session state.
- Resume, correction, stale-answer rejection, and source-context changes preserve
  valid work while revalidating affected decisions.
- No rendering occurs until the entire request is validated; rendering failures
  never mark a partial output as a completed plan.

This revision aims for predictable, testable handling of uncertainty. Finite tests
and a weak model cannot establish impeccable natural-language understanding;
explicit clarification remains the required outcome when meaning is unresolved.
