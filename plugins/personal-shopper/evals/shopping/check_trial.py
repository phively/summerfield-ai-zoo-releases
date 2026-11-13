"""Validate private, same-run evidence for the live grocery access gate.

This checker validates the receipt contract. It does not activate a skill or
call a provider. Deterministic controls are deliberately never R25 acceptance.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import parse_qs, urlsplit, unquote

import capture_invocation as capture


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PLUGIN_ROOT.parents[1]
MANIFEST = PLUGIN_ROOT / "evals" / "shopping" / "manifest.json"
MAX_RECEIPT_AGE_SECONDS = 900
MAX_RANGE_CELLS = 1000
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_OPERATIONS = {"resolve", "metadata", "read_values"}
ALLOWED_TOOL_SOURCES = {
    "connected_google_sheets_tool",
    "connected_google_drive_native_sheets_tool",
}
ALLOWED_HOST_SERVERS = {"google-drive", "google_drive", "google-drive-native-sheets"}
ALLOWED_NATIVE_READ_TOOLS = {
    "get_file_metadata", "get_spreadsheet_metadata", "get_spreadsheet_range", "get_spreadsheet_cells",
}
ALLOWED_DISCOVERY_TOOLS = {"list_mcp_resources", "list_mcp_resource_templates"}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign_receipt(receipt: dict[str, Any], key: str) -> str:
    """Return the HMAC for a receipt body, excluding its attestation field."""
    payload = {name: value for name, value in receipt.items() if name != "attestation"}
    return hmac.new(key.encode(), _canonical_json(payload), hashlib.sha256).hexdigest()


def candidate_digest(repo_root: Path = REPO_ROOT) -> str:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return capture.identity_digest(repo_root, capture.candidate_identity_patterns(manifest))


def suite_digest(repo_root: Path = REPO_ROOT) -> str:
    """Hash the evaluation fixtures, adapters, checker and protocol separately."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    patterns = manifest.get("suite_identity_files")
    if not isinstance(patterns, list) or not patterns:
        raise ValueError("suite identity patterns are missing")
    files: dict[str, Path] = {}
    root = repo_root.resolve()
    for pattern in patterns:
        file_pattern = pattern + "/*" if pattern.endswith("/**") else pattern
        matches = [path for path in root.glob(file_pattern) if path.is_file()]
        if not matches:
            raise ValueError("required suite identity pattern has no files")
        for path in matches:
            if path.is_symlink():
                raise ValueError("suite identity contains a symlink")
            resolved = path.resolve(strict=True)
            if root not in resolved.parents:
                raise ValueError("suite identity file escaped repository root")
            files[resolved.relative_to(root).as_posix()] = resolved
    if not files:
        raise ValueError("suite identity has no files")

    digest = hashlib.sha256()
    for relative_name, path in sorted(files.items()):
        relative = relative_name.encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _independent_host_calls(raw: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not raw or not raw.endswith(b"\n"):
        raise ValueError("incomplete_host_capture")
    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("invalid_host_capture") from error
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise ValueError("invalid_host_event")
        events.append(event)
    if not events:
        raise ValueError("empty_host_capture")
    calls: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for index, event in enumerate(events):
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "mcp_tool_call":
            continue
        call_id, server = item.get("id"), item.get("server")
        tool = item.get("tool") or item.get("name")
        if not all(isinstance(value, str) and value for value in (call_id, server, tool)):
            raise ValueError("invalid_host_tool_call")
        if call_id not in calls:
            calls[call_id] = {
                "call_id": call_id, "server": server, "tool": tool, "arguments": None,
                "result": None, "status": "incomplete", "event_indexes": [],
            }
            order.append(call_id)
        call = calls[call_id]
        if (call["server"], call["tool"]) != (server, tool):
            raise ValueError("host_tool_identity_changed")
        arguments = item.get("arguments", item.get("input"))
        if arguments is not None:
            if call["arguments"] is not None and call["arguments"] != arguments:
                raise ValueError("host_tool_arguments_changed")
            call["arguments"] = arguments
        if "result" in item:
            call["result"] = item["result"]
        elif "output" in item:
            call["result"] = item["output"]
        if "error" in item:
            call["error"] = item["error"]
        call["event_indexes"].append(index)
        if item.get("status") in {"completed", "failed", "cancelled"}:
            call["status"] = item["status"]
        elif event["type"] == "item.completed":
            call["status"] = "completed"
        elif event["type"] in {"item.failed", "turn.failed", "error"}:
            call["status"] = "failed"
    return events, [calls[call_id] for call_id in order]


def _native_tool_identity(call: dict[str, Any]) -> tuple[str, str] | None:
    server = str(call.get("server", "")).lower().replace("_", "-")
    tool = str(call.get("tool", ""))
    if server == "codex-apps" and tool.startswith("google_drive."):
        return "google-drive", tool.split(".", 1)[1]
    if server in ALLOWED_HOST_SERVERS:
        if tool.startswith("google_drive."):
            tool = tool.split(".", 1)[1]
        return server, tool
    if server.startswith("mcp--codex-apps--google-drive"):
        if tool.startswith("google_drive."):
            tool = tool.split(".", 1)[1]
        return "google-drive", tool
    return None


def _structured_tool_result(result: Any) -> Any:
    if isinstance(result, dict):
        value = result.get("structured_content", result.get("structuredContent"))
        if isinstance(value, (dict, list)):
            return value
    return result


def _requested_range(arguments: Any) -> str | None:
    if not isinstance(arguments, dict):
        return None
    value = arguments.get("range")
    if isinstance(value, str):
        return value
    ranges = arguments.get("ranges")
    if isinstance(ranges, list) and len(ranges) == 1 and isinstance(ranges[0], str):
        return ranges[0]
    return None


def _a1_range_area(value: str) -> int | None:
    part = value.rsplit("!", 1)[-1].replace("$", "").strip()
    match = re.fullmatch(r"([A-Za-z]+)([1-9][0-9]*)(?::([A-Za-z]+)([1-9][0-9]*))?", part)
    if not match:
        return None

    def column_number(letters: str) -> int:
        number = 0
        for char in letters.upper():
            number = number * 26 + ord(char) - ord("A") + 1
        return number

    start_column, start_row = column_number(match.group(1)), int(match.group(2))
    end_column = column_number(match.group(3)) if match.group(3) else start_column
    end_row = int(match.group(4)) if match.group(4) else start_row
    if end_column < start_column or end_row < start_row:
        return None
    return (end_column - start_column + 1) * (end_row - start_row + 1)


def _is_host_discovery_call(call: dict[str, Any]) -> bool:
    return call.get("server") == "codex" and call.get("tool") in ALLOWED_DISCOVERY_TOOLS


def _google_sheet_id(locator: str) -> str | None:
    value = locator.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{20,}", value):
        return value
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme != "https" or parsed.hostname not in {"docs.google.com", "drive.google.com"}:
        return None
    match = re.search(r"/spreadsheets/d/([^/]+)", parsed.path)
    if match:
        return unquote(match.group(1))
    query_id = parse_qs(parsed.query).get("id", [])
    return query_id[0] if query_id else None


def _resource_ids(value: Any, tool: str) -> set[str]:
    identity_keys = {
        "spreadsheet_id", "spreadsheetid", "file_id", "fileid", "resource_id", "resourceid",
        "document_id", "documentid",
    }
    url_keys = {"spreadsheet_url", "spreadsheeturl", "file_url", "fileurl"}
    if tool in {"get_file_metadata", "get_spreadsheet_metadata"}:
        url_keys.add("url")
    if tool == "get_file_metadata":
        identity_keys.add("id")
    result: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = re.sub(r"[^a-z0-9_]", "", str(key).lower())
                if normalized in identity_keys and isinstance(child, str) and child.strip():
                    result.add(child.strip())
                elif normalized in url_keys and isinstance(child, str):
                    resolved = _google_sheet_id(child)
                    if resolved:
                        result.add(resolved)
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return result


def _capture_bundle_errors(capture_path: str | Path | None, receipt: dict[str, Any],
                           operations: list[dict[str, Any]], locator: str = "") -> list[str]:
    errors: list[str] = []
    if not capture_path:
        return ["raw_host_capture_missing"]
    path = Path(capture_path)
    trace_path = path / "host-events.jsonl" if path.is_dir() else path
    if trace_path.is_symlink():
        return ["raw_host_capture_symlink_rejected"]
    try:
        trace_path = trace_path.resolve(strict=True)
        trace_path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        pass
    except OSError:
        return ["raw_host_capture_unavailable"]
    else:
        return ["raw_host_capture_must_be_private"]
    try:
        raw = trace_path.read_bytes()
        events, calls = _independent_host_calls(raw)
    except (OSError, ValueError) as error:
        return [str(error) if str(error) in {
            "incomplete_host_capture", "invalid_host_capture", "invalid_host_event",
            "empty_host_capture", "invalid_host_tool_call", "host_tool_identity_changed",
            "host_tool_arguments_changed",
        } else "raw_host_capture_invalid"]
    if not hmac.compare_digest(str(receipt.get("tool_trace_sha256", "")), hashlib.sha256(raw).hexdigest()):
        errors.append("raw_host_capture_digest_mismatch")
    if receipt.get("tool_trace_event_count") != len(events):
        errors.append("host_tool_trace_event_count_mismatch")
    if receipt.get("tool_trace_call_count") != len(calls):
        errors.append("host_tool_call_count_mismatch")
    if events[0].get("type") != "thread.started":
        errors.append("host_session_start_missing")
    if events[-1].get("type") != "turn.completed":
        errors.append("host_turn_completion_missing")
    activation = receipt.get("activation")
    if isinstance(activation, dict):
        session_ids = {event.get("thread_id") for event in events if event.get("type") == "thread.started"}
        if activation.get("session_id") not in session_ids:
            errors.append("host_session_activation_mismatch")
    calls_by_id = {call["call_id"]: call for call in calls}
    operation_call_ids: set[str] = set()
    native_call_ids: set[str] = set()
    discovery_call_ids: set[str] = set()
    event_ids = set()
    expected = receipt.get("resource")
    expected_native_id = str(expected.get("native_id", "")) if isinstance(expected, dict) else ""
    locator_hash = str(receipt.get("requested_locator_sha256", ""))
    locator_native_id = _google_sheet_id(locator)
    discovered_sheets: dict[str, str] = {}

    def strings(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [entry for key, item in value.items() for entry in [*strings(key), *strings(item)]]
        if isinstance(value, list):
            return [entry for item in value for entry in strings(item)]
        return []

    def sheet_metadata(result: Any) -> dict[str, str]:
        if not isinstance(result, dict):
            return {}
        sheets = result.get("sheets")
        if not isinstance(sheets, list):
            nested = result.get("spreadsheet")
            sheets = nested.get("sheets") if isinstance(nested, dict) else None
        output = {}
        for sheet in sheets if isinstance(sheets, list) else []:
            if not isinstance(sheet, dict):
                continue
            properties = sheet.get("properties", sheet)
            if isinstance(properties, dict) and properties.get("sheetId") is not None \
                    and isinstance(properties.get("title"), str):
                output[properties["title"]] = str(properties["sheetId"])
        return output

    for call in calls:
        if _is_host_discovery_call(call):
            if call.get("status") != "completed" or call.get("error") is not None \
                    or call.get("result") is None or call.get("arguments") not in (None, {}):
                errors.append("host_resource_discovery_failed_or_unexpected")
            else:
                discovery_call_ids.add(call["call_id"])
            continue
        if _native_tool_identity(call) is not None:
            native_call_ids.add(call["call_id"])
        else:
            errors.append("unapproved_or_unexplained_host_tool_call")

    for operation in operations:
        call_id = operation.get("tool_call_id")
        if not isinstance(call_id, str) or call_id not in calls_by_id:
            errors.append("receipt_operation_not_in_host_capture")
            continue
        operation_call_ids.add(call_id)
        call = calls_by_id[call_id]
        normalized_identity = _native_tool_identity(call)
        if normalized_identity is None:
            errors.append("host_tool_server_not_native_sheets")
            normalized_tool = ""
        else:
            _, normalized_tool = normalized_identity
        if normalized_tool not in ALLOWED_NATIVE_READ_TOOLS:
            errors.append("host_tool_operation_forbidden_or_unknown")
        if operation.get("operation") == "resolve" \
                and normalized_tool not in {"get_file_metadata", "get_spreadsheet_metadata"}:
            errors.append("host_tool_operation_mapping_invalid")
        if operation.get("operation") == "metadata" \
                and normalized_tool != "get_spreadsheet_metadata":
            errors.append("host_tool_operation_mapping_invalid")
        if operation.get("operation") == "read_values" \
                and normalized_tool not in {"get_spreadsheet_range", "get_spreadsheet_cells"}:
            errors.append("host_tool_operation_mapping_invalid")
        if call["status"] != "completed" or call.get("error") is not None:
            errors.append("host_tool_call_failed_or_incomplete")
        if call.get("arguments") is None or call.get("result") is None:
            errors.append("host_tool_request_or_result_missing")
        if operation.get("trace_event_indexes") != call["event_indexes"]:
            errors.append("receipt_operation_event_link_mismatch")
        if operation.get("request_sha256") != hashlib.sha256(_canonical_json(call.get("arguments"))).hexdigest():
            errors.append("receipt_operation_request_mismatch")
        if operation.get("result_sha256") != hashlib.sha256(_canonical_json(call.get("result"))).hexdigest():
            errors.append("receipt_operation_result_mismatch")
        request_resource_ids = _resource_ids(call.get("arguments"), normalized_tool)
        response_resource_ids = _resource_ids(_structured_tool_result(call.get("result")), normalized_tool)
        if expected_native_id and (
            any(value != expected_native_id for value in request_resource_ids | response_resource_ids)
            or (normalized_tool in {"get_spreadsheet_range", "get_spreadsheet_cells"}
                and expected_native_id not in request_resource_ids)
        ):
            errors.append("host_tool_call_wrong_resource")
        if operation.get("operation") == "resolve":
            request_strings = strings(call.get("arguments"))
            request_binds_locator = any(
                hashlib.sha256(value.strip().encode()).hexdigest() == locator_hash
                for value in request_strings
            )
            id_binds_locator = bool(locator_native_id) and locator_native_id == expected_native_id \
                and locator_native_id in request_strings \
                and locator_native_id in strings(_structured_tool_result(call.get("result")))
            if not request_binds_locator and not id_binds_locator:
                errors.append("runtime_locator_absent_from_host_request")
            result = _structured_tool_result(call.get("result"))
            if normalized_tool == "get_file_metadata" and (
                not isinstance(result, dict) or result.get("id") != expected_native_id
                or result.get("mime_type") != "application/vnd.google-apps.spreadsheet"
            ):
                errors.append("drive_file_resolution_unrecognized")
        elif operation.get("operation") == "metadata":
            result = _structured_tool_result(call.get("result"))
            if expected_native_id not in strings(result):
                errors.append("native_resource_identity_absent_from_metadata")
            actual_sheets = sheet_metadata(result)
            if not actual_sheets:
                errors.append("native_metadata_response_unrecognized")
            else:
                discovered_sheets = {sheet_id: title for title, sheet_id in actual_sheets.items()}
                claimed = operation.get("native_sheets")
                claimed_map = {str(sheet.get("sheet_id")): name
                               for sheet in claimed or [] if isinstance(sheet, dict)
                               for name in sheet.get("names", []) if isinstance(name, str)}
                if claimed_map != discovered_sheets:
                    errors.append("receipt_native_sheets_mismatch")
        elif operation.get("operation") == "read_values":
            result = _structured_tool_result(call.get("result"))
            values = result.get("values") if isinstance(result, dict) else None
            arguments = call.get("arguments")
            range_value = _requested_range(arguments)
            if not isinstance(values, list) or not values or not all(isinstance(row, list) for row in values):
                errors.append("native_range_result_unrecognized")
            else:
                cell_count = sum(len(row) for row in values)
                content_hash = hashlib.sha256(_canonical_json(values)).hexdigest()
                range_hash = hashlib.sha256(str(range_value).encode()).hexdigest() if range_value else ""
                if operation.get("content_sha256") != content_hash \
                        or operation.get("cell_count") != cell_count \
                        or operation.get("row_count") != max(0, len(values) - 1) \
                        or operation.get("headers") != values[0]:
                    errors.append("receipt_native_range_content_mismatch")
                if operation.get("range_sha256") != range_hash:
                    errors.append("receipt_native_range_bounds_mismatch")
                area = _a1_range_area(range_value) if isinstance(range_value, str) else None
                if area is None:
                    errors.append("native_range_bounds_unrecognized")
                elif area > MAX_RANGE_CELLS:
                    errors.append("native_range_exceeds_cell_limit")
                if isinstance(arguments, dict):
                    range_sheet = arguments.get("sheet_name")
                    if not isinstance(range_sheet, str) and isinstance(range_value, str) and "!" in range_value:
                        range_sheet = range_value.split("!", 1)[0].strip("'\"")
                else:
                    range_sheet = None
                if isinstance(range_sheet, str):
                    range_sheet = range_sheet.strip().strip("'\"").replace("''", "'")
                    expected_sheet_id = next((sheet_id for sheet_id, title in discovered_sheets.items()
                                              if title == range_sheet), None)
                    if not expected_sheet_id or str(operation.get("sheet_id")) != expected_sheet_id:
                        errors.append("native_range_sheet_mismatch")
                else:
                    errors.append("native_range_sheet_missing")
        event_id = operation.get("event_id")
        if not isinstance(event_id, str) or event_id in event_ids:
            errors.append("duplicate_tool_event_id")
        event_ids.add(event_id)
    if operation_call_ids != native_call_ids or operation_call_ids & discovery_call_ids:
        errors.append("host_tool_calls_not_fully_normalized")
    return sorted(set(errors))


def _config_errors(config: Any, locator: str, run_id: str, key: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        return ["invalid_private_config"]
    expected = config.get("expected_resource")
    if not isinstance(expected, dict) or expected.get("provider") != "google-sheets" \
            or not expected.get("native_id"):
        errors.append("missing_expected_resource_identity")
    elif set(expected) != {"provider", "native_id"}:
        errors.append("private_resource_config_contains_unapproved_fields")
    if not locator.strip():
        errors.append("missing_runtime_locator")
    if not run_id.strip():
        errors.append("missing_current_run_id")
    if len(key) < 32:
        errors.append("missing_or_short_receipt_key")
    return errors


def validate_receipt(
    receipt: Any,
    config: Any,
    *,
    locator: str,
    run_id: str,
    key: str,
    now: datetime | None = None,
    repo_root: Path = REPO_ROOT,
    host_capture_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return redacted checks; private identifiers and file paths are never echoed."""
    errors = _config_errors(config, locator, run_id, key)
    if errors:
        return {"status": "blocked", "accepted": False, "issues": sorted(set(errors))}
    if not isinstance(receipt, dict) or receipt.get("schema_version") != 1:
        return {"status": "blocked", "accepted": False, "issues": ["invalid_receipt_schema"]}

    expected = config["expected_resource"]
    errors = []
    attestation = receipt.get("attestation")
    if not isinstance(attestation, dict) or attestation.get("algorithm") != "hmac-sha256":
        errors.append("missing_receipt_attestation")
    elif not hmac.compare_digest(str(attestation.get("digest", "")), sign_receipt(receipt, key)):
        errors.append("invalid_receipt_attestation")

    kind = receipt.get("evidence_kind")
    if kind not in {"host-activation", "deterministic-control"}:
        errors.append("unsupported_evidence_kind")
    if receipt.get("receipt_schema") != "personal-shopper-live-receipt/v2":
        errors.append("wrong_receipt_schema")
    if receipt.get("run_id") != run_id:
        errors.append("wrong_or_stale_run")
    try:
        current_candidate = candidate_digest(repo_root)
        current_suite = suite_digest(repo_root)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        current_candidate = None
        current_suite = None
    if not current_candidate or receipt.get("candidate_sha256") != current_candidate:
        errors.append("stale_or_wrong_candidate")
    if not current_suite or receipt.get("suite_sha256") != current_suite:
        errors.append("stale_or_wrong_suite")

    locator_hash = hashlib.sha256(locator.strip().encode()).hexdigest()
    if receipt.get("requested_locator_sha256") != locator_hash:
        errors.append("runtime_locator_mismatch")

    resource = receipt.get("resource")
    if not isinstance(resource, dict) or resource.get("provider") != expected.get("provider") \
            or resource.get("native_id") != expected.get("native_id"):
        errors.append("wrong_canonical_resource")
    elif set(resource) != {"provider", "native_id"}:
        errors.append("receipt_contains_unapproved_resource_fields")

    activation = receipt.get("activation")
    runtime = receipt.get("runtime")
    if not isinstance(activation, dict) or activation.get("skill_id") != "personal-shopper:personal-shopper" \
            or activation.get("activated") is not True or not activation.get("session_id") \
            or activation.get("run_id") != run_id or activation.get("candidate_sha256") != current_candidate:
        errors.append("actual_candidate_activation_missing")
    if not isinstance(runtime, dict) or runtime.get("credentials_available") is not True \
            or runtime.get("connected_google_sheets_tool_available") is not True:
        errors.append("live_credentials_unavailable")
    if not isinstance(runtime, dict) or runtime.get("read_only_envelope") is not True:
        errors.append("read_only_envelope_missing")
    if not isinstance(runtime, dict) or runtime.get("host_receipt_source") != "actual_host_tool_trace":
        errors.append("actual_host_tool_trace_missing")
    if not HEX_SHA256.fullmatch(str(receipt.get("tool_trace_sha256", ""))):
        errors.append("host_tool_trace_digest_missing")

    started = _iso_datetime(activation.get("started_at") if isinstance(activation, dict) else None)
    completed = _iso_datetime(activation.get("completed_at") if isinstance(activation, dict) else None)
    current = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    if not started or not completed or completed < started or completed > current:
        errors.append("invalid_activation_time")
    elif (current - completed).total_seconds() > MAX_RECEIPT_AGE_SECONDS:
        errors.append("stale_activation_receipt")

    session_id = activation.get("session_id") if isinstance(activation, dict) else None
    operations = receipt.get("operations")
    if not isinstance(operations, list) or not operations:
        operations = []
        errors.append("missing_actual_tool_operations")
    errors.extend(_capture_bundle_errors(host_capture_path, receipt, operations, locator=locator))
    if any(not isinstance(event, dict) for event in operations):
        errors.append("invalid_tool_operation")
        operations = [event for event in operations if isinstance(event, dict)]

    if [event.get("seq") for event in operations] != list(range(1, len(operations) + 1)):
        errors.append("tool_operation_order_invalid")
    for event in operations:
        if event.get("operation") not in ALLOWED_OPERATIONS:
            errors.append("forbidden_or_unrecognized_tool_operation")
        event_time = _iso_datetime(event.get("timestamp"))
        if event.get("session_id") != session_id or event.get("run_id") != run_id \
                or not event.get("tool_call_id") or not started or not completed \
                or not event_time or not started <= event_time <= completed:
            errors.append("tool_event_not_bound_to_activation")
        if event.get("provider") != expected.get("provider") \
                or event.get("native_id") != expected.get("native_id"):
            errors.append("tool_event_wrong_resource")
        if event.get("source") not in ALLOWED_TOOL_SOURCES:
            errors.append("tool_event_not_from_native_sheets_api")

    operation_times = [_iso_datetime(event.get("timestamp")) for event in operations]
    if any(value is None for value in operation_times) or any(
        earlier > later for earlier, later in zip(operation_times, operation_times[1:])
        if earlier is not None and later is not None
    ):
        errors.append("tool_operation_order_invalid")

    resolves = [event for event in operations if event.get("operation") == "resolve"]
    metadata = [event for event in operations if event.get("operation") == "metadata"]
    reads = [event for event in operations if event.get("operation") == "read_values"]
    locator_hash = hashlib.sha256(locator.strip().encode()).hexdigest()
    if not resolves or not any(event.get("resolved") is True
                               and event.get("requested_locator_sha256") == locator_hash
                               for event in resolves):
        errors.append("native_resource_resolution_missing")
    if not metadata or not any(
        isinstance(event.get("native_sheets"), list) and event.get("native_sheets")
        for event in metadata
    ):
        errors.append("native_metadata_routing_missing")

    sheets: dict[str, set[str]] = {}
    for event in metadata:
        for sheet in event.get("native_sheets", []) if isinstance(event.get("native_sheets"), list) else []:
            if isinstance(sheet, dict) and sheet.get("sheet_id"):
                sheets[str(sheet["sheet_id"])] = set(sheet.get("names", []))

    valid_context_reads = []
    valid_route_reads = []
    for event in reads:
        if event.get("bounded") is not True or not isinstance(event.get("cell_count"), int) \
                or not 0 < event["cell_count"] <= MAX_RANGE_CELLS:
            errors.append("unbounded_or_empty_native_read")
        if not HEX_SHA256.fullmatch(str(event.get("content_sha256", ""))):
            errors.append("native_read_content_digest_missing")
        if not HEX_SHA256.fullmatch(str(event.get("range_sha256", ""))):
            errors.append("native_read_range_digest_missing")
        if not event.get("sheet_id") or str(event.get("sheet_id")) not in sheets:
            errors.append("native_read_not_bound_to_discovered_sheet")
        if event.get("purpose") == "grocery_context":
            valid_context_reads.append(event)
            headers = event.get("headers")
            mapping = event.get("header_map")
            if not isinstance(headers, list) or not isinstance(mapping, dict):
                errors.append("native_header_mapping_missing")
            else:
                required_header_roles = {"record_key"}
                if not required_header_roles <= mapping.keys():
                    errors.append("native_record_key_mapping_missing")
                if not ({"ingredient", "product", "preference", "store", "category", "price"}
                        & mapping.keys()):
                    errors.append("grocery_context_header_mapping_missing")
                for role, index in mapping.items():
                    if not isinstance(index, int) or not 0 <= index < len(headers):
                        errors.append("native_header_mapping_invalid")
                        break
                if not isinstance(event.get("row_count"), int) or event["row_count"] < 1:
                    errors.append("bounded_grocery_content_missing")
        elif event.get("purpose") == "routing":
            valid_route_reads.append(event)
            headers = event.get("headers")
            mapping = event.get("header_map")
            if not isinstance(headers, list) or not isinstance(mapping, dict) \
                    or not {"record_key", "record_role", "tab_name"} <= mapping.keys():
                errors.append("native_routing_headers_missing")
            elif any(not isinstance(index, int) or not 0 <= index < len(headers)
                     for index in mapping.values()):
                errors.append("native_routing_header_mapping_invalid")
            if not isinstance(event.get("row_count"), int) or event["row_count"] < 1:
                errors.append("native_routing_rows_missing")
        elif event.get("purpose") == "workbook_context":
            if not isinstance(headers, list) or not headers \
                    or not isinstance(event.get("row_count"), int) or event["row_count"] < 1:
                errors.append("supporting_workbook_context_missing")
        elif event.get("purpose") == "post_read_state_check":
            if not isinstance(headers, list) or not headers \
                    or not isinstance(event.get("row_count"), int) or event["row_count"] < 1:
                errors.append("post_read_context_missing")
        else:
            errors.append("native_read_purpose_unrecognized")

    if not valid_context_reads:
        errors.append("bounded_grocery_content_missing")
    resolve_positions = [event["seq"] for event in resolves]
    metadata_positions = [event["seq"] for event in metadata]
    context_positions = [event["seq"] for event in valid_context_reads]
    routing_positions = [event["seq"] for event in valid_route_reads]
    post_read_positions = [event["seq"] for event in reads
                           if event.get("purpose") == "post_read_state_check"]
    if not resolve_positions or not metadata_positions or not context_positions \
            or max(resolve_positions) >= min(metadata_positions) \
            or max(metadata_positions) >= min(context_positions):
        errors.append("native_operation_order_invalid")
    route = receipt.get("route_resolution")
    if isinstance(route, dict) and route.get("basis") == "record_index" \
            and (not routing_positions or max(metadata_positions, default=0) >= min(routing_positions)
                 or max(routing_positions) >= min(context_positions, default=0)):
        errors.append("native_operation_order_invalid")
    if not post_read_positions or not context_positions \
            or max(context_positions) >= min(post_read_positions) \
            or max(post_read_positions) != len(operations):
        errors.append("native_operation_order_invalid")
    route = receipt.get("route_resolution")
    route_valid = False
    if isinstance(route, dict) and route.get("native_role") == "grocery-authority" \
            and str(route.get("sheet_id", "")) in sheets:
        if route.get("basis") == "record_index":
            route_valid = any(event.get("event_id") == route.get("source_event_id")
                              and event.get("sheet_id") == route.get("routing_sheet_id")
                              and event.get("resolved_target_sheet_id") == route.get("sheet_id")
                              for event in valid_route_reads)
        elif route.get("basis") == "native_header_map":
            route_valid = any(event.get("event_id") == route.get("source_event_id")
                              and event.get("sheet_id") == route.get("sheet_id")
                              for event in valid_context_reads)
    if not route_valid:
        errors.append("native_role_resolution_missing")

    state_check = receipt.get("post_read_state_check")
    if not isinstance(state_check, dict) or state_check.get("write_count") != 0 \
            or state_check.get("unchanged") is not True:
        errors.append("read_only_final_state_unverified")
    else:
        source = next((event for event in valid_context_reads
                       if event.get("event_id") == state_check.get("source_event_id")), None)
        check_event = next((event for event in reads
                            if event.get("event_id") == state_check.get("check_event_id")
                            and event.get("purpose") == "post_read_state_check"), None)
        if not source or not check_event \
                or check_event.get("source_event_id") != source.get("event_id") \
                or check_event.get("sheet_id") != source.get("sheet_id") \
                or check_event.get("range_sha256") != source.get("range_sha256") \
                or state_check.get("before_sha256") != source.get("content_sha256") \
                or state_check.get("after_sha256") != check_event.get("content_sha256") \
                or state_check.get("before_sha256") != state_check.get("after_sha256"):
            errors.append("read_only_final_state_mismatch")

    errors = sorted(set(errors))
    if errors:
        return {"status": "blocked", "accepted": False, "issues": errors}
    if kind == "deterministic-control":
        return {"status": "control-only", "accepted": False, "issues": []}
    return {"status": "accepted", "accepted": True, "issues": []}


def load_private_inputs(config_path: str | None, receipt_path: str | None) -> tuple[Any, Any, list[str]]:
    """Load private inputs without returning their path or contents in diagnostics."""
    errors: list[str] = []
    if not config_path:
        errors.append("missing_private_config_path")
    if not receipt_path:
        errors.append("missing_receipt_path")
    if errors:
        return None, None, errors
    try:
        config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        config = None
        errors.append("private_config_unavailable_or_invalid")
    try:
        receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        receipt = None
        errors.append("receipt_unavailable_or_invalid")
    return config, receipt, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", help="private same-run host receipt")
    parser.add_argument("--shopping-host-capture", help="private complete JSONL host capture from the same run")
    parser.add_argument("--config", default=os.environ.get("SHOPPING_LIVE_CONFIG"),
                        help="private expected-resource configuration (or SHOPPING_LIVE_CONFIG)")
    args = parser.parse_args(argv)
    config, receipt, errors = load_private_inputs(args.config, args.receipt)
    if errors:
        result = {"status": "blocked", "accepted": False, "issues": errors}
    else:
        result = validate_receipt(
            receipt,
            config,
            locator=os.environ.get("SHOPPING_CANONICAL_GROCERY_LOCATOR", ""),
            run_id=os.environ.get("SHOPPING_LIVE_RUN_ID", ""),
            key=os.environ.get("SHOPPING_LIVE_RECEIPT_KEY", ""),
            host_capture_path=args.shopping_host_capture,
        )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["accepted"] else 2


if __name__ == "__main__":
    sys.exit(main())
