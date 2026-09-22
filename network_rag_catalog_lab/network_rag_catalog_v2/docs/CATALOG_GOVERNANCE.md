# Catalog Governance

The catalog is the control plane for this lab. Keep IDs stable; edit labels and
aliases instead of renaming IDs that schemas, templates, sessions, and future UI
clients may reference.

## Add an operation

1. Add an active entry to `data/catalog/operations.json` with a stable
   `operation_id`, `category_id`, `version`, `display_name`, aliases, and schema path.
2. Add or reuse parameters from `data/catalog/parameters.json`. Parameter
   `value_type`, aliases, clarification text, and normalizer metadata live there.
3. Add the operation schema under `data/operations/<category>/<operation>/`.
   The schema is the only authority for required fields, because requirements can
   differ by operation and vendor. Use `x-required-by-vendor` where necessary.
4. Add one `template.j2` for every vendor currently represented in inventory.
5. Run `python -m app.ingest` and `python -m unittest discover -s tests -v`.

`validate_catalog()` runs before planning and ingestion. It rejects duplicate IDs,
missing schemas/templates, undefined parameters, incompatible parameter types,
and invalid vendor-required fields.

## Change an operation

- Change `display_name`, aliases, clarification wording, or descriptions in the
  central catalog. These are shared by terminal prompts, RAG documents, and a
  future UI.
- Increase the operation `version` whenever behavior, schema semantics, or
  template semantics materially change.
- Rebuild Chroma after a catalog change: `python -m app.ingest`.
- Long-running processes must call `app.catalog.reload_catalog()` before the next
  request, then rebuild the retrieval index.

## Retire an operation

Set `status` to `inactive`; do not immediately delete the operation ID. Inactive
operations are excluded from planning, fallback intent splitting, and ingestion,
but their schema remains validateable for historical session inspection.

Do not delete a parameter ID or an operation ID while persisted sessions or a
future UI might still reference it. Retire first, migrate later.
