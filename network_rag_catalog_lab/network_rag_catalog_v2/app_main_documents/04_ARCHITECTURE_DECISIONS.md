# Architecture Decisions

**Status:** Established product decisions from Iteration -1 plus source-backed design decisions from Iteration 0. New implementation boundaries below are selected designs, not implemented or runtime-verified services.

## AD-001 — V9 is the authoritative AI engine

**Decision:** V9 owns AI planning, retrieval, clarification, validation, rendering, target resolution, and associated session semantics.

**Rationale:** It is the current product engine and already provides structured orchestration and clarification functions. Maintaining one authority prevents divergent behavior.

**Consequences:** The frontend must not duplicate this logic. The service layer adapts V9 behavior, and changes must preserve the CLI as a regression and development interface.

## AD-002 — The previous FYP is a selective reuse reference

**Decision:** The FYP prototype is a source of candidate components and patterns, not the foundation or semantic authority of the new platform.

**Rationale:** It contains relevant React, FastAPI, inventory, Monaco-adjacent, and infrastructure-management material, but its broad scope and prior intent pipeline require source-level quality assessment.

**Consequences:** No component, schema, API, dependency, or intent code is approved for reuse merely because it exists. Iteration 0 classifications in `05_FYP_REUSE_AUDIT.md` recommend small presentation reuse and exclude the old runtime/intent controllers and externally synchronizing inventory API.

## AD-003 — React/TypeScript and FastAPI form the workbench stack

**Decision:** Use React with TypeScript for the workbench and FastAPI for the local service/application adapter.

**Rationale:** This matches the revised product requirements, the required interactive workbench, and the need to expose existing Python V9 functions through structured contracts.

**Consequences:** The HTTP boundary must be typed and structured. Exact project layout, libraries beyond the mandated stack, and FYP code reuse remain Iteration 0 decisions.

## AD-004 — Monaco is mandatory

**Decision:** Monaco Editor is the required configuration review, editing, and comparison surface.

**Rationale:** Vendor configuration is code-like content that benefits from a capable editor and diff experience, and Monaco is part of the explicit product requirement.

**Consequences:** Iteration 1 must demonstrate a functional Monaco surface. Language registration, model lifecycle, and FYP editor reuse require source-backed design rather than assumptions.

## AD-005 — The demo inventory is the initial inventory authority

**Decision:** The local, editable demo inventory is the first inventory authority, and the GUI and V9 target resolution must use the same logical device records.

**Rationale:** A shared authority prevents browser-only demo devices from diverging from V9's planning targets while avoiding premature NetBox integration.

**Consequences:** The current static JSON loader is insufficient for the complete milestone. Iteration 0 selects a validated write repository around the same JSON source; see AD-015. Concurrency and staleness behavior must pass implementation tests before CRUD is enabled.

## AD-006 — The initial milestone is local and demo-only

**Decision:** The initial milestone operates locally with synthetic devices and clearly identified sample/replay data.

**Rationale:** It enables a polished, safe demonstration before December 2026 without coupling early work to unavailable infrastructure or production controls.

**Consequences:** Live NetBox, SSH, execution, telemetry, production identity, fleet automation, and deployment are deferred. The UI must not misrepresent mock or replay behavior as live.

## AD-007 — Prefer a modular monolith

**Decision:** Build the initial workbench as a modular monolith with explicit frontend, service-adapter, V9 domain, inventory, and persistence boundaries.

**Rationale:** This minimizes operational complexity for a local demonstration while keeping future extraction and external integrations feasible.

**Consequences:** Internal modules should communicate through narrow contracts. This decision does not prescribe unverified directories, classes, database tables, or deployment topology.

## AD-008 — Generated originals and working drafts are separate records

**Decision:** Preserve each original generated artifact and store manual edits as a distinct working draft linked to that original.

**Rationale:** Reviewability, provenance, comparison, and safe iteration require the engine's output not to be silently overwritten.

**Consequences:** The UI must make the distinction visible, and persistence must retain the relationship. Exact storage and versioning semantics remain to be designed.

## AD-009 — Future services integrate through explicit boundaries

**Decision:** External inventory, connectivity, execution, telemetry, and identity services will be introduced through suitable ports/adapters when authorized.

