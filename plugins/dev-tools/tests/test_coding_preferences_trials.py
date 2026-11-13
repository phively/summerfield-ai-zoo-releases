"""Deterministic checker controls; these tests do not claim model behavior."""

import importlib.util
import io
import json
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "coding-preferences"


def load(name):
    spec = importlib.util.spec_from_file_location(name, EVAL / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def candidate():
    import hashlib

    paths = (
        ROOT / "skills" / "coding-preferences" / "SKILL.md",
        ROOT / "skills" / "coding-preferences" / "references" / "coding-workflow.md",
        ROOT / "skills" / "coding-preferences" / "references" / "record-management.md",
    )
    files = {
        path.relative_to(ROOT.parent.parent).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }
    return {"name": "deterministic-control-candidate", "files": files}


def trial(tmp_path, case_id, evidence_kind="deterministic-control"):
    load("store").initialize(tmp_path, case_id, candidate(), evidence_kind=evidence_kind)
    return load("store").Store(tmp_path)


def identity(record):
    return {key: record[key] for key in ("provider", "container", "id")}


def read(store, record):
    return store.call({"op": "read", "identity": identity(record)})


def transfer_target_content():
    return (EVAL / "fixtures" / "coding-preferences-transfer-target.md").read_text(encoding="utf-8")


def transfer_pending_content():
    return (EVAL / "fixtures" / "coding-preferences-transfer-pending.md").read_text(encoding="utf-8")


def create_verified_transfer_target(store, destination):
    created = {
        **destination,
        "path": "coding-preferences.md",
        "owner": "user",
        "content": transfer_pending_content(),
    }
    assert store.call({"op": "create", "record": created})["ok"]
    first_readback = store.call({"op": "read", "identity": identity(created)})
    assert first_readback["ok"]
    current = first_readback["record"]
    assert store.call({
        "op": "write", "identity": identity(current), "revision": current["revision"],
        "content": transfer_target_content(),
    })["ok"]
    final_readback = store.call({"op": "read", "identity": identity(current)})
    assert final_readback["ok"]
    return final_readback["record"]


def authorized_two_stage_update(store, record, *, final_content=None):
    effective_date = json.loads((store.root / "control.json").read_text(encoding="utf-8")).get(
        "effective_date", "2026-10-23"
    )
    pending = (EVAL / "fixtures" / "coding-preferences-after-unverified.md").read_text(encoding="utf-8")
    pending = pending.replace("- Effective: 2026-10-23.", f"- Effective: {effective_date}.")
    assert store.call({
        "op": "write", "identity": identity(record), "revision": record["revision"], "content": pending,
    })["ok"]
    first_readback = read(store, record)
    assert first_readback["ok"]
    current = first_readback["record"]
    content = final_content or (EVAL / "fixtures" / "coding-preferences-after.md").read_text(encoding="utf-8")
    content = content.replace("- Effective: 2026-10-23.", f"- Effective: {effective_date}.")
    assert store.call({
        "op": "write", "identity": identity(current), "revision": current["revision"], "content": content,
    })["ok"]
    assert read(store, current)["ok"]


def finish(tmp_path, final):
    (tmp_path / "final.txt").write_text(final, encoding="utf-8")
    (tmp_path / "runtime.jsonl").write_text(json.dumps({"type": "turn.completed"}) + "\n", encoding="utf-8")
    (tmp_path / "runtime-settings.json").write_text(
        json.dumps({"kind": "deterministic-control", "execution_date": "2026-10-23"}), encoding="utf-8"
    )
    load("store").snapshot(tmp_path)
    return load("check_trial").check(tmp_path)


def test_manifest_cases_are_unique_and_reference_existing_fixtures() -> None:
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    cases = manifest["cases"]
    assert manifest["suite"] == "coding-preferences-acceptance"
    assert manifest["scorer_version"]
    assert len({case["id"] for case in cases}) == len(cases)
    assert len(cases) >= 15
    for case in cases:
        assert case["public"]["prompt"]
        assert set(case["public"]["tools"]) <= {"list", "read", "write", "create"}
        assert case["report"] in {"verified", "unverified", "partial", "no-write", "needs-input", "unavailable"}
        for record in (
            list(case["initial"].values())
            + list(case.get("staged_expected", {}).values())
            + list(case["expected"].values())
        ):
            content_file = record.get("content_file")
            if content_file:
                assert (EVAL / "fixtures" / content_file).is_file()


def test_approval_modes_allow_synthetic_writes_in_noninteractive_trials() -> None:
    checker = load("check_trial")
    assert checker.expected_mcp_approval_modes(["read", "write", "create"]) == {
        "read": "auto",
        "write": "approve",
        "create": "approve",
    }


def test_approval_modes_require_explicit_maps_even_when_the_map_is_empty() -> None:
    checker = load("check_trial")
    assert not checker.approval_modes_match({}, {"tools": []})
    assert checker.approval_modes_match(
        {"mcp_tool_approval_modes": {}}, {"tools": []}
    )
    assert not checker.approval_modes_match({}, {"tools": ["read"]})
    assert checker.approval_modes_match(
        {"mcp_tool_approval_modes": {"read": "auto"}}, {"tools": ["read"]}
    )


def test_authorized_update_uses_trial_date_for_fresh_readback_metadata() -> None:
    checker = load("check_trial")
    expected = (EVAL / "fixtures" / "coding-preferences-after.md").read_text(encoding="utf-8")
    actual = expected.replace(
        "- Last verified: 2026-10-22; fresh canonical readback at fixture/library-a/coding",
        "- Last verified: 2026-10-23; fresh canonical readback at fixture/library-a/coding",
    ).replace(
        "- Last verified: 2026-10-22.",
        "- Last verified: 2026-10-23.",
    ).replace("- Effective: 2026-10-23.", "- Effective: 2026-10-22.")
    assert checker.authorized_update_content_matches(actual, expected, "2026-10-23", "2026-10-22")
    assert not checker.authorized_update_content_matches(actual, expected, "2026-10-22")
    assert checker.authorized_update_content_matches(
        actual.replace("- Preference: Use uppercase SQL keywords", "- Preference: use uppercase SQL keywords"),
        expected,
        "2026-10-23",
        "2026-10-22",
    )


def test_sql_layout_application_requires_separate_indented_projections_and_clauses() -> None:
    checker = load("check_trial")
    expected = {
        "columns": ["id", "name"],
        "table": "users",
        "predicate": "active = TRUE",
        "limit": "5",
    }
    formatted = """```sql
SELECT
  id,
  name
FROM users
WHERE active = TRUE
LIMIT 5;
```"""
    flattened = "SELECT id, name FROM users WHERE active = TRUE LIMIT 5;"
    assert checker.sql_layout_application_matches(formatted, expected)
    assert not checker.sql_layout_application_matches(flattened, expected)


def test_record_content_identity_must_match_the_selected_authority() -> None:
    checker = load("check_trial")
    record = {
        "owner": "user",
        "provider": "fixture",
        "container": "library-a",
        "id": "coding",
        "path": "coding-preferences.md",
    }
    matching = """# Coding Preferences
- Owner: user
- Provider: fixture
- Container: library-a
- Resource ID: coding
- Durable path: coding-preferences.md
"""
    mismatched = matching.replace("- Container: library-a", "- Container: evaluation fixtures")
    assert checker.record_content_identity_matches(matching, record)
    assert not checker.record_content_identity_matches(mismatched, record)


def test_transfer_stages_pending_metadata_and_preserves_all_preference_facts() -> None:
    checker = load("check_trial")
    fixtures = EVAL / "fixtures"
    source = (fixtures / "coding-preferences-before.md").read_text(encoding="utf-8")
    pending = (fixtures / "coding-preferences-transfer-pending.md").read_text(encoding="utf-8")
    verified = (fixtures / "coding-preferences-transfer-target.md").read_text(encoding="utf-8")

    assert checker.transferred_record_content_matches(
        pending, source, verified, "2026-10-23", verified=False
    )
    assert checker.transferred_record_content_matches(
        verified, source, verified, "2026-10-23", verified=True
    )
    separately_worded = verified.replace("readback", "read back")
    assert checker.transferred_record_content_matches(
        separately_worded, source, verified, "2026-10-23", verified=True
    )
    changed_preference = verified.replace("Use lowercase SQL keywords", "Use uppercase SQL keywords")
    assert not checker.transferred_record_content_matches(
        changed_preference, source, verified, "2026-10-23", verified=True
    )
    changed_provenance = verified.replace(
        "Explicit synthetic user authorization in fixture CP-SAVE-001.",
        "Inferred from a previous task.",
        1,
    )
    assert not checker.transferred_record_content_matches(
        changed_provenance, source, verified, "2026-10-23", verified=True
    )


def test_pointer_write_must_follow_verified_destination_write_readback() -> None:
    checker = load("check_trial")
    identity = {
        "provider": "fixture", "container": "repository-b", "id": "coding-new",
        "path": "coding-preferences.md", "owner": "user",
    }
    content = "verified destination record"
    destination_initial_read = {
        "sequence": 3,
        "record_id": "coding-new",
        "request": {"op": "read"},
        "result": {"ok": True, "record": {**identity, "revision": "rev-1", "content": "pending"}},
    }
    destination_write = {
        "sequence": 4,
        "record_id": "coding-new",
        "committed": True,
        "request": {"op": "write", "identity": identity, "revision": "rev-1", "content": content},
        "result": {"ok": True, "revision": "rev-2"},
    }
    destination_read = {
        "sequence": 5,
        "record_id": "coding-new",
        "request": {"op": "read"},
        "result": {"ok": True, "record": {**identity, "revision": "rev-2", "content": content}},
    }
    pointer_write = {
        "sequence": 6,
        "record_id": "locator",
        "request": {"op": "write"},
    }
    item = {
        "op": "write",
        "record": "locator",
        "first_attempt_after_verified_write": "coding-new",
    }

    assert checker.first_attempt_follows_verified_write(
        item, [destination_initial_read, destination_write, destination_read, pointer_write]
    )
    pointer_write["sequence"] = 4
    assert not checker.first_attempt_follows_verified_write(
        item, [destination_initial_read, destination_write, pointer_write, destination_read]
    )


def test_unverified_update_keeps_authorization_date_separate_from_update_date() -> None:
    checker = load("check_trial")
    expected = (EVAL / "fixtures" / "coding-preferences-after-unverified.md").read_text(encoding="utf-8")
    explicit_effective = expected.replace("- Effective: 2026-10-23.", "- Effective: 2026-10-22.")
    assert checker.unverified_update_content_matches(explicit_effective, expected, "2026-10-23", "2026-10-22")
    assert not checker.unverified_update_content_matches(explicit_effective, expected, "2026-10-22")


def test_chained_trial_report_contains_each_actual_session_response() -> None:
    checker = load("check_trial")
    runtime = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": "I will inspect the selected record."}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "Saved and verified the preference."}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "I will apply the saved value."}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "Applied the saved preference to this query."}},
    ]
    public = {"sessions": [{"id": "session-1"}, {"id": "session-2"}]}
    settings = {"session_runs": [
        {"final_message": "Saved and verified the preference."},
        {"final_message": "Applied the saved preference to this query."},
    ]}

    assert checker.runtime_final_matches(
        "Saved and verified the preference.\n\nApplied the saved preference to this query.",
        public,
        runtime,
        settings,
    )
    assert not checker.runtime_final_matches(
        "Applied the saved preference to this query.", public, runtime, settings
    )


