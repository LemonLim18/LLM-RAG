# LLM-RAG

**LLM, Retrieval-Augmented Generation (RAG), and AI-Assisted Network Engineering**

This repository is a development and experimentation workspace exploring how Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), structured intent processing, and network engineering tools can work together to support intelligent network automation and troubleshooting.

The goal is to move beyond simple chatbot responses toward systems that can understand network-related requests, retrieve relevant information from available sources, reason over technical evidence, and produce useful, traceable engineering explanations.

## Project Overview

The repository brings together work across several related areas:

- **LLM Integration and Orchestration** — Exploring language models, structured responses, planning workflows, and model-assisted engineering tasks.
- **Retrieval-Augmented Generation (RAG)** — Retrieving relevant technical information and supplying source-grounded context to LLMs.
- **Network Intelligence and Troubleshooting** — Investigating network state, configurations, topology, interfaces, VRFs, forwarding behavior, and historical events.
- **Intent-Based Network Automation** — Translating natural-language requirements into structured network operations with parameter validation and disambiguation.
- **Network Topology and Visualization** — Representing network relationships to support interpretation and troubleshooting.
- **Experimentation and Evaluation** — Testing correctness, evidence completeness, model behavior, and reliability across different workflows.

These areas are developed and evaluated incrementally. The repository contains both experimental implementations and supporting infrastructure, rather than a single finished application.

## Network AI Assistant

One of the major development directions is a source-grounded AI network engineering assistant.

Its intended workflow is:

1. **Understand the request** — Identify the network question, relevant devices, interfaces, scope, and requested outcomes.
2. **Select information sources** — Determine which authorized sources are relevant, such as network state, configuration records, topology, or event logs.
3. **Retrieve technical evidence** — Collect records while preserving their source, identity, ownership, and time context.
4. **Perform evidence-grounded reasoning** — Use the LLM to compare records, explain network relationships, and distinguish observations from assumptions.
5. **Retrieve additional evidence when necessary** — Perform bounded supplementary queries when important source-owned information is missing.
6. **Produce an engineering explanation** — Explain what the available evidence supports, what remains uncertain, and which further checks may be appropriate.

The architecture aims to separate **evidence acquisition and transport** from **LLM reasoning quality**, allowing both to be evaluated independently.

### Development Status

The current research includes bounded validation of source selection, historical configuration retrieval, device identity resolution, interface ownership, evidence delivery, and supplementary retrieval.

Reliable technical deduction, temporal reasoning, causal interpretation, and complete-answer quality remain active areas of evaluation and improvement.

The project is intended for development, experimentation, and validation. Its AI-generated conclusions should not be treated as automatically verified network diagnoses or production-safe configuration instructions.

---

## Intent Schemas (Per-Operation YAML + JSON Types)

Another important part of the repository is the structured intent-definition and validation system used for intent-based network operations.

The intent-schema directory holds **one YAML file per intent `action`** (e.g. `create_vlan.yml`, `configure_interface.yml`).

The following documentation describes that subsystem. Paths such as `../intent_graph.yml` are relative to the intent-schema directory, rather than necessarily to the repository root.

### Relationship to the Canonical Doc and Graph

**Every operation is defined in these places (keep them aligned):**

1. **`docs/intent_operation_reference.md`** — Narrative: when to use which `action`/`feature`, anti-patterns.
2. **Intent-schema directory (`*.yml`)** — **Authoritative** `required` / `optional` / `resolution_order` / `questions` for `validate_completeness`, chat disambiguation, early `evaluate_intent_tree` checks (`build_params_disambiguation_fields_from_intent`), and LLM `get_required_params_hint_for_prompt()`.
3. **`*.schema.json`** (when present) — JSON Schema for **type** validation after parameters are filled.
4. **`../intent_graph.yml`** — Lists each **operation** under a **category**; run `python -m ansible.validate_intent_artifacts` after edits.
5. **`../category_schemas/*.yml`** — Optional vocabulary-only descriptions per category for the LLM (not required/optional).
6. **`../intent_keywords.yml`** — Editable rule-based classification keywords used by `llm/intent.py`.

If you change required/optional behavior, **update the YAML and the doc together** (see the “Source of truth” section at the top of `docs/intent_operation_reference.md`).

### File Roles

| File pattern | Contents |
|---|---|
| `<action>.yml` | `action`, `feature`, `required`, `optional`, `resolution_order`, `questions` |
| `<action>.schema.json` | Typed shape for `validate_types()` in `intent_validation.py` |

### Code Entry Points

- **Loader:** `ansible.intent_validation.load_schema`, `get_schema_for_parsed_intent`
- **LLM prompt text:** `get_intent_operation_reference_for_prompt()`, `get_required_params_hint_for_prompt()`, plus `ansible.intent_artifacts` (`get_category_vocabulary_for_prompt`, `get_intent_graph_summary_for_prompt`, `get_intent_keywords_digest_for_prompt`)

---

## Development Direction

The broader objective of this repository is to explore how structured network knowledge, authorized information retrieval, and language-model reasoning can be combined into dependable network engineering workflows.

Current priorities include:

- Improving the reliability of multi-source network investigations.
- Preserving technical evidence, provenance, and historical context.
- Strengthening model reasoning over configurations, topology, operational state, and events.
- Evaluating technical accuracy and completeness independently from successful data retrieval.
- Supporting modular components and model-neutral workflows where practical.

The long-term direction is an AI-assisted network engineering environment in which responses are grounded in available network evidence rather than unsupported model assumptions.

---

## Repository Scope

This repository serves as a workspace for ongoing development, prototypes, research experiments, technical documentation, and evaluation artifacts.

Individual components may have their own documentation, dependencies, execution procedures, and maturity levels. Refer to the relevant project directory for implementation-specific instructions.

**Status:** Active development and research.

## Limitations of this lab
- `qwen2.5:1.5b` is a small local model; its planning/extraction quality is intentionally not production-grade.
- The Jinja templates are architecture/demo templates, not release-certified production templates for every NOS and Ansible collection.
- The current inventory is a JSON file. A real platform would normally query NetBox or another authoritative inventory source.
- The current version renders configuration but does not run Ansible.
- Target resolution intentionally asks for clarification rather than guessing when multiple devices are plausible.
- Vendor-specific required fields remain in schemas. Junos OSPF has no numeric
  process ID; Junos BGP now requires an explicit peer group. Template compatibility
  is restricted by reviewed operation template bindings to the lab inventory
  releases; it is not a claim of release-certified CLI syntax.
