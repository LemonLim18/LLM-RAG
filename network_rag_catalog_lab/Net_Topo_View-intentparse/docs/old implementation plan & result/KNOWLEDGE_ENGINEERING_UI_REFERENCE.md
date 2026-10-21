# Knowledge Engineering UI reference

Authoritative selection (2026-10-12): latest_overview.png, latest_category.png, latest_operation.png, latest_global_parameters.png, latest_validation_publication.png in docs/reference_images. Templates retains template/template_sample 3.png, selected earlier; no newer template image was supplied. Estimates below describe the images, not claimed pixel measurements of the implementation.

## Shared visual language
Images are approximately 1672 × 941. Header is 54 px; sidebar 245–250 px; workspace begins at x270 with 20–25 px gutters. Dark navy background #071522, panels #0B1D2E, table headers #142A40, borders #203C58; white headings #F0F3FF and pale blue body #B4CDEE. Primary gradient #4730FF → #423CFF. Accents: purple #8857FF, blue #168FFF, cyan #00E6DC, green #00DBA4, pink #F629A7, yellow #FFCC00, error #FF356C. Rounded panels 10 px, inputs 5 px, badges pill-shaped. Main headings ~24 px bold, panel headings 17–19 px semibold, body/forms 12–14 px. Tables use 32–55 px rows and 12–16 px horizontal padding. Status outlines/fills communicate state; selected rows are blue-purple with a bright purple left edge. Existing CogniShield shell/routes remain authoritative for navigation behavior.

## Overview — latest_overview.png
Title with purple book tile and one-line description, followed by four equal 104 px summary cards. Remaining area has a 63% left / 37% right split. Left: four horizontal module cards, then Recently Updated table. Right: 2×2 quick actions, activity timeline, current-release card. Module icon tiles ~64 px, count separated by a vertical border, Open button at right. Cards use 12–16 px padding and 12 px gutters. Release state uses green, draft changes yellow, publication pink. All dynamic values in the live workspace come from API records; sample values belong only to the labeled preview.

## Categories — latest_category.png
Same heading and four summary cards. Body splits ~62% catalog / 38% details. Left catalog has icon/title/subtitle/Create Category, search and category filter, six-column table, count footer. Lower left is an inline create form with name, slug, description, Reset/Create. Right: selected category icon/name/status/edit, three tabs, category name/slug/description, assigned parameter pills, and operations table. Selected VLAN row has a #192877 background and purple border. Category icons vary blue/green/purple/pink/orange/gray. Details scroll independently; tabs must switch content and membership management reuses existing assignment API.

## Global Parameters — latest_global_parameters.png
Heading, four summary cards, then ~62% library / 38% form-and-usage split. Library has title/subtitle/Create, search/type/vendor filters, seven columns, pagination and rows-per-page. Form has parameter name, Type/Vendor two-column row, description, Default/Validation two-column row, and Cancel/Save footer. Usage Summary is below, with linked operation/template/category counts. Parameter badges are blue; Active badges green. Inputs ~34 px, description ~60 px. Vendor/default/global validation persistence is absent from the current parameter API: controls must identify that limitation rather than silently discard values.

## Operations — latest_operation.png
Heading/action buttons, breadcrumb, horizontal selected-operation summary, then 25% file tree / 43% Monaco / 32% details+parameters. Bottom spans full width with implementation variants table. Tree has three selectors, search, yellow folders and purple selected file. Editor includes filename/vendor/platform/version header and status bar; Jinja keywords purple, variables cyan, strings green, code light gray. Details has name/category/description; parameter rows have use toggles and required checkboxes. Variants has vendor/platform/version/file/date/actor/actions. Existing contract replacement, template save, metadata edit and variant creation APIs retained. No backend delete/format success is fabricated.

## Templates — template/template_sample 3.png
Retains selected three-column workspace: operation/vendor tree on left (~24%), template metadata + Monaco in center (~43%), parameter reference + JSON test/preview on right (~33%). Purple action buttons, green Published/yellow Draft, color-tokenized Jinja and JSON editors. Each panel has independent overflow. Existing draft template save and validation are functional; unsaved rendering has no current API and remains visibly unavailable.

## Validation & Publication — latest_validation_publication.png
Heading plus four summary cards. Middle ~57% left / 43% right: draft changes table above publication form on left; expandable Passed/Warnings/Errors above active release on right. Bottom full-width release history. Package form: name/version, notes, included-object counts, validation/build/publish controls. Green readiness, yellow warnings, pink errors. Live checks reflect real API validation; no fabricated readiness, timestamps, draft diff or history. Current API only exposes active pointer and authoring history, so unsupported release naming/build-only/rollback/history are explained and disabled.

