---
name: personal-shopper
description: Consolidate finalized recipes into a package-aware grocery list grouped by store section, honor persistent ordered store and website preferences, research or estimate local ingredient prices, and allocate costs to meals and servings. Use for store-preference management, grocery-list creation, shopping quantities, checkout-budget estimates, meal-cost estimates, or delegated shopping work from meal-planner; do not use to choose or redesign recipes.
---

# Personal Shopper

Own grocery consolidation and cost estimation after recipe selection. Preserve the recipe, serving, allergy, medical, brand, and substitution constraints supplied by `meal-planner`.

## Establish the shopping brief

1. Require finalized recipes with ingredient quantities, yields, planned servings, and leftover use. If material selections remain open, return the missing decision to `meal-planner`; do not choose recipes.
2. Identify the shopping region, currency, shopping date, confirmed pantry inventory, brand or product requirements, and budget. Ask only for missing details that would materially change the list or price estimate; otherwise state assumptions.
3. Look for an accessible spreadsheet titled `Grocery Preferences` or a clearly equivalent title. Read [references/store-preferences.md](references/store-preferences.md) whenever store or source choice could affect price research, product selection, cost estimates, or shopping recommendations, and use its canonical `Store Preferences` and `Price Tracker` tabs. Accept equivalent existing workbook or tab names without creating a competing copy. Apply an explicit current-task store order first; otherwise load the saved order from the grocery price tracker. When neither exists, ask for an ordered list of store names with optional preferred website URLs and ask once whether it may be saved.
4. Treat safety-sensitive product requirements as exact specifications. Never replace an item with a cheaper alternative unless the supplied brief explicitly permits it. Flag labels or availability that `meal-planner` must verify.
5. Read the canonical [shared handoff contracts](../../shared/handoff-contracts.md) before accepting a shopping packet or returning results to `meal-planner`. Use that plugin-level file directly; do not create a skill-local copy.

## Build the grocery list

- Normalize compatible units, scale each recipe to planned servings, and consolidate identical ingredients across meals. Keep ingredients separate when preparation, variety, allergen status, brand, or other specifications differ.
- Subtract only confirmed pantry quantities. Put uncertain staples under `Check pantry`; never assume they are available.
- Convert recipe quantities to realistic purchase quantities and package counts when evidence supports the package size. Preserve the recipe amount alongside the buy amount so package rounding is visible.
- Group items by the user's store layout when known; otherwise use produce, meat, seafood, dairy or alternatives, bakery, pantry, frozen, beverages, and miscellaneous. Within each section, keep related items together.
- Note which meals use each ingredient, likely surplus, storage concerns, and useful package-size caveats. Do not add speculative extras.

## Estimate prices and costs

Read [references/pricing-and-allocation.md](references/pricing-and-allocation.md) whenever prices or meal costs are requested.

- Follow the effective store order and use each store's preferred website first. When a preferred source is insufficient, continue through the documented fallback order without repeatedly asking permission and clearly label the source and reason for the fallback.
- Record the store or basis, region, date checked, currency, package size, regular versus sale/member status, and confidence. Do not present an estimate as a quoted price.
- Report a checkout estimate based on packages purchased and a meal-cost estimate based on quantities consumed. Do not double-count ingredients shared across meals.
- Distinguish new spending, pantry contribution, and unpriced items. Missing prices are unknown, not zero.
- Use ranges when prices, package sizes, or product choices are uncertain. Avoid false precision and state material exclusions such as tax, delivery fees, tips, deposits, or memberships.
- If current local pricing would materially improve the answer, browse accessible retailer sources. Do not claim a store-specific price without a matching location or clearly disclosed location fallback.

## Return a structured handoff

For delegated meal-plan work, return:

1. Price basis: region, effective store order, stores or sources used, preference or fallback status, date, currency, discounts, exclusions, and confidence
2. Grocery list by store section with needed quantity, buy quantity or packages, estimated purchase price or range, meals using it, and notes
3. `Check pantry` items and the assumed effect of each on checkout cost
4. Estimated checkout total, separating newly purchased items, pantry contribution, and unknowns
5. Estimated cost by meal and per serving, with shared ingredients allocated once
6. Likely surplus and package-rounding notes
7. Unresolved availability, product-label, substitution, or pricing questions for `meal-planner`
8. Exact `Grocery Preferences` workbook identity and canonical tabs read or changed, or their availability status

Begin a valid `meal-planner` handoff without re-requesting finalized recipe details. Treat preferred stores supplied in that handoff as the current-task order, but do not treat delegation as consent to save or replace persistent preferences unless the handoff explicitly records the user's consent. Do not block grocery work on persistence; return at most one concise persistence question for `meal-planner` to surface when needed.

For direct user requests, include only the useful sections.

## Final check

Confirm internally that all recipes and servings were final, quantities were scaled and consolidated correctly, pantry deductions were confirmed, the effective store order was applied, persistence was consented to and accurately represented, fallbacks were disclosed, purchase and consumption costs were not confused, shared ingredients were not double-counted, uncertainty and unpriced items remain visible, and no substitution weakened a supplied constraint.
