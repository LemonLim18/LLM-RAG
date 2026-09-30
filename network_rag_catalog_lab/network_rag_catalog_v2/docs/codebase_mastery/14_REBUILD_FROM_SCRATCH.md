# Rebuild the idea from an empty folder

This is a dependency/causality exercise, **not** instructions to replace the repository. Where “why” cannot be tied to a specific commit, it is an architectural inference from current code and retained legacy source.

1. **Minimal catalog.** Define stable category and operation IDs, names/aliases and descriptions. Without IDs the LLM's vocabulary and template paths drift; without aliases literal phrasing is brittle.
2. **Operation retrieval.** First match exact phrases. Then index operation descriptions in Chroma and allow a bounded LLM choice from retrieved IDs. This solves paraphrases but creates top-k/category failure modes and requires index freshness checks.
3. **Schema.** Give each operation an explicit required/optional/type contract. A direct `schema.json` is enough for a small library. Reused fields and future management later motivate shared `ParameterDefinition`, category membership, operation mapping/rules and `schema_compiler`.
4. **Parameter extraction.** Use the schema as the only field vocabulary. A weak model may invent missing fields or confuse IP/netmask; deterministic literal parsing, evidence grounding, nulls and provenance reduce that risk. They add domain regex maintenance.
5. **Inventory/target resolution.** A separate target argument or exact hostname string cannot reliably handle “KL core router.” Use a descriptive query with evidence; inventory resolves identity and checks every stated attribute. This adds attribute metadata, aliases and ambiguity states.
6. **Validation.** JSON Schema catches shape/range. Inventory checks interfaces/capabilities; reviewed device/resource policies catch facts such as existing trunk/VLAN, vendor-specific restrictions and cross-task resource conflicts. This layer exists because syntactically valid config can be wrong for the actual device.
7. **Templates.** One operation/vendor template turns validated parameters into CLI. Direct directory lookup is simple; explicit published bindings add platform/version compatibility and input contracts. StrictUndefined catches missing inputs; deterministic derivations handle masks/wildcards.
8. **Clarification.** Instead of failing or inventing values, turn issues into field-scoped, prioritized questions with options/custom answers. Question IDs and revisions prevent a reply intended for one field/source snapshot from mutating another. This adds a state machine.
9. **Persistence.** Store plan/questions/history in local session JSON so the next reply resumes a task rather than rerunning the whole prompt. Revalidation on load is necessary because files/inventory may have changed. This is not yet multi-user state infrastructure.
10. **Knowledge authoring.** When many operations share parameters and teams edit them, typed repositories, management service, revision checks and optional SQLite transactions help avoid partial/dangling changes. For direct terminal experimentation, these are additional platform capabilities, not prerequisites to generate one config.
11. **Publication/versioning.** A draft catalog and a live runtime must not mix schema/template/index revisions. Compile and validate, copy immutable artifacts, build a release-specific Chroma index, then atomically activate a pointer. The cost is two modes and release governance. Current files mode deliberately retains a simpler direct path for prompt tests.

## Earlier conceptual system

```text
Prompt -> category -> Chroma -> operation -> schema.json
       -> extracted values + target hostname -> vendor template -> config
```

## Current system around that core

```text
Prompt -> multi-intent planner -> exact or category/RAG/LLM operation proposal
       -> evidence-backed target query -> inventory constraint resolver
       -> per-device task -> direct or published schema
       -> deterministic + LLM extraction with evidence/provenance
       -> schema + device/resource/planned-context validation
       -> question/session loop (or cross-task order confirmation)
       -> direct or release-bound vendor template -> staged whole-plan render

Separate knowledge lane:
pack/review or manager -> JSON/SQLite authoring -> schema compilation
                     -> publication + release-specific Chroma -> active snapshot
Direct lab lane: data/ -> file validation -> direct Chroma ingestion -> runtime
```

Some complexity came from later scope, not a fundamental need for the first demo: GUI-ready normalized catalog, transactional SQLite authoring, pack promotion, vendor/profile binding governance and immutable releases. Removing those would simplify direct file experimentation but sacrifice safe team authoring and coherent published rollouts. Removing evidence, field-scoped clarification or inventory cross-checking would directly weaken the original goal of trustworthy prompt-to-config generation. See `00_REPOSITORY_AND_DATA_MAP.md` for a longer evidence/inference-tagged architectural history.
