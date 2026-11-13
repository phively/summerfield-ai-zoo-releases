import hashlib
import json
from copy import deepcopy
from pathlib import Path
import subprocess
import sys


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = PLUGIN_ROOT / "scripts" / "validate_workbook_audit.py"
BEFORE_ITEMS = [
    "sheet:Price Tracker",
    "column:Price Tracker:Record ID",
    "column:Price Tracker:Product",
    "column:Price Tracker:Price",
    "column:Price Tracker:Estimated Value",
    "table:Price Tracker:PriceTracker",
    "record:Price Tracker:PT-1",
    "record:Price Tracker:PT-2",
]


def workbook_fixture():
    before = {
        "schema_version": 1,
        "workbook": {"resource_id": "grocery-book", "title": "Grocery Preferences"},
        "sheets": [
            {
                "name": "Price Tracker",
                "role": "evidence",
                "columns": [
                    {"name": "Record ID"},
                    {"name": "Product"},
                    {"name": "Price"},
                    {"name": "Estimated Value"},
                ],
                "tables": [{"name": "PriceTracker", "range": "A1:D4"}],
                "rows": [
                    {
                        "record_id": "PT-1",
                        "values": {"Record ID": "PT-1", "Product": "Oats", "Price": 4.0},
                        "formulas": {"Estimated Value": "=C2*2"},
                        "validations": {},
                        "references": [],
                    },
                    {
                        "record_id": "PT-2",
                        "values": {"Record ID": "PT-2", "Product": "Rice", "Price": 8.0},
                        "formulas": {"Estimated Value": "=C3*2"},
                        "validations": {},
                        "references": [],
                    },
                ],
            }
        ],
        "named_ranges": [],
    }
    return before, deepcopy(before)


def canonical_hash(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def ledger_for(before, after):
    after_items = set(BEFORE_ITEMS[:-2])
    after_items.update(
        f"record:Price Tracker:{row['record_id']}" for row in after["sheets"][0]["rows"]
    )
    return {
        "schema_version": 1,
        "preserve_data_rows": True,
        "before_hash": canonical_hash(before),
        "after_hash": canonical_hash(after),
        "decisions": [
            {"before_ref": item, "disposition": "retained", "after_refs": [item]}
            for item in BEFORE_ITEMS
        ],
        "new_after_refs": sorted(after_items - set(BEFORE_ITEMS)),
        "new_items_justification": "Authorized new price observation",
    }


def run_validator(before, after, ledger, tmp_path):
    paths = [tmp_path / name for name in ("before.json", "after.json", "ledger.json")]
    for path, payload in zip(paths, (before, after, ledger)):
        path.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), *(str(path) for path in paths)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_audit_rejects_an_omitted_populated_row(tmp_path):
    before, after = workbook_fixture()
    after["sheets"][0]["rows"].pop(0)
    ledger = ledger_for(before, after)
    row = next(item for item in ledger["decisions"] if item["before_ref"] == "record:Price Tracker:PT-1")
    row.update(disposition="removed", after_refs=[])
    result = run_validator(before, after, ledger, tmp_path)

    assert result.returncode == 1
    assert "cannot remove a data row" in result.stderr


def test_audit_rejects_merging_distinct_record_keys(tmp_path):
    before, after = workbook_fixture()
    after["sheets"][0]["rows"].pop(1)
    ledger = ledger_for(before, after)
    merged = next(item for item in ledger["decisions"] if item["before_ref"] == "record:Price Tracker:PT-2")
    merged.update(
        disposition="updated",
        after_refs=["record:Price Tracker:PT-1"],
        authorized=True,
        justification="Attempted duplicate consolidation",
    )
    result = run_validator(before, after, ledger, tmp_path)

    assert result.returncode == 1
    assert "cannot merge source rows" in result.stderr


def test_audit_rejects_losing_a_protected_formula(tmp_path):
    before, after = workbook_fixture()
    after["sheets"][0]["rows"][0]["formulas"].pop("Estimated Value")
    ledger = ledger_for(before, after)
    result = run_validator(before, after, ledger, tmp_path)

    assert result.returncode == 1
    assert "changed native payload" in result.stderr


def test_audit_accepts_justified_addition_while_retaining_existing_rows(tmp_path):
    before, after = workbook_fixture()
    after["sheets"][0]["rows"].append(
        {
            "record_id": "PT-3",
            "values": {"Record ID": "PT-3", "Product": "Beans", "Price": 2.5},
            "formulas": {"Estimated Value": "=C4*2"},
            "validations": {},
            "references": [],
        }
    )
    ledger = ledger_for(before, after)
    result = run_validator(before, after, ledger, tmp_path)

    assert result.returncode == 0
    assert "PASS workbook audit" in result.stdout
