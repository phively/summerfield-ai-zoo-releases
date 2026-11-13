#!/usr/bin/env python3
"""Reconcile ChatGPT Work evidence with a direct native Sheets review.

Work does not expose its complete provider-call ledger. This adapter preserves
the original Work conversation and write payload, then uses a separate direct
Google Sheets UI review of the saved source and prior revision to check the
state assertions. It never creates Codex CLI events. Per-call IDs and timestamps
are not acceptance requirements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

import private_evidence


REPO_ROOT = Path(__file__).resolve().parents[4]
CAPTURE_NAME = "work-browser-capture.json"
NATIVE_UI_REVIEW_NAME = "native-ui-review.json"
CAPTURE_FORMAT = "chatgpt-work-browser-source-ui/v2"
RESOURCE_PATTERN = re.compile(r"skill://(Plugin_[A-Za-z0-9]+)/personal-shopper/SKILL\.md")
CODE_LINE_PATTERN = re.compile(r'(?m)^\s*- code: ("(?:\\.|[^"\\])*")\s*$')
REQUIRED_ACTIVITY_LABELS = (
    "Retrieving Google Sheets Metadata",
    "Reading Shopper Preferences and Change History cells",
    "Updating spreadsheet cell with market label",
)
BLOCKED_ISSUES = ["browser_native_source_observation_missing"]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _private_path(path: Path) -> Path:
    if private_evidence.path_has_link(path):
        raise ValueError("browser evidence must not use a symlink or junction")
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError("browser evidence must be stored outside the source checkout")


def _visible_write_request(snapshot: str) -> dict[str, Any]:
    marker = snapshot.find("Actual provider write request:")
    if marker < 0:
        raise ValueError("visible provider write request is missing")
    match = CODE_LINE_PATTERN.search(snapshot, marker)
    if not match:
        raise ValueError("visible provider write payload is missing")
    encoded = json.loads(match.group(1))
    if not isinstance(encoded, str):
        raise ValueError("visible provider write payload is malformed")
    request = json.loads(encoded)
    if not isinstance(request, dict):
        raise ValueError("visible provider write payload is malformed")
    return request


def _single_cell_write(request: Any) -> bool:
    if not isinstance(request, dict) or not isinstance(request.get("spreadsheet_id"), str):
        return False
    requests = request.get("requests")
    if not isinstance(requests, list) or len(requests) != 1 or not isinstance(requests[0], dict):
        return False
    if set(requests[0]) != {"updateCells"}:
        return False
    update = requests[0]["updateCells"]
    grid = update.get("range") if isinstance(update, dict) else None
    rows = update.get("rows") if isinstance(update, dict) else None
    if not isinstance(grid, dict) or not isinstance(rows, list) or len(rows) != 1:
        return False
    coordinates = [grid.get(name) for name in (
        "startRowIndex", "endRowIndex", "startColumnIndex", "endColumnIndex", "sheetId")
    ]
    if any(type(value) is not int for value in coordinates):
        return False
    if grid.get("endRowIndex") != grid.get("startRowIndex", -1) + 1 \
            or grid.get("endColumnIndex") != grid.get("startColumnIndex", -1) + 1:
        return False
    row = rows[0]
    values = row.get("values") if isinstance(row, dict) else None
    return bool(
        isinstance(values, list)
        and len(values) == 1
        and isinstance(values[0], dict)
        and set(values[0]) == {"userEnteredValue"}
        and isinstance(values[0]["userEnteredValue"], dict)
        and set(values[0]["userEnteredValue"]) == {"stringValue"}
        and update.get("fields") == "userEnteredValue"
    )


def _column_label(index: int) -> str:
    label = ""
    value = index + 1
    while value:
        value, remainder = divmod(value - 1, 26)
        label = chr(65 + remainder) + label
    return label


def _write_cell(request: dict[str, Any]) -> tuple[int, str]:
    update = request["requests"][0]["updateCells"]
    grid = update["range"]
    a1 = f"{_column_label(grid['startColumnIndex'])}{grid['startRowIndex'] + 1}"
    value = update["rows"][0]["values"][0]["userEnteredValue"]["stringValue"]
    return grid["sheetId"], a1


def parse_visible_conversation(snapshot: str) -> dict[str, Any]:
    """Extract visible host facts while keeping them distinct from raw events."""
    if not isinstance(snapshot, str) or 'region "Conversation":' not in snapshot:
        raise ValueError("browser conversation snapshot is missing")
    resource = RESOURCE_PATTERN.search(snapshot)
    request = _visible_write_request(snapshot)
    if not _single_cell_write(request):
        raise ValueError("visible provider write is not a single-cell update")
    return {
        "skill_resource_uri": resource.group(0) if resource else None,
        "plugin_id": resource.group(1) if resource else None,
        "google_drive_use_badges": len(re.findall(r"Used[^\n]*Google Drive", snapshot)),
        "activity_labels": [label for label in REQUIRED_ACTIVITY_LABELS if label in snapshot],
        "visible_write_request": request,
        "visible_write_result_present": "isError: false" in snapshot and "replies: [{}]" in snapshot,
        "visible_before_read_present": "before editing, the native read showed" in snapshot.lower(),
        "visible_readback_present": "fresh cell read confirmed" in snapshot.lower(),
        "visible_no_other_authority_claim": "no canonical grocery spreadsheet or other personal authority" in snapshot.lower(),
        "raw_native_tool_events_present": False,
    }


def _browser_expectations(config: Any) -> dict[str, Any] | None:
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        return None
    resource = config.get("expected_resource")
    expected = config.get("browser_expectations")
    if not isinstance(resource, dict) or resource.get("provider") != "google-sheets" \
            or not isinstance(resource.get("native_id"), str) or not resource["native_id"] \
            or not isinstance(expected, dict):
        return None
    target = expected.get("target")
    formula = expected.get("formula")
    validation = expected.get("validation")
    history = expected.get("history")
    if not all(isinstance(item, dict) for item in (target, formula, validation, history)):
        return None
    if type(target.get("sheet_id")) is not int or not all(
        isinstance(target.get(key), str) and target[key]
        for key in ("sheet", "a1", "after_value", "stable_key_cell", "stable_key")
    ) or not isinstance(target.get("before_value"), str) \
            or target["before_value"] == target["after_value"]:
        return None
    if not all(isinstance(formula.get(key), str) and formula[key] for key in ("cell", "value")) \
            or not isinstance(formula.get("result"), str):
        return None
    if not all(isinstance(validation.get(key), str) and validation[key]
               for key in ("range", "criteria", "invalid_input")) \
            or not isinstance(validation.get("allowed_values"), list) \
            or type(validation.get("strict")) is not bool:
        return None
    if not isinstance(history.get("range"), str) or not history["range"] \
            or not isinstance(history.get("values"), list):
        return None
    return {"native_id": resource["native_id"], "target": target, "formula": formula,
            "validation": validation, "history": history}


def _controller_binding_issues(
    visible: dict[str, Any], metadata: dict[str, Any], review: dict[str, Any],
    expected: dict[str, Any],
) -> list[str]:
    request = visible["visible_write_request"]
    target = expected["target"]
    formula = expected["formula"]
    validation = expected["validation"]
    history = expected["history"]
    previous = review["previous_revision"]
    current = review["current_revision"]
    before = metadata["before"]
    after = metadata["after"]
    issues: list[str] = []

    if request.get("spreadsheet_id") != expected["native_id"]:
        issues.append("browser_expected_workbook_mismatch")

    sheet_id, target_a1 = _write_cell(request)
    if (
        sheet_id != target["sheet_id"] or target_a1 != target["a1"]
        or previous.get("sheet") != target["sheet"] or current.get("sheet") != target["sheet"]
    ):
        issues.append("browser_expected_target_mismatch")

    if before.get("value") != target["before_value"] or after.get("value") != target["after_value"] \
            or after.get("key") != target["stable_key"] \
            or previous.get("stable_key_cell") != target["stable_key_cell"]:
        issues.append("browser_expected_state_mismatch")

    if before.get("formula_neighbor") != f"{target['sheet']}!{formula['cell']}" \
            or after.get("formula_neighbor") != f"{target['sheet']}!{formula['cell']}" \
            or before.get("formula") != formula["value"] \
            or before.get("formula_result") != formula["result"] \
            or previous.get("formula_cell") != formula["cell"] or current.get("formula_cell") != formula["cell"] \
            or previous.get("formula_result") != formula["result"] \
            or current.get("formula_result") != formula["result"]:
        issues.append("browser_expected_state_mismatch")

    review_validation = {key: validation[key] for key in ("range", "criteria", "allowed_values", "invalid_input")}
    before_validation = before.get("validation")
    after_validation = after.get("validation")
    if review.get("validation") != review_validation \
            or not isinstance(before_validation, dict) \
            or before_validation.get("strict") is not validation["strict"] \
            or not isinstance(after_validation, dict) \
            or after_validation.get("strict") is not validation["strict"] \
            or after_validation.get("allowed_values") != validation["allowed_values"]:
        issues.append("browser_expected_state_mismatch")

    if history.get("range") != review.get("history", {}).get("range") \
            or history.get("values") != before.get("history_row"):
        issues.append("browser_expected_state_mismatch")
    return sorted(set(issues))


def _review_issues(
    visible: dict[str, Any], metadata: dict[str, Any], review: dict[str, Any]
) -> list[str]:
    issues: list[str] = []
    if review.get("schema_version") != 1 or review.get("evidence_kind") != "native-google-sheets-ui-observation":
        return ["browser_native_source_observation_invalid"]
    if not review.get("acceptance_review", {}).get("result") == "pass":
        issues.append("browser_native_source_observation_unreviewed")

    request = visible.get("visible_write_request")
    if not isinstance(request, dict) or metadata.get("provider_write_request") != request:
        issues.append("browser_write_request_mismatch")
        return issues
    if not visible.get("visible_write_result_present"):
        issues.append("browser_write_result_missing")
    if not visible.get("visible_before_read_present") or not visible.get("visible_readback_present"):
        issues.append("browser_before_after_read_claim_missing")
    if not visible.get("visible_no_other_authority_claim"):
        issues.append("browser_scope_confirmation_missing")
    if visible.get("google_drive_use_badges", 0) < 1 \
            or set(visible.get("activity_labels", [])) != set(REQUIRED_ACTIVITY_LABELS):
        issues.append("browser_provider_activity_missing")
    plugin = metadata.get("plugin_id")
    if not visible.get("skill_resource_uri") or visible.get("plugin_id") != plugin \
            or metadata.get("skill_id") != "personal-shopper:personal-shopper":
        issues.append("browser_skill_activation_missing")

    provider = metadata.get("provider_identity")
    source_identity = review.get("account")
    workbook_id = request.get("spreadsheet_id")
    if not isinstance(provider, str) or source_identity != provider \
            or review.get("workbook_id") != workbook_id or review.get("saved_status") != "Saved to Drive":
        issues.append("browser_native_source_identity_mismatch")

    before = metadata.get("before")
    after = metadata.get("after")
    previous = review.get("previous_revision")
    current = review.get("current_revision")
    validation = review.get("validation")
    history = review.get("history")
    if not all(isinstance(item, dict) for item in (before, after, previous, current, validation, history)):
        issues.append("browser_native_source_observation_incomplete")
        return issues

    sheet_id, target_a1 = _write_cell(request)
    update = request["requests"][0]["updateCells"]
    written_value = update["rows"][0]["values"][0]["userEnteredValue"]["stringValue"]
    expected_location = f"{current.get('sheet')}!{target_a1}"
    if previous.get("sheet_id") != sheet_id or current.get("sheet_id") != sheet_id \
            or previous.get("target_a1") != target_a1 or current.get("target_a1") != target_a1 \
            or before.get("cell") != expected_location or after.get("cell") != expected_location \
            or previous.get("target_value") != before.get("value") \
            or current.get("target_value") != after.get("value") \
            or written_value != after.get("value"):
        issues.append("browser_native_target_reconciliation_failed")
    if before.get("value") == after.get("value"):
        issues.append("browser_native_target_not_changed")
    if current.get("is_current") is not True or current.get("edits_in_revision") != 1 \
            or current.get("write_count") != 1 \
            or current.get("changed_cell") != expected_location:
        issues.append("browser_native_revision_edit_count_invalid")

    previous_key = (previous.get("stable_key_cell"), previous.get("stable_key"))
    current_key = (current.get("stable_key_cell"), current.get("stable_key"))
    if previous_key != current_key or previous.get("stable_key") != after.get("key"):
        issues.append("browser_stable_key_not_preserved")

    formula = before.get("formula")
    if formula != after.get("formula") or formula != previous.get("formula") \
            or formula != current.get("formula") \
            or before.get("formula_result") != after.get("formula_result") \
            or formula != "=IF(C2=\"\",\"Unset\",\"Set\")":
        issues.append("browser_neighbor_formula_not_preserved")

    before_validation = before.get("validation")
    if not isinstance(validation, dict) or not isinstance(before_validation, dict) \
            or validation.get("range") != expected_location \
            or validation.get("criteria") != "Dropdown" \
            or validation.get("allowed_values") != before_validation.get("allowed_values") \
            or validation.get("invalid_input") != "Reject the input" \
            or before_validation.get("strict") is not True:
        issues.append("browser_validation_not_preserved")

    history_before = before.get("history_row")
    history_after = after.get("history_row")
    if not isinstance(history_before, list) or history_before != history_after \
            or history.get("prior_values") != history_before \
            or history.get("current_values") != history_after \
            or history.get("range") != "Change History!A2:E2":
        issues.append("browser_history_not_preserved")
    return issues


def archive_capture(
    conversation_path: str | Path,
    metadata_path: str | Path,
    screenshot_path: str | Path,
    candidate_path: str | Path,
    output_dir: str | Path,
    native_ui_review_path: str | Path | None = None,
) -> dict[str, Any]:
    """Hash original browser evidence and reconcile it with native UI review."""
    conversation = _private_path(Path(conversation_path))
    metadata_file = _private_path(Path(metadata_path))
    screenshot = _private_path(Path(screenshot_path))
    candidate = _private_path(Path(candidate_path))
    review_path = _private_path(Path(native_ui_review_path)) if native_ui_review_path else \
        _private_path(metadata_file.parent / NATIVE_UI_REVIEW_NAME)
    output = Path(output_dir).expanduser().absolute()
    if output.exists() or output.is_symlink():
        output = _private_path(output)
        if not private_evidence.private_directory(output):
            raise ValueError("browser evidence directory permissions are not private")
    else:
        try:
            output.resolve(strict=False).relative_to(REPO_ROOT.resolve())
        except ValueError:
            pass
        else:
            raise ValueError("browser evidence must be stored outside the source checkout")
        output = private_evidence.ensure_private_directory(output)

    snapshot_bytes = conversation.read_bytes()
    snapshot = snapshot_bytes.decode("utf-8")
    visible = parse_visible_conversation(snapshot)
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or not isinstance(review, dict):
        raise ValueError("browser run metadata or native UI review is malformed")
    candidate_hash = sha256(candidate.read_bytes())
    if str(metadata.get("candidate_zip_sha256", "")).lower() != candidate_hash:
        raise ValueError("candidate archive digest does not match the recorded candidate")

    issues = _review_issues(visible, metadata, review)
    source_files = {
        conversation.name: sha256(snapshot_bytes),
        metadata_file.name: sha256(metadata_file.read_bytes()),
        screenshot.name: sha256(screenshot.read_bytes()),
        candidate.name: candidate_hash,
        review_path.name: sha256(review_path.read_bytes()),
    }
    record = {
        "schema_version": 2,
        "capture_format": CAPTURE_FORMAT,
        "run_id": metadata.get("run_id"),
        "host": metadata.get("host"),
        "model": metadata.get("model"),
        "reasoning_effort": metadata.get("reasoning_effort"),
        "plugin": {
            "id": metadata.get("plugin_id"),
            "name": metadata.get("plugin_name"),
            "manifest_version": metadata.get("plugin_manifest_version"),
            "skill_id": metadata.get("skill_id"),
            "resource_uri": visible["skill_resource_uri"],
            "candidate_archive_sha256": candidate_hash,
        },
        "provider": {
            "plugin": metadata.get("provider_plugin"),
            "identity": metadata.get("provider_identity"),
        },
        "input_files": {
            "conversation": conversation.name,
            "metadata": metadata_file.name,
            "work_screenshot": screenshot.name,
            "candidate": candidate.name,
            "native_ui_review": review_path.name,
        },
        "source_artifacts": source_files,
        "visible_host_evidence": visible,
        "native_tool_trace": {
            "available": False,
            "reason": "Work does not expose its complete read-call ledger; direct native Sheets UI review verifies the saved source and prior revision.",
        },
        "acceptance_basis": "visible single-cell provider request/result reconciled with direct native source and prior-revision observations",
        "acceptance": {"status": "accepted" if not issues else "blocked", "issues": sorted(set(issues))},
    }
    destination = output / CAPTURE_NAME
    if destination.exists() or destination.is_symlink():
        raise ValueError("browser capture sidecar already exists")
    private_evidence.write_private_file(
        destination, (json.dumps(record, indent=2) + "\n").encode("utf-8")
    )
    return record


def validate_archived_capture(capture_dir: str | Path, config: Any) -> dict[str, Any] | None:
    root = Path(capture_dir)
    if not private_evidence.private_directory(root):
        return {"accepted": False, "status": "blocked", "issues": ["browser_capture_invalid"]}
    sidecar = root / CAPTURE_NAME
    if not sidecar.exists():
        return None
    expected = _browser_expectations(config)
    if expected is None:
        return {"accepted": False, "status": "blocked", "issues": ["browser_native_config_invalid"]}
    try:
        sidecar = _private_path(sidecar)
        if not private_evidence.private_file(sidecar):
            raise ValueError
        record = json.loads(sidecar.read_text(encoding="utf-8"))
        artifacts = record.get("source_artifacts")
        input_files = record.get("input_files")
        if record.get("schema_version") != 2 or record.get("capture_format") != CAPTURE_FORMAT \
                or not isinstance(artifacts, dict) or not isinstance(input_files, dict):
            raise ValueError
        loaded: dict[str, bytes] = {}
        for name, digest in artifacts.items():
            if not isinstance(name, str) or Path(name).name != name \
                    or not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
                raise ValueError
            path = _private_path(root / name)
            content = path.read_bytes()
            if sha256(content) != digest:
                raise ValueError
            loaded[name] = content
        if set(input_files) != {"conversation", "metadata", "work_screenshot", "candidate", "native_ui_review"}:
            raise ValueError
        snapshot = loaded[input_files["conversation"]].decode("utf-8")
        metadata = json.loads(loaded[input_files["metadata"]].decode("utf-8-sig"))
        review = json.loads(loaded[input_files["native_ui_review"]].decode("utf-8-sig"))
        candidate_hash = sha256(loaded[input_files["candidate"]])
        visible = parse_visible_conversation(snapshot)
        if candidate_hash != metadata.get("candidate_zip_sha256") \
                or candidate_hash != record.get("plugin", {}).get("candidate_archive_sha256"):
            raise ValueError
        issues = _review_issues(visible, metadata, review)
        if not issues:
            issues = _controller_binding_issues(visible, metadata, review, expected)
    except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        return {"accepted": False, "status": "blocked", "issues": ["browser_capture_invalid"]}
    return {
        "accepted": not issues,
        "status": "accepted" if not issues else "blocked",
        "issues": sorted(set(issues)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conversation", required=True, help="private raw Work conversation DOM snapshot")
    parser.add_argument("--metadata", required=True, help="private Work run metadata JSON")
    parser.add_argument("--screenshot", required=True, help="private Work result screenshot")
    parser.add_argument("--candidate", required=True, help="exact plugin ZIP uploaded to Work")
    parser.add_argument("--native-ui-review", help="reviewed direct Google Sheets source observations JSON")
    parser.add_argument("--output-dir", required=True, help="private evidence directory outside the checkout")
    args = parser.parse_args(argv)
    try:
        result = archive_capture(
            args.conversation, args.metadata, args.screenshot, args.candidate,
            args.output_dir, args.native_ui_review,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"status": "blocked", "issues": [str(error)]}, sort_keys=True))
        return 2
    print(json.dumps({"status": result["acceptance"]["status"],
                      "issues": result["acceptance"]["issues"],
                      "candidate_sha256": result["plugin"]["candidate_archive_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
