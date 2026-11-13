from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest


from shopping_test_support import EVAL, load_runner, load_scorer, load_store


def test_first_plan_fixture_exposes_collision_lookup_and_verified_plan_save(tmp_path, monkeypatch):
    store_module = load_store()
    case = {
        "id": "AE12-new", "context": {"existing_plan_ids": ["MP-2026-10-27-01"]},
        "expected": {"plan_id": "MP-2026-10-27-02"},
    }
    monkeypatch.setattr(store_module, "_case", lambda _case_id: case)
    root = store_module.initialize(tmp_path / "trial", "AE12-new", [
        "get_meal_plan_index", "record_grocery_result", "save_meal_plan", "read_meal_plan"
    ])
    store = store_module.Store(root)
    index, _ = store.call("1", "get_meal_plan_index", {})
    assert index["plan_ids"] == ["MP-2026-10-27-01"]
    grocery = {"identity_status": "proposed", "plan_id": "MP-2026-10-27-02",
               "native_resource": "not-yet-created"}
    result = {
        "protocol": "grocery-handoff/v1", "request_id": "SHOP-AE12-001",
        "recipe_ids": ["TEST-RECIPE-101"], "recipe_versions": {"TEST-RECIPE-101": "4"},
        "plan_identity": grocery,
        "workbook_identity": {"provider": "synthetic-shopping-fixture", "spreadsheet_id": "SYNTHETIC-SHOPPING-AE12"},
        "capability": "full", "grocery_sections": [{"items": [{
            "ingredient": "canned chickpeas", "required_quantity": {"value": 400, "unit": "g"},
        }]}],
    }
    observed, recorded_write = store.call("2", "record_grocery_result", {
        "plan_identity": grocery, "request_id": result["request_id"],
        "recipe_versions": result["recipe_versions"], "workbook_identity": result["workbook_identity"],
            "returned_grocery_result": result,
    })
    assert observed["ok"] and not recorded_write
    saved, attempted = store.call("3", "save_meal_plan", {"plan_id": grocery["plan_id"], "content": {"grocery": grocery}})
    assert saved["ok"] and attempted
    reread, _ = store.call("4", "read_meal_plan", {"plan_id": grocery["plan_id"]})
    assert reread["content"]["grocery"] == grocery
    assert reread["plan_id"] == grocery["plan_id"]
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    assert [event["tool"] for event in events] == ["get_meal_plan_index", "record_grocery_result", "save_meal_plan", "read_meal_plan"]


def test_first_plan_fixture_rejects_nested_only_grocery_result(tmp_path, monkeypatch):
    store_module = load_store()
    case = {"id": "AE12-new", "context": {}}
    monkeypatch.setattr(store_module, "_case", lambda _case_id: case)
    root = store_module.initialize(tmp_path / "trial", "AE12-new", ["record_grocery_result"])
    store = store_module.Store(root)
    identity = {"identity_status": "proposed", "plan_id": "MP-2026-10-27-02",
                "native_resource": "not-yet-created"}
    packet = {
        "protocol": "grocery-handoff/v1", "request_id": "SHOP-AE12-001",
        "recipe_ids": ["TEST-RECIPE-101"], "recipe_versions": {"TEST-RECIPE-101": "4"},
        "plan_identity": identity,
        "workbook_identity": {"provider": "synthetic-shopping-fixture", "spreadsheet_id": "SYNTHETIC-SHOPPING-AE12"},
        "capability": "fallback", "grocery_result": {"items": [{"ingredient": "canned chickpeas", "required_g": 400}]},
    }
    result, attempted = store.call("1", "record_grocery_result", {
        "plan_identity": identity, "request_id": packet["request_id"],
        "recipe_versions": packet["recipe_versions"], "workbook_identity": packet["workbook_identity"],
        "returned_grocery_result": packet,
    })
    assert result["ok"] is False
    assert not attempted


def test_fixture_tool_response_exposes_ledger_event_identity(tmp_path, monkeypatch):
    store_module = load_store()
    monkeypatch.setattr(store_module, "_case", lambda _case_id: {"id": "AE12", "context": {}})
    root = store_module.initialize(tmp_path / "fixture", "AE12", ["get_spreadsheet_metadata"])
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "get_spreadsheet_metadata",
            "arguments": {"spreadsheet_id": "SYNTHETIC-SHOPPING-AE12"}}},
    ]
    result = subprocess.run(
        [sys.executable, str(EVAL / "store.py"), "serve", str(root)],
        input="".join(json.dumps(request) + "\n" for request in requests),
        capture_output=True, text=True, check=True, timeout=10,
    )
    response = json.loads(result.stdout.splitlines()[-1])["result"]
    tool_result = json.loads(response["content"][0]["text"])
    event = json.loads((root / "events.jsonl").read_text().splitlines()[0])
    assert tool_result["fixture_event_id"] == event["event_id"]
    assert tool_result["ok"] is True