## Implementation/verification rules
Separate workspaces use the existing route IDs and shared React context; preview never mutates the API or SQLite. Large desktop follows reference proportions. Smaller screens retain bounded workspaces and panel scrollports; never expand beyond the viewport. Browser comparison is visual, not automated pixel equivalence. Preserve actual catalog records and existing authoring/validation/publication handlers.

## Per-image dimensional notes (estimated from supplied images)

| Workspace | Main content / dominant dimensions | Typography and hierarchy | Padding / spacing / accent emphasis |
| --- | --- | --- | --- |
| Overview | Title y~68; stats y~135, h~104; body y~254; left ~870 px, right ~500 px. Four module rows ~90 px; bottom table ~200 px. | 24 px title, 17 px panel names, 14 px resource labels, 12 px descriptions, 24 px blue counts. | 14–16 px panel padding, 12–14 px gaps; module icon ~64 px; teal parameters, blue operations, purple categories, pink publication. |
| Categories | Stats h~102; catalog ~855 px wide, details ~510 px; inline create panel ~135 px; six catalog rows ~54 px. | 24 px title, 18 px catalog/details title, 14 px selected resource, 12–13 px table/form. | Catalog controls ~35 px high; detail tabs ~40 px; 16 px insets; blue/purple selection, varied category icon colors; green status. |
| Global Parameters | Library ~845 px wide; right ~525 px; creation form ~500 px over ~165 px usage card; ten rows ~43 px. | 24 px title, 17 px panel titles, 12 px table; names and required fields have stronger weight. | Search/control band ~70 px, input ~34 px, description ~60 px, table 12–16 px cell padding; cyan usage links, blue type pills, green status, red delete. |
| Operations | Summary ~80 px; middle columns ~345 / 590 / 430 px; middle h~475 px; full-width variants ~190 px. | 24 px title, 18 px selected operation, 14 px panel titles; Monaco 13 px monospace with 20 px line height. | 12 px column gaps, 10–14 px headers; yellow folders, purple selected file, cyan variables, purple Jinja keywords, green strings; compact blue/purple use toggles. |
| Templates | Three columns ~300 / 580 / 485 px; information over editor in middle; parameter reference over test input/output on right. | 22–24 px title, 16–18 px numbered panels, 12–13 px form/table, 13 px code. | 14 px gaps, 14–16 px panel padding; purple actions, green published, yellow draft; orange commands and coral quoted strings in the selected sample. |
| Validation & Publication | Stats ~90 px; left ~785 px, right ~595 px; draft/validation ~340 px, package/active release ~230 px; history ~115 px. | 24 px heading; 17 px panel titles, 12 px forms, 11–12 px validation details/history. | 12–16 px panel insets, 12 px gaps; cyan/green passed/readiness, yellow warnings, pink errors, blue Updated/purple Modified/green Added labels. |

All panels use the shared ~1 px navy border and ~10 px corner radius. These measurements scale with the existing app content area; they are estimates rather than pixel-match guarantees.

## Implemented wiring and limitations

- Separate existing view IDs retained: knowledge_overview, knowledge_categories, knowledge_engineering, knowledge_parameters, knowledge_templates, knowledge_publication.
- Existing API handlers retained for category/parameter/operation authoring, category membership, operation contract replacement, schema compilation, template revisions, validation and publication. Inline category creation uses the same revision/reason guarded edit API. Operation template save and parameter contract save remain explicit separate actions.
- Live values come from the inspected catalog. Authoring history is labeled as stored history; it is not represented as a release diff. Readiness is shown only after backend validation. Missing publication metadata says Not returned.
- Unsupported delete, global default/vendor persistence, unsaved render, build-only release, user-chosen release IDs, rollback and full release history remain disabled or explained. Global constraints still belong to operation rules. No new backend success is fabricated.
- The supplied image records/counts are isolated in the explicitly labeled reference preview at /knowledge-reference.html. Preview authoring/publication writes are disabled. Templates uses the earlier selected sample 3 dataset. The original app header/sidebar are reused; they are not exact copies of the mockup shell.

## Actual verification — 2026-10-12 +08:00

