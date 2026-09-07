---
name: meal-planner
description: Coordinate safe, practical household meal plans by confirming allergies and medical restrictions, current-week instructions, and the household or preference records to use. Use for weekly dinner planning, meal schedules, grocery and prep coordination, or plans requiring dietary evidence; delegate recipe work to personal-chef and finalized grocery and cost estimates to personal-shopper when available.
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
2. Look for an accessible spreadsheet titled `Household Preferences` or a clearly equivalent title, then identify available household, allergy, pantry, schedule, and other planning records. Use the canonical tabs in [references/household-profile.md](references/household-profile.md); accept equivalent existing tab names without creating a competing workbook. Resolve the provider and workbook resource ID or canonical path, then use `Record Index`, a structured table or named range, or the worksheet's stable key definition for bounded retrieval. Do not identify a record by workbook title, worksheet title, or row number alone, and do not claim access to an unavailable source.
3. State concisely which exact records were found, which will be used, and which mentioned records remain unavailable or unconfirmed, including dates or versions when visible. Do not collapse a recipe-history sheet, preference file, and household safety profile into a generic “household record.” Ask whether anything has changed since the relevant records were updated. Do not repeat this checkpoint when the user already confirmed it for the current planning request.
4. Locate the current and historical meal-plan records defined in [shared record management](../../shared/record-management.md). Preserve one clearly equivalent existing Word document, Google Doc, Markdown pair, or selected durable authority; when creating filesystem records, use `meal-plan-current.md` and `meal-plan-history.md`. Identify it by provider and resource ID or canonical path plus the stable `MP-...` or `MH-...` identifier and heading, bookmark, or named section when supported. Read the current plan only when it could affect this request and do not load history without a targeted retrieval condition.
5. Read [references/household-profile.md](references/household-profile.md) when interpreting household or safety records, and read [shared record management](../../shared/record-management.md) before any persistent write, historical retrieval, lifecycle change, or access failure.
6. Separate hard constraints from preferences. Ask a focused question before planning when missing or conflicting information could materially affect allergy or medical safety. Handle ordinary gaps with labeled assumptions.

## Delegate bounded sub-work

Before selecting recipes for a newly requested plan, complete the pre-planning retrospective in [shared record management](../../shared/record-management.md). Read the previous current plan, ask which recipes were actually made, then collect the affected household members' opinions through `personal-chef`. Apply confirmed reusable feedback to the owning records before making the new plan. If the user declines, already answered, nothing was made, or no prior plan exists, continue without inventing feedback. A request to clean records alone does not start a retrospective or create a new meal plan.

Read the canonical [shared handoff contracts](../../shared/handoff-contracts.md) before delegating or accepting delegated results. Pass the shared file by reference; do not create a skill-local copy.

- Invoke `$research-briefing` when available for substantive dietary or condition-related guidance, uncertain nutrition claims, or current regional seasonality evidence. Give it the precise question and request claim-level sources. Do not invoke it for routine menu choices.
- Invoke `$personal-chef` when available for all recipe discovery, selection, adaptation, sourcing, preference interviewing, and preference-record updates. If agent delegation is supported, assign this as a bounded sub-task; otherwise activate the skill in the current workflow.
- Invoke `$personal-shopper` when available after recipe selection and safety review are complete. Give it the final recipes and servings to consolidate grocery quantities, estimate package-aware purchase costs, and allocate ingredient costs to meals. If agent delegation is supported, assign this as a bounded sub-task; otherwise activate the skill in the current workflow.
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
- canonical recipe IDs, Google Doc IDs and links, version/status, and verified or pending publication state;
- confirmed prepared or used status before asking for ratings; never infer consumption from plan inclusion.

Do not independently redo recipe selection after a valid handoff. Review and return targeted revision requests when a candidate fails a constraint.

After approving the final recipes, provide `personal-shopper` with:

- finalized recipe ingredients, yields, planned servings, and leftover uses;
- canonical recipe IDs, verified Google Doc links, and the versions used for ingredient quantities;
- confirmed pantry inventory and any `check pantry` items;
- the exact `Grocery Preferences` workbook identity and canonical tabs found, or their availability status;
- the exact current meal-plan identity and plan identifier;
- region, currency, preferred stores, shopping date, budget, and brand or product requirements when known;
- allergy, medical, label, and substitution constraints that affect purchasing.

Require it to return a grocery list by store section, purchase quantities and package assumptions, price basis and confidence, estimated checkout spending, pantry contribution, meal and per-serving cost estimates, surplus, unpriced items, and unresolved safety or availability questions. Do not ask it to select or redesign recipes.

## Validate and assemble the plan

- Verify every candidate and substitution against allergies, medical restrictions, servings, time, equipment, and current-week instructions. Safety approval remains with `meal-planner`.
- Do not diagnose, prescribe, or imply that a plan treats a condition. When the diet is not sufficiently defined, request clinician or dietitian guidance and plan only within confirmed limits.
- Cite substantive dietary recommendations near the claim. Distinguish established evidence, reasonable inference, and uncertainty.
- Coordinate ingredient reuse, fragile ingredients, leftovers, freezer meals, and batch prep across the week. Review `personal-shopper` quantities against the approved recipes rather than rebuilding its list without cause.
- Subtract pantry items only when confirmed. Distinguish active from unattended time and avoid unnecessary parallel cooking.
- Present checkout spending separately from allocated meal cost. Preserve pricing date, location, source basis, confidence, ranges, unpriced items, and material exclusions; do not convert estimates into false precision.
- Use [references/output-format.md](references/output-format.md) for the final response, scaled to the request.

## Finalize and maintain meal-plan records

- Own the single current/history meal-plan pair and update the selected authorities in place. Other Meal Planner skills may read relevant state and request changes but must not create parallel plan records.
- Persist only a user-confirmed finalized plan. Do not archive drafts, rejected candidates, trivial wording changes, or routine process events.
- After user approval, have `personal-chef` save new approved recipes and approved adaptations in the selected Recipes folder, update existing canonical Docs in place, and verify the Recipe Catalog pointers. Recipe selection and safety approval alone are not user approval. Persist the new current plan only after every required canonical recipe link resolves and its contents match the approved version. Retry by recipe ID without creating duplicate Docs.
- Keep meal-planning records within the user's designated Meal Planning folder and recipe documents within its designated recipe folder. Resolve and pass both folder IDs; preserve existing names and organization. Do not search or write similarly named backup folders as current authorities.
- Finalize coherently: archive the previously current plan when present and valuable, replace the current authority, add only useful pointers and relationships, and verify exactly one current plan remains. Do not claim persistence if a required write fails.
- Keep the current plan operationally complete without history and preserve exact record identities, safety constraints, servings, recipes, adaptations, dates, unresolved questions, and provenance.
- Check the shared format-aware review triggers at authorized write or consequential-use boundaries. Before compaction, splitting, migration, deduplication, or authority transfer, stage and validate the complete before/after records under the shared audit protocol; do not replace a canonical record after a failed audit.
- Run the retrospective before the next plan, rather than after its approval. If feedback changes the current approved plan's recipe ingredients, servings, or safety assumptions, reopen the affected approval and shopping work before publishing changes to that plan.
- Do not write chef-owned ratings or shopper-owned records directly. Send the exact identities, stable identifiers, source, attribution, confirmation status, effective date, uncertainty, and requested lifecycle action through the shared contract.

## Final check

Confirm internally that:

- the record and update checkpoint was completed or already satisfied;
- no hard constraint or substitution violates safety requirements;
- recipe work came from `personal-chef` when available;
- grocery and cost work came from `personal-shopper` when available and used only finalized recipes;
- times, servings, leftovers, grocery quantities, purchase totals, and meal-cost allocations are consistent;
- sources and record updates are accurately represented;
- the finalized current plan and any required historical entry were updated coherently, or persistence failure is explicit;
- health claims have appropriate evidence and citations;
- assumptions and unresolved limitations are visible.
