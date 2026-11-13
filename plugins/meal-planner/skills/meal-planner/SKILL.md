---
name: meal-planner
description: Coordinate safe, practical household meal plans by confirming allergies and medical restrictions, current-week instructions, and the household or preference records to use. Use for weekly dinner planning, meal schedules, grocery and prep coordination, or plans requiring dietary evidence; delegate recipe work to personal-chef and use Personal Shopper for the full grocery workflow when available, with a bounded local grocery fallback otherwise.
---

# Meal Planner

Own intake, safety, delegation, and final plan coherence. Treat recipe selection, canonical recipe Google Docs, and preference maintenance as `personal-chef` work.

## Apply priorities

Resolve conflicts in this order:

1. Allergies and confirmed medical restrictions
2. The user's current explicit instructions
3. The confirmed household and preference records
4. Practical constraints
5. Variety, novelty, and cost

Never silently relax a higher-priority constraint. Treat the current prompt as newer than a record unless the user declares that record authoritative.

## Run the intake checkpoint

1. Establish dates, requested meals, region, servings, equipment, time, budget, and leftover needs. Default to seven dinners only for an otherwise unspecified weekly plan.
2. Look for an accessible spreadsheet titled `Household Preferences` or a clearly equivalent title, then identify available household, allergy, pantry, schedule, and other planning records. Use the canonical tabs in [references/household-profile.md](references/household-profile.md); accept equivalent existing tab names without creating a competing workbook. When creating a new household record, prefer a Google Sheet in the user's designated Meal Planning folder. Resolve the provider and workbook resource ID or canonical path, then use `Record Index`, a structured table or named range, or the worksheet's stable key definition for bounded retrieval. Do not identify a record by workbook title, worksheet title, or row number alone, and do not claim access to an unavailable source.
3. State concisely which exact records were found, which will be used, and which mentioned records remain unavailable or unconfirmed, including dates or versions when visible. Do not collapse a recipe-history sheet, preference file, and household safety profile into a generic “household record.” Ask whether anything has changed since the relevant records were updated. Do not repeat this checkpoint when the user already confirmed it for the current planning request.
4. Locate the current and historical meal-plan records defined in [shared record management](../../shared/record-management.md). Preserve one clearly equivalent existing Word document, Google Doc, Markdown pair, or selected durable authority; when creating filesystem records, use `meal-plan-current.md` and `meal-plan-history.md`. Identify it by provider and resource ID or canonical path plus the stable `MP-...` or `MH-...` identifier and heading, bookmark, or named section when supported. Read the current plan only when it could affect this request and do not load history without a targeted retrieval condition.
5. Read [references/household-profile.md](references/household-profile.md) when interpreting household or safety records, and read [shared record management](../../shared/record-management.md) before any persistent write, historical retrieval, lifecycle change, or access failure.
6. Separate hard constraints from preferences. Ask a focused question before planning when missing or conflicting information could materially affect allergy or medical safety. Handle ordinary gaps with labeled assumptions.

## Delegate bounded sub-work

Before selecting recipes for a newly requested plan, complete the pre-planning retrospective in [shared record management](../../shared/record-management.md). Read the previous current plan, ask which recipes were actually made, then collect the affected household members' opinions through `personal-chef`. Apply confirmed reusable feedback to the owning records before making the new plan. If the user declines, already answered, nothing was made, or no prior plan exists, continue without inventing feedback. A request to clean records alone does not start a retrospective or create a new meal plan.

Read the canonical [shared handoff contracts](../../shared/handoff-contracts.md) before delegating or accepting delegated results. Read the local [grocery integration contract](../../shared/grocery-integration.md) before any shopper handoff or fallback. Pass shared references by reference; do not create skill-local copies.

