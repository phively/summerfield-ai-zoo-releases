# Personal Shopper record management

Read this reference before locating, creating, updating, archiving, restoring, or handing off durable shopping records. [Handoff contracts](handoff-contracts.md) define ownership and coordination; [shopping records](../shopping-records.md) defines category-scoped layouts and legacy compatibility. This file defines shopping-record identities, targeted retrieval, lifecycle procedures, and failure behavior.

## Record registry

Preserve a clearly equivalent existing authority rather than renaming or copying it. Use these identities only when creating a new shopping record:

| Owner | Current authority | Historical companion | Readers | Writers |
| --- | --- | --- | --- | --- |
| Personal Shopper | `Grocery Preferences` workbook: `Store Preferences` | `Store Preferences History` for material prior orders | Personal Shopper, limited to task-relevant shopping context | `personal-shopper` only |
| Personal Shopper | `Grocery Preferences` workbook: `Price Tracker` | Dated observations in the same tab; do not create a duplicate archive | Personal Shopper, limited to relevant price evidence | `personal-shopper` only |

The owner may create or update a record only when the user authorizes persistence or an existing confirmed workflow already authorizes that bounded write. Do not create per-task authorities, skill-local copies, or parallel workbooks.

## Storage and native format

Use an accessible native cloud spreadsheet as the canonical structured shopping store: Google Sheets, or a supported business Excel workbook in OneDrive or SharePoint through an available native access route. Prefer the user's accessible Google Drive for a new Google Sheet and use the user's selected location; no Meal Planning folder is required. Reuse a compatible existing authority in place. Resolve the actual provider, account, workbook, and capability for each operation before relying on it: bounded native reads, targeted updates or appends, canonical readback, native-property readback, and complete staging are separate capabilities. A text export is not native Excel editing.

Do not create a Markdown or text database, export, or second workbook as a competing authority. If the available route cannot read or persist the canonical workbook in its native format, continue with supported read-only work, report the limitation, and leave proposed updates unsaved. Read [native artifact formatting](artifact-formatting.md) before creating or formatting a workbook, and [cleanup and migration](cleanup-migration.md) before structural maintenance or conversion.

## Native identities and routing

Identify a workbook by its resolved provider and immutable resource ID or canonical file identity; use a visible title only as descriptive metadata. Identify each record by its mapped role, worksheet, table or named range when present, actual headers, stable key column wherever it appears, and relevant fields. A worksheet title or row number alone is not a durable identity. Preserve equivalent existing schemas; add, rename, or restructure workbook elements only with authorization.

Use workbook-native routing. For a new workbook, include a `Record Index` worksheet with one row per canonical worksheet or table and the fields `Record Type`, `Worksheet`, `Table or Named Range`, `Stable Key Column`, `Role`, `Owner`, `Last Audited`, `Row Count at Audit`, and `Retrieval Condition`. Store routing metadata only; do not duplicate shopping facts or observations there. For an existing workbook, treat its index as optional and confirm declared roles and keys against native tables or ranges and actual headers.

For an existing workbook, first use `Record Index` when present, then native tables, named ranges, stable keys, filters, metadata, and actual headers to resolve roles and keys. Accept equivalent worksheet and table names when their native mapping and headers support the role; do not require an ingredient catalog, a category column in a legacy grocery table, or a key in column A. Preserve existing keys and column order. Add `Record Index` only with authorization and when it materially improves targeted retrieval or auditability. If a stable key cannot be resolved for a proposed write, leave it unsaved rather than adding a key or restructuring the legacy table. Do not create a Markdown or other sidecar index because native routing is unfamiliar.

## Authority and retrieval

- Optimize in strict order: complete relevant recall, fewer cells loaded and updated, then retrieval speed. Never weaken recall to improve a lower-ranked objective.
- Read the applicable current authority first. Current store preferences govern over history; dated price observations are evidence, not current preference authority.
- Read only relevant current rows or targeted history, and bound the actual scanned cells rather than only the number of returned results. Retrieve history when the current record points to it, the user asks about prior state, provenance is needed to resolve a conflict, or restoration is being considered.
- A missing lookup does not prove that the authority, record, or history is absent. Resolve ambiguous candidates before relying on them or proposing a new authority.
- Preserve exact product constraints, units, prices, dates, source identities, attribution, confirmation status, and unresolved uncertainty.
- Current task instructions govern before saved category preferences and explicitly general preferences; hard product constraints remain controlling. Do not replace persistent state without authorization for that target.

## Store and price records

Keep the current ordered store list in `Store Preferences`, resolving the role through native metadata and actual headers. A legacy list without scope is grocery-specific. Preserve its prior order in `Store Preferences History` or an existing role-equivalent history only when its rationale or restoration value remains material. Record its stable history identity, prior and replacement order, region or context, reason, source, dates, and status. Use the scoped layout in [shopping records](../shopping-records.md) only for newly authorized category or general records.

