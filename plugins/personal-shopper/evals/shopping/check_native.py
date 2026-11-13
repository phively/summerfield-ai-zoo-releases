"""Validate private host captures for native Sheets preservation trials."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tomllib
from typing import Any

import build_live_receipt as live
import check_trial
import capture_work_browser
import private_evidence


REPO_ROOT = check_trial.REPO_ROOT.resolve()
PROFILE_ID = "native-sheets-preservation"
SKILL_ID = "personal-shopper:personal-shopper"
ALLOWED_TOOLS = {
    "get_file_metadata", "get_spreadsheet_metadata", "get_spreadsheet_range",
    "get_spreadsheet_cells", "batch_update_spreadsheet",
}


_acl_is_private = private_evidence.acl_is_private
_private_permissions = private_evidence.private_permissions
_private_file = private_evidence.private_file


def _private_capture(path: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(REPO_ROOT)
        return False
    except ValueError:
        pass
    except OSError:
        return False
    return private_evidence.private_directory(path)


def _skill_resource(call: dict[str, Any], trial: dict[str, Any]) -> str | None:
    if call.get("server") != "shopping-skill-resources" \
            or call.get("tool") != "read_installed_skill_file":
        return None
    args = call.get("arguments")
    if not isinstance(args, dict) or set(args) != {"relative_path"}:
        return None
    relative = args["relative_path"]
    if not isinstance(relative, str) or "\\" in relative:
        return None
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or str(path) != relative or not relative.endswith(".md"):
        return None
    result = live._unwrap(call.get("result"))
    if isinstance(result, dict) and "text" not in result:
        content = result.get("content")
        if not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict) \
                or content[0].get("type") != "text":
            return None
        try:
            result = json.loads(content[0]["text"])
        except (KeyError, TypeError, json.JSONDecodeError):
            return None
    if not isinstance(result, dict) or result.get("relative_path") != relative \
            or not isinstance(result.get("text"), str):
        return None
    key = "personal-shopper/skills/personal-shopper/" + relative
    digest = hashlib.sha256(result["text"].encode("utf-8")).hexdigest()
    if result.get("sha256") != digest or trial.get("installed_file_sha256", {}).get(key) != digest:
        return None
    source = REPO_ROOT / "plugins" / key
    try:
        if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            return None
    except OSError:
        return None
    return relative


def _json(path: Path) -> Any:
    if not _private_file(path):
        raise ValueError
    return json.loads(path.read_text(encoding="utf-8"))


def _native_ids(value: Any) -> set[str]:
    result = set()
    for item in live._strings(value):
        native_id = live._locator_native_id(item)
        if native_id:
            result.add(native_id)
    return result


def _a1_range(value: str) -> tuple[str, int, int, int, int] | None:
    match = re.fullmatch(r"(?:'((?:[^']|'')+)'|([^!]+))!\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)", value)
    if not match:
        return None
    title = (match.group(1).replace("''", "'") if match.group(1) else match.group(2)).strip()

    def column_index(letters: str) -> int:
        index = 0
        for char in letters:
            index = index * 26 + ord(char) - ord("A") + 1
        return index - 1

    first_col, first_row = column_index(match.group(3)), int(match.group(4)) - 1
    last_col, last_row = column_index(match.group(5)), int(match.group(6)) - 1
    if first_row < 0 or first_col < 0 or last_row < first_row or last_col < first_col:
        return None
    return title, first_row, last_row + 1, first_col, last_col + 1


def _ranges(call: dict[str, Any]) -> list[str]:
    args = call.get("arguments")
    values = args.get("ranges") if isinstance(args, dict) else None
    return [value for value in values if isinstance(value, str)] if isinstance(values, list) else []


def _call_index(call: dict[str, Any]) -> int:
    indexes = call.get("event_indexes")
    return min(indexes) if isinstance(indexes, list) and indexes else -1


def _sheet_title(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    title = value.strip()
    if len(title) >= 2 and title[0] == title[-1] and title[0] in "'\"":
        quote = title[0]
        title = title[1:-1].replace(quote + quote, quote)
    return title


def _cell_map(call: dict[str, Any]) -> dict[tuple[int, int, int], dict[str, Any]]:
    result = live._unwrap(call.get("result"))
    cells: dict[tuple[int, int, int], dict[str, Any]] = {}
    sheets = result.get("sheets") if isinstance(result, dict) else None
    if not isinstance(sheets, list):
        return cells
    for sheet in sheets:
        props = sheet.get("properties", sheet) if isinstance(sheet, dict) else None
        if not isinstance(props, dict) or props.get("sheetId") is None:
            continue
        try:
            sheet_id = int(props["sheetId"])
        except (TypeError, ValueError):
            continue
        data_blocks = sheet.get("data", [])
        for block in data_blocks if isinstance(data_blocks, list) else []:
            if not isinstance(block, dict):
                continue
            try:
                start_row = int(block.get("startRow", 0))
                start_column = int(block.get("startColumn", 0))
            except (TypeError, ValueError):
                continue
            row_data = block.get("rowData", [])
            for row_offset, row in enumerate(row_data if isinstance(row_data, list) else []):
                values = row.get("values", []) if isinstance(row, dict) else []
                for column_offset, cell in enumerate(values if isinstance(values, list) else []):
                    if isinstance(cell, dict):
                        cells[(sheet_id, start_row + row_offset, start_column + column_offset)] = cell
    return cells


def _user_value(cell: dict[str, Any]) -> Any:
    value = cell.get("userEnteredValue")
    if not isinstance(value, dict):
        return value
    return next((value[key] for key in ("stringValue", "numberValue", "boolValue", "formulaValue")
                 if key in value), None)


def _valid_update(call: dict[str, Any], expected: dict[str, Any]) -> bool:
    if call.get("status") != "completed" or call.get("error") is not None:
        return False
    args = call.get("arguments")
    if not isinstance(args, dict) or _native_ids(args) != {expected["native_id"]}:
        return False
    requests = args.get("requests")
    if not isinstance(requests, list) or len(requests) != 1 or not isinstance(requests[0], dict):
        return False
    request = requests[0]
    if set(request) != {"updateCells"}:
        return False
    update = request["updateCells"]
    target = expected["target"]
    grid = update.get("range") if isinstance(update, dict) else None
    if not isinstance(grid, dict):
        return False
    if (grid.get("sheetId"), grid.get("startRowIndex"), grid.get("endRowIndex"),
            grid.get("startColumnIndex"), grid.get("endColumnIndex")) != (
            target["sheet_id"], target["row_index"], target["row_index"] + 1,
            target["column_index"], target["column_index"] + 1):
        return False
    if update.get("fields") != "userEnteredValue":
        return False
    rows = update.get("rows")
    if not isinstance(rows, list) or len(rows) != 1:
        return False
    values = rows[0].get("values") if isinstance(rows[0], dict) else None
    if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], dict):
        return False
    return _user_value(values[0]) == expected["target"]["after_value"]


def validate_capture(capture_path: str | Path, config_path: str | Path) -> dict[str, Any]:
    """Reconcile one captured native update against controller-held expectations."""
    issues: list[str] = []
    capture = Path(capture_path).expanduser()
    config_file = Path(config_path).expanduser()
    if not _private_capture(capture):
        return {"accepted": False, "status": "blocked", "issues": ["private_input_permissions_invalid"]}
    if not config_file.exists():
        return {"accepted": False, "status": "blocked", "issues": ["private_config_missing"]}
    if not _private_file(config_file):
        return {"accepted": False, "status": "blocked", "issues": ["private_input_permissions_invalid"]}
    try:
        config = _json(config_file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {"accepted": False, "status": "blocked", "issues": ["private_config_invalid"]}
    browser_capture = capture_work_browser.validate_archived_capture(capture, config)
    if browser_capture is not None:
        return browser_capture
    try:
        trial = _json(capture / "trial-result.json")
        settings = _json(capture / "runtime-settings.json")
        runtime_profile = _json(capture / "runtime-profile.json")
        prompt = (capture / "invocation-prompt.txt").read_text(encoding="utf-8")
        raw = (capture / "host-events.jsonl").read_bytes()
        runtime_config_path = capture / "runtime-config.toml"
        runtime_config = runtime_config_path.read_bytes()
        time_path = capture / "host-event-times.jsonl"
        if not _private_file(capture / "invocation-prompt.txt") or not _private_file(capture / "host-events.jsonl") \
                or not _private_file(time_path) or not _private_file(runtime_config_path):
            raise ValueError
        events = [json.loads(line) for line in raw.splitlines()]
        times = [json.loads(line) for line in time_path.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {"accepted": False, "status": "blocked", "issues": ["private_capture_invalid"]}

    if not isinstance(config, dict) or config.get("schema_version") != 1:
        return {"accepted": False, "status": "blocked", "issues": ["private_config_invalid"]}
    resource = config.get("expected_resource")
    target = config.get("target")
    if not isinstance(resource, dict) or resource.get("provider") != "google-sheets" \
            or not isinstance(resource.get("native_id"), str) or not isinstance(target, dict):
        return {"accepted": False, "status": "blocked", "issues": ["private_config_invalid"]}
    expected = {"native_id": resource["native_id"], "target": target}
    if target.get("after_value") == target.get("before_value"):
        issues.append("private_config_invalid")
    if trial.get("profile_id") != PROFILE_ID or trial.get("trial_status") != "captured" \
            or trial.get("complete") is not True or trial.get("candidate_skill_id") != SKILL_ID \
            or trial.get("skill_id") != SKILL_ID or not trial.get("candidate_profile_unchanged") \
            or not trial.get("suite_identity_unchanged") or settings.get("profile_id") != PROFILE_ID \
            or settings.get("fresh_session") is not True or settings.get("isolated_codex_home") is not True:
        issues.append("activation_profile_invalid")
    try:
        runtime_config_hash = hashlib.sha256(runtime_config).hexdigest()
        candidate_hash = check_trial.candidate_digest()
        suite_hash = check_trial.suite_digest()
        if runtime_profile.get("config_sha256") != runtime_config_hash \
                or settings.get("runtime_config_sha256") != runtime_config_hash:
            issues.append("runtime_config_identity_mismatch")
        if trial.get("source_candidate_sha256_before") != candidate_hash \
                or trial.get("source_candidate_sha256_after") != candidate_hash \
                or settings.get("source_candidate_sha256") != candidate_hash \
                or trial.get("suite_sha256_before") != suite_hash \
                or trial.get("suite_sha256_after") != suite_hash \
                or settings.get("suite_sha256") != suite_hash:
            issues.append("candidate_or_suite_identity_stale")
    except (OSError, ValueError, KeyError):
        issues.append("candidate_or_suite_identity_unavailable")
    try:
        parsed_runtime_config = tomllib.loads(runtime_config.decode("utf-8"))
        apps = parsed_runtime_config.get("apps")
        app_tables = {key: value for key, value in apps.items() if key != "_default"} \
            if isinstance(apps, dict) else {}
        if len(app_tables) != 1 or not isinstance(apps.get("_default"), dict) \
                or apps["_default"].get("enabled") is not False \
                or apps["_default"].get("default_tools_enabled") is not False:
            raise ValueError
        app_config = next(iter(app_tables.values()))
        tool_config = app_config.get("tools") if isinstance(app_config, dict) else None
        if not isinstance(tool_config, dict) or set(tool_config) != ALLOWED_TOOLS \
                or app_config.get("enabled") is not True \
                or app_config.get("default_tools_enabled") is not False \
                or app_config.get("destructive_enabled") is not False \
                or app_config.get("open_world_enabled") is not False \
                or any(not isinstance(tool, dict) or tool.get("enabled") is not True
                       for tool in tool_config.values()) \
                or tool_config["batch_update_spreadsheet"].get("approval_mode") != "approve" \
                or any("approval_mode" in tool for name, tool in tool_config.items()
                       if name != "batch_update_spreadsheet"):
            raise ValueError
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, ValueError, TypeError):
        issues.append("native_write_approval_profile_invalid")
    provider_apps = settings.get("provider_apps")
    if not isinstance(provider_apps, list) or len(provider_apps) != 1 \
            or not isinstance(provider_apps[0], dict) \
            or provider_apps[0].get("plugin") != "google-drive" \
            or set(provider_apps[0].get("tools", [])) != ALLOWED_TOOLS \
            or provider_apps[0].get("tool_approval_modes") != {
                "batch_update_spreadsheet": "approve"}:
        issues.append("provider_profile_invalid")

    run_id = capture.name
    if trial.get("run_id") != run_id or run_id not in prompt or SKILL_ID not in prompt \
            or expected["native_id"] not in prompt:
        issues.append("activation_prompt_identity_invalid")
    if not raw.endswith(b"\n") or not events or len(events) != len(times) \
            or events[0].get("type") != "thread.started" or events[-1].get("type") != "turn.completed" \
            or len(events) != trial.get("event_count"):
        issues.append("host_capture_incomplete")
    if any(item.get("line") != index or live._iso(item.get("observed_at")) is None
           for index, item in enumerate(times)):
        issues.append("host_capture_timestamps_invalid")

    calls = live._call_ledger(events)
    if len(calls) != trial.get("tool_call_count"):
        issues.append("host_call_count_mismatch")
    provider_calls = []
    resource_calls = {}
    for call in calls:
        if call.get("status") != "completed" or call.get("error") is not None \
                or call.get("arguments") is None or call.get("result") is None:
            issues.append("host_tool_call_incomplete")
            continue
        if call.get("server") == "shopping-skill-resources":
            relative = _skill_resource(call, trial)
            if relative is None:
                issues.append("installed_skill_resource_invalid")
            else:
                resource_calls.setdefault(relative, _call_index(call))
            continue
        identity = live._tool_identity(call)
        if identity is None and call.get("server") == "codex" and call.get("tool") in live.DISCOVERY_TOOLS \
                and call.get("arguments") in (None, {}):
            continue
        if identity is None or identity[0] != "google-drive" or identity[1] not in ALLOWED_TOOLS:
            issues.append("provider_tool_unapproved")
            continue
        if _native_ids(call.get("arguments")) != {expected["native_id"]}:
            issues.append("provider_identity_mismatch")
        provider_calls.append(call)

    file_metadata = [call for call in provider_calls if live._tool_identity(call)[1] == "get_file_metadata"]
    metadata = [call for call in provider_calls if live._tool_identity(call)[1] == "get_spreadsheet_metadata"]
    index_range = config.get("record_index_range")
    routing = [call for call in provider_calls if live._tool_identity(call)[1] == "get_spreadsheet_range"
               and live._range_value(call.get("arguments")) == index_range]
    cells = [call for call in provider_calls if live._tool_identity(call)[1] == "get_spreadsheet_cells"]
    writes = [call for call in provider_calls if live._tool_identity(call)[1] == "batch_update_spreadsheet"]
    required_resources = {"SKILL.md", "references/contracts/record-management.md"}
    if not required_resources.issubset(resource_calls):
        issues.append("installed_skill_activation_missing")
    elif writes and max(resource_calls[name] for name in required_resources) >= min(
            _call_index(call) for call in writes):
        issues.append("installed_skill_loaded_after_write")
    if len(file_metadata) != 1:
        issues.append("native_file_resolution_missing")
    elif live._unwrap(file_metadata[0].get("result")) is None \
            or live._unwrap(file_metadata[0].get("result")).get("id") != expected["native_id"] \
            or live._unwrap(file_metadata[0].get("result")).get("mime_type") \
            != "application/vnd.google-apps.spreadsheet":
        issues.append("native_file_resolution_mismatch")
    if len(metadata) != 1:
        issues.append("native_metadata_missing_or_ambiguous")
    elif live._unwrap(metadata[0].get("result")) is None \
            or live._unwrap(metadata[0].get("result")).get("spreadsheetId") != expected["native_id"]:
        issues.append("native_metadata_identity_mismatch")
    elif isinstance(live._unwrap(metadata[0].get("result")), dict):
        sheet_map = {}
        for sheet in live._unwrap(metadata[0].get("result")).get("sheets", []):
            props = sheet.get("properties", sheet) if isinstance(sheet, dict) else None
            if isinstance(props, dict) and props.get("sheetId") is not None:
                sheet_map[int(props["sheetId"])] = props.get("title")
        if sheet_map.get(int(target.get("sheet_id", -1))) != target.get("sheet_title") \
                or sheet_map.get(int(config.get("history_sheet_id", -2))) != config.get("history_sheet_title"):
            issues.append("native_metadata_sheet_mapping_mismatch")
    if len(routing) != 1 or not isinstance(index_range, str):
        issues.append("record_index_read_missing")
    else:
        values = live._values(routing[0]) or []
        headers = live._headers(values)
        args = routing[0].get("arguments")
        columns = {name: live._header_index(headers, name) for name in
                   ("Worksheet", "Stable Key Column", "Role")}
        if not isinstance(args, dict) or _sheet_title(args.get("sheet_name")) != config.get("record_index_sheet_title") \
                or any(index is None for index in columns.values()):
            issues.append("record_index_headers_missing")
        else:
            route_found = any(
                max(columns.values()) < len(row)
                and str(row[columns["Worksheet"]]).strip() == target.get("sheet_title")
                and str(row[columns["Stable Key Column"]]).strip() == target.get("stable_key_column")
                and str(row[columns["Role"]]).strip().casefold() == "current"
                for row in values[1:]
            )
            if not route_found:
                issues.append("record_index_route_mismatch")

    if len(cells) != 2:
        issues.append("native_before_after_read_missing")
    read_ranges = config.get("verification_ranges")
    if not isinstance(read_ranges, list) or not read_ranges or any(not _a1_range(item) for item in read_ranges):
        issues.append("private_config_invalid")
    elif any(_ranges(call) != read_ranges for call in cells):
        issues.append("native_verification_ranges_mismatch")
    if len(writes) != 1 or len(writes) == 1 and not _valid_update(writes[0], expected):
        issues.append("authorized_update_invalid")

    if len(file_metadata) == 1 and len(metadata) == 1 and len(routing) == 1 \
            and len(cells) == 2 and len(writes) == 1:
        ordered = [file_metadata[0], metadata[0], routing[0], cells[0], writes[0], cells[1]]
        if [_call_index(call) for call in ordered] != sorted(_call_index(call) for call in ordered):
            issues.append("provider_call_order_invalid")
        if live._tool_identity(cells[0])[1] != "get_spreadsheet_cells" \
                or live._tool_identity(cells[1])[1] != "get_spreadsheet_cells":
            issues.append("provider_call_order_invalid")
        before_map, after_map = _cell_map(cells[0]), _cell_map(cells[1])
        if not before_map or not after_map:
            issues.append("native_celldata_missing")
        else:
            sheet_id = int(target.get("sheet_id", -1))
            target_key = (sheet_id, int(target.get("row_index", -1)), int(target.get("column_index", -1)))
            formula = config.get("formula")
            formula_key = (int(formula.get("sheet_id", -1)), int(formula.get("row_index", -1)),
                           int(formula.get("column_index", -1))) if isinstance(formula, dict) else None
            before_target, after_target = before_map.get(target_key), after_map.get(target_key)
            if not before_target or not after_target or _user_value(before_target) != target.get("before_value") \
                    or _user_value(after_target) != target.get("after_value"):
                issues.append("canonical_target_readback_mismatch")
            record_key = (sheet_id, int(target.get("record_id_row_index", -1)),
                          int(target.get("record_id_column_index", -1)))
            if _user_value(before_map.get(record_key, {})) != target.get("record_id") \
                    or _user_value(after_map.get(record_key, {})) != target.get("record_id"):
                issues.append("stable_record_identity_not_preserved")
            elif before_target.get("dataValidation") != after_target.get("dataValidation") \
                    or before_target.get("dataValidation") != config.get("expected_validation"):
                issues.append("target_validation_not_preserved")
            if formula_key:
                before_formula, after_formula = before_map.get(formula_key), after_map.get(formula_key)
                expected_formula = formula.get("formula_value")
                if not before_formula or not after_formula \
                        or _user_value(before_formula) != expected_formula \
                        or _user_value(after_formula) != expected_formula \
                        or before_formula != after_formula:
                    issues.append("neighbor_formula_not_preserved")
            for key, before in before_map.items():
                if key == target_key:
                    continue
                after = after_map.get(key)
                if after != before:
                    issues.append("neighboring_native_state_changed")
                    break
            for key, before in before_map.items():
                if key[0] != int(config.get("history_sheet_id", -2)):
                    continue
                if after_map.get(key) != before:
                    issues.append("history_not_preserved")
                    break

    accepted = not issues
    return {"accepted": accepted, "status": "accepted" if accepted else "blocked",
            "issues": sorted(set(issues))}
