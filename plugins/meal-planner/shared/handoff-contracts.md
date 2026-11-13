# Shared handoff contracts

This file is the canonical authority, ownership, and coordination contract for the plugin's skills. Read it from its plugin-level path; do not copy it into a skill folder. Preserve user-supplied facts, source identity, confirmation state, and unresolved uncertainty across every handoff. Read [record-management.md](record-management.md) for schemas, lifecycle procedures, targeted retrieval, and failure behavior.

## Workbook routing

Use these canonical workbook titles and tabs. Recognize clearly equivalent existing titles or tab names, but use the canonical names when creating new records:

| Owner | Canonical workbook | Canonical tabs |
| --- | --- | --- |
| Meal Planner | `Household Preferences` | Workbook-local `Record Index`; `Household Profile`, `Safety Constraints`, `Planning Preferences`, optional `Pantry Inventory`, and `Household History` |
| Personal Chef | `Meal Preferences` | Workbook-local `Record Index`; `Household Preferences`, `Household Preferences History`, `Ingredient Ratings`, `Ingredient Ratings History`, `Recipe Ratings`, `Recipe History`, and `Recipe Catalog` |
| Personal Shopper | `Grocery Preferences` | Workbook-local `Record Index`; `Store Preferences`, `Store Preferences History`, and `Price Tracker`; read or limited fallback writes by Meal Planner only as defined in [the local grocery integration contract](grocery-integration.md) |

Every handoff must preserve the exact workbook title and link or file identity by identifying the provider, immutable workbook resource ID or canonical link/file path, visible workbook title, exact worksheet, table or named range when present, stable key column and record ID or documented composite key, relevant columns, and any expected workbook structure that was unavailable. A workbook title, worksheet title, or row number alone is insufficient. Pass accessible shared records by identity; never create skill-local static copies.

Use native workbook routing. When present, read `Record Index` first and then retrieve only the relevant current rows or targeted history. Otherwise use the worksheet's stable key column, structured table, named range, or documented composite key. Do not create a sidecar file merely to index a workbook, and do not pass complete worksheet or archive contents when bounded rows preserve complete relevant recall.

## Record authority and access

`meal-planner` owns the `Household Preferences` workbook and the single current/history meal-plan pair. Prefer a Google Sheet for a newly created household workbook and Google Docs for newly created narrative meal-plan records when the user's Drive is accessible; use `meal-plan-current.md` and `meal-plan-history.md` only for a filesystem fallback. Preserve one clearly equivalent existing authority in place. All skills may read relevant current state; only `meal-planner` creates or updates these records.

`personal-chef` owns the `Meal Preferences` workbook, including current culinary preferences and recipe ratings plus their historical companions, and the canonical recipe Google Docs indexed by `Recipe Catalog`. All skills may read relevant current state; only `personal-chef` creates or updates these records. Use one numeric 1-5 Rating in half steps for culinary, ingredient, and recipe preferences; no separate preference label or strength score.

Every Drive handoff includes the designated Meal Planning, Recipes, and Audits folder IDs. Keep planning files inside Meal Planning, canonical recipe Docs inside Recipes, and audit, compaction, migration, staging, and recovery artifacts in a dated child folder under Audits. Preserve equivalent existing structure, resource IDs, and sharing. Follow [native artifact storage and formatting](artifact-formatting.md) for Drive-first creation, native formatting, and named verified links. During cleanup, follow [cleanup-migration.md](cleanup-migration.md): updates and additions may change data rows, but no populated source row may be deleted or silently merged. File-type or provider migration requires explicit user permission before a replacement is created for conversion, authority is transferred, the original is retired, or dependent links change.

`personal-shopper` owns the `Grocery Preferences` workbook. All Meal Planner skills may read bounded task-relevant current state and price evidence. Only `personal-shopper` performs the full shopping workflow and ordinary record maintenance. `meal-planner` may perform only the exact grocery fallback writes defined in [the local grocery integration contract](grocery-integration.md); that exception does not authorize structural changes, general shopping records, or unrelated updates.

Current records govern over history unless the user corrects them or requests historical reconstruction. Read history only under a targeted retrieval condition in [record-management.md](record-management.md). Never pass a complete archive, create a parallel authority, infer that a retrieval miss proves no history exists, or claim persistence after a partial write.

Every record-update request must include the exact current and historical identities when visible, expressed with the native resource, worksheet, table or named range, stable key and relevant columns; stable entry identifier when applicable; proposed state; source and household-member attribution; confirmation status; effective date if known; lifecycle intent; reason the change is reusable; uncertainty; and expected owner response. The prohibited information includes secrets, unrelated history, complete worksheets or source documents, and unsupported conclusions presented as facts.

## Personal Chef to Meal Planner

Return a recipe-selection packet containing:

- finalized or proposed status for every recipe;
- recipe title, source URL or original-recipe label, yield, and planned servings;
- stable Recipe ID, canonical Google Doc ID and descriptive verified link, current version, publication status, content and native-formatting verification result, link verification result, and designated folder IDs;
- ingredient quantities, active time, total time, equipment, and leftover yield;
- material adaptations and reasons;
- constraint-sensitive ingredients, labels, substitutions, and cross-contact questions requiring safety review;
- preference evidence used, open preference questions, and completed or proposed record changes;
- exact `Meal Preferences` workbook identity and tabs read or changed, or their availability status;
- exact current meal-plan identity and plan identifier when supplied, without copying the complete plan;
- ingredient-overlap, batch-prep, freezer, and leftover notes.

The meal planner owns final safety approval. A chef handoff must never claim that a recipe is medically safe. For a newly created or changed canonical recipe, report content, native-formatting, and link verification separately, including any unavailable or failed check. Formatting that was not read back from the native document remains unverified.

For feedback requested after a plan, return only confirmed preparation or use, member attribution, current ratings or preferences changed, historical entries created, material modifications, unresolved questions, and exact records changed. If preparation or consumption is unconfirmed, return no rating update and identify the smallest useful follow-up. User-visible links in every handoff must have descriptive labels and verified targets; pass raw URLs only in dedicated identity or source fields.

## Meal Planner to Personal Chef

For a new-plan request, first send the previous current plan's exact identity and plan identifier for the pre-planning retrospective. Prepared status may initially be unknown: ask which recipes were made before requesting opinions. Include recipe IDs and Doc links, version made when known, member attribution, existing ratings/dates, answered or declined questions, and persistence authorization. Confirm and apply affected record updates before selecting the new recipes. Then send the bounded constraint and updated preference packet for recipe selection.

Do not infer feedback merely because a recipe appeared in a plan or a fixed interval elapsed. A newly requested plan triggers the retrospective, with a preparation check first. `personal-chef` applies the shared gate and owns culinary preferences, ratings, Recipe Catalog, and recipe-Doc writes. Return safety or practical planning updates to `meal-planner`, and shopping preferences to `personal-shopper`. After plan approval, explicitly hand off approved recipe publication and require verified content, native formatting, and links before the new current plan is saved.

## Meal Planner to Personal Shopper

Use `grocery-handoff/v1`. Invoke the independently installed `personal-shopper:personal-shopper` only when the active host can activate it. After the plan is approved and recipe selection and safety review are complete, send one shopping packet; do not ask again for facts already supplied. Include:

- protocol version and unique request identity;
- final recipe names, ingredient quantities, source yields, planned servings, and leftover uses;
- canonical Recipe IDs, verified named Google Doc links, exact approved versions, and designated Meal Planning, Recipes, and Audits folder IDs;
- confirmed pantry quantities plus separate `check pantry` items;
- region, currency, shopping date, budget, and preferred stores in effective order;
- required brands, products, labels, allergy constraints, medical constraints, and permitted substitutions;
- exact `Grocery Preferences` workbook identity and available canonical tabs;
- meal-plan identity with `identity_status`, stable `plan_id`, and native resource identity when persisted;
- task-only corrections separately from saved record values;
- exact targets and fields the user authorized for persistence, or explicit no-persistence status; and
- unresolved questions and missing identities.

For an existing saved plan, set `identity_status: persisted` and include its exact provider/resource and section identity. For an approved new plan not yet saved, allocate a collision-checked stable `MP-YYYY-MM-DD-NN` ID, set `identity_status: proposed`, and set `native_resource: not-yet-created`. This proposed state is not a missing identity, does not describe a current persisted plan, and is valid only for a new approved plan; an existing plan with missing native identity remains unresolved. Meal Planner persists the new plan after grocery work using the same `plan_id`.

The personal shopper must not select, redesign, or silently substitute recipes. Return the same request ID, Recipe IDs and versions, meal-plan identity object and status, and workbook identity. A stale version, mismatch, or malformed packet requires targeted correction before use. Report capability and per-target persistence status; delegation grants no consent to write.

## Personal Shopper to Meal Planner

Return a `grocery-handoff/v1` shopping packet containing:

- the request ID and capability (`full` or `fallback`);
- the same Recipe IDs and exact approved versions, meal-plan identity object and status, and grocery-workbook identity received;
- exact `Grocery Preferences` workbook identity and tabs read or changed, or their availability status;
- the exact meal-plan identity object and status used;
- per-target persistence state based on canonical native readback, distinguishing task-only changes, proposed/unsaved changes, verified writes, and incomplete changes;
- unresolved availability, label, substitution, or pricing questions.

For `capability: full`, include the price basis, region, effective store order, sources used, date, currency, exclusions, confidence, disclosed fallbacks, store-section list with required and purchase quantities, package assumptions, prices, surplus, `check pantry` effect, checkout spending, pantry contribution, unpriced items, and meal and per-serving allocations when supported. For `capability: fallback`, return only the basic list, exact matches and dated record evidence, unmatched or ambiguous ingredients, missing prices, persistence status, and omitted full-workflow fields defined in [the local grocery integration contract](grocery-integration.md). The meal planner reviews quantities and unresolved safety questions against approved recipes without independently rebuilding a valid full shopping result.
