from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "shopping"
REPO_ROOT = ROOT.parents[1]


def load_checker():
    if str(EVAL) not in sys.path:
        sys.path.insert(0, str(EVAL))
    spec = importlib.util.spec_from_file_location("personal_shopper_trial_checker", EVAL / "check_trial.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_capture():
    spec = importlib.util.spec_from_file_location(
        "personal_shopper_capture_for_digest_contract", EVAL / "capture_invocation.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def control_receipt(checker, *, now=None):
    now = now or datetime.now(timezone.utc)
    key = "synthetic-control-key-not-a-live-secret-0001"
    locator = "synthetic runtime locator"
    run_id = "synthetic-control-run-001"
    resource_id = "SYNTHETIC-GROCERY-001"
    session_id = "synthetic-host-session-001"
    timestamp = now.isoformat()
    locator_hash = hashlib.sha256(locator.encode()).hexdigest()

    def canonical_hash(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False).encode()).hexdigest()

    routing_values = [["Role", "Tab", "Record ID"], ["grocery-authority", "Groceries", "g-1"]]
    grocery_values = [["Ingredient", "Record ID", "Price"], ["Rice", "r-1", 2.5], ["Beans", "r-2", 1.5]]
    digest = canonical_hash(grocery_values)

    def event(seq, operation, **kwargs):
        return {
            "seq": seq,
            "event_id": f"control-event-{seq}",
            "tool_call_id": f"control-call-{seq}",
            "session_id": session_id,
            "run_id": run_id,
            "timestamp": timestamp,
            "operation": operation,
            "provider": "google-sheets",
            "native_id": resource_id,
            "source": "connected_google_sheets_tool",
            **kwargs,
        }

    native_sheets = [
        {"sheet_id": "1", "names": ["Routing"]},
        {"sheet_id": "2", "names": ["Groceries"]},
    ]
    call_details = [
        ("get_spreadsheet_metadata", {"spreadsheet_url": locator},
         {"spreadsheetId": resource_id, "sheets": [
             {"properties": {"sheetId": 1, "title": "Routing"}},
             {"properties": {"sheetId": 2, "title": "Groceries"}},
         ]}),
        ("get_spreadsheet_range", {"spreadsheet_id": resource_id, "range": "Routing!A1:C2"},
         {"values": routing_values}),
        ("get_spreadsheet_range", {"spreadsheet_id": resource_id, "range": "Groceries!A1:C3"},
         {"values": grocery_values}),
        ("get_spreadsheet_range", {"spreadsheet_id": resource_id, "range": "Groceries!A1:C3"},
         {"values": grocery_values}),
    ]

    operations = [
        event(1, "resolve", resolved=True, requested_locator_sha256=locator_hash),
        event(2, "metadata", native_sheets=native_sheets),
        event(3, "read_values", purpose="routing", sheet_id="1", bounded=True,
              cell_count=6, row_count=1, headers=["Role", "Tab", "Record ID"],
              header_map={"record_role": 0, "tab_name": 1, "record_key": 2},
              content_sha256=canonical_hash(routing_values), range_sha256=hashlib.sha256(b"Routing!A1:C2").hexdigest(),
              resolved_target_sheet_id="2"),
        event(4, "read_values", purpose="grocery_context", sheet_id="2", bounded=True,
              cell_count=9, row_count=2, headers=["Ingredient", "Record ID", "Price"],
              header_map={"ingredient": 0, "record_key": 1, "price": 2},
              content_sha256=digest, range_sha256=hashlib.sha256(b"Groceries!A1:C3").hexdigest()),
        event(5, "read_values", purpose="post_read_state_check", source_event_id="control-event-4",
              sheet_id="2", bounded=True, cell_count=9, row_count=2,
              headers=["Ingredient", "Record ID", "Price"], content_sha256=digest,
              range_sha256=hashlib.sha256(b"Groceries!A1:C3").hexdigest()),
    ]
    operation_call_indexes = [0, 0, 1, 2, 3]
    operations[1]["tool_call_id"] = operations[0]["tool_call_id"]
    for operation, call_index in zip(operations, operation_call_indexes):
        tool, arguments, result = call_details[call_index]
        operation["tool_call_id"] = f"control-call-{call_index + 1}"
        operation["trace_event_indexes"] = [call_index * 2 + 2, call_index * 2 + 3]
        operation["request_sha256"] = canonical_hash(arguments)
        operation["result_sha256"] = canonical_hash(result)

    receipt = {
        "schema_version": 1,
        "receipt_schema": "personal-shopper-live-receipt/v2",
        "evidence_kind": "deterministic-control",
        "run_id": run_id,
        "tool_trace_sha256": "0" * 64,
        "tool_trace_event_count": 11,
        "tool_trace_call_count": 4,
        "candidate_sha256": checker.candidate_digest(REPO_ROOT),
        "suite_sha256": checker.suite_digest(REPO_ROOT),
        "requested_locator_sha256": hashlib.sha256(locator.encode()).hexdigest(),
        "resource": {"provider": "google-sheets", "native_id": resource_id},
        "activation": {
            "skill_id": "personal-shopper:personal-shopper",
            "activated": True,
            "session_id": session_id,
            "run_id": run_id,
            "candidate_sha256": checker.candidate_digest(REPO_ROOT),
            "started_at": timestamp,
            "completed_at": timestamp,
        },
        "runtime": {
            "credentials_available": True,
            "connected_google_sheets_tool_available": True,
            "read_only_envelope": True,
            "host_receipt_source": "actual_host_tool_trace",
        },
        "operations": operations,
        "route_resolution": {
            "native_role": "grocery-authority",
            "basis": "record_index",
            "source_event_id": "control-event-3",
            "routing_sheet_id": "1",
            "sheet_id": "2",
        },
        "post_read_state_check": {
            "source_event_id": "control-event-4",
            "check_event_id": "control-event-5",
            "before_sha256": digest,
            "after_sha256": digest,
            "write_count": 0,
            "unchanged": True,
        },
    }
    raw_events = [{"type": "thread.started", "thread_id": session_id}, {"type": "turn.started", "turn_id": "turn-1"}]
    for index, (tool, arguments, result) in enumerate(call_details):
        base = {"id": f"control-call-{index + 1}", "type": "mcp_tool_call", "server": "google-drive",
                "tool": tool, "arguments": arguments}
        raw_events.append({"type": "item.started", "item": {**base, "status": "in_progress"}})
        raw_events.append({"type": "item.completed", "item": {**base, "result": result, "status": "completed"}})
    raw_events.append({"type": "turn.completed", "turn_id": "turn-1"})
    raw = b"".join(json.dumps(item, separators=(",", ":")).encode() + b"\n" for item in raw_events)
    capture_dir = Path(tempfile.mkdtemp(prefix="shopping-control-"))
    os.chmod(capture_dir, 0o700)
    trace_path = capture_dir / "host-events.jsonl"
    trace_path.write_bytes(raw)
    os.chmod(trace_path, 0o600)
    receipt["tool_trace_sha256"] = hashlib.sha256(raw).hexdigest()
    receipt["attestation"] = {"algorithm": "hmac-sha256", "digest": checker.sign_receipt(receipt, key)}
    config = {
        "schema_version": 1,
        "expected_resource": {"provider": "google-sheets", "native_id": resource_id},
    }
    return receipt, config, {"locator": locator, "run_id": run_id, "key": key, "now": now,
                             "host_capture": capture_dir}


def reseal(checker, receipt, key):
    receipt["attestation"] = {"algorithm": "hmac-sha256", "digest": checker.sign_receipt(receipt, key)}


def validate(checker, receipt, config, private, *, now=None):
    return checker.validate_receipt(
        receipt,
        config,
        locator=private["locator"],
        run_id=private["run_id"],
        key=private["key"],
        now=now or private["now"],
        repo_root=REPO_ROOT,
        host_capture_path=private["host_capture"],
    )


def test_checker_cli_passes_private_host_capture_to_receipt_validation(monkeypatch, tmp_path, capsys):
    checker = load_checker()
    capture_path = tmp_path / "host-events.jsonl"
    capture_path.write_text("private trace path is not emitted\n", encoding="utf-8")
    seen = {}

    monkeypatch.setattr(checker, "load_private_inputs", lambda config, receipt: ({}, {}, []))

    def validate_receipt(receipt, config, **kwargs):
        seen.update(kwargs)
        return {"status": "accepted", "accepted": True, "issues": []}

    monkeypatch.setattr(checker, "validate_receipt", validate_receipt)
    result = checker.main([
        "--config", str(tmp_path / "private-config.json"),
        "--receipt", str(tmp_path / "receipt.json"),
        "--shopping-host-capture", str(capture_path),
    ])

    assert result == 0
    assert seen["host_capture_path"] == str(capture_path)
    assert capsys.readouterr().out == '{"accepted": true, "issues": [], "status": "accepted"}\n'


def test_manifest_and_fixture_matrix_include_all_acceptance_examples():
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    fixtures = json.loads((EVAL / "fixtures.json").read_text(encoding="utf-8"))
    fixture_cases = {case["id"]: case for case in fixtures["cases"]}

    assert [case["id"] for case in manifest["acceptance_cases"]] == [f"AE{i}" for i in range(1, 19)]
    assert all(case.get("fixture_id", case["id"]) in fixture_cases for case in manifest["acceptance_cases"])
    groups = {group["id"]: group for group in manifest["behavior_groups"]}
    assert set(groups) == {f"B{i}" for i in range(1, 19)}
    assert all(case_id in fixture_cases for group in groups.values() for case_id in group["case_ids"])
    assert groups["B11"]["evidence"] == "live-host-activation"
    assert manifest["evidence_policy"]["fixture_evidence_proves_live_access"] is False
    assert fixture_cases["AE11"]["context"]["fixture_tool_trace"] is None
    assert fixture_cases["AE11"]["expected"]["missing_live_evidence_status"] == "blocked or not-run"


def test_b7_has_activated_coverage_for_role_mapped_legacy_workbooks():
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    fixtures = json.loads((EVAL / "fixtures.json").read_text(encoding="utf-8"))
    fixture_cases = {case["id"]: case for case in fixtures["cases"]}
    subcases = {case["id"]: case for case in manifest["synthetic_subcases"]}

    subcase = subcases["B7-role-mapped-legacy-workbook"]
    fixture = fixture_cases["U7-B7-role-mapped-legacy-workbook"]
    assert subcase["group"] == "B7"
    assert {"get_spreadsheet_metadata", "get_spreadsheet_range"} <= set(subcase["tools"])
    assert "U7-B7-role-mapped-legacy-workbook" in next(
        group["case_ids"] for group in manifest["behavior_groups"] if group["id"] == "B7"
    )
    assert {sheet["title"] for sheet in fixture["workbook"]["sheets"]} == {
        "Price History", "Shopper Preferences", "Change History"
    }
    preferences = next(
        sheet for sheet in fixture["workbook"]["sheets"] if sheet["title"] == "Shopper Preferences"
    )
    assert preferences["headers"][-1] == "Record ID"
    assert "Record Index" not in {sheet["title"] for sheet in fixture["workbook"]["sheets"]}


def test_manifest_binds_separate_nonempty_suite_identity():
    checker = load_checker()
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["suite_identity_files"]


def test_multi_agent_profile_is_limited_to_the_new_plan_handoff_case():
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    profiles = manifest["candidate"]["profiles"]
    subcases = {item["id"]: item for item in manifest["synthetic_subcases"]}

    assert profiles["full-handoff"].get("multi_agent", False) is False
    assert profiles["full-handoff-delegating"]["multi_agent"] is True
    assert profiles["full-handoff-delegating"]["persist_rollouts"] is True
    assert subcases["B10-AE12-new-plan"]["profile"] == "full-handoff-delegating"
    assert subcases["B10-AE12-existing-plan"]["profile"] == "full-handoff"
    new_plan = subcases["B10-AE12-new-plan"]
    assert set(new_plan["required_caller_skill_resources"]) == {
        "meal-planner/skills/meal-planner/SKILL.md",
        "meal-planner/shared/handoff-contracts.md",
        "meal-planner/shared/record-management.md",
        "meal-planner/shared/grocery-integration.md",
    }
    assert set(new_plan["required_child_skill_resources"]) == {
        "personal-shopper/skills/personal-shopper/SKILL.md",
        "personal-shopper/skills/personal-shopper/references/contracts/handoff-contracts.md",
        "personal-shopper/skills/personal-shopper/references/contracts/record-management.md",
        "personal-shopper/skills/personal-shopper/references/grocery-workflow.md",
        "personal-shopper/skills/personal-shopper/references/pricing-and-allocation.md",
        "personal-shopper/skills/personal-shopper/references/shopping-records.md",
        "personal-shopper/skills/personal-shopper/references/store-preferences.md",
    }
    assert set(new_plan["required_caller_skill_resources"]) | set(new_plan["required_child_skill_resources"]) \
        == set(new_plan["required_skill_resources"])
    assert set(new_plan["required_child_fixture_read_tools"]) == {
        "get_spreadsheet_metadata", "get_spreadsheet_range",
    }
    assert set(new_plan["required_child_fixture_read_tools"]) <= set(new_plan["tools"])
    assert "save_meal_plan" not in new_plan["required_child_fixture_read_tools"]


def test_runner_and_checker_share_candidate_and_suite_digest_contract():
    checker = load_checker()
    capture = load_capture()
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))

    assert capture.identity_digest(
        REPO_ROOT, capture.candidate_identity_patterns(manifest)
    ) == checker.candidate_digest(REPO_ROOT)
    assert capture.identity_digest(REPO_ROOT, manifest["suite_identity_files"]) \
        == checker.suite_digest(REPO_ROOT)


