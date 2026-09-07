# Cleanup and schema migration

Read before cleaning up household documents, changing rating schemas, migrating recipes into Docs, or restructuring workbook records. This procedure supplements [record-management.md](record-management.md) and is stricter than the generic disposable-item audit: no populated source data row may be removed or silently merged. Changes may update or add rows, and preserve historical rows with explicit status and traceable identity.

## Scope and recovery

1. Resolve the user's designated Meal Planning folder, Recipes folder, current workbook and document IDs, and native schemas. Stay inside the planning folder; canonical recipe Docs stay in Recipes. Similar titles in backup folders do not establish current authority.
2. Create a new `Migration audit YYYY-MM-DD` subfolder inside Meal Planning using the user's local date; append the local time if that name already exists. Keep backups, staging workbooks, snapshots, hashes, row mappings, and the final report there. Existing audit folders remain historical.
3. Preserve native copies of affected files before content writes. Export complete before snapshots including hidden populated rows, stable keys, values, formulas, validation, named ranges, tables, relevant references, and document structure. Use bounded reads and assemble the complete snapshot. Stop a dependent write if extraction is incomplete.
4. Work on staged workbook copies, then validate before editing the original authorities in place. Re-read original values before applying the approved edits; stop on concurrent changes. Keep provider IDs, folder placement, and sharing unchanged.

## Ratings and recipe cleanup

- Replace active Preference and Strength with one numeric Rating: 1 through 5 in steps of 0.5. Preserve existing valid numeric liking ratings and their precision when surrounding evidence establishes their meaning. Otherwise propose Love=5, Like=4, Neutral=3, Dislike=2; obtain clarification for confidence scores, conflicting meanings, Limit, Exclude, or invalid values. Keep uncertain ratings blank with a visible unresolved status and preserve the exact legacy values in the audit. Never average, round, or infer a household aggregate.
- Preserve dates, source text, attribution, context, and constraints. Separating an exclusion from a rating must not weaken the exclusion. Keep hard constraints with the planner and culinary ratings with the chef.
- Register existing recipe Docs before creating missing ones. Keep proposed and incomplete recipes explicitly labeled. Move current recipe instructions and reusable modifications from cells into canonical Docs; replace those cells with version/section pointers only after Doc readback proves preservation. Retain outcome evidence in ratings/history.
- Add missing stable IDs without replacing existing IDs. Keep every data row, including superseded experiences and apparent duplicates. Use statuses and links to clarify authority. Add rows only for justified missing records or genuinely distinct context.
- Extend native table and named-range coverage to include every populated row/column. Update workbook guidance and Record Index to explain current roles, numeric ratings, recipe pointers, and the retrospective.
- Add verified recipe links to the existing current plan's table without changing its covered dates, approval status, meal choices, or historical version claims. Preserve old plan history. Missing recipe details remain visible; cleanup is not approval of a new recipe or new plan.

## Required validation

Set `preserve_data_rows: true` in the audit ledger. Run `../scripts/validate_workbook_audit.py` with complete before/after snapshots and a bidirectional ledger. Each populated source row must map to at least one distinct surviving data row; prohibit many-to-one collapse and the `removed` disposition for data rows. A matching total row count alone is insufficient. Map every addition to its reason and every changed field to preserved source evidence or an authorized update.

Check exact stable IDs, protected values, formulas, validations, source links, recipe Doc identity/contents, and native table coverage. Include every original tab, even when unchanged. Re-read all changed ranges after writing, compare against the validated staged state, and verify every original row's identity and unchanged fields. Record successful writes, counts, pending questions, and failed checks in the audit. Preserve backups until verification succeeds; never claim a complete cleanup after a partial write.
