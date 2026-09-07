# Workbook audit snapshot and ledger

Read this reference only when auditing, restructuring, migrating, or testing a Meal Planner workbook. The canonical procedure remains in [record-management.md](record-management.md); this file defines the connector-neutral JSON accepted by `../scripts/validate_workbook_audit.py`.

## Snapshot

Export the complete logical workbook structure before and after the proposed change:

```json
{
  "schema_version": 1,
  "workbook": {
    "resource_id": "immutable-provider-id-or-canonical-path",
    "title": "Meal Preferences"
  },
  "sheets": [
    {
      "name": "Recipe Ratings",
      "role": "current",
      "columns": [{"name": "Record ID"}],
      "tables": [{"name": "RecipeRatings", "range": "A1:N200"}],
      "rows": [
        {
          "record_id": "RR-2026-08-18-01",
          "values": {"Record ID": "RR-2026-08-18-01"},
          "formulas": {},
          "validations": {},
          "references": []
        }
      ]
    }
  ],
  "named_ranges": [
    {"name": "CurrentRecipeRatings", "sheet": "Recipe Ratings", "range": "A1:N200"}
  ]
}
```

Use worksheet role `current`, `history`, `evidence`, or `index`. Include every populated canonical row and every structural element that could affect interpretation or retrieval. Mark a column, row, table, or named range with `"disposable": true` only after classifying it as incorrect, transient, empty formatting, or valueless duplication; protected data is never disposable.

Represent same-workbook pointers with `workbook_id`, `sheet`, and `record_id`. Set `external` to `true` only for a pointer to another canonical resource and include that resource's exact `workbook_id` and `record_id`. A snapshot is incomplete if the connector omits formulas, validations, named ranges, hidden canonical rows, or relevant references; stop rather than treating absent export data as absent workbook data.

## Ledger

For household cleanup, set `preserve_data_rows: true`. This prohibits removing any source record (even one marked disposable), requires a record target for every source record, and prohibits mapping two source records onto one target. Preserve data by stable identity and field mapping, not row counts alone. See [cleanup-migration.md](cleanup-migration.md).

Create a bidirectional ledger after both snapshots exist:

```json
{
  "schema_version": 1,
  "preserve_data_rows": true,
  "before_hash": "sha256-of-canonical-before-json",
  "after_hash": "sha256-of-canonical-after-json",
  "decisions": [
    {
      "before_ref": "record:Recipe Ratings:RR-2026-08-18-01",
      "disposition": "retained",
      "after_refs": ["record:Recipe Ratings:RR-2026-08-18-01"]
    }
  ],
  "new_after_refs": [],
  "new_items_justification": ""
}
```

The validator generates these item references:

- `sheet:<worksheet>`
- `column:<worksheet>:<column>`
- `table:<worksheet>:<table>`
- `record:<worksheet>:<record-id>`
- `named-range:<name>`

Map every before item exactly once and every after item to a before origin or `new_after_refs`. Use `retained` or `moved` only when the native payload is exact. Use `reworded` only with `semantic_review: passed` and a justification. Use `updated` only with `authorized: true` and a justification; add `formula_review: passed` whenever formulas change. Use `archived` only when an exact record appears in a history-role worksheet. Use `removed` only for an item already marked disposable and provide a justification.

When the canonical workbook resource ID changes, record `authority_transfer_authorized: true` and an `authority_transfer_justification`. This proves an authorized transfer, not that external permissions, links, or connector state were updated successfully.

## Completion boundary

Run the validator before replacing the canonical workbook. A pass proves that the supplied snapshots are structurally valid and completely mapped; it does not prove the connector exported everything or that reworded content is semantically equivalent. Inspect the provider's native revision comparison when available, verify the written workbook against the accepted after snapshot, and retain the recovery copy until verification succeeds.
