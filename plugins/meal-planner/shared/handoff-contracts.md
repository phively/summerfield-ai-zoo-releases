# Shared handoff contracts

This file is the canonical authority, ownership, and coordination contract for the plugin's skills. Read it from its plugin-level path; do not copy it into a skill folder. Preserve user-supplied facts, source identity, confirmation state, and unresolved uncertainty across every handoff. Read [record-management.md](record-management.md) for schemas, lifecycle procedures, targeted retrieval, and failure behavior.

## Workbook routing

Use these canonical workbook titles and tabs. Recognize clearly equivalent existing titles or tab names, but use the canonical names when creating new records:

| Owner | Canonical workbook | Canonical tabs |
| --- | --- | --- |
| Meal Planner | `Household Preferences` | Workbook-local `Record Index`; `Household Profile`, `Safety Constraints`, `Planning Preferences`, optional `Pantry Inventory`, and `Household History` |
| Personal Chef | `Meal Preferences` | Workbook-local `Record Index`; `Household Preferences`, `Household Preferences History`, `Ingredient Ratings`, `Ingredient Ratings History`, `Recipe Ratings`, and `Recipe History` |
| Personal Shopper | `Grocery Preferences` | Workbook-local `Record Index`; `Store Preferences`, `Store Preferences History`, and `Price Tracker` |

Every handoff must preserve the exact workbook title and link or file identity by identifying the provider, immutable workbook resource ID or canonical link/file path, visible workbook title, exact worksheet, table or named range when present, stable key column and record ID or documented composite key, relevant columns, and any expected workbook structure that was unavailable. A workbook title, worksheet title, or row number alone is insufficient. Pass accessible shared records by identity; never create skill-local static copies.

Use native workbook routing. When present, read `Record Index` first and then retrieve only the relevant current rows or targeted history. Otherwise use the worksheet's stable key column, structured table, named range, or documented composite key. Do not create a sidecar file merely to index a workbook, and do not pass complete worksheet or archive contents when bounded rows preserve complete relevant recall.

## Record authority and access

`meal-planner` owns the `Household Preferences` workbook and the single current/history meal-plan pair. Use `meal-plan-current.md` and `meal-plan-history.md` when creating new filesystem records, or preserve one clearly equivalent existing Word document, Google Doc, Markdown pair, or other selected durable authority. All skills may read relevant current state; only `meal-planner` creates or updates these records.

`personal-chef` owns the `Meal Preferences` workbook, including current culinary preferences and recipe ratings plus their historical companions. All skills may read relevant current state; only `personal-chef` creates or updates these records.

`personal-shopper` owns the `Grocery Preferences` workbook. All skills may read relevant current state and price evidence; only `personal-shopper` creates or updates these records.

Current records govern over history unless the user corrects them or requests historical reconstruction. Read history only under a targeted retrieval condition in [record-management.md](record-management.md). Never pass a complete archive, create a parallel authority, infer that a retrieval miss proves no history exists, or claim persistence after a partial write.

Every record-update request must include the exact current and historical identities when visible, expressed with the native resource, worksheet, table or named range, stable key and relevant columns; stable entry identifier when applicable; proposed state; source and household-member attribution; confirmation status; effective date if known; lifecycle intent; reason the change is reusable; uncertainty; and expected owner response. The prohibited information includes secrets, unrelated history, complete worksheets or source documents, and unsupported conclusions presented as facts.

## Personal Chef to Meal Planner

Return a recipe-selection packet containing:

- finalized or proposed status for every recipe;
- recipe title, source URL or original-recipe label, yield, and planned servings;
- ingredient quantities, active time, total time, equipment, and leftover yield;
- material adaptations and reasons;
- constraint-sensitive ingredients, labels, substitutions, and cross-contact questions requiring safety review;
- preference evidence used, open preference questions, and completed or proposed record changes;
- exact `Meal Preferences` workbook identity and tabs read or changed, or their availability status;
- exact current meal-plan identity and plan identifier when supplied, without copying the complete plan;
- ingredient-overlap, batch-prep, freezer, and leftover notes.

The meal planner owns final safety approval. A chef handoff must never claim that a recipe is medically safe.

For feedback requested after a plan, return only confirmed preparation or use, member attribution, current ratings or preferences changed, historical entries created, material modifications, unresolved questions, and exact records changed. If preparation or consumption is unconfirmed, return no rating update and identify the smallest useful follow-up.

## Meal Planner to Personal Chef

For recipe selection, send the bounded constraint and preference packet already defined by the skills. For a post-plan feedback request, include the exact current meal-plan identity and plan identifier, recipe or ingredient identities, confirmed prepared or used status, preparation or modification, affected household members, prior current rating and date when visible, why review is decision-relevant now, and whether the user authorized persistence.

Do not request feedback merely because a recipe appeared in a plan or a fixed interval elapsed. `personal-chef` applies the feedback check-in gate and owns every preference or rating write.

## Meal Planner to Personal Shopper

Send a shopping packet only after recipe selection and safety review are complete. Include:

- final recipe names, ingredient quantities, source yields, planned servings, and leftover uses;
- confirmed pantry quantities plus separate `check pantry` items;
- region, currency, shopping date, budget, and preferred stores in effective order;
- required brands, products, labels, allergy constraints, medical constraints, and permitted substitutions;
- exact `Grocery Preferences` workbook identity and available canonical tabs;
- exact current meal-plan identity and plan identifier;
- whether the user consented to persist or replace store preferences.

The personal shopper must not select, redesign, or silently substitute recipes.

## Personal Shopper to Meal Planner

Return a shopping packet containing:

- price basis, region, effective store order, sources used, date, currency, exclusions, confidence, and disclosed fallbacks;
- grocery items grouped by store section with required quantity, purchase quantity or packages, price or range, meals using the item, and surplus notes;
- `check pantry` items and their possible effect on checkout cost;
- checkout spending, pantry contribution, unpriced items, and meal and per-serving cost allocations;
- exact `Grocery Preferences` workbook identity and tabs read or changed, or their availability status;
- exact current meal-plan identity and plan identifier used;
- unresolved availability, label, substitution, or pricing questions.

The meal planner reviews quantities and unresolved safety questions against the approved recipes without independently rebuilding a valid shopping result.
