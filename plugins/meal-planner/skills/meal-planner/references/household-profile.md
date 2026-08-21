# Household and safety intake

Collect only information relevant to the request. Prefer one focused checkpoint over a long questionnaire.

## Workbook and canonical tabs

Use a workbook or Google Sheet titled `Household Preferences` or a clearly equivalent title such as `Household Profile` or `Family Preferences`. When creating a new workbook, use `Household Preferences`. Reuse an accessible equivalent workbook instead of creating a competing copy.

For a new workbook, also create the workbook-local `Record Index` defined in shared record management. For an existing workbook, use its native table, named range, or stable-key metadata and add the routing worksheet only with authorization when it materially improves retrieval or auditability.

Use these canonical tabs, accepting clearly equivalent existing tab names without forcing a migration:

- `Household Profile`: household members, age groups, serving multipliers, region, and stable household context.
- `Safety Constraints`: allergies, affected people, severity, cross-contact sensitivity, medical restrictions, intolerances, confirmed limits, source, and updated date.
- `Planning Preferences`: standard servings, equipment, active and total time limits, leftover targets, shopping frequency, budget tier, and recurring schedule constraints.
- `Pantry Inventory`: item, quantity, unit, status, location, and updated date when the user maintains pantry data in this workbook.
- `Household History`: material superseded or restored household, safety, and planning state with continuing provenance, audit, or restoration value. Do not use it for routine pantry churn.

Treat exact workbook title, link or file identity, and tab names as part of source provenance. Report missing canonical tabs; create or rename tabs only with authorization, and do not copy their contents into skill-local files.

Use a `Record ID` column as the stable row key for new records. Prefer structured tables or named ranges named for their canonical worksheets. Preserve a clearly equivalent existing unique key, but document it in `Record Index` instead of identifying rows by position. Use these logical uniqueness rules to detect accidental duplicates:

- `Household Profile`: household member identity;
- `Safety Constraints`: affected member, constraint type, normalized constraint, and material context;
- `Planning Preferences`: preference category and material context;
- `Pantry Inventory`: normalized item and storage location; and
- `Household History`: stable `MH-...` history ID.

Keep source, updated date, status or uncertainty, and relevant history pointer columns with the owning row when applicable. A pointer must target the workbook resource ID, worksheet, stable record ID, and retrieval condition.

Read [the shared record-management contract](../../../shared/record-management.md) before changing household state, retrieving history, following a pointer, or resolving duplicates or partial writes. Current tabs govern over history. Read only a targeted historical entry when a defined retrieval condition applies.

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
