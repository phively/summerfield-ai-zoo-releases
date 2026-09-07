# Persistent record management

Read this reference before locating, creating, updating, archiving, restoring, or handing off durable Meal Planner records. [handoff-contracts.md](handoff-contracts.md) is the authority for ownership and coordination; this file defines record identities, schemas, lifecycle procedures, and failure behavior.

## Contents

- [Record registry](#record-registry)
- [Native identities and routing](#native-identities-and-routing)
- [Authority and retrieval](#authority-and-retrieval)
- [Meal-plan records](#meal-plan-records)
- [Household and safety history](#household-and-safety-history)
- [Preference and rating pairs](#preference-and-rating-pairs)
- [Store and price records](#store-and-price-records)
- [Coherent updates](#coherent-updates)
- [Format-aware review triggers](#format-aware-review-triggers)
- [Staged workbook audits](#staged-workbook-audits)
- [Feedback check-in gate](#feedback-check-in-gate)
- [Failure behavior](#failure-behavior)
- [Coherence validation](#coherence-validation)

## Record registry

Preserve a clearly equivalent existing authority instead of renaming or copying it. Use these identities only when creating a new record:

| Owner | Current authority | Historical companion | Readers | Writers |
| --- | --- | --- | --- | --- |
| Meal Planner | `Household Preferences` workbook: `Household Profile`, `Safety Constraints`, `Planning Preferences`, optional `Pantry Inventory` | `Household History` tab for material superseded household, safety, and planning state | All Meal Planner skills, limited to task-relevant state | `meal-planner` only |
| Meal Planner | `meal-plan-current.md`, or one clearly equivalent current Word document, Google Doc, or Markdown file | `meal-plan-history.md`, or one clearly equivalent historical companion in the same selected storage system | All Meal Planner skills; current first and history only conditionally | `meal-planner` only |
| Personal Chef | `Meal Preferences` workbook: `Household Preferences` | `Household Preferences History` | All Meal Planner skills, limited to task-relevant culinary preferences | `personal-chef` only |
| Personal Chef | `Meal Preferences` workbook: `Ingredient Ratings` | `Ingredient Ratings History` | All Meal Planner skills, limited to task-relevant ingredient evidence | `personal-chef` only |
| Personal Chef | `Meal Preferences` workbook: `Recipe Ratings` | `Recipe History` | All Meal Planner skills, limited to task-relevant recipe evidence | `personal-chef` only |
| Personal Chef | `Meal Preferences`: `Recipe Catalog` and one canonical Google Doc per Recipe ID in the designated Recipes folder | Native Google Docs revision history; targeted preparation context in the Doc | All Meal Planner skills, current recipe first | `personal-chef` only |
| Personal Shopper | `Grocery Preferences` workbook: `Store Preferences` | `Store Preferences History` | All Meal Planner skills, limited to task-relevant shopping context | `personal-shopper` only |
| Personal Shopper | `Grocery Preferences` workbook: `Price Tracker` | The dated observations in the same tab are the record; do not add a duplicate archive | All Meal Planner skills, limited to relevant price evidence | `personal-shopper` only |

The owner may create or update its records only when the user authorizes persistence or an existing confirmed workflow already authorizes that bounded write. Other skills send update requests through the canonical handoff contract. Do not create skill-local copies, per-plan authorities, or parallel workbooks.

Resolve the designated Meal Planning folder and Recipes subfolder by immutable provider IDs. Keep all planning records within Meal Planning and canonical recipes within Recipes. Preserve equivalent existing names, combined tabs with clear status, and file identities. Read [cleanup-migration.md](cleanup-migration.md) before any cleanup or schema migration; preserve every populated source row and create a dated Migration audit within Meal Planning. Recipe schemas and lifecycle are in [recipe storage](../skills/personal-chef/references/recipe-storage.md).

## Native identities and routing

Identify a workbook by provider, immutable resource ID or canonical link/file path, and visible title. Identify a record within it by worksheet title, table or named range when present, stable key column, stable record ID or documented composite key, and the relevant columns. A worksheet title or row number alone is not a durable identity. Preserve clearly equivalent existing schemas; add or rename structural elements only with authorization.

Use the workbook itself as its routing layer. For a new workbook, include a `Record Index` worksheet with one row per canonical worksheet or table and these columns: `Record Type`, `Worksheet`, `Table or Named Range`, `Stable Key Column`, `Role`, `Owner`, `Last Audited`, `Row Count at Audit`, and `Retrieval Condition`. Store routing metadata only, never duplicate household facts, constraints, preferences, ratings, prices, or history there.

For an existing workbook, first use its native tables, named ranges, stable key columns, filters, and metadata. Add `Record Index` only with authorization and when it materially improves targeted retrieval or auditability. If no index worksheet exists, require a `Record ID` column or a documented unique composite key in every current, history, or evidence table touched by a write. Do not create a Markdown or other sidecar index for a workbook merely because its native routing is unfamiliar.

For document-based meal plans, keep routing in the selected canonical document system: use the exact resource ID or path, stable `MP-...` plan ID, stable `MH-...` history entry ID, and a heading, bookmark, named section, or table-of-contents entry when supported. Do not create a separate index file unless the selected format cannot support reliable retrieval and the user authorizes a non-authoritative routing companion.

## Authority and retrieval

- Optimize in strict order: complete relevant recall, fewer cells or tokens loaded and updated, then retrieval speed. Never improve a lower-ranked objective by weakening a higher-ranked one.
- Read the applicable current authority first. Current records govern over history unless the user corrects them or requests historical reconstruction.
- Do not read a complete archive merely because it exists. Retrieve the smallest relevant entry when a current record points to it, the user asks about prior state, provenance is needed to resolve a contradiction, a prior plan or rating is relevant, or restoration is being considered.
- Use stable historical identifiers in the form `MH-YYYY-MM-DD-NN`. A pointer must include the exact canonical resource identity, entry identifier, subject, and retrieval condition; do not use line numbers or a filename alone.
- Preserve exact allergies, medical limits, ingredient exclusions, serving assumptions, formulas, dates, source identities, household-member attribution, and unresolved uncertainty.
- Current user instructions govern the current task, but do not silently replace persistent state unless the user authorizes the durable change. Safety-specific records retain priority over culinary preferences.

## Meal-plan records

### Current meal plan

Keep one operationally complete most recently finalized plan. It must be understandable without history and contain, when applicable:

- stable plan identifier in the form `MP-YYYY-MM-DD-NN`, status `finalized`, covered dates, meals, and last-updated date;
- exact document provider and resource ID or canonical path plus the stable heading, bookmark, or named section used for retrieval;
- household and serving assumptions;
- exact household, safety, preference, recipe, pantry, and grocery-record identities used;
- finalized recipe IDs, verified canonical Google Doc links in the weekly table, versions used, source attribution, planned servings, plan-specific adaptations, and constraint-sensitive details;
- schedule, leftovers, prep, storage, and shopping context needed to execute the plan;
- unresolved assumptions or safety, availability, pantry, and pricing questions;
- feedback candidates that may justify a later `personal-chef` check-in, without claiming a meal was prepared; and
- targeted historical pointers only when prior context could materially affect reuse or interpretation.

Do not store drafts, rejected candidates, complete source recipes, copied preference tables, or a full grocery tracker in the current plan.

### Meal-plan history

Archive only previously finalized plans and material plan changes with continuing reuse, comparison, audit, or restoration value. Each independently retrievable entry must contain:

- `MH-YYYY-MM-DD-NN` and related `MP-YYYY-MM-DD-NN` identifiers;
- status `archived`, `superseded`, or `restored`;
- finalized and archived dates;
- covered dates and concise meal and recipe identities;
- material constraints, serving assumptions, modifications, decisions, outcomes, and unresolved uncertainty worth preserving;
- source identities and provenance; and
- replacement or restoration relationship when applicable.

Do not archive abandoned drafts, trivial wording changes, complete transcripts, or routine process events.

### Finalization lifecycle

Treat finalization as one coherent operation:

1. Confirm user approval and resolve the authoritative current/history pair. Before changing either plan record, have the chef publish approved recipes and verify every canonical recipe Doc and catalog link. Do not publish newly proposed recipes before approval.
2. Preserve the existing current plan in history when one exists and retains the required historical value.
3. Replace the current authority with the newly finalized plan and its stable identifier.
4. Add any justified targeted pointers and replacement relationships.
5. Verify that exactly one plan is current and the archived plan is not presented as active.
6. Report success only after every required write and coherence check succeeds.

## Household and safety history

Keep current household, safety, and planning state in their existing tabs. Use `Household History` only for material superseded or restored state whose provenance, audit, or safety value justifies retention. Include `MH-...` identifier, subject, affected member, status, prior state, current replacement identity, source, recorded and effective dates, reason retained, and uncertainty.

Do not archive ordinary pantry quantity churn. Never let a historical allergy or medical restriction override the current `Safety Constraints` tab.

## Preference and rating pairs

### Household Preferences and Household Preferences History

Keep one current row per household member, category, item, and material context in `Household Preferences`. This is the current authority for culinary ingredient, cuisine, flavor, texture, technique, equipment, and similar preferences. Use a single numeric Rating from 1 to 5 in half steps for culinary preferences and all ingredient/recipe ratings. Unknown stays blank; preserve member and preparation context. Do not maintain a separate active Preference or Strength field. Hard exclusions and frequency limits remain separate planner-owned constraints.

When a confirmed current preference materially changes, preserve its prior formulation in `Household Preferences History` or a status-marked historical row when it retains continuing value. Record `MH-...` identifier, member, category, item, context, prior rating, replacement identity/value, reason, source, recorded/effective dates, and uncertainty. Historical legacy labels may remain as evidence; they never override the active numeric schema.

Recipe-specific feedback does not establish a general ingredient preference without explicit confirmation. Individual feedback does not establish a household-wide preference.

### Ingredient Ratings and Ingredient Ratings History

Keep `Ingredient Ratings` as the sole current authority for the latest decision-relevant rating of an ingredient by a household member or explicitly confirmed household aggregate. Include normalized ingredient identity, member, current 1-5 rating when supplied, rating date, preparation and dish context, what worked or did not, source classification, last-updated date, review status, and a targeted history pointer only when useful.

Use `Ingredient Ratings History` for prior material ingredient ratings and preparation-specific outcomes with continuing analytical, explanatory, audit, or restoration value. Include `MH-...` identifier, ingredient and member identities, prior and replacement values, preparation context, dates, reason retained, provenance, uncertainty, and status.

Do not silently generalize a preparation-specific ingredient rating. For example, disliking raw onion in one salsa does not change a current rating for cooked onion or the general onion preference.

### Recipe Ratings and Recipe History

Keep `Recipe Ratings` as the sole current authority for the latest decision-relevant rating of each recipe and household member or explicitly confirmed household aggregate. Use normalized recipe title plus source URL or stable original-recipe identity to match entries. Include:

- stable Recipe ID, canonical Google Doc link, and separate original source attribution;
- household member or confirmed aggregate;
- current 1-5 rating when supplied, `would make again`, and rating date;
- version made or a pointer to the Doc's preparation context;
- what worked, difficulty, leftovers quality, concise outcome context, and pointers to proposed or confirmed recipe modifications held in the Doc;
- source classification: direct report, confirmed interpretation, or unresolved;
- last-updated date and stale-review status; and
- a targeted pointer when historical context could materially affect reuse.

Use `Recipe History` for prior ratings and outcomes with continuing value. Each entry contains `MH-...` identifier, recipe/member identities, prior and replacement ratings, dates, Doc version or preparation pointer, reason retained, provenance, uncertainty, and status. Keep recipe instructions and modification text in the canonical Doc, with Google Docs revision history; the workbook is not a second recipe store. Preserve equivalent combined current/history tables with explicit row status during migration.

Do not append an identical rating merely because the recipe was served again. Do not erase meaningful prior outcomes, but do not turn history into a meal log.

## Store and price records

Keep the current ordered store list in `Store Preferences`. Preserve a prior order in `Store Preferences History` only when its rationale or restoration value remains material. Include `MH-...` identifier, prior order, replacement order, region or context, reason, source, dates, and status.

Keep dated product and package observations in `Price Tracker`; its observations are historical evidence rather than current preference authority. Select applicable evidence by store, location, product match, date, package, sale or membership status, and confidence. Do not copy observations into another history tab.

## Coherent updates

Treat a material current-state change as one transaction:

1. Resolve the canonical current and historical identities.
2. Confirm the revised current state, source, attribution, and effective date.
3. Preserve prior state only when it retains continuing value.
4. Update the current authority and write any required historical entry.
5. Mark superseded, archived, or restored state and record relationships.
6. Add or revise only useful targeted pointers.
7. Verify that no contradictory active formulation remains.

During cleanup, retain or update every populated source data row; do not remove or silently merge duplicates. Resolve conflicting active authority with status and pointers while preserving all original data in the row or its traceable history. A change requiring both current and history writes is incomplete unless both succeed.

## Format-aware review triggers

Check cheap workbook metadata at an authorized write, explicit audit, or consequential use. Make a workbook audit due when any of these conditions applies:

- `Last Audited` is missing or more than 180 days old;
- a current worksheet or table exceeds 500 data rows;
- a history or `Price Tracker` worksheet exceeds 2,000 data rows;
- a worksheet has grown by at least 25 percent since `Row Count at Audit`;
- duplicate stable keys, broken formulas, invalid named ranges, missing required columns or validations, unresolved authority conflicts, or broken record references are detected; or
- compaction, splitting, merging, deduplication, schema migration, or ownership transfer is proposed.

The numerical thresholds are conservative design heuristics, not research findings. They make review due; they never decide that a record should be deleted, archived, compressed, or split. A stable large table may remain intact, while a small contradictory table requires repair. Do not load every row merely to inspect row counts, schema metadata, or the recorded audit date. If an audit is due but no write is authorized, report it and continue read-only when reliable.

## Staged workbook audits

Treat structural workbook maintenance as a fail-closed transaction. Read [the workbook audit snapshot and ledger schema](workbook-audit-schema.md) before exporting or validating a staged workbook.

1. Resolve the canonical workbook resource identity, owner, current and history sheets, native tables or named ranges, stable key definitions, and external dependencies.
2. Preserve a recoverable workbook copy or revision and export a complete pre-audit snapshot containing workbook identity, worksheet roles, columns, tables, named ranges, stable record IDs, values, formulas, validations, and record references.
3. Stage the proposed workbook outside the canonical authority. Export the same complete snapshot after the proposed change.
4. Create a bidirectional ledger mapping every pre-audit structure and record to `retained`, `moved`, `reworded`, `updated`, `archived`, or justified disposable removal, and every post-audit item to its origin or an authorized addition.
5. Preserve exact allergies, medical limits, quantities, units, formulas, validations, stable keys, plan and history IDs, provenance, household-member attribution, dates, uncertainty, and reference targets. Require explicit authorization for factual or schema updates, a passed formula review for changed formulas, and a recorded semantic review for rewording.
6. Run `../scripts/validate_workbook_audit.py` against the exported before snapshot, after snapshot, and ledger. Also inspect the provider's native diff or revision history when available.
7. Replace the canonical workbook only after hashes, complete item coverage, uniqueness, formulas, validations, named ranges, record references, ownership, and semantic review all pass. Verify the written workbook against the accepted after snapshot and retain the recovery copy until verification succeeds.

On unexplained omission, duplicate stable key, changed protected value, broken formula or reference, ambiguous authority, semantic uncertainty, inaccessible dependency, or partial write, leave the canonical workbook unchanged and report the failed check. Snapshot hashes prove exact serialized snapshot integrity, not semantic equivalence or complete connector extraction; preserve that limitation explicitly.

## Feedback check-in gate

### Pre-planning retrospective

A request for a new meal plan triggers one bounded retrospective before recipe selection. Read the previous current plan and ask which recipes were actually made. For confirmed dishes, collect member-attributed opinions, optional numeric ratings in half steps, repeat interest, and modifications. Ask about the version actually prepared rather than assuming today's canonical Doc was used. Apply confirmed reusable recipe and preference updates through their owners before making the new plan. An existing confirmed workflow may authorize these bounded writes; do not repeat permission questions already answered.

Skip questions already answered or declined. If no prior plan exists, nothing was made, or feedback is unavailable, continue with current records and explicit uncertainty. Do not require numeric scores when qualitative feedback is all the user supplies. Do not run this interview for a cleanup-only request. Outside a new-plan request, collect or refresh feedback only when it could affect a current decision:

1. Confirm the recipe was actually prepared or the ingredient was actually used; a plan alone is not evidence of consumption.
2. Confirm that the affected household member is known or preserve individual attribution as unresolved.
3. Identify how an answer could change future selection, adaptation, shopping, or a current rating.
4. For re-rating outside the retrospective, require a decision-relevant reason such as changed preparation, a material modification, conflicting feedback, or upcoming reuse. Elapsed time alone is insufficient.
5. Ask the smallest useful set of questions and include the recipe or ingredient identity, preparation or modification, prior rating date and value when visible, and the reason review matters now.

Do not repeatedly ask after the user declines or lacks feedback unless a materially different preparation or decision creates a new reason.

## Failure behavior

- Missing record: do not claim it was read or updated. The owner may create the canonical identity in the user's selected location only with authorization.
- Duplicate or ambiguous candidates: resolve the authority before substantive use or writing when the choice could affect the result.
- Inaccessible history or broken pointer: preserve uncertainty; a retrieval miss is not evidence that history does not exist.
- Partial access or writability: do not claim a coherent update. Provide a clearly labeled proposed update or identify the failed write and recovery action.
- Unsupported format: preserve the logical current/history model in an accessible user-selected durable format; do not create several formats as competing authorities.
- Unconfirmed preparation, rating, preference, or lifecycle state: label it proposed or unknown and do not persist it as fact.

Do not modify unavailable household records during plugin development. Update schemas, instructions, examples, evaluations, and tests instead.

## Coherence validation

After a consequential update, verify that current records alone contain all operational state, historical material cannot silently override current state, stable identifiers and pointers resolve, attribution and dates remain explicit, safety constraints remain exact, ingredient and recipe ratings match the correct member and preparation, exactly one meal plan is current, downstream handoffs exclude irrelevant history, and no persistence claim exceeds the completed writes.
