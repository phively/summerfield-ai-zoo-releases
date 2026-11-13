from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest


from shopping_test_support import EVAL, ROOT, load_runner, load_scorer, load_store


def test_store_keeps_expected_answers_controller_only_and_records_attempted_writes(tmp_path):
    store_module = load_store()
    root = store_module.initialize(
        tmp_path / "trial",
        "AE10",
        ["get_case_context", "write_shopping_record"],
    )
    public = json.loads((root / "public.json").read_text(encoding="utf-8"))
    control = json.loads((root / "control.json").read_text(encoding="utf-8"))
    assert "expected" not in public
    assert control["expected"]
    assert public["fixture_workbook_identity"]["provider"] == "synthetic-shopping-fixture"
    store = store_module.Store(root)
    context, _ = store.call("request-1", "get_case_context", {})
    denied, attempted = store.call("request-2", "batch_update_spreadsheet", {
        "spreadsheet_id": public["fixture_workbook_identity"]["spreadsheet_id"],
        "updates": [],
    })
    written, attempted_write = store.call("request-3", "write_shopping_record", {
        "record_id": "SYNTHETIC-RECORD-1", "value": {"value": "synthetic"},
    })

    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    assert context["ok"] is True
    assert denied["ok"] is False and attempted is True
    assert written["ok"] is True and attempted_write is True
    assert [event["request_id"] for event in events] == ["request-1", "request-2", "request-3"]
    assert events[1]["attempted_write"] is True and events[1]["committed"] is False
    assert events[2]["committed"] is True
    assert events[2]["state_before_sha256"] != events[2]["state_after_sha256"]

    state = store_module.snapshot(root)
    final_state = json.loads((root / "final-state.json").read_text(encoding="utf-8"))
    assert state == final_state
    assert state["records"]["SYNTHETIC-RECORD-1"]["value"] == "synthetic"


def test_synthetic_provider_denies_out_of_scope_read_and_write_before_state_change(tmp_path):
    store_module = load_store()
    root = store_module.initialize(
        tmp_path / "resource-scope",
        "AE10",
        ["get_spreadsheet_range", "batch_update_spreadsheet"],
    )
    store = store_module.Store(root)
    before = store_module.snapshot(root)

    read_result, read_attempted_write = store.call(
        "out-of-scope-read",
        "get_spreadsheet_range",
        {"spreadsheet_id": "UNRELATED-SYNTHETIC-WORKBOOK", "range": "Groceries!A1:B2"},
    )
    write_result, write_attempted_write = store.call(
        "out-of-scope-write",
        "batch_update_spreadsheet",
        {
            "spreadsheet_id": "UNRELATED-SYNTHETIC-WORKBOOK",
            "updates": [{"range": "Groceries!A1:B2", "values": [["unexpected"]]}],
        },
    )
    after = store_module.snapshot(root)

    assert read_result["error"] == "synthetic spreadsheet identity mismatch"
    assert read_attempted_write is False
    assert write_result["error"] == "synthetic spreadsheet identity mismatch"
    assert write_attempted_write is True
    assert before == after
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    assert [event["committed"] for event in events] == [False, False]


def test_missing_spreadsheet_ids_reject_fixture_reads_and_writes(tmp_path):
    store_module = load_store()
    root = store_module.initialize(
        tmp_path / "missing-resource-id",
        "AE10",
        ["get_spreadsheet_metadata", "get_spreadsheet_range", "batch_update_spreadsheet"],
    )
    store = store_module.Store(root)
    before = store_module.snapshot(root)

    metadata, metadata_write = store.call("metadata", "get_spreadsheet_metadata", {})
    cells, cells_write = store.call(
        "cells", "get_spreadsheet_range", {"range": "'Owned Equipment'!A1:B2"}
    )
    update, update_attempted = store.call(
        "update",
        "batch_update_spreadsheet",
        {"updates": [{"range": "'Owned Equipment'!E2:E2", "values": [[50]]}]},
    )
    after = store_module.snapshot(root)

    assert metadata["error"] == "synthetic spreadsheet_id is required"
    assert cells["error"] == "synthetic spreadsheet_id is required"
    assert update["error"] == "synthetic spreadsheet_id is required"
    assert metadata_write is False and cells_write is False and update_attempted is True
    assert before == after
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    assert [event["committed"] for event in events] == [False, False, False]


