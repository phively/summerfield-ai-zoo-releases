"""Integrity checks for the exposed Research Briefing continuity packet."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace
import pytest


ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "evals" / "research-briefing-continuity"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_packet() -> tuple[dict, dict]:
    manifest = json.loads((EVAL_ROOT / "manifest.json").read_text(encoding="utf-8"))
    source_index = json.loads((EVAL_ROOT / "fixtures" / "source-index.json").read_text(encoding="utf-8"))
    return manifest, source_index


def test_manifest_groups_and_cases_are_complete_and_unique() -> None:
    manifest, _ = load_packet()
    groups = manifest["groups"]
    cases = manifest["cases"]
    group_ids = [group["id"] for group in groups]
    case_ids = [case["id"] for case in cases]
    assert group_ids == ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]
    assert len(case_ids) == len(set(case_ids))
    assert all(group["case_ids"] for group in groups)
    assert all(group["coverage"].strip() for group in groups)
    g7 = next(group for group in groups if group["id"] == "G7")
    assert g7["case_ids"] == ["transcript-formatting-is-adjacent", "mixed-adjacent-and-research-under-grant"]

    cases_by_group: dict[str, set[str]] = {group_id: set() for group_id in group_ids}
    for case in cases:
        assert case["group_id"] in cases_by_group
        assert case["initial_turn"].strip()
        assert isinstance(case["future_turns"], list)
        assert all(isinstance(turn, str) and turn.strip() for turn in case["future_turns"])
        controller = case["controller"]
        assert controller["expected_operations"]
        assert controller["must"]
        assert controller["critical_failures"]
        cases_by_group[case["group_id"]].add(case["id"])

    assert all(set(group["case_ids"]) == cases_by_group[group["id"]] for group in groups)


def test_mixed_adjacent_and_research_case_requires_both_behaviors_under_grant() -> None:
    manifest, _ = load_packet()
    case = next(case for case in manifest["cases"] if case["id"] == "mixed-adjacent-and-research-under-grant")
    assert case["group_id"] == "G7"
    assert len(case["future_turns"]) == 2
    assert case["future_turns"][0] == "I authorize research without further scope confirmations for the remainder of this conversation."
    final_turn = case["controller"]["expected_operations"][-1]
    assert final_turn["after_user_turn"] == 3
    assert final_turn["must_read_any"] == ["cairn-account-portal-current"]
    assert final_turn["must_not_gate"] is True
    assert final_turn["must_not_search_or_read_for_adjacent_task"] is True
    assert any("format the supplied note directly" in requirement.casefold() for requirement in case["controller"]["must"])


def test_unsupported_claim_calibration_is_controller_owned_and_outside_development_groups() -> None:
    manifest, _ = load_packet()
    controls = manifest["controls"]
    assert [control["id"] for control in controls] == ["unsupported-claim-control"]
    control = controls[0]
    assert control["group_id"] == "CONTROL"
    assert control["candidate_instructions"] == "controls/unsupported-claim-candidate.md"
    assert control["id"] not in {case["id"] for case in manifest["cases"]}
    assert control["controller"]["critical_failures"]
    instructions = (EVAL_ROOT / control["candidate_instructions"]).read_text(encoding="utf-8")
    assert "Deliberately noncompliant" in instructions
    assert "do not call any source tools" in instructions.casefold()

    negative_receipt = json.loads((EVAL_ROOT / "controls" / "unsupported-claim-negative-receipt.json").read_text(encoding="utf-8"))
    assert negative_receipt["receipt_type"] == "synthetic-controller-owned-negative-vector"
    assert negative_receipt["observed_model_response"] is False
    assert negative_receipt["source_operations"] == []
    assert "checked the current manufacturer guide" in negative_receipt["assistant_answer"].casefold()
    assert negative_receipt["assessment"]["source_grounding"] == {
        "score": 0,
        "result": "fail",
        "reason": "The answer claims a current source read, but the receipt contains no successful source-read event.",
    }


def test_fixture_index_resolves_only_bounded_synthetic_sources() -> None:
    _, source_index = load_packet()
    source_ids = [source["id"] for source in source_index["sources"]]
    assert len(source_ids) == len(set(source_ids))
    assert "fictional" in source_index["notice"].casefold()
    fixture_root = EVAL_ROOT / "fixtures"
    for source in source_index["sources"]:
        assert source["authority"]
        assert source["applies_to"]
        assert source["topics"]
        if source["status"] == "available":
            path = (fixture_root / source["path"]).resolve()
            assert path.is_relative_to(fixture_root.resolve())
            assert path.is_file()
            assert "synthetic test fixture" in path.read_text(encoding="utf-8").casefold()
        else:
            assert source["status"] == "unavailable"
            assert source["path"] is None


def test_controller_turns_and_grading_are_separate_from_public_sources() -> None:
    manifest, source_index = load_packet()
    source_ids = {source["id"] for source in source_index["sources"]}
    public_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (EVAL_ROOT / "fixtures").iterdir()
        if path.is_file() and path.suffix == ".md"
    )
    assert "future_turns" not in public_text
    assert "critical_failures" not in public_text
    assert "manifest.json" not in public_text
    for case in manifest["cases"]:
        assert case["initial_turn"] not in public_text
        for operation in case["controller"]["expected_operations"]:
            for source_id in operation.get("must_read_any", []) + operation.get("must_reuse_or_reread", []) + operation.get("must_attempt", []) + operation.get("must_read_all", []):
                assert source_id in source_ids
        candidate_fields = {key for key in case if key not in {"id", "group_id", "initial_turn", "future_turns", "controller"}}
        assert not candidate_fields


def test_fixture_server_logs_executed_source_reads_and_rejects_unavailable_material(tmp_path: Path) -> None:
    server_module = load_module("continuity_fixture_server", EVAL_ROOT / "fixture_server.py")
    server = server_module.FixtureServer(EVAL_ROOT / "fixtures", tmp_path / "events.jsonl", "smoke", "control")

    search = server.call("search_sources", {"query": "Cairn R6 port 2 firmware 4.2.1"})
    assert "cairn-mesh-r6-current-guide" in {item["id"] for item in search["structuredContent"]["sources"]}

    read = server.call("read_source", {"source_id": "cairn-mesh-r6-current-guide"})
    assert read["structuredContent"]["status"] == "read"
    assert "Port 2 is a 1 GbE LAN port" in read["structuredContent"]["content"]

    unavailable = server.call("read_source", {"source_id": "cairn-next-release-status"})
    assert unavailable["isError"] is True
    assert json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1])["exit_status"] == 1

    resumed_server = server_module.FixtureServer(EVAL_ROOT / "fixtures", tmp_path / "events.jsonl", "smoke", "control")
    resumed_server.search("Cairn R6 current guide")
    event_lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    sequences = [json.loads(line)["sequence"] for line in event_lines]
    assert sequences == list(range(1, len(sequences) + 1))


def test_fixture_server_uses_newline_delimited_json_rpc_stdio(tmp_path: Path) -> None:
    server_path = EVAL_ROOT / "fixture_server.py"
    event_path = tmp_path / "events.jsonl"
    command = [
        sys.executable,
        str(server_path),
        "serve",
        str(EVAL_ROOT / "fixtures"),
        str(event_path),
        "transport-smoke",
        "control",
    ]
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    result = subprocess.run(
        command,
        input="".join(json.dumps(request) + "\n" for request in requests),
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )

    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert [response["id"] for response in responses] == [1, 2]
    assert responses[0]["result"]["protocolVersion"] == "2025-11-25"
    assert [item["name"] for item in responses[1]["result"]["tools"]] == ["search_sources", "read_source"]
    events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
    assert [event["operation"] for event in events] == ["mcp_initialize", "mcp_tools_list"]


def test_runner_uses_an_isolated_read_only_fixture_tool_boundary() -> None:
    runner = load_module("continuity_trial_runner", EVAL_ROOT / "run_trial.py")
    command = runner.common_command("gpt-6.1-sol", "medium", Path("/tmp/events.jsonl"), "case", "candidate")
    config_values = [command[index + 1] for index, value in enumerate(command[:-1]) if value == "--config"]
    assert any(value == "features.shell_tool=false" for value in config_values)
    assert any(value == "features.apps=false" for value in config_values)
    assert any(value == "features.plugins=false" for value in config_values)
    assert any(value == "features.multi_agent=false" for value in config_values)
    assert any(value == "features.code_mode.enabled=false" for value in config_values)
    assert any(value == 'features.code_mode.excluded_tool_namespaces=["collaboration", "functions"]' for value in config_values)
    assert any(value == "features.code_mode_host=true" for value in config_values)
    assert any(value == "web_search=\"disabled\"" for value in config_values)
    assert any(value == "mcp_servers.continuity.enabled_tools=[\"search_sources\", \"read_source\"]" for value in config_values)

    control_command = runner.common_command("gpt-6-luna", "medium", Path("/tmp/control-events.jsonl"), "unsupported-claim-control", "control")
    control_values = [control_command[index + 1] for index, value in enumerate(control_command[:-1]) if value == "--config"]
    assert any(value == "mcp_servers.continuity.enabled=false" for value in control_values)
    assert any(value == "mcp_servers.continuity.enabled_tools=[]" for value in control_values)

    exposed = runner.tool_inventory([
        {"type": "additional_tools", "tools": [
            {"type": "namespace", "name": "continuity", "tools": [{"name": "search_sources"}, {"name": "read_source"}]},
            {"type": "namespace", "name": "functions", "tools": [{"name": "exec"}]},
        ]}
    ])
    assert exposed == ["continuity.read_source", "continuity.search_sources", "functions.exec"]

    resume_command = runner.common_command("gpt-6.1-sol", "medium", Path("/tmp/events.jsonl"), "case", "candidate", resume=True)
    assert resume_command[resume_command.index("exec"):][:2] == ["exec", "resume"]


def test_trial_validity_aggregates_every_turn_and_requires_observed_same_thread_identity() -> None:
    runner = load_module("continuity_trial_runner", EVAL_ROOT / "run_trial.py")
    initial = {"exit_status": 0, "thread_id": "thread-1", "turn_completed": True, "unexpected_tool_calls": []}
    resumed = {"exit_status": 0, "resumed_thread_id": "thread-1", "turn_completed": True, "unexpected_tool_calls": []}
    invalid_early = {**initial, "exit_status": 1}
    assert "Turn 1" in runner.trial_evidence_error({"thread_id": "thread-1", "turns": [invalid_early, resumed]})
    assert "thread identity" in runner.trial_evidence_error({"thread_id": "thread-1", "turns": [initial, {**resumed, "resumed_thread_id": None}]})
    assert "thread identity" in runner.trial_evidence_error({"thread_id": "thread-1", "turns": [initial, {**resumed, "resumed_thread_id": "thread-2"}]})
    assert runner.trial_evidence_error({"thread_id": "thread-1", "turns": [initial, resumed]}) is None


def test_controller_turns_must_be_sent_in_order() -> None:
    runner = load_module("continuity_trial_runner", EVAL_ROOT / "run_trial.py")
    case = {"future_turns": ["first", "second", "third"]}
    initial = {"turn": 1}
    turn_one = {"turn": 2, "controller_turn_index": 1}
    turn_two = {"turn": 3, "controller_turn_index": 2}
    assert "expected controller turn 1" in runner.controller_turn_error({"turns": [initial]}, case, 2)
    assert runner.controller_turn_error({"turns": [initial, turn_one]}, case, 2) is None
    assert "ordered prefix" in runner.controller_turn_error({"turns": [initial, turn_two]}, case, 1)
    assert "expected controller turn 3" in runner.controller_turn_error({"turns": [initial, turn_one, turn_two]}, case, 1)


def test_turn_validation_rejects_unexpected_tools_and_missing_completion(tmp_path: Path) -> None:
    runner = load_module("continuity_trial_runner", EVAL_ROOT / "run_trial.py")
    event_path = tmp_path / "turn.jsonl"
    event_path.write_text(json.dumps({"type": "item.completed", "item": {"type": "exec_command", "id": "bad"}}) + "\n", encoding="utf-8")
    _, unexpected, completed = runner.turn_validation(event_path)
    assert unexpected and unexpected[0]["type"] == "exec_command"
    assert completed is False


def test_workspace_cleanup_removes_only_runner_owned_temp_children(tmp_path: Path, monkeypatch) -> None:
    runner = load_module("continuity_trial_runner", EVAL_ROOT / "run_trial.py")
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: str(tmp_path))
    workspace = tmp_path / "rb-continuity-agent-owned"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("fixture", encoding="utf-8")
    record = {"workspace": str(workspace)}
    runner.cleanup_workspace(record)
    assert not workspace.exists()
    assert record["workspace"] is None
    assert record["workspace_cleanup"] == "removed"

    other = tmp_path / "unrelated"
    other.mkdir()
    with pytest.raises(SystemExit, match="refusing to remove"):
        runner.cleanup_workspace({"workspace": str(other)})


def test_runner_clears_parent_codex_session_context(monkeypatch) -> None:
    runner = load_module("continuity_trial_runner", EVAL_ROOT / "run_trial.py")
    monkeypatch.setenv("CODEX_SESSION_ID", "parent-session")
    monkeypatch.setenv("CODEX_THREAD_ID", "parent-thread")
    monkeypatch.setenv("CODEX_TOOL_CALL_ID", "parent-tool-call")
    monkeypatch.setenv("CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "parent-origin")
    monkeypatch.setenv("CODEX_HOME", "/home/test/.codex")

    environment, removed = runner.isolated_codex_environment()

    assert removed == [
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
        "CODEX_TOOL_CALL_ID",
        "CODEX_INTERNAL_ORIGINATOR_OVERRIDE",
    ]
    assert all(key not in environment for key in removed)
    assert environment["CODEX_HOME"] == "/home/test/.codex"


def test_invoke_terminates_and_reaps_process_group_on_keyboard_interrupt(tmp_path: Path, monkeypatch) -> None:
    runner = load_module("continuity_trial_runner", EVAL_ROOT / "run_trial.py")
    signals: list[int] = []

    class InterruptedProcess:
        pid = 1234
        returncode = -signal.SIGTERM

        def __init__(self) -> None:
            self.communicate_calls = 0

        def communicate(self, *args, **kwargs):
            self.communicate_calls += 1
            if self.communicate_calls == 1:
                raise KeyboardInterrupt
            return None, None

    process = InterruptedProcess()
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(runner.platform_support, "IS_WINDOWS", False)
    monkeypatch.setattr(runner.os, "killpg", lambda pid, sig: signals.append(sig), raising=False)

    result = runner.invoke(["codex"], "prompt", tmp_path, tmp_path / "turn.jsonl", tmp_path / "turn.stderr")

    assert result == (130, None, None)
    assert signals == [runner.signal.SIGTERM]
    assert process.communicate_calls == 2


def test_preflight_resolves_relative_output_and_preserves_interrupt_receipt(tmp_path: Path, monkeypatch) -> None:
    runner = load_module("continuity_trial_runner", EVAL_ROOT / "run_trial.py")
    monkeypatch.chdir(tmp_path)
    candidate = tmp_path / "candidate.md"
    candidate.write_text("candidate instructions", encoding="utf-8")
    workspace = tmp_path / "rb-continuity-preflight-owned"
    def make_workspace(**kwargs) -> str:
        workspace.mkdir()
        return str(workspace)

    monkeypatch.setattr(runner.tempfile, "mkdtemp", make_workspace)
    event_paths: list[Path] = []

    def fake_setting_args(server_script: Path, events_path: Path, *args):
        event_paths.append(events_path)
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events_path.write_text(json.dumps({"operation": "mcp_initialize"}) + "\n", encoding="utf-8")
        return []

    class InterruptedProcess:
        pid = 5678
        returncode = -signal.SIGTERM

        def __init__(self) -> None:
            self.communicate_calls = 0

        def communicate(self, *args, **kwargs):
            self.communicate_calls += 1
            if self.communicate_calls == 1:
                raise KeyboardInterrupt
            return b"{}", b"interrupted"

    process = InterruptedProcess()
    monkeypatch.setattr(runner, "setting_args", fake_setting_args)
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="codex test"))
    catalog_calls: list[bool] = []
    monkeypatch.setattr(runner, "model_catalog", lambda: (catalog_calls.append(True) or [{"slug": "model", "visibility": "list"}], None))
    monkeypatch.setattr(runner.platform_support, "IS_WINDOWS", False)
    monkeypatch.setattr(runner.os, "killpg", lambda pid, sig: None, raising=False)

    status = runner.preflight(SimpleNamespace(
        candidate=candidate,
        run_id="interrupt",
        output_base=Path("relative-output"),
        effort="medium",
        model="model",
    ))

    receipt_path = tmp_path / "relative-output" / "interrupt" / "preflight" / "preflight.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert status == 3
    assert event_paths[0].is_absolute()
    assert event_paths[0] == receipt_path.parent / "source-events.jsonl"
    assert receipt["exit_status"] == 130
    assert "interrupted" in receipt["reason"].casefold()
    assert "not queried after interruption" in receipt["reason"]
    assert not catalog_calls
    assert receipt["fixture_protocol_events"] == [{"operation": "mcp_initialize"}]
    assert process.communicate_calls == 2
    assert not workspace.exists()


def test_start_trial_resolves_relative_output_and_records_interruption(tmp_path: Path, monkeypatch) -> None:
    runner = load_module("continuity_trial_runner", EVAL_ROOT / "run_trial.py")
    monkeypatch.chdir(tmp_path)
    candidate = tmp_path / "candidate.md"
    candidate.write_text("candidate instructions", encoding="utf-8")
    workspace = tmp_path / "rb-continuity-agent-owned"
    workspace.mkdir()
    monkeypatch.setattr(runner.tempfile, "mkdtemp", lambda **kwargs: str(workspace))
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: str(tmp_path))
    event_paths: list[Path] = []

    def fake_common_command(model: str, effort: str, events_path: Path, *args, **kwargs):
        event_paths.append(events_path)
        return ["codex"]

    def fake_invoke(command, prompt, cwd, stdout_path, stderr_path):
        stdout_path.write_text(json.dumps({"type": "turn.completed"}) + "\n", encoding="utf-8")
        return 130, None, None

    monkeypatch.setattr(runner, "common_command", fake_common_command)
    monkeypatch.setattr(runner, "model_catalog", lambda: ([{"slug": "model", "visibility": "list"}], None))
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="codex test"))
    monkeypatch.setattr(runner, "invoke", fake_invoke)

    status = runner.start_trial(SimpleNamespace(
        case_id="conversation-waiver-followups",
        candidate=candidate,
        candidate_id="candidate",
        run_id="interrupt",
        output_base=Path("relative-output"),
        model="model",
        effort="medium",
    ))

    run_dir = tmp_path / "relative-output" / "interrupt" / "candidate" / "conversation-waiver-followups"
    record = json.loads((run_dir / "runtime-settings.json").read_text(encoding="utf-8"))
    assert status == 3
    assert event_paths[0].is_absolute()
    assert event_paths[0] == run_dir / "source-events.jsonl"
    assert record["evidence_status"] == "invalid"
    assert record["turns"][0]["interrupted"] is True
    assert record["turns"][0]["exit_status"] == 130
    assert record["workspace"] is None
    assert not workspace.exists()


def test_reply_trial_records_interruption_and_cleans_workspace(tmp_path: Path, monkeypatch) -> None:
    runner = load_module("continuity_trial_runner", EVAL_ROOT / "run_trial.py")
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: str(tmp_path))
    workspace = tmp_path / "rb-continuity-agent-owned"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("candidate instructions", encoding="utf-8")
    run_dir = tmp_path / "run" / "candidate" / "case"
    run_dir.mkdir(parents=True)
    (run_dir / "source-events.jsonl").write_text("", encoding="utf-8")
    (run_dir / "turn-01.jsonl").write_text(json.dumps({"type": "turn.completed"}) + "\n", encoding="utf-8")
    record = {
        "case_id": "conversation-waiver-followups",
        "candidate_id": "candidate",
        "candidate_sha256": "unused-in-this-test",
        "requested_model": "model",
        "requested_reasoning_effort": "medium",
        "thread_id": "thread-1",
        "workspace": str(workspace),
        "turns": [{"turn": 1, "exit_status": 0, "thread_id": "thread-1", "turn_completed": True, "unexpected_tool_calls": []}],
        "evidence_status": "valid",
    }
    (run_dir / "runtime-settings.json").write_text(json.dumps(record), encoding="utf-8")
    (run_dir / "turn-01-assistant.txt").write_text("Initial answer", encoding="utf-8")
    monkeypatch.setattr(runner, "common_command", lambda *args, **kwargs: ["codex"])

    def fake_invoke(command, prompt, cwd, stdout_path, stderr_path):
        stdout_path.write_text(json.dumps({"type": "turn.completed"}) + "\n", encoding="utf-8")
        return 130, None, None

    monkeypatch.setattr(runner, "invoke", fake_invoke)

    status = runner.reply_trial(SimpleNamespace(run_dir=run_dir, turn_index=1))

    saved = json.loads((run_dir / "runtime-settings.json").read_text(encoding="utf-8"))
    assert status == 3
    assert saved["evidence_status"] == "invalid"
    assert saved["turns"][1]["interrupted"] is True
    assert saved["turns"][1]["exit_status"] == 130
    assert saved["workspace"] is None
    assert not workspace.exists()
