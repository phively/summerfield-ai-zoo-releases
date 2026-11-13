#!/usr/bin/env python3
"""Serve isolated synthetic shopping fixtures over MCP and record every call."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
import sys
from typing import Any


EVAL_ROOT = Path(__file__).resolve().parent
FIXTURES = EVAL_ROOT / "fixtures.json"
SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}
HIDDEN_CASE_FIELDS = {"expected", "faults", "hidden_assertions", "controller", "sources"}
SOURCE_KINDS = {
    "manufacturer_specification", "retail_offer", "service_terms", "independent_review",
    "contractor_quote", "official_registry", "official_fee_schedule",
    "secondary_article", "completed_project_observations",
}


def _json_hash(value: Any) -> str:
    content = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(content).hexdigest()


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _case(case_id: str) -> dict[str, Any]:
    fixture_set = _read(FIXTURES)
    result = next((case for case in fixture_set["cases"] if case.get("id") == case_id), None)
    if result is None:
        raise ValueError("unknown synthetic shopping fixture")
    return deepcopy(result)


def public_case(case: dict[str, Any]) -> dict[str, Any]:
    """Return only task-visible fixture facts, never controller assertions."""
    return {key: deepcopy(value) for key, value in case.items() if key not in HIDDEN_CASE_FIELDS}


def workbook_identity(case_id: str) -> dict[str, str]:
    return {
        "provider": "synthetic-shopping-fixture",
        "spreadsheet_id": f"SYNTHETIC-SHOPPING-{case_id.upper()}",
    }


def spreadsheet_id_from_arguments(arguments: Any) -> str | None:
    if not isinstance(arguments, dict):
        return None
    if "spreadsheet_id" in arguments:
        requested_id = arguments["spreadsheet_id"]
    else:
        requested_id = arguments.get("spreadsheetId")
    return requested_id if isinstance(requested_id, str) and requested_id.strip() else None


_A1_RANGE = re.compile(r"^([A-Z]+)(\d+)(?::([A-Z]+)?(\d+)?)?$")


def _column_number(value: str) -> int:
    number = 0
    for character in value:
        number = number * 26 + ord(character) - ord("A") + 1
    return number


def _column_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def _parse_range(value: str) -> tuple[str, int, int, int, int]:
    if not isinstance(value, str) or "!" not in value:
        raise ValueError("invalid synthetic A1 range")
    sheet_value, coordinates = value.rsplit("!", 1)
    if sheet_value.startswith("'") and sheet_value.endswith("'"):
        sheet = sheet_value[1:-1].replace("''", "'")
    else:
        sheet = sheet_value
    match = _A1_RANGE.fullmatch(coordinates)
    if not sheet or match is None:
        raise ValueError("invalid synthetic A1 range")
    start_column = _column_number(match.group(1))
    start_row = int(match.group(2))
    end_column = _column_number(match.group(3) or match.group(1))
    end_row = int(match.group(4)) if match.group(4) else (2**31 - 1 if match.group(3) else start_row)
    if start_row < 1 or end_row < start_row or end_column < start_column:
        raise ValueError("invalid synthetic A1 range")
    return sheet, start_row, start_column, end_row, end_column


def _range_values(state: dict[str, Any], value: str) -> list[list[Any]]:
    sheet, start_row, start_column, end_row, end_column = _parse_range(value)
    table = state.get("tables", {}).get(sheet)
    if not isinstance(table, list):
        return deepcopy(state.get("ranges", {}).get(value, []))
    last_row = min(end_row, len(table))
    if start_row > last_row:
        return []
    result = []
    for row in table[start_row - 1:last_row]:
        cells = deepcopy(row[start_column - 1:end_column])
        while cells and cells[-1] in (None, ""):
            cells.pop()
        result.append(cells)
    while result and not any(cell not in (None, "") for cell in result[-1]):
        result.pop()
    return result


def _write_range(state: dict[str, Any], value: str, values: list[list[Any]]) -> None:
    sheet, start_row, start_column, _, _ = _parse_range(value)
    tables = state.setdefault("tables", {})
    if sheet not in tables or not isinstance(tables[sheet], list):
        raise ValueError("synthetic worksheet is unavailable")
    table = tables[sheet]
    if not isinstance(values, list) or any(not isinstance(row, list) for row in values):
        raise ValueError("synthetic values must be a two-dimensional list")
    for row_index, values_row in enumerate(values):
        target_row_index = start_row - 1 + row_index
        while len(table) <= target_row_index:
            table.append([])
        target_row = table[target_row_index]
        for column_offset, item in enumerate(values_row):
            target_column_index = start_column - 1 + column_offset
            while len(target_row) <= target_column_index:
                target_row.append("")
            target_row[target_column_index] = deepcopy(item)


def _range_unavailable_after_revision(
    state: dict[str, Any], value: str, fault: dict[str, Any]
) -> bool:
    unavailable = fault.get("unavailable_sheets_after_revision", {})
    if not isinstance(unavailable, dict):
        return False
    try:
        sheet, *_ = _parse_range(value)
        threshold = unavailable.get(sheet)
        return isinstance(threshold, int) and not isinstance(threshold, bool) \
            and state.get("revision", 0) >= threshold
    except ValueError:
        return False


def render_task(case_id: str, *, context_keys: list[str] | None = None,
                request_override: str | None = None) -> str:
    case = public_case(_case(case_id))
    context = case.get("context", {})
    if context_keys:
        if not isinstance(context, dict) or any(key not in context for key in context_keys):
            raise ValueError("synthetic public context section is missing")
        context = {key: context[key] for key in context_keys}
    requests = case.get("requests")
    if isinstance(request_override, str) and request_override.strip():
        request_text = request_override
    elif isinstance(requests, list):
        request_text = "\n".join(
            f"- {item.get('request', '')}" for item in requests if isinstance(item, dict)
        )
    else:
        request_text = case.get("request") or (context.get("request") if isinstance(context, dict) else None)
    if not isinstance(request_text, str) or not request_text.strip():
        request_text = case.get("name", "Complete the requested shopping task.")
    task_context = {
        "fixture_workbook_identity": workbook_identity(case_id),
        "public_context": context,
    }
    return (
        f"{request_text.strip()}\n\n"
        "Use the provided context and the isolated synthetic fixture tools when they help. "
        "These tools cannot access any real account, workbook, or provider.\n\n"
        f"Synthetic context:\n{json.dumps(task_context, ensure_ascii=False, indent=2)}\n"
    )


def _initial_state(case_id: str, case: dict[str, Any]) -> dict[str, Any]:
    context = case.get("context", {})
    workbook_id = workbook_identity(case_id)["spreadsheet_id"]
    default_sheets = [
        {"properties": {"sheetId": 101, "title": "Record Index", "index": 0}},
        {"properties": {"sheetId": 102, "title": "Store Preferences", "index": 1}},
        {"properties": {"sheetId": 103, "title": "Price Tracker", "index": 2}},
        {"properties": {"sheetId": 104, "title": "Store Preferences History", "index": 3}},
    ]
    ranges: dict[str, list[list[Any]]] = {
        "Record Index!A1:D1": [["Record ID", "Role", "Tab", "Key"]],
        "Store Preferences!A1:E1": [["Record ID", "Priority", "Store", "Preferred Website", "Updated At"]],
        "Price Tracker!A1:H1": [["Record ID", "Product", "Store", "Region", "Date", "Package", "Price", "Status"]],
        "Store Preferences History!A1:E1": [["Record ID", "Changed At", "Prior Order", "Reason", "Source"]],
    }
    tables = {
        "Record Index": deepcopy(ranges["Record Index!A1:D1"]),
        "Store Preferences": deepcopy(ranges["Store Preferences!A1:E1"]),
        "Price Tracker": deepcopy(ranges["Price Tracker!A1:H1"]),
        "Store Preferences History": deepcopy(ranges["Store Preferences History!A1:E1"]),
    }
    workbook = case.get("workbook")
    if isinstance(workbook, dict) and isinstance(workbook.get("sheets"), list):
        tables = {}
        sheets = []
        for index, sheet in enumerate(workbook["sheets"]):
            if not isinstance(sheet, dict) or not isinstance(sheet.get("title"), str) \
                    or not isinstance(sheet.get("headers"), list) or not isinstance(sheet.get("rows", []), list):
                raise ValueError("synthetic workbook sheet is malformed")
            title = sheet["title"]
            if title in tables or any(not isinstance(header, str) for header in sheet["headers"]):
                raise ValueError("synthetic workbook sheet identity or headers are invalid")
            rows = sheet.get("rows", [])
            if any(not isinstance(row, list) for row in rows):
                raise ValueError("synthetic workbook rows are malformed")
            tables[title] = [deepcopy(sheet["headers"]), *deepcopy(rows)]
            sheets.append({"properties": {"sheetId": 101 + index, "title": title, "index": index}})
    else:
        sheets = default_sheets
    records = {}
    for key in ("existing_record", "record", "existing_records", "candidate_records"):
        value = context.get(key)
        if isinstance(value, dict):
            record_id = value.get("stable_key") or value.get("record_id") or value.get("id")
            if isinstance(record_id, str):
                records[record_id] = deepcopy(value)
            else:
                records.update(deepcopy(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    record_id = item.get("stable_key") or item.get("record_id") or item.get("id")
                    if isinstance(record_id, str):
                        records[record_id] = deepcopy(item)
    return {
        "revision": 0,
        "spreadsheet_id": workbook_id,
        "provider": "synthetic-shopping-fixture",
        "metadata": {
            "spreadsheetId": workbook_id,
            "properties": {"title": f"Synthetic Shopping Fixture {case_id}"},
            "sheets": sheets,
        },
        "ranges": ranges,
        "tables": tables,
        "records": records,
        "remember_me_index": deepcopy(context.get("existing_remember_me_index", {})),
        "meal_plans": {},
        "context": deepcopy(context),
    }


def initialize(root: str | Path, case_id: str, allowed_tools: list[str], *, faults: dict[str, Any] | None = None) -> Path:
    root = Path(root).expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError("synthetic fixture root must be new or empty")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    case = _case(case_id)
    public = public_case(case)
    if not isinstance(allowed_tools, list) or len(allowed_tools) != len(set(allowed_tools)) \
            or not set(allowed_tools) <= set(TOOL_DETAILS):
        raise ValueError("synthetic fixture tools are invalid")
    control = {
        "case_id": case_id,
        "expected": deepcopy(case.get("expected", {})),
        "sources": deepcopy(case.get("sources", {})),
        "allowed_tools": list(allowed_tools),
        "faults": deepcopy(faults or case.get("faults", {})),
        "public_sha256": _json_hash(public),
    }
    state = _initial_state(case_id, case)
    public["fixture_workbook_identity"] = workbook_identity(case_id)
    _write(root / "public.json", public)
    _write(root / "control.json", control)
    _write(root / "state.json", state)
    _write(root / "initial-state.json", state)
    (root / "events.jsonl").touch(mode=0o600)
    os.chmod(root / "events.jsonl", 0o600)
    return root


def _append_event(root: Path, request_id: Any, tool: str, arguments: Any,
                  result: dict[str, Any], before_hash: str, after_hash: str,
                  attempted_write: bool, committed: bool) -> str:
    event_path = root / "events.jsonl"
    sequence = sum(1 for line in event_path.read_bytes().splitlines() if line) + 1
    event_id = f"fixture-{uuid.uuid4().hex}"
    event = {
        "sequence": sequence,
        "event_id": event_id,
        "request_id": request_id,
        "tool": tool,
        "arguments": deepcopy(arguments),
        "result": deepcopy(result),
        "state_before_sha256": before_hash,
        "state_after_sha256": after_hash,
        "attempted_write": bool(attempted_write),
        "committed": bool(committed),
    }
    with event_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event_id


class Store:
    """Return synthetic records, apply declared faults, and expose final state for scoring."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve(strict=True)
        self.control = _read(self.root / "control.json")
        self.last_event_id: str | None = None

    def call(self, request_id: Any, name: str, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        state_path = self.root / "state.json"
        state = _read(state_path)
        before_hash = _json_hash(state)
        result: dict[str, Any] = {"ok": False, "error": "invalid synthetic request"}
        attempted_write = name in {"batch_update_spreadsheet", "write_shopping_record", "update_remember_me_index", "save_meal_plan"}
        committed = False
        if name not in TOOL_DETAILS:
            result = {"ok": False, "error": "unknown synthetic tool"}
        elif name not in self.control["allowed_tools"]:
            result = {"ok": False, "error": "synthetic tool is not enabled for this subcase"}
        faults = self.control.get("faults", {})
        fault = faults.get(name) if isinstance(faults, dict) else None

        if result.get("error") in {"unknown synthetic tool", "synthetic tool is not enabled for this subcase"}:
            pass
        elif name == "get_case_context":
            result = {"ok": True, "case_id": self.control["case_id"], "context": _read(self.root / "public.json").get("context", {})}
        elif name == "retrieve_source":
            source_id = arguments.get("source_id")
            source = self.control.get("sources", {}).get(source_id) if isinstance(source_id, str) else None
            if set(arguments) != {"source_id"} or not isinstance(source_id, str) or not source_id:
                result = {"ok": False, "error": "invalid_source_selector"}
            elif source is None:
                result = {"ok": False, "error": "source_not_allowed", "source_id": source_id}
            elif not valid_source(source, source_id):
                result = {"ok": False, "error": "malformed_source", "source_id": source_id}
            elif source["available"] is False:
                result = {"ok": False, "error": "source_unavailable", "source_id": source_id}
            else:
                result = {"ok": True, "source": deepcopy(source), "source_sha256": _json_hash(source)}
        elif name == "get_meal_plan_index":
            result = {"ok": True, "plan_ids": sorted(set(state["context"].get("existing_plan_ids", [])) | set(state["meal_plans"]))}
        elif name == "record_grocery_result":
            identity = arguments.get("plan_identity")
            returned = arguments.get("returned_grocery_result")
            request_id = arguments.get("request_id")
            recipe_versions = arguments.get("recipe_versions")
            workbook_identity = arguments.get("workbook_identity")
            grocery_items = returned.get("grocery_list", returned.get("grocery_sections")) \
                if isinstance(returned, dict) else None
            valid = isinstance(returned, dict) and returned.get("protocol") == "grocery-handoff/v1" \
                and isinstance(identity, dict) and returned.get("plan_identity") == identity \
                and isinstance(request_id, str) and returned.get("request_id") == request_id \
                and isinstance(recipe_versions, dict) and returned.get("recipe_versions") == recipe_versions \
                and returned.get("recipe_ids") == list(recipe_versions) \
                and isinstance(workbook_identity, dict) and returned.get("workbook_identity") == workbook_identity \
                and returned.get("capability") in {"full", "fallback"} \
                and isinstance(grocery_items, list) and bool(grocery_items)
            result = {"ok": True} if valid else {
                "ok": False,
                "error": "complete top-level grocery-handoff/v1 result with grocery_list or grocery_sections is required",
            }
        elif name == "save_meal_plan":
            plan_id, content = arguments.get("plan_id"), arguments.get("content")
            if not isinstance(plan_id, str) or not re.fullmatch(r"MP-\d{4}-\d{2}-\d{2}-\d{2}", plan_id) or not isinstance(content, dict):
                result = {"ok": False, "error": "invalid synthetic plan"}
            elif plan_id in state["context"].get("existing_plan_ids", []) or plan_id in state["meal_plans"]:
                result = {"ok": False, "error": "synthetic plan ID already exists"}
            else:
                state["meal_plans"][plan_id] = {"plan_id": plan_id, "content": deepcopy(content)}
                state["revision"] += 1
                _write(state_path, state)
                committed = True
                result = {"ok": True, "plan_id": plan_id, "native_resource": "synthetic-plan-" + plan_id}
        elif name == "read_meal_plan":
            plan_id = arguments.get("plan_id")
            plan = state["meal_plans"].get(plan_id) if isinstance(plan_id, str) else None
            result = {"ok": True, **deepcopy(plan)} if plan else {"ok": False, "error": "synthetic plan not found"}
        elif name == "get_spreadsheet_metadata":
            requested_id = spreadsheet_id_from_arguments(arguments)
            if requested_id is None:
                result = {"ok": False, "error": "synthetic spreadsheet_id is required"}
            elif requested_id != state["spreadsheet_id"]:
                result = {"ok": False, "error": "synthetic spreadsheet identity mismatch"}
            elif fault == "unavailable":
                result = {"ok": False, "error": "synthetic spreadsheet metadata is unavailable"}
            else:
                result = {"ok": True, **deepcopy(state["metadata"]), "revision": state["revision"]}
        elif name in {"get_spreadsheet_range", "get_spreadsheet_cells"}:
            requested_id = spreadsheet_id_from_arguments(arguments)
            requested_range = arguments.get("range", arguments.get("a1_range", ""))
            if requested_id is None:
                result = {"ok": False, "error": "synthetic spreadsheet_id is required"}
            elif requested_id != state["spreadsheet_id"]:
                result = {"ok": False, "error": "synthetic spreadsheet identity mismatch"}
            elif fault == "unavailable":
                result = {"ok": False, "error": "synthetic spreadsheet range is unavailable"}
            elif fault == "partial":
                result = {"ok": True, "range": requested_range, "values": [], "warning": "synthetic partial read"}
            elif isinstance(fault, dict) and _range_unavailable_after_revision(
                state, requested_range, fault
            ):
                result = {"ok": False, "error": "synthetic spreadsheet range is unavailable after update"}
            else:
                try:
                    values = _range_values(state, requested_range)
                except ValueError:
                    result = {"ok": False, "error": "invalid synthetic spreadsheet range"}
                else:
                    result = {"ok": True, "range": requested_range, "values": values, "revision": state["revision"]}
        elif name == "batch_update_spreadsheet":
            requested_id = spreadsheet_id_from_arguments(arguments)
            updates = arguments.get("updates", arguments.get("data", []))
            if requested_id is None:
                result = {"ok": False, "error": "synthetic spreadsheet_id is required"}
            elif requested_id != state["spreadsheet_id"]:
                result = {"ok": False, "error": "synthetic spreadsheet identity mismatch"}
            elif fault == "reject":
                result = {"ok": False, "error": "synthetic update rejected"}
            elif not isinstance(updates, list):
                result = {"ok": False, "error": "synthetic updates must be a list"}
            elif not updates:
                result = {"ok": False, "error": "synthetic updates must not be empty"}
            else:
                try:
                    for update in updates:
                        if not isinstance(update, dict) or not isinstance(update.get("range"), str) \
                                or not isinstance(update.get("values"), list):
                            raise ValueError("invalid synthetic update")
                        sheet, *_ = _parse_range(update["range"])
                        if sheet not in state.get("tables", {}):
                            raise ValueError("synthetic worksheet is unavailable")
                except ValueError as error:
                    result = {"ok": False, "error": str(error)}
                else:
                    try:
                        for update in updates:
                            _write_range(state, update["range"], update["values"])
                            state["ranges"][update["range"]] = deepcopy(update["values"])
                    except (KeyError, TypeError, ValueError) as error:
                        result = {"ok": False, "error": str(error)}
                    else:
                        state["revision"] += 1
                        _write(state_path, state)
                        committed = True
                        result = {"ok": True, "updatedRanges": [update["range"] for update in updates], "revision": state["revision"]}
                        if fault == "timeout_after_commit":
                            result = {"ok": False, "error": "synthetic acknowledgement timed out after commit"}
        elif name == "read_shopping_record":
            record_id = arguments.get("record_id", arguments.get("key"))
            record = state["records"].get(record_id)
            result = {"ok": True, "record": deepcopy(record)} if record is not None else {"ok": False, "error": "synthetic record not found"}
        elif name == "read_remember_me_index":
            record_id = arguments.get("record_id", arguments.get("key"))
            record = state["remember_me_index"].get(record_id)
            result = {"ok": True, "record": deepcopy(record)} if record is not None else {"ok": False, "error": "synthetic index record not found"}
        elif name == "write_shopping_record":
            record_id = arguments.get("record_id", arguments.get("key"))
            value = arguments.get("value", arguments.get("record"))
            if fault == "reject":
                result = {"ok": False, "error": "synthetic record write rejected"}
            elif not isinstance(record_id, str) or not record_id or value is None:
                result = {"ok": False, "error": "invalid synthetic record update"}
            else:
                state["records"][record_id] = deepcopy(value)
                state["revision"] += 1
                _write(state_path, state)
                committed = True
                result = {"ok": True, "record_id": record_id, "revision": state["revision"]}
                if fault == "timeout_after_commit":
                    result = {"ok": False, "error": "synthetic acknowledgement timed out after commit"}
        elif name == "update_remember_me_index":
            record_id = arguments.get("record_id", arguments.get("key"))
            value = arguments.get("value", arguments.get("record"))
            if fault == "reject":
                result = {"ok": False, "error": "synthetic owner-index update rejected"}
            elif not isinstance(record_id, str) or value is None:
                result = {"ok": False, "error": "invalid synthetic owner-index update"}
            else:
                state["remember_me_index"][record_id] = deepcopy(value)
                state["revision"] += 1
                _write(state_path, state)
                committed = True
                result = {"ok": True, "record_id": record_id, "revision": state["revision"]}

        after_state = _read(state_path)
        after_hash = _json_hash(after_state)
        self.last_event_id = _append_event(self.root, request_id, name, arguments, result,
                                           before_hash, after_hash, attempted_write, committed)
        return result, attempted_write


def valid_source(source: Any, source_id: str) -> bool:
    return isinstance(source, dict) and source.get("source_id") == source_id \
        and isinstance(source.get("kind"), str) and source["kind"] in SOURCE_KINDS \
        and all(isinstance(source.get(field), str) and source[field].strip()
                for field in ("title", "url", "checked_at", "effective_date", "applicability")) \
        and isinstance(source.get("available"), bool) \
        and (source["available"] is False or isinstance(source.get("content"), (dict, list, str)))


TOOL_DETAILS: dict[str, tuple[str, dict[str, Any], list[str]]] = {
    "retrieve_source": (
        "Read one case-allowlisted synthetic research source by source_id from the source index. "
        "Returns attributable source bytes or an explicit unavailable result; never accesses the web or changes records.",
        {"type": "object", "properties": {"source_id": {"type": "string"}}, "additionalProperties": False},
        ["source_id"],
    ),
    "get_meal_plan_index": (
        "Read existing synthetic meal-plan IDs for a collision check.", {"type": "object", "properties": {}}, [],
    ),
    "record_grocery_result": (
        "Observe the actual returned grocery packet for synthetic reconciliation; this tool does not generate a result.",
        {"type": "object", "properties": {"plan_identity": {"type": "object"}, "request_id": {"type": "string"},
                                          "recipe_versions": {"type": "object"}, "workbook_identity": {"type": "object"},
                                          "returned_grocery_result": {"type": "object"}}},
        ["plan_identity", "request_id", "recipe_versions", "workbook_identity", "returned_grocery_result"],
    ),
    "save_meal_plan": (
        "Save the approved meal plan in the synthetic fixture only.",
        {"type": "object", "properties": {"plan_id": {"type": "string"}, "content": {"type": "object"}}}, ["plan_id", "content"],
    ),
    "read_meal_plan": (
        "Read back one saved synthetic meal plan by its stable ID.",
        {"type": "object", "properties": {"plan_id": {"type": "string"}}}, ["plan_id"],
    ),
    "get_case_context": (
        "Read the public synthetic case context. It contains no expected answers or controller assertions.",
        {"type": "object", "properties": {"section": {"type": "string"}}}, [],
    ),
    "get_spreadsheet_metadata": (
        "Read metadata for the synthetic workbook identified by spreadsheet_id.",
        {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}}, "required": ["spreadsheet_id"]},
        ["spreadsheet_id"],
    ),
    "get_spreadsheet_range": (
        "Read a synthetic spreadsheet range by its A1 range name.",
        {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}}, "required": ["spreadsheet_id", "range"]},
        ["spreadsheet_id", "range"],
    ),
    "get_spreadsheet_cells": (
        "Read cells from a synthetic spreadsheet range.",
        {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}}, "required": ["spreadsheet_id", "range"]},
        ["spreadsheet_id", "range"],
    ),
    "batch_update_spreadsheet": (
        "Apply requested updates only to the synthetic spreadsheet; all attempts are logged for scoring.",
        {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "updates": {"type": "array", "items": {"type": "object"}}}, "required": ["spreadsheet_id", "updates"]},
        ["spreadsheet_id", "updates"],
    ),
    "read_shopping_record": (
        "Read one synthetic shopping record by stable record_id.",
        {"type": "object", "properties": {"record_id": {"type": "string"}}, "required": ["record_id"]},
        ["record_id"],
    ),
    "read_remember_me_index": (
        "Read one synthetic Remember Me index entry by stable record_id.",
        {"type": "object", "properties": {"record_id": {"type": "string"}}, "required": ["record_id"]},
        ["record_id"],
    ),
    "write_shopping_record": (
        "Write one synthetic shopping record. This tool never accesses a real provider.",
        {"type": "object", "properties": {"record_id": {"type": "string"}, "value": {}}, "required": ["record_id", "value"]},
        ["record_id", "value"],
    ),
    "update_remember_me_index": (
        "Update one synthetic Remember Me ownership-index entry. This tool never accesses a real provider.",
        {"type": "object", "properties": {"record_id": {"type": "string"}, "value": {}}, "required": ["record_id", "value"]},
        ["record_id", "value"],
    ),
}


