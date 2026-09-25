# Context-Aware Clarification Revision

## Delivered Flow

`request -> evidence-preserving intents -> catalog operations -> per-device
bindings -> extraction + validation + permitted context -> question queue ->
full-request validation -> staged vendor rendering -> preview`

Primary design: `implementation.md`. The secondary resolution proposal informs
inventory-based descriptions and candidate explanations. Hard inventory
constraints take precedence over model confidence or ranking scores. No guessed
confidence percentage is used to waive a contradiction.

## Component Map

| Owner | Responsibility |
|---|---|
| `planner/intent_planner.py` | Original spans, explicit shared targets, bounded planning repair |
| `devices/target_query.py`, `target_resolver.py` | Evidence-backed characteristics and authoritative all-constraint search |
| `parameters/fields.py` | Nested paths and strict active-field parsing |
| `parameters/parameter_extractor.py` | Untrusted extraction, deterministic grounding, partial items and alternatives |
| `parameters/validator.py` | Types, ranges, network semantics, duplicate interfaces and supplied-field validation |
| `context.py` | Approved inventory/planned lookup, source revisions, record validation and conflicts |
| `questions.py` | Stable question/option identities, typed answers and choices |
| `pipeline.py` | Independent bindings, validation boundaries, corrections and whole-request render gate |
| `clarification.py` | Versioned JSON sessions, queue, resume and persistence |
| `main.py` | Single-question terminal presentation, pagination, selection and custom input |

The existing 12 operations remain. Juniper BGP additionally requires a peer
group; a description is no longer reused as a group name or replaced by a hidden
default. The catalog and schemas remain the extension points.

## Terminal Example

```powershell
..\..\.venv\Scripts\python.exe main.py "Configure OSPF on R1 and R3" --interactive
```

Select an interface with `select 1`, enter its area as `0`, then respond to the
next question. R1 requires a process ID; R3 does not. Each question identifies the
operation, device, task ID and exact field path. Use `select 1,2` for multiple
interfaces. Input `1` means literal 1, never option 1. Scalar integer replies
must be integers; `process 100` is intentionally not a scalar integer answer.

Other commands: `value TEXT`, `more`, `filter TEXT`, `quit`, and
`edit TASK_ID FIELD_PATH VALUE`. Resume with `--resume SESSION_ID --interactive`.
Completed sessions can be corrected with `--resume SESSION_ID --edit TASK_ID
FIELD_PATH VALUE`. Resume rechecks source data and retries rendering if a
previous render error has been repaired.

## Future UI Contract

Use `session.next_question` to show one question. `pending_questions` contains
the queue collected across all tasks, with operation/target questions first.
Question data includes:

- `question_id`, `task_id`, `binding_id`, `device_id`, operation/device labels;
- `field_path`, stable nested `item_id`, `issue_type`, wording and expected schema;
- dependencies, question revision, source fingerprint;
- typed options, stable option IDs, source references/revisions and explanations;
- `multiple` and `allow_custom` flags.

Construct `ClarificationAnswer(question_id, revision, source_revision, kind,
raw_input, selected_ids)` and pass it to `apply_answer(session, answer)`. Use
`kind="selection"` with option IDs or `kind="custom"` with raw text. Use
`apply_correction(session, task_id, field_path, raw_text)` for explicit edits.
Clients must reuse the supplied revisions; stale or out-of-order replies cannot
mutate parameters. Rejected replies retain their reason in history/feedback.

## Context and Provenance

`data/catalog/context_rules.json` declares lookup paths for each operation.
`data/planned/parameters.json` supplies versioned, device-scoped candidates. The
included values are examples, not live configuration. All configuration choices
from this dataset require confirmation, even when only one value exists.

Inventory identity and interface aliases are authoritative facts. Planned
assignments may conflict with a requested change; eligible operations offer an
explicit override. Facts cannot be overridden. Source files are never mutated
by clarification. Management addresses are not repurposed as interface IPs.

Tasks keep accepted values with `parameter_evidence`, provenance labels, pending
candidates, source spans, questions and answer history. Nested items preserve
identity while individual fields are completed. Changing an interface/target
invalidates dependent selected planned values. Source revisions cover local
catalog, inventory, planned JSON, schemas and templates. Changed sources trigger
revalidation; previously selected planned values require reconfirmation.

## States and Rendering

Bindings use `collecting`, `needs_clarification`, `validated`, `rendered` and
`failed`. Request/session states also include `needs_confirmation` for conflicting
operations, and `ready` only for a fully rendered preview. No configurations are
exposed while another task is unresolved or if any template fails.

Conflicting changes to a shared resource require correction or explicit order
confirmation (`confirm_session_order`, terminal `confirm order`). Edits invalidate
that confirmation. Configurations retain request order. This is not transactional
execution, conflict simulation or proof that the final network state is correct.

Old JSON sessions migrate on load: old configs are discarded, bindings are split
and all values pass the new validation/render gate. Session writes use unique
temporary files and atomic replacement. Multi-process concurrency control and
user authentication belong to a future service layer, not this terminal revision.

## Verification and Limits

Run `python -m unittest discover -s tests -q` in V2 using the existing environment.
Tests exercise real extraction fallbacks, answer parsing, inventory checks,
question options, session resume, source invalidation and template rendering.
Model responses are simulated for reproducible null/failure/hallucination tests;
these checks do not measure the quality of an installed local model.

- Clear coordinated clauses share trailing targets; semicolons separate groups.
  Pronouns, exclusions and other uncertain associations require confirmation.
  A second model attempt is bounded recovery, not proof of correct interpretation.
- Literal field grounding is deliberately conservative. Unfamiliar paraphrases
  or unsupported network operations can require manual selection/clarification.
- Where distinct per-device values cannot be grounded unambiguously, collect
  them separately; arbitrary prose is not guaranteed to be understood correctly.
- Planned lookup supports declared local records and interface choices. It does
  not discover topology, allocate addresses or derive unstated design intent.
- Compatibility metadata restricts template selection to declared lab releases.
  Nonblank rendering is tested; device command acceptance and all vendor syntax
  are not certified. Existing demo templates still require NOS-level validation.
- No external integrations, website, Ansible execution or business-intent engine
  are introduced by this revision.
