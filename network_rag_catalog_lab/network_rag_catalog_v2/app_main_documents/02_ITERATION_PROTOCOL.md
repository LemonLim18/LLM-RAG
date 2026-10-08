# Iteration Protocol

**Status:** Mandatory engineering protocol for work performed after Iteration -1.

## Core rule

Each iteration must deliver exactly one independently testable outcome. An iteration is not permission to continue into the next roadmap item, even when time or allowance remains.

## Before implementation

Every assigned iteration must state:

- A unique identifier and one-sentence objective.
- One independently testable deliverable.
- Explicit in-scope files, behaviors, and interfaces.
- Explicit out-of-scope behaviors and roadmap items.
- Acceptance criteria that can be verified in the current environment.
- The expected targeted tests or other verification method.
- Known prerequisites, assumptions, and relevant baseline failures.

The current explicitly assigned iteration overrides future roadmap suggestions. Historical documents are context, not standing implementation instructions.

## Mandatory engineering rules

1. Make the smallest coherent change that satisfies the assigned deliverable.
2. Do not perform unrelated refactoring, cleanup, dependency replacement, or style conversion.
3. Inspect only the repository areas needed to understand and verify the assigned change. Do not conduct uncontrolled repository-wide exploration.
4. Preserve the working CLI and established V9 behavior unless the iteration explicitly authorizes a compatible change to them.
5. Do not duplicate V9 planning semantics in the frontend or substitute the previous FYP intent parser.
6. Do not speculate future roadmap features into current code, schemas, interfaces, or dependencies.
7. Use targeted tests appropriate to the affected code and risk. Add or update tests when the deliverable changes testable behavior.
8. Record exact verification commands and outcomes. Distinguish new regressions from reproduced, pre-existing failures; never describe an unrun test as passing.
9. Preserve unrelated user changes and existing dirty-worktree changes. Stop and seek direction if the assigned work cannot avoid overwriting them.
10. Do not automatically create Git commits, branches, merges, tags, releases, or destructive changes. Each requires explicit authorization where applicable.
11. Do not automatically start the next iteration. Finish the report and stop.
12. Update the handover and progress documentation before stopping, including an explicit incomplete status if any acceptance criterion is unmet.

## Scope and change control

If a necessary change falls outside the stated scope, first determine whether the deliverable can be completed safely without it. If not, report the dependency and request a separately scoped iteration. Do not silently expand the iteration.

A narrowly required compatibility edit may be proposed, but it must be called out before or in the iteration report with its reason, risk, and verification. A new product feature is never a compatibility edit.

## Verification protocol

- Select the narrowest tests that exercise the changed behavior and its important boundary.
- Run relevant static checks, build checks, or document validation when executable tests do not apply.
- Record commands exactly as run, including working-directory assumptions when material.
- Record pass, failure, skipped, timeout, or environment-blocked outcomes accurately.
- For a failing baseline, compare against the unchanged behavior where practical and identify whether the failure is pre-existing, changed, or unclassified.
- Do not weaken tests, suppress errors, or broaden mocks merely to obtain a green result.
- When external dependencies such as local Ollama are unavailable, state the limitation and use only previously authorized deterministic substitutes. Do not present substitute evidence as a live integration result.

## Completion status

Use exactly one of these statuses:

- **Completed:** Every acceptance criterion is met and verification is recorded.
- **Partially completed:** A recoverable deliverable exists, but one or more acceptance criteria remain unmet.
- **Blocked:** The deliverable cannot progress coherently without user input, new authorization, an unavailable dependency, or resolution of a material external condition.

Incomplete work must never be reported as completed. A partially completed or blocked iteration must describe the last recoverable state and the precise condition needed to continue.

## Standard iteration report

Every iteration handover must contain these sections in this order:

1. **Iteration identifier and objective.**
2. **Completion status:** completed, partially completed, or blocked.
3. **Files added, modified, or removed.** State explicitly when none were removed.
4. **Architectural decisions and reasons.** Include decisions intentionally deferred.
5. **Tests run, with exact commands and outcomes.** Separate passing checks, failures, pre-existing failures, and tests not run.
6. **Remaining issues and risks.** Include environment constraints and unverified assumptions.
7. **Suggested next iteration.** Recommend one independently testable deliverable; do not begin it.
8. **Exact reproduction/verification instructions.** Provide the commands and observable result needed to verify the deliverable.

The report must also update `03_DEVELOPMENT_PROGRESS.md` when iteration state, known issues, or planned sequencing has changed materially.

## Quota-aware stopping rule

When a task expands beyond its planned scope or there is insufficient allowance to implement and verify it coherently, stop adding features. Preserve a recoverable working state, record what is complete and unverified, document the remaining work and risks, and request a separately scoped iteration.

Allowance pressure never changes partial work into completed work and never justifies skipping required verification.

## Stop condition

After the single deliverable is verified and the mandatory report is complete, stop. Wait for explicit authorization before implementing the suggested next iteration.