def test_runtime_locator_resolves_only_google_sheet_urls_or_native_ids():
    checker = load_checker()

    locator = "https://docs.google.com" + "/spreadsheets/d/" \
        + "Abc_def-12345678901234567890" + "/edit?gid=7"
    assert checker._google_sheet_id(locator) == "Abc_def-12345678901234567890"
    assert checker._google_sheet_id("Abc_def-12345678901234567890") == "Abc_def-12345678901234567890"
    assert checker._google_sheet_id(
        "https://example.com/spreadsheets/d/Abc_def-12345678901234567890/edit"
    ) is None
    assert re.fullmatch(r"[0-9a-f]{64}", checker.suite_digest(REPO_ROOT))


def test_private_locator_and_expected_identity_are_absent_from_tracked_contracts():
    tracked_inputs = [
        path for path in ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".py"}
    ]
    spreadsheet_url = re.compile(r"https?://docs\.google\.com/spreadsheets/d/[^\s/#?]+", re.I)
    hardcoded_resource_id = re.compile(
        r"(?i)(?:native_id|resource_id|spreadsheet_id|file_id)\s*[\"']?\s*:\s*"
        r"[\"'][A-Za-z0-9_-]{40,}[\"']"
    )
    for path in tracked_inputs:
        content = path.read_text(encoding="utf-8")
        assert spreadsheet_url.search(content) is None
        assert hardcoded_resource_id.search(content) is None

    cases = json.loads((EVAL / "fixtures.json").read_text(encoding="utf-8"))["cases"]
    live_case = next(case for case in cases if case["id"] == "AE11")
    assert "private runtime" in live_case["context"]["expected_resource_identity"]
    assert live_case["context"]["runtime_locator"].startswith("private runtime")


