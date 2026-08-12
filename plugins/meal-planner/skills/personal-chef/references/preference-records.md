# Preference and recipe records

Use a workbook or Google Sheet titled `Meal Preferences` or a clearly equivalent title such as `Recipe Preferences` or `Family Meal Preferences`. When creating a new workbook, use `Meal Preferences`. Reuse an accessible equivalent workbook instead of creating a competing copy.

Use two canonical tabs: `Household Preferences` and `Recipe History`. Accept clearly equivalent existing tab names and columns without forcing a migration. Treat the exact workbook title, link or file identity, and tab names as source provenance; do not copy the records into skill-local files.

## Household Preferences

| Field | Purpose |
| --- | --- |
| Household member | Person or “household” |
| Category | Ingredient, cuisine, flavor, texture, technique, equipment, budget, or other |
| Item | Normalized preference subject |
| Preference | Love, like, neutral, limit, dislike, or exclude |
| Strength | Optional 1–5 confidence or intensity |
| Context | Weeknight, seasonal, preparation-specific, and similar qualifiers |
| Reason or notes | User explanation in concise form |
| Status | Current or superseded |
| Source | Direct statement, repeated behavior, or confirmed interpretation |
| Updated date | ISO date |

Use `exclude` only for a user-confirmed culinary exclusion. Keep allergy and medical rules in the safety record owned by `meal-planner` unless the user explicitly requests otherwise.

## Recipe History

| Field | Purpose |
| --- | --- |
| Recipe name | Recognizable title |
| Source URL | Direct original recipe link, if any |
| Date made | ISO date |
| Household member | Individual or household rating |
| Rating | 1–5, if supplied |
| Would make again | Yes, no, or conditional |
| What worked | Flavor, texture, ease, leftovers, and similar notes |
| What to change | Specific actionable modification |
| Modification tried | What differed from the source |
| Prep difficulty | User assessment |
| Leftovers quality | User assessment |
| Tags | Cuisine, protein, season, method, or occasion |
| Updated date | ISO date |

Interpret ratings with notes rather than mechanically. Treat “would make again” and specific explanations as more informative than the number when they conflict.

## Update rules

1. Match existing recipes by normalized title plus source URL when possible.
2. Append a new experience row when the same recipe is cooked again; do not erase the older outcome.
3. Update a stable preference only after direct confirmation. Mark the previous row superseded when its meaning changed.
4. Attribute individual reactions to the correct household member.
5. Preserve blanks rather than inventing ratings, dates, reasons, or modifications.
6. Summarize every completed write and surface unresolved duplicates.
