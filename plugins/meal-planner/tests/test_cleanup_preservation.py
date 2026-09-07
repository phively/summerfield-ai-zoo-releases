"""Exercise data-row preservation independently of instruction wording."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "meal_audit", Path(__file__).parents[1] / "scripts" / "validate_workbook_audit.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def fixture():
    before = {"schema_version": 1, "workbook": {"resource_id": "book", "title": "Preferences"},
              "sheets": [{"name": "Ratings", "role": "current",
                          "columns": [{"name": "Rating"}], "rows": [
                              {"record_id": "one", "values": {"Rating": 3.5}, "disposable": True},
                              {"record_id": "two", "values": {"Rating": 4.5}},
                          ]}], "named_ranges": []}
    ledger = {"schema_version": 1, "preserve_data_rows": True,
              "before_hash": audit.canonical_hash(before), "after_hash": audit.canonical_hash(before),
              "decisions": [{"before_ref": key, "disposition": "retained", "after_refs": [key]}
                            for key in audit.inventory(before)], "new_after_refs": []}
    return before, deepcopy(before), ledger


def test_preserved_rows_and_half_step_values_pass():
    before, after, ledger = fixture()
    audit.validate_audit(before, after, ledger)


def test_cleanup_rejects_removal_even_when_marked_disposable():
    before, after, ledger = fixture()
    after["sheets"][0]["rows"].pop(0)
    ledger["after_hash"] = audit.canonical_hash(after)
    row = next(d for d in ledger["decisions"] if d["before_ref"].endswith(":one"))
    row.update(disposition="removed", after_refs=[], justification="Apparent duplicate")
    with pytest.raises(audit.AuditError, match="cannot remove a data row"):
        audit.validate_audit(before, after, ledger)


def test_cleanup_rejects_many_to_one_collapse():
    before, after, ledger = fixture()
    after["sheets"][0]["rows"].pop(0)
    ledger["after_hash"] = audit.canonical_hash(after)
    row = next(d for d in ledger["decisions"] if d["before_ref"].endswith(":one"))
    row.update(disposition="updated", after_refs=["record:Ratings:two"],
               authorized=True, justification="Attempted merge")
    with pytest.raises(audit.AuditError, match="cannot merge source rows"):
        audit.validate_audit(before, after, ledger)


def test_cleanup_rejects_mapping_row_to_metadata_only():
    before, after, ledger = fixture()
    after["sheets"][0]["rows"].pop(0)
    ledger["after_hash"] = audit.canonical_hash(after)
    row = next(d for d in ledger["decisions"] if d["before_ref"].endswith(":one"))
    row.update(disposition="updated", after_refs=["sheet:Ratings"],
               authorized=True, justification="Attempted loss")
    with pytest.raises(audit.AuditError, match="no surviving data row"):
        audit.validate_audit(before, after, ledger)


def test_cleanup_allows_update_and_addition_with_traceable_rows():
    before, after, ledger = fixture()
    after["sheets"][0]["rows"][0]["values"]["Rating"] = 4.5
    after["sheets"][0]["rows"].append({"record_id": "three", "values": {"Rating": 2.5}})
    ledger["after_hash"] = audit.canonical_hash(after)
    row = next(d for d in ledger["decisions"] if d["before_ref"].endswith(":one"))
    row.update(disposition="updated", authorized=True, justification="Confirmed revised rating")
    ledger.update(new_after_refs=["record:Ratings:three"], new_items_justification="New member feedback")
    audit.validate_audit(before, after, ledger)
