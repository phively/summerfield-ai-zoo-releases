# Delegated meal-plan grocery workflow

Use this workflow only when Meal Planner delegates grocery work for a finalized, safety-reviewed meal plan. A direct request to shop for groceries is product shopping and does not enter this recipe gate; use [product selection](product-selection.md).

## Accept the approved packet

Read [the shared handoff contract](contracts/handoff-contracts.md) before accepting a request or returning results. Accept `grocery-handoff/v1` only with a packet from the caller that identifies finalized, safety-reviewed recipes. Do not choose, redesign, approve, or publish recipes, weaken product requirements, or repeat intake already answered in the packet.

Carry forward the exact recipe IDs and approved versions, the meal-plan identity object, and the exact grocery-workbook identity and available native role, tab, table or range, key, and column mappings. For an existing saved plan, require `identity_status: persisted` and its exact native resource and section identity. For an approved new plan not yet saved, accept `identity_status: proposed` only with a collision-checked stable `MP-YYYY-MM-DD-NN` ID and `native_resource: not-yet-created`; this does not authorize or imply a plan write. Preserve source links and task-relevant source facts, ingredient quantities, yields, servings, leftovers, material adaptations, permitted substitutions, confirmed pantry amounts, constraints, effective store order, region, date, currency, budget, consent and target-specific authorization, and unresolved questions. Do not copy the full meal plan when its identity and bounded relevant facts suffice.

If a required identity, version, hard constraint, authorization, or material input is missing or ambiguous, request only the targeted correction needed to proceed. A proposed plan state is not a substitute for a missing identity on an existing plan. If the packet's recipe version is stale or does not match the current plan identity, stop use of that result and ask Meal Planner for a corrected approved packet before continuing.

## Build the grocery list

- Scale each finalized recipe to its planned servings and preserve leftover use. Normalize and consolidate only quantities with compatible units, products, preparation, variety, brand, allergy status, and other specifications. Keep incompatible ingredient requirements separate.
- Subtract only confirmed pantry quantities. Keep uncertain amounts under `Check pantry`; do not treat them as available.
- Convert required amounts into realistic package quantities only when product and package evidence supports the conversion. Show required and purchase amounts and package counts so rounding is visible. Note likely surplus and which meals use each ingredient.
- Group items by the user's effective grocery store order and store sections. Otherwise use produce, meat, seafood, dairy or alternatives, bakery, pantry, frozen, beverages, and miscellaneous. Keep related items together within each section.
- Preserve each recipe's brand, allergy, medical, label, and substitution constraints. Flag product labels or availability that Meal Planner must verify.

## Estimate prices and costs

Read [pricing and allocation](pricing-and-allocation.md) when prices or meal costs are requested. Read [store preferences](store-preferences.md) when store order or source choice affects research. Use the effective grocery store order and its preferred website first, then documented source fallbacks. Identify the source and reason for a fallback without repeatedly asking permission.

For each observation or estimate, identify the store or basis, matching region or disclosed fallback, date checked, currency, package identity, regular, sale, or member status, material exclusions, and confidence. Do not present an estimate as a quoted price, an unknown price as zero, or a conditional offer as eligible without confirmation. Use ranges when price, package size, or conversion is uncertain.

Keep these quantities distinct:

- **Required quantity:** recipe amount after serving scale and compatible consolidation.
- **Purchase quantity:** whole packages needed after confirmed pantry deductions and package rounding.
- **Checkout cost:** full packages bought for the trip, counted once even when shared across meals.
- **Allocated meal cost:** the priced quantity consumed by each meal, including its share of common ingredients.
- **Pantry contribution:** replacement-value estimate for confirmed inventory consumed, separate from new checkout spending.

Use the formulas and uncertainty rules in [pricing and allocation](pricing-and-allocation.md). Show missing prices as unknown and mark affected meal totals partial. Do not assign package surplus to the first meal or count a shared purchase multiple times.

## Return the result

Return a `grocery-handoff/v1` result with the same request, recipe/version, meal-plan identity object and status, and workbook identity. Echo a proposed plan as proposed without claiming a native plan write. Include:

1. Effective price basis: region, grocery store order, sources, date, currency, discount status, exclusions, confidence, and disclosed fallbacks.
2. Grocery list by store and section, with required and purchase quantities, packages, price or range, meals using each ingredient, and likely surplus.
3. Confirmed pantry deductions and `Check pantry` items.
4. Checkout spending, pantry contribution, unknown prices, and meal and per-serving allocations when supported.
5. Exact workbook identity and native tabs or records read or changed, with target-specific consent, persistence, and readback status.
6. Source facts, unresolved availability, label, substitution, pricing, or persistence questions, and any omitted outputs.

Return grocery results only. Meal-plan writes and final recipe safety approval remain with Meal Planner. A handoff does not authorize saving or replacing preferences unless it carries the user's consent. Do not claim a write from an acknowledgement, text export, or nonpersistent workbook session, and do not block useful grocery work on an optional persistent update.