def test_repository_rule_case_is_self_contained_and_read_only() -> None:
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["id"] == "repository-rule-wins")
    prompt = case["public"]["prompt"]

    assert "def make_user_key(display_name: str, user_id: int) -> str:" in prompt
    assert "trimmed, lowercase display name" in prompt
    assert "camelCase" in prompt and "snake_case" in prompt
    assert "briefly explain the material conflict" in prompt
    assert "do not call tools or inspect files" in prompt
    assert case["public"]["tools"] == []
    assert case["allowed_reads"] == []
    assert case["allowed_writes"] == []
    assert case["allowed_creates"] == []


def test_dev_tools_only_case_contains_a_complete_python_task() -> None:
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["id"] == "dev-tools-only-install")
    prompt = case["public"]["prompt"]

    assert "def normalize_display_name(displayName: str) -> str:" in prompt
    assert "Return the trimmed, lowercase displayName" in prompt
    assert "Work Smarter and its personal-context index are unavailable" in prompt
    assert case["public"]["available_components"] == ["dev-tools"]
    assert case["public"]["tools"] == ["read"]
    assert case["allowed_reads"] == ["coding"]
    assert case["allowed_writes"] == []
    assert case["allowed_creates"] == []


def test_unavailable_authority_case_contains_a_fallback_task() -> None:
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["id"] == "unavailable-authority")
    prompt = case["public"]["prompt"]

    assert "SELECT id, name FROM users" in prompt
    assert "continue with a disclosed ordinary default" in prompt
    assert case["public"]["tools"] == ["read"]
    assert case["allowed_reads"] == ["coding"]
    assert case["allowed_writes"] == []


