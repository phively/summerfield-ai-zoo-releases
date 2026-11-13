from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "shopping"
sys.path.insert(0, str(EVAL))
import check_native  # noqa: E402
import capture_work_browser  # noqa: E402


def one_cell_request(spreadsheet_id: str = "A" * 32) -> dict:
    return {
        "spreadsheet_id": spreadsheet_id,
        "requests": [{"updateCells": {
            "range": {"sheetId": 7, "startRowIndex": 1, "endRowIndex": 2,
                      "startColumnIndex": 2, "endColumnIndex": 3},
            "rows": [{"values": [{"userEnteredValue": {"stringValue": "Market B"}}]}],
            "fields": "userEnteredValue",
        }}],
    }


def work_dom(request: dict) -> str:
    encoded_json = json.dumps(request, separators=(",", ":"))
    return "\n".join([
        'region "Conversation":',
        '  button "Used Google Drive":',
        '  text: skill://Plugin_abc123/personal-shopper/SKILL.md',
        '  text: shopper@example.com',
        '  text: Retrieving Google Sheets Metadata',
        '  text: Reading Shopper Preferences and Change History cells',
        '  text: Updating spreadsheet cell with market label',
        '  text: Before editing, the native read showed C2=Market A',
        '  text: Actual provider write request:',
        "  - code: " + json.dumps(encoded_json),
        '  text: The provider returned isError: false and replies: [{}].',
        '  text: A fresh cell read confirmed C2=Market B and preserved the formula, validation, and history.',
        '  text: No canonical Grocery spreadsheet or other personal authority was accessed.',
    ])


def metadata(request: dict) -> dict:
    history = ["TEST-B12-001", "Market A", "Initial fixture", "Synthetic B12 test data", "2026-10-25"]
    formula = '=IF(C2="","Unset","Set")'
    validation = {"strict": True, "allowed_values": ["Market A", "Market B"]}
    common = {
        "formula_neighbor": "Shopper Preferences!D2",
        "formula": formula,
        "formula_result": "Set",
        "validation": validation,
        "history_row": history,
    }
    return {
        "run_id": "shopping-b12-browser-test",
        "host": "ChatGPT Work in-app browser",
        "model": "GPT-6 Luna",
        "reasoning_effort": "Extra High",
        "plugin_id": "Plugin_abc123",
        "plugin_name": "personal-shopper",
        "plugin_manifest_version": "1.0.0",
        "skill_id": "personal-shopper:personal-shopper",
        "skill_resource_uri": "skill://Plugin_abc123/personal-shopper/SKILL.md",
        "provider_plugin": "Google Drive",
        "provider_identity": "shopper@example.com",
        "candidate_zip_sha256": "",
        "provider_write_request": request,
        "provider_write_result_as_displayed": {"isError": False, "replies": [{}]},
        "before": {"cell": "Shopper Preferences!C2", "value": "Market A", **common},
        "after": {"cell": "Shopper Preferences!C2", "value": "Market B",
                  "key": "TEST-B12-001", **common},
    }


def native_ui_review(spreadsheet_id: str) -> dict:
    history = ["TEST-B12-001", "Market A", "Initial fixture", "Synthetic B12 test data", "2026-10-25"]
    formula = '=IF(C2="","Unset","Set")'
    return {
        "schema_version": 1,
        "evidence_kind": "native-google-sheets-ui-observation",
        "observer": "Codex visual review",
        "source": "Google Sheets in ChatGPT in-app browser",
        "account": "shopper@example.com",
        "workbook_id": spreadsheet_id,
        "workbook_title": "Personal Shopper B12 Disposable Test 2026-10-25",
        "saved_status": "Saved to Drive",
        "previous_revision": {
            "displayed": "October 25, 11:01 AM", "sheet_id": 7, "sheet": "Shopper Preferences",
            "target_a1": "C2", "target_value": "Market A", "stable_key_cell": "A2",
            "stable_key": "TEST-B12-001", "formula_cell": "D2", "formula": formula,
            "formula_result": "Set",
        },
        "current_revision": {
            "displayed": "October 26, 9:46 AM", "is_current": True, "edits_in_revision": 1,
            "write_count": 1, "changed_cell": "Shopper Preferences!C2", "sheet_id": 7,
            "sheet": "Shopper Preferences", "target_a1": "C2", "target_value": "Market B",
            "stable_key_cell": "A2", "stable_key": "TEST-B12-001", "formula_cell": "D2",
            "formula": formula, "formula_result": "Set",
        },
        "validation": {
            "range": "Shopper Preferences!C2", "criteria": "Dropdown",
            "allowed_values": ["Market A", "Market B"], "invalid_input": "Reject the input",
        },
        "history": {
            "range": "Change History!A2:E2", "prior_values": history, "current_values": history,
        },
        "acceptance_review": {
            "result": "pass", "read_source_identity_confirmed": True,
            "prior_revision_before_value_confirmed": True, "saved_source_readback_confirmed": True,
        },
    }