**Rationale:** The local demo must not become coupled to a specific external service, while later production capabilities will need controlled substitution, configuration, and failure handling.

**Consequences:** Current interfaces should avoid assumptions that prevent later adapters, but speculative implementations and vendor abstractions are prohibited.

## AD-010 — Preserve the V9 CLI

**Decision:** The existing CLI remains supported as a regression and development interface.

**Rationale:** It provides an independent way to exercise V9 and protects against coupling the domain engine exclusively to the GUI transport.

**Consequences:** GUI integration should call shared functions, not parse CLI text, and targeted regression checks must accompany affected V9 changes.

## AD-011 — GUI clarification uses structured contracts

**Decision:** Clarification, correction, ordering, resumption, validation errors, and session states must cross the service boundary as structured data with stable identifiers.

**Rationale:** Terminal prompts and numbered prose are brittle application contracts and do not support a robust interactive workbench.

**Consequences:** Existing V9 session functions are the starting point. Iteration 0 defines proposed contracts in `06_GUI_INTEGRATION_DESIGN.md`, retaining question/option/task identity, evidence and task/source revisions. Transport session revisions are separate from V9 task revisions.

## AD-012 — Demonstration provenance must be explicit

**Decision:** Synthetic current-session results, static samples, mocks, and replays must be visibly distinguishable.

**Rationale:** A credible demonstration must not imply live discovery, execution, monitoring, or AI calls when those actions did not occur.

**Consequences:** Provenance becomes part of presentation and, where necessary, structured service data.

## AD-013 — The combined Phase 0 + Phase 1 instruction is superseded

**Decision:** The earlier instruction to conduct the architecture audit and immediately implement a vertical slice in one combined task is no longer active.

**Rationale:** The current governance requires one independently testable deliverable per iteration and explicit authorization before continuing.

**Consequences:** Iteration 0 is a separate audit. Iteration 1 may begin only after its scope is explicitly assigned, using accepted Iteration 0 findings.

## AD-014 — New workbench composition with narrow presentation reuse

**Decision:** Propose a new V9-root `frontend/` and later isolated `app/workbench/` FastAPI composition. Reuse the FYP ChatInput and static SVG artwork with minor changes; adapt layout/editor patterns and build new controllers.

**Rationale:** The FYP's closest shell is bound to approval, deployment and SSH. Its backend lifecycle and inventory CRUD start deferred external work. Small presentation extraction saves effort without importing those dependencies.

**Consequences:** No FYP backend import or cross-tree frontend runtime dependency. React Context/reducer plus scoped CSS is sufficient initially. Dependencies and copied assets need implementation-time compatibility/ownership checks.

## AD-015 — Existing JSON is the first shared demo inventory store

**Decision:** Keep `data/inventory/devices.json` as the single persisted inventory source; add validated atomic CRUD and content-hash revisions in a later iteration. Preserve V9 string IDs and its vendor/platform/capability model.

**Rationale:** V9 already reads the file without caching and incorporates inventory changes into source/context revisions. This avoids an incompatible FYP SQLite schema and duplicate inventory authorities.

**Consequences:** New records become visible through ordinary V9 reads. Protect identity and neighbor/planned-data references; flag existing sessions stale and revalidate explicitly. Backups live outside hashed inventory data. Initial service serialization does not claim cross-process CLI safety; simultaneous same-session mutation is unsupported until shared coordination is verified. No inventory data changed during this audit.

## AD-016 — Passive session reads and explicit resume are different operations

**Decision:** Proposed GET reads saved session JSON; proposed resume calls V9's refreshing loader. Add an opaque saved-content session token, request/answer IDs and a serialized service write boundary while retaining all existing task/question/source revisions.

**Rationale:** `load_session` clears saved task configurations and refreshes/renders. V9's atomic saves and question checks do not prevent competing session writes or identify retried requests.

**Consequences:** Stale submissions require user review. Slow V9 work runs outside the event loop with explicit operation status. Durable request recovery and CLI-change detection are implementation gates; no process wrapper around `main.py` is permitted.

## AD-017 — Workbench artifact storage is separate from V9 session output

