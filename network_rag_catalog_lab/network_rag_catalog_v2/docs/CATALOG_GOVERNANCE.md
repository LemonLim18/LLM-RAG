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
5. Add approved inventory/planned lookups and conflict resource keys to
   `data/catalog/context_rules.json`. Do not expose unrelated inventory fields
   as configuration values. Declare platform/releases in `template_support.json`
   only after reviewing the templates for that environment.
6. Run `python -m app.ingest` and `python -m unittest discover -s tests -v`.

`validate_catalog()` runs before planning and ingestion. It rejects duplicate IDs,
missing schemas/templates, undefined parameters, incompatible parameter types,
and invalid vendor-required fields.

`validate_context_catalog()` checks approved lookup paths, planned record IDs,
device/operation scopes, revisions and typed candidate values. A planned record
must have `id`, `device_id`, `operation_id`, `field`, `value`, `kind`, `source_ref`
and `revision`. `when` scopes a value to dependencies such as an interface name.
`candidate` values are suggestions. `intended_assignment` conflicts require
explicit confirmation and an operation that allows plan override. `fact`
conflicts cannot be overridden by a user answer. No answer edits these files.

Nested schema fields can use `x-parameter-id` to reuse central metadata under a
different structural key; OSPF `interfaces[].name` references `interface` labels.

## Change an operation

- Change `display_name`, aliases, clarification wording, or descriptions in the
  central catalog. These are shared by terminal prompts, RAG documents, and a
  future UI.
- Increase the operation `version` whenever behavior, schema semantics, or
  template semantics materially change.
- Rebuild Chroma after a catalog change: `python -m app.ingest`.
- Long-running processes must call `app.catalog.reload_catalog()` before the next
  request, then rebuild the retrieval index.
- Saved questions contain source fingerprints. Resuming after a context/catalog
  change revalidates saved values and rejects stale answers. Context-derived
  planned values require reconfirmation. Unknown saved-session versions fail
  explicitly instead of being interpreted as the current contract.

## Retire an operation

Set `status` to `inactive`; do not immediately delete the operation ID. Inactive
operations are excluded from planning, fallback intent splitting, and ingestion,
but their schema remains validateable for historical session inspection.

Do not delete a parameter ID or an operation ID while persisted sessions or a
future UI might still reference it. Retire first, migrate later.
