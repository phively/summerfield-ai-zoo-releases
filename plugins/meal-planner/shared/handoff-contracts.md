# Shared handoff contracts

This file is the canonical contract for coordination among the plugin's skills. Read it from its plugin-level path; do not copy it into a skill folder. Preserve user-supplied facts, source identity, and unresolved uncertainty across every handoff.

## Workbook routing

Use these canonical workbook titles and tabs. Recognize clearly equivalent existing titles or tab names, but use the canonical names when creating new records:

| Owner | Canonical workbook | Canonical tabs |
| --- | --- | --- |
| Meal Planner | `Household Preferences` | `Household Profile`, `Safety Constraints`, `Planning Preferences`, and optional `Pantry Inventory` |
| Personal Chef | `Meal Preferences` | `Household Preferences`, `Recipe History` |
| Personal Shopper | `Grocery Preferences` | `Store Preferences`, `Price Tracker` |

Every handoff must identify the exact workbook title and link or file identity, the exact tabs used or changed, and any expected workbook or tab that was unavailable. Pass accessible shared records by identity; never create skill-local static copies.

## Personal Chef to Meal Planner

Return a recipe-selection packet containing:

- finalized or proposed status for every recipe;
- recipe title, source URL or original-recipe label, yield, and planned servings;
- ingredient quantities, active time, total time, equipment, and leftover yield;
- material adaptations and reasons;
- constraint-sensitive ingredients, labels, substitutions, and cross-contact questions requiring safety review;
- preference evidence used, open preference questions, and completed or proposed record changes;
- exact `Meal Preferences` workbook identity and tabs read or changed, or their availability status;
- ingredient-overlap, batch-prep, freezer, and leftover notes.

The meal planner owns final safety approval. A chef handoff must never claim that a recipe is medically safe.

## Meal Planner to Personal Shopper

Send a shopping packet only after recipe selection and safety review are complete. Include:

- final recipe names, ingredient quantities, source yields, planned servings, and leftover uses;
- confirmed pantry quantities plus separate `check pantry` items;
- region, currency, shopping date, budget, and preferred stores in effective order;
- required brands, products, labels, allergy constraints, medical constraints, and permitted substitutions;
- exact `Grocery Preferences` workbook identity and available canonical tabs;
- whether the user consented to persist or replace store preferences.

The personal shopper must not select, redesign, or silently substitute recipes.

## Personal Shopper to Meal Planner

Return a shopping packet containing:

- price basis, region, effective store order, sources used, date, currency, exclusions, confidence, and disclosed fallbacks;
- grocery items grouped by store section with required quantity, purchase quantity or packages, price or range, meals using the item, and surplus notes;
- `check pantry` items and their possible effect on checkout cost;
- checkout spending, pantry contribution, unpriced items, and meal and per-serving cost allocations;
- exact `Grocery Preferences` workbook identity and tabs read or changed, or their availability status;
- unresolved availability, label, substitution, or pricing questions.

The meal planner reviews quantities and unresolved safety questions against the approved recipes without independently rebuilding a valid shopping result.
