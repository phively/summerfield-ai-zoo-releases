#!/usr/bin/env python3
"""Score Personal Shopper's delegated first-plan synthetic evidence."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import re
import sys
import tomllib
from typing import Any

import capture_invocation as capture
from store import spreadsheet_id_from_arguments

EVAL_ROOT = Path(__file__).resolve().parent


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _valid_installed_resource(call: dict[str, Any], installed: dict[str, str]) -> bool:
    if call.get("server") != "shopping-skill-resources" or call.get("tool") != "read_installed_skill_file" \
            or call.get("status") != "completed" or call.get("error"):
        return False
    args = call.get("arguments")
    if not isinstance(args, dict) or set(args) != {"package", "relative_path"}:
        return False
    package, relative = args["package"], args["relative_path"]
    if not isinstance(package, str) or not isinstance(relative, str) or "\\" in relative:
        return False
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or str(path) != relative or not relative.endswith(".md"):
        return False
    payload = call.get("result")
    if isinstance(payload, dict) and (payload.get("isError") or payload.get("is_error")):
        return False
    if isinstance(payload, dict) and isinstance(payload.get("structuredContent"), dict):
        payload = payload["structuredContent"]
    elif isinstance(payload, dict) and isinstance(payload.get("structured_content"), dict):
        payload = payload["structured_content"]
    elif isinstance(payload, dict) and isinstance(payload.get("content"), list):
        try:
            payload = json.loads(payload["content"][0]["text"])
        except (IndexError, KeyError, TypeError, json.JSONDecodeError):
            return False
    if not isinstance(payload, dict) or payload.get("package") != package \
            or payload.get("relative_path") != relative or not isinstance(payload.get("text"), str):
        return False
    digest = capture.sha256(payload["text"].encode())
    return payload.get("sha256") == digest == installed.get(f"{package}/{relative}")


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk(nested)
    elif isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return
        if isinstance(decoded, (dict, list)):
            yield from _walk(decoded)


def _rollout_events(path: Path, expected_sha256: str) -> list[dict[str, Any]]:
    try:
        return capture._read_rollout(path, expected_sha256=expected_sha256)
    except ValueError as error:
        if str(error) == "rollout path is invalid":
            raise ValueError("delegation rollout path is invalid") from error
        if str(error) == "rollout digest mismatch":
            raise ValueError("delegation rollout digest or completeness check failed") from error
        raise ValueError("delegation rollout is incomplete or invalid") from error


def _delegation_capture(directory: Path, result: dict[str, Any], stdout: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        return _load_delegation_capture(directory, result, stdout)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return {"valid": False, "parent": [], "children": {}}


def _load_delegation_capture(directory: Path, result: dict[str, Any], stdout: list[dict[str, Any]]) -> dict[str, Any]:
    declared = result.get("delegation_rollouts")
    metadata_path = directory / "delegation-rollouts.json"
    if metadata_path.is_symlink():
        return {"valid": False, "parent": [], "children": {}}
    metadata = _read(metadata_path)
    if not isinstance(declared, dict) or declared != metadata \
            or metadata.get("schema") != "codex-delegation-rollouts/v1" \
            or metadata.get("status") != "captured":
        return {"valid": False, "parent": [], "children": {}}
    parent_id = metadata.get("parent_thread_id")
    stdout_parent = next((event.get("thread_id") for event in stdout if event.get("type") == "thread.started"), None)
    parent_file = metadata.get("parent_file")
    if parent_id != stdout_parent or parent_file != "delegation-rollouts/parent.jsonl":
        return {"valid": False, "parent": [], "children": {}}
    parent_path = directory / parent_file
    parent_events = _rollout_events(parent_path, metadata.get("parent_sha256", ""))
    children = {}
    child_meta = metadata.get("children")
    if not isinstance(child_meta, list) or not child_meta:
        return {"valid": False, "parent": parent_events, "children": {}}
    for entry in child_meta:
        if not isinstance(entry, dict):
            return {"valid": False, "parent": parent_events, "children": {}}
        thread_id, relative, digest = entry.get("thread_id"), entry.get("file"), entry.get("sha256")
        if not isinstance(thread_id, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,128}", thread_id) \
                or relative != f"delegation-rollouts/child-{thread_id}.jsonl" \
                or thread_id in children:
            return {"valid": False, "parent": parent_events, "children": {}}
        children[thread_id] = _rollout_events(directory / relative, digest)
    related = _subagent_activities(parent_events)
    if set(children) != {activity["thread_id"] for activity in related}:
        return {"valid": False, "parent": parent_events, "children": children}
    return {"valid": True, "parent": parent_events, "children": children,
            "parent_thread_id": parent_id}


def _subagent_activities(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    activities: dict[str, dict[str, Any]] = {}
    for index, event in enumerate(events):
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        item = payload.get("item")
        if not isinstance(item, dict) or item.get("type") != "SubAgentActivity":
            continue
        thread_id = item.get("agent_thread_id") or item.get("child_thread_id")
        item_id = item.get("id") or item.get("call_id")
        if not isinstance(thread_id, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,128}", thread_id) \
                or not isinstance(item_id, str):
            raise ValueError("subagent activity has no valid identity")
        activity = activities.setdefault(thread_id, {"thread_id": thread_id, "started": None,
                                                       "completed": None, "start_item_id": None,
                                                       "complete_item_id": None, "start_count": 0,
                                                       "complete_count": 0,
                                                       "completion_indexes": []})
        kind = item.get("kind")
        if kind == "started" or payload.get("type") in {"item_started", "item.started"}:
            activity["start_count"] += 1
            activity["started"] = index
            activity["start_item_id"] = item_id
        elif kind == "completed" or payload.get("type") in {"item_completed", "item.completed"}:
            activity["complete_count"] += 1
            activity["completed"] = index
            activity["complete_item_id"] = item_id
            activity["completion_indexes"].append(index)
            activity["result"] = item.get("result") or item.get("output") or item.get("message")
    return [item for item in activities.values() if item["started"] is not None
            and item["completed"] is not None and item["start_count"] == 1
            and item["complete_count"] >= 1 and item["completed"] > item["started"]
            and all(index > item["started"] for index in item["completion_indexes"])]


def _rollout_tool_calls(events: list[dict[str, Any]], thread_id: str,
                        require_explicit_thread: bool = True) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for index, event in enumerate(events):
        payload = event.get("payload")
        item = payload.get("item") if isinstance(payload, dict) else None
        if not isinstance(item, dict) or item.get("type") != "McpToolCall":
            continue
        owner = item.get("thread_id") or payload.get("thread_id") or event.get("thread_id")
        if (require_explicit_thread and owner != thread_id) or (owner is not None and owner != thread_id):
            continue
        call_id = item.get("call_id") or item.get("id")
        server = item.get("server") or item.get("server_name")
        tool = item.get("tool") or item.get("name") or item.get("tool_name")
        arguments = item.get("arguments", item.get("input"))
        if not all(isinstance(value, str) and value for value in (call_id, server, tool)):
            continue
        if call_id not in grouped:
            grouped[call_id] = {"event_index": index, "start_index": None,
                                "completion_index": None,
                                "thread_id": owner, "call_id": call_id,
                                "server": server, "tool": tool, "arguments": arguments,
                                "result": None, "status": "incomplete"}
            order.append(call_id)
        call = grouped[call_id]
        if call["status"] == "invalid":
            continue
        if (call["server"], call["tool"]) != (server, tool) \
                or call["arguments"] not in (None, arguments) and arguments is not None:
            call["status"] = "invalid"
            continue
        if arguments is not None:
            call["arguments"] = arguments
        status = item.get("status")
        event_type = payload.get("type")
        if event_type in {"item_completed", "item.completed"}:
            status = "completed"
        elif event_type in {"item_failed", "item.failed"}:
            status = "failed"
        if event_type in {"item_started", "item.started"} or status in {"in_progress", "started"}:
            if call["completion_index"] is not None or call["status"] in {"completed", "failed", "cancelled"}:
                call["status"] = "invalid"
                continue
            if call["start_index"] is not None and call["start_index"] != index:
                call["status"] = "invalid"
                continue
            call["start_index"] = index
        if status in {"completed", "failed", "cancelled"}:
            if call["start_index"] is not None and call["start_index"] >= index:
                call["status"] = "invalid"
                continue
            if call["status"] in {"completed", "failed", "cancelled"} and call["status"] != status:
                call["status"] = "invalid"
                continue
            if call["completion_index"] is None:
                call["completion_index"] = index
                call["event_index"] = index
            call["status"] = status
        if "result" in item:
            if call["result"] is not None and call["result"] != item["result"]:
                call["status"] = "invalid"
                continue
            call["result"] = item["result"]
        elif "output" in item:
            if call["result"] is not None and call["result"] != item["output"]:
                call["status"] = "invalid"
                continue
            call["result"] = item["output"]
    return [grouped[call_id] for call_id in order]


def _child_rollout_calls(events: list[dict[str, Any]], child_thread_id: str,
                         parent_thread_id: str) -> list[dict[str, Any]] | None:
    calls = []
    for index, event in enumerate(events):
        payload = event.get("payload")
        item = payload.get("item") if isinstance(payload, dict) else None
        if not isinstance(item, dict) or item.get("type") != "McpToolCall":
            continue
        owner = item.get("thread_id") or payload.get("thread_id") or event.get("thread_id")
        if owner == parent_thread_id:
            continue
        if owner != child_thread_id:
            return None
        if not all(isinstance(item.get(key) or item.get(alternate), str) and (item.get(key) or item.get(alternate))
                   for key, alternate in (("call_id", "id"), ("server", "server_name"), ("tool", "name"))):
            return None
    return _rollout_tool_calls(events, child_thread_id)


def _message_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [_message_text(item) for item in value]
        text = "".join(part or "" for part in parts)
        return text if text else None
    if isinstance(value, dict):
        for key in ("text", "body", "content"):
            if key in value:
                text = _message_text(value[key])
                if text is not None:
                    return text
    return None


def _assistant_messages(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    messages = []
    for index, event in enumerate(events):
        if event.get("type") != "response_item":
            continue
        item = event.get("payload")
        if not isinstance(item, dict) or item.get("type") != "message" or item.get("role") != "assistant":
            continue
        text = _message_text(item.get("content", item.get("body", item.get("text"))))
        message_id = item.get("id") or item.get("message_id")
        if isinstance(text, str) and isinstance(message_id, str):
            messages.append({"index": index, "id": message_id, "text": text,
                             "sha256": capture.sha256(text.encode()),
                             "phase": item.get("phase"), "status": item.get("status")})
    return messages


def _agent_message_returns(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    messages = []
    for index, event in enumerate(events):
        payload = event.get("payload")
        item = payload.get("item") if isinstance(payload, dict) else None
        if not isinstance(item, dict) or item.get("type") != "AgentMessage" \
                or item.get("phase") != "final_answer":
            continue
        message_id = item.get("id")
        text = _message_text(item.get("content"))
        if isinstance(message_id, str) and isinstance(text, str):
            messages.append({"index": index, "id": message_id, "text": text,
                             "sha256": capture.sha256(text.encode())})
    return messages


def _fixture_event_id_from_result(value: Any) -> str | None:
    found: set[str] = set()
    for item in _walk(value):
        event_id = item.get("fixture_event_id")
        if isinstance(event_id, str):
            found.add(event_id)
    if len(found) != 1:
        return None
    event_id = next(iter(found))
    return event_id if re.fullmatch(r"fixture-[0-9a-f]{32}", event_id) else None


def _fixture_result_payload_from_tool_result(value: Any) -> dict[str, Any] | None:
    payloads: dict[str, str] = {}
    for item in _walk(value):
        if isinstance(item.get("fixture_event_id"), str):
            payload = {key: nested for key, nested in item.items() if key != "fixture_event_id"}
            payloads[json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))] = ""
    if len(payloads) != 1:
        return None
    try:
        return json.loads(next(iter(payloads)))
    except json.JSONDecodeError:
        return None


def _fixture_calls_reconcile(parent_calls: list[dict[str, Any]], child_calls: list[dict[str, Any]],
                             fixture_events: list[dict[str, Any]], *,
                             allow_failed_results: bool = False) -> bool:
    recorded: dict[str, dict[str, Any]] = {}
    for event in fixture_events:
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not re.fullmatch(r"fixture-[0-9a-f]{32}", event_id) \
                or event_id in recorded:
            return False
        recorded[event_id] = event
    observed: dict[str, dict[str, Any]] = {}
    for calls in (parent_calls, child_calls):
        seen_in_source: set[str] = set()
        for call in calls:
            if call.get("server") != "shopping-fixture" or call.get("status") not in {"completed", "failed"}:
                return False
            event_id = _fixture_event_id_from_result(call.get("result"))
            if event_id is None or event_id not in recorded or event_id in seen_in_source:
                return False
            event = recorded[event_id]
            if call.get("status") == "failed" and not (
                allow_failed_results and event.get("result", {}).get("ok") is False
            ):
                return False
            if call.get("tool") != event.get("tool") or call.get("arguments") != event.get("arguments") \
                    or _fixture_result_payload_from_tool_result(call.get("result")) != event.get("result"):
                return False
            existing = observed.get(event_id)
            identity = {"tool": call.get("tool"), "arguments": call.get("arguments")}
            if existing is not None and existing != identity:
                return False
            observed[event_id] = identity
            seen_in_source.add(event_id)
    return set(observed) == set(recorded)


def _matches_expected_handoff(packet: Any, expected: dict[str, Any], identity: dict[str, Any],
                              public_context: dict[str, Any]) -> bool:
    if not isinstance(packet, dict):
        return False
    versions = expected.get("recipe_versions", {})
    required = {
        "protocol": public_context.get("protocol"),
        "request_id": expected.get("request_id"),
        "recipe_ids": list(versions),
        "recipe_versions": versions,
        "plan_identity": identity,
        "workbook_identity": expected.get("workbook_identity"),
        "recipe_packet": public_context.get("recipe_packet"),
        "approval": public_context.get("approval"),
        "confirmed_pantry": public_context.get("confirmed_pantry"),
        "region": public_context.get("region"),
        "currency": public_context.get("currency"),
        "shopping_date": public_context.get("shopping_date"),
        "budget": public_context.get("budget"),
        "preferred_stores": public_context.get("preferred_stores"),
        "check_pantry": public_context.get("check_pantry"),
        "required_constraints": public_context.get("required_constraints"),
        "shopping_record_write_authorization": public_context.get("shopping_record_write_authorization"),
        "unresolved_questions": public_context.get("unresolved_questions"),
    }
    return all(value is not None and packet.get(key) == value for key, value in required.items())


def _completed_shopper_return(rollouts: dict[str, Any], expected: dict[str, Any], identity: dict[str, Any],
                              public_context: dict[str, Any], installed: dict[str, str],
                              required_caller_resources: list[str],
                              required_child_resources: list[str],
                              required_child_fixture_tools: list[str],
                              fixture_events: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rollouts.get("valid"):
        return None
    parent_events = rollouts["parent"]
    activities = _subagent_activities(parent_events)
    if len(activities) != 1:
        return None
    activity = activities[0]
    parent_messages = _assistant_messages(parent_events)
    before_fork = [message for message in parent_messages if message["index"] < activity["started"]]
    packet_message = None
    packet = None
    for message in reversed(before_fork):
        try:
            parsed = json.loads(message["text"])
        except json.JSONDecodeError:
            continue
        if _matches_expected_handoff(parsed, expected, identity, public_context):
            packet_message, packet = message, parsed
            break
    if packet_message is None:
        return None
    if not before_fork or before_fork[-1] != packet_message:
        return None
    parent_thread_id = rollouts.get("parent_thread_id", "")
    parent_calls = _rollout_tool_calls(parent_events, parent_thread_id, require_explicit_thread=False)
    fixture_events_by_id = {event.get("event_id"): event for event in fixture_events
                            if isinstance(event.get("event_id"), str)}
    required_caller_resources = set(required_caller_resources)
    if not required_caller_resources:
        return None
    caller_resource_calls = [call for call in parent_calls
                             if call.get("server") == "shopping-skill-resources"
                             and call.get("tool") == "read_installed_skill_file"]
    observed_caller_resources = {
        f"{call.get('arguments', {}).get('package')}/{call.get('arguments', {}).get('relative_path')}"
        for call in caller_resource_calls if isinstance(call.get("arguments"), dict)
        and _valid_installed_resource(call, installed)
        and call.get("completion_index", -1) < packet_message["index"]
    }
    if any(not _valid_installed_resource(call, installed)
           or call.get("completion_index", -1) >= packet_message["index"] for call in caller_resource_calls) \
            or not required_caller_resources <= observed_caller_resources:
        return None
    index_calls = [call for call in parent_calls if call.get("server") == "shopping-fixture"
                   and call.get("tool") == "get_meal_plan_index"
                   and call.get("status") == "completed"]
    if len(index_calls) != 1:
        return None
    index_call = index_calls[0]
    index_event = fixture_events_by_id.get(_fixture_event_id_from_result(index_call.get("result")))
    if index_call.get("completion_index", -1) >= packet_message["index"] \
            or index_event is None or index_event.get("tool") != "get_meal_plan_index" \
            or index_event.get("arguments") != index_call.get("arguments") \
            or _fixture_result_payload_from_tool_result(index_call.get("result")) != index_event.get("result") \
            or not isinstance(index_event.get("result"), dict) \
            or index_event["result"].get("ok") is not True \
            or not isinstance(index_event["result"].get("plan_ids"), list) \
            or expected.get("plan_id") in index_event["result"].get("plan_ids", []):
        return None
    child_events = rollouts["children"].get(activity["thread_id"], [])
    child_messages = _assistant_messages(child_events)
    inherited = [message for message in child_messages
                 if message["id"] == packet_message["id"] and message["sha256"] == packet_message["sha256"]]
    if not inherited:
        return None
    child_calls = _child_rollout_calls(
        child_events, activity["thread_id"], rollouts.get("parent_thread_id", "")
    )
    if child_calls is None:
        return None
    required_child_resources = set(required_child_resources)
    required_child_fixture_tools = set(required_child_fixture_tools)
    if not required_child_resources or not required_child_fixture_tools:
        return None
    child_resource_calls = [call for call in child_calls
                            if call.get("server") == "shopping-skill-resources"
                            and call.get("tool") == "read_installed_skill_file"]
    child_fixture_calls = [call for call in child_calls if call.get("server") == "shopping-fixture"]
    observed_child_resources = {
        f"{call.get('arguments', {}).get('package')}/{call.get('arguments', {}).get('relative_path')}"
        for call in child_resource_calls if isinstance(call.get("arguments"), dict)
        and _valid_installed_resource(call, installed)
    }
    if any(not _valid_installed_resource(call, installed) for call in child_resource_calls) \
            or not required_child_resources <= observed_child_resources:
        return None
    if any(call.get("tool") not in required_child_fixture_tools
           or call.get("status") != "completed"
           or not isinstance(call.get("arguments"), dict)
           or spreadsheet_id_from_arguments(call["arguments"]) != expected.get("workbook_identity", {}).get("spreadsheet_id")
           for call in child_fixture_calls):
        return None
    if any(call.get("start_index") is None for call in child_fixture_calls):
        return None
    if any(
        (event := fixture_events_by_id.get(_fixture_event_id_from_result(call.get("result")))) is None
        or event.get("tool") != call.get("tool")
        or event.get("arguments") != call.get("arguments")
        or _fixture_result_payload_from_tool_result(call.get("result")) != event.get("result")
        or not isinstance(event.get("result"), dict)
        or event["result"].get("ok") is not True
        for call in child_fixture_calls
    ):
        return None
    child_fixture_starts = [call["start_index"] for call in child_fixture_calls]
    pre_work_resources = {
        f"{call.get('arguments', {}).get('package')}/{call.get('arguments', {}).get('relative_path')}"
        for call in child_resource_calls if isinstance(call.get("arguments"), dict)
        and (not child_fixture_starts or call["completion_index"] < min(child_fixture_starts))
    }
    if child_fixture_starts and not required_child_resources <= pre_work_resources:
        return None
    if not child_messages:
        return None
    terminal_messages = [message for message in child_messages
                         if message.get("phase") == "final_answer" and message.get("status") == "completed"]
    if not terminal_messages:
        return None
    response_message = max(terminal_messages, key=lambda message: message["index"])
    if response_message["index"] <= max(call["event_index"] for call in child_calls) \
            or response_message != max(child_messages, key=lambda message: message["index"]):
        return None
    try:
        response = json.loads(response_message["text"])
    except json.JSONDecodeError:
        return None
    if not isinstance(response, dict) or response.get("protocol") != "grocery-handoff/v1":
        return None
    returned_by_agent = [message for message in _agent_message_returns(parent_events)
                         if message["index"] > activity["completed"]
                         and message["id"] == response_message["id"]
                         and message["sha256"] == response_message["sha256"]]
    if len(returned_by_agent) != 1:
        return None
    parent_return_messages = [message for message in parent_messages
                              if message["index"] > returned_by_agent[0]["index"]
                              and message.get("phase") == "final_answer"
                              and message.get("status") == "completed"
                              and message["id"] == response_message["id"]
                              and message["sha256"] == response_message["sha256"]]
    if len(parent_return_messages) != 1:
        return None
    parent_record_calls = [call for call in parent_calls if call.get("server") == "shopping-fixture"
                           and call.get("tool") == "record_grocery_result"
                           and call.get("status") == "completed"]
    if len(parent_record_calls) != 1 \
            or parent_record_calls[0].get("arguments", {}).get("returned_grocery_result") != response \
            or parent_record_calls[0].get("start_index") is None \
        or parent_record_calls[0].get("start_index", -1) <= parent_return_messages[0]["index"]:
        return None
    return {"activity": activity, "packet_message": packet_message, "packet": packet,
            "child_calls": child_calls, "response_message": response_message,
            "response": response, "child_thread_id": activity["thread_id"],
            "parent_record_call": parent_record_calls[0],
            "parent_return_message": parent_return_messages[0],
            "child_fixture_calls": child_fixture_calls,
            "caller_resource_calls": caller_resource_calls}


def _multi_agent_runtime_matches(settings: dict[str, Any], enabled: bool) -> bool:
    command = settings.get("command")
    if not isinstance(command, list) or any(not isinstance(item, str) for item in command):
        return False
    disabled = [command[index + 1] for index, value in enumerate(command[:-1])
                if value == "--disable"]
    enabled_values = [command[index + 1] for index, value in enumerate(command[:-1])
                      if value == "--enable"]
    persist_rollouts = settings.get("persist_rollouts")
    required_disabled = {"shell_tool", "unified_exec", "apps", "browser_use", "computer_use"}
    return settings.get("multi_agent_enabled") is enabled \
        and persist_rollouts is enabled \
        and (("--ephemeral" not in command) if enabled else ("--ephemeral" in command)) \
        and (disabled.count("multi_agent") == 0 if enabled else disabled.count("multi_agent") == 1) \
        and enabled_values == (["multi_agent"] if enabled else []) \
        and settings.get("sandbox") == "read-only" \
        and required_disabled <= set(disabled) and settings.get("provider_apps") == []


def _delegation_runtime_matches(directory: Path, result: dict[str, Any],
                                settings: dict[str, Any], subcase: dict[str, Any]) -> bool:
    try:
        workspace_path = directory / "runtime-config.toml"
        home_path = directory / "isolated-codex-home-config.toml"
        resources_path = directory / "skill-resource-config.json"
        if any(path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077
               for path in (workspace_path, home_path, resources_path)):
            return False
        workspace_raw, home_raw, resources_raw = (
            workspace_path.read_bytes(), home_path.read_bytes(), resources_path.read_bytes()
        )
        if capture.sha256(workspace_raw) != settings.get("runtime_config_sha256") \
                or capture.sha256(home_raw) != result.get("isolated_codex_home_config_sha256") \
                or settings.get("isolated_codex_home_config_sha256") != result.get("isolated_codex_home_config_sha256"):
            return False
        workspace = tomllib.loads(workspace_raw.decode("utf-8"))
        home = tomllib.loads(home_raw.decode("utf-8"))
        if home.get("approval_policy") != "never" or home.get("sandbox_mode") != "read-only":
            return False
        features = workspace.get("features", {})
        if not all(features.get(name) is expected for name, expected in {
            "multi_agent": True, "shell_tool": False, "unified_exec": False,
            "apps": False, "browser_use": False, "computer_use": False,
        }.items()):
            return False
        apps = workspace.get("apps", {})
        if apps != {"_default": {"enabled": False, "default_tools_enabled": False}}:
            return False
        servers = home.get("mcp_servers", {})
        if set(servers) != {"shopping-fixture", "shopping-skill-resources"}:
            return False
        fixture = settings.get("fixture")
        if not isinstance(fixture, dict) or fixture.get("allowed_tools") != subcase.get("tools") \
                or fixture.get("permitted_operations") != subcase.get("permitted_operations"):
            return False
        fixture_server = servers["shopping-fixture"]
        fixture_args = fixture_server.get("args")
        if Path(fixture_server.get("command", "")).resolve() != Path(sys.executable).resolve() \
                or not isinstance(fixture_args, list) or len(fixture_args) != 3 \
                or Path(fixture_args[0]).resolve() != (EVAL_ROOT / "store.py").resolve() \
                or fixture_args[1] != "serve" \
                or Path(fixture_args[2]).resolve() != (directory / "fixture-store").resolve():
            return False
        reader = settings.get("skill_resource_reader")
        if not isinstance(reader, dict) or reader.get("server") != "shopping-skill-resources" \
                or reader.get("tool") != "read_installed_skill_file":
            return False
        reader_args = servers["shopping-skill-resources"].get("args")
        if Path(servers["shopping-skill-resources"].get("command", "")).resolve() != Path(sys.executable).resolve() \
                or not isinstance(reader_args, list) or len(reader_args) != 2 \
                or Path(reader_args[0]).resolve() != (EVAL_ROOT / "skill_resources.py").resolve() \
                or Path(reader_args[1]).resolve() != (directory / "skill-resource-config.json").resolve():
            return False
        if capture.sha256(resources_raw) != reader.get("config_sha256"):
            return False
        resource_config = json.loads(resources_raw)
        packages = resource_config.get("packages") if isinstance(resource_config, dict) else None
        declared = reader.get("packages")
        actual = {f"{name}/{path}" for name, item in packages.items()
                  for path in item.get("files", {})} if isinstance(packages, dict) else set()
        expected = set(subcase.get("required_skill_resources", []))
        required_caller = subcase.get("required_caller_skill_resources")
        required_child = subcase.get("required_child_skill_resources")
        if not isinstance(required_caller, list) or not required_caller \
                or any(not isinstance(path, str) for path in required_caller) \
                or len(required_caller) != len(set(required_caller)) \
                or not isinstance(required_child, list) or not required_child \
                or any(not isinstance(path, str) for path in required_child) \
                or len(required_child) != len(set(required_child)) \
                or set(required_caller) & set(required_child) \
                or set(required_caller) | set(required_child) != expected:
            return False
        required_child_fixture_tools = subcase.get("required_child_fixture_read_tools")
        if not isinstance(required_child_fixture_tools, list) or not required_child_fixture_tools \
                or len(required_child_fixture_tools) != len(set(required_child_fixture_tools)) \
                or not set(required_child_fixture_tools) <= set(subcase.get("tools", [])) \
                or not set(required_child_fixture_tools) <= {"get_spreadsheet_metadata", "get_spreadsheet_range"}:
            return False
        declared_paths = {f"{name}/{path}" for name, files in declared.items()
                          for path in files} if isinstance(declared, dict) else set()
        return actual == declared_paths == expected and settings.get("external_packages") == {}
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, json.JSONDecodeError, tomllib.TOMLDecodeError):
        return False


def case_checks(subcase_id: str, state: dict[str, Any], events: list[dict[str, Any]],
                control: dict[str, Any] | None = None,
                delegation: dict[str, Any] | None = None) -> dict[str, bool]:
    if subcase_id == "B10-AE12-new-plan":
        delegation = delegation or {}
        indexes = [e for e in events if e.get("tool") == "get_meal_plan_index" and e.get("result", {}).get("ok") is True]
        results = [e for e in events if e.get("tool") == "record_grocery_result" and e.get("result", {}).get("ok") is True]
        saves = [e for e in events if e.get("tool") == "save_meal_plan" and e.get("attempted_write")]
        reads = [e for e in events if e.get("tool") == "read_meal_plan" and e.get("result", {}).get("ok") is True]
        grocery_arguments = results[-1].get("arguments", {}) if results else {}
        identity = grocery_arguments.get("plan_identity", {})
        returned_result = grocery_arguments.get("returned_grocery_result")
        plan_id = identity.get("plan_id") if isinstance(identity, dict) else None
        content = state.get("meal_plans", {}).get(plan_id, {}).get("content", {})
        expected = (control or {}).get("expected", {})
        expected_versions = expected.get("recipe_versions", {})
        shopper_return = _completed_shopper_return(
            delegation.get("rollouts", {}), expected, identity,
            delegation.get("public_context", {}), delegation.get("installed", {}),
            delegation.get("required_caller_skill_resources", []),
            delegation.get("required_child_skill_resources", []),
            delegation.get("required_child_fixture_read_tools", []),
            delegation.get("fixture_events", []),
        )
        response = shopper_return["response"] if shopper_return else None
        packet_identity = response.get("plan_identity") if isinstance(response, dict) else None
        packet_grocery = response if isinstance(response, dict) else None

        record_calls = [call for call in capture.mcp_tool_ledger(delegation.get("host_events", []))
                        if call.get("server") == "shopping-fixture"
                        and call.get("tool") == "record_grocery_result"
                        and call.get("status") == "completed"]
        record_call_index = max(record_calls[0].get("event_indexes", []), default=-1) \
            if len(record_calls) == 1 else -1

        def contains_required_item(value: Any) -> bool:
            if isinstance(value, dict):
                if value.get("ingredient") == expected.get("required_ingredient"):
                    required_g = expected.get("required_g")
                    required_quantity = value.get("required_quantity")
                    if (value.get("required_g") == required_g
                            or isinstance(required_quantity, dict)
                            and required_quantity.get("value") == required_g
                            and required_quantity.get("unit") == "g"):
                        return True
                return any(contains_required_item(item) for item in value.values())
            if isinstance(value, list):
                return any(contains_required_item(item) for item in value)
            return False

        def contains_identity(value: Any) -> bool:
            if value == identity:
                return True
            if isinstance(value, dict):
                return any(contains_identity(item) for item in value.values())
            if isinstance(value, list):
                return any(contains_identity(item) for item in value)
            return False
        return {
            "proposed_id_checked_for_collision": bool(indexes and results) and isinstance(plan_id, str)
            and bool(re.fullmatch(r"MP-\d{4}-\d{2}-\d{2}-\d{2}", plan_id))
            and (not expected.get("plan_date") or plan_id.startswith(f"MP-{expected['plan_date']}-"))
            and plan_id not in indexes[-1]["result"].get("plan_ids", [])
            and indexes[-1].get("sequence", 0) < results[-1].get("sequence", 0),
            "grocery_identity_unchanged": bool(results) and isinstance(identity, dict)
            and identity.get("identity_status") == "proposed" and identity.get("native_resource") == "not-yet-created",
            "grocery_source_identities_unchanged": bool(results) and all(
                key not in expected or grocery_arguments.get(key) == expected[key]
                for key in ("request_id", "recipe_versions", "workbook_identity")
            ),
            "actual_shopper_return_recorded_before_plan_save": bool(shopper_return and results)
            and response.get("protocol") == "grocery-handoff/v1"
            and response.get("request_id") == expected.get("request_id")
            and response.get("recipe_ids") == list(expected_versions)
            and response.get("recipe_versions") == expected_versions
            and packet_identity == identity
            and response.get("workbook_identity") == expected.get("workbook_identity")
            and response.get("capability") in {"full", "fallback"}
            and isinstance(packet_grocery, dict) and contains_required_item(packet_grocery)
            and returned_result == response
            and len(record_calls) == 1
            and record_calls[0].get("arguments") == grocery_arguments
            and shopper_return["parent_record_call"].get("arguments") == grocery_arguments
            and record_call_index >= 0,
            "same_plan_saved_after_grocery_and_read_back": len(saves) == 1 and saves[0].get("committed") is True and bool(results and reads)
            and saves[0].get("arguments", {}).get("plan_id") == plan_id
            and results[-1].get("sequence", 0) < saves[0].get("sequence", 0) < reads[-1].get("sequence", 0)
            and reads[-1].get("result", {}).get("plan_id") == plan_id
            and reads[-1].get("result", {}).get("content") == content
            and isinstance(content, dict) and contains_identity(content)
            and content.get("grocery") == returned_result,
        }
    if subcase_id == "B10-AE12-existing-plan":
        return {"no_grocery_result_or_plan_write_without_existing_identity": not any(
            event.get("attempted_write") or event.get("tool") == "record_grocery_result" for event in events
        )}
    raise ValueError(f"unsupported AE12 subcase: {subcase_id}")