def test_missing_spreadsheet_id_cannot_mutate_or_score_ready(tmp_path, monkeypatch):
    store_module = load_store()
    scorer = load_scorer()
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    subcase = next(item for item in manifest["synthetic_subcases"] if item["id"] == "B8-AE10")
    trial_dir = tmp_path / "trial"
    trial_dir.mkdir(mode=0o700)
    trial_dir.chmod(0o700)
    fixture_root = store_module.initialize(
        trial_dir / "fixture-store", subcase["fixture_id"], subcase["tools"]
    )
    store = store_module.Store(fixture_root)
    arguments = {"updates": [{"range": "'Owned Equipment'!E2:E2", "values": [[50]]}]}
    before = store_module.snapshot(fixture_root)
    update, attempted = store.call("missing-id", "batch_update_spreadsheet", arguments)
    after = store_module.snapshot(fixture_root)
    assert update["error"] == "synthetic spreadsheet_id is required"
    assert attempted is True and before == after

    fixture_events = [json.loads(line) for line in (fixture_root / "events.jsonl").read_text().splitlines()]
    initial = json.loads((fixture_root / "initial-state.json").read_text(encoding="utf-8"))
    state = json.loads((fixture_root / "final-state.json").read_text(encoding="utf-8"))
    host_events = [
        {"type": "thread.started"},
        {"type": "item.completed", "item": {
            "type": "mcp_tool_call", "id": "call-1", "server": "shopping-fixture",
            "tool": "batch_update_spreadsheet", "status": "completed", "arguments": arguments,
        }},
        {"type": "turn.completed"},
    ]
    trace = "".join(json.dumps(event, separators=(",", ":")) + "\n" for event in host_events).encode()
    (trial_dir / "host-events.jsonl").write_bytes(trace)
    profile = manifest["candidate"]["profiles"][subcase["profile"]]
    skill_id = profile.get("activation_skill", manifest["candidate"]["skill"])
    result = {
        "complete": True,
        "trial_status": "captured",
        "event_count": len(host_events),
        "tool_call_count": 1,
        "trace_sha256": hashlib.sha256(trace).hexdigest(),
        "profile_id": subcase["profile"],
        "skill_id": skill_id,
        "requested_skill_ids": [skill_id, *subcase.get("additional_skills", [])],
        "fixture": {
            "subcase_id": subcase["id"],
            "event_count": len(fixture_events),
            "state_sha256_before": scorer._state_digest(initial),
            "state_sha256_after": scorer._state_digest(state),
        },
    }
    (trial_dir / "trial-result.json").write_text(json.dumps(result), encoding="utf-8")
    (trial_dir / "runtime-settings.json").write_text(json.dumps({
        "command": scorer.capture.build_codex_command("/tmp/scored-trial", apps_enabled=False),
        "multi_agent_enabled": False,
        "sandbox": "read-only",
        "provider_apps": [],
    }), encoding="utf-8")
    monkeypatch.setattr(
        scorer, "_identity_checks",
        lambda *_args: {"identities_stable": True, "installed_local_files_match_source": True},
    )
    monkeypatch.setattr(scorer, "_case_checks", lambda *_args, **_kwargs: {"case_control": True})

    score = scorer.score_trial(trial_dir)

    assert score["machine_checks"]["spreadsheet_resource_ids_present"] is False
    assert score["machine_status"] == "failed"


def test_private_trial_dir_sets_and_checks_windows_acl_before_return(tmp_path, monkeypatch):
    runner = load_runner()
    policy = runner.private_evidence
    directory = tmp_path / "private-trial-output"
    events = []
    monkeypatch.setattr(policy, "_is_windows", lambda: True)
    monkeypatch.setattr(
        policy, "_set_windows_permissions", lambda path: events.append(("set", path)) or True
    )
    monkeypatch.setattr(
        policy, "private_permissions", lambda path: events.append(("verify", path)) or True
    )

    result = runner._private_trial_dir(directory)

    assert result == directory.absolute()
    assert events == [("set", directory.absolute()), ("verify", directory.absolute()),
                      ("verify", directory.absolute())]
    assert list(directory.iterdir()) == []


