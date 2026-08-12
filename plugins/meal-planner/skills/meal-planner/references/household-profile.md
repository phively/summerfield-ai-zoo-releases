# Household and safety intake

Collect only information relevant to the request. Prefer one focused checkpoint over a long questionnaire.

## Workbook and canonical tabs

Use a workbook or Google Sheet titled `Household Preferences` or a clearly equivalent title such as `Household Profile` or `Family Preferences`. When creating a new workbook, use `Household Preferences`. Reuse an accessible equivalent workbook instead of creating a competing copy.

Use these canonical tabs, accepting clearly equivalent existing tab names without forcing a migration:

- `Household Profile`: household members, age groups, serving multipliers, region, and stable household context.
- `Safety Constraints`: allergies, affected people, severity, cross-contact sensitivity, medical restrictions, intolerances, confirmed limits, source, and updated date.
- `Planning Preferences`: standard servings, equipment, active and total time limits, leftover targets, shopping frequency, budget tier, and recurring schedule constraints.
- `Pantry Inventory`: item, quantity, unit, status, location, and updated date when the user maintains pantry data in this workbook.

Treat exact workbook title, link or file identity, and tab names as part of source provenance. Report missing canonical tabs; create or rename tabs only with authorization, and do not copy their contents into skill-local files.

## Household and safety fields

- Region or ZIP code when seasonality matters
- Household member name or label
- Age group and serving multiplier
- Allergy, affected person, severity, cross-contact sensitivity, and emergency-relevant notes supplied by the user
- Medical restriction, affected person, source of the restriction, and confirmed food limits
- Intolerance and acceptable quantity, if known
- Pregnancy, age, immune status, or other food-safety consideration only when volunteered or directly relevant

Do not infer medical restrictions from a dietary-pattern label. If a label has multiple interpretations, confirm only the ambiguity that affects safety or the plan.

## Planning fields

- Dates and meals requested
- Maximum active and total time
- Available equipment and desired complexity
- Servings and leftover targets
- Shopping frequency, store, and budget tier
- Pantry records and schedule constraints

## Source inventory checkpoint

Report available sources in a compact list or table:

| Source | Available | Last updated | Use for this plan | Notes or conflicts |
| --- | --- | --- | --- | --- |

Include only sources that exist or that the user identifies. Distinguish a found file from a file that is merely mentioned, inaccessible, or not yet supplied. Ask once whether allergies, medical restrictions, household membership, weekly needs, or preference records have changed since the visible update date.

When records conflict, use:

1. Current user instruction
2. Explicit authoritative-file designation
3. Safety-specific record
4. Most recently dated record
5. More specific record

Always surface safety-relevant conflicts. Send preference ambiguities to `personal-chef` unless they block safe planning.
