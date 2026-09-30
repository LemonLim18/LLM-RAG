# Retrieval and operation selection

## Actual path

`pipeline._process_intent` first calls `operation_selector._explicit_operation(request_text, load_operations())`. This scans active operation display names and aliases with word-boundary regexes and returns a unique longest match. **Literal matches do not use Chroma.** If none, `category_classifier.classify_category` tries `catalog.category_for_text` (category display names/aliases); otherwise it sends the active category list and clause to the Ollama `llm`, accepts only a known category ID, or raises.

`operation_retriever.retrieve_operation_candidates(prompt, category, k=3)` calls `vectorstore.get_vectorstore` then `similarity_search_with_score(..., filter={"category": category})`. Each document's `operation_id` is rechecked against `catalog.get_operation`; inactive/unknown IDs are dropped. In published mode release ID, operation version and category metadata must agree with the current snapshot or retrieval errors. Candidate dictionaries include ID, category, description, vendor-support JSON and `distance`; lower distance is better for the default metric. The retriever does not by itself decide the operation or ensure three usable candidates remain.

`operation_selector.select_operation` first tries `_explicit_operation` **within candidates**, then gives candidate descriptions and support metadata to the local LLM. It accepts only a candidate ID; `null`, invalid JSON or a non-candidate ID gets one repair attempt, then raises. `pipeline._process_intent` records `OPERATION_PROPOSAL` for this semantic route; user confirmation is a separate gate.

## Index construction and identity

- Default files mode: `app/file_runtime.file_documents` builds operation documents from direct catalog/schema/vendor-template availability. `app.ingest.ingest_files` inserts/upserts in Chroma collection `network_operation_catalog`, removes stale IDs, verifies stored metadata/content and `catalog_revision`.
- `app/vectorstore.get_vectorstore` rechecks current operation IDs, `catalog_revision` and `OLLAMA_EMBED_MODEL` before a files-mode semantic search. A changed catalog/template/schema can make retrieval fail until ingestion; exact operation matching may still work.
- Published mode: `knowledge.publication.build_documents` includes operation version, compiled schema, parameter summaries and vendor profiles. `app.ingest.build_release_index` creates `knowledge_<release_id>` and verifies IDs/content/metadata before `publication.publish` switches `active.json`. `KnowledgeSnapshot` ensures release artifacts and active pointer match. An offline release allows literal operation selection but blocks semantic retrieval.
- `app/embeddings.py` supplies Ollama embeddings; `app/config.py` names `nomic-embed-text`. `app/llm.py` names the local text model. No retrieved score threshold is enforced in `retrieve_operation_candidates`; candidate filtering plus confirmation are the downstream controls.

## Who owns a change?

| Change | Source owner | Follow-up |
|---|---|---|
| Category IDs/aliases/descriptions/display names | `data/catalog/categories.json` in files mode; management authoring in published mode | Reingest or publish; `category_for_text` tests ID/aliases, while LLM listing includes display name/description |
| Operation aliases/use cases | `data/catalog/operations.json` or management records | Reingest/publish |
| Retrieval count | `pipeline._process_intent` passes `3`; retriever default also `k=3` | Test candidate/selector behavior |
| Retrieval document text | `file_runtime.file_documents` (files), `publication.build_documents` (published) | Rebuild matching index |
| Embedding model | `config.OLLAMA_EMBED_MODEL`, `embeddings.py`, `vectorstore.py` | Rebuild index; published release requires new publication |
| Selector prompt/repair | `retrieval/operation_selector.py:select_operation` | Focused selector tests |
| Exact phrase shortcut | `operation_selector._explicit_operation` and catalog aliases | Check ambiguous longest-match cases |
| Category LLM prompt | `retrieval/category_classifier.py:classify_category` | Test misclassified categories |

Failure example: a correct operation omitted from the top three cannot be selected, because selector IDs are restricted to those candidates. Another failure: wrong category classification filters out the right operation before retrieval. This is why the catalog phrase shortcut, RAG indexing and confirmation are separate decisions.