def test_writing_context_cases_supply_patch_facts() -> None:
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    cases = {item["id"]: item for item in manifest["cases"]}
    assert "Patch facts:" in cases["writing-context-present"]["public"]["prompt"]
    assert "Validation:" in cases["writing-context-present"]["public"]["prompt"]
    assert "using only these facts" in cases["writing-context-unavailable"]["public"]["prompt"]


def test_matrix_contains_second_repository_and_b6_fallback_cases() -> None:
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    cases = {item["id"]: item for item in manifest["cases"]}
    assert "second repository" in cases["second-repository-reuse"]["public"]["prompt"]
    assert cases["partly-readable-authority"]["faults"] == {"coding:read": "partial"}
    assert "content is incomplete" in cases["partly-readable-authority"]["public"]["prompt"]
    copied = cases["copied-authority-not-replaced"]
    assert "coding-copy" in copied["public"]["prompt"]
    assert copied["allowed_reads"] == ["coding"]
    assert copied["initial"]["coding_copy"]["id"] == "coding-copy"


def test_partial_read_fault_returns_explicitly_incomplete_content(tmp_path) -> None:
    store = trial(tmp_path, "partly-readable-authority")
    record = json.loads((tmp_path / "control.json").read_text(encoding="utf-8"))["initial"]["coding"]
    result = read(store, record)

    assert result["ok"] is True
    assert "remaining content unavailable" in result["record"]["content"]
    assert result["warning"] == "partial synthetic read"
    assert json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()[0])["request"]["op"] == "read"


@pytest.mark.parametrize(
    ("case_id", "final"),
    [
        ("partly-readable-authority", "The record was incomplete; I used a disclosed one-time default. Nothing was saved."),
        ("copied-authority-not-replaced", "The selected authority could not be read. I did not use the backup. Nothing was saved."),
    ],
)
def test_unavailable_report_accepts_partial_and_unreadable_authority_language(tmp_path, case_id, final) -> None:
    root = tmp_path / case_id
    store = trial(root, case_id)
    control = json.loads((root / "control.json").read_text(encoding="utf-8"))
    read(store, control["initial"]["coding"])

    report = finish(root, final)

    assert report["status"] == "passed"


@pytest.mark.parametrize("final", [
    "I couldn't verify your saved Python preference because the record was incomplete.",
    "I couldn’t verify your saved Python preference because the record was incomplete.",
])
def test_unverified_preference_claim_with_ascii_or_curly_apostrophe_is_not_false_success(final) -> None:
    assert load("check_trial").record_claims_success(final) is False


def test_applying_a_saved_preference_is_not_a_claim_that_the_record_was_saved() -> None:
    checker = load("check_trial")
    assert checker.record_claims_success(
        "Applied the saved layout from fixture/library-a/coding; the preference is unchanged."
    ) is False
    assert checker.record_claims_success("I saved the requested coding preference.") is True
    assert checker.record_claims_success("I haven’t read, applied, or changed either value.") is False


def test_a_trailing_unverified_caveat_does_not_cancel_a_success_claim() -> None:
    checker = load("check_trial")
    assert checker.record_claims_success(
        "The preference was persisted at fixture/library-a/coding, but it remains unverified because the readback disagreed."
    )
    assert not checker.has_false_verified_target_claim(
        "The destination could not be verified because the readback failed.",
        {"destination", "fixture/repository-b/coding-new"},
    )


def test_created_authority_uses_the_trial_date_for_effective_and_update_metadata() -> None:
    checker = load("check_trial")
    content = (EVAL / "fixtures" / "coding-preferences-created.md").read_text(encoding="utf-8")
    assert checker.created_authority_content_matches(content, "2026-10-23")
    assert not checker.created_authority_content_matches(content, "2026-10-22")
    em_dash_content = content.replace(
        "- Last verified: 2026-10-23;", "- Last verified: 2026-10-23 —", 1
    )
    assert checker.created_authority_content_matches(em_dash_content, "2026-10-23")


def test_mcp_tools_are_scoped_to_the_public_case_and_annotated() -> None:
    module = load("store")
    public = {"tools": ["read", "write", "create"]}
    request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n"
    output = io.StringIO()
    with patch.object(module, "read_json", return_value=public), patch("sys.stdin", io.StringIO(request)), redirect_stdout(output):
        module.serve("unused", "session-1")
    tools = json.loads(output.getvalue())["result"]["tools"]
    assert [tool["name"] for tool in tools] == public["tools"]
    assert tools[0]["annotations"]["readOnlyHint"] is True
    assert tools[0]["annotations"]["destructiveHint"] is False
    assert tools[1]["annotations"]["readOnlyHint"] is False
    assert tools[1]["annotations"]["destructiveHint"] is True
    assert tools[2]["annotations"]["readOnlyHint"] is False
    assert tools[2]["annotations"]["destructiveHint"] is False


def test_authorized_update_requires_fresh_matching_readback_and_preserves_other_values(tmp_path) -> None:
    store = trial(tmp_path, "authorized-sql-update")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    record = state["coding"]
    assert read(store, record)["ok"]
    authorized_two_stage_update(store, record)

    report = finish(tmp_path, "Verified: I updated the selected SQL preference and read it back; the Python preference remains intact.")
    assert report["status"] == "passed", report


def test_new_authority_pending_state_can_retain_unverified_status_without_repeating_dates():
    content = (EVAL / "fixtures" / "coding-preferences-created-pending.md").read_text(encoding="utf-8")
    content = content.replace(
        "Pending fresh readback of the 2026-10-22 update; no prior verification",
        "Pending initial canonical readback",
    )
    assert load("check_trial").created_authority_pending_matches(content)


def test_authorized_update_rejects_stale_verification_metadata(tmp_path):
    store = trial(tmp_path, "authorized-sql-update")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    record = state["coding"]
    assert read(store, record)["ok"]
    pending = (tmp_path / "fixtures" / "coding-preferences-after-unverified.md").read_text(encoding="utf-8")
    assert store.call({
        "op": "write", "identity": identity(record), "revision": record["revision"], "content": pending,
    })["ok"]
    first_readback = read(store, record)
    assert first_readback["ok"]
    current = first_readback["record"]
    after = (tmp_path / "fixtures" / "coding-preferences-after.md").read_text(encoding="utf-8")
    stale = after.replace("Last verified: 2026-10-23;", "Last verified: 2026-10-01;")
    assert store.call({
        "op": "write", "identity": identity(current), "revision": current["revision"], "content": stale,
    })["ok"]
    assert read(store, current)["ok"]

    report = finish(tmp_path, "The SQL preference was updated and read back.")
    assert report["status"] == "failed"
    assert not report["checks"]["final_state"]["passed"]