- Invoke `$research-briefing` when available for substantive dietary or condition-related guidance, uncertain nutrition claims, or current regional seasonality evidence. Give it the precise question and request claim-level sources. Do not invoke it for routine menu choices.
- Invoke `$personal-chef` when available for all recipe discovery, selection, adaptation, sourcing, preference interviewing, and preference-record updates. If agent delegation is supported, assign this as a bounded sub-task; otherwise activate the skill in the current workflow.
- After the user approves the plan and recipe selection passes safety review, invoke `$personal-shopper:personal-shopper` once only when the active host can actually activate that independent skill. Send the `grocery-handoff/v1` packet from the shared contract, preserving exact Recipe IDs, approved versions, meal-plan identity and status, workbook identity, already answered intake, and target-specific write authorization. For a new approved plan not yet saved, use a collision-checked stable `MP-YYYY-MM-DD-NN` ID with `identity_status: proposed` and `native_resource: not-yet-created`; use `persisted` plus the exact native resource identity for an existing saved plan. Do not use proposed status to fill in missing identity for an existing plan. Do not ask again for information in the packet. Check that the result preserves the request and complete identity object before using it; request targeted correction for a stale version, mismatch, or malformed result. Do not start another writer while a delegated write may have an uncertain outcome.
- If Personal Shopper cannot be activated, follow the local fallback in [grocery integration](../../shared/grocery-integration.md) using only this plugin's resources. Never load Personal Shopper files to perform or explain the fallback. An activated Personal Shopper with inaccessible records reports the R24 limitation itself; this does not transfer its write authority to Meal Planner.
- If a needed skill is unavailable, perform only the necessary fallback work and disclose that fallback briefly. Never lower the evidence or safety standard.

Provide `personal-chef` with:

- confirmed hard constraints and affected household members;
- current-week instructions and practical limits;
- the exact `Meal Preferences` workbook identity and canonical tabs found, or their availability status;
- the exact current meal-plan identity and plan identifier when relevant;
- the preference and recipe-history sources it may use;
- servings, leftover targets, and desired output detail;
- any evidence conclusions that constrain recipe choice.

Require it to return:

- proposed recipes with direct original sources or a clear original-recipe label;
- material adaptations and their reasons;
- active and total time, yield, leftovers, and ingredient-overlap notes;
- constraint-sensitive ingredients or labels needing final verification;
- preference observations and any proposed or completed record changes.
- canonical recipe IDs, Google Doc IDs and links, version/status, content and native-formatting verification results, and verified or pending publication state;
- confirmed prepared or used status before asking for ratings; never infer consumption from plan inclusion.

Do not independently redo recipe selection after a valid handoff. Review and return targeted revision requests when a candidate fails a constraint.

When Personal Shopper is available, pass it the approved packet once with:

- protocol version and request identity;
- finalized recipe ingredients, yields, planned servings, and leftover uses;
- canonical Recipe IDs, verified named Google Doc links, and exact approved versions used for ingredient quantities;
- confirmed pantry inventory and any `check pantry` items;
- the exact `Grocery Preferences` workbook identity and canonical tabs found, or their availability status;
- meal-plan identity with `identity_status`, stable `plan_id`, and native resource identity when persisted;
- region, currency, preferred stores, shopping date, budget, and brand or product requirements when known;
- allergy, medical, label, and substitution constraints that affect purchasing;
- task-only corrections separately from saved record values and exact target-specific persistence authorization, or explicit no-write status.

Require any returned shopper result to preserve the same request, Recipe IDs and versions, meal-plan identity object and status, and workbook identity. For a proposed new plan, persist the final plan using the same stable `plan_id` after grocery work is complete; neither a delegated result nor fallback may claim a native plan write. For a valid full result, use the returned grocery list, purchase quantities, package assumptions, price basis, costs, surplus, unpriced items, and unresolved safety or availability questions; do not ask it to select or redesign recipes. If Personal Shopper cannot be activated, use the local fallback and disclose its narrower capability and omitted fields.

## Validate and assemble the plan