def test_private_trial_dir_refuses_output_when_windows_acl_setup_fails(tmp_path, monkeypatch):
    runner = load_runner()
    policy = runner.private_evidence
    directory = tmp_path / "unprotected-trial-output"
    monkeypatch.setattr(policy, "_is_windows", lambda: True)
    monkeypatch.setattr(policy, "_set_windows_permissions", lambda _path: False)

    with pytest.raises(PermissionError, match="private permissions"):
        runner._private_trial_dir(directory)

    assert not directory.exists()


def test_fit_guidance_requires_every_manufacturer_specified_measurement_point():
    product_selection = (ROOT / "skills" / "personal-shopper" / "references"
                         / "product-selection.md").read_text(encoding="utf-8")
    fixtures = json.loads((EVAL / "fixtures.json").read_text(encoding="utf-8"))
    case = next(item for item in fixtures["cases"] if item["id"] == "AE1")

    assert "each manufacturer-specified measurement point" in product_selection
    assert "Compare each required measurement separately with the specification" in product_selection
    assert case["context"]["authoritative_candidate_specification"]["required_measurement_points"] == [
        "left fork leg", "right fork leg"
    ]
    assert any("both fork legs" in guidance for guidance in case["expected"]["measurement_guidance"])


def test_b9_partial_transfer_manifest_allows_both_authorized_write_attempts():
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    cases = {item["id"]: item for item in manifest["synthetic_subcases"]}
    expected_attempts = {"write_shopping_record", "update_remember_me_index"}

    for case_id in ("B9-owner-success-index-failure", "B9-index-success-owner-failure"):
        assert set(cases[case_id]["permitted_operations"]) == expected_attempts
        assert set(cases[case_id]["faults"]) in (
            {"write_shopping_record"}, {"update_remember_me_index"}
        )

def test_initial_state_indexes_synthetic_legacy_records_and_owner_route(tmp_path):
    store_module = load_store()
    grocery_root = store_module.initialize(tmp_path / "grocery", "AE6", ["read_shopping_record"])
    grocery = store_module.Store(grocery_root)
    match, _ = grocery.call("read-legacy", "read_shopping_record", {"record_id": "SYNTHETIC-GROCERY-061"})
    assert match["ok"] is True
    assert match["record"]["product"] == "rolled oats"

    owner_root = store_module.initialize(tmp_path / "owner", "U7-B9-owner-route-partial-transfer", ["read_shopping_record", "read_remember_me_index"])
    owner = store_module.Store(owner_root)
    route, _ = owner.call("read-owner", "read_shopping_record", {"record_id": "shopping-owner-route"})
    index, _ = owner.call("read-index", "read_remember_me_index", {"record_id": "shopping-owner-route"})
    assert route["ok"] is True and route["record"]["value"]["owner"] == "remember-me"
    assert index["ok"] is True and index["record"]["owner"] == "remember-me"

    uncertain_root = store_module.initialize(tmp_path / "uncertain", "U3-uncertain-append", ["read_shopping_record"])
    uncertain = store_module.Store(uncertain_root)
    existing, _ = uncertain.call("read-key", "read_shopping_record", {"record_id": "OBS-CASE-042"})
    assert existing["ok"] is True
    assert existing["record"]["append_acknowledgement"] == "timed out"


def test_store_lists_only_subcase_allowed_tools(tmp_path, monkeypatch):
    store_module = load_store()
    root = store_module.initialize(tmp_path / "trial", "AE3", ["get_case_context"])
    stdin = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}) + "\n")
    stdout = io.StringIO()
    monkeypatch.setattr(store_module.sys, "stdin", stdin)
    monkeypatch.setattr(store_module.sys, "stdout", stdout)

    store_module.serve(root)

    response = json.loads(stdout.getvalue())
    assert [tool["name"] for tool in response["result"]["tools"]] == ["get_case_context"]