def serve(root: str | Path) -> None:
    store = Store(root)
    for line in sys.stdin:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(request, dict) or "id" not in request:
            continue
        request_id = request["id"]
        method = request.get("method")
        params = request.get("params", {})
        response: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
        if method == "initialize":
            requested = params.get("protocolVersion") if isinstance(params, dict) else None
            response["result"] = {
                "protocolVersion": requested if requested in SUPPORTED_PROTOCOLS else "2025-11-25",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "personal-shopper-synthetic-store", "version": "1.0.0"},
            }
        elif method == "ping":
            response["result"] = {}
        elif method == "tools/list":
            tools = []
            for name in store.control["allowed_tools"]:
                description, schema, required = TOOL_DETAILS[name]
                tools.append({
                    "name": name,
                    "description": description,
                    "inputSchema": {**deepcopy(schema), "required": required},
                })
            response["result"] = {"tools": tools}
        elif method == "tools/call" and isinstance(params, dict) and isinstance(params.get("name"), str):
            name = params["name"]
            arguments = params.get("arguments", {})
            if name not in TOOL_DETAILS or not isinstance(arguments, dict):
                result, attempted_write = {"ok": False, "error": "unknown synthetic tool"}, False
            else:
                result, attempted_write = store.call(request_id, name, arguments)
                if store.last_event_id is not None:
                    result = {**result, "fixture_event_id": store.last_event_id}
            response["result"] = {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "isError": not result.get("ok", False),
            }
        else:
            response["error"] = {"code": -32601, "message": "Unknown synthetic fixture method"}
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def snapshot(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    state = _read(root / "state.json")
    _write(root / "final-state.json", state)
    _write(root / "final-state.sha256", {"sha256": _json_hash(state)})
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    initialize_parser = subparsers.add_parser("init")
    initialize_parser.add_argument("root", type=Path)
    initialize_parser.add_argument("--case", required=True)
    initialize_parser.add_argument("--allowed-tools", default="[]")
    initialize_parser.add_argument("--faults", default="{}")
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("root", type=Path)
    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("root", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "init":
            initialize(args.root, args.case, json.loads(args.allowed_tools), faults=json.loads(args.faults))
        elif args.action == "serve":
            serve(args.root)
        else:
            snapshot(args.root)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"store: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