def test_first_plan_scorer_rejects_changed_identity_and_save_before_grocery():
    scorer = load_scorer()
    plan_id = "MP-2026-10-27-02"
    identity = {"identity_status": "proposed", "plan_id": plan_id, "native_resource": "not-yet-created"}
    result = {
        "protocol": "grocery-handoff/v1", "request_id": "SHOP-AE12-001",
        "recipe_ids": ["TEST-RECIPE-101"], "recipe_versions": {"TEST-RECIPE-101": "4"},
        "plan_identity": identity,
        "workbook_identity": {"provider": "synthetic-shopping-fixture", "spreadsheet_id": "SYNTHETIC-SHOPPING-AE12"},
        "capability": "full", "grocery_sections": [{"items": [{
            "ingredient": "canned chickpeas", "required_quantity": {"value": 400, "unit": "g"},
        }]}],
    }
    events = [
        {"sequence": 1, "event_id": "fixture-" + "b" * 32, "tool": "get_meal_plan_index",
         "arguments": {}, "result": {"ok": True, "plan_ids": []}},
        {"sequence": 2, "tool": "record_grocery_result", "arguments": {
            "plan_identity": identity, "request_id": result["request_id"],
            "recipe_versions": result["recipe_versions"], "workbook_identity": result["workbook_identity"],
                "returned_grocery_result": result,
        }, "result": {"ok": True}},
        {"sequence": 3, "tool": "save_meal_plan", "arguments": {"plan_id": plan_id, "content": {"grocery": result}}, "result": {"ok": True}, "attempted_write": True, "committed": True},
        {"sequence": 4, "tool": "read_meal_plan", "arguments": {"plan_id": plan_id}, "result": {"ok": True, "plan_id": plan_id, "content": {"grocery": result}}},
    ]
    control = {"expected": {
        "plan_id": plan_id, "plan_date": "2026-10-27", "request_id": result["request_id"],
        "recipe_versions": result["recipe_versions"], "workbook_identity": result["workbook_identity"],
        "required_ingredient": "canned chickpeas", "required_g": 400,
    }}
    state = {"meal_plans": {plan_id: {"plan_id": plan_id, "content": {"grocery": result}}}}
    public_context = {
        "protocol": "grocery-handoff/v1", "request_id": result["request_id"],
        "recipe_packet": {"safety_reviewed": True, "recipes": [{
            "recipe_id": "TEST-RECIPE-101", "approved_version": "4",
            "canonical_document": {"provider": "synthetic-fixture", "resource_id": "SYNTHETIC-RECIPE-101", "verified": True},
            "ingredient": "canned chickpeas", "required_g": 400, "yield_servings": 4,
            "planned_servings": 4, "leftovers": "none", "permitted_substitutions": [],
        }]}, "approval": "approved new synthetic plan; one final plan save authorized",
        "confirmed_pantry": {}, "region": "synthetic region", "currency": "USD",
        "shopping_date": "2026-10-27", "budget": "no stated limit",
        "preferred_stores": ["Synthetic Market"], "check_pantry": [], "required_constraints": [],
        "shopping_record_write_authorization": "none", "unresolved_questions": [],
    }
    packet = {
        "protocol": public_context["protocol"], "request_id": result["request_id"],
        "recipe_ids": result["recipe_ids"], "recipe_versions": result["recipe_versions"],
        "plan_identity": identity, "workbook_identity": result["workbook_identity"],
        **{key: value for key, value in public_context.items() if key not in {"protocol", "request_id"}},
    }
    packet_text = json.dumps(packet, separators=(",", ":"))
    child_message = json.dumps(result)
    installed = {}
    required_child_resources = [
        ("personal-shopper", "skills/personal-shopper/SKILL.md", "installed shopper skill\n"),
        ("personal-shopper", "skills/personal-shopper/references/contracts/handoff-contracts.md", "installed receiver contract\n"),
        ("personal-shopper", "skills/personal-shopper/references/contracts/record-management.md", "record identities\n"),
        ("personal-shopper", "skills/personal-shopper/references/grocery-workflow.md", "grocery workflow\n"),
        ("personal-shopper", "skills/personal-shopper/references/pricing-and-allocation.md", "price rules\n"),
        ("personal-shopper", "skills/personal-shopper/references/shopping-records.md", "shopping record roles\n"),
        ("personal-shopper", "skills/personal-shopper/references/store-preferences.md", "store preferences\n"),
    ]
    required_caller_resources = [
        ("meal-planner", "skills/meal-planner/SKILL.md", "installed planner skill\n"),
        ("meal-planner", "shared/handoff-contracts.md", "installed planner handoff contract\n"),
        ("meal-planner", "shared/record-management.md", "installed planner record management\n"),
        ("meal-planner", "shared/grocery-integration.md", "installed grocery contract\n"),
    ]

    def resource_call(thread_id, index, package, relative_path, body):
        digest = hashlib.sha256(body.encode()).hexdigest()
        installed[f"{package}/{relative_path}"] = digest
        payload = {"package": package, "relative_path": relative_path, "sha256": digest, "text": body}
        item = {"type": "McpToolCall", "thread_id": thread_id, "call_id": f"read-{thread_id}-{index}",
            "server": "shopping-skill-resources", "tool": "read_installed_skill_file",
            "arguments": {"package": package, "relative_path": relative_path}}
        started = {"type": "event_msg", "payload": {"type": "item_started", "thread_id": thread_id,
            "item": {**item, "status": "in_progress"}}}
        completed = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": thread_id,
            "item": {**item,
                "result": {"structuredContent": payload}, "status": "completed"}}}
        return started, completed

    parent_resource_calls = [event for index, resource in enumerate(required_caller_resources, 1)
                             for event in resource_call("root", index, *resource)]
    child_resource_calls = [event for index, resource in enumerate(required_child_resources, 1)
                            for event in resource_call("child", index, *resource)]
    fixture_event_id = "fixture-" + "a" * 32
    workbook_read_arguments = {"spreadsheet_id": result["workbook_identity"]["spreadsheet_id"]}
    workbook_read_result = {"ok": True, "spreadsheetId": result["workbook_identity"]["spreadsheet_id"],
                            "sheets": [{"properties": {"title": "Record Index"}}]}
    workbook_read_event = {"event_id": fixture_event_id, "sequence": 5,
        "tool": "get_spreadsheet_metadata", "arguments": workbook_read_arguments,
        "result": workbook_read_result}
    workbook_read_start = {"type": "event_msg", "payload": {"type": "item_started", "thread_id": "child",
        "item": {"type": "McpToolCall", "thread_id": "child", "call_id": "workbook-read-1",
            "server": "shopping-fixture", "tool": "get_spreadsheet_metadata",
            "arguments": workbook_read_arguments, "status": "in_progress"}}}
    workbook_read_call = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": "child",
        "item": {"type": "McpToolCall", "thread_id": "child", "call_id": "workbook-read-1",
            "server": "shopping-fixture", "tool": "get_spreadsheet_metadata",
            "arguments": workbook_read_arguments,
            "result": {"content": [{"type": "text", "text": json.dumps({**workbook_read_result,
                "fixture_event_id": fixture_event_id})}], "isError": False}, "status": "completed"}}}
    plan_index_call = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": "root",
        "item": {"type": "McpToolCall", "thread_id": "root", "call_id": "plan-index-1",
            "server": "shopping-fixture", "tool": "get_meal_plan_index", "arguments": {},
            "result": {"content": [{"type": "text", "text": json.dumps({
                "ok": True, "plan_ids": [], "fixture_event_id": events[0]["event_id"]})}],
                "isError": False}, "status": "completed"}}}
    child_calls = [*child_resource_calls, workbook_read_start, workbook_read_call]
    parent_message = {"type": "response_item", "payload": {"type": "message", "id": "packet-message",
        "role": "assistant", "content": [{"type": "output_text", "text": packet_text}]}}
    child_return = {"type": "response_item", "payload": {"type": "message", "id": "return-message",
        "role": "assistant", "phase": "final_answer", "status": "completed",
        "content": [{"type": "output_text", "text": child_message}]}}
    activity_start = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": "root",
        "item": {"type": "SubAgentActivity", "id": "activity-start", "kind": "started",
                 "agent_thread_id": "child"}}}
    activity_complete = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": "root",
        "item": {"type": "SubAgentActivity", "id": "activity-complete", "kind": "completed",
                 "agent_thread_id": "child"}}}
    activity_complete_again = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": "root",
        "item": {"type": "SubAgentActivity", "id": "activity-complete-again", "kind": "completed",
                 "agent_thread_id": "child"}}}
    activity_complete_final = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": "root",
        "item": {"type": "SubAgentActivity", "id": "activity-complete-final", "kind": "completed",
                 "agent_thread_id": "child"}}}
    parent_agent_return = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": "root",
        "item": {"type": "AgentMessage", "id": "return-message", "phase": "final_answer",
                 "content": [{"type": "Text", "text": child_message}]}}}
    parent_return = {"type": "response_item", "payload": {"type": "message", "id": "return-message",
        "role": "assistant", "phase": "final_answer", "status": "completed",
        "content": [{"type": "output_text", "text": child_message}]}}
    prior_child_answer = {"type": "response_item", "payload": {"type": "message", "id": "prior-return-message",
        "role": "assistant", "phase": "final_answer", "status": "completed",
        "content": [{"type": "output_text", "text": child_message}]}}
    record_rollout = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": "root",
        "item": {"type": "McpToolCall", "thread_id": "root", "call_id": "record-1",
            "server": "shopping-fixture", "tool": "record_grocery_result",
            "arguments": events[1]["arguments"], "result": {"ok": True}, "status": "completed"}}}
    record_started = {"type": "event_msg", "payload": {"type": "item_started", "thread_id": "root",
        "item": {"type": "McpToolCall", "thread_id": "root", "call_id": "record-1",
            "server": "shopping-fixture", "tool": "record_grocery_result",
            "arguments": events[1]["arguments"], "status": "in_progress"}}}
    rollouts = {"valid": True, "parent_thread_id": "root",
        "parent": [*parent_resource_calls, plan_index_call, parent_message, activity_start, activity_complete,
                   activity_complete_again, activity_complete_final,
                   parent_agent_return, parent_return, record_started, record_rollout],
        "children": {"child": [parent_message, *child_calls, prior_child_answer, child_return]}}
    activities = scorer.ae12_scoring._subagent_activities(rollouts["parent"])
    assert len(activities) == 1
    assert activities[0]["start_count"] == 1
    assert activities[0]["complete_count"] == 3
    assert activities[0]["completed"] == rollouts["parent"].index(activity_complete_final)
    host = [
        {"type": "item.completed", "item": {"id": "spawn", "type": "collab_tool_call", "tool": "spawn_agent",
         "sender_thread_id": "root", "receiver_thread_ids": ["child"], "prompt": packet_text,
         "agents_states": {}, "status": "completed"}},
        {"type": "item.completed", "item": {"id": "wait", "type": "collab_tool_call", "tool": "wait",
         "sender_thread_id": "root", "receiver_thread_ids": ["child"],
         "agents_states": {"child": {"status": "completed", "message": child_message}}, "status": "completed"}},
        {"type": "item.started", "item": {"id": "record", "type": "mcp_tool_call", "server": "shopping-fixture",
         "tool": "record_grocery_result", "arguments": events[1]["arguments"], "status": "in_progress"}},
        {"type": "item.completed", "item": {"id": "record", "type": "mcp_tool_call", "server": "shopping-fixture",
         "tool": "record_grocery_result", "arguments": events[1]["arguments"],
         "result": {"content": [{"type": "text", "text": "{\"ok\": true}"}]}, "status": "completed"}},
    ]
    delegation = {"host_events": host, "rollouts": rollouts, "public_context": public_context,
                  "installed": installed,
                  "required_caller_skill_resources": [f"{package}/{path}" for package, path, _ in required_caller_resources],
                  "required_child_skill_resources": [f"{package}/{path}" for package, path, _ in required_child_resources],
                  "required_child_fixture_read_tools": ["get_spreadsheet_metadata", "get_spreadsheet_range"],
                  "fixture_events": [*events, workbook_read_event]}

    def assert_valid_baseline():
        assert all(scorer._case_checks("B10-AE12-new-plan", state, events, control,
                                       delegation=delegation).values())

    assert_valid_baseline()
    interim_draft = {"type": "response_item", "payload": {"type": "message", "id": "draft-message",
        "role": "assistant", "phase": "commentary", "status": "completed",
        "content": [{"type": "output_text", "text": child_message}]}}
    refusal_text = "I could not complete the grocery handoff. Do not use the draft."
    child_refusal = {"type": "response_item", "payload": {"type": "message", "id": "refusal-message",
        "role": "assistant", "phase": "final_answer", "status": "completed",
        "content": [{"type": "output_text", "text": refusal_text}]}}
    parent_refusal_event = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": "root",
        "item": {"type": "AgentMessage", "id": "refusal-message", "phase": "final_answer",
                 "content": [{"type": "Text", "text": refusal_text}]}}}
    parent_refusal = {"type": "response_item", "payload": {"type": "message", "id": "refusal-message",
        "role": "assistant", "phase": "final_answer", "status": "completed",
        "content": [{"type": "output_text", "text": refusal_text}]}}
    assert_valid_baseline()
    refusal_rollouts = {**rollouts,
        "parent": [*parent_resource_calls, plan_index_call, parent_message, activity_start, activity_complete,
                   parent_refusal_event, parent_refusal, record_started, record_rollout],
        "children": {"child": [parent_message, *child_calls, interim_draft, child_return, child_refusal]}}
    refusal_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": refusal_rollouts},
    )
    assert not refusal_result["actual_shopper_return_recorded_before_plan_save"], (
        "an interim grocery JSON draft cannot replace the child's terminal refusal"
    )
    assert_valid_baseline()
    generic_echo_rollouts = {**rollouts, "children": {"child": [parent_message, child_return]}}
    generic_echo = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": generic_echo_rollouts},
    )
    assert not generic_echo["actual_shopper_return_recorded_before_plan_save"], (
        "an exact child JSON echo without child-owned installed-skill reads is not a shopper return"
    )
    parent_reads = []
    for call_event in child_resource_calls:
        call_copy = json.loads(json.dumps(call_event))
        call_copy["payload"]["thread_id"] = "root"
        call_copy["payload"]["item"]["thread_id"] = "root"
        parent_reads.append(call_copy)
    assert_valid_baseline()
    inherited_only = {**rollouts,
        "parent": [*parent_resource_calls, plan_index_call, parent_message, activity_start, activity_complete,
                   parent_agent_return, parent_return, record_started, record_rollout],
        "children": {"child": [parent_message, *parent_reads, workbook_read_start, workbook_read_call, child_return]},
    }
    parent_read_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": inherited_only},
    )
    assert not parent_read_result["actual_shopper_return_recorded_before_plan_save"], (
        "the parent's installed-skill reads cannot establish child activation"
    )

    assert_valid_baseline()
    reversed_child_read = {**rollouts,
        "children": {"child": [parent_message, *child_resource_calls, workbook_read_call,
                               workbook_read_start, child_return]},
    }
    reversed_child_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": reversed_child_read},
    )
    assert not reversed_child_result["actual_shopper_return_recorded_before_plan_save"], (
        "a child workbook completion before its explicit start is not a valid read"
    )

    assert_valid_baseline()
    reversed_parent_record = {**rollouts,
        "parent": [*parent_resource_calls, plan_index_call, parent_message, activity_start,
                   activity_complete, activity_complete_again, activity_complete_final,
                   parent_agent_return, parent_return, record_rollout, record_started],
    }
    reversed_parent_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": reversed_parent_record},
    )
    assert not reversed_parent_result["actual_shopper_return_recorded_before_plan_save"], (
        "a parent result-record completion before its explicit start is not valid"
    )

    missing_parent_reads = {**rollouts,
        "parent": [plan_index_call, parent_message, activity_start, activity_complete,
                   parent_agent_return, parent_return, record_started, record_rollout]}
    missing_parent_reads_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": missing_parent_reads},
    )
    assert not missing_parent_reads_result["actual_shopper_return_recorded_before_plan_save"], (
        "the caller must read its installed handoff instructions before packet construction"
    )
    wrong_workbook_call = json.loads(json.dumps(workbook_read_call))
    wrong_workbook_call["payload"]["item"]["arguments"]["spreadsheet_id"] = "SYNTHETIC-OTHER"
    wrong_workbook_rollouts = {**rollouts, "children": {"child": [parent_message, *child_resource_calls,
        workbook_read_start, wrong_workbook_call, child_return]}}
    wrong_workbook_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": wrong_workbook_rollouts},
    )
    assert not wrong_workbook_result["actual_shopper_return_recorded_before_plan_save"]
    child_save_call = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": "child",
        "item": {"type": "McpToolCall", "thread_id": "child", "call_id": "child-save",
            "server": "shopping-fixture", "tool": "save_meal_plan",
            "arguments": {"plan_id": plan_id, "content": {}}, "status": "completed"}}}
    child_save_rollouts = {**rollouts, "children": {"child": [parent_message, *child_calls,
        child_save_call, child_return]}}
    child_save_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": child_save_rollouts},
    )
    assert not child_save_result["actual_shopper_return_recorded_before_plan_save"], (
        "only the parent may save the approved meal plan"
    )
    wrong_thread_event = json.loads(json.dumps(child_calls[0]))
    wrong_thread_event["payload"]["item"]["call_id"] = "unrelated-read"
    wrong_thread_event["payload"]["thread_id"] = "unrelated-thread"
    wrong_thread_event["payload"]["item"]["thread_id"] = "unrelated-thread"
    wrong_thread_rollouts = {**rollouts, "children": {"child": [parent_message,
        *child_calls, wrong_thread_event, child_return]}}
    wrong_thread_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": wrong_thread_rollouts},
    )
    assert not wrong_thread_result["actual_shopper_return_recorded_before_plan_save"]
    early_workbook_start = {"type": "event_msg", "payload": {"type": "item_started", "thread_id": "child",
        "item": {"type": "McpToolCall", "thread_id": "child", "call_id": "workbook-read-1",
            "server": "shopping-fixture", "tool": "get_spreadsheet_metadata",
            "arguments": workbook_read_arguments, "status": "in_progress"}}}
    early_workbook_rollouts = {**rollouts, "children": {"child": [parent_message,
        early_workbook_start, *child_resource_calls, workbook_read_call, child_return]}}
    early_workbook_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": early_workbook_rollouts},
    )
    assert not early_workbook_result["actual_shopper_return_recorded_before_plan_save"], (
        "a workbook request that starts before installed contracts are read must be rejected"
    )
    completion_only_workbook_rollouts = {**rollouts, "children": {"child": [parent_message,
        *child_resource_calls, workbook_read_call, prior_child_answer, child_return]}}
    completion_only_workbook_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": completion_only_workbook_rollouts},
    )
    assert not completion_only_workbook_result["actual_shopper_return_recorded_before_plan_save"], (
        "completion-only workbook evidence cannot establish that reads finished before the request started"
    )
    early_record_rollouts = {**rollouts,
        "parent": [*parent_resource_calls, plan_index_call, parent_message, activity_start,
                   activity_complete, activity_complete_again, activity_complete_final,
                   record_started, parent_agent_return, parent_return, record_rollout]}
    early_record_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": early_record_rollouts},
    )
    assert not early_record_result["actual_shopper_return_recorded_before_plan_save"], (
        "the parent result-record request must start after the completed child return"
    )
    delayed_lookup_rollouts = {**rollouts,
        "parent": [*parent_resource_calls, parent_message, activity_start, activity_complete,
                   activity_complete_again, activity_complete_final, parent_agent_return,
                   parent_return, plan_index_call, record_started, record_rollout]}
    delayed_lookup_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": delayed_lookup_rollouts},
    )
    assert not delayed_lookup_result["actual_shopper_return_recorded_before_plan_save"], (
        "the proposed identity must be collision-checked before the packet is handed off"
    )
    changed_inherited = {**parent_message, "payload": {**parent_message["payload"],
        "content": [{"type": "output_text", "text": packet_text + " "}]}}
    changed_inherited_rollouts = {**rollouts, "children": {"child": [changed_inherited,
        *child_calls, child_return]}}
    inherited_result = scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": changed_inherited_rollouts},
    )
    assert not inherited_result["actual_shopper_return_recorded_before_plan_save"]
    assert not all(scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": {"valid": False}},
    ).values())
    reordered = [events[0], events[2], events[1], events[3]]
    for sequence, event in enumerate(reordered, 1):
        reordered[sequence - 1] = {**event, "sequence": sequence}
    assert not all(scorer._case_checks("B10-AE12-new-plan", state, reordered, control,
                                       delegation=delegation).values())
    altered = [*events[:1], {**events[1], "arguments": {"plan_identity": {**identity, "plan_id": "MP-2026-10-27-99"}}}, *events[2:]]
    assert not all(scorer._case_checks("B10-AE12-new-plan", state, altered, control,
                                       delegation=delegation).values())
    collision = [{**events[0], "result": {"ok": True, "plan_ids": [plan_id]}}, *events[1:]]
    assert not all(scorer._case_checks("B10-AE12-new-plan", state, collision, control,
                                       delegation=delegation).values())
    missing_readback = events[:-1]
    assert not all(scorer._case_checks("B10-AE12-new-plan", state, missing_readback, control,
                                       delegation=delegation).values())
    changed_children = {"child": [*rollouts["children"]["child"][:-1], {
        **child_return, "payload": {**child_return["payload"], "content": [{"type": "output_text",
            "text": json.dumps({**result, "plan_identity": {**identity, "plan_id": "MP-2026-10-27-99"}})}]}
    }]}
    changed_rollouts = {**rollouts, "children": changed_children}
    assert not all(scorer._case_checks(
        "B10-AE12-new-plan", state, events, control,
        delegation={**delegation, "rollouts": changed_rollouts},
    ).values())
    assert all(scorer._case_checks("B10-AE12-existing-plan", {}, [], control).values())
    assert not all(scorer._case_checks("B10-AE12-existing-plan", {}, [events[1]], control).values())


