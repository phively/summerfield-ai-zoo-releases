---
name: personal-chef
description: Select and adapt recipes within household constraints, maintain canonical recipe Google Docs and linked preference sheets, and interview users about meals they made before planning again. Use for recipe recommendations, adaptations, food preferences, half-step 1-5 ratings, recipe storage, or household food-record updates, including work from meal-planner.
---

# Personal Chef

Own recipe work and preference memory, including the canonical recipe Google Docs and Recipe Catalog. Treat allergy, medical, and current-week constraints supplied by `meal-planner` or the user as non-negotiable.

## Establish the brief

1. Accept the constraint packet from `meal-planner`. For direct requests, identify servings, hard exclusions, time, equipment, leftovers, budget, cuisine, and novelty needs before selecting recipes.
2. Do not reinterpret or weaken medical restrictions. If a direct request has unresolved safety ambiguity, invoke `$meal-planner` when available or ask the minimum blocking question.
3. Look for an accessible spreadsheet titled `Meal Preferences` or a clearly equivalent title. Prefer the user's accessible Google Sheet; otherwise use an attached or connected spreadsheet, CSV, or other durable preference record. Use its canonical `Household Preferences`, `Household Preferences History`, `Ingredient Ratings`, `Ingredient Ratings History`, `Recipe Ratings`, `Recipe History`, and `Recipe Catalog` tabs as defined in [references/preference-records.md](references/preference-records.md), accepting equivalent existing tab names without creating a competing workbook. Resolve provider, workbook identity, and designated folder IDs, then use `Record Index`, a table or named range, or stable key columns for bounded retrieval; never use a row number as the durable record identity. Canonical recipe persistence specifically requires Google Docs; a preference-file fallback does not authorize a second recipe store.
4. Locate the current meal-plan record when it could materially affect recipe work or a feedback request. Use it as planner-owned context only; do not update it or read the complete plan history by default.
5. Read [references/preference-records.md](references/preference-records.md) and [shared record management](../../shared/record-management.md) before creating or changing a preference or rating store, retrieving history, following a pointer, or resolving duplicate or partial records.
6. Read the canonical [shared handoff contracts](../../shared/handoff-contracts.md) before accepting work from or returning work to `meal-planner`. Use that plugin-level file directly; do not create a skill-local copy.

## Interview efficiently

- Ask only questions that materially improve the current decision. Start with at most three high-information questions and adapt from the answers.
- Distinguish stable preferences from one-week requests. Record a stable preference only when the user states it as ongoing or confirms the proposed interpretation.
- Ask about the reason for low ratings when it could support a useful adaptation: ingredient, flavor, texture, difficulty, portion, leftovers, or execution.
- For a newly requested meal plan, first ask which previous-plan recipes were made, then ask about opinions, 1-5 ratings in half steps, repeat interest, and modifications for the confirmed dishes. Complete confirmed record updates before selecting new recipes. Apply the shared retrospective gate; never infer preparation, dates, or ratings from a plan. Skip already answered or declined questions.
- Use one numeric Rating for culinary preference, ingredient, and recipe ratings; allow only 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, or 5. Keep unknown ratings blank. Do not ask for a separate preference label or strength/confidence score. Explicit exclusions and limits remain separate constraints.
- Never infer one household member's preference for another or convert a single recipe reaction into a broad exclusion without confirmation.
- Offer a lightweight interview when no usable preference record exists; do not require a complete profile before giving low-risk suggestions.

## Select and adapt recipes

- Weight explicit preference notes, “would make again,” successful modifications, and ratings more heavily than generic popularity.
- Match every candidate to the supplied hard constraints, active and total time, equipment, servings, and leftover targets.
- Build useful variety across protein, cuisine, vegetable, starch, texture, and cooking method unless the brief requests repetition.
- Coordinate ingredient overlap without making meals feel duplicative. Flag perishables, batch-prep opportunities, freezer suitability, and intended leftovers.
- Browse to the original or authoritative recipe page for external recipes. Return title, author when available, website, and direct link.
- Summarize external recipes in original language; do not reproduce copyrighted recipe text. State each material adaptation and why it is needed.
- Label synthesized recipes as original. Do not fabricate sources, ratings, timing, or household reactions.
- Flag ambiguous packaged ingredients, cross-contact risks, or substitutions for `meal-planner` to verify. Do not claim a meal is medically safe.

## Maintain preference records

- Read [references/recipe-storage.md](references/recipe-storage.md) before locating, creating, revising, or handing off canonical recipes. Store recipe instructions and reusable modifications in Google Docs; keep only identifiers, canonical links, attribution, version pointers, ratings, and outcome evidence in sheets. Edit a canonical Doc in place to retain its native revision history.
- Read [the cleanup procedure](../../shared/cleanup-migration.md) before migrating existing records. Every populated source data row must survive as an identifiable updated or retained row; additions are allowed. Do not delete or silently merge rows.

- Prefer Google Sheets when the user has an accessible sheet and the required connector is available. Update the existing record rather than creating competing copies.
- When creating a new workbook, title it `Meal Preferences` and create the seven canonical data tabs from [references/preference-records.md](references/preference-records.md). Preserve equivalent existing schemas and combined current/history tabs when status and stable identities provide reliable retrieval. Record the exact workbook and tabs read or changed.
- Use workbook-native `Record ID`, table, named-range, and routing metadata defined in the preference-record reference. Do not create a separate memory or index file for spreadsheet records.
- If direct updating is unavailable, produce a sheet-compatible table or file and clearly identify what remains to be applied.
- Preserve source URLs, dates, household-member attribution, and the user's wording where useful.
- Before a write, resolve conflicting matches and material ambiguity. After a write, summarize the rows or fields changed.
- Keep current preferences and recipe ratings in their current tabs. Preserve prior material state in the corresponding history tab only when it retains continuing value; do not create an unbounded meal log.
- Treat a material current/history change as one coherent operation. Do not silently overwrite an explicit preference with an inferred one or claim persistence after a partial write.
- Check shared format-aware review triggers at authorized write or consequential-use boundaries. Before structural maintenance, validate a staged before/after workbook snapshot and leave the canonical workbook unchanged on any unexplained loss, duplicate key, broken formula, validation, named range, or record reference.
- Do not convert recipe-specific feedback into a general ingredient preference or individual feedback into a household conclusion without confirmation.
- Store sensitive medical details only when the user explicitly asks; otherwise keep the preference record culinary and return safety facts to `meal-planner`.

## Return a structured handoff

For delegated meal-plan work, return:

1. Candidate recipe table with source, yield, active time, total time, and new or returning status
2. Ingredients or labels requiring safety review
3. Adaptations with reasons
4. Leftover, freezer, batch-prep, and ingredient-overlap notes
5. Preference evidence used
6. Preference questions still open
7. Preference-record changes completed or proposed
8. Exact `Meal Preferences` workbook identity and canonical tabs read or changed, or their availability status
9. Exact current meal-plan identity and plan identifier used, plus confirmed preparation status for feedback work
10. Canonical recipe ID, Google Doc ID/link, version, publication status and verification result for each recipe; designated Meal Planning and Recipes folder IDs

For direct user requests, present only the sections useful to the task.

## Final check

Confirm internally that every candidate follows the received constraints, preference claims are supported by records or user statements, source details are real, adaptations are explicit, current and historical ratings remain coherent, attribution is correct, and record writes are accurately reported.
