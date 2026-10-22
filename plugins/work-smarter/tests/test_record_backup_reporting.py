"""Offline backup/reporting invariants; no provider or GitHub writes."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "record-backup" / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reporting = load("reporting")
validator = load("validate_snapshot")


def receipt(number=1, mode="daily"):
    result = {
        "schema_version": 1, "run_id": f"run-{number}", "mode": mode,
        "status": "verified-no-change", "started_at": f"2026-09-{number:02}T01:00:00Z",
        "ended_at": f"2026-09-{number:02}T01:01:00Z", "snapshot_commit": "a" * 40,
        "checks": {"local_snapshot": True, "remote_snapshot": True},
        "scope": "configured roots", "exclusions": "secrets", "history_coverage": "daily observations only",
        "coverage_limits": [], "current_state_complete": True,
        "counts": {"records": 3, "bytes": 50, "changed": 0, "deleted": 0},
        "discovery": {"listing_calls": 2, "content_reads": 3, "duplicates": 1, "pointer_cycles": 0, "retries": 0},
    }
    if mode == "weekly":
        result.update(repaired_items=[], unrecoverable_gaps=[], source_access_limits=[], restore_test="latest snapshot reconstructed")
    return result


def save(root, value):
    (root / "receipts").mkdir(exist_ok=True)
    (root / "receipts" / f"{value['run_id']}.json").write_text(json.dumps(value), encoding="utf-8")


def snapshot(root):
    records = []
    for path, data, role in (
        ("records/configuration/profile.yaml", b"schema_version: 1\r\n", "configuration"),
        ("records/image.bin", bytes(range(256)), "current-authority"),
        ("records/extensionless", b"\x00\xff", "supporting"),
    ):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        records.append({"repository_path": path, "source_provider": "fixture", "source_container": "root",
                        "source_id": path, "source_path": path, "owner": "fixture", "classification": role,
                        "byte_size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {"schema_version": 1, "operational_layout": 1, "profile_repository_path": records[0]["repository_path"], "records": records}
    (root / "backup-index.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def test_formats_and_profile_round_trip(tmp_path):
    manifest = snapshot(tmp_path)
    reporting.process(tmp_path, write=True)
    assert validator.validate(tmp_path, tmp_path / "backup-index.json")["record_count"] == 3
    for item in manifest["records"]:
        assert hashlib.sha256((tmp_path / item["repository_path"]).read_bytes()).hexdigest() == item["sha256"]
    (tmp_path / manifest["profile_repository_path"]).write_bytes(b"normalized\n")
    with pytest.raises(validator.SnapshotError, match="content mismatch"):
        validator.validate(tmp_path, tmp_path / "backup-index.json")


def test_summary_retains_history_and_surrounding_bytes(tmp_path):
    original = "# User notes\r\nKeep this.\r\n"
    (tmp_path / "README.md").write_bytes(original.encode())
    for number in range(1, 10):
        save(tmp_path, receipt(number))
    failed = receipt(10, "weekly")
    failed.update(status="failed", current_state_complete=False, snapshot_commit=None,
                  checks={"local_snapshot": False, "remote_snapshot": False}, coverage_limits=["Unavailable | <root>"])
    save(tmp_path, failed)
    save(tmp_path, receipt(11, "manual"))
    save(tmp_path, receipt(2, "weekly") | {"run_id": "weekly-old"})
    reporting.process(tmp_path, write=True)
    first = (tmp_path / "README.md").read_bytes()
    assert first.startswith(original.encode())
    text = first.decode()
    assert text.count("](receipts/") == 8
    assert "receipts/run-3.json" in text and "receipts/run-1.json" not in text
    assert "receipts/run-10.json" in text and "receipts/weekly-old.json" not in text
    assert "Unavailable \\| &lt;root&gt;" in text
    assert len(list((tmp_path / "receipts").iterdir())) == 12
    reporting.process(tmp_path, write=True)
    assert (tmp_path / "README.md").read_bytes() == first
    reporting.process(tmp_path)


@pytest.mark.parametrize("change", [
    {"snapshot_commit": None}, {"current_state_complete": False},
    {"checks": {"local_snapshot": True, "remote_snapshot": False}},
    {"ended_at": "2026-08-01T00:00:00Z"}, {"ended_at": "2026-09-01T00:00:00"},
    {"counts": {"records": True, "bytes": 0, "changed": 0, "deleted": 0}},
    {"counts": {"records": 1, "bytes": 0, "changed": 1, "deleted": 0}},
    {"status": "failed"}, {"schema_version": True},
])
def test_receipt_rejects_false_or_inconsistent_success(change):
    value = receipt() | copy.deepcopy(change)
    with pytest.raises(ValueError):
        reporting.validate_receipt(value, "run-1")


def test_destination_exclusions_require_separate_preservation_evidence():
    value = receipt()
    value["destination_exclusions"] = ["separately-managed/research"]
    with pytest.raises(ValueError, match="require separate preservation evidence"):
        reporting.validate_receipt(value, "run-1")

    value["destination_preservation"] = {
        "status": "content_preserved",
        "protected_roots": ["separately-managed/research"],
        "baseline_commit": "b" * 40,
        "content_commit": "a" * 40,
    }
    assert reporting.validate_receipt(value, "run-1")["destination_preservation"]["status"] == "content_preserved"

    legacy = copy.deepcopy(value)
    legacy["destination_preservation"] = {
        "status": "preserved",
        "protected_roots": ["separately-managed/research"],
        "baseline_commit": "b" * 40,
        "content_commit": "a" * 40,
        "operational_commit": "d" * 40,
    }
    assert reporting.validate_receipt(legacy, "run-1")["destination_preservation"]["status"] == "preserved"


def test_verified_receipt_rejects_mismatched_destination_content_commit():
    value = receipt()
    value["destination_exclusions"] = ["separately-managed/research"]
    value["destination_preservation"] = {
        "status": "content_preserved",
        "protected_roots": ["separately-managed/research"],
        "baseline_commit": "b" * 40,
        "content_commit": "c" * 40,
    }

    with pytest.raises(ValueError, match="content_commit to match snapshot_commit"):
        reporting.validate_receipt(value, "run-1")


@pytest.mark.parametrize("preservation_status", ["staged_preserved", "unverified", "failed"])
def test_verified_receipt_rejects_partial_destination_preservation(preservation_status):
    value = receipt()
    value["destination_exclusions"] = ["separately-managed/research"]
    value["destination_preservation"] = {
        "status": preservation_status,
        "protected_roots": ["separately-managed/research"],
        "baseline_commit": "b" * 40,
        "content_commit": "c" * 40 if preservation_status != "staged_preserved" else None,
    }

    with pytest.raises(ValueError, match="verified receipt requires complete destination preservation"):
        reporting.validate_receipt(value, "run-1")


def test_readme_summary_displays_preservation_separately_from_snapshot_status():
    value = receipt()
    value["mode"] = "weekly"
    value["restore_test"] = "synthetic recovery evidence"
    value["destination_exclusions"] = ["separately-managed/research"]
    value["destination_preservation"] = {
        "status": "content_preserved",
        "protected_roots": ["separately-managed/research"],
        "baseline_commit": "b" * 40,
        "content_commit": "a" * 40,
    }
    text = reporting.render_block([value])

    assert "| Preservation |" in text
    assert "| content\\_preserved |" in text


def test_snapshot_rejects_unindexed_files_and_stale_summary(tmp_path):
    snapshot(tmp_path)
    reporting.process(tmp_path, write=True)
    save(tmp_path, receipt())
    with pytest.raises(validator.SnapshotError, match="stale"):
        validator.validate(tmp_path, tmp_path / "backup-index.json")
    reporting.process(tmp_path, write=True)
    validator.validate(tmp_path, tmp_path / "backup-index.json")
    (tmp_path / "unindexed.txt").write_text("extra")
    with pytest.raises(validator.SnapshotError, match="unindexed"):
        validator.validate(tmp_path, tmp_path / "backup-index.json")


def test_cli_and_ambiguous_markers(tmp_path):
    snapshot(tmp_path)
    save(tmp_path, receipt())
    for args in (["reporting.py", str(tmp_path), "--write"], ["reporting.py", str(tmp_path)], ["validate_snapshot.py", str(tmp_path)]):
        result = subprocess.run([sys.executable, str(SCRIPTS / args[0]), *args[1:]], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    with pytest.raises(ValueError, match="ambiguous"):
        reporting.update_readme(reporting.START * 2 + reporting.END, "unused")


def test_legacy_layout_still_validates(tmp_path):
    manifest = snapshot(tmp_path)
    manifest.pop("operational_layout")
    manifest.pop("profile_repository_path")
    (tmp_path / "backup-index.json").write_text(json.dumps(manifest))
    save(tmp_path, {"run_id": "old", "status": "verified"})
    assert validator.validate(tmp_path, tmp_path / "backup-index.json")["record_count"] == 3


def test_order_uses_instants_not_timestamp_strings():
    a, b = receipt(1), receipt(2)
    a["ended_at"] = "2026-09-02T04:00:00+05:00"
    assert reporting.timestamp(a["ended_at"]) < reporting.timestamp(b["ended_at"])


def test_missing_profile_and_invalid_operational_files(tmp_path):
    manifest = snapshot(tmp_path)
    reporting.process(tmp_path, write=True)
    manifest["profile_repository_path"] = "records/not-present.yaml"
    (tmp_path / "backup-index.json").write_text(json.dumps(manifest))
    with pytest.raises(validator.SnapshotError, match="indexed configuration"):
        validator.validate(tmp_path, tmp_path / "backup-index.json")
    snapshot(tmp_path)
    save(tmp_path, {"run_id": "bad", "status": "verified"})
    with pytest.raises(validator.SnapshotError, match="receipt schema_version"):
        validator.validate(tmp_path, tmp_path / "backup-index.json")


def test_incomplete_subset_and_failure_receipts(tmp_path):
    for number, status in ((1, "incomplete"), (2, "failed")):
        value = receipt(number)
        value.update(status=status, current_state_complete=False, coverage_limits=["source access unavailable"])
        if status == "failed":
            value.update(snapshot_commit=None, checks={"local_snapshot": False, "remote_snapshot": False})
        save(tmp_path, value)
    reporting.process(tmp_path, write=True)
    assert reporting.process(tmp_path) == 2
    assert "failed" in (tmp_path / "README.md").read_text()
    assert "incomplete" in (tmp_path / "README.md").read_text()


def test_weekly_schema_and_nested_receipts_rejected(tmp_path):
    value = receipt(mode="weekly")
    value.pop("restore_test")
    with pytest.raises(ValueError, match="restore_test"):
        reporting.validate_receipt(value, "run-1")
    (tmp_path / "receipts" / "nested").mkdir(parents=True)
    with pytest.raises(ValueError, match="direct regular"):
        reporting.load_receipts(tmp_path)


def test_sorting_receipts_and_preserving_suffix(tmp_path):
    a, b = receipt(1), receipt(2)
    a["ended_at"] = "2026-09-02T04:00:00+05:00"
    save(tmp_path, a)
    save(tmp_path, b)
    assert [r["run_id"] for r in reporting.load_receipts(tmp_path)] == ["run-2", "run-1"]
    original = "Before\r\n" + reporting.START + "\nold\n" + reporting.END + "\r\nAfter\r\n"
    result = reporting.update_readme(original, reporting.render_block([]))
    assert result.startswith("Before\r\n") and result.endswith("\r\nAfter\r\n")


def legacy_receipt():
    return {"schema_version": 1, "run_id": "2026-09-17T063048-0500", "mode": "daily-sync",
            "result": "verified", "started_at": "2026-09-17T06:30:48-05:00",
            "ended_at": "2026-09-17T06:56:05-05:00", "source": {"provider": "fixture"},
            "destination": {"repository": "fixture/backup"}, "checks": {"changed_blob_readback": True},
            "reconciliation": {"findings": ["historical fixture"]}, "coverage": {"current_state": "reported complete"}}


def pin_legacy(root, manifest, value, stem):
    (root / "receipts").mkdir(exist_ok=True)
    raw = (json.dumps(value, indent=2) + "\n").encode()
    path = f"receipts/{stem}.json"
    (root / path).write_bytes(raw)
    entry = {"repository_path": path, "byte_size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
             "provenance": "reviewed synthetic historical fixture"}
    manifest["legacy_receipts"] = [entry]
    (root / "backup-index.json").write_text(json.dumps(manifest))
    return root / path, raw


@pytest.mark.parametrize("operational", [True, False])
def test_reviewed_legacy_receipts_preserve_bytes_and_work_in_both_layouts(tmp_path, operational):
    manifest = snapshot(tmp_path)
    if not operational:
        manifest.pop("operational_layout")
        manifest.pop("profile_repository_path")
    path, raw = pin_legacy(tmp_path, manifest, legacy_receipt(), "daily-2026-09-17T063048-0500")
    save(tmp_path, receipt())
    reporting.process(tmp_path, write=True)
    assert "1 reviewed historical receipts retained unchanged" in (tmp_path / "README.md").read_text()
    assert reporting.load_receipts(tmp_path) == [receipt()]
    assert validator.validate(tmp_path, tmp_path / "backup-index.json")["record_count"] == 3
    assert path.read_bytes() == raw
    path.write_bytes(raw + b" ")
    with pytest.raises(validator.SnapshotError, match="reviewed evidence"):
        validator.validate(tmp_path, tmp_path / "backup-index.json")


def test_unknown_and_malformed_modern_receipts_cannot_be_allowlisted(tmp_path):
    manifest = snapshot(tmp_path)
    invalid = receipt() | {"checks": {"local_snapshot": True, "remote_snapshot": False}}
    pin_legacy(tmp_path, manifest, invalid, "run-1")
    with pytest.raises(ValueError, match="modern receipts cannot be exempted"):
        reporting.process(tmp_path, write=True)
    pin_legacy(tmp_path, manifest, legacy_receipt() | {"mode": "unknown"}, "daily-2026-09-17T063048-0500")
    with pytest.raises(ValueError, match="unknown incompatible"):
        reporting.process(tmp_path, write=True)


@pytest.mark.parametrize("mode", ["weekly-reconciliation", "daily-missed-recovery"])
def test_other_inspected_historical_shapes_remain_excluded_from_current_rows(tmp_path, mode):
    manifest = snapshot(tmp_path)
    if mode == "weekly-reconciliation":
        value = legacy_receipt() | {"mode": mode, "restore_test": "historical reported drill", "history_coverage": "unknown"}
        stem = "weekly-" + value["run_id"]
    else:
        value = receipt() | {"mode": mode, "discovery": {
            "listing_pages": 4, "inventory_items": 373, "configured_records": 44,
            "stable_rechecks": 1, "pointer_cycles": 0}}
        stem = value["run_id"]
    path, raw = pin_legacy(tmp_path, manifest, value, stem)
    reporting.process(tmp_path, write=True)
    assert reporting.load_receipts(tmp_path) == []
    assert validator.validate(tmp_path, tmp_path / "backup-index.json")["record_count"] == 3
    assert path.read_bytes() == raw


@pytest.mark.parametrize("key", ["listing_pages", "inventory_items", "configured_records", "stable_rechecks", "pointer_cycles"])
@pytest.mark.parametrize("invalid", [None, True, -1])
def test_historical_discovery_counters_remain_strict(key, invalid):
    value = receipt() | {"mode": "daily-missed-recovery", "discovery": {
        "listing_pages": 4, "inventory_items": 373, "configured_records": 44,
        "stable_rechecks": 1, "pointer_cycles": 0}}
    original = copy.deepcopy(value)
    reporting.validate_legacy_receipt(value, value["run_id"])
    assert value == original
    with pytest.raises(ValueError, match="nonnegative integer discovery"):
        reporting.validate_receipt(value | {"mode": "daily"}, value["run_id"])
    value["discovery"][key] = invalid
    with pytest.raises(ValueError, match="nonnegative integer discovery"):
        reporting.validate_legacy_receipt(value, value["run_id"])


def test_missing_and_unreviewed_historical_receipts_are_rejected(tmp_path):
    manifest = snapshot(tmp_path)
    value = legacy_receipt()
    path, _ = pin_legacy(tmp_path, manifest, value, "daily-2026-09-17T063048-0500")
    path.unlink()
    with pytest.raises(ValueError, match="missing reviewed"):
        reporting.load_receipts(tmp_path)
    manifest.pop("legacy_receipts")
    (tmp_path / "backup-index.json").write_text(json.dumps(manifest))
    pin_legacy(tmp_path, manifest, value, "daily-2026-09-17T063048-0500")
    manifest.pop("legacy_receipts")
    (tmp_path / "backup-index.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="run_id"):
        reporting.load_receipts(tmp_path)


def migration_plan(original, removed):
    raw, block = original.encode(), removed.encode()
    start = raw.index(block)
    return {"readme_sha256": hashlib.sha256(raw).hexdigest(), "remove_ranges": [
        {"start": start, "end": start + len(block), "sha256": hashlib.sha256(block).hexdigest()}]}


def test_legacy_readme_cleanup_is_previewed_and_preserves_user_bytes(tmp_path):
    snapshot(tmp_path)
    save(tmp_path, receipt())
    old = "## Daily sync — 2026-09-15\r\n\r\n- Result: incomplete\r\n\r\n"
    original = "# User notes\r\nKeep café.\r\n\r\n" + old + "## My notes\r\nKeep these too.\r\n"
    (tmp_path / "README.md").write_bytes(original.encode())
    plan = migration_plan(original, old)
    preview = reporting.process(tmp_path, migration_plan=plan)
    assert "-## Daily sync" in preview and "+## Backup status" in preview
    assert (tmp_path / "README.md").read_bytes() == original.encode()
    reporting.process(tmp_path, write=True, migration_plan=plan)
    expected_prefix = (original.replace(old, "")).encode()
    after = (tmp_path / "README.md").read_bytes()
    assert after.startswith(expected_prefix)
    assert len(list((tmp_path / "receipts").iterdir())) == 1
    reporting.process(tmp_path, write=True)
    assert (tmp_path / "README.md").read_bytes() == after
    with pytest.raises(ValueError, match="reviewed migration source"):
        reporting.process(tmp_path, write=True, migration_plan=plan)


def test_cleanup_rejects_changed_ranges_and_status_block_removal():
    old = "## Verified structural cutover\nOld generated notes.\n\n"
    original = "# Keep\n\n" + old + reporting.render_block([]) + "\n"
    bad = migration_plan(original, old)
    bad["remove_ranges"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="reviewed bytes"):
        reporting.migrate_readme(original, bad)
    with pytest.raises(ValueError, match="generated status block"):
        reporting.migrate_readme(original, migration_plan(original, reporting.render_block([]) + "\n"))


@pytest.mark.parametrize("check", ["full_latest_restore", "full_older_restore"])
def test_attestation_cannot_make_a_failed_weekly_recovery_verified(check):
    value = receipt(mode="weekly")
    value["checks"][check] = False
    value["attestation"] = "user says the blob matches"
    with pytest.raises(ValueError, match="failed recovery drill"):
        reporting.validate_receipt(value, "run-1")