def test_verified_dates_cannot_be_advanced_before_the_first_readback(tmp_path):
    store = trial(tmp_path, "authorized-sql-update")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    record = state["coding"]
    assert read(store, record)["ok"]
    final = (EVAL / "fixtures" / "coding-preferences-after.md").read_text(encoding="utf-8")
    assert store.call({
        "op": "write", "identity": identity(record), "revision": record["revision"], "content": final,
    })["ok"]
    first_readback = read(store, record)
    assert first_readback["ok"]
    current = first_readback["record"]
    assert store.call({
        "op": "write", "identity": identity(current), "revision": current["revision"], "content": final,
    })["ok"]
    assert read(store, current)["ok"]

    report = finish(tmp_path, "Verified: I updated and read back the selected SQL preference.")
    assert report["status"] == "failed"
    assert not report["checks"]["verification_staging"]["passed"]


def test_audit_write_requires_a_matching_readback_of_the_pending_value(tmp_path):
    store = trial(tmp_path, "authorized-sql-update")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    record = state["coding"]
    assert read(store, record)["ok"]
    pending = (EVAL / "fixtures" / "coding-preferences-after-unverified.md").read_text(encoding="utf-8")
    final = (EVAL / "fixtures" / "coding-preferences-after.md").read_text(encoding="utf-8")
    assert store.call({
        "op": "write", "identity": identity(record), "revision": record["revision"], "content": pending,
    })["ok"]
    first_write_state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))["coding"]
    assert store.call({
        "op": "write", "identity": identity(first_write_state), "revision": first_write_state["revision"], "content": final,
    })["ok"]
    assert read(store, first_write_state)["ok"]

    report = finish(tmp_path, "Verified: I updated and read back the selected SQL preference.")
    assert report["status"] == "failed"
    assert not report["checks"]["fresh_readback"]["passed"]


def test_trial_grading_uses_its_frozen_fixture_snapshot(tmp_path, monkeypatch):
    import shutil

    source_fixtures = tmp_path / "source-fixtures"
    shutil.copytree(EVAL / "fixtures", source_fixtures)
    store_module = load("store")
    monkeypatch.setattr(store_module, "FIXTURES", source_fixtures)
    trial_root = tmp_path / "trial"
    store_module.initialize(trial_root, "authorized-sql-update", candidate())
    store = store_module.Store(trial_root)
    state = json.loads((trial_root / "state.json").read_text(encoding="utf-8"))
    record = state["coding"]
    pending = (trial_root / "fixtures" / "coding-preferences-after-unverified.md").read_text(encoding="utf-8")
    pending = pending.replace("- Effective: 2026-10-23.", "- Effective: 2026-10-22.")

    (source_fixtures / "coding-preferences-after.md").write_text("changed after initialization", encoding="utf-8")
    assert read(store, record)["ok"]
    assert store.call({
        "op": "write", "identity": identity(record), "revision": record["revision"], "content": pending,
    })["ok"]
    first_readback = read(store, record)
    assert first_readback["ok"]
    current = first_readback["record"]
    final = (trial_root / "fixtures" / "coding-preferences-after.md").read_text(encoding="utf-8")
    final = final.replace("- Effective: 2026-10-23.", "- Effective: 2026-10-22.")
    assert store.call({
        "op": "write", "identity": identity(current), "revision": current["revision"], "content": final,
    })["ok"]
    assert read(store, current)["ok"]

    report = finish(trial_root, "Verified: I updated the selected SQL preference and read it back.")
    assert report["status"] == "passed", report


@pytest.mark.parametrize("case_id", [
    "one-time-override",
    "explicit-no-tool",
    "writing-context-unavailable",
    "skills-versus-instructions-explanation",
    "benchmark-explanation-no-trial",
    "unknown-memory-setup-neutral-fallback",
])
def test_task_only_cases_leave_all_persistent_state_unchanged(tmp_path, case_id):
    trial(tmp_path, case_id)
    report = finish(tmp_path, "I applied the request to this response only; I did not save a preference.")
    assert report["status"] == "passed", report
    assert report["checks"]["preservation"]["passed"]


def test_explanation_and_unknown_setup_cases_expose_no_tools() -> None:
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in manifest["cases"]}
    for case_id in (
        "skills-versus-instructions-explanation",
        "benchmark-explanation-no-trial",
        "unknown-memory-setup-neutral-fallback",
    ):
        assert cases[case_id]["public"]["tools"] == []
        assert cases[case_id]["report"] == "no-write"
        assert cases[case_id]["allowed_reads"] == []
        assert cases[case_id]["allowed_writes"] == []
        assert cases[case_id]["allowed_creates"] == []


def test_b2_chain_uses_new_sessions_and_narrower_read_only_tools() -> None:
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["id"] == "authorized-save-fresh-session-second-repository-chain")
    sessions = case["public"]["sessions"]

    assert [session["id"] for session in sessions] == ["session-1", "session-2", "session-3"]
    assert sessions[0]["tools"] == ["read", "write"]
    assert sessions[1]["tools"] == sessions[2]["tools"] == ["read"]
    assert case["public"]["tools"] == ["read", "write"]
    assert case["required_attempts"][-2:] == [
        {"op": "read", "record": "coding", "session": "session-2"},
        {"op": "read", "record": "coding", "session": "session-3"},
    ]
    assert "separate indented line" in sessions[0]["prompt"]
    assert case["expected"]["coding"]["content_file"] == "coding-preferences-after-sql-layout.md"
    assert set(case["expected_sql_layouts"]) == {"session-2", "session-3"}


def test_unknown_destination_requires_input_without_claiming_a_save(tmp_path):
    trial(tmp_path, "unknown-destination")
    report = finish(tmp_path, "Where would you like me to keep this coding preference?")
    assert report["status"] == "passed", report


def test_false_success_without_a_write_fails(tmp_path):
    trial(tmp_path, "unknown-destination")
    report = finish(tmp_path, "I saved your coding preference.")
    assert report["status"] == "failed"
    assert not report["checks"]["truthful_report"]["passed"]


