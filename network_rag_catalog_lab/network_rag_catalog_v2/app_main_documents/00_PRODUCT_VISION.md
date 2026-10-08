# Product Vision and Current Scope

**Status:** Authoritative product scope established in Iteration -1.

This document consolidates the current product direction. Historical vision and implementation documents remain useful context, but they do not override this document or the explicitly assigned iteration.

## Requirements precedence

When requirements disagree, use this order:

1. The latest revised GUI requirements in `1st_step_chatgpt_prompt_revised.md`.
2. Explicit constraints in the currently assigned task or iteration.
3. The long-term vision in `1st_step_chatgpt_prompt.md`.
4. Earlier implementation plans, including `1st_step_implementation.md`, as background only.

The earlier combined Phase 0 + Phase 1 implementation instruction is superseded. It must not be executed as a current instruction.

## Long-term platform vision

The product will evolve V9 into a VS Code-inspired, AI-assisted infrastructure management workbench. It should provide one coherent environment in which infrastructure engineers can inspect inventory and topology, express operational intent, review the AI engine's structured plan, resolve ambiguity, compare and edit generated configuration, approve controlled changes, and eventually observe execution and operational state.

V9 remains the authoritative AI planning engine. The workbench will expose its planning, retrieval, clarification, validation, rendering, and session capabilities through stable application boundaries rather than reimplementing those semantics in the browser. Deterministic validation, policy, authorization, and approval controls must remain distinct from probabilistic AI assistance.

The long-term direction may include external inventory systems, deployment engines, device connectivity, discovery, telemetry, production identity and access controls, and fleet automation. Those capabilities are a roadmap, not authorization to implement them now.

## Current demo-only milestone

The current milestone is a polished, working local demonstration targeted for completion before December 2026. It is intentionally constrained to synthetic or otherwise safe local data and contains:

- A React and TypeScript workbench with a left infrastructure explorer, central workspace, right AI chat, and bottom activity/output panel.
- Monaco Editor surfaces for reviewing, editing, and comparing generated vendor configuration.
- A central, editable demo-device inventory that is persisted locally and is intended to provide the same device records used by V9 target resolution.
- A FastAPI service layer that adapts existing V9 planning, retrieval, clarification, validation, rendering, and session functions.
- Structured GUI clarification and session handling; terminal output and numbered CLI selections are not an application API.
- Multi-device and multi-intent configuration previews.
- Separation between original generated artifacts and manually edited working drafts.
- Selective reuse from the previous FYP prototype only after a source-level quality and fit assessment.
- Local/demo execution using synthetic device records, with sample or replay sessions clearly labelled wherever live behavior is not available.
- Preservation of the existing V9 CLI as a regression and development interface.

The frontend must not duplicate V9 planning logic or replace it with the previous FYP intent parser.

## Deferred capabilities

The following are out of scope until explicitly authorized:

- NetBox integration.
- SSH connections to devices.
- Ansible or Terraform execution.
- Live monitoring, discovery, and telemetry.
- Production authentication and authorization.
- Server-fleet automation.
- Live infrastructure configuration deployment.

Mock controls or representative views may support a coherent demonstration, but they must not imply that deferred capabilities are operational. Disabled, sample, simulated, and replayed behavior must be labelled accurately.

## Principal user workflows

### 1. Manage the demo inventory

The user views, adds, edits, or removes synthetic devices in a central local inventory. The workbench and V9 target resolution observe the same authoritative records rather than maintaining divergent browser-only data.

### 2. Plan an infrastructure change

The user describes one or more intents in the AI chat. The service submits the request to V9 and returns structured plan, target, evidence, warning, validation, and session data suitable for GUI rendering.

### 3. Resolve clarification

When V9 requires more information, the workbench displays structured questions and choices with stable identifiers. The user can answer, correct, confirm order, resume, or cancel without parsing terminal prose.

### 4. Review multi-device and multi-intent output

The central workspace groups plan tasks and generated artifacts by intent and target device. The user can inspect validation and provenance before treating any artifact as reviewable.

### 5. Edit and compare configuration

The original generated artifact is retained unchanged. Editing creates or updates a separate working draft. Monaco provides source editing and a comparison between the generated original and the draft.

### 6. Inspect session activity

The bottom panel exposes useful local activity, validation, diagnostics, and output. Sample or replay records are visually distinguishable from results produced in the current session.

## Functional requirements

- **FR-01 — Workbench layout:** Provide the four primary workbench regions and allow the main review workflow to remain usable at normal desktop sizes.
- **FR-02 — Inventory authority:** Persist editable demo-device records locally and make one logical inventory source available to both the GUI and V9 target resolution.
- **FR-03 — V9 adapter:** Expose V9 application behavior through structured FastAPI contracts without duplicating planning semantics.
- **FR-04 — Session lifecycle:** Support creation, inspection, clarification, correction, ordering, resumption, cancellation, and clear terminal states as applicable to V9's session model.
- **FR-05 — Structured clarification:** Return questions, options, stable identifiers, validation errors, and next actions as structured data.
- **FR-06 — Multi-task preview:** Present multiple intents and multiple target devices without collapsing them into an ambiguous single artifact.
- **FR-07 — Monaco review:** Use Monaco for readable vendor-aware editing and original-versus-draft comparison.
- **FR-08 — Artifact integrity:** Preserve the generated original and track manual edits in a distinct working draft.
- **FR-09 — Evidence and validation:** Surface relevant V9 retrieval evidence, warnings, validation results, and failure states without claiming unsupported certainty.
- **FR-10 — Honest demo state:** Label synthetic inventory, mocked features, sample data, and replay sessions clearly.
- **FR-11 — CLI preservation:** Keep the V9 CLI operational as a regression and development interface.
- **FR-12 — Safe boundaries:** Do not initiate live device or external-service actions in the demo milestone.

## Initial product acceptance criteria

The initial product milestone is accepted only when all of the following are demonstrated and documented:

1. The local React/TypeScript workbench launches with the required four-region layout and a functional Monaco editing surface.
2. A user can maintain locally persisted synthetic devices, and the GUI and V9 target resolution use the same logical inventory records.
3. A user can submit an intent through the GUI and receive a structured response from a FastAPI adapter backed by V9 functions.
4. Clarification, correction, ordering, resumption, validation, and failure states used by the demonstrated workflows are represented as structured UI interactions.
5. A plan containing multiple intents and/or multiple devices can be reviewed without losing task-to-device association.
6. Generated configuration is retained as an original artifact, while manual edits are stored as a separate working draft and can be compared in Monaco.
7. Synthetic, sample, mocked, and replayed information is unmistakably labelled.
8. No deferred integration performs a live external action.
9. The existing V9 CLI and its established behavior remain available, with targeted regression evidence recorded.
10. Setup and verification instructions allow the complete local demonstration to be reproduced.

