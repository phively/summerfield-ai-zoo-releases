# Shopping records

Read this reference with [record management](contracts/record-management.md) before resolving, saving, or maintaining category shopping context. The Personal Shopper owns these records. Installing the plugin creates no workbook or worksheet.

## Resolve existing records first

Resolve the user's selected canonical workbook through runtime context and its native identity. Do not identify an authority by title or a similar-looking workbook alone. In the workbook, use `Record Index` when present to map record roles, worksheets or tables, stable key columns, owners, and retrieval conditions. Confirm that routing against native tables or named ranges and the actual headers before reading or writing.

When no index exists, discover the relevant native tables or ranges and map their roles from their actual headers, values, and references. Accept equivalent role names such as `Price History` for price evidence, `Shopper Preferences` for current preferences, and `Change History` for material prior state when native metadata and headers support that mapping. Read fields by header and the mapped key column wherever it appears; the key column is not assumed to be column A. Do not require an ingredient catalog, a category column in an existing grocery table, or a new `Record Index` in a compatible legacy workbook.

A missing lookup does not prove that the authority is absent. Bound discovery to relevant native metadata, tables, ranges, and headers; resolve ambiguous candidates before relying on them. Keep the workbook identity, compatible tabs, existing keys, column order, formulas, validations, links, and useful history. Do not rename, convert, replace, duplicate, or restructure a compatible workbook to match these defaults.

## New-record layouts

These layouts apply only to newly authorized records. Create only worksheets relevant to the current task, in the selected compatible workbook, after confirming the route can perform the required native operation. New general context must not duplicate grocery facts into a second authority.

| Record role | New worksheet default | Fields in addition to provenance | Compatibility rule |
| --- | --- | --- | --- |
| Routing | `Record Index` | Existing nine-column schema: `Record Type`, `Worksheet`, `Table or Named Range`, `Stable Key Column`, `Role`, `Owner`, `Last Audited`, `Row Count at Audit`, `Retrieval Condition` | Optional for a compatible existing workbook; map declared roles and keys when present |
| Category rules and product-class preferences | `Shopping Rules` | `Record ID`, scope (`general` or category), category, rule type, rule/value, classification as hard constraint or preference | Only explicitly general rules apply across categories; category rules remain scoped |
| Ordered stores | `Store Preferences` | `Record ID`, scope/category, region, priority, store, preferred website | A legacy five-column table remains unchanged; absent scope means groceries |
| Existing equipment and fit | `Owned Equipment` | `Record ID`, category, model/specification, confirmed measured dimension and unit, interface or placement, confirmation state | Save useful confirmed setup only; unknown measurements remain unknown |
| Discount eligibility | `Discount Eligibility` | `Record ID`, eligibility type/value, scope, confirmation state, validity conditions and dates | Save only relevant authorized traits; never save account secrets or infer membership |
| Observed prices | `Price Tracker` | `Record ID`, category, product/model/specification, store/region, observation date, package quantity/unit, price/currency, offer conditions, source, confidence | A role-mapped equivalent such as `Price History` is valid; observations are dated evidence, not preference authority |
| Material previous state | `Shopping History`; `Store Preferences History` for prior store orders | An `MH-...` or established history key, subject, prior/new state, reason, dates, and current-record pointer | Reuse an existing combined history such as `Change History`; do not duplicate price observations |

Current and evidence records also retain source, attribution when relevant, confirmation state, effective or observation date, and unresolved uncertainty. Product and category fields determine applicability; record keys identify rows. Equivalent preference/value tables may already hold region, budget, brands, memberships, or shopping objectives and should be used without restructuring when their role and headers are clear.

For stores, preserve an existing five-column grocery list and its order exactly; a missing scope or category in that legacy table means groceries. Do not add columns to it to represent other categories. If a newly authorized category-specific store record needs the expanded fields and no compatible table exists, add a separate task-relevant role-mapped table in the same canonical workbook, using the new layout and a non-conflicting worksheet name such as `Store Preferences - Shopper`. Do not create another workbook.

## Apply records to a task

Apply current task instructions first, then relevant saved category preferences, then explicitly general preferences. A saved preference never overrides a hard product constraint. Apply a legacy grocery store order only to grocery work; for other categories use only a task instruction or a saved preference with matching category and region.

Use existing Shopping Rules, Discount Eligibility, or equivalent preference roles for confirmed service-category preferences when their actual headers support that scope. Keep a contractor or subscription rule within its service category; never insert contractor rankings into legacy grocery store order or add grocery columns for service research. A project estimate and its comparable-outcome data remain in the task response unless a useful durable record update is separately requested. Apply task-only service corrections without saving; authorized saves retain the same native identity, stable keys, history requirements, and per-target verification as product or grocery records.

Use confirmed equipment, dimensions, interfaces, and placement when evaluating fit. Leave missing measurements unknown and explain when they could change compatibility. A task correction can guide the current recommendation immediately, but update saved equipment only when persistence is authorized and the corrected fact is confirmed.

Prefer dated prices that match the product or model, package, region, and store. Keep the observed date, source, currency, package or model, offer conditions, and confidence attached to the evidence. Distinguish verified regular prices from membership or other conditional offers. Apply a discount only when eligibility is confirmed for the applicable period; an unconfirmed offer stays conditional and does not establish a saved membership fact.

## Authorize and verify changes

Persist only useful facts the user has confirmed and authorized for the intended scope. Current-task corrections, one-time store orders, provisional measurements, and unconfirmed eligibility remain task-only unless the user authorizes a durable update. Before writing, resolve the exact workbook, record role, mapped key, affected fields, source, date, scope, and any required history target.

Check capabilities for the actual provider, account, workbook, and operation: bounded native reads, targeted updates or appends, canonical readback, affected native properties, and complete staging when structural maintenance is proposed. A route that can fetch text but cannot edit and verify the native workbook does not support a save. If access or a required operation is unavailable, continue useful work from reliable supplied evidence, name the unavailable records or capability, and return any proposed updates unsaved. Keep the existing authority; do not substitute a text database, convert silently, or create a competing workbook.

For an authorized update, write only the intended keyed fields and preserve adjacent formulas, validations, links, and unrelated rows. Freshly read back each canonical target and relevant native properties before describing it as verified. If an update includes material history, preflight that target too; if the current row verifies but required history does not, report only the verified target and mark the combined change incomplete. If an append acknowledgement is uncertain, look up its stable key and verify the canonical row before retrying. Do not claim cross-resource atomicity or rollback.

Structural cleanup or migration requires the complete staged audit in [record management](contracts/record-management.md) and [cleanup and migration](contracts/cleanup-migration.md). A partial before or after snapshot cannot authorize canonical cleanup. R25's live access evidence must come from an activated skill run using a locator supplied at runtime or by private test configuration; fixtures and static checks do not prove provider access. Never put a private workbook locator, resource ID, title, path, account secret, or personal row in repository content.