def test_rollout_calls_keep_separate_start_and_completion_indexes_across_duplicate_completions():
    scorer = load_scorer()
    started = {"type": "event_msg", "payload": {"type": "item_started", "thread_id": "child",
        "item": {"type": "McpToolCall", "thread_id": "child", "call_id": "read-1",
            "server": "shopping-skill-resources", "tool": "read_installed_skill_file",
            "arguments": {"package": "meal-planner", "relative_path": "shared/grocery-integration.md"},
            "status": "in_progress"}}}
    completed = {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": "child",
        "item": {"type": "McpToolCall", "thread_id": "child", "call_id": "read-1",
            "server": "shopping-skill-resources", "tool": "read_installed_skill_file",
            "arguments": {"package": "meal-planner", "relative_path": "shared/grocery-integration.md"},
            "result": {"text": "same result"}, "status": "completed"}}}

    call, = scorer.ae12_scoring._rollout_tool_calls([started, completed, completed], "child")

    assert call["start_index"] == 0
    assert call["completion_index"] == call["event_index"] == 1
    assert call["status"] == "completed"
    completion_only, = scorer.ae12_scoring._rollout_tool_calls([completed], "child")
    assert completion_only["start_index"] is None
    assert completion_only["completion_index"] == 0


def test_trial_scorer_reconciles_parent_and_child_fixture_event_ids():
    scorer = load_scorer()
    parent_id, child_id = "fixture-" + "1" * 32, "fixture-" + "2" * 32
    parent_args = {"plan_id": "MP-2026-10-27-02", "content": {}}
    child_args = {"spreadsheet_id": "SYNTHETIC-SHOPPING-AE12"}
    events = [
        {"event_id": parent_id, "tool": "save_meal_plan", "arguments": parent_args,
         "result": {"ok": True, "plan_id": parent_args["plan_id"]}},
        {"event_id": child_id, "tool": "get_spreadsheet_metadata", "arguments": child_args,
         "result": {"ok": True, "spreadsheetId": child_args["spreadsheet_id"]}},
    ]

    def observed_call(tool, arguments, event_id):
        result = next(event["result"] for event in events if event["event_id"] == event_id)
        result_text = json.dumps({**result, "fixture_event_id": event_id})
        return {"server": "shopping-fixture", "tool": tool, "status": "completed",
                "call_id": f"call-{event_id}", "arguments": arguments,
                "result": {"content": [{"type": "text", "text": result_text}], "isError": False}}

    parent_call = observed_call("save_meal_plan", parent_args, parent_id)
    child_call = observed_call("get_spreadsheet_metadata", child_args, child_id)
    assert scorer.ae12_scoring._fixture_calls_reconcile([parent_call], [child_call], events)
    assert not scorer.ae12_scoring._fixture_calls_reconcile([parent_call], [], events)
    assert not scorer.ae12_scoring._fixture_calls_reconcile([parent_call], [child_call, child_call], events)
    duplicated = observed_call("get_spreadsheet_metadata", child_args, parent_id)
    assert not scorer.ae12_scoring._fixture_calls_reconcile([parent_call], [duplicated], events)
    changed_args = observed_call("get_spreadsheet_metadata", {**child_args, "spreadsheet_id": "OTHER"}, child_id)
    assert not scorer.ae12_scoring._fixture_calls_reconcile([parent_call], [changed_args], events)
    altered_result = {**child_call, "result": {"content": [{"type": "text", "text": json.dumps({
        "ok": True, "spreadsheetId": "OTHER", "fixture_event_id": child_id,
    })}], "isError": False}}
    assert not scorer.ae12_scoring._fixture_calls_reconcile([parent_call], [altered_result], events)


