# Native spreadsheet storage and formatting

Read this reference before creating or formatting a canonical shopping workbook, or proposing a file-type or provider migration. Preserve the existing authority, provider identity, sharing, and compatible structure unless the user authorizes a change.

## Storage preference

Use the user's accessible native cloud spreadsheet for canonical structured shopping records: Google Sheets, or a supported business Excel workbook in OneDrive or SharePoint through an available native access route. Reuse a compatible existing workbook and its location. For a new Google Sheet, use the user's selected Drive location; do not require a Meal Planning folder or create a competing workbook. Resolve the provider, account, workbook, and supported operations before relying on them. Check native read, targeted update or append, canonical readback, native-property readback, and complete staging separately for the requested operation. Excel text export is not native workbook editing.

If the workbook is unavailable, the route is read-only, or a required native operation is unsupported, continue useful work from reliable supplied or readable evidence, report the specific limitation, and leave proposed changes unsaved. Keep the current authority. Do not create a Markdown or text database, silently convert formats, or create a competing workbook as a fallback.

## Native structure

- Use real cells, header formatting, native tables or filters when supported, named ranges, data validation, wrapping, and suitable column widths.
- Keep stable keys, formulas, validations, links, hidden populated rows, and unrelated columns intact.
- For a narrow update, change only the authorized keyed fields and preserve adjacent formulas, validations, links, and unrelated rows. Do not infer write support from successful reads or text extraction.
- Use the provider's native hyperlink representation for visible workbook links. Keep immutable resource IDs and raw URLs only in fields intended for identity or source provenance.
- Read back consequential content and inspect its native structure after writing. Correct cell values do not establish that required tables, formulas, filters, validation, or links were preserved.

## Format-aware completion check

Before creating a workbook or changing its structure, identify the applicable record schema and required fields. After writing:

1. Read back the content, native structure, applicable properties, and user-visible links using the strongest available native representation.
2. Compare affected headers, ranges, tables or filters, wrapping, widths, validation, formulas, stable keys, and links with the accepted structure.
3. Repair mismatches only within the authorized scope, then read the affected elements again.
4. Mark native formatting and persistence verified only when the required checks pass. If the provider exposes values but not the relevant structure or source persistence, report that part as unverified.

Do not update dependent pointers or claim a completed record until required content, native structure, and links are freshly verified in the canonical source. Report each target by its observed verification state; when a required companion target is unverified, the combined change remains incomplete. Preserve workbook identity and use the same target when resolving a failed check.

## Links and migration

Every user-visible link must have concise descriptive display text and resolve to the intended target. Do not present a bare URL or raw HTML as the visible link. A pending or inaccessible target stays labeled unresolved.

Treat provider or file-type conversion as a proposed migration. Obtain explicit user permission before creating a replacement as a migration, transferring canonical authority, retiring the original, or changing dependent links. Preserve the original or an equally recoverable native revision, stage the replacement, validate content and native structure, and recheck the source for concurrent changes before any authorized cutover. Leave the existing authority unchanged when permission is absent or validation fails.