- Verify every candidate and substitution against allergies, medical restrictions, servings, time, equipment, and current-week instructions. Safety approval remains with `meal-planner`.
- Do not diagnose, prescribe, or imply that a plan treats a condition. When the diet is not sufficiently defined, request clinician or dietitian guidance and plan only within confirmed limits.
- Cite substantive dietary recommendations near the claim. Distinguish established evidence, reasonable inference, and uncertainty.
- Coordinate ingredient reuse, fragile ingredients, leftovers, freezer meals, and batch prep across the week. Review shopper or fallback quantities against the approved recipes rather than rebuilding a valid list without cause.
- Subtract pantry items only when confirmed. Distinguish active from unattended time and avoid unnecessary parallel cooking.
- Present full checkout spending separately from allocated meal cost only when supplied by a valid full Personal Shopper result. A local fallback may show only relevant dated existing price evidence and missing prices; it cannot estimate checkout totals, optimize packages, or allocate meal or per-serving costs. Preserve evidence dates, location, basis, confidence, ranges, unpriced items, and material exclusions when those fields are present.
- Label a local result as `fallback`; retain exact recipe versions, matched record identities and evidence dates, unmatched or ambiguous ingredients, missing prices, per-target persistence status, and omitted full-workflow outputs. Do not present a partial list as a complete or fully costed basket.
- Use [references/output-format.md](references/output-format.md) for the final response, scaled to the request. Before persisting or reformatting a plan, read [the canonical meal-plan document template](references/meal-plan-document-template.md) and the linked native-formatting contract.

## Finalize and maintain meal-plan records

- Own the single current/history meal-plan pair and update the selected authorities in place. Other Meal Planner skills may read relevant state and request changes but must not create parallel plan records.
- Persist only a user-confirmed finalized plan. Do not archive drafts, rejected candidates, trivial wording changes, or routine process events.
- After user approval, have `personal-chef` save new approved recipes and approved adaptations in the selected `Recipes` folder, update existing canonical Docs in place, and verify the Recipe Catalog pointers. Recipe selection and safety approval alone are not user approval. Persist the new current plan only after every required canonical recipe has verified content, native formatting, and descriptive links, and every required link resolves and matches the approved version. Treat an unavailable or failed recipe-formatting check as pending publication. Retry by recipe ID without creating duplicate Docs.
- Keep meal-planning records within the user's designated Meal Planning folder, recipe documents within `Recipes`, and audit or recovery artifacts within dated child folders under `Audits`. Resolve and pass all three folder IDs; preserve equivalent existing names and organization. Do not search or write similarly named backup folders as current authorities.
- Prefer Google Docs for newly created narrative meal-plan records when Drive is accessible. Read the canonical meal-plan template and shared native-formatting contract, then use native `Title`, `Heading 1`, `Heading 2`, `Normal text`, lists, tables, and hyperlinks. Read back and repair the affected structure and styles before reporting persistence complete. Preserve an existing compatible authority rather than converting it implicitly; file-type or provider migration requires explicit user permission and a passed staged audit.
- Finalize coherently: archive the previously current plan when present and valuable, replace the current authority, add only useful pointers and relationships, and verify exactly one current plan remains. Do not claim persistence if a required write fails.
- Keep the current plan operationally complete without history and preserve exact record identities, safety constraints, servings, recipes, adaptations, dates, unresolved questions, and provenance.
- Check the shared format-aware review triggers at authorized write or consequential-use boundaries. Before compaction, splitting, migration, deduplication, or authority transfer, stage and validate the complete before/after records under the shared audit protocol; do not replace a canonical record after a failed audit.
- Run the retrospective before the next plan, rather than after its approval. If feedback changes the current approved plan's recipe ingredients, servings, or safety assumptions, reopen the affected approval and shopping work before publishing changes to that plan.
- Do not write chef-owned records. Do not write shopper-owned records except for the exact existing grocery rows permitted by the local fallback contract when Personal Shopper is unavailable and each target is authorized and verifiable. Send other requested updates with exact identities, stable identifiers, source, attribution, confirmation status, effective date, uncertainty, and requested lifecycle action through the shared contract.

## Final check

Confirm internally that:

- the record and update checkpoint was completed or already satisfied;
- no hard constraint or substitution violates safety requirements;
- recipe work came from `personal-chef` when available;
- grocery work came from a valid `personal-shopper` result when available, or is explicitly labeled `fallback` and uses only finalized recipes;
- full purchase totals and meal-cost allocations are included only when supported by a valid full shopper result; otherwise fallback gaps, missing prices, persistence states, and omitted outputs are visible;
- sources and record updates are accurately represented;
- newly created or reformatted Google Docs have verified required native structure and paragraph styles, or the formatting check is explicitly pending;
- the finalized current plan and any required historical entry were updated coherently, or persistence failure is explicit;
- health claims have appropriate evidence and citations;
- assumptions and unresolved limitations are visible.