- Production build: passed, TypeScript + Vite, 3946 modules, final run 24.73 seconds. Existing DaisyUI @property and large-chunk warnings remain. Initial npm shim was missing; used its installed Node/npm CLI directly. Vite's sandbox filesystem restriction required an authorized build. No dependencies changed.
- Browser: visually compared all six separate preview workspaces with supplied references. Corrected panel density, template metadata spacing, checkbox/toggle decoration and text encoding. At 1600×900 all six workspace/document bounds fit. At actual CSS viewport 1000×750 all six document bounds fit and internal scrollports were present; viewport restored afterward.
- Interactions passed: category search (OSPF-only result), detail tab switch, parameter page 2 (rows 11–20), parameter name editing, preview save disabled, operation use toggle disables required selection when unused, operation preview modal opens, Monaco keyboard typing visibly adds an editor comment.
- Browser console error query returned no errors during inspection. Example records only; no SQLite writes or sibling V9 modifications. Live backend save/publication was not exercised in this visual verification, and backend tests were not rerun for frontend-only changes.
- Screenshot: tmp/knowledge-ui-verification/overview.png. This is visual evidence, not automated pixel equivalence. Idea 2 backend gaps listed above remain open.


### Follow-up visual verification — 2026-10-12 20:07

Scoped the Knowledge Engineering sidebar entries to the reference purple selection/accent palette, leaving other navigation groups unchanged. Deprecated release badges now use yellow. Corrected the compact-card CSS cascade so the desktop density rule cannot override small-screen card heights. Browser comparison confirmed the template metadata/status now fit and the Categories layout retains internal panel scrolling. Screenshot: `tmp/knowledge-ui-verification/categories.png`. Existing API handlers and catalog data were unchanged.

Final continuation verification: TypeScript and Vite production build passed (3,946 modules, 14.46s); existing CSS @property and bundle-size warnings remain.


### Global theme and responsive integration — 2026-10-12

The application uses Tailwind 4 and DaisyUI 5, with App.tsx setting `data-theme` on the root and storing the chosen theme. Knowledge Engineering no longer shadows DaisyUI's base/accent variables or defines independent Monaco themes. Its reusable CSS aliases resolve to global surfaces, text, borders and semantic role accents. Missing selector themes are now enabled in the existing DaisyUI configuration; Header and the isolated preview share `src/themes.ts`. Purple authoring, blue networking, cyan telemetry, pink change, green success, amber warning and red error remain distinct. Focus, hover, selected rows, form controls and status fills inherit these roles.

Monaco uses the existing `useMonacoTheme` utility; the utility applies its updated theme immediately, including Jinja/JSON tokens. Compact workspaces stack, module cards use a readable grid, and IDE panels expose native vertical resize handles when stacked. Dense tables retain horizontal scrolling. Phone navigation uses the existing collapsed sidebar behavior for Knowledge Engineering only. No API or persistence contracts changed.

Verification: TypeScript and production Vite build passed (3,947 modules, 20.52 seconds). Existing DaisyUI @property and bundle-size warnings remain. Browser exercised 180 theme/page combinations (30 available themes × six pages) with no document horizontal overflow at desktop size. Checked actual CSS viewports 390×844, 768×1024, 1367×769, plus the default desktop. A tablet Overview observation initially caught a pending navigation, so it was explicitly revisited and confirmed. Mobile card clipping found during inspection was corrected. Confirmed light Monaco `vs` / white background and dark Monaco `vs-dark` / #0f172a without refresh, colored syntax, category search surviving a theme change, and disabling Use vlan_name disabling its Required control. The preview logged one development hot-reload createRoot warning while editing its entry file; production compilation passed. There is no frontend test script in package.json, so verification used the existing TypeScript/build and focused browser checks. No backend writes or publication were performed.


### Readable page scrolling — 2026-10-12

User requested whole-view scrolling instead of compressing panels into one screen. All six Knowledge Engineering workspaces now scroll vertically at the ke-workspace boundary while the application sidebar stays fixed. Panels use content-sized rows or generous IDE row minimums, forms have 40px inputs and 90px textareas, table cells have 13px text and expanded padding, and stacked mobile workspaces expand naturally. Horizontal table overflow and Monaco's own editor scrolling remain where needed. Removed wheel overscroll containment on table wrappers so gestures reach the outer page.

Browser: all six pages exceeded the 844px workspace height (content heights 1115–1396px) with overflow-y:auto. Actual wheel scrolling reached scrollTop=488 on Validation & Publication while sidebar top remained 56px; release history and publication controls became visible. Screenshot: tmp/knowledge-ui-verification/page-scroll.png. No API contract changes.
