# Store preference workflow

Use this workflow to resolve, persist, apply, update, or remove store preferences without changing unrelated grocery-tracker data.

## Preference scope

Store orders in this reference are grocery-specific. Treat a legacy store-preference list with no category or scope field as groceries only; it is not a general shopping default. Apply an order the user explicitly gives for a current task only to the product category they specified. For a non-grocery request such as clothing or equipment, use only an applicable task instruction or relevant saved category preference, and do not infer one from the grocery order.

## Workbook and canonical tabs

Resolve the canonical workbook from its native provider and immutable identity; a familiar title such as `Grocery Preferences`, `Grocery Price Tracker`, or `Shopping Preferences` is descriptive metadata, not proof of identity. When creating a new workbook and the user's Google Drive is accessible, prefer a Google Sheet in the user's selected location. Reuse an accessible compatible workbook instead of creating a competing copy. Read [native artifact storage and formatting](contracts/artifact-formatting.md) before creating or formatting it, and [shopping records](shopping-records.md) for category scope and legacy-schema rules.

Resolve these record roles through the workbook's `Record Index` when present, then confirm them with native tables or ranges and actual headers. Accept equivalent worksheet or table names when their native mapping supports the role; do not force a migration to these default names:

- `Store Preferences`: the ordered stores and preferred websites defined below.
- `Store Preferences History`: material prior store orders with continuing rationale, audit, or restoration value.
- `Price Tracker`: observed product, store, location, date, package, price, sale or membership status, and source details used for future estimates.

Use the resolved workbook identity, mapped worksheet/table, key, and relevant columns as source provenance. A missing default tab name does not mean the authority or role is absent. Add or rename tabs only with authorization and when needed for a new task-relevant record; do not copy records into skill-local files.

For a new workbook, also create the workbook-local `Record Index` defined in shared record management. Prefer structured tables or named ranges for each new worksheet, with formatted headers, suitable wrapping and widths, filters, stable keys, and applicable validation. The Markdown structures in this reference describe schemas; never paste them as literal Markdown into a worksheet. Read back each created or changed range and verify the applicable headers, wrapping or widths, filters or tables, validations, named links, and stable-key structure before reporting the write complete. Use `Record ID` for new current and evidence rows and `MH-...` for new history rows. Preserve existing equivalent keys wherever located in legacy tables; never use row position as identity.

Read [the shared record-management contract](contracts/record-management.md) before creating, revising, archiving, restoring, or resolving these records. Current `Store Preferences` govern over history. Treat dated `Price Tracker` rows as evidence observations and do not duplicate them into a separate archive.

## Resolve the effective order

1. For grocery work, use an ordered store list explicitly supplied for the current grocery request or in the approved `meal-planner` packet. Treat it as task-specific unless the user also asks or consents to save it.
2. Otherwise, read the saved active grocery order from the accessible spreadsheet by its mapped role and key. Apply other saved store orders only when their category and region match the current request.
3. If neither is available, ask one focused question for an ordered list. Accept a store name and an optional preferred website URL for each entry. In the same question, ask whether the list may be saved in the grocery price tracker.
4. If the user declines to name stores, use ordinary local-source fallbacks. If the user supplies a list but declines storage, use it for the current task only.
5. Never claim that preferences were loaded or saved when the tracker is unavailable or a write did not succeed.

Current explicit grocery-store instructions override the saved grocery order for that task. Do not silently replace the saved list when a one-time order differs from it.

## Persist with consent

- Require the user's explicit consent before the first save or before replacing a saved grocery list. A delegated handoff counts only when it states that the user consented. An explicit request to update, reorder, or remove saved preferences authorizes that requested change.
- Keep the legacy grocery preference table in its existing role and workbook with the `Price Tracker` role. Do not create a separate preference file or claim cross-task persistence when that workbook is unavailable.
- Reuse an existing clearly designated compatible preference area when present. Otherwise, after consent, add a worksheet named `Store Preferences` using the scoped new-record layout in [shopping records](shopping-records.md); do not add columns to the price table or alter its rows, formulas, formatting, named ranges, or schema.
- If `Store Preferences` already contains unrelated data, preserve it and use a new worksheet named `Store Preferences - Shopper`. Never overwrite or repurpose ambiguous content.
- Preserve an existing legacy five-column grocery layout in this order: `Record ID`, `Priority`, `Store`, `Preferred Website`, `Updated At`. Keep one store per row, positive unique priorities in ascending order, blank website cells when none were supplied, and a visible timestamp for successful changes. Its missing scope means groceries. Do not add a category column or repurpose this list for other categories.
- For newly authorized non-grocery or explicitly general store preferences, use the expanded scoped layout in [shopping records](shopping-records.md). If the existing grocery table cannot represent that scope, create only a task-relevant separate table or `Store Preferences - Shopper` worksheet in the same canonical workbook; preserve the legacy rows and schema.
- Treat normalized store plus scope, region, and material context as the logical uniqueness rule for new scoped records.
- On update, touch only the designated preference rows and renumber priorities as needed. On removal, delete or clear only the requested store row, then close the priority gap. Preserve spreadsheet revision history when the connected tool provides it.
- Preserve a prior order in `Store Preferences History` only when its rationale or restoration value remains material. Treat a current/history change as one coherent operation and do not claim success after a partial write.
- Give every new price observation a stable `Record ID`; preserve the existing key in a role-equivalent legacy table. Match evidence by store, region, product/model, date, package identity, offer conditions, source, and confidence. Preserve formulas and validations during maintenance.
- Check workbook audit triggers using `Record Index` metadata or native row counts and schema metadata. Before structural maintenance, export and validate staged before/after snapshots under the shared protocol; do not use the Markdown audit validator for these workbook records.
- Report whether the grocery preference change was saved, used only for the current task, or could not be saved. Do not repeatedly ask for storage permission after the user has answered unless a materially different write is proposed.

## Apply preferences and fallbacks

- For each store, start with its supplied or saved preferred website when one exists, then use a suitable same-store source for the requested location. Continue through preferred stores in ascending priority before using a non-preferred retailer.
- Select constraint-compliant products at the highest-ranked feasible store. Do not sacrifice allergies, medical restrictions, required labels, brands, package needs, or explicit budget rules to honor store preference.
- Use the same order for price research and cost estimation. Do not optimize across lower-ranked stores unless the user asks for lowest price or another objective that changes the ranking.
- Organize a single-store list by store section. For a split basket, group stores in preference order and sections within each store.
- When a preferred source lacks a usable location, product, package, label, or current price, continue without another permission request. Identify the fallback store or estimate basis and briefly state why it was needed.
- Do not represent a third-party marketplace, unmatched location, or regional estimate as a direct preferred-store price.