Keep dated product and package observations in `Price Tracker`; do not duplicate them in another archive. Select applicable evidence by store, location, product match, date, package, sale or membership status, and confidence. Give each observation a stable `Record ID`; use store, location, normalized product, observed date, package identity, and sale or membership status to identify an observation logically.

## Coherent updates

Treat a material current-state change as one bounded operation:

1. Resolve the canonical workbook, current and history identities, owner, and affected keys.
2. Confirm the requested fields, source, attribution, effective date, and exact persistence authorization.
3. Preserve prior state only when it has continuing rationale, audit, or restoration value.
4. Preflight each required current and history destination and the native verification available for each target.
5. Apply only authorized fields, then freshly read back the canonical rows and affected native properties.
6. Confirm every required target and pointer, and report the state of each separately.

An update requiring a current row and a material history companion is incomplete if either write or its verification fails. Report each exact target by its observed state; a verified current row does not verify a failed history write. After an uncertain append, resolve its stable key and freshly read the canonical row before retrying. Do not claim cross-resource atomicity or rollback.

During cleanup, retain or update every populated source row; do not remove or silently merge records. Preserve original identities and resolve conflicts through explicit status and pointers.

## Format-aware review triggers

Check inexpensive workbook metadata during an authorized write, explicit audit, or consequential use. Make an audit due when any of these conditions applies:

- `Last Audited` is missing or more than 180 days old;
- a current worksheet or table exceeds 500 data rows;
- a history or `Price Tracker` worksheet exceeds 2,000 data rows;
- a worksheet has grown by at least 25 percent since `Row Count at Audit`;
- duplicate stable keys, broken formulas, invalid named ranges, missing required columns or validations, unresolved authority conflicts, or broken record references are detected; or
- cleanup, compaction, schema migration, provider conversion, or authority transfer is proposed.

These are conservative review triggers, not reasons to delete or restructure records. Do not load every row merely to inspect row counts, schema metadata, or the recorded audit date. If review is due but no write is authorized, report it and continue read-only when reliable.

## Staged workbook audits

Treat structural maintenance as a fail-closed transaction. Read [the workbook audit snapshot and ledger schema](workbook-audit-schema.md) before exporting or validating a staged workbook. An incomplete before or after snapshot cannot authorize cleanup; bounded reads for ordinary use are not a complete maintenance audit.

1. Resolve workbook identity, owner, roles, native tables or named ranges, stable keys, and external dependencies.
2. Preserve a recoverable workbook copy or native revision and export a complete before snapshot, including roles, columns, tables, named ranges, stable IDs, values, formulas, validations, and references.
3. Stage proposed changes outside the canonical authority and export the same complete after snapshot.
4. Create a bidirectional ledger mapping every original item to a retained, moved, reworded, updated, archived, or justified disposable removal, and every after item to its origin or an authorized addition.
5. Preserve stable keys, protected values, formulas, validations, provenance, dates, source identities, and uncertainty. Require explicit authorization for factual or schema updates, formula review for changed formulas, and semantic review for rewording.
6. Run `../../scripts/validate_workbook_audit.py` against both snapshots and the ledger. Inspect the provider's native diff or revision history when available.
7. Replace the canonical workbook only after hashes, complete item coverage, uniqueness, formulas, validations, named ranges, references, ownership, and semantic review pass. Verify the written workbook against the accepted after snapshot and retain the recovery copy until verification succeeds.

On unexplained omission, duplicate key, changed protected value, broken formula or reference, ambiguous authority, inaccessible dependency, or partial write, leave the canonical workbook unchanged and report the failed check. Snapshot hashes prove serialized snapshot integrity; they do not prove complete connector extraction or semantic equivalence.

## Failure behavior

- Missing or inaccessible workbook, record, history, or pointer: do not claim it was read or updated; preserve uncertainty.
- Duplicate or ambiguous candidates: resolve the authority before substantive use or writing when the choice could affect the result.
- Partial access, writability, or native readback: do not claim a coherent update. Identify the failed target and recovery action.
- Unsupported format or provider route: keep the existing authority and report unsaved proposed changes. Do not silently convert, transfer authority, or change dependent links.
- Unconfirmed preference, membership, price, source, or lifecycle state: label it proposed or unknown and do not persist it as fact.

## Coherence validation

After a consequential update, verify that current records contain the operational state, history cannot silently override current state, stable identifiers and pointers resolve, user-visible links have verified targets, native structure matches the applicable schema, attribution and dates remain explicit, and no persistence claim exceeds the writes and readbacks that succeeded.
