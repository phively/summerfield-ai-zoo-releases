# Remember Me record management

Read this reference before creating or changing the index or a topic file, selecting ownership, refreshing an external summary, retrieving history, forgetting information, or resolving duplicate or partial records.

## Contents

- [Canonical records](#canonical-records)
- [Resource identity](#resource-identity)
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

## Resource identity

Identify a library resource with the strongest fields the provider exposes, in this order:

1. provider and library or container scope;
2. immutable resource or object identifier;
3. canonical permalink;
4. visible filename, title, path, and search terms as human recovery fallbacks; and
5. a stable internal entry identifier when pointing to part of the resource.

For a local filesystem without provider identifiers or permalinks, use the resolved durable path plus a stable internal entry identifier. A rename changes fallback metadata rather than authority. After a move, verify that the provider-scoped identifier still resolves and update the permalink or fallback path when needed. Treat a copy as a new identity unless the provider explicitly preserves identity semantics.

If an identifier or permalink stops resolving, try the other canonical field, then use the fallback metadata to locate candidates and verify the identity before use. Never select among same-named candidates by filename alone. Do not replace the canonical identity with a newly found candidate until authority is verified.

## Index schema

Keep `index.md` concise and understandable without loading any topic file. Include record owner, exact identity, last-audited date, and one section per populated topic. Record these fields when applicable:

- topic name and concise current summary;
- ownership type: `remember-me` or `external`;
- owning skill or workflow;
- provider and library or container scope, immutable resource or object identifier, and canonical permalink when available;
- current visible filename, title, path, and search terms as recovery fallbacks, or a remember-me-relative durable path when no provider identity exists;
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

- title, owner, provider-scoped resource identity and permalink, fallback filename or path, last-updated date, and effective date;
- current user-stated facts and confirmed preferences;
- evidence-supported patterns and their supporting examples or source identities;
- reasonable inferences and working hypotheses under explicit labels;
- stable constraints, boundaries, and requirements exactly as confirmed;
- unresolved questions and contradictions;
- source attribution and household-member attribution; and
- targeted historical pointers only when justified.

Consolidate duplicate active formulations. Do not store complete conversation transcripts, routine task state, externally owned domain detail, unsupported conclusions, or a one-time choice presented as a stable preference.

## External summaries

Request only what the index needs: topic, bounded current summary, provider and library or container scope, immutable resource or object identifier, canonical permalink, fallback filename or title, owner, last-updated date when visible, evidence classifications, uncertainty, refresh trigger, and retrieval condition. Do not request or pass a complete history.

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

A current-file pointer must record the history resource's provider-scoped identity and canonical permalink when available, visible `history.md` filename as a recovery fallback, stable entry identifier, subject, and condition for consulting it. Do not use line numbers or a filename alone. Never archive trivial edits, transient state, valueless duplication, secrets, or information the user explicitly asked to forget.

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
- 180 days have elapsed since `last-audited` or the date is missing;
- 25 material changes have accumulated since audit, or a record has grown by 25 percent since audit, when that metadata is inexpensive to maintain;
- a persistent-record compaction, split, merge, deduplication, archive migration, schema migration, or ownership transfer is proposed;
- duplicate or conflicting current authorities, contradictory active state, or current content that cannot be understood without history is detected;
- a required resource identifier, permalink, stable entry identifier, or pointer no longer resolves; or
- a stale index or structure aid, repeated bounded retrieval miss, or routine need to load substantial unrelated content shows that targeted retrieval is failing.

These numerical thresholds are conservative default design heuristics, not universal research findings. They bound routine context while avoiding constant maintenance. A table of contents or section map is a conditional retrieval aid, not a requirement or trigger by itself. Do not read every topic merely to test a trigger, do not treat elapsed time as evidence that stable content is stale, and do not take a lifecycle action from any trigger alone. If an audit is due but no write is authorized, report it and continue read-only when reliable.

Conversation-context compaction is not persistent-record compaction. After conversation compaction, refresh the current conversational brief and recheck exact constraints against their authoritative sources. Audit the persistent remember-me records only when one of the record triggers above is met.

For an authorized audit, use the canonical loss-controlled protocol in [Superb Skills working memory](../../superb-skills/references/working-memory.md#loss-controlled-audits). Inventory the complete remember-me file set plus every protected semantic item before drafting. Stage the candidate outside the canonical folder, map all before and after items bidirectionally, run `../../../scripts/validate_memory_audit.py`, and inspect the full diff. A compaction or split must preserve exact constraints, numerical rules, provenance, stable identifiers, required pointer targets, meaningful history, attribution, uncertainty, and ownership. Rewording a protected non-exact item requires a recorded semantic-equivalence review; factual changes require the applicable confirmation and must remain distinct from maintenance.

Replace the canonical files only after validation succeeds, then verify the written hashes and pointer resolution. Retain the recoverable snapshot until that check passes. On any unexplained omission, semantic uncertainty, broken pointer, competing authority, inaccessible source, or partial write, leave the original authority unchanged, record which check failed, and offer a proposed repair.

## Failure behavior

- Missing index: create it only when persistence is authorized; otherwise report that no durable index was found.
- Duplicate candidates: resolve the authoritative record before writing when the result could differ.
- Renamed or moved source: resolve the provider-scoped identity first and update only the fallback metadata that changed.
- Copied source: treat it as a separate candidate identity and do not transfer authority without verification.
- Inaccessible source or broken pointer: preserve uncertainty and offer a labeled proposed repair.
- Partial access or writability: identify the completed and failed operations; never claim coherent persistence.
- Unsupported external integration: keep reliable routing metadata only and do not simulate a plugin response.
- Sensitive or ambiguous content: request confirmation before persistence and minimize the retained detail.