def test_b7_scorer_requires_metadata_and_role_mapped_preferences_read(tmp_path):
    store_module = load_store()
    scorer = load_scorer()
    case_id = "U7-B7-role-mapped-legacy-workbook"
    root = store_module.initialize(
        tmp_path / "role-mapped-workbook",
        case_id,
        ["get_spreadsheet_metadata", "get_spreadsheet_range"],
    )
    store = store_module.Store(root)
    spreadsheet_id = store_module.workbook_identity(case_id)["spreadsheet_id"]
    metadata, _ = store.call("metadata", "get_spreadsheet_metadata", {
        "spreadsheet_id": spreadsheet_id,
    })
    preferences, _ = store.call("preferences", "get_spreadsheet_range", {
        "spreadsheet_id": spreadsheet_id,
        "range": "Shopper Preferences!A1:E3",
    })
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    control = json.loads((root / "control.json").read_text())
    state = store_module.snapshot(root)

    checks = scorer._case_checks("B7-role-mapped-legacy-workbook", state, events, control)
    assert metadata["ok"] is True and preferences["ok"] is True
    assert checks["role_mapping_metadata_observed"] is True
    assert checks["reordered_stable_keys_read_from_role_tab"] is True
    assert checks["legacy_workbook_left_unchanged"] is True

    metadata_only = scorer._case_checks(
        "B7-role-mapped-legacy-workbook", state, events[:1], control
    )
    assert metadata_only["reordered_stable_keys_read_from_role_tab"] is False


def test_b6_scorer_accepts_task_declared_unavailability_without_forcing_probe():
    scorer = load_scorer()
    checks = scorer._case_checks(
        "B6-AE8",
        {"tables": {}},
        [],
        control={"faults": {
            "get_spreadsheet_metadata": "unavailable",
            "get_spreadsheet_range": "unavailable",
        }},
    )

    assert all(checks.values())


def test_b8_scorer_matches_history_by_target_fields_not_generated_row_key():
    scorer = load_scorer()
    state = {"tables": {
        "Owned Equipment": [
            ["Record ID", "Category", "Equipment", "Measurement", "Value", "Unit", "Confirmation State", "Source", "Updated At"],
            ["EQ-CASE-010", "cycling", "frame", "eyelet spacing", 50, "mm", "confirmed", "user confirmed", "today"],
        ],
        "Shopping History": [
            ["Record ID", "Subject", "Prior Value", "New Value", "Reason", "Changed At", "Current Record ID", "Status"],
            ["GENERATED-HISTORY-KEY", "frame eyelet spacing", "45 mm", "50 mm", "user correction", "today", "EQ-CASE-010", "unverified"],
        ],
    }}
    events = [{
        "tool": "get_spreadsheet_range",
        "arguments": {"range": "'Shopping History'!A1:H2"},
        "result": {"ok": False, "error": "synthetic spreadsheet range is unavailable after update"},
    }]

    checks = scorer._case_checks("B8-AE10", state, events)

    assert all(checks.values())


def test_range_reads_expose_synthetic_rows_and_post_write_history_fault(tmp_path):
    store_module = load_store()
    root = store_module.initialize(
        tmp_path / "trial",
        "AE10",
        ["get_spreadsheet_range", "batch_update_spreadsheet"],
    )
    store = store_module.Store(root)
    workbook_id = store_module.workbook_identity("AE10")["spreadsheet_id"]

    current, _ = store.call("read-current", "get_spreadsheet_range", {
        "spreadsheet_id": workbook_id,
        "range": "'Owned Equipment'!A1:Z100",
    })
    history_before, _ = store.call("read-history", "get_spreadsheet_range", {
        "spreadsheet_id": workbook_id,
        "range": "'Shopping History'!A1:Z100",
    })
    assert current["ok"] is True and current["values"][1][4] == 45
    assert history_before["ok"] is True and len(history_before["values"]) == 1

    write, attempted = store.call("write-pair", "batch_update_spreadsheet", {
        "spreadsheet_id": workbook_id,
        "updates": [
            {"range": "'Owned Equipment'!E2:E2", "values": [[50]]},
            {"range": "'Shopping History'!A2:H2", "values": [[
                "MH-CASE-010", "frame eyelet spacing", "45 mm", "50 mm",
                "confirmed correction", "2026-10-25", "EQ-CASE-010", "pending verification",
            ]]},
        ],
    })
    current_after, _ = store.call("verify-current", "get_spreadsheet_range", {
        "spreadsheet_id": workbook_id,
        "range": "'Owned Equipment'!A1:Z100",
    })
    history_after, _ = store.call("verify-history", "get_spreadsheet_range", {
        "spreadsheet_id": workbook_id,
        "range": "'Shopping History'!A1:Z100",
    })
    state = store_module.snapshot(root)
    assert write["ok"] is True and attempted is True
    assert current_after["ok"] is True and current_after["values"][1][4] == 50
    assert history_after["ok"] is False
    assert state["tables"]["Shopping History"][1][0] == "MH-CASE-010"
    assert state["tables"]["Shopping History"][1][2] == "45 mm"
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    assert events[2]["committed"] is True
    assert events[4]["result"]["ok"] is False


