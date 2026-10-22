"""Synthetic mode fixtures for exclusion-aware backup flows.

These tests validate offline packets, snapshots and independent state checks.
They do not activate the skill or contact a source or destination provider.
"""

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals" / "record-backup-destination-exclusions"


def load_fixtures():
    spec = importlib.util.spec_from_file_location(
        "record_backup_exclusion_fixtures", EVALS / "fixtures.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixtures = load_fixtures()
validator = fixtures.load_script("validate_snapshot")
preservation = fixtures.load_script("check_destination_preservation")
reporting = fixtures.load_script("reporting")


def validate(snapshot):
    return validator.validate(
        snapshot["root"],
        snapshot["manifest_path"],
        destination_policy=snapshot["policy"],
        policy_expectations=snapshot["expectations"],
    )


def test_daily_snapshot_and_both_publications_preserve_independent_destination_files(tmp_path):
    exclusion = "separately-managed/jobs"
    protected = {
        f"{exclusion}/posting.md": b"Independently maintained synthetic posting.\n",
        f"{exclusion}/notes/source.bin": b"\x00\x01synthetic independent data",
    }
    snapshot = fixtures.write_snapshot(
        tmp_path / "daily-stage",
        exclusions=[exclusion],
        managed_records={"records/topics/current.md": (
            "synthetic-current-topic", b"# Updated synthetic current topic\n")},
        protected_files=protected,
    )

    result = validate(snapshot)
    packet = fixtures.preservation_packet(
        protected_roots=[exclusion],
        baseline_files={
            "records/topics/current.md": b"# Prior synthetic current topic\n",
            **protected,
        },
        staged_files={
            "records/topics/current.md": b"# Updated synthetic current topic\n",
            **protected,
        },
        content_files={
            "records/topics/current.md": b"# Updated synthetic current topic\n",
            **protected,
        },
        operational_files={
            "records/topics/current.md": b"# Updated synthetic current topic\n",
            "receipts/synthetic-daily-run.json": b"synthetic receipt",
            "README.md": b"synthetic operational summary",
            **protected,
        },
    )
    preserved = preservation.check_preservation(packet)

    assert result["record_count"] == 2
    assert preserved["status"] == "preserved"
    assert [item["path"] for item in packet["baseline"]["inventory"]
            if item["path"].startswith(exclusion + "/") and item["type"] == "blob"] == sorted(protected)
    assert not any(item["repository_path"] in protected
                   for item in snapshot["manifest"]["records"])
    assert all((snapshot["root"] / path).read_bytes() == content
               for path, content in protected.items())


def test_manual_subset_keeps_omitted_prior_records_and_reports_incomplete_scope(tmp_path):
    exclusion = "separately-managed/research"
    protected = {f"{exclusion}/reference.md": b"synthetic independent reference\n"}
    snapshot = fixtures.write_snapshot(
        tmp_path / "manual-subset",
        exclusions=[exclusion],
        managed_records={
            "records/topics/selected.md": (
                "selected-source", b"# Updated selected record\n"),
            "records/topics/omitted.md": (
                "omitted-source", b"# Previous omitted record\n"),
        },
        protected_files=protected,
    )

    result = validate(snapshot)
    receipt = fixtures.mode_receipt(
        "manual", complete=False, records=result["record_count"],
        exclusions=[exclusion],
    )
    reporting.validate_receipt(receipt, receipt["run_id"])

    assert result["record_count"] == 3
    assert (snapshot["root"] / "records/topics/omitted.md").read_bytes() == (
        b"# Previous omitted record\n")
    assert receipt["status"] == "incomplete"
    assert not receipt["current_state_complete"]
    assert not receipt["checks"]["remote_snapshot"]


def test_weekly_fresh_enumeration_finds_cached_omission_and_denials_preserve_old_record(tmp_path):
    exclusion = "independent/archive"
    protected = {f"{exclusion}/ledger.json": b"synthetic external ledger\n"}
    fresh_pages = [
        [("alpha", "records/topics/alpha.md", b"# Current alpha\n")],
        [("beta", "records/topics/beta.md", b"# Current beta\n")],
    ]
    poisoned_daily_cache = {"alpha"}
    fresh_capture = fixtures.enumerate_fresh_pages(fresh_pages)
    fresh_items = fresh_capture["items"]
    assert {item[0] for item in fresh_items} == {"alpha", "beta"}
    assert "beta" not in poisoned_daily_cache
    assert fresh_capture["complete"]
    assert [event["page_number"] for event in fresh_capture["events"]] == [1, 2]

    complete_snapshot = fixtures.write_snapshot(
        tmp_path / "weekly-fresh",
        exclusions=[exclusion],
        managed_records={
            path: (source_id, content)
            for source_id, path, content in fresh_items
        },
        protected_files=protected,
    )
    assert validate(complete_snapshot)["record_count"] == 3
    weekly_preservation = fixtures.preservation_packet(
        protected_roots=[exclusion],
        baseline_files={
            "records/topics/alpha.md": b"# Prior alpha\n",
            "records/topics/beta.md": b"# Prior beta\n",
            **protected,
        },
        staged_files={
            "records/topics/alpha.md": b"# Current alpha\n",
            "records/topics/beta.md": b"# Current beta\n",
            **protected,
        },
        content_files={
            "records/topics/alpha.md": b"# Current alpha\n",
            "records/topics/beta.md": b"# Current beta\n",
            **protected,
        },
        operational_files={
            "records/topics/alpha.md": b"# Current alpha\n",
            "records/topics/beta.md": b"# Current beta\n",
            "receipts/synthetic-weekly-run.json": b"synthetic receipt",
            "README.md": b"synthetic operational summary",
            **protected,
        },
    )
    assert preservation.check_preservation(weekly_preservation)["status"] == "preserved"

    denied_snapshot = fixtures.write_snapshot(
        tmp_path / "weekly-source-denied",
        exclusions=[exclusion],
        managed_records={
            "records/topics/alpha.md": ("alpha", b"# Current alpha\n"),
            "records/topics/beta.md": ("beta", b"# Last verified beta\n"),
        },
        protected_files=protected,
    )
    denied_result = validate(denied_snapshot)
    denied_receipt = fixtures.mode_receipt(
        "weekly", complete=False, records=denied_result["record_count"],
        exclusions=[exclusion],
    )
    reporting.validate_receipt(denied_receipt, denied_receipt["run_id"])

    denied_staged_protected = {
        path: (denied_snapshot["root"] / path).read_bytes()
        for path in protected
        if (denied_snapshot["root"] / path).is_file()
    }
    denied_preservation = fixtures.preservation_packet(
        protected_roots=[exclusion],
        baseline_files={
            "records/topics/alpha.md": b"# Prior alpha\n",
            "records/topics/beta.md": b"# Last verified beta\n",
            **protected,
        },
        staged_files=denied_staged_protected,
        content_files={},
        operational_files={},
    )
    denied_preservation["publications"] = []
    denied_preservation_result = preservation.check_preservation(denied_preservation)

    assert (denied_snapshot["root"] / "records/topics/beta.md").read_bytes() == (
        b"# Last verified beta\n")
    assert denied_receipt["status"] == "incomplete"
    assert not denied_receipt["current_state_complete"]
    assert denied_preservation_result["status"] == "staged_preserved"
    assert denied_receipt["destination_preservation"]["status"] == (
        denied_preservation_result["status"])
    assert "Not repeated" in denied_receipt["restore_test"]

    missing_excluded = fixtures.preservation_packet(
        protected_roots=[exclusion],
        baseline_files={
            "records/topics/alpha.md": b"# Prior alpha\n",
            "records/topics/beta.md": b"# Last verified beta\n",
            **protected,
        },
        staged_files={},
        content_files={},
        operational_files={},
    )
    missing_excluded["publications"] = []
    with pytest.raises(preservation.PreservationError,
                       match="protected destination changed at staging"):
        preservation.check_preservation(missing_excluded)

    changed_excluded_packet = fixtures.preservation_packet(
        protected_roots=[exclusion],
        baseline_files={
            "records/topics/alpha.md": b"# Prior alpha\n",
            "records/topics/beta.md": b"# Last verified beta\n",
            **protected,
        },
        staged_files={
            f"{exclusion}/ledger.json": b"changed synthetic external ledger\n",
        },
        content_files={},
        operational_files={},
    )
    changed_excluded_packet["publications"] = []
    with pytest.raises(preservation.PreservationError,
                       match="protected destination changed at staging"):
        preservation.check_preservation(changed_excluded_packet)


def test_historical_snapshot_uses_its_own_packet_then_manual_run_reloads_current_profile(tmp_path):
    historical_exclusions = ["archive/old-independent"]
    historical_profile = fixtures.profile_bytes(historical_exclusions)
    historical = fixtures.write_snapshot(
        tmp_path / "historical-snapshot",
        exclusions=historical_exclusions,
        profile=historical_profile,
        managed_records={"records/topics/current.md": (
            "synthetic-current-topic", b"# Historical synthetic topic\n")},
        protected_files={
            "archive/old-independent/prior.txt": b"historical independent data\n",
        },
    )
    historical_manifest_before = historical["manifest_path"].read_bytes()
    assert validate(historical)["record_count"] == 2

    current_exclusions = ["independent/currently-managed"]
    current_profile = fixtures.profile_bytes(current_exclusions)
    current = fixtures.write_snapshot(
        tmp_path / "current-manual-run",
        exclusions=current_exclusions,
        profile=current_profile,
        managed_records={"records/topics/current.md": (
            "synthetic-current-topic", b"# Current synthetic topic\n")},
        protected_files={
            "independent/currently-managed/current.txt": b"current independent data\n",
        },
    )
    with pytest.raises(validator.SnapshotError, match="staged profile bytes differ"):
        validator.validate(
            historical["root"],
            historical["manifest_path"],
            destination_policy=current["policy"],
            policy_expectations=current["expectations"],
        )

    assert validate(current)["record_count"] == 2
    assert historical["manifest_path"].read_bytes() == historical_manifest_before
    assert historical["manifest"]["capture_policy"]["exclusions"] == historical_exclusions
    assert current["manifest"]["capture_policy"]["exclusions"] == current_exclusions
    assert current["profile_read"]["sha256"] == current["policy"]["profile"]["sha256"]