def browser_config(request: dict | None = None) -> dict:
    request = request or one_cell_request()
    history = ["TEST-B12-001", "Market A", "Initial fixture", "Synthetic B12 test data", "2026-10-25"]
    formula = '=IF(C2="","Unset","Set")'
    return {
        "schema_version": 1,
        "expected_resource": {"provider": "google-sheets", "native_id": request["spreadsheet_id"]},
        "target": {
            "sheet_id": 7, "row_index": 1, "column_index": 2,
            "before_value": "Market A", "after_value": "Market B",
        },
        "browser_expectations": {
            "target": {
                "sheet_id": 7, "sheet": "Shopper Preferences", "a1": "C2",
                "before_value": "Market A", "after_value": "Market B",
                "stable_key_cell": "A2", "stable_key": "TEST-B12-001",
            },
            "formula": {"cell": "D2", "value": formula, "result": "Set"},
            "validation": {
                "range": "Shopper Preferences!C2", "criteria": "Dropdown",
                "allowed_values": ["Market A", "Market B"],
                "invalid_input": "Reject the input", "strict": True,
            },
            "history": {"range": "Change History!A2:E2", "values": history},
        },
    }


def write_private_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    path.chmod(0o600)
    return path


def capture_inputs(capture_dir: Path, request: dict | None = None) -> tuple[Path, Path, Path, Path]:
    capture_dir.mkdir(mode=0o700)
    os.chmod(capture_dir, 0o700)
    request = request or one_cell_request()
    conversation = capture_dir / "work-conversation-dom.txt"
    conversation.write_text(work_dom(request), encoding="utf-8")
    candidate = capture_dir / "candidate.zip"
    candidate.write_bytes(b"plugin package")
    run = metadata(request)
    run["candidate_zip_sha256"] = hashlib.sha256(candidate.read_bytes()).hexdigest()
    run_path = capture_dir / "run-evidence.json"
    run_path.write_text(json.dumps(run), encoding="utf-8")
    screenshot = capture_dir / "work-result.png"
    screenshot.write_bytes(b"visible Work result screenshot")
    review_path = capture_dir / capture_work_browser.NATIVE_UI_REVIEW_NAME
    review_path.write_text(json.dumps(native_ui_review(request["spreadsheet_id"])), encoding="utf-8")
    for artifact in capture_dir.iterdir():
        os.chmod(artifact, 0o600)
    return conversation, run_path, screenshot, candidate


def test_browser_source_review_accepts_without_per_call_ids_or_timestamps(tmp_path):
    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    review_path = capture_dir / capture_work_browser.NATIVE_UI_REVIEW_NAME
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review.pop("observed_at_utc", None)
    review_path.write_text(json.dumps(review), encoding="utf-8")

    record = capture_work_browser.archive_capture(
        conversation, run_path, screenshot, candidate, capture_dir
    )

    assert record["acceptance"]["status"] == "accepted"
    assert record["native_tool_trace"]["available"] is False
    assert record["acceptance_basis"].startswith("visible single-cell provider request/result")
    assert not (capture_dir / "host-events.jsonl").exists()
    assert capture_work_browser.validate_archived_capture(capture_dir, browser_config()) == {
        "accepted": True, "status": "accepted", "issues": [],
    }


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode-bit assertion")
def test_browser_capture_secures_new_directory_and_sidecar_before_payload(tmp_path):
    source_dir = tmp_path / "source"
    conversation, run_path, screenshot, candidate = capture_inputs(source_dir)
    output = tmp_path / "nested" / "private-output"
    previous_umask = os.umask(0)
    try:
        capture_work_browser.archive_capture(
            conversation, run_path, screenshot, candidate, output
        )
    finally:
        os.umask(previous_umask)

    sidecar = output / capture_work_browser.CAPTURE_NAME
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600
    assert json.loads(sidecar.read_text(encoding="utf-8"))["acceptance"]["status"] == "accepted"


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode-bit assertion")
def test_browser_capture_rejects_insecure_existing_output_without_repair(tmp_path):
    source_dir = tmp_path / "source"
    conversation, run_path, screenshot, candidate = capture_inputs(source_dir)
    output = tmp_path / "insecure-output"
    output.mkdir(mode=0o755)
    output.chmod(0o755)

    with pytest.raises(ValueError, match="private"):
        capture_work_browser.archive_capture(
            conversation, run_path, screenshot, candidate, output
        )

    assert stat.S_IMODE(output.stat().st_mode) == 0o755
    assert not (output / capture_work_browser.CAPTURE_NAME).exists()