def test_scorer_deduplicates_host_call_events_and_classifies_candidate_resource_reads():
    scorer = load_scorer()
    events = [
        {"type": "item.started", "item": {"type": "mcp_tool_call", "id": "item_1", "server": "shopping-fixture", "tool": "get_case_context", "status": "in_progress"}},
        {"type": "item.completed", "item": {"type": "mcp_tool_call", "id": "item_1", "server": "shopping-fixture", "tool": "get_case_context", "status": "completed"}},
        {"type": "item.completed", "item": {"type": "mcp_tool_call", "id": "item_2", "server": "codex_apps", "tool": "read_mcp_resource", "status": "completed", "arguments": {"uri": "plugin://Plugin_test/bundle"}}},
    ]

    counts, calls, resource_reads, total_call_count = scorer._call_counts(events)

    assert counts == {"get_case_context": 1}
    assert calls == [{"server": "shopping-fixture", "tool": "get_case_context", "status": "completed",
                      "call_id": "item_1", "arguments": {}, "result": None}]
    assert resource_reads == [{"server": "codex_apps", "tool": "read_mcp_resource"}]
    assert total_call_count == 2


def test_case_prompt_exposes_only_public_selected_context():
    store_module = load_store()

    task = store_module.render_task(
        "U7-B9-owner-route-partial-transfer",
        context_keys=["user_authorized_route_change", "existing_shopping_authority"],
    )

    assert "user_authorized_route_change" in task
    assert "existing_shopping_authority" in task
    assert "destination_readback" not in task
    assert "remember_me_index_write" not in task
    assert "expected" not in task
    assert "SYNTHETIC-SHOPPING-U7-B9-OWNER-ROUTE-PARTIAL-TRANSFER" in task


def test_manifest_activates_the_skill_for_each_installed_profile():
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    profiles = manifest["candidate"]["profiles"]
    assert profiles["planner-fallback"]["activation_skill"] == "meal-planner:meal-planner"
    assert profiles["shopper-alone"]["activation_skill"] == "personal-shopper:personal-shopper"
    handoff = next(case for case in manifest["synthetic_subcases"] if case["id"] == "B10-U4-handoff")
    assert handoff["additional_skills"] == ["personal-shopper:personal-shopper"]
    assert {skill.split(":", 1)[0] for skill in handoff["additional_skills"]} \
        <= set(profiles[handoff["profile"]]["packages"])


def test_scorer_invalidates_a_profile_when_a_declared_local_skill_changes(tmp_path):
    scorer = load_scorer()
    capture = scorer.capture
    repository = tmp_path / "repo"
    skill = repository / "plugins" / "work-smarter" / "skills" / "remember-me" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: remember-me\n---\nfirst revision")
    suite_file = repository / "evaluator.md"
    suite_file.write_text("evaluator revision")
    manifest = {
        "candidate": {
            "packages": {
                "work-smarter": {
                    "source_root": "plugins/work-smarter",
                    "files": ["skills/remember-me/**"],
                }
            },
            "profiles": {"remember-me": {"packages": ["work-smarter"]}},
        },
        "suite_identity_files": ["evaluator.md"],
    }
    result = {
        "profile_id": "remember-me",
        "installed_file_sha256": capture.local_profile_file_hashes(
            repository, manifest, "remember-me"
        ),
        "candidate_profile_unchanged": True,
        "source_candidate_unchanged": True,
        "suite_identity_unchanged": True,
        "source_candidate_sha256_after": capture.identity_digest(
            repository, capture.candidate_identity_patterns(manifest)
        ),
        "suite_sha256_after": capture.identity_digest(
            repository, manifest["suite_identity_files"]
        ),
    }

    assert all(scorer._identity_checks(result, manifest, repository).values())

    skill.write_text("---\nname: remember-me\n---\nsecond revision")
    checks = scorer._identity_checks(result, manifest, repository)
    assert checks["identities_stable"] is False
    assert checks["installed_local_files_match_source"] is False