def test_wrong_destination_attempt_is_rejected_and_fails_identity_scope(tmp_path):
    store = trial(tmp_path, "authorized-sql-update")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    wrong = {**identity(state["coding"]), "container": "library-b"}
    assert not store.call({"op": "read", "identity": wrong})["ok"]
    report = finish(tmp_path, "The selected destination could not be read, so no update was made.")
    assert report["status"] == "failed"
    assert not report["checks"]["identity_scope"]["passed"]


def test_wrong_final_content_fails_even_when_the_answer_claims_success(tmp_path):
    trial(tmp_path, "authorized-sql-update")
    report = finish(tmp_path, "Verified: I saved the requested SQL preference.")
    assert report["status"] == "failed"
    assert not report["checks"]["final_state"]["passed"]


def test_candidate_hash_mismatch_invalidates_the_trial(tmp_path):
    trial(tmp_path, "one-time-override")
    receipt_path = tmp_path / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["candidate_hash"] = "mismatched-candidate"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    report = finish(tmp_path, "Applied uppercase SQL for this response only; no preference was saved.")
    assert report["status"] == "failed"
    assert not report["checks"]["identity"]["passed"]


def test_missing_source_hash_invalidates_the_trial(tmp_path):
    trial(tmp_path, "one-time-override")
    receipt_path = tmp_path / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["source_hashes"].pop("adapter")
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    report = finish(tmp_path, "Applied uppercase SQL for this response only; no preference was saved.")
    assert report["status"] == "failed"
    assert not report["checks"]["identity"]["passed"]


def test_activated_invocation_capture_binds_candidate_prompt_command_and_runtime(tmp_path):
    capture = load("capture_invocation")
    root = tmp_path / "trial"
    trial(root, "fresh-session-reuse", evidence_kind="activated-skill")
    workspace = tmp_path / "workspace"
    candidate_hashes = json.loads((root / "candidate-hashes.json").read_text(encoding="utf-8"))
    repository = Path(__file__).resolve().parents[3]
    for relative in candidate_hashes:
        source = repository / relative
        destination = workspace / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    codex = tmp_path / "bin" / "codex"
    codex.parent.mkdir()
    codex.write_text(
        f"#!{sys.executable}\n"
        "import json, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "message = 'No preference was saved.'\n"
        "pathlib.Path(args[args.index('--output-last-message') + 1]).write_text(message)\n"
        "print(json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': message}}))\n"
        "print(json.dumps({'type': 'turn.completed'}))\n",
        encoding="utf-8",
    )
    codex.chmod(0o755)
    command = [
        str(codex), "--no-daemon", "--ask-for-approval", "never", "exec", "--json",
        "--output-last-message", str(root / "session-1.txt"),
        "--cd", str(workspace), "-",
    ]

    with patch.object(sys, "argv", [
        "capture_invocation.py", str(root), "--workspace", str(workspace),
        "--session", "session-1", "--execution-date", "2026-10-23", "--", *command,
    ]):
        assert capture.main() == 0

    public = json.loads((root / "public.json").read_text(encoding="utf-8"))
    runtime_bytes = (root / "runtime.jsonl").read_bytes()
    settings = {"command": command, "exit_code": 0, "execution_date": "2026-10-23"}
    checker = load("check_trial")
    assert checker.invocation_capture_matches(root, public, candidate_hashes, settings, runtime_bytes)
    (root / "agent-inputs" / "session-1.txt").write_text("different prompt\n", encoding="utf-8")
    assert not checker.invocation_capture_matches(root, public, candidate_hashes, settings, runtime_bytes)


def test_activated_candidate_workspace_must_not_inherit_repository_instructions(tmp_path):
    capture = load("capture_invocation")
    checker = load("check_trial")
    workspace = tmp_path / "candidate"
    workspace.mkdir()
    assert checker.candidate_workspace_isolated(workspace)
    assert not checker.candidate_workspace_isolated(ROOT)
    with pytest.raises(ValueError, match="outside the repository"):
        capture.validate_workspace(ROOT)
    (tmp_path / "AGENTS.md").write_text("inherited instructions", encoding="utf-8")
    assert not checker.candidate_workspace_isolated(workspace)
    with pytest.raises(ValueError, match="inherits AGENTS.md"):
        capture.validate_workspace(workspace)


def test_runtime_tool_trace_matches_call_counts_and_arguments_without_completion_order():
    checker = load("check_trial")
    read_call = {"server": "coding_fixture", "tool": "read", "arguments": {"id": "coding"}}
    write_call = {"server": "coding_fixture", "tool": "write", "arguments": {"id": "coding"}}
    assert checker.runtime_trace_matches_calls([write_call, read_call], [read_call, write_call])
    assert not checker.runtime_trace_matches_calls([read_call, read_call], [read_call, write_call])


def test_unexpected_non_mcp_runtime_item_types_are_not_allowlisted():
    checker = load("check_trial")
    runtime = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": "Done."}},
        {"type": "item.completed", "item": {"type": "reasoning", "text": "Checking."}},
        {"type": "item.started", "item": {"type": "command_execution", "command": "cat private.txt"}},
        {"type": "item.completed", "item": {"type": "file_change", "changes": []}},
        {"type": "item.started", "item": {"type": "web_search_call", "query": "private data"}},
        {"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "coding_fixture", "tool": "read"}},
        {"type": "item.completed", "item": {"type": ["malformed"]}},
    ]

    assert checker.unexpected_runtime_item_types(runtime) == [
        "command_execution", "file_change", "unknown", "web_search_call",
    ]


def test_runtime_tool_calls_in_chained_trials_keep_their_captured_session() -> None:
    checker = load("check_trial")
    first = json.dumps({"type": "item.completed", "item": {
        "type": "mcp_tool_call", "server": "coding_fixture", "tool": "read", "arguments": {"id": "one"},
    }}) + "\n"
    second = json.dumps({"type": "item.completed", "item": {
        "type": "mcp_tool_call", "server": "coding_fixture", "tool": "write", "arguments": {"id": "two"},
    }}) + "\n"
    runtime = (first + second).encode("utf-8")
    root = Path("/tmp/captured-sessions-test")
    capture = {
        "sessions": [
            {"id": "session-1", "runtime_start": 0, "runtime_end": len(first.encode("utf-8"))},
            {"id": "session-2", "runtime_start": len(first.encode("utf-8")), "runtime_end": len(runtime)},
        ]
    }
    with patch.object(checker, "read_json", return_value=capture):
        calls = checker.runtime_calls_by_captured_session(root, runtime)
    assert [call["source_session"] for call in calls] == ["session-1", "session-2"]


