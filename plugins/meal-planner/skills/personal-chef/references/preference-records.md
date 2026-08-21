# Preference and recipe records

Use a workbook or Google Sheet titled `Meal Preferences` or a clearly equivalent title such as `Recipe Preferences` or `Family Meal Preferences`. When creating a new workbook, use `Meal Preferences`. Reuse an accessible equivalent workbook instead of creating a competing copy.

Use six canonical data tabs: `Household Preferences`, `Household Preferences History`, `Ingredient Ratings`, `Ingredient Ratings History`, `Recipe Ratings`, and `Recipe History`. For a new workbook, also create the workbook-local `Record Index` defined in shared record management. Accept clearly equivalent existing tab names and columns without forcing a migration. Treat the provider, immutable workbook ID or canonical path, visible title, worksheet, table or named range, stable key column, record ID, and relevant columns as source provenance; do not copy the records into skill-local files. Read [the shared record-management contract](../../../shared/record-management.md) before creating, revising, archiving, restoring, or resolving these records.

Use a `Record ID` column in every new current table and the existing `History ID` or `MH-...` field in history tables. Prefer structured tables or named ranges named for the canonical worksheet. Preserve a clearly equivalent existing composite key, but document it in `Record Index` rather than using row numbers. Use the logical uniqueness rules below to detect duplicates.

## Household Preferences

| Field | Purpose |
| --- | --- |
| Record ID | Stable unique key; never a row number |
| Household member | Person or `household` |
| Category | Ingredient, cuisine, flavor, texture, technique, equipment, budget, or other |
| Item | Normalized preference subject |
| Preference | Love, like, neutral, limit, dislike, or exclude |
| Strength | Optional 1-5 confidence or intensity |
| Context | Weeknight, seasonal, preparation-specific, and similar qualifiers |
| Reason or notes | User explanation in concise form |
| Source | Direct statement, repeated behavior, or confirmed interpretation |
| Updated date | ISO date |

Use `exclude` only for a user-confirmed culinary exclusion. Keep allergy and medical rules in the safety record owned by `meal-planner` unless the user explicitly requests otherwise. Keep only current preference rows here.

## Household Preferences History

Move a prior material preference here only when a confirmed change retains analytical, explanatory, audit, or restoration value. Include stable history identifier, member, category, item, context, prior value and strength, current replacement, reason retained, source, recorded and effective dates, modification context when relevant, status, and uncertainty. Do not let a historical preference override the current tab.

## Ingredient Ratings

Keep one current decision-relevant row per normalized ingredient, household member or confirmed aggregate, and material preparation context. That composite is the logical uniqueness rule even when `Record ID` is the physical key.

| Field | Purpose |
| --- | --- |
| Record ID | Stable unique key; never a row number |
| Ingredient | Normalized ingredient identity |
| Household member | Individual or confirmed aggregate |
| Rating | Current 1-5 value, if supplied |
| Rating date | ISO date |
| Preparation and dish context | Raw, roasted, blended, recipe identity, and similar qualifiers |
| What worked or did not | Concise user feedback |
| Source classification | Direct report, confirmed interpretation, or unresolved |
| Last updated | ISO date |
| History pointer | Stable entry and retrieval condition, only when useful |
| Review status | Current or review-worthy; never stale from elapsed time alone |

## Ingredient Ratings History

Preserve only prior material ingredient ratings and preparation-specific outcomes with continuing value. Include `MH-...` identifier, ingredient and member identities, prior and replacement values, preparation context, dates, reason retained, provenance, uncertainty, and status. Do not generalize a raw, cooked, or recipe-specific reaction to other preparations without confirmation.

## Recipe Ratings

Keep one current decision-relevant row per normalized recipe identity and household member or explicitly confirmed household aggregate. Normalized recipe title plus source URL or stable original-recipe identity plus member is the logical uniqueness rule.

| Field | Purpose |
| --- | --- |
| Record ID | Stable unique key; never a row number |
| Recipe name | Recognizable title |
| Source URL | Direct original recipe link, if any |
| Household member | Individual or confirmed aggregate |
| Rating | Current 1-5 value, if supplied |
| Rating date | ISO date |
| Would make again | Yes, no, or conditional |
| Preparation or modification | Version that was actually made |
| What worked | Concise user feedback |
| What to change | Specific actionable modification |
| Prep difficulty | User assessment |
| Leftovers quality | User assessment |
| Source classification | Direct report, confirmed interpretation, or unresolved |
| Last updated | ISO date |
| History pointer | Stable entry and retrieval condition, only when useful |
| Review status | Current or review-worthy; never stale from elapsed time alone |

Interpret ratings with notes rather than mechanically. Treat `would make again` and specific explanations as more informative than the number when they conflict.

## Recipe History

Keep only prior ratings, material preparation experiences, modifications, and outcomes with continuing value.

| Field | Purpose |
| --- | --- |
| History ID | Stable `MH-YYYY-MM-DD-NN` identifier |
| Recipe name | Recognizable title |
| Source URL | Direct original recipe link, if any |
| Date made | ISO date, when confirmed |
| Household member | Individual or confirmed aggregate |
| Prior rating | Prior 1-5 value, if supplied |
| Replacement rating | Current replacement, when applicable |
| Would make again | Yes, no, or conditional |
| What worked | Flavor, texture, ease, leftovers, and similar notes |
| What to change | Specific actionable modification |
| Modification tried | What differed from the source |
| Prep difficulty | User assessment |
| Leftovers quality | User assessment |
| Tags | Cuisine, protein, season, method, or occasion |
| Status and relationship | Superseded, archived, or restored plus replacement identity |
| Source and uncertainty | Attribution and unresolved limits |
| Updated date | ISO date |

Do not append an identical rating merely because the recipe was served again or use this tab as an unbounded meal log.

## Update rules

1. Match existing recipes by normalized title plus source URL when possible.
2. Confirm that the recipe was actually prepared before recording an outcome. A plan is not evidence that it was made.
3. Update a current ingredient or recipe rating only after direct feedback or confirmed interpretation. Preserve prior state in its historical companion only when it retains continuing value.
4. Update a stable preference only after direct confirmation. Preserve the prior row in `Household Preferences History` only when it retains continuing value.
5. Attribute individual reactions to the correct household member; do not convert recipe-specific feedback into a general ingredient preference or preparation-specific ingredient rating without confirmation.
6. Revisit an older rating only when elapsed time combines with a decision-relevant reason such as repeated use, changed preparation, material modification, conflicting feedback, or upcoming reuse.
7. Preserve blanks rather than inventing ratings, dates, reasons, or modifications.
8. Treat a material current/history update as one coherent operation. Summarize every completed write and surface unresolved duplicates or partial failures.
9. Check workbook audit triggers using `Record Index` metadata or native row counts and schema metadata. Before structural maintenance, export and validate staged before/after snapshots under the shared protocol; do not use the Markdown audit validator for these workbook records.
