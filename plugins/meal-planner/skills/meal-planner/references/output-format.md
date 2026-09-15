# Meal-plan output format

Scale detail to the request. For a full printable weekly plan, use the structure below. For brainstorming, revisions, or short plans, include only the relevant sections.

This reference governs conversational output. When persisting or reformatting a canonical plan, also read [the canonical meal-plan document template](meal-plan-document-template.md) and [native artifact storage and formatting](../../../shared/artifact-formatting.md). Render Google Docs with native headings, lists, tables, and descriptive hyperlinks; do not paste this Markdown structure into the document.

## Assumptions and safety notes

List only assumptions or warnings that materially affect the plan.

## Weekly overview

Use a compact table with day, meal, canonical recipe link, servings, active time, total time, planned leftovers, and new or returning status. In the persisted current plan, use a native table and give every recipe a descriptive link to its verified canonical Google Doc; leftover-only meals use a named link to the source dinner. Preserve the approved recipe version in plan metadata. For drafts, label an unpublished recipe link pending rather than inventing a URL. Use native Google resource links or supported smart chips when available, and never show a bare URL or raw HTML as link text.

## Dinner cards

For each dinner, include:

- Recipe name
- Descriptive verified canonical Google Doc link and approved version, distinct from the original source attribution
- Servings
- Prep, cook, active, and total time
- Protein, vegetables, and starch or approved alternative
- One concise selection rationale
- Ingredients with usable quantities
- No more than seven clear instruction steps
- Prep-ahead actions
- Leftover and storage strategy
- Freezer notes when useful
- Approximate calories, protein, fiber, carbohydrates, and fat per serving when requested or reliably calculable
- Original recipe title, author, website, and descriptive verified link when externally sourced
- Material modifications and reasons

Avoid repeating full instructions for a planned leftover night. Refer back to the source dinner and provide reheating or transformation directions.

## Weekly summary

### Grocery list

Use the validated `personal-shopper` handoff when available. Combine duplicate ingredients and group them under:

- Produce
- Meat
- Seafood
- Dairy or alternatives
- Pantry
- Frozen
- Bakery
- Miscellaneous

Distinguish `buy` from `check pantry`. Show required quantity, purchase quantity or packages, estimated purchase price or range, meals using the item, and material notes. Do not fabricate store prices or package sizes.

### Cost estimate

State the price region, store or estimate basis, date, currency, discounts, exclusions, and confidence. Report estimated checkout spending separately from pantry contribution and unpriced items. Provide estimated cost by meal and per serving without double-counting shared ingredients; label partial totals and likely package surplus.

### Batch prep

Order tasks for efficiency and identify storage duration or container needs when relevant.

### Leftover plan

Map each source meal to its reuse or freezer destination.

### Variety summary

Summarize proteins, cuisines, cooking methods, new recipes, and returning favorites. Note any requested variety rule that could not be met.

### Evidence and sources

Provide descriptive, verified links near health claims and a concise source list for nutrition guidance, seasonal-produce guidance, and original recipe pages actually used. Do not display bare URLs or pad the section with sources that did not affect the plan.
