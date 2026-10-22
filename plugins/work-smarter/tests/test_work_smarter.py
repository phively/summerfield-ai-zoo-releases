#!/usr/bin/env python3
"""Structural and behavioral contract tests for work-smarter."""

import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
import sys
import time
from contextlib import redirect_stdout
from unittest.mock import patch
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def exact_sha256(path: Path) -> str:
    content = path.read_bytes()
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def load_validator():
    path = ROOT / "scripts" / "validate_plugin.py"
    spec = importlib.util.spec_from_file_location("validate_plugin", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_memory_audit_validator():
    path = ROOT / "scripts" / "validate_memory_audit.py"
    spec = importlib.util.spec_from_file_location("validate_memory_audit", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_snapshot_validator():
    path = ROOT / "skills" / "record-backup" / "scripts" / "validate_snapshot.py"
    spec = importlib.util.spec_from_file_location("validate_snapshot", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_instruction_length_checker():
    path = ROOT / "skills" / "superb-skills" / "scripts" / "check_instruction_length.py"
    spec = importlib.util.spec_from_file_location("check_instruction_length", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_candidate_comparison_runner():
    path = ROOT / "skills" / "superb-skills" / "scripts" / "compare_candidates.py"
    spec = importlib.util.spec_from_file_location("compare_candidates", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_full_validator() -> None:
    assert load_validator().main() == 0



def test_research_checkpoint_is_preserved() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    assert "Begin with a research-scope checkpoint" in research
    assert "Ask the user to confirm or revise this scope, then wait" in research
    assert "must not treat initiation of the handoff as confirmation" in contract


def _comparison_inputs(tmp_path: Path) -> dict[str, Path | dict]:
    baseline = tmp_path / "baseline.md"
    improved = tmp_path / "improved.md"
    baseline.write_text("required\nprivate\n", encoding="utf-8")
    improved.write_text("required\npublic\n", encoding="utf-8")
    suite = tmp_path / "suite.json"
    suite.write_text(json.dumps({
        "suite_id": "unrelated-target-suite",
        "suite_version": "1.0.0",
        "rubric_id": "unrelated-target-rubric",
        "rubric_version": "1.0.0",
        "cases": [
            {"id": "required-guidance", "required": True, "critical": True, "checks": [{"type": "contains", "value": "required"}]},
            {"id": "no-private-guidance", "required": True, "checks": [{"type": "not_contains", "value": "private"}]},
        ],
        "red_green": [{"criterion_id": "privacy", "red_candidate_id": "baseline", "green_candidate_id": "improved", "case_ids": ["no-private-guidance"]}],
    }), encoding="utf-8")
    partition = tmp_path / "partition.json"
    partition.write_text(json.dumps({
        "plan_id": "unrelated-target-development",
        "scope": "target_runtime",
        "scheme": "grouped_development_evaluation",
        "grouping_key": "scenario_family",
        "assignment": {"algorithm": "stable_group_order", "version": "1", "stable_inputs": ["required", "privacy"]},
        "requested_fold_count": 5,
        "requested_holdout_percent": 10,
        "rounding_rule": "round_half_up",
        "coverage": {"status": "insufficient_coverage", "reason": "Two cases cannot support five folds and a non-empty holdout."},
        "exposure_policy": {"holdout_content_before_freeze": "implementation_agent_prohibited", "exposure_log": []},
        "case_ids": ["required-guidance", "no-private-guidance"],
        "groups": [
            {"id": "required", "case_ids": ["required-guidance"]},
            {"id": "privacy", "case_ids": ["no-private-guidance"]},
        ],
        "folds": [{"id": "fold-1", "group_ids": ["required", "privacy"], "training_group_ids": [], "case_ids": ["required-guidance", "no-private-guidance"], "case_count": 2}],
        "holdout": {"case_ids": [], "case_count": 0, "status": "insufficient_coverage"},
    }), encoding="utf-8")
    config = {
        "requested_runner": "luna-xhigh",
        "requested_model": "runtime-selected-test-model",
        "requested_reasoning_effort": "xhigh",
        "actual_runner": "deterministic-adapter",
        "actual_model": "not_applicable",
        "actual_reasoning_effort": "not_applicable",
        "substitution_reason": "No model was invoked by the deterministic adapter.",
        "model_selection": {
            "policy": "cost_intelligence_time",
            "basis": "configured_benchmark_findings",
            "reason": "The adapter is a local structural smoke path.",
        },
        "requested_environment_identity": "local-test-request",
        "actual_environment_identity": "pytest-local",
        "permissions_profile": "temporary-test-output",
        "authorization": {"run": True, "output": True},
        "concurrency": 2,
        "command_output_limit_bytes": 10_000_000,
        "smoke_test": {"status": "passed", "output_inspected": True, "permissions_verified": True, "trial_id": "smoke-local-1"},
        "target_package_id": "unrelated-target",
        "target_content_hash": "sha256:target-fixture",
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return {"baseline": baseline, "improved": improved, "suite": suite, "partition": partition, "config": config_path, "config_data": config}


def _comparison_args(inputs: dict[str, Path | dict], output: Path, adapter: str = "deterministic") -> list[str]:
    return [
        "--candidate", f"baseline={inputs['baseline']}",
        "--candidate", f"improved={inputs['improved']}",
        "--suite", str(inputs["suite"]),
        "--partition-plan", str(inputs["partition"]),
        "--config", str(inputs["config"]),
        "--output", str(output),
        "--adapter", adapter,
        "--run-id", "test-comparison",
    ]


def _prepare_comparison_smoke(inputs: dict[str, Path | dict], runner, adapter: str = "deterministic") -> None:
    suite, suite_hash, cases = runner.load_suite(Path(inputs["suite"]).resolve())
    partition = runner.validate_partition(runner.read_json(Path(inputs["partition"]).resolve()), set(cases))
    candidates = runner.parse_candidates([f"baseline={inputs['baseline']}", f"improved={inputs['improved']}"])
    smoke = Path(inputs["config"]).parent / "smoke-output.txt"
    smoke.write_text("inspected smoke output\n", encoding="utf-8")
    inputs["config_data"]["smoke_test"].update({
        "artifact_path": str(smoke),
        "output_hash": runner.content_hash(smoke),
        "execution_fingerprint": "pending",
    })
    config = runner.validate_config(inputs["config_data"], adapter)
    suite_meta = {
        "suite_id": suite["suite_id"],
        "suite_version": suite["suite_version"],
        "rubric_id": suite["rubric_id"],
        "rubric_version": suite["rubric_version"],
        "content_hash": suite_hash,
    }
    fingerprint = runner.execution_fingerprint(adapter, candidates, suite_meta, partition, config)
    inputs["config_data"]["smoke_test"]["execution_fingerprint"] = fingerprint
    inputs["config"].write_text(json.dumps(inputs["config_data"]), encoding="utf-8")


def test_candidate_comparison_is_target_agnostic_and_preserves_requested_actual_runtime(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    _prepare_comparison_smoke(inputs, runner)
    output = tmp_path / "comparison.json"

    assert runner.main(_comparison_args(inputs, output)) == 0
    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["status"] == "complete"
    assert report["target_package"]["id"] == "unrelated-target"
    assert report["configuration"]["requested"]["runner"] == "luna-xhigh"
    assert report["configuration"]["actual"]["runner"] == "deterministic-adapter"
    assert report["configuration"]["requested"]["model"] != report["configuration"]["actual"]["model"]
    assert report["configuration"]["requested_environment_identity"] == "local-test-request"
    assert report["configuration"]["actual_environment_identity"] == "pytest-local"
    assert report["recommendation"]["selected_candidate_id"] == "improved"
    assert all(result["command_output_limit_bytes"] == 10_000_000 for result in report["results"])
    assert all(result["process_controller_version"] == runner.PROCESS_CONTROLLER_VERSION for result in report["results"])
    assert all(result["evidence_valid"] for result in report["results"])
    assert report["red_green_results"][0]["status"] == "demonstrated"
    assert "structural evidence only" in report["recommendation"]["limitations"][0]
    assert len(report["results"]) == 4
    assert all(result["candidate_content_hash"] for result in report["results"])
    assert all(result["suite_content_hash"] for result in report["results"])
    assert "Comparison complete" in report["summary"]


def test_candidate_comparison_command_adapter_captures_a_real_local_execution(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is the verified execution path for this smoke run."
    config["command_argv"] = [
        sys.executable,
        "-c",
        "from pathlib import Path; print(Path(r'{candidate}').read_text(encoding='utf-8'))",
    ]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "command-comparison.json"

    assert runner.main(_comparison_args(inputs, output, adapter="command")) == 0
    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["status"] == "complete"
    assert all("attempt_artifacts" in result for result in report["results"])
    assert all(result["attempt_artifacts"]["returncode"] == 0 for result in report["results"])
    assert all(result["attempt_artifacts"]["tree_cleanup_verified"] for result in report["results"])
    assert all(result["attempt_artifacts"]["containment_method"] for result in report["results"])
    assert all(result["evidence_valid"] for result in report["results"])
    assert report["recommendation"]["selected_candidate_id"] == "improved"


def test_candidate_comparison_hashes_exact_file_bytes(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    crlf = tmp_path / "crlf.bin"
    lf = tmp_path / "lf.bin"
    crlf.write_bytes(b"header\r\n\x00\xff")
    lf.write_bytes(b"header\n\x00\xff")

    assert runner.content_hash(crlf) != runner.content_hash(lf)


def test_candidate_comparison_terminates_descendants_after_timeout(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    marker = tmp_path / "late-child-marker.txt"
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is the verified execution path for this timeout test."
    config["command_timeout_seconds"] = 0.2
    child_code = f"import time; from pathlib import Path; time.sleep(1); Path({str(marker)!r}).write_text('late')"
    parent_code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child_code!r}]); time.sleep(5)"
    config["command_argv"] = [
        sys.executable,
        "-c",
        parent_code,
    ]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "timeout.json"

    assert runner.main(_comparison_args(inputs, output, adapter="command")) == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "incomplete"
    assert all(result["status"] == "failed" for result in report["results"])
    assert all(not result["evidence_valid"] for result in report["results"])
    assert all(result["attempt_artifacts"]["termination_reason"] == "command_timeout" for result in report["results"])
    assert all(result["attempt_artifacts"]["tree_cleanup_verified"] for result in report["results"])
    assert all(result["attempt_artifacts"]["elapsed_seconds"] < 4.0 for result in report["results"])
    time.sleep(1.2)
    assert not marker.exists()


def test_candidate_comparison_rejects_nonfinite_or_boolean_command_timeouts(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is used only to validate timeout input handling."
    config["command_argv"] = [sys.executable, "-c", "print('required')"]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")

    for index, invalid_timeout in enumerate((float("nan"), float("inf"), float("-inf"), True)):
        invalid_config = dict(inputs["config_data"])
        invalid_config["command_timeout_seconds"] = invalid_timeout
        try:
            runner.validate_config(invalid_config, "command")
        except runner.ConfigurationError:
            pass
        else:
            raise AssertionError(f"invalid timeout was accepted: {invalid_timeout!r}")
        inputs["config"].write_text(json.dumps(invalid_config), encoding="utf-8")
        output = tmp_path / f"invalid-timeout-{index}.json"
        assert runner.main(_comparison_args(inputs, output, adapter="command")) == 2
        assert not output.exists()


def test_candidate_comparison_cleans_descendants_after_parent_exits(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    marker = tmp_path / "orphan-child-marker.txt"
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is the verified execution path for this process-tree cleanup test."
    child_code = f"import time; from pathlib import Path; time.sleep(2); Path({str(marker)!r}).write_text('late')"
    parent_code = f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child_code!r}]); print(open(r'{{candidate}}', encoding='utf-8').read())"
    config["command_argv"] = [sys.executable, "-c", parent_code]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "orphan-cleanup.json"

    assert runner.main(_comparison_args(inputs, output, adapter="command")) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert all(result["status"] == "passed" for result in report["results"] if result["candidate_id"] == "improved")
    baseline_privacy = next(result for result in report["results"] if result["candidate_id"] == "baseline" and result["case_id"] == "no-private-guidance")
    assert baseline_privacy["status"] == "failed"
    assert all(result["attempt_artifacts"]["tree_cleanup_verified"] for result in report["results"])
    assert all(result["attempt_artifacts"]["elapsed_seconds"] < 4.0 for result in report["results"])
    time.sleep(2.2)
    assert not marker.exists()


def test_candidate_comparison_bounds_command_output(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is the verified execution path for this output-limit test."
    config["command_output_limit_bytes"] = 1024
    config["command_argv"] = [sys.executable, "-c", "print('x' * 100000)"]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "output-limit.json"

    assert runner.main(_comparison_args(inputs, output, adapter="command")) == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "incomplete"
    assert all(result["attempt_artifacts"]["termination_reason"] == "command_output_limit" for result in report["results"])
    assert all(result["attempt_artifacts"]["output_truncated"] for result in report["results"])
    assert all(Path(result["attempt_artifacts"]["stdout"]["path"]).stat().st_size <= 1024 for result in report["results"])
    assert all(not result["evidence_valid"] for result in report["results"])


def test_candidate_comparison_invalidates_reader_errors_before_scoring(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is replaced by a fault-injection test."
    config["command_argv"] = [sys.executable, "-c", "print('required\\npublic')", "{candidate_id}"]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "reader-error.json"

    def fake_run(controller, timeout):
        return {
            "returncode": 0,
            "stdout": b"required\npublic\n",
            "stderr": b"",
            "stdout_total_bytes": 16,
            "stderr_total_bytes": 0,
            "output_truncated": False,
            "termination_reason": None,
            "termination_method": "fault-injection",
            "containment_method": "fault-injection",
            "tree_cleanup_verified": True,
            "elapsed_seconds": 0.01,
            "reader_errors": ["injected output read failure"],
        }

    with patch.object(runner.ProcessTreeController, "run", new=fake_run):
        assert runner.main(_comparison_args(inputs, output, adapter="command")) == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "incomplete"
    assert report["recommendation"]["selected_candidate_id"] is None
    assert report["red_green_results"][0]["status"] == "invalid_evidence"
    assert all(not result["evidence_valid"] for result in report["results"])
    assert all(result["observed_evidence"][0]["type"] == "command_output_read" for result in report["results"])


def test_candidate_comparison_invalidates_unverified_cleanup_before_selection(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is replaced by a fault-injection test."
    config["command_argv"] = [sys.executable, "-c", "print('required\\npublic')", "{candidate_id}"]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "cleanup-error.json"

    def fake_run(controller, timeout):
        return {
            "returncode": 0,
            "stdout": b"required\npublic\n",
            "stderr": b"",
            "stdout_total_bytes": 16,
            "stderr_total_bytes": 0,
            "output_truncated": False,
            "termination_reason": None,
            "termination_method": "fault-injection",
            "containment_method": "fault-injection",
            "tree_cleanup_verified": controller.argv[-1] == "improved",
            "elapsed_seconds": 0.01,
            "reader_errors": [],
        }

    with patch.object(runner.ProcessTreeController, "run", new=fake_run):
        assert runner.main(_comparison_args(inputs, output, adapter="command")) == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "incomplete"
    assert report["recommendation"]["selected_candidate_id"] is None
    assert report["red_green_results"][0]["status"] == "invalid_evidence"
    baseline = [result for result in report["results"] if result["candidate_id"] == "baseline"]
    improved = [result for result in report["results"] if result["candidate_id"] == "improved"]
    assert all(not result["evidence_valid"] for result in baseline)
    assert all(result["evidence_valid"] for result in improved)


def test_candidate_comparison_isolates_trial_copies_and_collects_declared_files(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is the verified execution path for this smoke run."
    config["artifact_paths"] = ["generated.txt"]
    config["command_argv"] = [
        sys.executable,
        "-c",
        "from pathlib import Path; p=Path(r'{candidate}'); text=p.read_text(encoding='utf-8'); Path(r'{trial_dir}/generated.txt').write_text(text, encoding='utf-8'); print(text)",
    ]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "isolated.json"

    assert runner.main(_comparison_args(inputs, output, adapter="command")) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    improved_privacy = next(result for result in report["results"] if result["candidate_id"] == "improved" and result["case_id"] == "no-private-guidance")
    assert improved_privacy["status"] == "passed"
    improved_artifacts = [result["attempt_artifacts"]["files"]["files"][0] for result in report["results"] if result["candidate_id"] == "improved"]
    assert len({artifact["path"] for artifact in improved_artifacts}) == 2
    assert all(Path(artifact["path"]).is_file() for artifact in improved_artifacts)


def test_candidate_comparison_fails_when_declared_artifact_is_missing(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is the verified execution path for this smoke run."
    config["artifact_paths"] = ["required-results.json"]
    config["command_argv"] = [sys.executable, "-c", "print('required')"]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "missing-artifact.json"

    assert runner.main(_comparison_args(inputs, output, adapter="command")) == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "incomplete"
    assert all(result["status"] == "failed" for result in report["results"])
    assert all(result["observed_evidence"][0]["type"] == "artifact_collection" for result in report["results"])
    assert all(not result["evidence_valid"] for result in report["results"])


def test_candidate_comparison_rejects_modified_candidate_snapshot(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is the verified execution path for this smoke run."
    config["command_argv"] = [
        sys.executable,
        "-c",
        "from pathlib import Path; p=Path(r'{candidate}'); p.write_text(p.read_text(encoding='utf-8') + '\\nmutation', encoding='utf-8'); print(p.read_text(encoding='utf-8'))",
    ]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "mutation.json"

    assert runner.main(_comparison_args(inputs, output, adapter="command")) == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "incomplete"
    assert all(result["status"] == "failed" for result in report["results"])
    assert all(result["attempt_artifacts"]["candidate_modified"] for result in report["results"])
    assert all(not result["evidence_valid"] for result in report["results"])
    assert report["recommendation"]["selected_candidate_id"] is None


def test_candidate_comparison_scores_full_output_and_retains_raw_attempt_artifacts(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    inputs["baseline"].write_text("required\nprivate" + ("x" * 25_000), encoding="utf-8")
    inputs["improved"].write_text("required\npublic\n", encoding="utf-8")
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is the verified execution path for this smoke run."
    config["command_argv"] = [
        sys.executable,
        "-c",
        "from pathlib import Path; print(Path(r'{candidate}').read_text(encoding='utf-8'))",
    ]
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "long-output.json"

    assert runner.main(_comparison_args(inputs, output, adapter="command")) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    baseline_result = next(result for result in report["results"] if result["candidate_id"] == "baseline" and result["case_id"] == "no-private-guidance")
    assert baseline_result["status"] == "failed"
    stdout_path = Path(baseline_result["attempt_artifacts"]["stdout"]["path"])
    assert stdout_path.is_file()
    assert stdout_path.stat().st_size > 20_000


def test_candidate_comparison_rejects_existing_report_before_launching_trials(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    _prepare_comparison_smoke(inputs, runner)
    output = tmp_path / "already-present.json"
    output.write_text("historical report", encoding="utf-8")

    with patch.object(runner, "execute_trial", side_effect=AssertionError("trial launched before output reservation")):
        assert runner.main(_comparison_args(inputs, output)) == 2
    assert output.read_text(encoding="utf-8") == "historical report"


def test_candidate_comparison_rejects_output_inside_candidate_before_launching_trials(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    _prepare_comparison_smoke(inputs, runner)
    candidate_dir = tmp_path / "candidate-package"
    candidate_dir.mkdir()
    candidate_file = candidate_dir / "SKILL.md"
    candidate_file.write_text("candidate", encoding="utf-8")
    output = candidate_dir / "report.json"
    args = _comparison_args(inputs, output)
    args[1] = f"baseline={candidate_dir}"

    with patch.object(runner, "execute_trial", side_effect=AssertionError("trial launched before path validation")):
        assert runner.main(args) == 2
    assert not output.exists()


def test_candidate_comparison_never_overwrites_an_existing_report(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    _prepare_comparison_smoke(inputs, runner)
    output = tmp_path / "immutable.json"
    args = _comparison_args(inputs, output)

    assert runner.main(args) == 0
    original = output.read_bytes()
    assert runner.main(args) == 2
    assert output.read_bytes() == original
    assert output.with_suffix(output.suffix + ".attempts.jsonl").is_file()


def test_candidate_comparison_rejects_changed_inputs_after_smoke_preflight(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    _prepare_comparison_smoke(inputs, runner)
    inputs["baseline"].write_text("changed after smoke\n", encoding="utf-8")
    output = tmp_path / "stale-smoke.json"

    assert runner.main(_comparison_args(inputs, output)) == 2
    assert not output.exists()


def test_candidate_comparison_preflight_prints_fingerprint_without_running_or_writing(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    smoke = tmp_path / "future-smoke.txt"
    inputs["config_data"]["smoke_test"] = {
        "status": "pending",
        "output_inspected": False,
        "permissions_verified": False,
        "trial_id": "pending-smoke",
        "artifact_path": str(smoke),
    }
    inputs["config"].write_text(json.dumps(inputs["config_data"]), encoding="utf-8")
    output = tmp_path / "preflight-report.json"
    captured = io.StringIO()
    with redirect_stdout(captured):
        exit_code = runner.main(_comparison_args(inputs, output) + ["--preflight"])

    report = json.loads(captured.getvalue())
    assert exit_code == 0
    assert report["artifact_kind"] == "candidate_comparison_preflight"
    assert report["execution_fingerprint"]
    assert not output.exists()
    assert not smoke.exists()


def test_candidate_comparison_smoke_rejects_changed_timeout_or_dependency(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    dependency = tmp_path / "runner-dependency.txt"
    dependency.write_text("version one", encoding="utf-8")
    config = inputs["config_data"]
    config["command_dependencies"] = [str(dependency)]
    config["command_timeout_seconds"] = 30
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner)
    dependency.write_text("version two", encoding="utf-8")
    config["command_timeout_seconds"] = 31
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")

    assert runner.main(_comparison_args(inputs, tmp_path / "stale-runtime.json")) == 2


def test_candidate_comparison_interrupt_cancels_queued_trials_and_preserves_partial_log(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is the verified execution path for this smoke run."
    config["concurrency"] = 1
    config["command_argv"] = [
        sys.executable,
        "-c",
        "import time; time.sleep(0.2); print('required')",
    ]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "interrupted.json"

    with patch.object(runner, "as_completed", side_effect=KeyboardInterrupt):
        assert runner.main(_comparison_args(inputs, output, adapter="command")) == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "incomplete"
    attempts_path = Path(report["attempts_log"])
    attempts = [json.loads(line) for line in attempts_path.read_text(encoding="utf-8").splitlines()]
    assert len(attempts) == 4
    assert sum(attempt["status"] == "not_run" for attempt in attempts) >= 3
    assert len({attempt["trial_id"] for attempt in attempts}) == 4


def test_public_unrelated_target_fixture_passes_comparison_preflight(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    fixture_root = ROOT / "evals" / "fixtures" / "superb-skills"
    comparison_root = fixture_root / "comparison-contract"
    args = [
        "--candidate", f"baseline={fixture_root / 'targets' / 'document-assistant' / 'baseline' / 'SKILL.md'}",
        "--candidate", f"improved={fixture_root / 'targets' / 'document-assistant' / 'improved' / 'SKILL.md'}",
        "--suite", str(comparison_root / "suite.json"),
        "--partition-plan", str(comparison_root / "partition.json"),
        "--config", str(comparison_root / "config.json"),
        "--output", str(tmp_path / "preflight.json"),
        "--preflight",
    ]

    assert runner.main(args) == 0
    assert not (tmp_path / "preflight.json").exists()


def test_candidate_comparison_permission_gate_writes_only_a_blocked_report(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    config = inputs["config_data"]
    config["authorization"] = {"run": False, "output": True}
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner)
    output = tmp_path / "blocked.json"

    assert runner.main(_comparison_args(inputs, output)) == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "blocked"
    assert report["results"] == []
    assert report["recommendation"]["status"] == "blocked"


def test_candidate_comparison_keeps_holdout_cases_out_of_development_runs(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    suite = json.loads(inputs["suite"].read_text(encoding="utf-8"))
    suite["cases"] = [case for case in suite["cases"] if case["id"] != "no-private-guidance"]
    suite["red_green"] = []
    inputs["suite"].write_text(json.dumps(suite), encoding="utf-8")
    partition = json.loads(inputs["partition"].read_text(encoding="utf-8"))
    partition["groups"] = [{"id": "required", "case_ids": ["required-guidance"]}]
    partition["folds"] = [{"id": "fold-1", "group_ids": ["required"], "training_group_ids": [], "case_ids": ["required-guidance"], "case_count": 1}]
    partition["holdout"] = {"case_ids": ["no-private-guidance"], "case_count": 1, "status": "frozen"}
    partition["holdout"]["groups"] = [{"id": "private", "case_ids": ["no-private-guidance"]}]
    inputs["partition"].write_text(json.dumps(partition), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner)
    output = tmp_path / "development-only.json"

    assert runner.main(_comparison_args(inputs, output)) == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["partition"]["holdout_case_ids"] == ["no-private-guidance"]
    assert {result["case_id"] for result in report["results"]} == {"required-guidance"}
    assert report["output_destination"] == str(output.resolve())


def test_candidate_comparison_rejects_holdout_content_in_the_supplied_suite(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    partition = json.loads(inputs["partition"].read_text(encoding="utf-8"))
    partition["holdout"] = {"case_ids": ["no-private-guidance"], "case_count": 1, "status": "frozen"}
    partition["holdout"]["groups"] = [{"id": "private", "case_ids": ["no-private-guidance"]}]
    inputs["partition"].write_text(json.dumps(partition), encoding="utf-8")

    assert runner.main(_comparison_args(inputs, tmp_path / "holdout-leak.json")) == 2


def test_candidate_comparison_rejects_a_group_shared_by_development_and_holdout(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    partition = json.loads(inputs["partition"].read_text(encoding="utf-8"))
    partition["groups"] = [{"id": "required", "case_ids": ["required-guidance"]}]
    partition["folds"] = [{"id": "fold-1", "group_ids": ["required"], "training_group_ids": [], "case_ids": ["required-guidance"], "case_count": 1}]
    partition["holdout"] = {"case_ids": ["no-private-guidance"], "case_count": 1, "status": "frozen", "groups": [{"id": "required", "case_ids": ["no-private-guidance"]}]}

    try:
        runner.validate_partition(partition, {"required-guidance"})
    except runner.ConfigurationError as exc:
        assert "overlaps a development group" in str(exc)
    else:
        raise AssertionError("a partition group must not cross the development/holdout boundary")


def test_safe_names_remain_unique_for_distinct_identifiers() -> None:
    runner = load_candidate_comparison_runner()
    assert runner.safe_name("a/b") != runner.safe_name("a_b")
    assert runner.trial_identity("run", "a:b", "c") != runner.trial_identity("run", "a", "b:c")
    assert runner.trial_identity("run", "candidate", "case") == runner.trial_identity("run", "candidate", "case")


def test_command_trials_keep_a_suite_named_candidate_file_separate(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    candidate_root = tmp_path / "candidate-source"
    candidate_root.mkdir()
    candidate_file = candidate_root / "suite.json"
    candidate_file.write_text("required\nprivate\n", encoding="utf-8")
    inputs["baseline"] = candidate_file
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is the verified execution path for this smoke run."
    config["command_argv"] = [
        sys.executable,
        "-c",
        "from pathlib import Path; candidate=Path(r'{candidate}'); candidate_id=r'{candidate_id}'; helper_suite=Path(r'{suite}'); assert candidate.parent.name == 'candidate'; assert (candidate.name == 'suite.json') == (candidate_id == 'baseline'); assert helper_suite.name == 'suite.json' and helper_suite != candidate; print(candidate.read_text(encoding='utf-8'))",
    ]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "candidate-file-layout.json"

    assert runner.main(_comparison_args(inputs, output, adapter="command")) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["recommendation"]["selected_candidate_id"] == "improved"
    assert len({result["trial_id"] for result in report["results"]}) == 4


def test_candidate_hash_rejects_nested_symbolic_links(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    external = tmp_path / "external.txt"
    external.write_text("private", encoding="utf-8")
    package = tmp_path / "package"
    package.mkdir()
    try:
        os.symlink(external, package / "linked.txt")
    except (OSError, NotImplementedError):
        return

    try:
        runner.content_hash(package)
    except runner.ConfigurationError as exc:
        assert "symbolic link" in str(exc)
    else:
        raise AssertionError("symbolic links must not be included in hashed packages")


def test_candidate_comparison_rejects_a_partition_that_splits_or_drops_cases(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    invalid = json.loads(inputs["partition"].read_text(encoding="utf-8"))
    invalid["folds"][0]["case_ids"] = ["required-guidance"]
    inputs["partition"].write_text(json.dumps(invalid), encoding="utf-8")
    output = tmp_path / "invalid.json"

    assert runner.main(_comparison_args(inputs, output)) == 2
    assert not output.exists()


def test_candidate_comparison_rejects_partition_without_reproducibility_metadata(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    partition = json.loads(inputs["partition"].read_text(encoding="utf-8"))
    del partition["assignment"]
    inputs["partition"].write_text(json.dumps(partition), encoding="utf-8")

    assert runner.main(_comparison_args(inputs, tmp_path / "missing-partition-metadata.json")) == 2


def test_candidate_comparison_requires_observed_red_failure_for_selection(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    inputs["improved"].write_text("required\nprivate\n", encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner)
    output = tmp_path / "no-red-green.json"

    assert runner.main(_comparison_args(inputs, output)) == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["red_green_results"][0]["status"] == "green_failed"
    assert report["recommendation"]["status"] == "red_green_not_demonstrated"


def test_candidate_comparison_rejects_contradictory_partition_metadata(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    partition = json.loads(inputs["partition"].read_text(encoding="utf-8"))
    partition["coverage"] = {"status": "sufficient", "reason": "claimed sufficient"}
    partition["requested_holdout_percent"] = 50
    partition["assignment"]["stable_inputs"] = None
    inputs["partition"].write_text(json.dumps(partition), encoding="utf-8")

    assert runner.main(_comparison_args(inputs, tmp_path / "contradictory-partition.json")) == 2


def test_candidate_comparison_rejects_invalid_red_evidence_in_multi_case_criterion(tmp_path: Path) -> None:
    runner = load_candidate_comparison_runner()
    inputs = _comparison_inputs(tmp_path)
    suite = json.loads(inputs["suite"].read_text(encoding="utf-8"))
    suite["red_green"][0]["case_ids"] = ["required-guidance", "no-private-guidance"]
    inputs["suite"].write_text(json.dumps(suite), encoding="utf-8")
    config = inputs["config_data"]
    config["actual_runner"] = "local-command"
    config["substitution_reason"] = "The configured local command is the verified execution path for this smoke run."
    config["command_argv"] = [
        sys.executable,
        "-c",
        "from pathlib import Path; p=Path(r'{candidate}'); text=p.read_text(encoding='utf-8'); p.write_text(text + '\\nmutation', encoding='utf-8') if r'{candidate_id}' == 'baseline' and r'{case_id}' == 'required-guidance' else None; print(text)",
    ]
    inputs["config"].write_text(json.dumps(config), encoding="utf-8")
    _prepare_comparison_smoke(inputs, runner, adapter="command")
    output = tmp_path / "invalid-red-evidence.json"

    assert runner.main(_comparison_args(inputs, output, adapter="command")) == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "incomplete"
    assert report["red_green_results"][0]["status"] == "invalid_evidence"
    assert report["recommendation"]["status"] == "incomplete"


def test_research_briefing_routes_adjacent_tasks_before_research_checkpoint() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    lane = research.index("## Handle adjacent tasks directly")
    checkpoint = research.index("## Begin with a research-scope checkpoint")
    assert lane < checkpoint
    adjacent = research[lane:checkpoint]
    for phrase in (
        "complete the requested adjacent task directly",
        "Preserve supplied claims, numbers, meaning, scope",
        "ask one focused question",
        "Do not add an evidence assessment",
        "source-to-source comparison",
    ):
        assert phrase in adjacent
    assert "do not pause for research-scope confirmation" in research


def test_research_briefing_verifies_consequential_claims_before_synthesis() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    verification = research.index("## Verify before drafting")
    synthesis = research.index("## Synthesize objectively")
    assert verification < synthesis
    section = research[verification:synthesis]
    for phrase in (
        "consequential factual, numerical, comparative, causal, temporal",
        "requested questions, constraints, decision criteria",
        "targeted counterevidence",
        "preserve the affected claims as unverified",
        "re-check every consequential claim",
        "reconcile the draft against the requested coverage map",
    ):
        assert phrase in section


def test_research_checkpoint_offers_phases_only_for_defined_large_work() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    for phrase in (
        "multiple separable issues or research domains",
        "Do not warn about phasing merely because",
        "Do not propose or create phases by default",
        "without addressing work structure, proceed as one continuous briefing",
        "silence does not authorize research",
        "do not introduce a phase checkpoint unless the user requested phased work",
        "Research only the current phase",
        "Stop and wait for the user's explicit instruction to continue",
        "A progress update is not a completed checkpoint",
        "unreported findings or in-progress tool-call state",
    ):
        assert phrase in research


def test_research_opening_names_decision_shaping_sources() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    assert "opening summary name and directly link" in research
    assert "what each reference influenced" in research
    assert "two to five references" in research
    assert "claim-level citations in the body" in research


def test_svg_assets_are_referenced_and_sized() -> None:
    manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
    plugin_assets = {
        manifest["interface"]["composerIcon"]: ("24", "24", "0 0 24 24"),
        manifest["interface"]["logo"]: ("64", "64", "0 0 64 64"),
    }
    for relative, expected in plugin_assets.items():
        root = ET.parse(ROOT / relative.removeprefix("./")).getroot()
        assert (root.get("width"), root.get("height"), root.get("viewBox")) == expected

    for skill in ("remember-me", "research-briefing", "superb-skills", "teach-me"):
        assets = ROOT / "skills" / skill / "assets"
        for filename, expected in (
            ("icon-small.svg", ("24", "24", "0 0 24 24")),
            ("icon-large.svg", ("64", "64", "0 0 64 64")),
        ):
            root = ET.parse(assets / filename).getroot()
            assert (root.get("width"), root.get("height"), root.get("viewBox")) == expected


def test_remember_me_uses_targeted_authoritative_records() -> None:
    root = ROOT / "skills" / "remember-me"
    skill = read(root / "SKILL.md")
    records = read(root / "references" / "record-management.md")
    assert "Treat the index as the authority for topic routing" in skill
    assert "convenience cache" in skill
    assert "The canonical external source wins on conflict" in skill
    assert "Do not load every topic" in skill
    assert "Create no empty topic files" in skill
    assert "Do not create `history.md` until" in records
    assert "RMH-YYYY-MM-DD-NN" in records
    assert not (root / "index.md").exists()
    assert not (root / "history.md").exists()


def test_remember_me_topic_ownership_and_taxonomy() -> None:
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    for owner in (
        "career-coach:career-direction", "meal-planner:meal-planner",
        "meal-planner:personal-chef", "meal-planner:personal-shopper",
    ):
        assert owner in records
    for filename in (
        "communication-collaboration.md", "values-goals.md",
        "lifestyle-routines.md", "entertainment-interests.md",
        "travel-places.md", "household-relationships.md", "technology-tools.md",
    ):
        assert filename in records


def test_bundled_skills_consult_remember_me_selectively() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    assert "remember-me/index.md" in research
    assert "smallest sufficient set of relevant current context" in research
    assert "Expand retrieval when the bounded context" in research
    assert "silently changing durable memory" in research
    superb = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    assert "Consult `remember-me`" in superb
    assert "through the same contract" in superb
    assert "Never copy its retrieval, storage, or lifecycle procedure" in superb
    assert "remember-me/index.md" not in superb
    teaching = read(ROOT / "skills" / "teach-me" / "SKILL.md")
    assert "smallest sufficient set of relevant current context" in teaching
    assert "silently changing durable memory" in teaching
    assert "it is not evidence for an external claim" in research


def test_remember_me_contracts_preserve_authority_and_confirmation() -> None:
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    for heading in (
        "Teach Me to Research Briefing",
        "Bundled Skills to Remember Me: targeted consultation",
        "Bundled Skills to Remember Me: durable update request",
        "Remember Me to External Domain Owner",
    ):
        assert heading in contract
    assert "The Remember Me summary is a cache and pointer only" in contract
    assert "Other bundled skills must not maintain competing personal-profile files" in contract
    assert "Require confirmation before persisting an inference" in contract


def test_manifest_represents_all_bundled_skills() -> None:
    manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
    description = manifest["description"]
    assert "research" in description
    assert "adaptive teaching" in description
    assert "instruction design" in description
    assert "personal-context indexing" in description


def test_superb_skills_uses_conditional_memory() -> None:
    skill = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    reference = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    for trigger in (
        "persistent current state must survive extended work or conversation boundaries",
        "multiple workflows need one current authority",
        "history must remain reconstructable",
        "drift creates material risk",
    ):
        assert trigger in skill
    assert "Do not create persistent working-memory files by default" in skill
    assert "read the reference when this gate fails" in skill
    assert "Use one current-state file" not in skill
    assert "Designate exactly one source as authoritative" in reference
    assert "Read the working briefing first" in reference


def test_memory_guidance_prioritizes_recall_then_tokens_then_speed() -> None:
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")

    priorities = (
        "1. Preserve reliable recall",
        "2. Minimize the tokens",
        "3. Minimize the time",
    )
    positions = [memory.index(priority) for priority in priorities]
    assert positions == sorted(positions)
    assert "Never improve a lower-ranked objective by weakening a higher-ranked one" in memory
    assert "Reliable recall takes priority over reducing context tokens" in remember

    for artifact in (memory, remember, records, contract):
        assert "incomplete" in artifact
        assert "stale" in artifact
        assert "ambiguous" in artifact
        assert "conflicting" in artifact
        assert "consequential detail" in artifact

    assert "Keep the transaction narrow only when" in records
    assert "Expand beyond the index summary" in contract


def test_memory_maintenance_triggers_are_measurable_and_non_destructive() -> None:
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    for phrase in ("8 KiB", "16 KiB", "180 days", "conservative default design heuristic"):
        assert phrase in memory
        assert phrase in records
    assert "Any trigger can make an audit due. No trigger decides" in memory
    assert "A due trigger requires review, not automatic" in remember
    assert "Follow an explicit domain review policy when supplied" in memory
    assert "Use elapsed time for routine cleanup review; absolute file size is advisory" in remember
    triggers = records.split("make an audit due when", 1)[1].split("These numerical thresholds", 1)[0]
    assert "180 days" in triggers
    assert "8 KiB" not in triggers
    assert "16 KiB" not in triggers
    assert "not an independent audit trigger" in records
    assert "An unchanged healthy oversized file does not make another audit due" in records
    assert "no content changes are needed" in records
    assert "Incomplete or failed audits preserve the prior audit-completion metadata" in records
    assert "ordinary saves do not reset it" in records
    assert "Only a completed review of the full Remember Me file set" in records


def test_comparative_claims_require_basis_but_preserve_labeled_opinion() -> None:
    instruction = read(ROOT / "skills" / "superb-skills" / "references" / "instruction-design.md")
    evaluation = read(ROOT / "skills" / "superb-skills" / "references" / "evaluation.md")
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")

    for artifact in (instruction, research, remember):
        assert "explicit or implicit comparison" in artifact
        assert "comparison set" in artifact or "reference set" in artifact
        assert "supported absolute property" in artifact
        assert "subjective" in artifact
    assert "unsupported explicit and implicit comparisons" in evaluation
    assert "reference set and supporting evidence" in contract


def test_record_identity_prefers_provider_ids_and_permalinks() -> None:
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")

    for artifact in (memory, remember, records, contract):
        assert "provider" in artifact
        assert "library or container" in artifact
        assert "permalink" in artifact
        assert "fallback" in artifact
    assert "Treat a copy as a new identity" in records
    assert "never choose among same-named candidates by filename alone" in memory


def test_memory_review_uses_independent_trigger_classes() -> None:
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")

    for artifact in (memory, records):
        for phrase in (
            "25 material changes", "25 percent", "conflict", "pointer",
            "bounded retrieval", "substantial unrelated content",
        ):
            assert phrase in artifact
    assert "No trigger decides the lifecycle action by itself" in memory
    assert "table of contents or section map is a conditional retrieval aid" in records


def test_context_compaction_is_distinct_from_record_compaction() -> None:
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")

    assert "Conversation-context compaction is different from persistent-record compaction" in memory
    assert "Conversation-context compaction is not persistent-record compaction" in records
    for artifact in (memory, records):
        assert "recheck exact" in artifact


def test_memory_audit_validates_complete_staged_rewrite_and_rejects_loss() -> None:
    audit = load_memory_audit_validator()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        before = root / "before"
        after = root / "after"
        invalid = root / "invalid"
        broken = root / "broken"
        before.mkdir()
        after.mkdir()
        invalid.mkdir()
        broken.mkdir()
        original = (
            "# Index\n\n- Record ID: PREF-001\n- Limit: $5,000\n- Source: user interview\n"
            "- Prefers concise updates.\n- History: RMH-2026-01-01-01\n- duplicate wording\n"
        )
        history = "# History\n\n## RMH-2026-01-01-01\n\n- Prior preference: detailed updates.\n"
        (before / "index.md").write_text(original, encoding="utf-8")
        (before / "history.md").write_text(history, encoding="utf-8")
        compact_index = (
            "# Index\n\n- Record ID: PREF-001\n- Prefers concise status updates.\n"
            "- History: RMH-2026-01-01-01\n"
        )
        (after / "index.md").write_text(compact_index, encoding="utf-8")
        (after / "topic.md").write_text("# Topic\n\n- Limit: $5,000\n- Source: user interview\n", encoding="utf-8")
        (after / "history.md").write_text(history, encoding="utf-8")
        (invalid / "index.md").write_text(compact_index, encoding="utf-8")
        (invalid / "topic.md").write_text("# Topic\n\n- Source: user interview\n", encoding="utf-8")
        (invalid / "history.md").write_text(history, encoding="utf-8")
        (broken / "index.md").write_text(compact_index, encoding="utf-8")
        (broken / "topic.md").write_text("# Topic\n\n- Limit: $5,000\n- Source: user interview\n", encoding="utf-8")
        (broken / "history.md").write_text("# History\n\n- Prior preference: detailed updates.\n", encoding="utf-8")

        before_items = [
            {"id": "limit", "kind": "numeric_rule", "path": "index.md", "text": "- Limit: $5,000"},
            {"id": "source", "kind": "provenance", "path": "index.md", "text": "- Source: user interview"},
            {"id": "record-id", "kind": "stable_id", "path": "index.md", "text": "- Record ID: PREF-001"},
            {"id": "history-pointer", "kind": "pointer", "path": "index.md", "text": "- History: RMH-2026-01-01-01",
             "target_path": "history.md", "target_text": "## RMH-2026-01-01-01"},
            {"id": "history-item", "kind": "historical_item", "path": "history.md", "text": "- Prior preference: detailed updates."},
            {"id": "preference", "kind": "active_fact", "path": "index.md", "text": "- Prefers concise updates."},
            {"id": "duplicate", "kind": "valueless_duplicate", "path": "index.md", "text": "- duplicate wording"},
        ]
        after_items = [
            {"id": "limit-after", "kind": "numeric_rule", "path": "topic.md", "text": "- Limit: $5,000"},
            {"id": "source-after", "kind": "provenance", "path": "topic.md", "text": "- Source: user interview"},
            {"id": "record-id-after", "kind": "stable_id", "path": "index.md", "text": "- Record ID: PREF-001"},
            {"id": "history-pointer-after", "kind": "pointer", "path": "index.md", "text": "- History: RMH-2026-01-01-01",
             "target_path": "history.md", "target_text": "## RMH-2026-01-01-01"},
            {"id": "history-item-after", "kind": "historical_item", "path": "history.md", "text": "- Prior preference: detailed updates."},
            {"id": "preference-after", "kind": "active_fact", "path": "index.md", "text": "- Prefers concise status updates."},
        ]
        decisions = [
            {"before_id": "limit", "disposition": "moved", "after_ids": ["limit-after"]},
            {"before_id": "source", "disposition": "moved", "after_ids": ["source-after"]},
            {"before_id": "record-id", "disposition": "retained", "after_ids": ["record-id-after"]},
            {"before_id": "history-pointer", "disposition": "retained", "after_ids": ["history-pointer-after"]},
            {"before_id": "history-item", "disposition": "retained", "after_ids": ["history-item-after"]},
            {"before_id": "preference", "disposition": "reworded", "after_ids": ["preference-after"],
             "semantic_review": "passed", "justification": "Equivalent concise wording"},
            {"before_id": "duplicate", "disposition": "removed", "after_ids": [],
             "justification": "Valueless duplicate"},
        ]
        ledger = {
            "schema_version": 1,
            "before_files": audit.markdown_inventory(before),
            "after_files": audit.markdown_inventory(after),
            "before_items": before_items,
            "after_items": after_items,
            "decisions": decisions,
            "new_after_ids": [],
        }
        audit.validate_audit(before, after, ledger)

        invalid_ledger = dict(ledger)
        invalid_ledger["after_files"] = audit.markdown_inventory(invalid)
        invalid_ledger["after_items"] = [item for item in after_items if item["id"] != "limit-after"]
        failed = False
        try:
            audit.validate_audit(before, invalid, invalid_ledger)
        except audit.AuditError:
            failed = True
        assert failed
        assert (before / "index.md").read_text(encoding="utf-8") == original

        broken_ledger = dict(ledger)
        broken_ledger["after_files"] = audit.markdown_inventory(broken)
        pointer_failed = False
        try:
            audit.validate_audit(before, broken, broken_ledger)
        except audit.AuditError:
            pointer_failed = True
        assert pointer_failed
        assert (before / "history.md").read_text(encoding="utf-8") == history


def test_contract_is_single_and_explicit() -> None:
    contracts = list(ROOT.rglob("handoff-contracts.md"))
    assert contracts == [ROOT / "shared" / "handoff-contracts.md"]
    skill = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    assert "../../shared/handoff-contracts.md" in skill


def test_record_backup_preserves_authority_and_has_three_modes() -> None:
    root = ROOT / "skills" / "record-backup"
    skill = read(root / "SKILL.md")
    agent = read(root / "agents" / "openai.yaml")
    schema = read(root / "references" / "configuration-and-schema.md")
    daily = read(root / "references" / "daily-sync.md")
    weekly = read(root / "references" / "weekly-reconciliation.md")
    restore = read(root / "references" / "restore-staging.md")

    assert "GitHub is backup and recovery history only" in skill
    assert "An on-demand backup uses the daily-sync procedure" in skill
    assert "independent remote read" in skill
    assert "weekly reconciliation" in skill
    assert "records" in schema and "backup-index.json" in schema
    assert "do not create an empty content commit" in daily
    assert "rediscover the complete configured scope" in weekly
    assert "Obtain explicit confirmation" in restore
    assert "$record-backup" in agent


def test_record_backup_snapshot_validator_checks_hashes_and_unindexed_files() -> None:
    validator = load_snapshot_validator()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        record = root / "records" / "remember-me" / "topic.md"
        record.parent.mkdir(parents=True)
        content = b"# Topic\n\nA durable record.\n"
        record.write_bytes(content)
        manifest = {
            "schema_version": 1,
            "records": [{
                "repository_path": "records/remember-me/topic.md",
                "source_provider": "test",
                "source_container": "container-1",
                "source_id": "source-1",
                "source_path": "remember-me/topic.md",
                "owner": "test",
                "classification": "current-authority",
                "byte_size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }],
        }
        (root / "backup-index.json").write_text(json.dumps(manifest), encoding="utf-8")
        second = root / "records" / "career" / "topic.md"
        second.parent.mkdir(parents=True)
        second_content = b"# Career\n\nAnother scoped record.\n"
        second.write_bytes(second_content)
        manifest["records"].append({
            "repository_path": "records/career/topic.md",
            "source_provider": "other-provider",
            "source_container": "container-2",
            "source_id": "source-1",
            "source_path": "career/topic.md",
            "owner": "test",
            "classification": "current-authority",
            "byte_size": len(second_content),
            "sha256": hashlib.sha256(second_content).hexdigest(),
        })
        (root / "backup-index.json").write_text(json.dumps(manifest), encoding="utf-8")
        (root / "receipts").mkdir()
        (root / "receipts" / "run-1.json").write_text('{"status":"verified"}', encoding="utf-8")
        result = validator.validate(root, root / "backup-index.json")
        assert result["record_count"] == 2
        duplicate = dict(manifest["records"][0])
        duplicate["repository_path"] = "records/remember-me/duplicate.md"
        duplicate_path = root / "records" / "remember-me" / "duplicate.md"
        duplicate_path.write_bytes(content)
        manifest["records"].append(duplicate)
        (root / "backup-index.json").write_text(json.dumps(manifest), encoding="utf-8")
        try:
            validator.validate(root, root / "backup-index.json")
        except validator.SnapshotError as exc:
            assert "duplicate source identity" in str(exc)
        else:
            raise AssertionError("duplicate scoped source identity was not detected")
        manifest["records"].pop()
        duplicate_path.unlink()
        (root / "backup-index.json").write_text(json.dumps(manifest), encoding="utf-8")
        record.write_bytes(content + b"changed")
        try:
            validator.validate(root, root / "backup-index.json")
        except validator.SnapshotError:
            pass
        else:
            raise AssertionError("content hash mismatch was not detected")
        record.write_bytes(content)
        (root / "records" / "unindexed.md").write_bytes(b"extra")
        try:
            validator.validate(root, root / "backup-index.json")
        except validator.SnapshotError as exc:
            assert "unindexed files" in str(exc)
        else:
            raise AssertionError("unindexed file was not detected")


def test_superb_skills_routes_conditional_references() -> None:
    root = ROOT / "skills" / "superb-skills"
    skill = read(root / "SKILL.md")
    expected = {
        "instruction-design.md": "one-time prompts",
        "project-instructions-template.md": "drafting project or custom instructions",
        "plugin-architecture.md": "multiple coordinated skills",
        "evaluation.md": "evaluation design or behavior checks",
        "preferences-and-lessons.md": "missing preferences",
        "working-memory.md": "persistent current state",
    }
    for filename, trigger in expected.items():
        assert (root / "references" / filename).is_file()
        assert f"](references/{filename})" in skill
        assert trigger in skill
    assert "load no reference merely because it exists" in skill
    assert "one observed operational mistake with a potentially reusable remedy" in skill


def test_preferences_and_lessons_guidance_keeps_records_and_permissions_separate() -> None:
    guidance = read(ROOT / "skills" / "superb-skills" / "references" / "preferences-and-lessons.md")
    for phrase in (
        "Project setting",
        "Task override",
        "Verified lesson",
        "partial-write branches",
        "One occurrence is not proof of a recurring pattern",
        "A single observation may support a *preventive* lesson only after a target-relevant remedy has been verified",
        "stable lesson ID, observed mistake, verified remedy, applicability, evidence reference, date, owner, status, and permission limits",
        "when applicability changes, revise the scope",
        "Lessons never authorize a benchmark rerun",
        "create a competing cache",
        "Do not add preference intake, durable lessons, or a record layer to a simple target",
    ):
        assert phrase in guidance
    assert "../../../shared/handoff-contracts.md#bundled-skills-to-remember-me-targeted-consultation" in guidance
    assert "remember-me/index.md" not in guidance
    assert "target's own runtime records" in guidance


def test_preference_fixture_covers_each_intake_and_lesson_branch() -> None:
    fixture_root = ROOT / "evals" / "fixtures" / "superb-skills"
    target = read(fixture_root / "targets" / "preference-dependent" / "SKILL.md")
    settings = read(fixture_root / "targets" / "preference-dependent" / "settings.yaml")
    lessons = read(fixture_root / "targets" / "preference-dependent" / "lessons.md")
    manifest = json.loads(read(fixture_root / "manifest.json"))
    scenarios = {scenario["id"]: scenario for scenario in manifest["scenarios"]}

    for phrase in ("needs_focused_input", "partial-write", "stale lesson", "task-specific preference", "currently authorized bound"):
        assert phrase in target
    assert "authorization:" in settings and "project_write: explicit_only" in settings
    assert "L-001" in lessons and "L-002" in lessons
    assert scenarios["pref-missing-settings"]["expected_final_state"]["status"] == "needs_focused_input"
    assert scenarios["pref-partial-write"]["expected_final_state"]["persistence_verified"] is False
    assert scenarios["pref-stale-lesson"]["expected_final_state"]["lesson_applied"] is False
    assert scenarios["pref-conflicting-settings"]["expected_final_state"]["project_settings_changed"] is False


def test_superb_skills_entrypoint_is_thin_and_keeps_other_skills_authoritative() -> None:
    root = ROOT / "skills" / "superb-skills"
    skill = read(root / "SKILL.md")
    route = skill.split("## Route the work", 1)[1].split("## Keep one authority", 1)[0]
    assert len(skill) <= 6000
    assert "Do not reproduce platform behavior" in skill
    assert "A routing sentence is not permission" in skill
    assert "research-scope checkpoint" not in skill
    assert "remember-me/index.md" not in skill
    assert "8 KiB" not in skill
    classification = route.index("Classify the request before acting")
    workflow_selection = route.index("Select the smallest applicable workflow")
    completion = route.index("Complete only that mode")
    assert classification < workflow_selection < completion
    assert "Do not implement planning or review requests" in route
    assert "Implement the smallest complete change" not in route
    assert "bounded handoff" in skill


def test_plugin_architecture_guides_coordination_assets_and_release_checks() -> None:
    architecture = read(ROOT / "skills" / "superb-skills" / "references" / "plugin-architecture.md")
    for phrase in (
        "Delegate only bounded work",
        "Let scripts own repeated deterministic transformations",
        "Keep simple target work simple",
        "legibility at 32×32",
        "no larger than 128×128",
        "Dimension checks are structural evidence",
        "Preserve suitable SVG assets",
        "version decision",
        "applicable mirrored metadata",
        "Do not hard-code this repository's mirror names",
    ):
        assert phrase in architecture


def test_instruction_design_enforces_budget_and_prevents_authority_leakage() -> None:
    root = ROOT / "skills" / "superb-skills"
    instruction = read(root / "references" / "instruction-design.md")
    template = read(root / "references" / "project-instructions-template.md")
    for phrase in (
        "8,000-character limit",
        "7,600 characters",
        "Count the complete copy-ready artifact",
        "Revise any artifact above the hard limit before delivery",
        "Do not copy the procedures of `research-briefing`, `remember-me`, `skill-creator`",
        "Keep commentary, rationale, and placement recommendations outside the artifact",
    ):
        assert phrase in instruction
    assert "omit unused headings" in template
    assert "do not reproduce another skill's procedure" in template


def test_instruction_length_checker_enforces_hard_limit_and_preserves_headroom() -> None:
    checker = load_instruction_length_checker()
    assert checker.classify(7600, 7600, 8000) == "WITHIN_TARGET"
    assert checker.classify(7601, 7600, 8000) == "WITHIN_LIMIT_ABOVE_TARGET"
    assert checker.classify(8001, 7600, 8000) == "OVER_LIMIT"
    with TemporaryDirectory() as directory:
        artifact = Path(directory) / "instructions.md"
        artifact.write_text("x" * 8001, encoding="utf-8", newline="")
        assert checker.count_characters(artifact) == 8001
        assert checker.main([str(artifact)]) == 1


def test_skill_creator_remains_implementation_authority() -> None:
    skill = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    plugin = read(ROOT / "skills" / "superb-skills" / "references" / "plugin-architecture.md")
    assert "Invoke `skill-creator`" in skill
    assert "Do not duplicate its platform-specific implementation procedure" in skill
    assert "Treat it as authoritative" in plugin


def test_teach_me_researches_before_teaching_and_avoids_reflexive_agreement() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    workflow = read(root / "references" / "teaching-workflow.md")
    personality = read(root / "references" / "personalities" / "nicer-socrates.md")

    assert "Complete the research before substantive teaching begins" in skill
    assert "must not begin substantive teaching" in read(ROOT / "shared" / "handoff-contracts.md")
    assert "A chain of reasonable answers can still drift" in workflow
    assert "resisting reflexive agreement" in personality
    assert "constitutive of the concept" in personality


def test_teach_me_separates_philosophy_workflow_evidence_and_style() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    philosophy = read(root / "references" / "learning-philosophy.md")
    workflow = read(root / "references" / "teaching-workflow.md")
    evidence = read(root / "references" / "learning-evidence.md")
    personality = read(root / "references" / "personalities" / "nicer-socrates.md")

    assert "Do not load it for an ordinary lesson merely because it exists" in skill
    assert "conceptual authority" in philosophy
    assert "operational authority" in workflow
    assert "current evidence authority" in evidence
    assert "controls tone, pacing, question presentation, and feedback style" in personality
    assert "This record supports the philosophy" in skill


def test_teach_me_builds_capability_without_overgeneralizing_learning_methods() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    philosophy = read(root / "references" / "learning-philosophy.md")
    workflow = read(root / "references" / "teaching-workflow.md")

    assert "task completion without a learning goal as outside this skill" in skill
    assert "Neither generation-first nor explanation-first is universally preferable" in philosophy
    assert "example-first" in workflow
    assert "generation-first" in workflow
    assert "least substitutive assistance" in workflow
    assert "commission" in workflow and "omission" in workflow
    assert "Do not claim mastery" in workflow
    assert "do not imply that the skill will return autonomously" in skill


def test_teach_me_routes_visual_art_domains_without_2d_leakage() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    visual = read(root / "references" / "domains" / "visual-arts.md")
    drawing = read(root / "references" / "domains" / "drawing-painting.md")

    shared_link = "](references/domains/visual-arts.md)"
    family_link = "](references/domains/drawing-painting.md)"
    assert shared_link in skill and family_link in skill
    assert skill.index(shared_link) < skill.index(family_link)
    assert "without a making-skill goal" in skill
    assert "Do not import drawing or painting procedures" in visual
    assert "Do not load it for sculpture, ceramics, weaving" in drawing
    assert "If the artwork itself is unavailable, do not pretend to inspect it" in drawing
    assert "Do not assume cross-medium transfer" in visual
    assert "Apply the shared visual-arts reference-use procedure" in drawing


def test_teach_me_evidence_has_provenance_intake_and_maintenance_boundaries() -> None:
    evidence = read(ROOT / "skills" / "teach-me" / "references" / "learning-evidence.md")

    for phrase in (
        "Initial provenance",
        "the supplied 2026-09-06 audit reported checking the source",
        "Candidate-source intake",
        "User-supplied claims remain attributed and `candidate`",
        "A due date means review is due; it does not authorize research",
        "LE-001",
        "LE-025",
    ):
        assert phrase in evidence


def test_teach_me_default_personality_is_modular_and_purposeful() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    personality = read(root / "references" / "personalities" / "nicer-socrates.md")

    assert "](references/personalities/nicer-socrates.md)" in skill
    assert "Load only the selected personality" in skill
    assert "fall back to `nicer-socrates.md`" in skill
    assert "Ask one question at a time" in personality
    assert "Do not ask a question merely because" in personality
    assert "Skip directly to explanation" in personality


def test_teach_me_memory_is_targeted_and_does_not_store_session_noise() -> None:
    skill = read(ROOT / "skills" / "teach-me" / "SKILL.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")

    assert "smallest sufficient set of relevant current context" in skill
    assert "Do not persist lesson transcripts" in skill
    assert "Never maintain a competing learner profile" in skill
    assert "`superb-skills`, `research-briefing`, or `teach-me`" in contract


def test_teach_me_standalone_mirrors_references_without_plugin_dependencies() -> None:
    plugin_root = ROOT / "skills" / "teach-me"
    standalone_root = ROOT.parents[1] / "skills" / "teach-me"
    plugin = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))

    for relative in (
        Path("references/learning-evidence.md"),
        Path("references/learning-philosophy.md"),
        Path("references/learning-plan-research.md"),
        Path("references/teaching-workflow.md"),
        Path("references/personalities/nicer-socrates.md"),
        Path("references/personalities/financial-fiduciary.md"),
        Path("references/domains/visual-arts.md"),
        Path("references/domains/drawing-painting.md"),
        Path("references/domains/if-you-can.md"),
        Path("assets/icon-small.svg"),
        Path("assets/icon-large.svg"),
    ):
        assert read(plugin_root / relative) == read(standalone_root / relative)

    standalone_skill = read(standalone_root / "SKILL.md")
    standalone_agent = read(standalone_root / "agents" / "openai.yaml")
    assert "Standalone adaptive teaching and advice skill" in standalone_skill
    assert f'metadata:\n  version: "{plugin["version"]}"\n---' in standalone_skill
    assert "proceed without a research-scope confirmation pause" in standalone_skill
    for forbidden in ("work-smarter", "remember-me", "research-briefing", "handoff-contracts"):
        assert forbidden not in standalone_skill
        assert forbidden not in standalone_agent
    assert "dependencies:" not in standalone_agent


def test_eval_suite_covers_required_behaviors() -> None:
    cases = json.loads(read(ROOT / "evals" / "regression.json"))["cases"]
    ids = {case["id"] for case in cases}
    assert {
        "route-superb-skills", "negative-route", "research-handoff",
        "instruction-hard-limit", "instruction-existing-skill-authority",
        "instruction-local-override",
        "research-nontrigger", "research-confirmation", "memory-no-file",
        "memory-single-file", "memory-split", "memory-conflict",
        "memory-missing", "memory-recall-before-token-reduction",
        "memory-token-reduction-before-speed", "memory-narrow-update-fallback",
        "memory-maintenance-trigger", "memory-audit-success",
        "memory-audit-loss-failure", "research-opening-influential-sources",
        "research-large-request-phase-choice",
        "research-ordinary-request-no-phase-warning",
        "research-phase-choice-default-continuous",
        "research-phase-checkpoint-no-response",
        "research-phased-work-stops-after-log",
        "research-waiver-no-phase-pause",
        "research-unsupported-implicit-comparison",
        "research-supported-comparison", "research-subjective-comparison",
        "memory-nonsize-audit-trigger", "memory-context-vs-record-compaction",
        "memory-conditional-toc", "memory-provider-identity-pointer",
        "contract-failure", "backward-compatibility",
        "remember-explicit", "remember-indirect-query", "remember-negative",
        "remember-owned-topic", "remember-external-career",
        "remember-targeted-consultation", "remember-missing-source",
        "remember-stale-summary", "remember-source-conflict",
        "remember-duplicate-index", "remember-task-override",
        "remember-history-gate", "remember-sensitive-content",
        "teach-explicit", "teach-indirect", "teach-negative-direct-answer",
        "teach-research-first", "teach-research-failure",
        "teach-default-personality", "teach-selected-personality",
        "teach-stuck-explanation", "teach-premise-challenge",
        "teach-memory-consultation", "teach-memory-no-session-write",
        "teach-learning-plan", "teach-novice-example-first",
        "teach-generation-first", "teach-target-vs-supporting",
        "teach-reconstruct-after-feedback", "teach-fade-and-restore",
        "teach-tool-boundary", "teach-commission-and-omission",
        "teach-pedagogy-evidence", "teach-reminder-boundary",
        "teach-visual-digital-plan", "teach-visual-tool-only",
        "teach-visual-production-negative", "teach-visual-mixed-production-learning",
        "teach-visual-critique-learning", "teach-visual-critique-no-image",
        "teach-visual-material-art", "teach-visual-nonmaking",
        "teach-visual-calligraphy", "teach-visual-aid-boundary",
        "teach-visual-stylized-imagination", "teach-visual-cross-medium-transfer",
        "teach-visual-reference-study", "record-backup-daily-sync",
        "record-backup-weekly-reconcile", "record-backup-manual-subset",
        "record-backup-restore-staging",
    }.issubset(ids)


def test_superb_skills_evaluation_suite_has_cases_and_provenance_contract() -> None:
    suite_path = ROOT / "evals" / "superb-skills-evaluation.json"
    suite = json.loads(read(suite_path))
    assert suite["schema_version"] == "1.0.0"
    assert suite["suite_id"] == "superb-skills-evaluation"
    assert suite["suite_version"] == "2026-09-28.2"
    assert suite["status"] == "design_only"
    assert set(suite["result_states"]) == {"passed", "failed", "blocked", "not_run"}
    assert len(suite["source_evidence"]) == 4
    assert all(source["access"] == "authenticated_browser_readable" for source in suite["source_evidence"])
    assert all(source["review_status"] == "reviewed_user_report_2026-09-21" for source in suite["source_evidence"])
    assert all(source["independent_reproduction"] == "not_run" for source in suite["source_evidence"])
    assert all("url" not in source for source in suite["source_evidence"])

    cases = {case["id"]: case for case in suite["cases"]}
    required_cases = {
        "scope-simple-rewrite-no-evaluation",
        "preference-intake-missing-decision",
        "ownership-personal-project-evidence",
        "lesson-repeated-permission-output-failure",
        "candidate-comparison-common-protocol",
        "runner-unavailable-explicit-block",
        "result-persistence-current-report",
        "icon-raster-dimensions-and-legibility",
        "red-green-authority-duplication",
        "context-transfer-without-history",
        "red-green-version-synchronization",
        "target-design-preference-dependent-skill",
        "target-design-competing-candidates",
        "target-design-simple-no-evaluation",
        "negative-no-durable-record-for-style-edit",
    }
    assert required_cases.issubset(cases)
    for case in suite["cases"]:
        for field in ("id", "family", "kind", "input", "intended_behavior", "success_criteria", "failure_criteria", "evidence_mode"):
            assert case.get(field), f"missing {field} in {case.get('id')}"
        assert case["success_criteria"]
        assert case["failure_criteria"]

    assert cases["red-green-authority-duplication"]["baseline_evidence"] == ["conv-1"]
    assert cases["red-green-version-synchronization"]["baseline_evidence"] == ["conv-2", "conv-3"]
    assert cases["lesson-repeated-permission-output-failure"]["baseline_evidence"] == ["conv-4"]
    assert len(cases) == len(suite["cases"])
    assert len({case["id"] for case in suite["cases"]}) == len(suite["cases"])
    assert all(case["evidence_mode"] in suite["evidence_modes"] for case in suite["cases"])

    fixture_path = ROOT / "evals" / "fixtures" / "superb-skills" / "manifest.json"
    assert suite["fixture_manifest"] == "plugins/work-smarter/evals/fixtures/superb-skills/manifest.json"
    fixture = json.loads(read(fixture_path))
    assert fixture["fixture_id"] == "superb-skills-fixtures"
    assert fixture["fixture_version"] == "2026-09-28.2"
    fixture_root = fixture_path.parent
    target_by_id = {target["id"]: target for target in fixture["targets"]}
    profile_by_id = {profile["id"]: profile for profile in fixture["environment_profiles"]}
    artifact_by_id = {artifact["id"]: artifact for artifact in fixture["artifacts"]}
    candidate_set_by_id = {candidate_set["id"]: candidate_set for candidate_set in fixture["candidate_sets"]}
    scenarios = {scenario["id"]: scenario for scenario in fixture["scenarios"]}
    assert len(target_by_id) == len(fixture["targets"])
    assert len(scenarios) == len(fixture["scenarios"])
    assert len(candidate_set_by_id) == len(fixture["candidate_sets"])

    partition_policy = fixture["partition_policy"]
    assert partition_policy["schema_version"] == "1.0.0"
    assert partition_policy["supported_development_folds"] == [3, 5, 10]
    initial_partition = partition_policy["initial_configuration"]
    assert initial_partition["scheme"] == "grouped_development_evaluation"
    assert initial_partition["holdout_percent"] == 10
    assert initial_partition["development_fold_count"] == 5
    assert initial_partition["group_key"] == "partition_group"
    assert initial_partition["development_validation_percent_by_fold"] == {"3": 30, "5": 18, "10": 9}
    assert "round-half-up" in initial_partition["rounding_rule"]
    exposure_policy = partition_policy["exposure_policy"]
    assert exposure_policy["holdout_content_before_freeze"] == "implementation_agent_prohibited"
    assert exposure_policy["rubric_before_freeze"] == "implementation_agent_prohibited"
    assert set(exposure_policy["required_log_fields"]) == {
        "case_or_group_ids", "actor", "role", "timestamp", "reason", "exposure_type",
    }
    plans = {plan["id"]: plan for plan in partition_policy["plans"]}
    assert set(plans) == {"designer-evaluation", "downstream-target-evaluation"}
    suite_case_ids = {case["id"] for case in suite["cases"]}
    designer_plan = plans["designer-evaluation"]
    assert designer_plan["scope"] == "designer_quality"
    assert set(designer_plan["case_ids"]) == suite_case_ids
    groups = {group["id"]: group for group in designer_plan["groups"]}
    assert len(groups) == len(designer_plan["groups"])
    grouped_case_ids = [case_id for group in groups.values() for case_id in group["case_ids"]]
    assert set(grouped_case_ids) == suite_case_ids
    assert len(grouped_case_ids) == len(set(grouped_case_ids))
    assert all(group["case_ids"] and 1 <= group["fold"] <= 5 for group in groups.values())
    ordered_groups = sorted(
        groups.values(),
        key=lambda group: hashlib.sha256(
            f"{group['id']}|{suite['suite_id']}|{suite['suite_version']}".encode("utf-8")
        ).hexdigest(),
    )
    assert [group["fold"] for group in ordered_groups] == [index % 5 + 1 for index in range(len(ordered_groups))]
    development = designer_plan["development"]
    assert development["scheme"] == "grouped_development_evaluation"
    assert development["fold_count"] == 5
    assert development["total_case_count"] == len(suite_case_ids)
    folds = {fold["id"]: fold for fold in development["folds"]}
    assert set(folds) == {f"fold-{index}" for index in range(1, 6)}
    fold_case_ids = []
    for fold in folds.values():
        expected_ids = {
            case_id
            for group_id in fold["group_ids"]
            for case_id in groups[group_id]["case_ids"]
        }
        assert set(fold["case_ids"]) == expected_ids
        assert fold["case_count"] == len(expected_ids)
        assert fold["training_case_count"] == len(suite_case_ids) - fold["case_count"]
        fold_case_ids.extend(fold["case_ids"])
    assert set(fold_case_ids) == suite_case_ids
    assert len(fold_case_ids) == len(set(fold_case_ids))
    assert sum(fold["case_count"] for fold in folds.values()) == len(suite_case_ids)
    assert designer_plan["holdout"] == {
        "requested_percent": 10,
        "case_ids": [],
        "case_count": 0,
        "status": "ineligible_as_untouched_holdout",
        "reason": "All current fixture cases were visible during design and are exposed development evidence; no case may be relabeled as an untouched final holdout.",
    }
    assert designer_plan["exposure"]["exposure_log"] == [{
        "case_or_group_ids": ["all-current-fixture-groups"],
        "actor": "evaluation-author",
        "role": "designer",
        "timestamp": "2026-09-21",
        "reason": "fixture_design_and_structural_review",
        "exposure_type": "development_fixture",
    }]
    downstream_plan = plans["downstream-target-evaluation"]
    assert downstream_plan["scope"] == "target_runtime"
    assert downstream_plan["case_source"] == "target_supplied_suite"
    assert downstream_plan["development"]["supported_fold_counts"] == [3, 5, 10]
    assert downstream_plan["holdout"]["status"] == "required_after_target_suite_freeze"
    assert downstream_plan["exposure"]["implementation_agent_access"] == "must_remain_prohibited_before_final_validation"

    required_scenario_parents = {
        "authority-duplication-review": "red-green-authority-duplication",
        "context-transfer-without-history": "context-transfer-without-history",
        "version-metadata-missing": "red-green-version-synchronization",
        "pref-supplied-settings": "target-design-preference-dependent-skill",
        "pref-missing-settings": "target-design-preference-dependent-skill",
        "pref-context-unavailable": "target-design-preference-dependent-skill",
        "pref-partial-write": "target-design-preference-dependent-skill",
        "pref-stale-lesson": "target-design-preference-dependent-skill",
        "pref-conflicting-settings": "target-design-preference-dependent-skill",
        "benchmark-preflight-gate": "lesson-repeated-permission-output-failure",
        "runner-unavailable-explicit-block": "runner-unavailable-explicit-block",
        "runner-input-gate-not-executed": "runner-input-delivery-gate-failure",
        "runner-input-delivery-design": "runner-input-delivery-gate-design",
        "result-persistence-current-report": "result-persistence-current-report",
        "comparison-complete": "target-design-competing-candidates",
        "comparison-missing-output": "target-design-competing-candidates",
        "comparison-interrupted-valid-attempts": "target-design-competing-candidates",
        "comparison-reviewer-unavailable": "target-design-competing-candidates",
        "simple-normalizer-positive": "target-design-simple-no-evaluation",
        "simple-normalizer-negative": "target-design-simple-no-evaluation",
    }
    assert set(required_scenario_parents).issubset(scenarios)
    delivery_failure = next(case for case in suite["cases"] if case["id"] == "runner-input-delivery-gate-failure")
    delivery_design = next(case for case in suite["cases"] if case["id"] == "runner-input-delivery-gate-design")
    assert delivery_failure["evidence_mode"] == "behavioral_trial"
    assert "does not send candidate sources or start design before exact-byte local verification" in delivery_failure["success_criteria"]
    assert "does not score or disqualify the candidate" in delivery_failure["success_criteria"]
    assert "names the smallest authorized same-execution round-trip preflight as the next action" in delivery_failure["success_criteria"]
    assert "does not label the whole phase blocked while that bounded action remains available" in delivery_failure["success_criteria"]
    assert "labels the whole phase blocked without an actionable next step" in delivery_failure["failure_criteria"]
    assert "reruns completed work or overwrites its evidence" in delivery_failure["failure_criteria"]
    assert {"requires observed execution, exit status, and matching hashes before design", "prohibits stale checkout substitution and repository writes"}.issubset(
        set(delivery_design["success_criteria"])
    )
    assert {
        "does not misstate the anticipated overflow as an observed platform limit",
        "chooses a supported non-duplicative delivery route and bounds each call",
        "preflights the same route with harmless data at least as large as the planned maximum chunk",
        "requires observed execution, exit status, exact output/hash, and local artifact retrieval before candidate delivery",
        "does not resend candidate payload or start design before the preflight is evidenced",
    }.issubset(set(delivery_design["success_criteria"]))
    failed_gate_scenario = scenarios["runner-input-gate-not-executed"]
    assert failed_gate_scenario["expected_final_state"] == {
        "status": "roundtrip_preflight_only",
        "previous_evidence_preserved": True,
        "exact_byte_return_verified": True,
        "candidate_sources_transmitted": False,
        "design_started": False,
        "automatic_retry": False,
    }
    delivery_scenario = scenarios["runner-input-delivery-design"]
    assert delivery_scenario["expected_final_state"]["design_requires_gate_pass"] is True
    assert delivery_scenario["expected_final_state"]["repository_writes"] is False
    assert delivery_scenario["expected_final_state"]["capacity_proof_requires_max_chunk"] is True
    assert delivery_scenario["expected_final_state"]["candidate_sources_transmitted"] is False
    assert delivery_scenario["expected_final_state"]["design_started"] is False

    for target in fixture["targets"]:
        target_root = fixture_root / target["path"]
        for relative in target["content_files"]:
            assert (target_root / relative).is_file(), f"missing fixture target file: {target['id']}/{relative}"
        for scenario_id in target["scenario_ids"]:
                assert scenario_id in scenarios
                assert scenarios[scenario_id].get("target_id") == target["id"]

    preference_target = target_by_id["preference-dependent-target"]
    assert {"SKILL.md", "settings.yaml", "lessons.md"} <= set(preference_target["content_files"])
    preference_scenario_ids = {
        "pref-supplied-settings",
        "pref-missing-settings",
        "pref-context-unavailable",
        "pref-partial-write",
        "pref-stale-lesson",
        "pref-conflicting-settings",
    }
    assert set(preference_target["scenario_ids"]) == preference_scenario_ids
    assert scenarios["pref-missing-settings"]["expected_final_state"] == {"status": "needs_focused_input", "persistent_settings_write": False}
    assert scenarios["pref-context-unavailable"]["expected_final_state"]["fabricated_context"] is False
    assert scenarios["pref-partial-write"]["expected_final_state"]["persistence_verified"] is False
    assert scenarios["pref-stale-lesson"]["expected_final_state"]["lesson_applied"] is False
    assert scenarios["pref-conflicting-settings"]["expected_final_state"] == {"status": "complete", "task_override_applied": True, "project_settings_changed": False}

    for candidate_set in fixture["candidate_sets"]:
        assert candidate_set["case_id"] in cases
        assert len(candidate_set["candidates"]) == 2
        for candidate in candidate_set["candidates"]:
            assert (fixture_root / candidate["path"]).is_file()
        for scenario_id in candidate_set["scenario_ids"]:
            assert scenario_id in scenarios
            assert scenarios[scenario_id].get("candidate_set_id") == candidate_set["id"]

    for artifact in fixture["artifacts"]:
        artifact_path = fixture_root / artifact["path"]
        assert artifact_path.is_file(), f"missing fixture artifact: {artifact['id']}"
        if artifact_path.suffix == ".json":
            json.loads(read(artifact_path))

    complete_artifact = json.loads(read(fixture_root / "artifacts" / "comparison-complete.json"))
    assert complete_artifact["artifact_state"] == "complete"
    assert complete_artifact["artifact_kind"] == "synthetic_result_fixture"
    assert complete_artifact["evidence_scope"] == "fixture_only"
    assert complete_artifact["execution_status"] == "synthetic_complete"
    assert complete_artifact["suite_id"] == suite["suite_id"]
    assert complete_artifact["suite_version"] == suite["suite_version"]
    assert complete_artifact["suite_content_hash"] == exact_sha256(suite_path)
    assert complete_artifact["rubric_id"] == suite["rubric_id"]
    assert complete_artifact["rubric_version"] == suite["rubric_version"]
    candidate_paths = {
        candidate["id"]: fixture_root / candidate["path"]
        for candidate in candidate_set_by_id["document-assistant"]["candidates"]
    }
    required_result_fields = {
        "trial_id",
        "case_id",
        "candidate_id",
        "candidate_content_hash",
        "target_content_hash",
        "suite_id",
        "suite_version",
        "suite_content_hash",
        "rubric_id",
        "rubric_version",
        "requested_runner",
        "actual_runner",
        "requested_reasoning_effort",
        "actual_reasoning_effort",
        "environment_identity",
        "substitution_reason",
        "permissions_profile",
        "concurrency",
        "started_at",
        "finished_at",
        "status",
        "evidence_valid",
        "observed_evidence",
        "loaded_references",
        "failure_reason",
        "output_reference",
    }
    assert set(complete_artifact["required_records"]) == required_result_fields
    assert {result["candidate_id"] for result in complete_artifact["results"]} == set(candidate_paths)
    assert {result["status"] for result in complete_artifact["results"]} == {"failed", "passed"}
    for result in complete_artifact["results"]:
        assert required_result_fields.issubset(result)
        assert result["case_id"] == "target-design-competing-candidates"
        assert result["suite_id"] == suite["suite_id"]
        assert result["suite_version"] == suite["suite_version"]
        assert result["suite_content_hash"] == complete_artifact["suite_content_hash"]
        assert result["rubric_id"] == suite["rubric_id"]
        assert result["rubric_version"] == suite["rubric_version"]
        assert result["environment_identity"].startswith("fixture:")
        assert result["substitution_reason"]
        assert result["candidate_content_hash"] == exact_sha256(candidate_paths[result["candidate_id"]])
        assert result["target_content_hash"] == result["candidate_content_hash"]
        assert result["observed_evidence"]
        if result["status"] == "failed":
            assert result["failure_reason"]
        else:
            assert result["failure_reason"] is None
        assert result["output_reference"] == "artifacts/comparison-complete.json"
    assert complete_artifact["recommendation"]["selected_candidate_id"] == "document-assistant-improved"
    assert complete_artifact["recommendation"]["raw_evidence"]
    assert complete_artifact["recommendation"]["limitations"]

    missing_output = json.loads(read(fixture_root / "artifacts" / "comparison-missing-output.json"))
    assert missing_output["artifact_kind"] == "synthetic_result_fixture"
    assert set(missing_output["required_records"]) == required_result_fields
    partial_result = missing_output["result"]
    assert set(missing_output["missing_records"]) == {"observed_evidence", "output_reference"}
    assert required_result_fields - set(partial_result) == set(missing_output["missing_records"])

    interrupted = json.loads(read(fixture_root / "artifacts" / "comparison-interrupted.json"))
    assert interrupted["artifact_kind"] == "synthetic_result_fixture"
    assert interrupted["retry_authorization"] == "invalid_attempts_only"
    frozen = interrupted["frozen_configuration"]
    for field in ("suite_id", "suite_version", "suite_content_hash", "rubric_id", "rubric_version", "requested_runner", "actual_runner", "environment_identity", "substitution_reason", "permissions_profile", "concurrency"):
        assert frozen.get(field) is not None
    attempts = {attempt["trial_id"]: attempt for attempt in interrupted["attempts"]}
    assert set(attempts) == set(interrupted["valid_attempts"] + interrupted["invalid_attempts"])
    for attempt in attempts.values():
        assert required_result_fields.issubset(attempt)
        assert attempt["candidate_id"] in candidate_paths
        assert attempt["candidate_content_hash"] == exact_sha256(candidate_paths[attempt["candidate_id"]])
        assert attempt["target_content_hash"] == attempt["candidate_content_hash"]
        assert attempt["suite_content_hash"] == frozen["suite_content_hash"]
        assert attempt["rubric_version"] == frozen["rubric_version"]
        assert attempt["environment_identity"] == frozen["environment_identity"]
    assert all(attempts[trial_id]["status"] == "passed" for trial_id in interrupted["valid_attempts"])
    assert all(attempts[trial_id]["status"] == "failed" for trial_id in interrupted["invalid_attempts"])
    assert interrupted["retry_rule"].startswith("retry only")

    for scenario in fixture["scenarios"]:
        for field in (
            "parent_case_id",
            "environment_profile",
            "starting_state",
            "user_input",
            "available_tools",
            "expected_actions",
            "prohibited_actions",
            "expected_final_state",
        ):
            assert scenario.get(field), f"missing scenario field {field}: {scenario.get('id')}"
        assert scenario["parent_case_id"] in cases
        assert scenario["environment_profile"] in profile_by_id
        if "target_id" in scenario:
            assert scenario["target_id"] in target_by_id
        if "candidate_set_id" in scenario:
            assert scenario["candidate_set_id"] in candidate_set_by_id

    assert {scenario_id: scenarios[scenario_id]["parent_case_id"] for scenario_id in required_scenario_parents} == required_scenario_parents

    for case in suite["cases"]:
        if "fixture_ref" in case:
            ref_type, ref_id = case["fixture_ref"].split(":", 1)
            catalogs = {
                "target": target_by_id,
                "profile": profile_by_id,
                "artifact": artifact_by_id,
                "comparison": candidate_set_by_id,
            }
            assert ref_type in catalogs
            assert ref_id in catalogs[ref_type]
        for scenario_id in case.get("runtime_scenario_ids", []):
            assert scenario_id in scenarios
            assert scenarios[scenario_id]["parent_case_id"] == case["id"]

    invalid_results = {item["id"]: item for item in suite["invalid_result_examples"]}
    assert set(invalid_results) == {"missing-output", "permission-not-granted", "runner-unavailable", "input-gate-not-executed", "interrupted-with-valid-attempts"}
    assert {item["required_status"] for item in invalid_results.values()} <= set(suite["result_states"])
    assert {item["must_not_be_counted_as"] for item in invalid_results.values()} <= {"passed", "complete_comparison"}
    assert invalid_results["missing-output"]["required_status"] == "failed"
    assert invalid_results["permission-not-granted"]["required_status"] == "blocked"
    assert invalid_results["runner-unavailable"]["required_status"] == "blocked"
    assert invalid_results["input-gate-not-executed"]["required_status"] == "blocked"
    assert invalid_results["interrupted-with-valid-attempts"]["required_status"] == "failed"
    assert invalid_results["interrupted-with-valid-attempts"]["must_not_be_counted_as"] == "complete_comparison"
    assert set(suite["designer_scorecard"]["required_record"]) == {"score", "evidence_span", "unresolved_limitation", "target_trial_decision", "grader_id"}
    scorecard_rules = suite["designer_scorecard"]["criterion_rules"]
    assert scorecard_rules["required_dimensions"] == "Every dimension must be scored; a score of 0 is a blocking failure."
    assert set(scorecard_rules["critical_failures"]) == {
        "fabricated source or runtime evidence",
        "unauthorized persistence or action",
        "holdout or rubric leakage",
        "ignored explicit task boundary",
        "missing target ownership for a persistent rule",
    }
    assert "same case_id, criterion_id, candidate boundary, and rubric version" in scorecard_rules["paired_red_green"]
    required_provenance = set(suite["provenance_requirements"]["required_fields"])
    assert {"trial_id", "candidate_content_hash", "target_content_hash", "suite_content_hash", "actual_runner", "environment_identity", "substitution_reason", "status", "evidence_valid", "observed_evidence", "loaded_references"}.issubset(required_provenance)
    assert len(suite["designer_scorecard"]["dimensions"]) == 5
    assert "target_package" in suite["clean_context_target_trial"]["required_inputs"]

    protocol = read(ROOT / "evals" / "superb-skills-evaluation-protocol.md")
    superb_skill = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    evaluation_reference = read(ROOT / "skills" / "superb-skills" / "references" / "evaluation.md")
    assert "Surface blockers at their gate: state observed evidence, unknowns, and the smallest resolving action." in superb_skill
    assert "## Resolve blockers at each gate" in evaluation_reference
    assert "Do not call the whole phase blocked while that action remains available." in evaluation_reference
    assert "## Verify inputs before a clean-context trial" in evaluation_reference
    assert "commands_run: []" in evaluation_reference
    assert "smallest resolving action" in protocol
    assert "Pause for user input only when required input or authority is missing" in protocol
    for phrase in (
        "Deterministic checks",
        "Behavioral trials",
        "Environment checks",
        "Reviewed evidence ledger",
        "Target-design cases and scoring",
        "fixture manifest",
        "`0` means absent",
        "invalid-result fixtures",
        "Clean-context target-trial contract",
        "put the case's operational permission envelope in the agent-facing prompt",
        "Do not rely on evaluator-only manifests, READMEs, rubrics, or hidden setup notes",
        "a child's `out_of_scope` result does not imply the designer must refuse an in-scope request",
        "grouped development evaluation",
        "five folds",
        "untouched final holdout",
        "exposure log",
        "fresh final holdout",
        "An observed failure is not itself a green result",
        "Neither `blocked` nor `not_run` may be counted as a pass",
        "retry only failed or invalid attempts",
        "mark only this gate blocked",
        "smallest supported bounded route",
        "exact returned bytes locally",
        "No provider calls, benchmark runs, installation, publication",
    ):
        assert phrase in protocol

    for evidence_path in (
        suite_path,
        ROOT / "evals" / "superb-skills-evaluation-protocol.md",
        ROOT / "evals" / "superb-skills-requirements.md",
    ):
        assert "chatgpt.com/s/" not in read(evidence_path)


if __name__ == "__main__":
    tests = sorted(
        (name, value)
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    )
    for name, test in tests:
        test()
        print(f"PASS {name}")
    print(f"PASS {len(tests)} plugin tests")


def test_save_trial_validator_rejects_missing_acceptance_coverage(tmp_path, monkeypatch):
    validator = load_validator()
    copytree(ROOT / 'evals' / 'remember-me-save', tmp_path / 'evals' / 'remember-me-save')
    manifest = tmp_path / 'evals' / 'remember-me-save' / 'manifest.json'
    data = json.loads(read(manifest))
    for case in data['cases']:
        case['acceptance'] = [ae for ae in case['acceptance'] if ae != 'AE10']
    manifest.write_text(json.dumps(data))
    monkeypatch.setattr(validator, 'ROOT', tmp_path)
    with pytest.raises(AssertionError, match='AE1-AE10'):
        validator.validate_save_trials()


def test_remember_me_runtime_references_and_static_policy():
    import yaml
    skill = ROOT / 'skills' / 'remember-me'
    metadata = yaml.safe_load(read(skill / 'agents' / 'openai.yaml'))
    assert metadata['policy']['allow_implicit_invocation'] is True
    assert (skill / 'references' / 'transcript-sources.md').is_file()
    assert 'ordinary-save-verification' in read(skill / 'SKILL.md')
    assert 'setup_confirmed' in read(ROOT / 'shared' / 'handoff-contracts.md')
    assert 'first-use/setup gate' in read(ROOT / 'skills' / 'research-briefing' / 'SKILL.md')