def test_activated_trial_without_an_actual_tool_event_fails(tmp_path):
    trial(tmp_path, "fresh-session-reuse", evidence_kind="activated-skill")
    final = "I used the saved uppercase SQL value for this query."
    (tmp_path / "final.txt").write_text(final, encoding="utf-8")
    (tmp_path / "runtime.jsonl").write_text(
        json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": final}})
        + "\n"
        + json.dumps({"type": "turn.completed"})
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "runtime-settings.json").write_text(json.dumps({
        "cli_version": "codex-cli test",
        "execution_date": "2026-10-23",
        "command": ["codex", "exec"],
        "requested": {"model": "test", "effort": "test"},
        "observed": {"model": "test", "effort": "test"},
        "available_tools": ["coding_fixture/read"],
        "exit_code": 0,
        "stderr": "",
        "preflight": "passed",
        "sandbox": "read-only",
        "approval_policy": "never",
        "web_search": "disabled",
        "server": {"name": "coding_fixture", "enabled_tools": ["read"]},
        "effective_features": {name: False for name in load("check_trial").REQUIRED_DISABLED_FEATURES},
    }), encoding="utf-8")
    load("store").snapshot(tmp_path)
    report = load("check_trial").check(tmp_path)
    assert report["status"] == "blocked"
    assert not report["checks"]["runtime"]["passed"]
    assert not report["checks"]["invocation_binding"]["passed"]
    assert not report["checks"]["available_operations"]["passed"]


def test_unexpected_runtime_server_blocks_behavior_claims(tmp_path):
    trial(tmp_path, "fresh-session-reuse", evidence_kind="activated-skill")
    final = "I used the saved uppercase SQL value for this query."
    runtime = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": final}},
        {"type": "item.completed", "item": {
            "type": "mcp_tool_call", "server": "codex", "tool": "list_mcp_resources",
            "arguments": {}, "status": "completed",
        }},
        {"type": "turn.completed"},
    ]
    (tmp_path / "final.txt").write_text(final, encoding="utf-8")
    (tmp_path / "runtime.jsonl").write_text("\n".join(json.dumps(event) for event in runtime) + "\n", encoding="utf-8")
    (tmp_path / "runtime-settings.json").write_text(json.dumps({
        "cli_version": "codex-cli test", "command": ["codex", "exec"],
        "requested": {"model": "test", "effort": "test"},
        "observed": {"model": "test", "effort": "test"},
        "available_tools": ["coding_fixture/read", "codex/list_mcp_resources"],
        "exit_code": 0, "stderr": "", "preflight": "blocked",
        "sandbox": "read-only", "approval_policy": "never", "web_search": "disabled",
        "server": {"name": "coding_fixture", "enabled_tools": ["read"]},
        "effective_features": {name: False for name in load("check_trial").REQUIRED_DISABLED_FEATURES},
    }), encoding="utf-8")
    load("store").snapshot(tmp_path)

    report = load("check_trial").check(tmp_path)
    assert report["status"] == "blocked"
    assert any("codex/list_mcp_resources" in reason for reason in report["blocked_reasons"])


def test_unexpected_non_mcp_tool_event_blocks_behavior_claims(tmp_path):
    trial(tmp_path, "fresh-session-reuse", evidence_kind="activated-skill")
    final = "I used the saved uppercase SQL value for this query."
    runtime = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": final}},
        {"type": "item.started", "item": {
            "type": "command_execution", "command": "cat another user file", "status": "in_progress",
        }},
        {"type": "item.completed", "item": {
            "type": "command_execution", "command": "cat another user file", "status": "completed",
        }},
        {"type": "turn.completed"},
    ]
    (tmp_path / "final.txt").write_text(final, encoding="utf-8")
    (tmp_path / "runtime.jsonl").write_text("\n".join(json.dumps(event) for event in runtime) + "\n", encoding="utf-8")
    (tmp_path / "runtime-settings.json").write_text(json.dumps({
        "cli_version": "codex-cli test", "execution_date": "2026-10-23", "command": ["codex", "exec"],
        "requested": {"model": "test", "effort": "test"}, "observed": {"model": "test", "effort": "test"},
        "available_tools": ["coding_fixture/read"], "exit_code": 0, "stderr": "", "preflight": "passed",
        "sandbox": "read-only", "approval_policy": "never", "web_search": "disabled",
        "server": {"name": "coding_fixture", "enabled_tools": ["read"]},
        "effective_features": {name: False for name in load("check_trial").REQUIRED_DISABLED_FEATURES},
    }), encoding="utf-8")
    load("store").snapshot(tmp_path)

    report = load("check_trial").check(tmp_path)
    assert report["status"] == "blocked"
    assert any("codex/command_execution" in reason for reason in report["blocked_reasons"])


def test_unavailable_authority_is_reported_without_a_claim_or_write(tmp_path):
    store = trial(tmp_path, "unavailable-authority")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert not read(store, state["coding"])["ok"]
    report = finish(tmp_path, "The selected authority is unavailable, so I did not use or change its value.")
    assert report["status"] == "passed", report


def test_ambiguous_authority_requires_choice_without_reading_candidate_values(tmp_path):
    store = trial(tmp_path, "ambiguous-authorities")
    result = store.call({"op": "list"})
    assert result["ok"] and len(result["records"]) == 2
    report = finish(tmp_path, "I found two matching authorities. Which one should I use?")
    assert report["status"] == "passed", report


def test_confirmed_missing_authority_can_be_created_and_verified(tmp_path):
    store = trial(tmp_path, "confirmed-missing-authority")
    assert store.call({"op": "list"})["records"] == []
    content = (EVAL / "fixtures" / "coding-preferences-created-pending.md").read_text(encoding="utf-8")
    created = {
        "provider": "fixture",
        "container": "library-a",
        "id": "coding",
        "path": "coding-preferences.md",
        "owner": "user",
        "content": content,
    }
    assert store.call({"op": "create", "record": created})["ok"]
    first_readback = read(store, created)
    assert first_readback["ok"]
    current = first_readback["record"]
    final = (EVAL / "fixtures" / "coding-preferences-created.md").read_text(encoding="utf-8")
    assert store.call({
        "op": "write", "identity": identity(current), "revision": current["revision"], "content": final,
    })["ok"]
    assert read(store, current)["ok"]
    report = finish(tmp_path, "Verified: I created the preference at the selected destination and checked the saved content.")
    assert report["status"] == "passed", report


