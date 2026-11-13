# Grocery integration contract

This file is the complete grocery integration and local fallback contract for Meal Planner. It works when Personal Shopper is unavailable and never requires Meal Planner to open Personal Shopper package files. Read [record management](record-management.md) for native record identities, retrieval limits, and shared verification rules.

## Capability selection

Use protocol `grocery-handoff/v1` for delegated meal-plan grocery work. Meal Planner owns the request, approved recipe packet, and final meal-plan document; Personal Shopper owns the full grocery workflow and shopping records.

After the plan is approved and its recipes are finalized and safety-reviewed, invoke the independently installed `personal-shopper:personal-shopper` skill once when the host can actually activate it. Send the complete approved packet described in [handoff contracts](handoff-contracts.md), including exact Recipe IDs and approved versions, meal-plan identity and status, the established Grocery Preferences workbook identity, already answered intake, and target-specific persistence authorization. Do not ask intake questions again when their answers are in the packet. Preserve the same request, recipe/version, meal-plan identity object and status, and workbook identity in the result.

If the host cannot activate Personal Shopper, use this local fallback. Do not simulate activation, inspect or load another plugin's files, or continue a fallback after a delegated writer may have made an uncertain change. A present Personal Shopper whose records are inaccessible remains responsible for reporting the access limitation under R24; Meal Planner does not start a competing write. A stale version, mismatched identity, or malformed result must be returned for targeted correction before use. If a delegated write's outcome is uncertain, resolve it with the owner before any other writer acts.

## Inputs and identity checks

The fallback receives:

- a unique request identity for the `grocery-handoff/v1` exchange;
- the finalized, safety-reviewed recipe packet, with each Recipe ID, canonical recipe document identity, exact approved version, ingredient, yield, planned servings, leftovers, material adaptation, and permitted substitution;
- meal-plan identity with `identity_status`, stable `plan_id`, and native resource identity when persisted;
- the established Grocery Preferences workbook identity and its available native role, worksheet, table or named range, stable key, and relevant field mappings;
- current user instructions, confirmed pantry quantities and separate `check pantry` items, applicable region and currency, and any exact write authorizations; and
- unresolved safety, product, brand, allergy, medical, label, quantity, unit, and availability constraints.

For an existing saved plan, set `identity_status: persisted` and include the exact provider/resource and section identity. For an approved new plan not yet saved, use a collision-checked stable `MP-YYYY-MM-DD-NN` ID with `identity_status: proposed` and `native_resource: not-yet-created`. This state applies only to an approved new plan; it does not excuse missing native identity on an existing plan. Before using a delegated result, compare its request ID, every Recipe ID and approved version, the complete meal-plan identity object and status, and the grocery-workbook identity with the request. Do not use stale, substituted, or incomplete identities. Return only the smallest correction needed. Do not ask the user to repeat information already supplied.

Resolve the Grocery Preferences authority using native routing and bounded reads. Use the workbook's existing identities, headers, key mappings, and relevant records; a title, tab name, or row number alone is insufficient. If the authority or required record cannot be accessed or resolved, continue with the approved ingredient requirements and explicit current-task information, report the missing data, and leave all proposed updates unsaved. Do not create a workbook, worksheet, table, index, text database, or competing authority.

## Local fallback operations

The fallback is intentionally limited to existing records and explicit current-task facts. Mark the result capability as `fallback`. It may:

| Operation | Allowed behavior | Boundary |
| --- | --- | --- |
| Read grocery context | Read only relevant existing grocery store-order, grocery-preference, and dated product-price records, with targeted material history when needed | Same canonical workbook; no archive or whole-workbook load by default |
| Match ingredients | Match an approved ingredient to an unambiguous existing product/specification and compatible quantity unit, respecting material brand, allergen, preparation, region, and other constraints | Do not infer equivalence, convert ambiguous units, or choose among plausible records |
| Prepare a basic list | Consolidate only simple compatible quantities; apply confirmed pantry deductions; group by existing store section when known; show matched records and dated evidence, unmatched or ambiguous ingredients, and missing prices | Do not conduct live research, verify current offers, optimize package sizes, allocate costs to meals or servings, or claim a full shopping result |
| Apply a task-only correction | Use explicit current user instructions for this request | Do not change saved values or represent the correction as reusable preference |
| Update an existing grocery record | Make a task-relevant change to an existing grocery store-order or preference record only with exact user-backed authorization; update a material required history companion when applicable | Preflight all required targets. No general-category expansion, inferred membership, unrelated update, or structural change |
| Update an existing price observation | Correct an identified observation or record a complete observation explicitly supplied by the user, with stable identity and provenance, only under exact authorization | Never invent a price or product match; never create a missing worksheet or new authority |

No other writes are permitted. In particular, do not create or replace a workbook, change ownership/provider/file type, rename or restructure existing tabs or columns, migrate/clean/compact records, add general product-shopping context, or write meal-plan or recipe records through the shopping fallback.

## Consent and write verification

Task-relevant information may be used for the current request without being saved. Keep those task-only facts separate from current saved values. Persist only the exact fields and targets the user authorized or an existing confirmed workflow explicitly covers; delegation alone grants no consent.

Before writing, resolve the current and required history identities, stable keys, target fields, authorization, and supported native verification. If a required existing target or verification route is missing, leave the whole proposed change unsaved. For each authorized target, report one of: `not attempted`, `proposed/unsaved`, `saved and verified`, or `incomplete`. A write is verified only after a fresh read of the canonical native record and relevant native properties. If a paired change is only partially verified, describe the verified target and failed target separately and mark the combined change incomplete. After a timeout or uncertain append, look up the stable key before any retry. Do not imply atomicity across targets.

## Result

Return the same request, Recipe IDs and approved versions, meal-plan identity object and status, and workbook identity. Identify capability as `full` or `fallback`, then report only fields supported by that capability. Echo a proposed plan as proposed and do not claim the native plan record was saved; Meal Planner saves it under the same `plan_id` after the grocery work is complete.

A fallback result includes the basic ingredient list, approved required amounts, compatible simple consolidations, confirmed pantry deductions, matched record identities and dates, unmatched or ambiguous items, missing prices, explicit task-only corrections, per-target persistence status, and the full-workflow fields omitted. A price observation remains dated historical evidence; it is not a newly verified offer or an estimate of today's checkout basket. Do not return package-optimized quantities, live offer research, checkout spending, pantry contribution totals, meal or per-serving costs, or a fully costed basket from the fallback.

A full result must pass the identity checks above. Meal Planner reviews quantities and unresolved safety questions but does not repeat a valid shopper analysis or write shopper records outside this fallback boundary. Meal-plan writes and final safety approval always remain with Meal Planner.
