#!/usr/bin/env python3
"""Build a redacted R25 receipt from one private, captured Codex invocation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import check_trial


SKILL_ID = "personal-shopper:personal-shopper"
READ_TOOLS = {
    "get_file_metadata", "get_spreadsheet_metadata", "get_spreadsheet_range", "get_spreadsheet_cells",
}
DISCOVERY_TOOLS = {"list_mcp_resources", "list_mcp_resource_templates"}
PROVIDER_TOOLS = {
    "get_file_metadata", "get_spreadsheet_metadata", "get_spreadsheet_range", "get_spreadsheet_cells",
}
SENSITIVE_NAME = re.compile(r"(?:TOKEN|SECRET|PASSWORD|CREDENTIAL|SHOPPING|GOOGLE|SHEETS)", re.I)


class ReceiptBuildError(ValueError):
    """A private capture cannot support an R25 receipt."""


def _fail(code: str) -> None:
    raise ReceiptBuildError(code)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _locator_native_id(locator: str) -> str | None:
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
    query_ids = parse_qs(parsed.query).get("id", [])
    return query_ids[0] if query_ids else None


def _private_file(path: str | Path) -> Path:
    value = Path(path).expanduser()
    if value.is_symlink() or not value.is_file():
        _fail("private_input_unavailable")
    value = value.resolve(strict=True)
    if check_trial.REPO_ROOT.resolve() == value or check_trial.REPO_ROOT.resolve() in value.parents:
        _fail("private_input_inside_repository")
    if stat.S_IMODE(value.stat().st_mode) & 0o077:
        _fail("private_input_permissions_invalid")
    return value


def _private_dir(path: str | Path) -> Path:
    value = Path(path).expanduser()
    if value.is_symlink() or not value.is_dir():
        _fail("private_capture_unavailable")
    value = value.resolve(strict=True)
    if check_trial.REPO_ROOT.resolve() == value or check_trial.REPO_ROOT.resolve() in value.parents:
        _fail("private_capture_inside_repository")
    if stat.S_IMODE(value.stat().st_mode) & 0o077:
        _fail("private_capture_permissions_invalid")
    return value


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _fail("private_json_invalid")


def _iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result.astimezone(timezone.utc) if result.tzinfo else None


def _tool_identity(call: dict[str, Any]) -> tuple[str, str] | None:
    server = str(call.get("server", "")).lower().replace("_", "-")
    tool = str(call.get("tool", ""))
    if server == "codex-apps" and tool.startswith("google_drive."):
        return "google-drive", tool.split(".", 1)[1]
    if server in check_trial.ALLOWED_HOST_SERVERS:
        if tool.startswith("google_drive."):
            tool = tool.split(".", 1)[1]
        return server, tool
    if server.startswith("mcp--codex-apps--google-drive"):
        if tool.startswith("google_drive."):
            tool = tool.split(".", 1)[1]
        return "google-drive", tool
    return None


def _unwrap(result: Any) -> Any:
    if isinstance(result, dict):
        value = result.get("structured_content", result.get("structuredContent"))
        if isinstance(value, (dict, list)):
            return value
    return result


def _call_ledger(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for index, event in enumerate(events):
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "mcp_tool_call":
            continue
        call_id, server = item.get("id"), item.get("server")
        tool = item.get("tool") or item.get("name")
        if not all(isinstance(value, str) and value for value in (call_id, server, tool)):
            _fail("host_tool_event_invalid")
        if call_id not in calls:
            calls[call_id] = {
                "call_id": call_id, "server": server, "tool": tool,
                "arguments": None, "result": None, "error": None,
                "status": "incomplete", "event_indexes": [], "first_index": index,
            }
            order.append(call_id)
        call = calls[call_id]
        if (call["server"], call["tool"]) != (server, tool):
            _fail("host_tool_identity_changed")
        arguments = item.get("arguments", item.get("input"))
        if arguments is not None:
            if call["arguments"] is not None and call["arguments"] != arguments:
                _fail("host_tool_arguments_changed")
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
        elif event.get("type") == "item.completed":
            call["status"] = "completed"
        elif event.get("type") in {"item.failed", "turn.failed", "error"}:
            call["status"] = "failed"
    return [calls[key] for key in order]


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [entry for key, item in value.items() for entry in [*_strings(key), *_strings(item)]]
    if isinstance(value, list):
        return [entry for item in value for entry in _strings(item)]
    return []


def _range_value(arguments: Any) -> str | None:
    if not isinstance(arguments, dict):
        return None
    value = arguments.get("range")
    if isinstance(value, str):
        return value
    ranges = arguments.get("ranges")
    return ranges[0] if isinstance(ranges, list) and len(ranges) == 1 and isinstance(ranges[0], str) else None


def _sheet_name(arguments: Any, range_value: str | None) -> str | None:
    if isinstance(arguments, dict) and isinstance(arguments.get("sheet_name"), str):
        return arguments["sheet_name"].strip().strip("'\"").replace("''", "'")
    if isinstance(range_value, str) and "!" in range_value:
        return range_value.rsplit("!", 1)[0].strip("'\"").replace("''", "'")
    return None


def _values(call: dict[str, Any]) -> list[list[Any]] | None:
    result = _unwrap(call.get("result"))
    values = result.get("values") if isinstance(result, dict) else None
    return values if isinstance(values, list) and values and all(isinstance(row, list) for row in values) else None


def _headers(values: list[list[Any]]) -> list[Any]:
    return values[0] if values else []


def _header_index(headers: list[Any], name: str) -> int | None:
    normalized = name.strip().casefold()
    return next((index for index, value in enumerate(headers)
                 if isinstance(value, str) and value.strip().casefold() == normalized), None)


def _metadata_sheets(metadata: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    sheets = metadata.get("sheets")
    if not isinstance(sheets, list):
        _fail("native_metadata_missing_sheets")
    by_name: dict[str, str] = {}
    receipts: dict[str, list[str]] = {}
    for sheet in sheets:
        props = sheet.get("properties", sheet) if isinstance(sheet, dict) else None
        if not isinstance(props, dict) or not isinstance(props.get("title"), str) \
                or props.get("sheetId") is None:
            _fail("native_metadata_sheet_invalid")
        name, sheet_id = props["title"], str(props["sheetId"])
        if name in by_name or sheet_id in receipts and name in receipts[sheet_id]:
            _fail("native_metadata_sheet_duplicate")
        by_name[name] = sheet_id
        receipts.setdefault(sheet_id, []).append(name)
    return by_name, [{"sheet_id": key, "names": names} for key, names in receipts.items()]


def _validate_runtime(trial: dict[str, Any], settings: dict[str, Any], prompt: str,
                      run_id: str, candidate_hash: str, suite_hash: str,
                      locator: str) -> None:
    if trial.get("trial_status") != "captured" or trial.get("complete") is not True \
            or trial.get("profile_id") != "r25" or trial.get("skill_id") != SKILL_ID \
            or trial.get("candidate_skill_id") != SKILL_ID or run_id != trial.get("run_id"):
        _fail("host_activation_missing")
    if SKILL_ID not in trial.get("requested_skill_ids", []) \
            or SKILL_ID not in trial.get("skill_discovery", {}).get("candidate_skills", []):
        _fail("candidate_skill_discovery_missing")
    if not trial.get("source_candidate_unchanged") or not trial.get("candidate_profile_unchanged") \
            or not trial.get("suite_identity_unchanged"):
        _fail("candidate_or_suite_changed_during_run")
    if trial.get("source_candidate_sha256_before") != candidate_hash \
            or trial.get("source_candidate_sha256_after") != candidate_hash \
            or trial.get("suite_sha256_before") != suite_hash \
            or trial.get("suite_sha256_after") != suite_hash:
        _fail("candidate_or_suite_identity_mismatch")
    if settings.get("profile_id") != "r25" or settings.get("sandbox") != "read-only" \
            or settings.get("fresh_session") is not True \
            or settings.get("isolated_codex_home") is not True \
            or settings.get("global_user_profile_unchanged") is not True:
        _fail("isolated_read_only_profile_missing")
    trial_started = _iso(trial.get("capture_started_at"))
    settings_started = _iso(settings.get("capture_started_at"))
    settings_completed = _iso(settings.get("capture_completed_at"))
    if not trial_started or settings_started != trial_started or not settings_completed \
            or settings_completed < settings_started or settings_completed > datetime.now(timezone.utc):
        _fail("activation_capture_times_invalid")
    if set(settings.get("installed_plugins", {})) != {"personal-shopper", "google-drive"}:
        _fail("unexpected_installed_plugin_set")
    policies = settings.get("provider_apps")
    if not isinstance(policies, list) or len(policies) != 1 \
            or policies[0].get("plugin") != "google-drive" \
            or set(policies[0].get("tools", [])) != PROVIDER_TOOLS:
        _fail("provider_read_tool_allowlist_mismatch")
    environment_names = settings.get("child_environment_names", [])
    if not isinstance(environment_names, list) or any(
        isinstance(name, str) and SENSITIVE_NAME.search(name) for name in environment_names
    ):
        _fail("private_environment_passed_to_candidate")
    if SKILL_ID not in prompt or run_id not in prompt or locator.strip() not in prompt:
        _fail("private_runtime_input_not_bound_to_activation")


def build_receipt(trial_dir: str | Path, *, config_path: str | Path,
                  locator_path: str | Path, key_path: str | Path) -> dict[str, Any]:
    """Derive a private receipt only from one completed R25 Codex capture."""
    trial_root = _private_dir(trial_dir)
    config_file = _private_file(config_path)
    locator_file = _private_file(locator_path)
    key_file = _private_file(key_path)
    config = _read_json(config_file)
    locator = locator_file.read_text(encoding="utf-8").strip()
    key = key_file.read_text(encoding="utf-8").strip()
    if not isinstance(config, dict) or set(config) != {"schema_version", "expected_resource"} \
            or config.get("schema_version") != 1 or not locator or len(key) < 32:
        _fail("private_live_inputs_invalid")
    expected = config.get("expected_resource")
    if not isinstance(expected, dict) or set(expected) != {"provider", "native_id"} \
            or expected.get("provider") != "google-sheets" \
            or not isinstance(expected.get("native_id"), str) or not expected["native_id"]:
        _fail("private_expected_identity_invalid")

    trial = _read_json(_private_file(trial_root / "trial-result.json"))
    settings = _read_json(_private_file(trial_root / "runtime-settings.json"))
    prompt = _private_file(trial_root / "invocation-prompt.txt").read_text(encoding="utf-8")
    run_id = trial_root.name
    candidate_hash = check_trial.candidate_digest()
    suite_hash = check_trial.suite_digest()
    _validate_runtime(trial, settings, prompt, run_id, candidate_hash, suite_hash, locator)

    trace_path = _private_file(trial_root / "host-events.jsonl")
    times_path = _private_file(trial_root / "host-event-times.jsonl")
    raw = trace_path.read_bytes()
    if not raw.endswith(b"\n"):
        _fail("incomplete_host_capture")
    try:
        events = [json.loads(line) for line in raw.splitlines()]
        times = [json.loads(line) for line in times_path.read_text(encoding="utf-8").splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        _fail("host_capture_invalid")
    if not events or len(events) != len(times) or events[0].get("type") != "thread.started" \
            or events[-1].get("type") != "turn.completed":
        _fail("host_capture_incomplete")
    if any(record.get("line") != index or _iso(record.get("observed_at")) is None
           for index, record in enumerate(times)):
        _fail("host_event_timestamps_invalid")
    session_id = events[0].get("thread_id")
    if not isinstance(session_id, str) or not session_id:
        _fail("host_session_missing")
    calls = _call_ledger(events)
    if not calls or len(calls) != trial.get("tool_call_count") \
            or len(events) != trial.get("event_count"):
        _fail("host_trace_counts_mismatch")

    started = _iso(trial.get("capture_started_at"))
    completed = _iso(settings.get("capture_completed_at"))
    now = datetime.now(timezone.utc)
    if not started or not completed or completed < started or completed > now \
            or (now - completed).total_seconds() > check_trial.MAX_RECEIPT_AGE_SECONDS:
        _fail("activation_receipt_stale_or_invalid")

    native_calls = []
    for call in calls:
        if call.get("status") != "completed" or call.get("error") is not None \
                or call.get("arguments") is None or call.get("result") is None:
            _fail("host_tool_call_failed_or_incomplete")
        if call.get("server") == "codex" and call.get("tool") in DISCOVERY_TOOLS:
            if call.get("arguments") not in (None, {}):
                _fail("host_resource_discovery_unexpected_arguments")
            continue
        identity = _tool_identity(call)
        if identity is None or identity[1] not in READ_TOOLS:
            _fail("unapproved_or_unexplained_host_tool_call")
        native_calls.append(call)

    metadata_calls = [call for call in native_calls if _tool_identity(call)[1] == "get_spreadsheet_metadata"]
    if len(metadata_calls) != 1:
        _fail("native_metadata_call_count_invalid")
    metadata_call = metadata_calls[0]
    resolver_calls = [call for call in native_calls if _tool_identity(call)[1] == "get_file_metadata"]
    if len(resolver_calls) > 1:
        _fail("native_file_resolution_call_count_invalid")
    expected_locator_id = _locator_native_id(locator)
    if expected_locator_id != expected["native_id"]:
        _fail("runtime_locator_identity_invalid")
    if resolver_calls:
        resolve_call = resolver_calls[0]
        drive_file = _unwrap(resolve_call.get("result"))
        if not isinstance(drive_file, dict) or drive_file.get("id") != expected["native_id"] \
                or drive_file.get("mime_type") != "application/vnd.google-apps.spreadsheet" \
                or expected["native_id"] not in _strings(resolve_call.get("arguments")):
            _fail("native_file_resolution_unrecognized")
    else:
        resolve_call = metadata_call
        if expected["native_id"] not in _strings(resolve_call.get("arguments")):
            _fail("runtime_locator_not_used")
    if locator.strip() not in _strings(metadata_call.get("arguments")):
        if expected["native_id"] not in _strings(metadata_call.get("arguments")):
            _fail("runtime_locator_not_used")
    metadata = _unwrap(metadata_call.get("result"))
    if not isinstance(metadata, dict) or metadata.get("spreadsheetId") != expected["native_id"]:
        _fail("canonical_identity_mismatch")
    sheet_ids, native_sheets = _metadata_sheets(metadata)

    range_calls = [call for call in native_calls if _tool_identity(call)[1] in {
        "get_spreadsheet_range", "get_spreadsheet_cells",
    }]
    if not range_calls:
        _fail("native_content_read_missing")
    reads: list[dict[str, Any]] = []
    for call in range_calls:
        values = _values(call)
        args = call.get("arguments")
        range_value = _range_value(args)
        tab = _sheet_name(args, range_value)
        area = check_trial._a1_range_area(range_value) if range_value else None
        if values is None or not isinstance(range_value, str) or area is None \
                or area < 1 or area > check_trial.MAX_RANGE_CELLS \
                or tab not in sheet_ids:
            _fail("native_range_unbounded_or_unrecognized")
        reads.append({"call": call, "values": values, "range": range_value,
                      "sheet_name": tab, "sheet_id": sheet_ids[tab], "area": area,
                      "first_index": call["first_index"]})

    routing_headers_required = {"worksheet", "stable key column", "role"}
    routing_reads = []
    for read in reads:
        normalized_headers = {value.strip().casefold() for value in _headers(read["values"])
                              if isinstance(value, str)}
        if routing_headers_required <= normalized_headers:
            routing_reads.append(read)
    if len(routing_reads) > 1:
        _fail("native_routing_read_ambiguous")
    routing_read = routing_reads[0] if routing_reads else None
    route_rows: list[dict[str, Any]] = []
    if routing_read:
        headers = _headers(routing_read["values"])
        tab_index = _header_index(headers, "Worksheet")
        key_index = _header_index(headers, "Stable Key Column")
        role_index = _header_index(headers, "Role")
        if None in (tab_index, key_index, role_index):
            _fail("native_routing_headers_invalid")
        for row in routing_read["values"][1:]:
            if max(tab_index, key_index, role_index) >= len(row):
                continue
            route_rows.append({
                "tab": str(row[tab_index]).strip(),
                "stable_key": str(row[key_index]).strip(),
                "role": str(row[role_index]).strip(),
            })

    relevant_headers = {"ingredient", "product", "preference", "store", "category", "price"}
    content_reads = []
    routing_call_id = routing_read["call"]["call_id"] if routing_read else None
    for read in reads:
        if read["call"]["call_id"] == routing_call_id:
            continue
        headers = _headers(read["values"])
        if not any(isinstance(value, str) and value.strip().casefold() in relevant_headers for value in headers):
            continue
        route = next((entry for entry in route_rows
                      if entry["tab"] == read["sheet_name"]
                      and entry["role"].casefold() in {"current", "grocery", "grocery authority"}), None)
        stable_key = route["stable_key"] if route else "Record ID"
        key_index = _header_index(headers, stable_key)
        if key_index is None:
            continue
        if not any(key_index < len(row) and str(row[key_index]).strip() for row in read["values"][1:]):
            continue
        content_reads.append({**read, "stable_key": stable_key, "key_index": key_index,
                              "route": route})
    if not content_reads:
        _fail("bounded_grocery_content_missing")

    pairs = []
    for content in content_reads:
        for post in content_reads:
            if post["first_index"] > content["first_index"] \
                    and post["sheet_name"] == content["sheet_name"] \
                    and post["range"] == content["range"] \
                    and post["values"] == content["values"]:
                pairs.append((content, post))
    if not pairs:
        _fail("matching_post_read_missing")
    content_read, post_read = min(pairs, key=lambda pair: (pair[0]["first_index"], pair[1]["first_index"]))
    explained_call_ids = {
        content_read["call"]["call_id"], post_read["call"]["call_id"],
        *([routing_read["call"]["call_id"]] if routing_read else []),
    }
    supporting_reads = [read for read in reads if read["call"]["call_id"] not in explained_call_ids]
    if len(supporting_reads) > 1 or any(not _headers(read["values"]) for read in supporting_reads):
        _fail("supporting_context_read_invalid")

    run_prefix = f"{run_id}:operation:"
    operations: list[dict[str, Any]] = []
    call_timestamp: dict[str, str] = {}
    for call in calls:
        last_index = call["event_indexes"][-1]
        call_timestamp[call["call_id"]] = times[last_index]["observed_at"]

    def base_operation(call: dict[str, Any], operation: str) -> dict[str, Any]:
        timestamp = call_timestamp[call["call_id"]]
        if not started <= _iso(timestamp) <= completed:
            _fail("tool_event_outside_activation")
        return {
            "seq": len(operations) + 1,
            "event_id": run_prefix + str(len(operations) + 1),
            "tool_call_id": call["call_id"],
            "trace_event_indexes": call["event_indexes"],
            "session_id": session_id,
            "run_id": run_id,
            "timestamp": timestamp,
            "operation": operation,
            "provider": "google-sheets",
            "native_id": expected["native_id"],
            "source": "connected_google_drive_native_sheets_tool",
            "request_sha256": hashlib.sha256(_canonical_json(call.get("arguments"))).hexdigest(),
            "result_sha256": hashlib.sha256(_canonical_json(call.get("result"))).hexdigest(),
        }

    locator_hash = hashlib.sha256(locator.strip().encode()).hexdigest()
    resolve = base_operation(resolve_call, "resolve")
    resolve.update({"resolved": True, "requested_locator_sha256": locator_hash})
    operations.append(resolve)
    metadata_operation = base_operation(metadata_call, "metadata")
    metadata_operation["native_sheets"] = native_sheets
    operations.append(metadata_operation)

    read_operation_by_call: dict[str, dict[str, Any]] = {}
    content_call_id = content_read["call"]["call_id"]
    post_call_id = post_read["call"]["call_id"]
    routing_call_id = routing_read["call"]["call_id"] if routing_read else None
    for read in sorted(reads, key=lambda item: item["first_index"]):
        call = read["call"]
        if call["call_id"] == post_call_id:
            continue
        operation = base_operation(call, "read_values")
        values = read["values"]
        headers = _headers(values)
        cell_count = sum(len(row) for row in values)
        if call["call_id"] == routing_call_id:
            purpose = "routing"
        elif call["call_id"] == content_call_id:
            purpose = "grocery_context"
        else:
            purpose = "workbook_context"
        operation.update({
            "purpose": purpose,
            "sheet_id": read["sheet_id"],
            "bounded": True,
            "cell_count": cell_count,
            "row_count": max(0, len(values) - 1),
            "headers": headers,
            "content_sha256": _hash(values),
            "range_sha256": hashlib.sha256(read["range"].encode()).hexdigest(),
        })
        if purpose == "routing":
            operation["header_map"] = {
                "tab_name": _header_index(headers, "Worksheet"),
                "record_key": _header_index(headers, "Stable Key Column"),
                "record_role": _header_index(headers, "Role"),
            }
            target = next((entry for entry in route_rows
                           if entry["tab"] == content_read["sheet_name"]
                           and entry["role"].casefold() in {"current", "grocery", "grocery authority"}), None)
            if target is None or target["stable_key"].casefold() != content_read["stable_key"].casefold():
                _fail("record_index_does_not_route_content_read")
            operation["resolved_target_sheet_id"] = content_read["sheet_id"]
        elif purpose == "grocery_context":
            key_name = content_read["stable_key"]
            header_map = {"record_key": _header_index(headers, key_name)}
            for role_name in ("ingredient", "product", "preference", "store", "category", "price"):
                index = _header_index(headers, role_name)
                if index is not None:
                    header_map[role_name] = index
                    break
            if header_map["record_key"] is None or len(header_map) < 2:
                _fail("grocery_header_mapping_missing")
            operation["header_map"] = header_map
        elif not headers:
            _fail("supporting_context_headers_missing")
        read_operation_by_call[call["call_id"]] = operation
        operations.append(operation)

    if post_read is None:
        _fail("matching_post_read_missing")
    source_operation = read_operation_by_call.get(content_read["call"]["call_id"])
    if source_operation is None:
        _fail("grocery_context_receipt_missing")
    post_operation = base_operation(post_read["call"], "read_values")
    post_operation.update({
        "purpose": "post_read_state_check",
        "source_event_id": source_operation["event_id"],
        "sheet_id": post_read["sheet_id"],
        "bounded": True,
        "cell_count": sum(len(row) for row in post_read["values"]),
        "row_count": max(0, len(post_read["values"]) - 1),
        "headers": _headers(post_read["values"]),
        "content_sha256": _hash(post_read["values"]),
        "range_sha256": hashlib.sha256(post_read["range"].encode()).hexdigest(),
    })
    operations.append(post_operation)

    if routing_read:
        route_operation = read_operation_by_call.get(routing_read["call"]["call_id"])
        if route_operation is None:
            _fail("native_routing_receipt_missing")
        route_resolution = {
            "native_role": "grocery-authority",
            "basis": "record_index",
            "source_event_id": route_operation["event_id"],
            "routing_sheet_id": routing_read["sheet_id"],
            "sheet_id": content_read["sheet_id"],
        }
    else:
        route_resolution = {
            "native_role": "grocery-authority",
            "basis": "native_header_map",
            "source_event_id": source_operation["event_id"],
            "sheet_id": content_read["sheet_id"],
        }

    digest = source_operation["content_sha256"]
    receipt = {
        "schema_version": 1,
        "receipt_schema": "personal-shopper-live-receipt/v2",
        "evidence_kind": "host-activation",
        "run_id": run_id,
        "candidate_sha256": candidate_hash,
        "suite_sha256": suite_hash,
        "requested_locator_sha256": locator_hash,
        "resource": {"provider": expected["provider"], "native_id": expected["native_id"]},
        "activation": {
            "skill_id": SKILL_ID,
            "activated": True,
            "session_id": session_id,
            "run_id": run_id,
            "candidate_sha256": candidate_hash,
            "started_at": trial["capture_started_at"],
            "completed_at": settings["capture_completed_at"],
        },
        "runtime": {
            "credentials_available": True,
            "connected_google_sheets_tool_available": True,
            "read_only_envelope": True,
            "host_receipt_source": "actual_host_tool_trace",
        },
        "tool_trace_sha256": hashlib.sha256(raw).hexdigest(),
        "tool_trace_event_count": len(events),
        "tool_trace_call_count": len(calls),
        "operations": operations,
        "route_resolution": route_resolution,
        "post_read_state_check": {
            "source_event_id": source_operation["event_id"],
            "check_event_id": post_operation["event_id"],
            "before_sha256": digest,
            "after_sha256": post_operation["content_sha256"],
            "write_count": 0,
            "unchanged": digest == post_operation["content_sha256"],
        },
    }
    receipt["attestation"] = {
        "algorithm": "hmac-sha256",
        "digest": check_trial.sign_receipt(receipt, key),
    }
    return receipt


def write_receipt(receipt: dict[str, Any], output_path: str | Path) -> Path:
    output = Path(output_path).expanduser()
    parent = output.parent.resolve(strict=True)
    if check_trial.REPO_ROOT.resolve() == parent or check_trial.REPO_ROOT.resolve() in parent.parents:
        _fail("receipt_output_inside_repository")
    if stat.S_IMODE(parent.stat().st_mode) & 0o077 or output.exists() or output.is_symlink():
        _fail("receipt_output_permissions_or_state_invalid")
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    os.chmod(output, 0o600)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial_dir", type=Path, help="private completed R25 capture directory")
    parser.add_argument("--config", required=True, help="private expected-resource config")
    parser.add_argument("--locator-file", required=True, help="private runtime locator file")
    parser.add_argument("--key-file", required=True, help="private HMAC key file")
    parser.add_argument("--output", required=True, help="new private receipt path")
    args = parser.parse_args(argv)
    try:
        receipt = build_receipt(args.trial_dir, config_path=args.config,
                                locator_path=args.locator_file, key_path=args.key_file)
        write_receipt(receipt, args.output)
    except ReceiptBuildError as error:
        print(json.dumps({"status": "blocked", "reason": str(error)}))
        return 2
    print(json.dumps({
        "status": "created",
        "evidence_kind": receipt["evidence_kind"],
        "operation_count": len(receipt["operations"]),
        "tool_trace_event_count": receipt["tool_trace_event_count"],
        "tool_trace_call_count": receipt["tool_trace_call_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
