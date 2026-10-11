# Canonical meal-plan document template

Use this semantic template when creating or reformatting a canonical meal plan. Read [native artifact storage and formatting](../../../shared/artifact-formatting.md) first. Render these elements with the destination's native features; the Markdown below describes structure and must not be pasted literally into a Google Doc.

## Document structure

1. Document title using the native `Title` paragraph style.
2. A compact metadata table containing plan ID, status, covered dates, last updated, household or serving assumptions, and the exact record identities used.
3. A `Safety and unresolved questions` `Heading 1` followed by short native bullets containing only material constraints, assumptions, or pending checks.
4. A `Weekly plan` `Heading 1` followed by a native table with day, meal, named canonical recipe link, version used, servings, active time, total time, and planned leftovers. A leftover-only row uses a named link to its source dinner or recipe.
5. A `Dinner details` `Heading 1` with one `Heading 2` subsection per dinner. Use `Normal text` labeled paragraphs or a small native metadata table for timing and servings, a native bulleted ingredient list, a native numbered instruction list, and short native bulleted adaptations, prep-ahead, storage, and leftover notes.
6. A `Grocery and cost summary` `Heading 1` with native section headings and lists or tables appropriate to the finalized shopper handoff.
7. `Batch prep`, `Leftover plan`, and `Sources` `Heading 1` sections when their content is useful. Sources use descriptive named links and keep canonical recipe links distinct from original-source links.

Use native `Title`, `Heading 1`, `Heading 2`, and `Normal text` paragraph styles for the corresponding elements. Bold, larger, or indented text does not satisfy a required paragraph style. Read back the title, headings, lists, tables, and links and repair mismatches before reporting a newly persisted Google Doc meal plan as complete.

Keep the current plan operationally complete without history. Do not copy complete recipes or preference tables into it when stable named links and bounded context are sufficient.
