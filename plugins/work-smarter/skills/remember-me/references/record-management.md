# Remember Me record management

Read this reference before creating or changing the index or a topic file, selecting ownership, refreshing an external summary, retrieving history, forgetting information, or resolving duplicate or partial records.

## Contents

- [Canonical records](#canonical-records)
- [Index schema](#index-schema)
- [Topic ownership and taxonomy](#topic-ownership-and-taxonomy)
- [Topic-file schema](#topic-file-schema)
- [External summaries](#external-summaries)
- [History](#history)
- [Lifecycle and coherence](#lifecycle-and-coherence)
- [Maintenance triggers and audit](#maintenance-triggers-and-audit)
- [Failure behavior](#failure-behavior)

## Canonical records

Use a dedicated `remember-me/` folder in the user's selected accessible library. Preserve clearly equivalent existing authorities instead of renaming or copying them.

| Record | Owner | Authority | Readers | Writers |
| --- | --- | --- | --- | --- |
| `index.md` | `remember-me` | Topic registry, routing, ownership, source identity, and freshness | Any skill needing relevant personal context | `remember-me` only |
| Remember-me topic file | `remember-me` | Detailed current state for that topic | Relevant skills, using targeted retrieval | `remember-me` only |
| External canonical source | Identified specialist skill | Detailed current state for its domain | As allowed by the owner's contract | The external owner only |
| `history.md` | `remember-me` | Material prior state only | `remember-me`, under a targeted retrieval condition | `remember-me` only |

Do not package or prepopulate these user records in the plugin repository. Create them only at runtime in an authorized library location.

## Index schema

Keep `index.md` concise and understandable without loading any topic file. Include record owner, exact identity, last-audited date, and one section per populated topic. Record these fields when applicable:

- topic name and concise current summary;
- ownership type: `remember-me` or `external`;
- owning skill or workflow;
- exact canonical resource identity or remember-me-relative path;
- evidence classification and source attribution;
- last verified or refreshed date;
- refresh trigger or justified review interval;
- condition for retrieving the detailed source;
- unresolved conflicts, unknowns, or access limitations;
- sensitivity or handling restrictions; and
- a targeted history pointer only when later history could materially affect interpretation.

An index summary never overrides its identified detailed current source. Mark a summary `stale` when its source is newer, a contradiction exists, or required verification failed. Do not present stale content as confirmed current state.

Use the index as a low-token routing layer, not as a ceiling on recall. Retrieve the identified current source or additional relevant sections whenever the summary is incomplete, stale, ambiguous, conflicting, or lacks consequential detail. After recall is protected, minimize read and update tokens; improve retrieval speed only after both objectives are satisfied.

## Topic ownership and taxonomy

Prefer a specialist owner whenever an available skill has a canonical record-management workflow for the topic. Read the external owner's contract before relying on or requesting changes to its record:

- Career direction, goals, constraints, and related coaching context: `career-coach:career-direction`; use the canonical [Career Coach contract](../../../../career-coach/shared/handoff-contracts.md).
- Household planning and safety constraints: `meal-planner:meal-planner`.
- Culinary preferences, ingredient evidence, and recipe feedback: `meal-planner:personal-chef`.
- Store order, grocery preferences, and pricing observations: `meal-planner:personal-shopper`.
- For Meal Planner topics, use the canonical [Meal Planner contract](../../../../meal-planner/shared/handoff-contracts.md) and preserve its workbook, tab, record, and household-member identities.

When no specialist handles a useful topic, choose the narrowest fitting file from this default taxonomy:

- `communication-collaboration.md`
- `values-goals.md`
- `lifestyle-routines.md`
- `entertainment-interests.md`
- `travel-places.md`
- `household-relationships.md`
- `technology-tools.md`

Create a file only when useful durable information exists. Keep related interests together; for example, do not split entertainment into book, movie, television, and game files unless scale or retrieval failures justify it. Create a new topic filename only when none of the defaults fits and a separate authority materially improves retrieval or ownership clarity.

Temporary unavailability does not erase an established external owner's authority. If no specialist currently exists and `remember-me` owns a topic that a later specialist can handle, migrate only with user authorization and a verified destination; then update the index and remove or archive the prior current authority so no parallel copy remains.

## Topic-file schema

Keep each current topic file operationally complete without history. Include when applicable:

- title, owner, exact identity, last-updated date, and effective date;
- current user-stated facts and confirmed preferences;
- evidence-supported patterns and their supporting examples or source identities;
- reasonable inferences and working hypotheses under explicit labels;
- stable constraints, boundaries, and requirements exactly as confirmed;
- unresolved questions and contradictions;
- source attribution and household-member attribution; and
- targeted historical pointers only when justified.

Consolidate duplicate active formulations. Do not store complete conversation transcripts, routine task state, externally owned domain detail, unsupported conclusions, or a one-time choice presented as a stable preference.

## External summaries

Request only what the index needs: topic, bounded current summary, exact canonical identity, owner, last-updated date when visible, evidence classifications, uncertainty, refresh trigger, and retrieval condition. Do not request or pass a complete history.

The external source remains authoritative for domain detail. If the index conflicts with it, use the external source, label the index stale, and request a bounded refresh. A failed retrieval is not evidence that the source does not exist. Never invent an identity, date, summary, or successful handoff.

## History

Do not create `history.md` until meaningful superseded state, rationale, provenance, audit, or restoration needs exist. When the gate passes, use independently retrievable entries with:

- stable identifier `RMH-YYYY-MM-DD-NN`;
- subject and status: `superseded`, `archived`, `rejected`, or `restored`;
- recorded and effective dates when known;
- prior formulation or decision;
- reason it remains useful;
- source identity and evidence classification;
- replacement or restoration relationship; and
- unresolved uncertainty.

A current-file pointer must name `history.md`, the stable entry identifier, subject, and condition for consulting it. Do not use line numbers or a filename alone. Never archive trivial edits, transient state, valueless duplication, secrets, or information the user explicitly asked to forget.

## Lifecycle and coherence

Treat a material update as one transaction: confirm current state, preserve only useful prior state, update the affected portion of the detailed authority, update the index fields that depend on it, revise justified pointers, and verify that no contradictory active copy remains. Keep the transaction narrow only when every dependent current fact and pointer remains complete and coherent. If any required write fails, do not describe the operation as coherent or complete.

Apply lifecycle actions deliberately:

- **Promote:** restore archived information to a current topic only after confirmation.
- **Demote:** remove no-longer-current information and archive it only when it retains value.
- **Invalidate:** mark a retained prior formulation superseded and identify its replacement.
- **Remove:** delete incorrect, transient, valueless, or explicitly forgotten information rather than archiving it.
- **Transfer:** move authority to a verified specialist only with authorization and without leaving a competing current record.

After consequential changes or an audit, verify that every index pointer resolves, each topic has one detailed current authority, external summaries identify their owner, stale state is visible, exact constraints remain exact, history cannot silently override current state, and routine retrieval does not require loading history.

## Maintenance triggers and audit

Record `last-audited` in `index.md`. At an authorized write, explicit audit, or consequential use, make an audit due when any of these conditions is visible from routing metadata or file statistics:

- `index.md` exceeds 8 KiB;
- a remember-me-owned current topic file exceeds 16 KiB;
- 180 days have elapsed since `last-audited` or the date is missing; or
- a compaction, split, merge, archive migration, or ownership transfer is proposed.

These numerical thresholds are conservative default design heuristics, not universal research findings. They bound routine context while avoiding constant maintenance. Do not read every topic merely to test them, do not treat elapsed time as evidence that stable content is stale, and do not take a lifecycle action from size or age alone. If an audit is due but no write is authorized, report it and continue read-only when reliable.

For an authorized audit, use the canonical loss-controlled protocol in [Superb Skills working memory](../../superb-skills/references/working-memory.md#loss-controlled-audits). Inventory the complete remember-me file set plus every protected semantic item before drafting. Stage the candidate outside the canonical folder, map all before and after items bidirectionally, run `../../../scripts/validate_memory_audit.py`, and inspect the full diff. A compaction or split must preserve exact constraints, numerical rules, provenance, stable identifiers, required pointer targets, meaningful history, attribution, uncertainty, and ownership. Rewording a protected non-exact item requires a recorded semantic-equivalence review; factual changes require the applicable confirmation and must remain distinct from maintenance.

Replace the canonical files only after validation succeeds, then verify the written hashes and pointer resolution. Retain the recoverable snapshot until that check passes. On any unexplained omission, semantic uncertainty, broken pointer, competing authority, inaccessible source, or partial write, leave the original authority unchanged, record which check failed, and offer a proposed repair.

## Failure behavior

- Missing index: create it only when persistence is authorized; otherwise report that no durable index was found.
- Duplicate candidates: resolve the authoritative record before writing when the result could differ.
- Inaccessible source or broken pointer: preserve uncertainty and offer a labeled proposed repair.
- Partial access or writability: identify the completed and failed operations; never claim coherent persistence.
- Unsupported external integration: keep reliable routing metadata only and do not simulate a plugin response.
- Sensitive or ambiguous content: request confirmation before persistence and minimize the retained detail.