def test_browser_capture_acl_setup_failure_writes_no_sidecar(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    conversation, run_path, screenshot, candidate = capture_inputs(source_dir)
    output = tmp_path / "windows-policy-output"
    policy = capture_work_browser.private_evidence
    monkeypatch.setattr(policy, "_is_windows", lambda: True)
    monkeypatch.setattr(policy, "_set_windows_permissions", lambda _path: False)

    with pytest.raises(PermissionError, match="private permissions"):
        capture_work_browser.archive_capture(
            conversation, run_path, screenshot, candidate, output
        )

    assert not (output / capture_work_browser.CAPTURE_NAME).exists()


def test_browser_capture_verifies_windows_permissions_before_directory_and_file_writes(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    conversation, run_path, screenshot, candidate = capture_inputs(source_dir)
    output = tmp_path / "windows-policy-output"
    policy = capture_work_browser.private_evidence
    protected = []
    monkeypatch.setattr(policy, "_is_windows", lambda: True)
    monkeypatch.setattr(policy, "_set_windows_permissions", lambda path: protected.append(path) or True)
    monkeypatch.setattr(policy, "private_permissions", lambda _path: True)

    capture_work_browser.archive_capture(conversation, run_path, screenshot, candidate, output)

    assert protected == [output, output / capture_work_browser.CAPTURE_NAME]
    assert json.loads((output / capture_work_browser.CAPTURE_NAME).read_text(encoding="utf-8"))[
        "acceptance"]["status"
    ] == "accepted"


def test_browser_capture_file_acl_failure_leaves_no_sidecar_payload(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    conversation, run_path, screenshot, candidate = capture_inputs(source_dir)
    output = tmp_path / "windows-policy-output"
    policy = capture_work_browser.private_evidence
    monkeypatch.setattr(policy, "_is_windows", lambda: True)
    monkeypatch.setattr(policy, "private_permissions", lambda _path: True)
    monkeypatch.setattr(
        policy,
        "_set_windows_permissions",
        lambda path: path == output,
    )

    with pytest.raises(PermissionError, match="private permissions"):
        capture_work_browser.archive_capture(
            conversation, run_path, screenshot, candidate, output
        )

    assert list(output.iterdir()) == []


def test_browser_payload_is_written_after_directory_and_sidecar_permissions_verify(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    conversation, run_path, screenshot, candidate = capture_inputs(source_dir)
    output = tmp_path / "windows-policy-output"
    sidecar = output / capture_work_browser.CAPTURE_NAME
    policy = capture_work_browser.private_evidence
    owner = "S-1-5-21-1234"
    acl = {
        "current_sid": owner,
        "owner_sid": owner,
        "rules": [
            {"sid": owner, "type": "Allow"},
            {"sid": "S-1-5-18", "type": "Allow"},
            {"sid": "S-1-5-32-544", "type": "Allow"},
        ],
    }
    verified = set()
    writes = []
    monkeypatch.setattr(policy, "_is_windows", lambda: True)
    monkeypatch.setattr(policy, "_set_windows_permissions", lambda _path: True)

    def acl_for(path):
        verified.add(Path(path).absolute())
        return acl

    monkeypatch.setattr(policy, "_windows_acl", acl_for)
    real_fdopen = policy.os.fdopen

    class GuardedStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def write(self, payload):
            if payload:
                writes.append(payload)
                assert output.absolute() in verified
                assert sidecar.absolute() in verified
            return self.stream.write(payload)

        def __getattr__(self, name):
            return getattr(self.stream, name)

    monkeypatch.setattr(policy.os, "fdopen", lambda fd, *args, **kwargs: GuardedStream(
        real_fdopen(fd, *args, **kwargs)
    ))

    capture_work_browser.archive_capture(
        conversation, run_path, screenshot, candidate, output
    )

    assert writes
    assert output.absolute() in verified and sidecar.absolute() in verified


def test_browser_permission_failure_attempts_zero_payload_writes(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    conversation, run_path, screenshot, candidate = capture_inputs(source_dir)
    output = tmp_path / "windows-policy-output"
    policy = capture_work_browser.private_evidence
    writes = []
    monkeypatch.setattr(policy, "_is_windows", lambda: True)
    monkeypatch.setattr(policy, "_set_windows_permissions", lambda path: path == output)
    real_fdopen = policy.os.fdopen

    class GuardedStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def write(self, payload):
            if payload:
                writes.append(payload)
            return self.stream.write(payload)

        def __getattr__(self, name):
            return getattr(self.stream, name)

    monkeypatch.setattr(policy, "private_permissions", lambda _path: True)
    monkeypatch.setattr(policy.os, "fdopen", lambda fd, *args, **kwargs: GuardedStream(
        real_fdopen(fd, *args, **kwargs)
    ))

    with pytest.raises(PermissionError, match="private permissions"):
        capture_work_browser.archive_capture(
            conversation, run_path, screenshot, candidate, output
        )

    assert writes == []
    assert list(output.iterdir()) == []


def test_browser_capture_refuses_preexisting_sidecar_without_rewriting_it(tmp_path):
    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    sidecar = capture_dir / capture_work_browser.CAPTURE_NAME
    sidecar.write_text("preserve this file", encoding="utf-8")
    os.chmod(sidecar, 0o600)

    with pytest.raises(ValueError, match="already exists"):
        capture_work_browser.archive_capture(
            conversation, run_path, screenshot, candidate, capture_dir
        )

    assert sidecar.read_text(encoding="utf-8") == "preserve this file"


@pytest.mark.skipif(os.name == "nt", reason="Windows symlink privileges vary")
def test_browser_capture_refuses_sidecar_symlink_without_touching_target(tmp_path):
    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    target = tmp_path / "preserved-target.txt"
    target.write_text("keep this file", encoding="utf-8")
    sidecar = capture_dir / capture_work_browser.CAPTURE_NAME
    sidecar.symlink_to(target)

    with pytest.raises(ValueError, match="already exists"):
        capture_work_browser.archive_capture(
            conversation, run_path, screenshot, candidate, capture_dir
        )

    assert target.read_text(encoding="utf-8") == "keep this file"


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode-bit assertion")
def test_browser_validator_rejects_archived_capture_after_permissions_widen(tmp_path):
    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    capture_work_browser.archive_capture(conversation, run_path, screenshot, candidate, capture_dir)
    capture_dir.chmod(0o755)

    assert capture_work_browser.validate_archived_capture(capture_dir, browser_config()) == {
        "accepted": False, "status": "blocked", "issues": ["browser_capture_invalid"],
    }


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode-bit assertion")
def test_browser_validator_rejects_readable_sidecar(tmp_path):
    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    capture_work_browser.archive_capture(conversation, run_path, screenshot, candidate, capture_dir)
    (capture_dir / capture_work_browser.CAPTURE_NAME).chmod(0o644)

    assert capture_work_browser.validate_archived_capture(capture_dir, browser_config()) == {
        "accepted": False, "status": "blocked", "issues": ["browser_capture_invalid"],
    }


def test_native_checker_accepts_reviewed_browser_evidence_without_cli_conversion(tmp_path, monkeypatch):
    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    capture_work_browser.archive_capture(conversation, run_path, screenshot, candidate, capture_dir)
    monkeypatch.setattr(check_native, "_private_capture", lambda _path: True)
    config_path = write_private_json(capture_dir / "native-config.json", browser_config())

    result = check_native.validate_capture(capture_dir, config_path)

    assert result == {"accepted": True, "status": "accepted", "issues": []}
    assert not (capture_dir / "host-events.jsonl").exists()


def test_native_checker_requires_private_config_for_archived_browser_evidence(tmp_path, monkeypatch):
    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    capture_work_browser.archive_capture(conversation, run_path, screenshot, candidate, capture_dir)
    monkeypatch.setattr(check_native, "_private_capture", lambda _path: True)

    result = check_native.validate_capture(capture_dir, tmp_path / "missing-config.json")

    assert result == {"accepted": False, "status": "blocked", "issues": ["private_config_missing"]}


@pytest.mark.parametrize(("mismatch", "issue"), [
    ("workbook", "browser_expected_workbook_mismatch"),
    ("target", "browser_expected_target_mismatch"),
    ("state", "browser_expected_state_mismatch"),
])
def test_native_checker_binds_archived_browser_evidence_to_private_expectations(
    tmp_path, monkeypatch, mismatch, issue
):
    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    capture_work_browser.archive_capture(conversation, run_path, screenshot, candidate, capture_dir)
    monkeypatch.setattr(check_native, "_private_capture", lambda _path: True)
    config = browser_config()
    if mismatch == "workbook":
        config["expected_resource"]["native_id"] = "B" * 32
    elif mismatch == "target":
        config["browser_expectations"]["target"]["a1"] = "D2"
    else:
        config["browser_expectations"]["target"]["after_value"] = "Market C"
    config_path = write_private_json(capture_dir / "native-config.json", config)

    result = check_native.validate_capture(capture_dir, config_path)

    assert result["accepted"] is False
    assert result["status"] == "blocked"
    assert issue in result["issues"]


def test_noop_browser_write_is_blocked_even_when_source_evidence_reconciles(tmp_path):
    capture_dir = tmp_path / "private-capture"
    request = one_cell_request()
    request["requests"][0]["updateCells"]["rows"][0]["values"][0]["userEnteredValue"][
        "stringValue"
    ] = "Market A"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir, request)
    conversation.write_text(
        conversation.read_text(encoding="utf-8").replace("C2=Market B", "C2=Market A"),
        encoding="utf-8",
    )
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["after"]["value"] = "Market A"
    run_path.write_text(json.dumps(run), encoding="utf-8")
    review_path = capture_dir / capture_work_browser.NATIVE_UI_REVIEW_NAME
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["current_revision"]["target_value"] = "Market A"
    review_path.write_text(json.dumps(review), encoding="utf-8")

    capture_work_browser.archive_capture(conversation, run_path, screenshot, candidate, capture_dir)

    result = capture_work_browser.validate_archived_capture(capture_dir, browser_config())
    assert result["accepted"] is False
    assert result["status"] == "blocked"
    assert result["issues"] == ["browser_native_target_not_changed"]


@pytest.mark.parametrize(("field", "value", "issue"), [
    ("target_value", "Market A", "browser_native_target_reconciliation_failed"),
    ("formula", "=1+1", "browser_neighbor_formula_not_preserved"),
])
def test_native_source_mismatch_blocks_browser_acceptance(tmp_path, field, value, issue):
    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    review_path = capture_dir / capture_work_browser.NATIVE_UI_REVIEW_NAME
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["current_revision"][field] = value
    review_path.write_text(json.dumps(review), encoding="utf-8")

    capture_work_browser.archive_capture(conversation, run_path, screenshot, candidate, capture_dir)

    result = capture_work_browser.validate_archived_capture(capture_dir, browser_config())
    assert result["accepted"] is False
    assert issue in result["issues"]


@pytest.mark.parametrize(("section", "field", "value", "issue"), [
    ("validation", "allowed_values", ["unexpected option"], "browser_validation_not_preserved"),
    ("history", "prior_values", ["damaged prior row"], "browser_history_not_preserved"),
    ("current_revision", "stable_key", "OTHER-KEY", "browser_stable_key_not_preserved"),
])
def test_native_validation_history_and_stable_key_mismatches_block_acceptance(
    tmp_path, section, field, value, issue
):
    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    review_path = capture_dir / capture_work_browser.NATIVE_UI_REVIEW_NAME
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review[section][field] = value
    review_path.write_text(json.dumps(review), encoding="utf-8")

    capture_work_browser.archive_capture(conversation, run_path, screenshot, candidate, capture_dir)

    result = capture_work_browser.validate_archived_capture(capture_dir, browser_config())
    assert result["accepted"] is False
    assert result["status"] == "blocked"
    assert issue in result["issues"]


def test_capture_detects_tampering_and_keeps_source_observation_separate(tmp_path):
    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    capture_work_browser.archive_capture(conversation, run_path, screenshot, candidate, capture_dir)
    conversation.write_text(conversation.read_text(encoding="utf-8") + " edited", encoding="utf-8")

    result = capture_work_browser.validate_archived_capture(capture_dir, browser_config())

    assert result == {"accepted": False, "status": "blocked", "issues": ["browser_capture_invalid"]}
    assert not (capture_dir / "host-events.jsonl").exists()


def test_multi_cell_payload_and_candidate_digest_mismatch_are_rejected(tmp_path):
    request = one_cell_request()
    update = request["requests"][0]["updateCells"]
    update["range"]["endColumnIndex"] = 4
    update["rows"][0]["values"].append({"userEnteredValue": {"stringValue": "extra"}})
    with pytest.raises(ValueError, match="single-cell"):
        capture_work_browser.parse_visible_conversation(work_dom(request))

    capture_dir = tmp_path / "private-capture"
    conversation, run_path, screenshot, candidate = capture_inputs(capture_dir)
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["candidate_zip_sha256"] = "0" * 64
    run_path.write_text(json.dumps(run), encoding="utf-8")

    with pytest.raises(ValueError, match="candidate archive digest"):
        capture_work_browser.archive_capture(conversation, run_path, screenshot, candidate, capture_dir)