**Decision:** Capture immutable generated originals with task/device/context identity and store draft content/revisions separately under proposed `storage/workbench/` paths. Monaco model identity follows artifact/draft identity.

**Rationale:** V9 produces inline configs and may replace them on refresh; it has no persistent draft model or arbitrary edited-command validator.

**Consequences:** Regeneration creates new originals while preserving history. Draft edits are unvalidated and never inherit the original's validation. Record exact validation scope/content hash; compare with Monaco DiffEditor, not the FYP line-set diff. Recovery between session save and artifact capture needs testing.

## AD-018 — Shell mock, local V9 and replay have distinct provenance

**Decision:** Iteration 1 uses only in-memory labelled mock data. Later local V9 and deterministic replay use explicit adapters and provenance; service failure never silently becomes replay success.

**Rationale:** Model availability, index freshness, runtime authority and synthetic inventory are independent facts. Existing V9 traces do not prove every model/retrieval call.

**Consequences:** Runtime health is read-only and cannot ingest/publish as a side effect. Replay fixtures have versioned IDs and allowed transitions isolated from live sessions. The shell contains no persistence or real API integration.

## AD-019 — Iteration 1 uses a standalone Vite frontend and reducer-owned shell state

**Decision:** The workbench is implemented as an isolated root `frontend/` Vite application. A typed React Context/reducer owns only selected device, open/active configuration tabs, per-tab content, mock messages, simulated activity, panel visibility and panel dimensions.

**Rationale:** This realizes the Iteration 0 structure with the smallest coherent state boundary and avoids importing the FYP's service-coupled controllers or adding a competing state library.

**Consequences:** All Iteration 1 data is local fixture state and resets on reload. Future HTTP integration must enter through typed feature services without moving V9 semantics into the reducer. The FYP ChatInput callback contract and static router artwork were adapted into dependency-free components; no FYP runtime import exists.

## AD-020 — Monaco is bundled locally with stable per-tab models

**Decision:** Use `@monaco-editor/react` with the local `monaco-editor` package, an explicitly configured local editor worker, a small `network-cli` language definition, and a stable URI model path per sample configuration tab.

**Rationale:** Local worker loading prevents CDN/network dependency, while stable models preserve editor state independently across tab switches and provide a clean future artifact/draft identity seam.

**Consequences:** Iteration 1 uses one ordinary Monaco editor and in-memory documents only. DiffEditor, persisted drafts, generated-original immutability, validation records and bundle optimization remain later independently testable deliverables.

## AD-021 — Passive runtime status is a separate FastAPI boundary

**Decision:** The first service composition is `app.workbench.api:app`, with only `GET /api/v1/health` and `GET /api/v1/runtime/status`. It reads V9's existing runtime mode, authoring authority marker and active published-release pointer directly; it does not wrap the CLI or call session/planning functions.

**Rationale:** These sources accurately identify the configured and effective knowledge authority without initializing models, opening Chroma, refreshing sessions or causing knowledge side effects.

**Consequences:** Service reachability and knowledge authority are independent from AI, embedding and retrieval readiness. Unprobed capabilities return `not_checked`. Direct-file mode returns `active_release_id: null`; it never fabricates a release identity. The API package remains a thin adapter, not a second runtime configuration system.

## AD-022 — Frontend connectivity is resilient and separately configured

**Decision:** The frontend uses a small typed fetch client with a relative `/api/v1` default, `VITE_API_BASE_URL` for deployed builds and `VITE_DEV_API_TARGET` for the development proxy. The status bar owns the passive connection presentation and retry action without adding connection state to the workbench reducer.

**Rationale:** Connectivity is external synchronization state rather than durable workspace state. A feature-local hook keeps the Iteration 1 reducer focused and prevents API failure from blocking Monaco or mock interactions.

**Consequences:** Loading, connected, transport-disconnected and HTTP-error states are explicit. Development CORS defaults only to the two local Vite origins and can be overridden by `NETWORK_RAG_CORS_ORIGINS`. A connected status endpoint does not turn mock chat, sample inventory or sample configuration into live V9 data.

## AD-023 — Read-only inventory is a safe projection of V9's existing authority

