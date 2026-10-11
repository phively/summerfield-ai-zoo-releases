# Career Coach preferences and storage

Read this reference when reusable coaching or output preferences could change the task, when selecting a destination for a new durable record, or when the user requests a settings change. [handoff-contracts.md](handoff-contracts.md) owns capability boundaries and record authority; this reference owns the shared settings schema, precedence, discovery, and update procedure.

## External authority and ownership

The user owns the settings and authorizes their values. Reuse the existing external `career-coach-preferences.md` authority in the user's selected Library or project, including an authoritative equivalent. Preserve its verified provider, container, immutable resource ID when available, durable path or link, and role. Never store user values, a duplicate profile, or a durable cache in plugin/skill packages or their installation directories. Updating or reinstalling a package must not initialize, migrate, or replace external records.

All five Career Coach skills may read relevant settings. Any of them may maintain only coaching/output preferences and storage settings through the bounded update procedure below when the user has explicitly authorized that exact change. This common procedure is the sole settings-maintenance protocol. Reusable career goals and work/management/location criteria belong to `career-direction`, development execution to `professional-development`, and opportunity-specific state to `evaluate-opportunity`; route those changes to their existing owner rather than adding them to the settings file. Interview preparation and one-time instructions remain task-specific.

An already resolved authoritative pointer or explicitly designated resource takes precedence over filename discovery. If none is supplied, search only the accessible user-selected scope for `career-coach-preferences.md` or its equivalent. A Remember Me index may supply a pointer when available; it is optional and does not become a copy or writer of Career Coach settings. Identify whether a returned file is canonical or a backup. Read the live authority before consequential use or writing; backups may show provenance or prior configuration but never silently become current authority. Do not embed a particular user's IDs or provider choices in the package.

## Settings schema

Preserve existing sections and equivalent metadata. Add sections only as part of an authorized change; this schema alone is not permission to edit records.

| Section | Fields |
| --- | --- |
| Record identity | Owner (user), provider, container, durable path/link, resource ID when available, last updated, last verified |
| Career Coach preferences | Only confirmed reusable coaching, questioning, analysis, writing, formatting, or output choices; scope, source, and effective/verified date for material values |
| Storage settings | One entry per record role: provider, container or repository, branch for GitHub, durable path or resource ID, canonical link when supported, verification date; distinguish a new-record destination from an existing canonical identity |

Storage roles are `preferences`, `career-direction-current`, `career-direction-history`, `professional-development-current`, `opportunities-current`, `opportunities-history`, and `captured-postings`. A history destination may reference its current companion's location. A posting destination may be a directory/prefix; resolve each file's exact identity when created. Existing records may use different providers: do not require all roles to share a provider. Keep current/history companions together unless the user's existing arrangement explicitly identifies another authoritative relationship. Store pointers to career records here only when useful for discovery; do not duplicate their contents.

Google Drive, Library, GitHub, and other user-selected stores are eligible only when actual tools support the required operations. No provider is preferred by this package. Selecting a destination is not proof of access or permission to write. For GitHub, resolve repository, branch, path, and current revision; for Drive or Library, resolve the container and resource identity using available tools. Do not invent a Library API, cross-provider transaction, or unavailable connector.

## Resolve the task and destination

1. Use explicit current-task values first. Read only relevant current settings when a reusable default could change the result or a new-record destination must be resolved. A narrow edit with sufficient supplied context needs no record search.
2. For discretionary choices, apply explicit task instructions, then applicable explicit project settings, then verified reusable Career Coach settings, then a neutral task-only default. Preserve conflicts and identify the winning value when material. Stored choices never weaken factual accuracy, evidence integrity, non-fabrication, or the owning workflow's authorization boundary. A conflicting stored instruction needs explicit current-task confirmation before use, even if it is normally a default.
3. Existing canonical records retain their identity. Resolve them through known pointers or bounded discovery; a changed creation default does not move, copy, or relabel them. An explicit request to change an existing record's destination is a migration and must follow its owner's lifecycle protocol with separate migration authorization. Do not silently treat a temporary storage override as migration.
4. For new records, use the explicit task destination, otherwise the applicable verified storage setting. Ask one focused question for only the unresolved role/provider/location/branch needed to proceed. An existing posting location recorded in the opportunity authority may supply a verified default. Do not substitute Drive, another available provider, or a backup because the chosen destination is unavailable. Return `needs_focused_input` for unattended work requiring a missing decision; otherwise continue with a labeled proposal without saving.
5. A statement such as “use GitHub for this posting” affects this task only. Persist it as a default only if the user explicitly requests that persistence; a preference read or task write does not authorize a settings update.

## Bounded settings updates

1. Resolve the exact canonical settings resource and read its latest complete state, including its current revision when the provider supports it. If ambiguous, inaccessible, or partly readable, stop the write and provide a proposed patch; never overwrite unknown fields or create a replacement.
2. Establish the exact authorized fields, values, scope, and destination. Reuse authorization already given in the request; do not ask again for the same change. If persistence was not authorized, keep values task-only. Inferences or materially different changes require confirmation.
3. Initialize only a confirmed-missing authority at the user-designated external path after exact save authorization. A search miss is not confirmation of absence. Preserve unrelated values and existing record identities; make the smallest in-place edit.
4. Use revision/expected-head checks when supported. If the resource changed, reread it and reconcile only the authorized fields. Stop on conflicting values or changed authority; never force-write. Attempt at most one reconciled retry, only when current authorization covers it; otherwise request fresh authorization.
5. Read back the saved state and verify the authorized fields and preservation of unrelated values. Only a verified update supplies defaults to subsequent tasks. Report the exact resource and changed scope without reproducing unrelated personal content.

## Failure and maintenance

- **Confirmed missing:** use supplied task values or focused intake. Create the settings record only under the initialization rule above.
- **Unavailable or stale:** preserve uncertainty; use explicit task values and neutral discretionary defaults where safe. Ask for current confirmation when stale values could materially change a decision. Do not claim retrieval, save success, or freshness.
- **Ambiguous or partially readable:** resolve the canonical identity or obtain the complete current state before any update; do not merge guesses or overwrite unknown fields.
- **Partial write or failed verification:** retain the last verified authority as such, mark new state uncertain, and report exactly which writes succeeded, failed, or remain unverified. Stop dependent writes and do not claim coherent persistence. GitHub and Library operations are not assumed atomic; recovery must reread affected resources and remain within authorization.

The repository maintainer owns maintenance of this shared protocol. Changed provider capabilities, optional supporting skills, canonical-pointer conventions, record roles, issue requirements, or posting metadata require revisiting the affected schema, read/write and fallback rules, and handoff links. At the validation stage, replace affected synthetic fixtures/reference responses, confirm criteria, and rerun affected checks; external user settings themselves remain user-owned.