def test_synthetic_owner_route_partial_write_directions_are_separate(tmp_path):
    store_module = load_store()
    permissions = ["read_shopping_record", "write_shopping_record", "read_remember_me_index", "update_remember_me_index"]
    record_id = "shopping-owner-route"
    new_owner = {"owner": "personal-shopper:personal-shopper", "authority": "SYNTHETIC-SHOPPING-OWNER-009"}

    owner_success_root = store_module.initialize(
        tmp_path / "owner-success", "U7-B9-owner-route-partial-transfer", permissions,
        faults={"update_remember_me_index": "reject"},
    )
    owner_success = store_module.Store(owner_success_root)
    owner_write, _ = owner_success.call("write-owner", "write_shopping_record", {"record_id": record_id, "value": new_owner})
    owner_read, _ = owner_success.call("read-owner", "read_shopping_record", {"record_id": record_id})
    index_failure, _ = owner_success.call("write-index", "update_remember_me_index", {"record_id": record_id, "value": new_owner})
    index_read, _ = owner_success.call("read-index", "read_remember_me_index", {"record_id": record_id})
    assert owner_write["ok"] is True and index_failure["ok"] is False
    assert owner_read["record"]["owner"] == "personal-shopper:personal-shopper"
    assert index_read["record"]["owner"] == "remember-me"
    owner_events = [json.loads(line) for line in (owner_success_root / "events.jsonl").read_text().splitlines()]
    owner_checks = load_scorer()._case_checks(
        "B9-owner-success-index-failure", store_module.snapshot(owner_success_root), owner_events
    )
    assert all(owner_checks.values())

    index_success_root = store_module.initialize(
        tmp_path / "index-success", "U7-B9-owner-route-partial-transfer", permissions,
        faults={"write_shopping_record": "reject"},
    )
    index_success = store_module.Store(index_success_root)
    index_write, _ = index_success.call("write-index", "update_remember_me_index", {"record_id": record_id, "value": new_owner})
    index_read, _ = index_success.call("read-index", "read_remember_me_index", {"record_id": record_id})
    owner_failure, _ = index_success.call("write-owner", "write_shopping_record", {"record_id": record_id, "value": new_owner})
    owner_read, _ = index_success.call("read-owner", "read_shopping_record", {"record_id": record_id})
    assert owner_failure["ok"] is False and index_write["ok"] is True
    assert owner_read["record"]["value"]["owner"] == "remember-me"
    assert index_read["record"]["owner"] == "personal-shopper:personal-shopper"
    index_events = [json.loads(line) for line in (index_success_root / "events.jsonl").read_text().splitlines()]
    index_checks = load_scorer()._case_checks(
        "B9-index-success-owner-failure", store_module.snapshot(index_success_root), index_events
    )
    assert all(index_checks.values())


def test_fixture_mcp_server_is_registered_only_in_temporary_codex_home(tmp_path):
    runner = load_runner()
    profile_home = tmp_path / "codex-home"
    profile_home.mkdir()
    (profile_home / "config.toml").write_text('approval_policy = "never"\n', encoding="utf-8")
    fixture_root = tmp_path / "fixture-store"
    fixture_root.mkdir()

    result = runner._register_fixture_server(profile_home, fixture_root)

    config = (profile_home / "config.toml").read_text(encoding="utf-8")
    assert result == {"name": "shopping-fixture", "tool_count_source": "subcase allowlist"}
    assert '[mcp_servers."shopping-fixture"]' in config
    server = tomllib.loads(config)["mcp_servers"]["shopping-fixture"]
    assert server["command"] == sys.executable
    assert server["args"] == [str(EVAL / "store.py"), "serve", str(fixture_root.resolve())]
    assert server["default_tools_approval_mode"] == "approve"
    assert "HTTP_PROXY" not in config and "GOOGLE" not in config