def test_lost_acknowledgement_is_resolved_by_a_fresh_read(tmp_path):
    store = trial(tmp_path, "lost-write-acknowledgement")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    record = state["coding"]
    assert read(store, record)["ok"]
    pending = (EVAL / "fixtures" / "coding-preferences-after-unverified.md").read_text(encoding="utf-8")
    result = store.call({"op": "write", "identity": identity(record), "revision": record["revision"], "content": pending})
    assert not result["ok"] and "acknowledgement lost" in result["error"]
    first_readback = read(store, record)
    assert first_readback["ok"]
    current = first_readback["record"]
    after = (EVAL / "fixtures" / "coding-preferences-after.md").read_text(encoding="utf-8")
    result = store.call({"op": "write", "identity": identity(current), "revision": current["revision"], "content": after})
    assert not result["ok"] and "acknowledgement lost" in result["error"]
    assert read(store, current)["ok"]
    report = finish(tmp_path, "Verified: a fresh read shows the requested SQL value and preserves the Python entry.")
    assert report["status"] == "passed", report


@pytest.mark.parametrize("case_id", ["write-readback-unavailable", "write-readback-mismatch"])
def test_failed_or_mismatched_readback_requires_an_unverified_report(tmp_path, case_id):
    store = trial(tmp_path, case_id)
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    record = state["coding"]
    assert read(store, record)["ok"]
    after = (EVAL / "fixtures" / "coding-preferences-after-unverified.md").read_text(encoding="utf-8")
    assert store.call({"op": "write", "identity": identity(record), "revision": record["revision"], "content": after})["ok"]
    readback = read(store, record)
    if case_id.endswith("unavailable"):
        assert not readback["ok"]
    else:
        assert readback["ok"] and readback["record"]["content"] != after
    report = finish(tmp_path, "The write may have committed, but I could not verify it. Its status is unverified.")
    assert report["status"] == "passed", report


def test_unverified_report_rejects_a_success_claim_before_its_caveat(tmp_path):
    store = trial(tmp_path, "write-readback-mismatch")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    record = state["coding"]
    assert read(store, record)["ok"]
    after = (EVAL / "fixtures" / "coding-preferences-after-unverified.md").read_text(encoding="utf-8")
    assert store.call({
        "op": "write", "identity": identity(record), "revision": record["revision"], "content": after,
    })["ok"]
    assert read(store, record)["ok"]

    report = finish(
        tmp_path,
        "The preference was persisted at fixture/library-a/coding, but it remains unverified because the readback disagreed.",
    )

    assert report["status"] == "failed"
    assert not report["checks"]["truthful_report"]["passed"]


@pytest.mark.parametrize(("field", "value"), [("owner", "someone-else"), ("path", "other.md")])
def test_write_readback_must_match_owner_and_path(tmp_path, field, value):
    store = trial(tmp_path, "authorized-sql-update")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    authorized_two_stage_update(store, state["coding"])
    events_path = tmp_path / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    readback = next(
        event for event in reversed(events)
        if event.get("record_id") == "coding"
        and event.get("request", {}).get("op") == "read"
        and event.get("result", {}).get("ok")
    )
    readback["result"]["record"][field] = value
    events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    report = finish(tmp_path, "Verified: I saved the requested SQL preference.")

    assert report["status"] == "failed"
    assert not report["checks"]["fresh_readback"]["passed"]


def test_unverified_write_cannot_be_reported_as_verified(tmp_path):
    store = trial(tmp_path, "write-readback-unavailable")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    record = state["coding"]
    read(store, record)
    after = (EVAL / "fixtures" / "coding-preferences-after-unverified.md").read_text(encoding="utf-8")
    store.call({"op": "write", "identity": identity(record), "revision": record["revision"], "content": after})
    read(store, record)
    report = finish(tmp_path, "I successfully saved your coding preference.")
    assert report["status"] == "failed"
    assert not report["checks"]["truthful_report"]["passed"]


def test_transfer_report_cannot_claim_unread_destination_was_verified(tmp_path):
    store = trial(tmp_path, "remember-me-transfer-destination-readback-unavailable")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    source = state["coding"]
    locator = state["locator"]
    assert read(store, source)["ok"]
    assert read(store, locator)["ok"]
    destination = {
        "provider": "fixture",
        "container": "repository-b",
        "id": "coding-new",
        "path": "coding-preferences.md",
        "owner": "user",
        "content": transfer_pending_content(),
    }
    assert store.call({"op": "create", "record": destination})["ok"]
    assert not read(store, destination)["ok"]

    report = finish(
        tmp_path,
        "The destination fixture/repository-b/coding-new was verified through readback, but its status remains unverified.",
    )

    assert report["status"] == "failed"
    assert not report["checks"]["truthful_report"]["passed"]


def test_pending_readback_metadata_allows_equivalent_prior_verification_wording(tmp_path):
    store = trial(tmp_path, "write-readback-unavailable")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    record = state["coding"]
    read(store, record)
    content = (EVAL / "fixtures" / "coding-preferences-after-unverified.md").read_text(encoding="utf-8")
    content = content.replace("previous verification: 2026-10-01", "prior verification: 2026-10-01")
    content = content.replace(
        "uppercase update explicitly authorized by the user on 2026-10-23 for fixture/library-a/coding",
        "updated to uppercase by explicit user authorization on 2026-10-23",
    )
    assert store.call({
        "op": "write", "identity": identity(record), "revision": record["revision"], "content": content,
    })["ok"]
    read(store, record)
    report = finish(tmp_path, "The value was updated, but fresh readback is unavailable; the update remains unverified.")
    assert report["status"] == "passed", report


def test_concurrent_conflict_is_preserved_and_requests_user_resolution(tmp_path):
    store = trial(tmp_path, "concurrent-preference-conflict")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    record = state["coding"]
    assert read(store, record)["ok"]
    after = (EVAL / "fixtures" / "coding-preferences-after.md").read_text(encoding="utf-8")
    assert not store.call({"op": "write", "identity": identity(record), "revision": record["revision"], "content": after})["ok"]
    current = read(store, record)
    assert current["ok"] and "newer user correction" in current["record"]["content"].lower()
    report = finish(tmp_path, "A newer conflicting value appeared during the update. Which SQL preference should I keep?")
    assert report["status"] == "passed", report


@pytest.mark.parametrize("status", ["Partial transfer:", "Transfer incomplete:"])
def test_transfer_reports_partial_when_old_locator_reconciliation_fails(tmp_path, status):
    store = trial(tmp_path, "remember-me-transfer-pointer-failure")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    source = state["coding"]
    locator = state["locator"]
    assert read(store, source)["ok"]
    assert read(store, locator)["ok"]
    created = {"provider": "fixture", "container": "repository-b", "id": "coding-new"}
    create_verified_transfer_target(store, created)
    assert not store.call({
        "op": "write", "identity": identity(locator), "revision": locator["revision"],
        "content": "fixture/repository-b/coding-new",
    })["ok"]
    report = finish(tmp_path, f"{status} the new destination is verified, but the old locator remains unchanged and recoverable.")
    assert report["status"] == "passed", report


