# Store preference workflow

Use this workflow to resolve, persist, apply, update, or remove store preferences without changing unrelated grocery-tracker data.

## Workbook and canonical tabs

Use a workbook or Google Sheet titled `Grocery Preferences` or a clearly equivalent title such as `Grocery Price Tracker` or `Shopping Preferences`. When creating a new workbook, use `Grocery Preferences`. Reuse an accessible equivalent workbook instead of creating a competing copy.

Use these canonical tabs, accepting clearly equivalent existing tab names without forcing a migration:

- `Store Preferences`: the ordered stores and preferred websites defined below.
- `Price Tracker`: observed product, store, location, date, package, price, sale or membership status, and source details used for future estimates.

Treat the exact workbook title, link or file identity, and tab names as source provenance. Report missing canonical tabs; create or rename tabs only with authorization, and do not copy their contents into skill-local files.

## Resolve the effective order

1. Use an ordered store list explicitly supplied for the current request or by `meal-planner`. Treat it as task-specific unless the user also asks or consents to save it.
2. Otherwise, read the saved active order from the accessible spreadsheet used as the grocery price tracker.
3. If neither is available, ask one focused question for an ordered list. Accept a store name and an optional preferred website URL for each entry. In the same question, ask whether the list may be saved in the grocery price tracker.
4. If the user declines to name stores, use ordinary local-source fallbacks. If the user supplies a list but declines storage, use it for the current task only.
5. Never claim that preferences were loaded or saved when the tracker is unavailable or a write did not succeed.

Current explicit instructions override saved preferences for the task. Do not silently replace the saved list when a one-time order differs from it.

## Persist with consent

- Require the user's explicit consent before the first save or before replacing a saved list. A delegated handoff counts only when it states that the user consented. An explicit request to update, reorder, or remove saved preferences authorizes that requested change.
- Store preferences in the `Store Preferences` tab of the same workbook as the `Price Tracker` tab. Do not create a separate preference file or claim cross-task persistence when that workbook is unavailable.
- Reuse an existing clearly designated compatible preference area when present. Otherwise, after consent, add a worksheet named `Store Preferences`; do not add columns to the tracker table or alter its rows, formulas, formatting, named ranges, or schema.
- If `Store Preferences` already contains unrelated data, preserve it and use a new worksheet named `Store Preferences - Shopper`. Never overwrite or repurpose ambiguous content.
- Use these columns, in this order: `Priority`, `Store`, `Preferred Website`, `Updated At`. Keep one store per row, positive unique priorities in ascending order, blank website cells when none were supplied, and a visible timestamp for successful changes.
- On update, touch only the designated preference rows and renumber priorities as needed. On removal, delete or clear only the requested store row, then close the priority gap. Preserve spreadsheet revision history when the connected tool provides it.
- Report whether the preference change was saved, used only for the current task, or could not be saved. Do not repeatedly ask for storage permission after the user has answered unless a materially different write is proposed.

## Apply preferences and fallbacks

- For each store, start with its supplied or saved preferred website when one exists, then use a suitable same-store source for the requested location. Continue through preferred stores in ascending priority before using a non-preferred retailer.
- Select constraint-compliant products at the highest-ranked feasible store. Do not sacrifice allergies, medical restrictions, required labels, brands, package needs, or explicit budget rules to honor store preference.
- Use the same order for price research and cost estimation. Do not optimize across lower-ranked stores unless the user asks for lowest price or another objective that changes the ranking.
- Organize a single-store list by store section. For a split basket, group stores in preference order and sections within each store.
- When a preferred source lacks a usable location, product, package, label, or current price, continue without another permission request. Identify the fallback store or estimate basis and briefly state why it was needed.
- Do not represent a third-party marketplace, unmatched location, or regional estimate as a direct preferred-store price.