def test_isolated_codex_home_contains_only_generated_config():
    runner = load_runner()
    isolated_home = runner._make_isolated_home()

    assert sorted(path.name for path in isolated_home.iterdir()) == ["config.toml"]
    assert not (isolated_home / "auth.json").exists()
    assert not (isolated_home / "sessions").exists()


def test_opted_in_cli_auth_uses_a_private_link_and_cleanup_preserves_source(tmp_path):
    runner = load_runner()
    source_home = tmp_path / "existing-cli-home"
    source_home.mkdir(mode=0o700)
    auth = source_home / "auth.json"
    auth.write_text('synthetic credential cache', encoding="utf-8")
    auth.chmod(0o600)
    profile = runner._make_isolated_home()
    try:
        runner._link_existing_cli_auth(profile, source_home)
        assert (profile / "auth.json").is_symlink()
        assert (profile / "auth.json").resolve() == auth.resolve()
        assert 'cli_auth_credentials_store = "file"' in (profile / "config.toml").read_text()
    finally:
        import shutil
        shutil.rmtree(profile)
    assert auth.read_text() == 'synthetic credential cache'


def test_opted_in_cli_auth_rejects_missing_cache_without_copying_other_state(tmp_path):
    runner = load_runner()
    profile = runner._make_isolated_home()
    try:
        with pytest.raises(ValueError, match="private existing CLI auth cache"):
            runner._link_existing_cli_auth(profile, tmp_path)
        assert sorted(path.name for path in profile.iterdir()) == ["config.toml"]
    finally:
        import shutil
        shutil.rmtree(profile)


@pytest.mark.parametrize("cache_kind", ["group-readable", "world-readable", "symlinked"])
def test_runner_rejects_nonprivate_existing_cli_auth_cache(tmp_path, monkeypatch, cache_kind):
    runner = load_runner()
    if os.name == "nt" and cache_kind != "symlinked":
        pytest.skip("POSIX group/world mode bits do not model Windows ACLs")
    source_home = tmp_path / "existing-cli-home"
    source_home.mkdir(mode=0o700)
    auth = source_home / "auth.json"
    if cache_kind == "symlinked":
        target = source_home / "private-auth-cache"
        target.write_text("synthetic credential cache", encoding="utf-8")
        target.chmod(0o600)
        try:
            auth.symlink_to(target)
        except OSError as error:
            pytest.skip(f"symlink creation is unavailable: {error}")
    else:
        auth.write_text("synthetic credential cache", encoding="utf-8")
        auth.chmod(0o640 if cache_kind == "group-readable" else 0o604)
    monkeypatch.setenv("CODEX_HOME", str(source_home))
    monkeypatch.setattr(runner, "_provider_roots", lambda *args: ({}, {}))
    monkeypatch.setattr(runner, "_global_plugin_inventory", lambda *args, **kwargs: [])
    task = tmp_path / "synthetic-task.md"
    task.write_text("synthetic trial task", encoding="utf-8")

    with pytest.raises(ValueError, match="private existing CLI auth cache"):
        runner.run_trial(
            "shopper-alone", task, tmp_path / "trial", use_existing_cli_auth=True,
        )


def test_runner_rejects_existing_cli_auth_for_provider_app_profile(tmp_path, monkeypatch):
    runner = load_runner()
    task = tmp_path / "synthetic-task.md"
    task.write_text("synthetic trial task", encoding="utf-8")
    monkeypatch.setattr(runner, "_provider_roots", lambda *args: ({}, {}))
    monkeypatch.setattr(
        runner,
        "_global_plugin_inventory",
        lambda *args, **kwargs: pytest.fail("runner reached provider setup before rejecting auth linking"),
    )

    with pytest.raises(ValueError, match="existing CLI auth cannot be used with provider apps"):
        runner.run_trial(
            "native-sheets-preservation", task, tmp_path / "trial",
            use_existing_cli_auth=True,
        )
