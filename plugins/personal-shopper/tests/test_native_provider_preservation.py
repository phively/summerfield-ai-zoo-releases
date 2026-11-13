from __future__ import annotations

import importlib.util
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "shopping"
sys.path.insert(0, str(EVAL))
import check_native  # noqa: E402
import private_evidence  # noqa: E402


def test_private_capture_supports_native_windows_acl_and_posix_modes(tmp_path):
    path = tmp_path / "private.json"
    path.write_text("{}", encoding="utf-8")
    if os.name != "nt":
        tmp_path.chmod(0o700)
        path.chmod(0o600)
    assert check_native._private_file(path)
    assert check_native._private_capture(tmp_path)


def test_windows_acl_rejects_shared_or_unowned_evidence():
    owner = "S-1-5-21-1-2-3-1001"
    acl = {"current_sid": owner, "owner_sid": owner, "rules": [
        {"sid": owner, "type": "Allow"}, {"sid": "S-1-5-18", "type": "Allow"},
    ]}
    assert check_native._acl_is_private(acl)
    owner_rights = copy.deepcopy(acl)
    owner_rights["rules"][0]["sid"] = "S-1-3-4"
    assert check_native._acl_is_private(owner_rights)
    assert not check_native._acl_is_private({**owner_rights, "owner_sid": "S-1-5-21-9"})
    administrators = copy.deepcopy(acl)
    administrators["rules"].append({"sid": "S-1-5-32-544", "type": "Allow"})
    assert check_native._acl_is_private(administrators)
    shared = copy.deepcopy(acl)
    shared["rules"].append({"sid": "S-1-1-0", "type": "Allow"})
    assert not check_native._acl_is_private(shared)
    assert not check_native._acl_is_private({**acl, "owner_sid": "S-1-5-21-9"})
    assert not check_native._acl_is_private({**acl, "rules": []})
    assert not check_native._acl_is_private(None)


def test_native_and_browser_validation_share_the_private_evidence_policy():
    assert check_native._acl_is_private is private_evidence.acl_is_private
    assert check_native._private_permissions is private_evidence.private_permissions
    assert check_native._private_file is private_evidence.private_file


def test_installed_resource_reader_and_capture_reject_changed_or_escaped_files(tmp_path, monkeypatch):
    import skill_resources

    relative = "references/contracts/record-management.md"
    source = tmp_path / "plugins/personal-shopper/skills/personal-shopper" / relative
    source.parent.mkdir(parents=True)
    source.write_bytes(b"contract bytes\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    control = {"installed_skill_root": str(source.parents[2]), "files": {relative: digest}}
    payload = skill_resources.read_resource(control, {"relative_path": relative})
    call = {"server": "shopping-skill-resources", "tool": "read_installed_skill_file",
            "arguments": {"relative_path": relative}, "result": {
                "content": [{"type": "text", "text": json.dumps(payload)}]}}
    trial = {"installed_file_sha256": {"personal-shopper/skills/personal-shopper/" + relative: digest}}
    monkeypatch.setattr(check_native, "REPO_ROOT", tmp_path)
    assert check_native._skill_resource(call, trial) == relative
    altered = copy.deepcopy(call)
    altered["result"]["content"][0]["text"] = json.dumps({**payload, "text": "invented"})
    assert check_native._skill_resource(altered, trial) is None
    wrong = copy.deepcopy(call)
    wrong["server"] = "another-resource-server"
    assert check_native._skill_resource(wrong, trial) is None
    for path in ("../secret.md", "/secret.md", "references/../secret.md", "references\\secret.md"):
        with pytest.raises(ValueError):
            skill_resources.read_resource(control, {"relative_path": path})
    source.write_bytes(b"modified after installation\n")
    with pytest.raises(ValueError, match="changed"):
        skill_resources.read_resource(control, {"relative_path": relative})
    assert check_native._skill_resource(call, trial) is None


def test_installed_resource_reader_stdio_protocol_uses_real_installed_bytes(tmp_path):
    import subprocess
    import skill_resources

    raw = b"# Installed skill\n"
    (tmp_path / "SKILL.md").write_bytes(raw)
    control = {"installed_skill_root": str(tmp_path),
               "files": {"SKILL.md": hashlib.sha256(raw).hexdigest()}}
    config = tmp_path / "control.json"
    config.write_text(json.dumps(control))
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": skill_resources.TOOL, "arguments": {"relative_path": "SKILL.md"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
            "name": skill_resources.TOOL, "arguments": {"relative_path": "../secret.md"}}},
    ]
    result = subprocess.run([sys.executable, str(EVAL / "skill_resources.py"), str(config)],
                            input="".join(json.dumps(r) + "\n" for r in requests),
                            capture_output=True, text=True, check=True, timeout=10)
    responses = [json.loads(line)["result"] for line in result.stdout.splitlines()]
    assert responses[1]["tools"][0]["annotations"]["readOnlyHint"] is True
    assert responses[2]["structuredContent"]["text"].encode() == raw
    assert responses[3]["isError"] is True


