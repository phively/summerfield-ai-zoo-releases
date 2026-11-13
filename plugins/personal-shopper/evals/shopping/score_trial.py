#!/usr/bin/env python3
"""Independently reconcile a private synthetic trial; leave semantics for review."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

import capture_invocation as capture
import ae12_scoring
from ae12_scoring import (
    _delegation_capture,
    _delegation_runtime_matches,
    _fixture_calls_reconcile,
    _multi_agent_runtime_matches,
    _rollout_tool_calls,
    _valid_installed_resource,
)
from store import _parse_range, spreadsheet_id_from_arguments, valid_source


EVAL_ROOT = Path(__file__).resolve().parent
RESEARCH_GROUPS = {"B13", "B14", "B15", "B16", "B17", "B18"}
PLUGIN_ROOT = EVAL_ROOT.parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[1]
MANIFEST = EVAL_ROOT / "manifest.json"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _host_events(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise ValueError("host capture is missing or incomplete")
    result = []
    for line in raw.splitlines():
        event = json.loads(line)
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise ValueError("host capture contains an invalid event")
        result.append(event)
    return result


def _state_digest(state: Any) -> str:
    canonical = json.dumps(state, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return capture.sha256(canonical)


def _b18_tables_match_authorized_changes(state: dict[str, Any], frozen_case: dict[str, Any],
                                         rule_row_number: int | None) -> bool:
    sheets = frozen_case.get("workbook", {}).get("sheets", [])
    initial = {sheet.get("title"): [sheet.get("headers"), *sheet.get("rows", [])]
               for sheet in sheets if isinstance(sheet, dict) and isinstance(sheet.get("title"), str)}
    final = state.get("tables")
    if not isinstance(final, dict) or set(final) != set(initial) or rule_row_number is None:
        return False
    for title, initial_rows in initial.items():
        final_rows = final.get(title)
        if not isinstance(final_rows, list):
            return False
        if title == "Shopping Rules":
            if len(final_rows) != len(initial_rows):
                return False
            for row_index, (before, after) in enumerate(zip(initial_rows, final_rows), start=1):
                if not isinstance(before, list) or not isinstance(after, list):
                    return False
                for column_index in range(max(len(before), len(after))):
                    if row_index == rule_row_number and column_index + 1 in {2, 4, 6}:
                        continue
                    before_cell = before[column_index] if column_index < len(before) else None
                    after_cell = after[column_index] if column_index < len(after) else None
                    if before_cell != after_cell:
                        return False
        elif title == "Shopping History":
            if len(final_rows) != len(initial_rows) + 1 or final_rows[:-1] != initial_rows:
                return False
        elif final_rows != initial_rows:
            return False
    return True


def _identity_checks(result: dict[str, Any], manifest: dict[str, Any],
                     repo_root: Path = REPO_ROOT) -> dict[str, bool]:
    candidate_now = capture.identity_digest(
        repo_root, capture.candidate_identity_patterns(manifest)
    )
    suite_now = capture.identity_digest(repo_root, manifest["suite_identity_files"])
    return {
        "identities_stable": all(
            result.get(key) is True for key in (
                "candidate_profile_unchanged", "source_candidate_unchanged", "suite_identity_unchanged"
            )
        ) and result.get("source_candidate_sha256_after") == candidate_now
            and result.get("suite_sha256_after") == suite_now,
        "installed_local_files_match_source": capture.installed_local_files_match(
            result, manifest, repo_root
        ),
    }


def _fixture_events(path: Path) -> list[dict[str, Any]]:
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if not isinstance(event, dict) or not isinstance(event.get("tool"), str):
            raise ValueError("fixture capture contains an invalid event")
        result.append(event)
    return result


def _call_counts(events: list[dict[str, Any]]) -> tuple[Counter, list[dict[str, Any]], list[dict[str, str]], int]:
    calls_by_id: dict[str, dict[str, Any]] = {}
    for event in events:
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "mcp_tool_call":
            continue
        call_id, tool, server = item.get("id"), item.get("tool") or item.get("name"), item.get("server")
        if not all(isinstance(value, str) and value for value in (call_id, tool, server)):
            raise ValueError("host trace contains an unidentified MCP call")
        call = calls_by_id.setdefault(call_id, {"call_id": call_id, "server": server, "tool": tool,
                                                "status": None, "arguments": {}})
        if (call["server"], call["tool"]) != (server, tool):
            raise ValueError("host trace changed MCP call identity")
        if isinstance(item.get("arguments"), dict):
            call["arguments"] = item["arguments"]
        if isinstance(item.get("status"), str):
            call["status"] = item["status"]
        if "result" in item:
            call["result"] = item["result"]
        elif "output" in item:
            call["result"] = item["output"]
        if "error" in item:
            call["error"] = item["error"]

    counts: Counter = Counter()
    actual_calls = []
    resource_calls = []
    for call in calls_by_id.values():
        tool, server = call["tool"], call["server"]
        if server in {"codex", "codex_apps", "shopping-fixture"} \
                and tool in {"list_mcp_resources", "list_mcp_resource_templates"}:
            continue
        if server == "codex_apps" and tool == "read_mcp_resource" \
                and str(call["arguments"].get("uri", "")).startswith("plugin://Plugin_"):
            resource_calls.append({"server": server, "tool": tool})
            continue
        if server == "shopping-skill-resources" and tool == "read_installed_skill_file":
            resource_calls.append(call)
            continue
        actual_calls.append({"server": server, "tool": tool, "status": call["status"],
                             "call_id": call["call_id"], "arguments": call["arguments"],
                             "result": call.get("result")})
        counts[tool] += 1
    return counts, actual_calls, resource_calls, len(calls_by_id)


def _case_checks(subcase_id: str, state: dict[str, Any], events: list[dict[str, Any]],
                 control: dict[str, Any] | None = None,
                 delegation: dict[str, Any] | None = None) -> dict[str, bool]:
    if subcase_id.split("-", 1)[0] in RESEARCH_GROUPS:
        return _research_checks(subcase_id, state, events, control or {})
    if subcase_id in {"B10-AE12-new-plan", "B10-AE12-existing-plan"}:
        return ae12_scoring.case_checks(subcase_id, state, events, control, delegation)
    if subcase_id == "B7-role-mapped-legacy-workbook":
        expected = control.get("expected", {}) if isinstance(control, dict) else {}
        role_sheet = expected.get("role_sheet")
        required_sheets = set(expected.get("required_role_sheets", []))
        metadata_titles: set[str] = set()
        metadata_reads = []
        for event in events:
            if event.get("tool") != "get_spreadsheet_metadata" or event.get("result", {}).get("ok") is not True:
                continue
            result = event["result"]
            metadata_reads.append(result)
            for sheet in result.get("sheets", []):
                if isinstance(sheet, dict):
                    properties = sheet.get("properties", sheet)
                    if isinstance(properties, dict) and isinstance(properties.get("title"), str):
                        metadata_titles.add(properties["title"])

        role_reads = []
        for event in events:
            if event.get("tool") != "get_spreadsheet_range" or event.get("result", {}).get("ok") is not True:
                continue
            range_value = event.get("arguments", {}).get("range", "")
            if not isinstance(range_value, str) or "!" not in range_value:
                continue
            sheet_name = range_value.rsplit("!", 1)[0]
            if sheet_name.startswith("'") and sheet_name.endswith("'"):
                sheet_name = sheet_name[1:-1].replace("''", "'")
            if sheet_name == role_sheet:
                values = event["result"].get("values", [])
                role_reads.extend(row for row in values if isinstance(row, list))

        table = state.get("tables", {}).get(role_sheet, [])
        headers = table[0] if table and isinstance(table[0], list) else []
        try:
            key_index = headers.index(expected.get("stable_key_header"))
            store_index = headers.index(expected.get("store_header"))
            priority_index = headers.index(expected.get("priority_header"))
        except ValueError:
            key_index = store_index = priority_index = -1
        records = {}
        for row in role_reads:
            if min(key_index, store_index, priority_index) < 0 or len(row) <= max(key_index, store_index, priority_index):
                continue
            record_id = row[key_index]
            if record_id in expected.get("record_ids", []):
                records[record_id] = (row[priority_index], row[store_index])
        try:
            resolved_order = [store for _, store in sorted(records.values(), key=lambda item: int(item[0]))]
        except (TypeError, ValueError):
            resolved_order = []

        expected_ids = set(expected.get("record_ids", []))
        header_observed = any(row == headers for row in role_reads)
        read_ids = {
            row[key_index] for row in role_reads
            if key_index >= 0 and len(row) > key_index and row[key_index] in expected_ids
        }
        sheet_titles = {
            sheet.get("properties", sheet).get("title")
            for sheet in state.get("metadata", {}).get("sheets", []) if isinstance(sheet, dict)
        }
        no_writes = not any(event.get("attempted_write") for event in events)
        return {
            "role_mapping_metadata_observed": bool(metadata_reads)
            and required_sheets <= metadata_titles
            and state.get("spreadsheet_id") in {
                result.get("spreadsheetId") for result in metadata_reads
            },
            "reordered_stable_keys_read_from_role_tab": bool(headers)
            and headers[-1] == expected.get("stable_key_header")
            and header_observed and read_ids == expected_ids
            and resolved_order == expected.get("store_order"),
            "legacy_workbook_left_unchanged": no_writes
            and state.get("revision") == 0
            and ("Record Index" not in sheet_titles) == (expected.get("record_index_present") is False),
        }
    if subcase_id == "B5-AE6":
        rows = [event for event in events if event.get("tool") == "read_shopping_record"
                and event.get("arguments", {}).get("record_id") == "SYNTHETIC-GROCERY-061"]
        return {
            "existing_authority_read_by_stable_key": bool(rows) and rows[-1].get("result", {}).get("ok") is True,
            "fallback_made_no_persistent_write": not any(event.get("attempted_write") for event in events),
        }
    if subcase_id == "B5-AE7":
        reads = {
            event.get("arguments", {}).get("record_id") for event in events
            if event.get("tool") == "read_shopping_record" and event.get("result", {}).get("ok") is True
        }
        return {
            "both_ambiguous_candidates_read": {"SYNTHETIC-GROCERY-071", "SYNTHETIC-GROCERY-072"} <= reads,
            "ambiguous_fallback_made_no_persistent_write": not any(event.get("attempted_write") for event in events),
        }
    if subcase_id == "B6-AE8":
        faults = control.get("faults", {}) if isinstance(control, dict) else {}
        metadata_unavailable = any(
            event.get("tool") == "get_spreadsheet_metadata" and event.get("result", {}).get("ok") is False
            for event in events
        ) or (isinstance(faults, dict)
              and faults.get("get_spreadsheet_metadata") == "unavailable"
              and faults.get("get_spreadsheet_range") == "unavailable")
        return {
            "authority_unavailable_in_fixture": metadata_unavailable,
            "unavailable_route_made_no_persistent_write": not any(event.get("attempted_write") for event in events),
        }
    if subcase_id == "B8-U3-uncertain-append":
        existing = [event for event in events if event.get("tool") == "read_shopping_record"
                    and event.get("arguments", {}).get("record_id") == "OBS-CASE-042"]
        return {
            "timed_out_append_checked_by_stable_key": bool(existing) and existing[-1].get("result", {}).get("ok") is True,
            "no_duplicate_retry_attempted": not any(
                event.get("tool") == "write_shopping_record" and event.get("attempted_write") for event in events
            ),
        }
    if subcase_id in {"B9-owner-success-index-failure", "B9-index-success-owner-failure"}:
        record_id = "shopping-owner-route"
        owner_writes = [event for event in events if event.get("tool") == "write_shopping_record"
                        and event.get("arguments", {}).get("record_id") == record_id]
        index_writes = [event for event in events if event.get("tool") == "update_remember_me_index"
                        and event.get("arguments", {}).get("record_id") == record_id]
        owner_reads = [event for event in events if event.get("tool") == "read_shopping_record"
                       and event.get("arguments", {}).get("record_id") == record_id]
        index_reads = [event for event in events if event.get("tool") == "read_remember_me_index"
                       and event.get("arguments", {}).get("record_id") == record_id]
        owner_value = state.get("records", {}).get(record_id)
        if isinstance(owner_value, dict) and isinstance(owner_value.get("value"), dict):
            owner_value = owner_value["value"]
        index_value = state.get("remember_me_index", {}).get(record_id)
        owner_success = subcase_id == "B9-owner-success-index-failure"
        owner_readback_verified = bool(owner_reads and owner_writes) and max(
            event.get("sequence", 0) for event in owner_reads
        ) > max(event.get("sequence", 0) for event in owner_writes)
        index_readback_verified = bool(index_reads and index_writes) and max(
            event.get("sequence", 0) for event in index_reads
        ) > max(event.get("sequence", 0) for event in index_writes)
        return {
            "owner_and_index_writes_attempted": bool(owner_writes) and bool(index_writes),
            "expected_single_target_commit_observed": (
                bool(owner_writes) and owner_writes[-1].get("committed") is True
                and bool(index_writes) and index_writes[-1].get("committed") is False
            ) if owner_success else (
                bool(owner_writes) and owner_writes[-1].get("committed") is False
                and bool(index_writes) and index_writes[-1].get("committed") is True
            ),
            "owner_and_index_readbacks_follow_their_own_writes": owner_readback_verified and index_readback_verified,
            "final_state_reports_each_owner_separately": (
                isinstance(owner_value, dict) and owner_value.get("owner") == "personal-shopper:personal-shopper"
                and isinstance(index_value, dict) and index_value.get("owner") == "remember-me"
            ) if owner_success else (
                isinstance(owner_value, dict) and owner_value.get("owner") == "remember-me"
                and isinstance(index_value, dict) and index_value.get("owner") == "personal-shopper:personal-shopper"
            ),
        }
    if subcase_id != "B8-AE10":
        return {}
    equipment = state.get("tables", {}).get("Owned Equipment", [])
    history = state.get("tables", {}).get("Shopping History", [])
    current_rows = [row for row in equipment[1:] if row and row[0] == "EQ-CASE-010"]
    history_rows = [row for row in history[1:] if len(row) > 6
                    and row[2:4] == ["45 mm", "50 mm"] and row[6] == "EQ-CASE-010"]
    read_failures = [
        event for event in events
        if event.get("tool") == "get_spreadsheet_range"
        and event.get("arguments", {}).get("range", "").startswith("'Shopping History'!")
        and event.get("result", {}).get("ok") is False
    ]
    if len(current_rows) != 1 or len(history_rows) != 1:
        return {
            "current_record_contains_confirmed_correction": False,
            "history_records_prior_value_and_pointer": False,
            "history_readback_failure_observed": bool(read_failures),
        }
    current, prior = current_rows[0], history_rows[0]
    return {
        "current_record_contains_confirmed_correction": len(current) > 8
        and current[4:7] == [50, "mm", "confirmed"],
        "history_records_prior_value_and_pointer": len(prior) > 7
        and prior[2:4] == ["45 mm", "50 mm"] and prior[6] == "EQ-CASE-010",
        "history_readback_failure_observed": bool(read_failures),
    }


def _research_checks(subcase_id: str, state: dict[str, Any], events: list[dict[str, Any]],
                     control: dict[str, Any]) -> dict[str, bool]:
    expected = control.get("expected", {})
    sources = control.get("sources", {})
    frozen_case = next((case for case in _read(EVAL_ROOT / "fixtures.json")["cases"]
                        if case.get("id") == control.get("case_id")), {})
    reads = [event for event in events if event.get("tool") == "retrieve_source"]
    succeeded: set[str] = set()
    unavailable: set[str] = set()
    source_results_match = True
    for event in reads:
        arguments = event.get("arguments", {})
        source_id = arguments.get("source_id") if isinstance(arguments, dict) else None
        source = sources.get(source_id) if isinstance(source_id, str) else None
        result = event.get("result", {})
        if not isinstance(arguments, dict) or set(arguments) != {"source_id"} \
                or not valid_source(source, source_id):
            source_results_match = False
        elif source["available"] is False:
            matches = result == {"ok": False, "error": "source_unavailable", "source_id": source_id}
            source_results_match = source_results_match and matches
            if matches:
                unavailable.add(source_id)
        else:
            matches = result == {"ok": True, "source": source, "source_sha256": _state_digest(source)}
            source_results_match = source_results_match and matches
            if matches:
                succeeded.add(source_id)
    checks = {
        "research_control_matches_frozen_fixture": bool(frozen_case)
        and sources == frozen_case.get("sources", {}) and expected == frozen_case.get("expected", {}),
        "required_research_sources_observed": set(expected.get("required_source_ids", [])) <= succeeded,
        "required_unavailable_sources_observed": set(expected.get("unavailable_source_ids", [])) <= unavailable,
        "retrieved_source_identity_and_bytes_match": source_results_match,
        "source_reads_leave_shopping_state_unchanged": all(
            event.get("state_before_sha256") == event.get("state_after_sha256")
            and event.get("attempted_write") is False and event.get("committed") is False
            for event in reads
        ),
    }
    if expected.get("first_source_id"):
        checks["manufacturer_retrieved_before_secondary_sources"] = bool(reads) \
            and reads[0].get("arguments", {}).get("source_id") == expected["first_source_id"]
    if subcase_id != "B18-AE18":
        checks["research_does_not_write_records"] = state.get("revision") == 0 \
            and not any(event.get("attempted_write") for event in events)
        return checks

    rules = state.get("tables", {}).get("Shopping Rules", [])
    history = state.get("tables", {}).get("Shopping History", [])
    rule_rows = [row for row in rules[1:] if len(row) > 2 and row[2] == expected.get("stable_key")]
    history_rows = [row for row in history[1:] if len(row) > 6 and row[6] == expected.get("stable_key")]
    writes = [event for event in events if event.get("attempted_write")]
    rule_sheet = next((sheet for sheet in frozen_case.get("workbook", {}).get("sheets", [])
                       if sheet.get("title") == "Shopping Rules"), {})
    history_sheet = next((sheet for sheet in frozen_case.get("workbook", {}).get("sheets", [])
                          if sheet.get("title") == "Shopping History"), {})
    rule_headers = rule_sheet.get("headers", [])
    history_headers = history_sheet.get("headers", [])
    rule_rows_before = rule_sheet.get("rows", [])
    history_rows_before = history_sheet.get("rows", [])
    rule_row_numbers = [index + 2 for index, row in enumerate(rule_rows_before)
                        if len(row) > 2 and row[2] == expected.get("stable_key")]
    rule_row_number = rule_row_numbers[0] if len(rule_row_numbers) == 1 else None
    history_row_number = len(history_rows_before) + 2
    committed_ranges: dict[str, int] = {}
    written_cells: set[tuple[str, int, int]] = set()
    authorized_writes = bool(writes) and rule_row_number is not None \
        and bool(rule_headers) and bool(history_headers)
    for event in writes:
        arguments = event.get("arguments")
        updates = arguments.get("updates") if isinstance(arguments, dict) else None
        if event.get("tool") != "batch_update_spreadsheet" or event.get("committed") is not True \
                or not isinstance(updates, list) or not updates:
            authorized_writes = False
            continue
        sequence = event.get("sequence", 0)
        for update in updates:
            if not isinstance(update, dict) or not isinstance(update.get("range"), str) \
                    or not isinstance(update.get("values"), list):
                authorized_writes = False
                continue
            try:
                sheet, start_row, start_column, end_row, end_column = _parse_range(update["range"])
            except (TypeError, ValueError):
                authorized_writes = False
                continue
            values = update["values"]
            row_count = end_row - start_row + 1
            column_count = end_column - start_column + 1
            if sheet == "Shopping Rules":
                permitted = start_row == end_row == rule_row_number \
                    and end_column <= len(rule_headers) \
                    and all(column in {2, 4, 6} for column in range(start_column, end_column + 1))
            elif sheet == "Shopping History":
                permitted = start_row == end_row == history_row_number \
                    and end_column <= len(history_headers)
            else:
                permitted = False
            if not permitted or len(values) != row_count \
                    or any(not isinstance(row, list) or len(row) != column_count for row in values):
                authorized_writes = False
                continue
            cells = {(sheet, row, column)
                     for row in range(start_row, end_row + 1)
                     for column in range(start_column, end_column + 1)}
            if written_cells & cells:
                authorized_writes = False
            written_cells.update(cells)
            committed_ranges[sheet] = max(committed_ranges.get(sheet, 0), sequence)
    current_verified = any(
        event.get("tool") == "get_spreadsheet_range" and event.get("result", {}).get("ok") is True
        and _range_sheet(event.get("arguments", {}).get("range")) == "Shopping Rules"
        and event.get("sequence", 0) > committed_ranges.get("Shopping Rules", float("inf"))
        and any(len(row) > 2 and row[2] == expected.get("stable_key")
                and row[1] == expected.get("confirmed_rule")
                for row in event.get("result", {}).get("values", []))
        for event in events
    )
    history_failed = any(
        event.get("tool") == "get_spreadsheet_range"
        and event.get("arguments", {}).get("range", "").rsplit("!", 1)[0].strip("'") == "Shopping History"
        and event.get("sequence", 0) > committed_ranges.get("Shopping History", float("inf"))
        and event.get("result", {}).get("ok") is False
        for event in events
    )
    checks.update({
        "service_correction_saved_to_existing_stable_key": len(rule_rows) == 1
        and rule_rows[0][1] == expected.get("confirmed_rule") and rule_rows[0][0] == "contractor"
        and rule_rows[0][4] == "service:contractor",
        "current_record_readback_observed": current_verified,
        "required_history_written_once_but_unverified": len(history_rows) == 1
        and len(history_rows[0]) == len(history_headers)
        and all(value not in (None, "") for value in history_rows[0])
        and history_rows[0][2:4] == [expected.get("prior_rule"), expected.get("confirmed_rule")]
        and history_failed,
        "grocery_schema_and_preferences_unchanged": state.get("tables", {}).get("Store Preferences")
        == expected.get("grocery_table"),
        "workbook_changes_stay_within_authorized_service_rows": _b18_tables_match_authorized_changes(
            state, frozen_case, rule_row_number
        ),
        "only_authorized_current_and_history_writes": authorized_writes
        and ("Shopping Rules", rule_row_number, 2) in written_cells
        and all(("Shopping History", history_row_number, column) in written_cells
                for column in (1, 3, 4, 7))
        and set(committed_ranges) == {"Shopping Rules", "Shopping History"},
    })
    return checks


def _range_sheet(value: Any) -> str | None:
    try:
        return _parse_range(value)[0]
    except (TypeError, ValueError):
        return None


def score_trial(trial_dir: str | Path) -> dict[str, Any]:
    requested_directory = Path(trial_dir).expanduser()
    if requested_directory.is_symlink():
        raise ValueError("trial evidence directory is invalid")
    directory = requested_directory.resolve(strict=True)
    if not directory.is_dir() or directory.stat().st_mode & 0o077:
        raise ValueError("trial evidence directory must be private")
    result = _read(directory / "trial-result.json")
    state = _read(directory / "fixture-store" / "final-state.json")
    control = _read(directory / "fixture-store" / "control.json")
    runtime_settings = _read(directory / "runtime-settings.json")
    host = _host_events(directory / "host-events.jsonl")
    fixture = _fixture_events(directory / "fixture-store" / "events.jsonl")
    manifest = _read(MANIFEST)
    subcase_id = result.get("fixture", {}).get("subcase_id")
    subcase = next((item for item in manifest["synthetic_subcases"] if item.get("id") == subcase_id), None)
    if subcase is None or control.get("case_id") != subcase.get("fixture_id"):
        raise ValueError("trial identity does not match a declared synthetic subcase")

    host_counts, host_calls, resource_calls, host_tool_call_count = _call_counts(host)
    rollout_capture = _delegation_capture(directory, result, host) \
        if subcase_id == "B10-AE12-new-plan" else {"valid": True, "parent": [], "children": {}}
    child_tool_calls = [call for thread_id, child_events in rollout_capture.get("children", {}).items()
                        for call in _rollout_tool_calls(child_events, thread_id)]
    child_fixture_calls = [call for call in child_tool_calls if call.get("server") == "shopping-fixture"]
    child_resource_calls = [call for call in child_tool_calls
                            if call.get("server") != "shopping-fixture"]
    resource_calls.extend(child_resource_calls)
    fixture_counts = Counter(event["tool"] for event in fixture)
    candidate_permissions = set(subcase.get("tools", []))
    permitted_writes = set(subcase.get("permitted_operations", []))
    expected_skill_id = manifest["candidate"]["profiles"][subcase["profile"]].get(
        "activation_skill", manifest["candidate"]["skill"]
    )
    expected_multi_agent = manifest["candidate"]["profiles"][subcase["profile"]].get("multi_agent", False)
    expected_requested_skills = [expected_skill_id, *subcase.get("additional_skills", [])]
    called_servers_match = all(call["server"] == "shopping-fixture" for call in host_calls)
    if subcase_id == "B10-AE12-new-plan" or subcase.get("group") in RESEARCH_GROUPS:
        host_fixture_calls_match = _fixture_calls_reconcile(
            [call for call in host_calls if call.get("server") == "shopping-fixture"],
            child_fixture_calls, fixture,
            allow_failed_results=subcase.get("group") in RESEARCH_GROUPS,
        )
    else:
        host_fixture_calls_match = host_counts == fixture_counts
    allowed_calls_match = set(fixture_counts) <= candidate_permissions
    writes_match = all(
        not event.get("attempted_write") or event.get("tool") in permitted_writes
        for event in fixture
    )
    spreadsheet_tools = {
        "get_spreadsheet_metadata", "get_spreadsheet_range", "get_spreadsheet_cells",
        "batch_update_spreadsheet",
    }
    spreadsheet_resource_ids_present = all(
        spreadsheet_id_from_arguments(event.get("arguments")) is not None
        for event in fixture if event.get("tool") in spreadsheet_tools
    )
    identity_checks = _identity_checks(result, manifest)
    capture_complete = result.get("complete") is True and result.get("trial_status") == "captured" \
        and host[0].get("type") == "thread.started" and host[-1].get("type") == "turn.completed"
    raw_trace = (directory / "host-events.jsonl").read_bytes()
    capture_counts_match = result.get("event_count") == len(host) \
        and result.get("tool_call_count") == host_tool_call_count \
        and result.get("trace_sha256") == capture.sha256(raw_trace)
    fixture_chain_valid = all(event.get("sequence") == index for index, event in enumerate(fixture, 1))
    fixture_chain_valid = fixture_chain_valid and all(
        fixture[index - 1].get("state_after_sha256") == fixture[index].get("state_before_sha256")
        for index in range(1, len(fixture))
    )
    initial_state = _read(directory / "fixture-store" / "initial-state.json")
    expected_final_hash = fixture[-1].get("state_after_sha256") if fixture else _state_digest(initial_state)
    fixture_state_matches = expected_final_hash == _state_digest(state) \
        and result.get("fixture", {}).get("event_count") == len(fixture) \
        and result.get("fixture", {}).get("state_sha256_before") == _state_digest(initial_state) \
        and result.get("fixture", {}).get("state_sha256_after") == _state_digest(state)
    checks = {
        "capture_complete": capture_complete,
        "capture_digest_and_counts_match": capture_counts_match,
        **identity_checks,
        "activation_route_matches_profile": result.get("profile_id") == subcase["profile"]
        and result.get("skill_id") == expected_skill_id
        and result.get("requested_skill_ids") == expected_requested_skills,
        "isolated_runtime_tool_policy": _multi_agent_runtime_matches(runtime_settings, expected_multi_agent),
        "delegation_runtime_mcp_surface": subcase_id != "B10-AE12-new-plan" or
        _delegation_runtime_matches(directory, result, runtime_settings, subcase),
        "delegation_rollouts_bound_to_parent_and_child": rollout_capture.get("valid") is True,
        "fixture_tool_surface_respected": called_servers_match and allowed_calls_match,
        "host_and_fixture_calls_reconcile": host_fixture_calls_match,
        "fixture_event_chain_valid": fixture_chain_valid,
        "fixture_final_state_matches_capture": fixture_state_matches,
        "only_candidate_plugin_resources_read": all(
            call["tool"] == "read_mcp_resource" or _valid_installed_resource(call, result.get("installed_file_sha256", {}))
            for call in resource_calls
        ),
        "writes_authorized_by_subcase": writes_match,
        "spreadsheet_resource_ids_present": spreadsheet_resource_ids_present,
    }
    required_resources = subcase.get("required_skill_resources", [])
    if required_resources:
        observed = {f"{call['arguments']['package']}/{call['arguments']['relative_path']}"
                    for call in resource_calls if _valid_installed_resource(call, result.get("installed_file_sha256", {}))}
        checks["required_installed_contracts_observed"] = set(required_resources) <= observed
    public_case_data = _read(directory / "fixture-store" / "public.json")
    case_checks = _case_checks(
        subcase_id, state, fixture, control=control,
        delegation={
            "host_events": host,
            "rollouts": rollout_capture,
            "public_context": public_case_data.get("context", {}),
            "installed": result.get("installed_file_sha256", {}),
            "required_caller_skill_resources": subcase.get("required_caller_skill_resources", []),
            "required_child_skill_resources": subcase.get("required_child_skill_resources", []),
            "required_child_fixture_read_tools": subcase.get("required_child_fixture_read_tools", []),
            "fixture_events": fixture,
        },
    )
    checks.update({f"case:{name}": value for name, value in case_checks.items()})
    machine_ok = all(checks.values())
    return {
        "schema": "personal-shopper-synthetic-score/v1",
        "subcase_id": subcase_id,
        "group": subcase["group"],
        "profile": subcase["profile"],
        "machine_status": "ready-for-semantic-review" if machine_ok else "failed",
        "machine_checks": checks,
        "fixture_tool_call_count": sum(fixture_counts.values()),
        "candidate_plugin_resource_read_count": len(resource_calls),
        "write_attempt_count": sum(bool(event.get("attempted_write")) for event in fixture),
        "committed_write_count": sum(bool(event.get("committed")) for event in fixture),
        "semantic_review": "pending",
        "acceptance": "not-accepted",
        "expected_answer_comparison": "deferred-to-independent-semantic-review",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial_dir", type=Path)
    args = parser.parse_args()
    try:
        score = score_trial(args.trial_dir)
        report = Path(args.trial_dir).expanduser().resolve() / "machine-score.json"
        report.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")
        os.chmod(report, 0o600)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"synthetic scoring failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(score, sort_keys=True))
    return 0 if score["machine_status"] == "ready-for-semantic-review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
