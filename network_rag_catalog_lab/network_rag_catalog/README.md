# Network RAG Catalog Lab

Local prototype for hierarchical network-operation retrieval.

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen2.5:1.5b
ollama pull nomic-embed-text
```

## Build ChromaDB

```bash
python -m app.ingest
```

This creates `storage/chroma/`. Each operation is one retrieval chunk/document.

## Run

```bash
python main.py "Configure OSPF process 100 and enable OSPF on Gi0/0 in area 0 on R1."
```

Change `main.py` targets to `R2` or `R3` to test Huawei/Juniper rendering.

## Design

1. Qwen classifies the broad category.
2. Nomic embeds the request and ChromaDB retrieves only operations in that category.
3. Qwen selects one operation from the retrieved candidates.
4. The selected operation loads its complete JSON Schema.
5. Qwen extracts parameters.
6. `jsonschema` validates them deterministically.
7. Local inventory identifies vendor/platform/version.
8. Template selection is deterministic from vendor + category + operation ID.
9. Jinja2 renders the vendor configuration.

External systems such as NetBox, Ansible execution, telemetry and databases are intentionally omitted from this first lab.