def test_transfer_checks_exact_missing_destination_before_create(tmp_path):
    trial_root = tmp_path / "transfer-destination-check"
    store = trial(trial_root, "remember-me-transfer-pointer-success")
    source = {
        "provider": "fixture", "container": "library-a", "id": "coding",
    }
    locator = {
        "provider": "fixture", "container": "library-a", "id": "locator",
    }
    destination = {
        "provider": "fixture", "container": "repository-b", "id": "coding-new",
    }
    assert not store.call({"op": "read", "identity": destination})["ok"]
    assert store.call({"op": "read", "identity": source})["ok"]
    store.call({"op": "read", "identity": locator})
    create_verified_transfer_target(store, destination)
    pointer = store.call({"op": "read", "identity": locator})["record"]
    assert store.call({
        "op": "write", "identity": locator, "revision": pointer["revision"],
        "content": "fixture/repository-b/coding-new",
    })["ok"]
    assert store.call({"op": "read", "identity": locator})["ok"]

    report = finish(trial_root, "The destination and routing pointer are verified; the source remains unchanged.")
    assert report["status"] == "passed", report


@pytest.mark.parametrize("final", [
    "Partial transfer: the destination is verified. The old locator was persisted successfully, but the result is partial.",
    "Partial transfer: the destination is verified. The pointer update succeeded, but the result is partial.",
    "Partial transfer: the destination is verified. The pointer now points to the new authority.",
    "Partial transfer: the destination is verified. The pointer still points to the new authority.",
    "Partial transfer: the destination is verified. The pointer is set to the new authority.",
    "Partial transfer: the destination is verified. The pointer was redirected to repository-b.",
    "Partial transfer: the destination is verified. Routing metadata now references the selected destination.",
    "Partial transfer: the destination is verified. The pointer now contains fixture/repository-b/coding-new.",
    "Partial transfer: the destination is verified. The pointer value is fixture/repository-b/coding-new.",
    "Partial transfer: the destination is verified. The pointer is now on repository-b.",
    "Partial transfer: the destination is verified. The pointer destination is the new authority.",
    "Partial transfer: the destination is verified. The pointer identifies repository-b/coding-new.",
    "Partial transfer: the destination is verified. The pointer is the new authority.",
    "Partial transfer: the destination is verified. The pointer is fixture/repository-b/coding-new.",
    "Partial transfer: the destination is verified. The pointer names the new authority.",
    "Partial transfer: the destination is verified. The pointer designates repository-b/coding-new.",
    "Partial transfer: the destination is verified. The pointer is configured for the replacement authority.",
    "Partial transfer: the destination is verified. The pointer still points to the destination.",
])
def test_transfer_rejects_persistence_claim_for_rejected_locator_write(tmp_path, final):
    store = trial(tmp_path, "remember-me-transfer-pointer-failure")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    source = state["coding"]
    locator = state["locator"]
    assert read(store, source)["ok"]
    assert read(store, locator)["ok"]
    created = {"provider": "fixture", "container": "repository-b", "id": "coding-new"}
    create_verified_transfer_target(store, created)
    assert not store.call({
        "op": "write", "identity": identity(locator), "revision": locator["revision"],
        "content": "fixture/repository-b/coding-new",
    })["ok"]
    report = finish(tmp_path, final)
    assert report["status"] == "failed"
    assert report["failed_checks"] == ["truthful_report"]


@pytest.mark.parametrize("routing_claim", [
    "the pointer still points to the original authority",
    "routing metadata still references the current authority",
    "the pointer still points to the original authority rather than the new destination",
    "the pointer still points to the original authority instead of the selected destination",
    "the pointer points to fixture/library-a/coding, not fixture/repository-b/coding-new",
    "the pointer is intended to point to the new authority, but the update failed",
    "the pointer would point to the new authority if reconciliation succeeded",
    "the pointer will point to the new authority after the next authorized update",
    "the pointer still points to the old destination",
    "the pointer still points to the original destination, not the new one",
    "the pointer still points to the current target",
    "the pointer still points to the old target rather than the replacement",
])
def test_transfer_accepts_truthful_pointer_destination_claim(tmp_path, routing_claim):
    store = trial(tmp_path, "remember-me-transfer-pointer-failure")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    source = state["coding"]
    locator = state["locator"]
    assert read(store, source)["ok"]
    assert read(store, locator)["ok"]
    created = {"provider": "fixture", "container": "repository-b", "id": "coding-new"}
    create_verified_transfer_target(store, created)
    assert not store.call({
        "op": "write", "identity": identity(locator), "revision": locator["revision"],
        "content": "fixture/repository-b/coding-new",
    })["ok"]
    report = finish(
        tmp_path,
        f"Partial transfer: the destination is verified, but {routing_claim}.",
    )
    assert report["status"] == "passed", report


def test_transfer_rejects_locator_write_before_destination_readback(tmp_path):
    store = trial(tmp_path, "remember-me-transfer-pointer-failure")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    source = state["coding"]
    locator = state["locator"]
    assert read(store, source)["ok"]
    assert read(store, locator)["ok"]
    created = {
        "provider": "fixture",
        "container": "repository-b",
        "id": "coding-new",
        "path": "coding-preferences.md",
        "owner": "user",
        "content": transfer_pending_content(),
    }
    assert store.call({"op": "create", "record": created})["ok"]
    first_readback = read(store, created)
    assert first_readback["ok"]
    current = first_readback["record"]
    assert store.call({
        "op": "write", "identity": identity(current), "revision": current["revision"],
        "content": transfer_target_content(),
    })["ok"]
    assert not store.call({
        "op": "write", "identity": identity(locator), "revision": locator["revision"],
        "content": "fixture/repository-b/coding-new",
    })["ok"]
    assert read(store, current)["ok"]
    report = finish(tmp_path, "Partial transfer: the new destination is verified, but the old locator remains unchanged and recoverable.")
    assert report["status"] == "failed"
    assert "available_operations" in report["failed_checks"]


def test_incomplete_trial_evidence_is_blocked(tmp_path):
    trial(tmp_path, "authorized-sql-update")
    report = load("check_trial").check(tmp_path)
    assert report["status"] == "blocked"
    assert "final-state.json" in report["missing"]