@pytest.mark.shopping_native
def test_native_provider_preservation(request):
    capture_path = request.config.getoption("--shopping-native-capture")
    config_path = request.config.getoption("--shopping-native-config")
    required = request.config.getoption("--require-shopping-native")
    if not capture_path and not config_path and not required:
        pytest.skip("B12 NOT RUN: private disposable-workbook config and activated-skill capture were not supplied")
    if not capture_path or not config_path:
        pytest.fail("B12 BLOCKED: required native mode needs private config and same-run host capture")
    result = check_native.validate_capture(capture_path, config_path)
    if not result["accepted"]:
        pytest.fail("B12 NOT ACCEPTED (" + result["status"] + "): " + ", ".join(result["issues"]))
    assert result["status"] == "accepted"


def test_authorized_update_is_one_cell_and_preserves_validation():
    expected = {
        "native_id": "A" * 32,
        "target": {"sheet_id": 22, "row_index": 1, "column_index": 2, "after_value": "tea bags"},
    }
    call = {"arguments": {
        "spreadsheet_id": "A" * 32,
        "requests": [{"updateCells": {
            "range": {"sheetId": 22, "startRowIndex": 1, "endRowIndex": 2,
                      "startColumnIndex": 2, "endColumnIndex": 3},
            "rows": [{"values": [{"userEnteredValue": {"stringValue": "tea bags"}}]}],
            "fields": "userEnteredValue",
        }}],
    }, "status": "completed", "error": None}
    assert check_native._valid_update(call, expected)


def test_authorized_update_rejects_other_resource_or_cell():
    expected = {
        "native_id": "A" * 32,
        "target": {"sheet_id": 22, "row_index": 1, "column_index": 2, "after_value": "tea bags"},
    }
    call = {"arguments": {
        "spreadsheet_id": "B" * 32,
        "requests": [{"updateCells": {
            "range": {"sheetId": 22, "startRowIndex": 1, "endRowIndex": 2,
                      "startColumnIndex": 2, "endColumnIndex": 3},
            "rows": [{"values": [{"userEnteredValue": {"stringValue": "tea bags"}}]}],
            "fields": "userEnteredValue",
        }}],
    }, "status": "completed", "error": None}
    assert not check_native._valid_update(call, expected)
    call["arguments"]["spreadsheet_id"] = "A" * 32
    call["arguments"]["requests"][0]["updateCells"]["range"]["startColumnIndex"] = 3
    assert not check_native._valid_update(call, expected)


def test_failed_write_cannot_satisfy_native_preservation():
    expected = {
        "native_id": "A" * 32,
        "target": {"sheet_id": 22, "row_index": 1, "column_index": 2, "after_value": "tea bags"},
    }
    call = {
        "arguments": {
            "spreadsheet_id": "A" * 32,
            "requests": [{"updateCells": {
                "range": {"sheetId": 22, "startRowIndex": 1, "endRowIndex": 2,
                              "startColumnIndex": 2, "endColumnIndex": 3},
                "rows": [{"values": [{"userEnteredValue": {"stringValue": "tea bags"}}]}],
                "fields": "userEnteredValue",
            }}],
        },
        "status": "failed",
        "error": {"message": "approval required"},
    }
    assert not check_native._valid_update(call, expected)


def test_bounded_a1_ranges_require_explicit_tab_and_bounds():
    assert check_native._a1_range("'Shopper Preferences'!A1:E2") == ("Shopper Preferences", 0, 2, 0, 5)
    assert check_native._a1_range("A:A") is None
    assert check_native._a1_range("'Shopper Preferences'!A1") is None


def test_sheet_title_normalizes_provider_quoted_tab_names():
    assert check_native._sheet_title("'Record Index'") == "Record Index"
    assert check_native._sheet_title('"Record Index"') == "Record Index"
    assert check_native._sheet_title("Record Index") == "Record Index"
    assert check_native._sheet_title(None) is None
