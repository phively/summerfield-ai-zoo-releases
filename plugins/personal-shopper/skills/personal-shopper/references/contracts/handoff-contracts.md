# Personal Shopper handoff contracts

This is the local authority and handoff contract for Personal Shopper. Read [record management](record-management.md) for workbook identities, retrieval, persistence, and verification. Preserve user-supplied facts, source identity, confirmation state, authorization, and unresolved uncertainty in every request and result.

## Grocery workbook identity

Use the established `Grocery Preferences` workbook and its compatible tabs, including `Store Preferences`, `Store Preferences History`, and `Price Tracker`. Preserve equivalent workbook and tab names. Every reference to a workbook record identifies the provider, immutable workbook resource ID or canonical file identity, visible title, exact worksheet, table or named range when present, stable key and record ID or documented composite key, relevant columns, and any unavailable expected structure. A workbook or worksheet title or row number alone is not an identity.

Resolve the workbook's native routing first. When `Record Index` exists, use it to identify roles and keys, then retrieve only relevant current rows or targeted history. Otherwise use native tables, named ranges, stable key columns, or documented composite keys. Never create a sidecar index, a parallel workbook, or a text database merely because native routing is unfamiliar.

## `grocery-handoff/v1` request

Accept delegated meal-plan grocery work only after the recipes are finalized and safety-reviewed by the caller. Do not choose, redesign, approve, or publish recipes. Do not repeat questions already answered in the packet.

The caller sends one packet with a unique request identity that preserves:

- protocol version and request identity;
- recipe names, finalized status, ingredients and quantities, yields, planned servings, leftovers, material adaptations, and permitted substitutions;
- stable Recipe IDs, exact approved versions, verified named source links, and constraint-sensitive requirements;
- meal-plan identity with `identity_status` and stable `plan_id`: use `identity_status: persisted` with the exact provider/resource and section identity for an existing saved plan, or `identity_status: proposed` with a collision-checked `MP-YYYY-MM-DD-NN` ID and `native_resource: not-yet-created` for an approved new plan that Meal Planner has not saved yet;
- confirmed pantry quantities, separate `check pantry` items, and the region, currency, date, budget, and effective store order;
- exact `Grocery Preferences` workbook identity and available tab, table, named-range, and stable-key mappings;
- product, brand, allergy, medical, label, and other hard requirements;
- task-only facts separately from saved record values; target-specific persistence authorization (including whether the user consented to persist or replace a preference, or explicitly authorized no write); and unresolved questions.

An absent or ambiguous required identity, recipe version, constraint, authorization, or material input stays unresolved and is returned for targeted correction. `proposed` is valid only for an approved new plan whose native plan record does not exist yet; it cannot replace a missing or ambiguous identity for an existing plan. Delegation alone does not grant consent to persist preferences.

## `grocery-handoff/v1` result

Return the same request identity, Recipe IDs and exact approved versions, meal-plan identity object and status, and workbook identity. Echo a proposed plan as proposed; do not claim that Meal Planner's native plan record has been created or saved. Identify `capability: full` and work completed, then include:

- effective price basis: region, store order, sources, date, currency, discounts, exclusions, confidence, and disclosed fallbacks;
- grocery items grouped by store section, with required and purchase quantities, packages, price or range, meals using each item, and likely surplus;
- confirmed pantry deductions, `check pantry` items, checkout spending, pantry contribution, unpriced items, and meal and per-serving allocations;
- exact workbook identity and tabs or records read or changed, with per-target persistence and fresh native readback status (`not attempted`, `proposed/unsaved`, `saved and verified`, or `incomplete`);
- unresolved availability, label, substitution, pricing, or persistence questions and any omitted result fields.

The shopper returns grocery results only. Meal-plan writes and final recipe safety approval remain with the caller. A result with a stale recipe version or mismatched request, plan, or workbook identity requires a targeted correction before use. Report each persistence target by observed state; do not claim a write from an acknowledgement, text export, or nonpersistent Excel session. If the canonical workbook or a required record cannot be accessed, return useful bounded work with the limitation disclosed and all unavailable updates unsaved. An uncertain write must be resolved by stable identity before retry; the caller must not start a second writer while that outcome is unknown.
