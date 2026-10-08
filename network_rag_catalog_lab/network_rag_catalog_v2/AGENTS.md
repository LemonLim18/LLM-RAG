# Repository Engineering Instructions

## Authority and precedence

Read these documents before changing product behavior:

1. `app_main_documents/00_PRODUCT_VISION.md` — authoritative current product scope.
2. `app_main_documents/01_ARCHITECTURE.md` — verified facts, preliminary boundaries, and unresolved decisions.
3. `app_main_documents/02_ITERATION_PROTOCOL.md` — mandatory delivery and handover process.
4. `app_main_documents/03_DEVELOPMENT_PROGRESS.md` — current status and known issues.
5. `app_main_documents/04_ARCHITECTURE_DECISIONS.md` — established decisions and rationale.

The explicitly assigned current iteration takes precedence over future roadmap suggestions. Never begin a later iteration automatically.

`app_main_documents/1st_step_chatgpt_prompt.md`, `1st_step_chatgpt_prompt_revised.md`, and `1st_step_implementation.md` are preserved historical sources. Use the precedence defined in `00_PRODUCT_VISION.md`. The old combined Phase 0 + Phase 1 implementation instruction is superseded and must not be executed.

## Engineering rules

- Deliver exactly one independently testable outcome per iteration with explicit in-scope and out-of-scope boundaries.
- Make minimal coherent changes; do not perform unrelated refactoring or speculative roadmap work.
- Limit inspection to the areas needed for the assigned deliverable.
- Preserve V9 as the authoritative AI engine and keep its CLI usable.
- Do not duplicate V9 planning logic in the frontend or replace it with the previous FYP intent parser.
- Reuse FYP code only after the required source-level assessment and an explicit decision.
- Run targeted verification, record exact commands and outcomes, and distinguish pre-existing failures from new regressions.
- Use the workspace Python environment at `C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/.venv` for installs, backend commands, and Python tests; do not fall back to global `py -3`.
- Preserve unrelated and pre-existing working-tree changes.
- Do not commit, merge, delete, reset, publish, install dependencies, or make destructive changes without explicit authorization where required.
- Report partially completed or blocked work honestly. Complete the iteration handover and update progress before stopping.

Follow any more specific `AGENTS.md` that applies to a nested directory, provided it does not conflict with these authoritative project rules or the current assignment.
