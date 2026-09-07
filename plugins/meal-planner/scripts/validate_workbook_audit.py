#!/usr/bin/env python3
"""Validate a staged Meal Planner workbook audit from native structure snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROLES = {"current", "history", "evidence", "index"}
DISPOSITIONS = {"retained", "moved", "reworded", "updated", "archived", "removed"}


class AuditError(ValueError):
    """Raised when a staged workbook audit cannot prove safe coverage."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _named_objects(items: Any, label: str) -> list[dict[str, Any]]:
    _require(isinstance(items, list), f"{label} must be a list")
    names: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        _require(isinstance(item, dict), f"Every {label} item must be an object")
        name = item.get("name")
        _require(isinstance(name, str) and name, f"{label} item has no name")
        _require(name not in names, f"Duplicate {label} name: {name}")
        names.add(name)
        result.append(item)
    return result


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    _require(snapshot.get("schema_version") == 1, "Unsupported snapshot schema_version")
    workbook = snapshot.get("workbook")
    _require(isinstance(workbook, dict), "workbook must be an object")
    for field in ("resource_id", "title"):
        _require(isinstance(workbook.get(field), str) and workbook[field], f"workbook.{field} is required")

    sheets = _named_objects(snapshot.get("sheets"), "sheet")
    _require(bool(sheets), "Snapshot must contain at least one sheet")
    sheet_by_name = {sheet["name"]: sheet for sheet in sheets}
    all_records: dict[str, tuple[str, dict[str, Any]]] = {}

    for sheet in sheets:
        role = sheet.get("role")
        _require(role in ROLES, f"Invalid role for sheet {sheet['name']}: {role}")
        columns = _named_objects(sheet.get("columns"), f"columns in {sheet['name']}")
        column_names = {column["name"] for column in columns}
        _named_objects(sheet.get("tables", []), f"tables in {sheet['name']}")
        rows = sheet.get("rows")
        _require(isinstance(rows, list), f"rows in {sheet['name']} must be a list")
        for row in rows:
            _require(isinstance(row, dict), f"Every row in {sheet['name']} must be an object")
            record_id = row.get("record_id")
            _require(isinstance(record_id, str) and record_id, f"Row in {sheet['name']} has no stable record_id")
            _require(record_id not in all_records, f"Duplicate stable record_id: {record_id}")
            all_records[record_id] = (sheet["name"], row)
            for field in ("values", "formulas", "validations"):
                mapping = row.get(field, {})
                _require(isinstance(mapping, dict), f"{field} for {record_id} must be an object")
                unknown = set(mapping) - column_names
                _require(not unknown, f"{record_id} uses columns absent from {sheet['name']}: {sorted(unknown)}")
            for formula in row.get("formulas", {}).values():
                _require(isinstance(formula, str) and formula, f"Empty formula in {record_id}")
                _require("#REF!" not in formula.upper(), f"Broken formula reference in {record_id}")
            references = row.get("references", [])
            _require(isinstance(references, list), f"references for {record_id} must be a list")

    for sheet_name, row in all_records.values():
        for reference in row.get("references", []):
            _require(isinstance(reference, dict), f"Reference in {row['record_id']} must be an object")
            if reference.get("external") is True:
                _require(reference.get("workbook_id") and reference.get("record_id"),
                         f"External reference in {row['record_id']} lacks identity")
                continue
            _require(reference.get("workbook_id") == workbook["resource_id"],
                     f"Local reference in {row['record_id']} uses the wrong workbook identity")
            target_sheet = reference.get("sheet")
            target_id = reference.get("record_id")
            _require(target_sheet in sheet_by_name, f"Broken sheet reference from {row['record_id']}: {target_sheet}")
            _require(target_id in all_records, f"Broken record reference from {row['record_id']}: {target_id}")
            _require(all_records[target_id][0] == target_sheet,
                     f"Reference from {row['record_id']} points to the wrong sheet for {target_id}")

    for named_range in _named_objects(snapshot.get("named_ranges", []), "named range"):
        target_sheet = named_range.get("sheet")
        _require(target_sheet in sheet_by_name, f"Named range {named_range['name']} targets missing sheet: {target_sheet}")
        _require(isinstance(named_range.get("range"), str) and named_range["range"],
                 f"Named range {named_range['name']} has no range")