def test_trial_scorer_requires_multi_agent_only_inside_restricted_runtime():
    capture = load_runner().capture
    scorer = load_scorer()
    safe = {
        "command": capture.build_codex_command(
            "/tmp/delegated", multi_agent_enabled=True, apps_enabled=False, persist_rollouts=True
        ),
        "multi_agent_enabled": True,
        "persist_rollouts": True,
        "sandbox": "read-only",
        "provider_apps": [],
    }
    assert scorer.ae12_scoring._multi_agent_runtime_matches(safe, True)
    assert not scorer.ae12_scoring._multi_agent_runtime_matches(safe, False)
    escaped = {**safe, "command": [*safe["command"][:-1], "--enable", "apps", "-"]}
    assert not scorer.ae12_scoring._multi_agent_runtime_matches(escaped, True)


def test_delegation_runtime_reconciles_exact_mcp_surface_and_persisted_config(tmp_path):
    scorer = load_scorer()
    capture = load_runner().capture
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    subcase = next(item for item in manifest["synthetic_subcases"]
                   if item["id"] == "B10-AE12-new-plan")
    directory = tmp_path / "trial"
    directory.mkdir(mode=0o700)
    workspace_config = (
        "[features]\nmulti_agent = true\nshell_tool = false\nunified_exec = false\n"
        "apps = false\nbrowser_use = false\ncomputer_use = false\nplugins = true\n\n"
        "[apps._default]\nenabled = false\ndefault_tools_enabled = false\n"
    ).encode()
    (directory / "runtime-config.toml").write_bytes(workspace_config)
    resources = {"packages": {}}
    for index, qualified in enumerate(subcase["required_skill_resources"], 1):
        package, relative = qualified.split("/", 1)
        package_files = resources["packages"].setdefault(package, {
            "installed_root": f"/tmp/{package}", "files": {},
        })["files"]
        package_files[relative] = f"{index:064x}"
    resources_raw = json.dumps(resources).encode() + b"\n"
    (directory / "skill-resource-config.json").write_bytes(resources_raw)
    home_config = (
        'approval_policy = "never"\nsandbox_mode = "read-only"\n\n'
        '[mcp_servers."shopping-fixture"]\n'
        f'command = {json.dumps(sys.executable)}\n'
        f'args = {json.dumps([str(EVAL / "store.py"), "serve", str(directory / "fixture-store")])}\n\n'
        '[mcp_servers."shopping-skill-resources"]\n'
        f'command = {json.dumps(sys.executable)}\n'
        f'args = {json.dumps([str(EVAL / "skill_resources.py"), str(directory / "skill-resource-config.json")])}\n'
    ).encode()
    (directory / "isolated-codex-home-config.toml").write_bytes(home_config)
    for name in ("runtime-config.toml", "skill-resource-config.json", "isolated-codex-home-config.toml"):
        (directory / name).chmod(0o600)
    settings = {
        "command": capture.build_codex_command(
            "/tmp/delegated", multi_agent_enabled=True, persist_rollouts=True, apps_enabled=False,
        ),
        "multi_agent_enabled": True, "persist_rollouts": True, "sandbox": "read-only",
        "provider_apps": [], "external_packages": {}, "runtime_config_sha256": hashlib.sha256(workspace_config).hexdigest(),
        "isolated_codex_home_config_sha256": hashlib.sha256(home_config).hexdigest(),
        "fixture": {"allowed_tools": subcase["tools"], "permitted_operations": subcase["permitted_operations"]},
        "skill_resource_reader": {
            "server": "shopping-skill-resources", "tool": "read_installed_skill_file",
            "packages": {name: value["files"] for name, value in resources["packages"].items()},
            "config_sha256": hashlib.sha256(resources_raw).hexdigest(),
        },
    }
    result = {"isolated_codex_home_config_sha256": hashlib.sha256(home_config).hexdigest()}

    assert scorer.ae12_scoring._delegation_runtime_matches(directory, result, settings, subcase)
    expanded_home = home_config + b'\n[mcp_servers."unexpected-provider"]\ncommand = "provider"\nargs = []\n'
    (directory / "isolated-codex-home-config.toml").write_bytes(expanded_home)
    new_hash = hashlib.sha256(expanded_home).hexdigest()
    result["isolated_codex_home_config_sha256"] = new_hash
    settings["isolated_codex_home_config_sha256"] = new_hash
    assert not scorer.ae12_scoring._delegation_runtime_matches(directory, result, settings, subcase)


def test_first_plan_resource_evidence_requires_matching_installed_bytes():
    scorer = load_scorer()
    body = "installed contract\n"
    digest = hashlib.sha256(body.encode()).hexdigest()
    call = {"server": "shopping-skill-resources", "tool": "read_installed_skill_file", "status": "completed",
            "arguments": {"package": "meal-planner", "relative_path": "shared/grocery-integration.md"},
            "result": {"content": [{"type": "text", "text": json.dumps({"package": "meal-planner", "relative_path": "shared/grocery-integration.md", "sha256": digest, "text": body})}]}}
    installed = {"meal-planner/shared/grocery-integration.md": digest}
    assert scorer.ae12_scoring._valid_installed_resource(call, installed)
    assert not scorer.ae12_scoring._valid_installed_resource({**call, "status": "failed"}, installed)
    assert not scorer.ae12_scoring._valid_installed_resource(call, {**installed, "meal-planner/shared/grocery-integration.md": "0" * 64})
    assert not scorer.ae12_scoring._valid_installed_resource({**call, "arguments": {"package": "meal-planner", "relative_path": "../secret.md"}}, installed)
