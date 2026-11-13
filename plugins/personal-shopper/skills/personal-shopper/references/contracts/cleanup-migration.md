# Shopping workbook cleanup and migration

Read before cleaning up, restructuring, compacting, or migrating a canonical shopping workbook. This procedure supplements [record management](record-management.md) and requires every populated source row to remain represented by a distinct surviving row.

## Scope and recovery

1. Resolve the canonical workbook by provider and immutable resource identity, then identify its current and history roles, native schema, keys, formulas, validations, and dependent references. A similar title in another folder does not establish authority.
2. Keep snapshots, hashes, row mappings, and staging copies in a user-authorized recovery location or preserve an equally recoverable native revision. Do not place personal records in the plugin package or create a second canonical workbook.
3. Export a complete before snapshot, including hidden populated rows, values, formulas, validations, tables, named ranges, stable keys, and relevant references. A bounded task read or partial provider export is not a complete snapshot. If extraction is incomplete or a native property cannot be read, stop before cleanup or any dependent write; missing snapshot content does not establish that source data is absent.
4. Stage proposed changes outside the canonical authority and export a complete after snapshot with the same coverage as the before snapshot. Re-read the source before applying an approved in-place change; stop if concurrent changes invalidate the staged state. An incomplete before or after snapshot cannot authorize cleanup.

## Formatting and conversion

During cleanup, compare the workbook with its canonical structure. Useful in-place repairs may include restoring native tables or filters, correcting header formatting, repairing supported validation, and resolving descriptive links. Perform in-place formatting only inside the authorized scope and only when the staged audit proves that content and structure remain preserved.

A change of file type or provider, creation of a replacement for conversion, transfer of canonical authority, retirement of the original, or dependent-link cutover requires explicit user permission after the source, proposed target, affected identities, benefits, and recovery plan are explained. General permission to clean records is not permission to migrate the file type.

For an approved migration, preserve the recoverable original or native revision, validate the staged replacement's content and native structure, recheck the source for concurrent changes, and update dependent pointers only after the audit passes. Without permission or after a failed check, leave the canonical authority and its links unchanged.

## Required validation

Set `preserve_data_rows: true` in the audit ledger. Run [the workbook audit validator](../../scripts/validate_workbook_audit.py) with complete before and after snapshots and a bidirectional ledger. Each populated source row must map to at least one distinct surviving data row; do not remove a data row or merge two source rows into one target. Row counts alone do not prove preservation.

Check stable IDs, protected values, formulas, validations, named ranges, descriptive link targets, and complete table coverage. Include every original sheet, even when unchanged, and map every source item to a retained or justified outcome. Re-read changed ranges and affected native properties after writing and compare them with the accepted staged snapshot. Preserve recoverable state until verification succeeds, and do not claim complete cleanup after a partial write.