def test_positive_control_validates_receipt_shape_but_never_accepts_r25():
    checker = load_checker()
    receipt, config, private = control_receipt(checker)

    result = validate(checker, receipt, config, private, now=datetime.now(timezone.utc))

    assert result == {"status": "control-only", "accepted": False, "issues": []}


def test_wrong_expected_resource_is_rejected_without_echoing_private_identity():
    checker = load_checker()
    receipt, config, private = control_receipt(checker)
    receipt["resource"]["native_id"] = "SYNTHETIC-OTHER-IDENTITY"
    reseal(checker, receipt, private["key"])
    result = validate(checker, receipt, config, private)

    assert "wrong_canonical_resource" in result["issues"]
    assert "SYNTHETIC-OTHER-IDENTITY" not in json.dumps(result)


def test_host_capture_rejects_conflicting_resource_ids_in_one_provider_call():
    checker = load_checker()
    receipt, config, private = control_receipt(checker)
    trace_path = private["host_capture"] / "host-events.jsonl"
    events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    for event in events:
        item = event.get("item", {})
        if item.get("id") == "control-call-3":
            item["arguments"]["spreadsheet_id"] = "SYNTHETIC-OTHER-IDENTITY"
    raw = b"".join(json.dumps(event, separators=(",", ":")).encode() + b"\n" for event in events)
    trace_path.write_bytes(raw)
    receipt["tool_trace_sha256"] = hashlib.sha256(raw).hexdigest()
    call_args = next(
        event["item"]["arguments"] for event in events
        if event.get("item", {}).get("id") == "control-call-3"
    )
    operation = next(item for item in receipt["operations"] if item["tool_call_id"] == "control-call-3")
    operation["request_sha256"] = hashlib.sha256(
        json.dumps(call_args, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    reseal(checker, receipt, private["key"])

    result = validate(checker, receipt, config, private)

    assert result["accepted"] is False
    assert "host_tool_call_wrong_resource" in result["issues"]
    assert "SYNTHETIC-OTHER-IDENTITY" not in json.dumps(result)


def test_metadata_only_receipt_does_not_satisfy_content_read():
    checker = load_checker()
    receipt, config, private = control_receipt(checker)
    receipt["operations"] = receipt["operations"][:2]
    reseal(checker, receipt, private["key"])

    result = validate(checker, receipt, config, private)

    assert result["accepted"] is False
    assert "bounded_grocery_content_missing" in result["issues"]
    assert "read_only_final_state_mismatch" in result["issues"]


def test_native_receipt_requires_ordered_resolution_reads_and_post_read_check():
    checker = load_checker()
    receipt, config, private = control_receipt(checker)
    route_read, grocery_read = receipt["operations"][2:4]
    grocery_read["seq"] = 3
    route_read["seq"] = 4
    receipt["operations"][2:4] = [grocery_read, route_read]
    reseal(checker, receipt, private["key"])

    result = validate(checker, receipt, config, private)

    assert result["accepted"] is False
    assert "native_operation_order_invalid" in result["issues"]


def test_any_write_attempt_fails_even_when_provider_would_reject_it():
    checker = load_checker()
    receipt, config, private = control_receipt(checker)
    write = dict(receipt["operations"][-1], seq=6, event_id="control-event-6",
                 tool_call_id="control-call-6", operation="write", result="rejected")
    receipt["operations"].append(write)
    receipt["tool_trace_event_count"] = 6
    reseal(checker, receipt, private["key"])

    result = validate(checker, receipt, config, private)

    assert result["accepted"] is False
    assert "forbidden_or_unrecognized_tool_operation" in result["issues"]


def test_stale_run_candidate_and_locator_are_rejected():
    checker = load_checker()
    receipt, config, private = control_receipt(checker)
    receipt["run_id"] = "previous-run"
    receipt["candidate_sha256"] = "0" * 64
    receipt["requested_locator_sha256"] = "1" * 64
    reseal(checker, receipt, private["key"])

    result = validate(checker, receipt, config, private)

    assert {"wrong_or_stale_run", "stale_or_wrong_candidate", "runtime_locator_mismatch"} <= set(result["issues"])


def test_stale_activation_and_bad_attestation_are_rejected():
    checker = load_checker()
    now = datetime.now(timezone.utc)
    receipt, config, private = control_receipt(checker, now=now - timedelta(minutes=20))
    reseal(checker, receipt, private["key"])
    result = validate(checker, receipt, config, private, now=now)
    assert "stale_activation_receipt" in result["issues"]

    receipt, config, private = control_receipt(checker)
    receipt["suite_sha256"] = "0" * 64
    reseal(checker, receipt, private["key"])
    result = validate(checker, receipt, config, private)
    assert "stale_or_wrong_suite" in result["issues"]

    receipt["attestation"]["digest"] = "0" * 64
    result = validate(checker, receipt, config, private, now=now)
    assert "invalid_receipt_attestation" in result["issues"]


def test_missing_credentials_activation_and_direct_connector_are_rejected():
    checker = load_checker()
    receipt, config, private = control_receipt(checker)
    receipt["runtime"]["credentials_available"] = False
    receipt["activation"]["activated"] = False
    reseal(checker, receipt, private["key"])
    result = validate(checker, receipt, config, private)
    assert {"live_credentials_unavailable", "actual_candidate_activation_missing"} <= set(result["issues"])

    receipt, config, private = control_receipt(checker)
    receipt["operations"][1]["source"] = "direct_google_drive_connector"
    reseal(checker, receipt, private["key"])
    result = validate(checker, receipt, config, private)
    assert "tool_event_not_from_native_sheets_api" in result["issues"]


def test_missing_private_identity_locator_run_or_receipt_key_blocks():
    checker = load_checker()
    receipt, config, private = control_receipt(checker)
    result = checker.validate_receipt(
        receipt, {}, locator="", run_id="", key="", now=private["now"], repo_root=REPO_ROOT
    )
    assert result["status"] == "blocked"
    assert result["accepted"] is False
    assert "invalid_private_config" in result["issues"]
    assert checker.load_private_inputs(None, None)[2] == [
        "missing_private_config_path", "missing_receipt_path"
    ]


def test_private_resource_contract_rejects_titles_paths_and_urls():
    checker = load_checker()
    receipt, config, private = control_receipt(checker)
    config["expected_resource"]["title"] = "Private workbook title"
    result = validate(checker, receipt, config, private)
    assert result["accepted"] is False
    assert "private_resource_config_contains_unapproved_fields" in result["issues"]

    del config["expected_resource"]["title"]
    receipt["resource"]["url"] = "https://example.invalid/private"
    reseal(checker, receipt, private["key"])
    result = validate(checker, receipt, config, private)

    assert result["accepted"] is False
    assert "receipt_contains_unapproved_resource_fields" in result["issues"]
    assert "Private workbook title" not in json.dumps(result)