def inventory(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return deterministic native workbook structure and record items."""
    validate_snapshot(snapshot)
    items: dict[str, dict[str, Any]] = {}
    for sheet in snapshot["sheets"]:
        sheet_name = sheet["name"]
        items[f"sheet:{sheet_name}"] = {
            "kind": "sheet",
            "payload": {"name": sheet_name, "role": sheet["role"]},
            "disposable": bool(sheet.get("disposable", False)),
        }
        for column in sheet["columns"]:
            ref = f"column:{sheet_name}:{column['name']}"
            items[ref] = {
                "kind": "column",
                "payload": {"name": column["name"]},
                "disposable": bool(column.get("disposable", False)),
            }
        for table in sheet.get("tables", []):
            ref = f"table:{sheet_name}:{table['name']}"
            items[ref] = {
                "kind": "table",
                "payload": {key: value for key, value in table.items() if key != "disposable"},
                "disposable": bool(table.get("disposable", False)),
            }
        for row in sheet["rows"]:
            ref = f"record:{sheet_name}:{row['record_id']}"
            items[ref] = {
                "kind": "record",
                "role": sheet["role"],
                "payload": {
                    "record_id": row["record_id"],
                    "values": row.get("values", {}),
                    "formulas": row.get("formulas", {}),
                    "validations": row.get("validations", {}),
                    "references": row.get("references", []),
                },
                "disposable": bool(row.get("disposable", False)),
            }
    for named_range in snapshot.get("named_ranges", []):
        ref = f"named-range:{named_range['name']}"
        items[ref] = {
            "kind": "named_range",
            "payload": {key: value for key, value in named_range.items() if key != "disposable"},
            "disposable": bool(named_range.get("disposable", False)),
        }
    return items


def validate_audit(before: dict[str, Any], after: dict[str, Any], ledger: dict[str, Any]) -> None:
    """Validate complete bidirectional coverage without modifying either workbook."""
    before_items = inventory(before)
    after_items = inventory(after)
    _require(ledger.get("schema_version") == 1, "Unsupported ledger schema_version")
    _require(ledger.get("before_hash") == canonical_hash(before), "before_hash does not match snapshot")
    _require(ledger.get("after_hash") == canonical_hash(after), "after_hash does not match snapshot")

    before_book = before["workbook"]
    after_book = after["workbook"]
    if before_book["resource_id"] != after_book["resource_id"]:
        _require(ledger.get("authority_transfer_authorized") is True,
                 "Workbook resource identity changed without authorized transfer")
        _require(bool(ledger.get("authority_transfer_justification")),
                 "Authorized workbook transfer lacks justification")

    decisions = ledger.get("decisions")
    _require(isinstance(decisions, list), "decisions must be a list")
    by_before: dict[str, dict[str, Any]] = {}
    referenced_after: set[str] = set()
    record_targets: set[str] = set()
    for decision in decisions:
        _require(isinstance(decision, dict), "Every decision must be an object")
        before_ref = decision.get("before_ref")
        disposition = decision.get("disposition")
        after_refs = decision.get("after_refs")
        _require(before_ref in before_items, f"Decision refers to unknown before item: {before_ref}")
        _require(before_ref not in by_before, f"Multiple decisions for before item: {before_ref}")
        _require(disposition in DISPOSITIONS, f"Invalid disposition for {before_ref}: {disposition}")
        _require(isinstance(after_refs, list), f"after_refs must be a list for {before_ref}")
        _require(all(ref in after_items for ref in after_refs), f"Unknown after item for {before_ref}")
        by_before[before_ref] = decision
        referenced_after.update(after_refs)

        source = before_items[before_ref]
        targets = [after_items[ref] for ref in after_refs]
        if ledger.get("preserve_data_rows") is True and source["kind"] == "record":
            _require(disposition != "removed", f"Cleanup cannot remove a data row: {before_ref}")
            surviving = {ref for ref in after_refs if after_items[ref]["kind"] == "record"}
            _require(bool(surviving), f"Cleanup row has no surviving data row: {before_ref}")
            _require(record_targets.isdisjoint(surviving),
                     f"Cleanup cannot merge source rows into one target: {before_ref}")
            record_targets.update(surviving)
        justification = decision.get("justification")
        if disposition in {"retained", "moved"}:
            _require(targets, f"{disposition} item has no target: {before_ref}")
            _require(any(target["kind"] == source["kind"] and target["payload"] == source["payload"] for target in targets),
                     f"{disposition} item changed native payload: {before_ref}")
        elif disposition == "reworded":
            _require(source["kind"] == "record", f"Only record content may be reworded: {before_ref}")
            _require(targets, f"Reworded record has no target: {before_ref}")
            _require(decision.get("semantic_review") == "passed",
                     f"Reworded record lacks passed semantic review: {before_ref}")
            _require(isinstance(justification, str) and justification,
                     f"Reworded record lacks justification: {before_ref}")
            if any(target["payload"].get("formulas") != source["payload"].get("formulas") for target in targets):
                _require(decision.get("formula_review") == "passed",
                         f"Reworded record changes a formula without review: {before_ref}")
        elif disposition == "updated":
            _require(targets, f"Updated item has no target: {before_ref}")
            _require(decision.get("authorized") is True, f"Updated item lacks authorization: {before_ref}")
            _require(isinstance(justification, str) and justification,
                     f"Updated item lacks justification: {before_ref}")
            if source["kind"] == "record" and any(
                target["payload"].get("formulas") != source["payload"].get("formulas") for target in targets
            ):
                _require(decision.get("formula_review") == "passed",
                         f"Updated record changes a formula without review: {before_ref}")
        elif disposition == "archived":
            _require(source["kind"] == "record", f"Only records may be archived: {before_ref}")
            _require(targets, f"Archived record has no target: {before_ref}")
            _require(any(target["kind"] == "record" and target.get("role") == "history" and
                         target["payload"] == source["payload"] for target in targets),
                     f"Archived record was not preserved exactly in a history sheet: {before_ref}")
        elif disposition == "removed":
            _require(source["disposable"], f"Protected workbook item cannot be removed: {before_ref}")
            _require(not targets, f"Removed item still has targets: {before_ref}")
            _require(isinstance(justification, str) and justification,
                     f"Removed item lacks justification: {before_ref}")

    _require(set(by_before) == set(before_items), "Every before item must have exactly one decision")
    new_after = ledger.get("new_after_refs", [])
    _require(isinstance(new_after, list), "new_after_refs must be a list")
    _require(len(new_after) == len(set(new_after)), "new_after_refs contains duplicates")
    _require(all(ref in after_items for ref in new_after), "new_after_refs contains an unknown item")
    _require(referenced_after.isdisjoint(new_after), "An after item cannot be both derived and new")
    _require(referenced_after | set(new_after) == set(after_items),
             "Every after item must map to before state or be explicitly marked new")
    if new_after:
        _require(isinstance(ledger.get("new_items_justification"), str) and ledger["new_items_justification"],
                 "New workbook items require a justification")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before_snapshot", type=Path)
    parser.add_argument("after_snapshot", type=Path)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args(argv)
    before = json.loads(args.before_snapshot.read_text(encoding="utf-8"))
    after = json.loads(args.after_snapshot.read_text(encoding="utf-8"))
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    validate_audit(before, after, ledger)
    print("PASS workbook audit: native structure, records, formulas, validations, and references verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, json.JSONDecodeError, OSError) as exc:
        print(f"FAIL workbook audit: {exc}", file=sys.stderr)
        raise SystemExit(1)