**Decision:** Both inventory endpoints call the existing uncached `app.devices.inventory.load_inventory()` function. The adapter returns an explicit typed projection with `source: synthetic` and a SHA-256 revision of the canonical loaded records; it does not parse or persist a second dataset.

**Rationale:** The target resolver already uses `load_inventory()` by default. Reusing it guarantees the GUI and V9 observe the same stable device IDs, hostnames, vendor/platform facts, interfaces and capabilities while preventing transport exposure of operational metadata not needed by this UI.

**Consequences:** Ansible metadata, monitoring labels, source references and management addresses are not exposed. A future editing iteration must validate and atomically replace the same `data/inventory/devices.json` source; subsequent ordinary GUI and target-resolver reads will then discover the new record without synchronization or mirroring. Write concurrency, reference integrity and stale-session behavior remain future gates.

## AD-024 — Inventory state may fail independently from the sample editor

**Decision:** API inventory loading, revision, selection and retry live in the existing workbench state, while sample Monaco documents retain their own immutable display snapshot and in-memory contents.

**Rationale:** The explorer needs a shared selection visible to the status bar, but loss of the read-only inventory service must not erase or block sample editor documents.

**Consequences:** The explorer has honest loading, ready, empty and error states and never falls back to hard-coded device records. Selecting a device activates a matching sample document when one exists; devices without a sample document remain selectable without inventing configuration. Monaco and mock chat remain usable during API failure.

## AD-025 — Creation is a thin worker-backed, single-process V9 adapter

**Decision:** Iteration 4 adds only `POST /api/v1/planning/sessions`, using strict request validation, existing `create_session` / `session_to_dict`, V9 plan dataclasses and its original atomic session persistence. A synchronous FastAPI endpoint runs in the worker pool. A per-application gate serializes creation; busy requests fail explicitly.

**Rationale:** This supplies the requested independently testable creation workflow without implementing the broader operation queue/polling/journal architecture proposed in Iteration 0. Planning and vendor decisions remain in V9; its snapshot context is established inside the worker. Passive routes do not import/call the creator on a health request.

**Consequences:** HTTP 200 carries the actual V9 session state, including unresolved/failed/clarification states, not a deployment-success claim. Propagated errors are sanitized HTTP errors; V9-caught problems retain their task feedback. No subprocess CLI wrapper, new planner or session database. The saved-byte hash is informational until a later mutation-concurrency boundary is implemented.

## AD-026 — Bound creation retries without claiming durable exactly-once behavior

**Decision:** Require a client UUID; retain up to 256 completed/in-progress/error outcomes per backend process without eviction. Repeated identical requests reuse the outcome; conflicting payloads/in-flight retries return 409. Frontend submission uses an immediate pending guard, a 120-second request bound, manual same-ID retry and no automatic fallback or retry.

**Rationale:** Accidental duplicate clicks and same-process response loss can be handled without inventing a second persistence system. Durable journaling and worker cancellation require separately scoped implementation and recovery tests.

**Consequences:** Run one local Uvicorn process without reload during requests. Browser timeout/disconnect does not stop V9; the existing creator may save after the browser has given up. Restart loses deduplication and can make a retry create another session. Inspect saved JSON before resubmission after an ambiguous failure/restart. Cached terminal failures do not rerun until the user intentionally starts a new request ID. Capacity exhaustion is explicit, not silent eviction. These limits are user-visible and documented, not claimed resolved.

## AD-027 — Local V9 results and demo chat remain visibly separate

**Decision:** Use an explicit mode selector and a small provider-owned planning hook. Preserve the full server result and display its stable task/question identities and evidence. Keep Monaco sample edits, synthetic API inventory, simulated activity and mock messages clearly separate from real V9 creation.

**Rationale:** Panel toggling must not discard pending work or enable duplicates, while API failure must not block Monaco or impersonate an AI response. V9 may use deterministic fallback even when a real session is created.

**Consequences:** Pending questions have no answer controls in Iteration 4. Generated text is read-only session output, not a Monaco draft. Real model and retrieval participation is verified separately by an opt-in delegating probe, not inferred from health, session status or installed model tags. Browser state resets on reload; V9 sessions remain on disk.
