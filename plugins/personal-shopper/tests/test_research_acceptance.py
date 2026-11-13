"""Offline controls for source-retrieval trials; these are not activated passes."""

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from math import ceil

import pytest

from shopping_test_support import EVAL, ROOT, load_runner, load_scorer, load_store


RESEARCH_CASES = {
    "B13-AE13", "B13-primary-unavailable", "B14-AE14", "B14-service-priorities",
    "B14-product-alternatives", "B15-AE15", "B15-qualification-unavailable",
    "B16-AE16", "B16-missing-jurisdiction", "B17-AE17", "B17-insufficient-class",
    "B18-AE18", "B18-task-only",
}


def test_research_instruction_reader_allows_hashed_links_but_not_other_packages_or_credentials(tmp_path):
    import importlib.util
    runner = load_runner()
    package = tmp_path / "installed"
    skill = package / "skills" / "personal-shopper"
    skill.mkdir(parents=True)
    identity = {}
    for name, content in (("SKILL.md", "Read linked.md"), ("linked.md", "linked instructions")):
        path = skill / name
        path.write_text(content)
        identity[f"personal-shopper/skills/personal-shopper/{name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    identity["personal-shopper/auth.json"] = "not-a-resource"
    identity["other/skills/private.md"] = "not-a-resource"
    home = tmp_path / "home"
    home.mkdir()
    required = ["personal-shopper/skills/personal-shopper/SKILL.md"]
    runner._register_integration_reader(home, {"personal-shopper": package}, identity, tmp_path,
                                        required, include_package_references=True)
    control = read(tmp_path / "skill-resource-config.json")
    spec = importlib.util.spec_from_file_location("research_resource_reader", EVAL / "skill_resources.py")
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    result = reader.read_resource(control, {"package": "personal-shopper", "relative_path": "skills/personal-shopper/linked.md"})
    assert result["text"] == "linked instructions"
    for arguments in ({"package": "personal-shopper", "relative_path": "auth.json"},
                      {"package": "other", "relative_path": "skills/private.md"}):
        with pytest.raises(ValueError):
            reader.read_resource(control, arguments)
    runner._register_integration_reader(home, {"personal-shopper": package}, identity, tmp_path, required)
    with pytest.raises(ValueError):
        reader.read_resource(read(tmp_path / "skill-resource-config.json"),
                             {"package": "personal-shopper", "relative_path": "skills/personal-shopper/linked.md"})


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def subcase(case_id):
    manifest = read(EVAL / "manifest.json")
    return next(case for case in manifest["synthetic_subcases"] if case["id"] == case_id)


def trial(tmp_path, case_id):
    module = load_store()
    case = subcase(case_id)
    root = module.initialize(tmp_path / "fixture", case["fixture_id"], case["tools"],
                             faults=case.get("faults", {}))
    return module, module.Store(root), root


def events(root):
    return [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]


def retrieve_required(store, root, *, source_order=None):
    control = read(root / "control.json")
    expected = control["expected"]
    declared = expected.get("required_source_ids", []) + expected.get("unavailable_source_ids", [])
    if source_order is None:
        source_ids = list(declared)
        first = expected.get("first_source_id")
        if first:
            source_ids = [first, *(source_id for source_id in source_ids if source_id != first)]
    else:
        source_ids = list(source_order)
        assert len(source_ids) == len(set(source_ids))
        assert set(source_ids) == set(declared)
    for source_id in source_ids:
        store.call(source_id, "retrieve_source", {"source_id": source_id})


def test_research_cases_are_separate_and_bind_their_controls():
    manifest = read(EVAL / "manifest.json")
    declared = {case["id"] for case in manifest["synthetic_subcases"]}
    assert RESEARCH_CASES <= declared
    assert "plugins/personal-shopper/tests/test_research_acceptance.py" in manifest["suite_identity_files"]
    for case_id in RESEARCH_CASES:
        case = subcase(case_id)
        assert case["profile"] == "shopper-alone"
        assert case["group"] == case_id.split("-", 1)[0]
        assert "personal-shopper/skills/personal-shopper/SKILL.md" in case["required_skill_resources"]
        assert not case.get("additional_skills")
    # The pre-existing historical/deferred cases remain separately declared.
    assert {"B1-AE3", "B4-AE5", "B10-AE12-new-plan"} <= declared


def test_source_bodies_and_expected_answers_are_not_in_public_context(tmp_path):
    module, store, root = trial(tmp_path, "B13-AE13")
    public = read(root / "public.json")
    control = read(root / "control.json")
    assert "sources" not in public and "expected" not in public
    assert "sources" in control and "expected" in control
    context, _ = store.call("context", "get_case_context", {})
    assert context["context"]["source_index"]
    task = module.render_task(subcase("B13-AE13")["fixture_id"])
    for source in control["sources"].values():
        assert json.dumps(source["content"], ensure_ascii=False) not in task
    assert "expected" not in context["context"]


def test_retrieval_returns_exact_source_identity_without_changing_state(tmp_path):
    module, store, root = trial(tmp_path, "B13-AE13")
    before = read(root / "state.json")
    control = read(root / "control.json")
    source_id = control["expected"]["required_source_ids"][0]
    result, attempted_write = store.call("source", "retrieve_source", {"source_id": source_id})
    assert result["ok"] is True
    assert result["source"] == control["sources"][source_id]
    canonical = json.dumps(result["source"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    assert result["source_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert attempted_write is False and read(root / "state.json") == before
    event = events(root)[-1]
    assert event["state_before_sha256"] == event["state_after_sha256"]
    assert event["committed"] is False


@pytest.mark.parametrize("arguments", [{}, {"source_id": 12}, {"source_id": "other-case-source"},
                                         {"source_id": "bolt-maker", "url": "https://unrelated.invalid"}])
def test_retrieval_rejects_missing_unknown_or_extra_selectors(tmp_path, arguments):
    _, store, root = trial(tmp_path, "B13-AE13")
    result, attempted = store.call("denied", "retrieve_source", arguments)
    assert result["ok"] is False and attempted is False
    assert events(root)[-1]["state_before_sha256"] == events(root)[-1]["state_after_sha256"]


def test_source_tool_cannot_bypass_the_case_tool_allowlist(tmp_path):
    module = load_store()
    root = module.initialize(tmp_path / "fixture", "AE3", ["get_case_context"])
    result, attempted = module.Store(root).call("denied", "retrieve_source", {"source_id": "bolt-maker"})
    assert result["ok"] is False and "not enabled" in result["error"]
    assert attempted is False


def test_unavailable_primary_is_a_recorded_failure_not_an_empty_specification(tmp_path):
    _, store, root = trial(tmp_path, "B13-primary-unavailable")
    source_id = read(root / "control.json")["expected"]["unavailable_source_ids"][0]
    result, _ = store.call("unavailable", "retrieve_source", {"source_id": source_id})
    assert result["ok"] is False and result["error"] == "source_unavailable"
    assert result["source_id"] == source_id and "source" not in result


@pytest.mark.parametrize("case_id", sorted(RESEARCH_CASES - {"B18-AE18"}))
def test_research_checks_require_the_declared_reads_and_preserve_task_state(tmp_path, case_id):
    module, store, root = trial(tmp_path, case_id)
    scorer = load_scorer()
    control = read(root / "control.json")
    if control["expected"].get("required_source_ids") or control["expected"].get("unavailable_source_ids"):
        missing = scorer._case_checks(case_id, read(root / "state.json"), [], control)
        assert missing and not all(missing.values())
    retrieve_required(store, root)
    checks = scorer._case_checks(case_id, module.snapshot(root), events(root), control)
    assert checks and all(checks.values())
    if case_id in {"B13-AE13", "B13-primary-unavailable"}:
        assert checks["manufacturer_retrieved_before_secondary_sources"] is True


@pytest.mark.parametrize(("case_id", "source_order"), [
    ("B13-AE13", ["bolt-offer-20", "bolt-maker", "bolt-offer-5", "bolt-conflict"]),
    ("B13-primary-unavailable", ["secondary-bolt", "maker-offline"]),
], ids=["available-manufacturer", "unavailable-manufacturer"])
def test_manufacturer_order_control_rejects_secondary_first_with_complete_valid_reads(
    tmp_path, case_id, source_order,
):
    module, store, root = trial(tmp_path, case_id)
    control = read(root / "control.json")
    retrieve_required(store, root, source_order=source_order)

    checks = load_scorer()._case_checks(case_id, module.snapshot(root), events(root), control)

    assert checks["required_research_sources_observed"] is True
    assert checks["required_unavailable_sources_observed"] is True
    assert checks["retrieved_source_identity_and_bytes_match"] is True
    assert checks["source_reads_leave_shopping_state_unchanged"] is True
    assert checks["research_does_not_write_records"] is True
    assert checks["manufacturer_retrieved_before_secondary_sources"] is False
    assert all(
        result for name, result in checks.items()
        if name != "manufacturer_retrieved_before_secondary_sources"
    )


def test_forged_source_body_and_undeclared_source_attempt_fail_reconciliation(tmp_path):
    module, store, root = trial(tmp_path, "B13-AE13")
    retrieve_required(store, root)
    scorer = load_scorer()
    control = read(root / "control.json")
    trace = events(root)
    trace[0]["result"]["source"]["content"] = {"invented": "manufacturer says compatible"}
    trace[0]["result"]["source_sha256"] = module._json_hash(trace[0]["result"]["source"])
    assert not all(scorer._case_checks("B13-AE13", module.snapshot(root), trace, control).values())
    store.call("unknown", "retrieve_source", {"source_id": "other-case-source"})
    assert not all(scorer._case_checks("B13-AE13", module.snapshot(root), events(root), control).values())


def test_host_reconciliation_checks_source_arguments_and_returned_bytes(tmp_path):
    _, store, root = trial(tmp_path, "B13-AE13")
    retrieve_required(store, root)
    trace = events(root)
    calls = [{"server": "shopping-fixture", "tool": event["tool"], "status": "completed",
              "arguments": event["arguments"],
              "result": {**event["result"], "fixture_event_id": event["event_id"]}}
             for event in trace]
    scorer = load_scorer()
    assert scorer._fixture_calls_reconcile(calls, [], trace)
    forged = deepcopy(calls)
    forged[0]["result"]["source"]["title"] = "unobserved source"
    assert not scorer._fixture_calls_reconcile(forged, [], trace)
    assert not scorer._fixture_calls_reconcile(calls[:-1], [], trace)


def test_research_reconciliation_binds_failed_source_results_without_accepting_failed_successes(tmp_path):
    _, store, root = trial(tmp_path, "B13-primary-unavailable")
    retrieve_required(store, root)
    trace = events(root)
    calls = [{"server": "shopping-fixture", "tool": event["tool"],
              "status": "completed" if event["result"].get("ok") else "failed",
              "arguments": event["arguments"],
              "result": {**event["result"], "fixture_event_id": event["event_id"]}}
             for event in trace]
    reconcile = load_scorer()._fixture_calls_reconcile
    assert reconcile(calls, [], trace, allow_failed_results=True)
    assert not reconcile(calls, [], trace)
    successful = next(call for call in calls if call["status"] == "completed")
    successful["status"] = "failed"
    assert not reconcile(calls, [], trace, allow_failed_results=True)


def control_capture(tmp_path, mutation=None):
    """Reconstruct deterministic checker input; never claim this is activation."""
    scorer = load_scorer()
    manifest = read(EVAL / "manifest.json")
    case = subcase("B13-AE13")
    directory = tmp_path / "checker-control"
    directory.mkdir(mode=0o700)
    module = load_store()
    fixture = module.initialize(directory / "fixture-store", case["fixture_id"], case["tools"])
    store = module.Store(fixture)
    retrieve_required(store, fixture)
    final_state = module.snapshot(fixture)
    fixture_events = events(fixture)
    installed = scorer.capture.local_profile_file_hashes(ROOT.parents[1], manifest, "shopper-alone")
    calls = []
    for qualified in case["required_skill_resources"]:
        package, relative = qualified.split("/", 1)
        payload = {"package": package, "relative_path": relative, "sha256": installed[qualified],
                   "text": (ROOT / relative).read_text(encoding="utf-8")}
        calls.append({"server": "shopping-skill-resources", "tool": "read_installed_skill_file",
                      "arguments": {"package": package, "relative_path": relative},
                      "result": {"structuredContent": payload}})
    for event in fixture_events:
        calls.append({"server": "shopping-fixture", "tool": event["tool"],
                      "arguments": event["arguments"],
                      "result": {**event["result"], "fixture_event_id": event["event_id"]}})
    if mutation == "omitted-source":
        calls.pop()
    elif mutation == "changed-source":
        calls[-1]["result"]["source"]["content"] = {"invented": "model-generated evidence"}
    elif mutation == "missing-instructions":
        calls = [call for call in calls if call["server"] != "shopping-skill-resources"]
    host = [{"type": "thread.started"}]
    for index, call in enumerate(calls):
        host.append({"type": "item.completed", "item": {
            "type": "mcp_tool_call", "id": f"checker-control-{index}", "status": "completed", **call,
        }})
    host.append({"type": "item.completed", "item": {
        "type": "agent_message", "text": "Deterministic scorer control only. The wrong unit price is $12 per bolt.",
    }})
    host.append({"type": "turn.completed"})
    trace = "".join(json.dumps(event) + "\n" for event in host).encode()
    (directory / "host-events.jsonl").write_bytes(trace)
    result = {
        "evidence_kind": "deterministic-control",
        "complete": True, "trial_status": "captured", "event_count": len(host),
        "tool_call_count": len(calls), "trace_sha256": hashlib.sha256(trace).hexdigest(),
        "profile_id": "shopper-alone", "skill_id": "personal-shopper:personal-shopper",
        "requested_skill_ids": ["personal-shopper:personal-shopper"],
        "candidate_profile_unchanged": True, "source_candidate_unchanged": True,
        "suite_identity_unchanged": True, "installed_file_sha256": installed,
        "source_candidate_sha256_after": scorer.capture.identity_digest(
            ROOT.parents[1], scorer.capture.candidate_identity_patterns(manifest)),
        "suite_sha256_after": scorer.capture.identity_digest(ROOT.parents[1], manifest["suite_identity_files"]),
        "fixture": {"subcase_id": case["id"], "event_count": len(fixture_events),
                    "state_sha256_before": scorer._state_digest(read(fixture / "initial-state.json")),
                    "state_sha256_after": scorer._state_digest(final_state)},
    }
    if mutation == "wrong-activation":
        result["skill_id"] = "unrelated:skill"
    elif mutation == "stale-suite":
        result["suite_sha256_after"] = "0" * 64
    (directory / "trial-result.json").write_text(json.dumps(result), encoding="utf-8")
    (directory / "runtime-settings.json").write_text(json.dumps({
        "command": scorer.capture.build_codex_command("/tmp/checker-control", apps_enabled=False),
        "multi_agent_enabled": False, "persist_rollouts": False,
        "sandbox": "read-only", "provider_apps": [],
    }), encoding="utf-8")
    return scorer.score_trial(directory)


def test_complete_research_trace_is_machine_ready_but_wrong_math_is_not_semantic_acceptance(tmp_path):
    score = control_capture(tmp_path)
    assert score["machine_status"] == "ready-for-semantic-review"
    assert score["semantic_review"] == "pending"
    assert score["acceptance"] == "not-accepted"


@pytest.mark.parametrize("mutation,failed_check", [
    ("omitted-source", "host_and_fixture_calls_reconcile"),
    ("changed-source", "host_and_fixture_calls_reconcile"),
    ("missing-instructions", "required_installed_contracts_observed"),
    ("wrong-activation", "activation_route_matches_profile"),
    ("stale-suite", "identities_stable"),
])
def test_research_trace_controls_fail_closed_for_missing_or_fabricated_evidence(tmp_path, mutation, failed_check):
    score = control_capture(tmp_path, mutation)
    assert score["machine_status"] == "failed"
    assert score["machine_checks"][failed_check] is False
    assert score["acceptance"] == "not-accepted"


def test_changed_controller_source_cannot_make_fabricated_evidence_current(tmp_path):
    module, store, root = trial(tmp_path, "B13-AE13")
    retrieve_required(store, root)
    control = read(root / "control.json")
    trace = events(root)
    source_id = trace[0]["arguments"]["source_id"]
    control["sources"][source_id]["content"] = {"invented": "new primary specification"}
    trace[0]["result"] = {"ok": True, "source": control["sources"][source_id],
                          "source_sha256": module._json_hash(control["sources"][source_id])}
    checks = load_scorer()._case_checks("B13-AE13", module.snapshot(root), trace, control)
    assert checks["research_control_matches_frozen_fixture"] is False


def test_malformed_source_envelope_cannot_return_evidence(tmp_path, monkeypatch):
    module = load_store()
    case_id = subcase("B13-AE13")["fixture_id"]
    case = module._case(case_id)
    del case["sources"]["bolt-maker"]["kind"]
    monkeypatch.setattr(module, "_case", lambda _: case)
    root = module.initialize(tmp_path / "fixture", case_id, ["retrieve_source"])
    result, _ = module.Store(root).call("malformed", "retrieve_source", {"source_id": "bolt-maker"})
    assert result == {"ok": False, "error": "malformed_source", "source_id": "bolt-maker"}


def test_reference_class_arithmetic_is_independently_reproducible():
    module = load_store()
    case = module._case(subcase("B17-AE17")["fixture_id"])
    source_id = case["expected"]["required_source_ids"][0]
    observations = case["sources"][source_id]["content"]["projects"]
    ratios = sorted(Decimal(str(row["final_cost"])) / Decimal(str(row["original_base"]))
                    for row in observations)
    assert len(ratios) == 20
    assert ratios == [Decimal("0.80") + Decimal("0.05") * i for i in range(20)]
    assert ratios[ceil(Decimal("0.50") * len(ratios)) - 1] * Decimal(10000) == Decimal(12500)
    assert ratios[ceil(Decimal("0.80") * len(ratios)) - 1] * Decimal(10000) == Decimal(15500)


def test_matching_bolt_unit_price_is_not_the_lowest_pack_price():
    module = load_store()
    case = module._case(subcase("B13-AE13")["fixture_id"])
    offers = [source["content"] for source in case["sources"].values() if source["kind"] == "retail_offer"]
    matching = [offer for offer in offers if offer["model"] == "MX-1050-88-Z"
                and offer["pitch_mm"] == 1.5 and offer["property_class"] == "8.8"
                and offer["coating"] == "zinc plated"]
    assert sorted(Decimal(str(offer["package_price"])) / offer["pack_quantity"] for offer in matching) == [Decimal("0.60"), Decimal("0.80")]


def test_service_preference_readback_is_required_and_history_failure_stays_incomplete(tmp_path):
    module, store, root = trial(tmp_path, "B18-AE18")
    state = read(root / "state.json")
    spreadsheet_id = state["spreadsheet_id"]
    store.call("metadata", "get_spreadsheet_metadata", {"spreadsheet_id": spreadsheet_id})
    for range_value in ("'Record Index'!A1:D3", "'Shopping Rules'!A1:G2", "'Shopping History'!A1:G1"):
        store.call(range_value, "get_spreadsheet_range", {"spreadsheet_id": spreadsheet_id, "range": range_value})
    store.call("current", "batch_update_spreadsheet", {"spreadsheet_id": spreadsheet_id, "updates": [
        {"range": "'Shopping Rules'!B2:B2", "values": [["written change orders required"]]}]})
    store.call("history", "batch_update_spreadsheet", {"spreadsheet_id": spreadsheet_id, "updates": [
        {"range": "'Shopping History'!A2:G2", "values": [["H-SERVICE-1", "2026-11-05", "verbal changes acceptable", "written change orders required", "user confirmed", "current task", "SERVICE-RULE-1"]]}]})
    store.call("history-read", "get_spreadsheet_range", {"spreadsheet_id": spreadsheet_id, "range": "'Shopping History'!A1:G2"})
    scorer = load_scorer()
    control = read(root / "control.json")
    assert not all(scorer._case_checks("B18-AE18", module.snapshot(root), events(root), control).values())
    store.call("current-read", "get_spreadsheet_range", {"spreadsheet_id": spreadsheet_id, "range": "'Shopping Rules'!A1:G2"})
    assert all(scorer._case_checks("B18-AE18", module.snapshot(root), events(root), control).values())


def test_service_preference_combined_authorized_write_is_accepted(tmp_path):
    module, store, root = trial(tmp_path, "B18-AE18")
    state = read(root / "state.json")
    spreadsheet_id = state["spreadsheet_id"]
    store.call("metadata", "get_spreadsheet_metadata", {"spreadsheet_id": spreadsheet_id})
    for range_value in ("'Record Index'!A1:D3", "'Shopping Rules'!A1:G2", "'Shopping History'!A1:G1"):
        store.call(range_value, "get_spreadsheet_range", {"spreadsheet_id": spreadsheet_id, "range": range_value})
    store.call("combined", "batch_update_spreadsheet", {"spreadsheet_id": spreadsheet_id, "updates": [
        {"range": "'Shopping Rules'!B2", "values": [["written change orders required"]]},
        {"range": "'Shopping Rules'!D2", "values": [["2026-11-05"]]},
        {"range": "'Shopping Rules'!F2", "values": [["current user request"]]},
        {"range": "'Shopping History'!A2:G2", "values": [[
            "MH-2026-11-05-SERVICE-RULE-1", "2026-11-05", "verbal changes acceptable",
            "written change orders required", "Confirmed contractor preference correction",
            "current user request", "SERVICE-RULE-1",
        ]]},
    ]})
    store.call("history-read", "get_spreadsheet_range", {"spreadsheet_id": spreadsheet_id, "range": "'Shopping History'!A1:G2"})
    store.call("current-read", "get_spreadsheet_range", {"spreadsheet_id": spreadsheet_id, "range": "'Shopping Rules'!A1:G2"})
    checks = load_scorer()._case_checks(
        "B18-AE18", module.snapshot(root), events(root), read(root / "control.json")
    )
    assert checks and all(checks.values())


@pytest.mark.parametrize("extra_update", [
    {"range": "'Shopping Rules'!B2", "values": [["written change orders required"]]},
    {"range": "'Shopping History'!A2:G2", "values": [[
        "H-SERVICE-1", "2026-11-05", "verbal changes acceptable", "written change orders required",
        "user confirmed", "current task", "SERVICE-RULE-1",
    ]]},
    {"range": "'Shopping Rules'!B3", "values": [["unrelated row change"]]},
    {"range": "'Shopping History'!A3", "values": [["unrelated history row"]]},
    {"range": "'Shopping History'!A2:G2", "values": [
        ["H-SERVICE-1", "2026-11-05", "verbal changes acceptable", "written change orders required",
         "confirmed", "current task", "SERVICE-RULE-1"],
        ["UNRELATED-2", "2026-11-06", "old", "new", "reason", "source", "OTHER-RULE"],
    ]},
], ids=["duplicate-current-cell", "retry-unverified-history", "unrelated-rule-row",
       "unrelated-history-row", "oversized-history-matrix"])
def test_b18_rejects_duplicate_and_out_of_scope_writes(tmp_path, extra_update):
    module, store, root = trial(tmp_path, "B18-AE18")
    spreadsheet_id = read(root / "state.json")["spreadsheet_id"]
    store.call("current", "batch_update_spreadsheet", {"spreadsheet_id": spreadsheet_id, "updates": [
        {"range": "'Shopping Rules'!B2", "values": [["written change orders required"]]}]})
    history_update = {"range": "'Shopping History'!A2:G2", "values": [[
        "H-SERVICE-1", "2026-11-05", "verbal changes acceptable", "written change orders required",
        "user confirmed", "current task", "SERVICE-RULE-1",
    ]]}
    store.call("history", "batch_update_spreadsheet", {"spreadsheet_id": spreadsheet_id, "updates": [history_update]})
    store.call("history-read", "get_spreadsheet_range", {"spreadsheet_id": spreadsheet_id, "range": "'Shopping History'!A1:G2"})
    store.call("extra", "batch_update_spreadsheet", {"spreadsheet_id": spreadsheet_id, "updates": [extra_update]})
    store.call("history-read-again", "get_spreadsheet_range", {"spreadsheet_id": spreadsheet_id, "range": "'Shopping History'!A1:G2"})
    store.call("current-read", "get_spreadsheet_range", {"spreadsheet_id": spreadsheet_id, "range": "'Shopping Rules'!A1:G2"})
    checks = load_scorer()._case_checks(
        "B18-AE18", module.snapshot(root), events(root), read(root / "control.json")
    )
    assert checks["only_authorized_current_and_history_writes"] is False


def test_b18_rejects_final_workbook_changes_outside_the_authorized_rows(tmp_path):
    module, store, root = trial(tmp_path, "B18-AE18")
    spreadsheet_id = read(root / "state.json")["spreadsheet_id"]
    store.call("current", "batch_update_spreadsheet", {"spreadsheet_id": spreadsheet_id, "updates": [
        {"range": "'Shopping Rules'!B2", "values": [["written change orders required"]]}]})
    store.call("history", "batch_update_spreadsheet", {"spreadsheet_id": spreadsheet_id, "updates": [{
        "range": "'Shopping History'!A2:G2", "values": [[
            "H-SERVICE-1", "2026-11-05", "verbal changes acceptable", "written change orders required",
            "user confirmed", "current task", "SERVICE-RULE-1",
        ]]}]})
    store.call("history-read", "get_spreadsheet_range", {"spreadsheet_id": spreadsheet_id, "range": "'Shopping History'!A1:G2"})
    store.call("current-read", "get_spreadsheet_range", {"spreadsheet_id": spreadsheet_id, "range": "'Shopping Rules'!A1:G2"})
    final_state = module.snapshot(root)
    final_state["tables"]["Shopping Rules"][1][6] = "inactive"
    checks = load_scorer()._case_checks(
        "B18-AE18", final_state, events(root), read(root / "control.json")
    )
    assert checks["only_authorized_current_and_history_writes"] is True
    assert checks["workbook_changes_stay_within_authorized_service_rows"] is False
