from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "shopping"


def load_capture():
    spec = importlib.util.spec_from_file_location(
        "personal_shopper_invocation_capture", EVAL / "capture_invocation.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_runner():
    sys.path.insert(0, str(EVAL))
    try:
        spec = importlib.util.spec_from_file_location("personal_shopper_trial_runner", EVAL / "run_trial.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def load_scorer():
    sys.path.insert(0, str(EVAL))
    try:
        spec = importlib.util.spec_from_file_location("personal_shopper_trial_scorer", EVAL / "score_trial.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def load_receipt_builder():
    sys.path.insert(0, str(EVAL))
    try:
        spec = importlib.util.spec_from_file_location(
            "personal_shopper_live_receipt_builder", EVAL / "build_live_receipt.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_host_stream_keeps_lifecycle_events_and_links_tool_results():
    capture = load_capture()
    raw = b"\n".join(
        json.dumps(event).encode()
        for event in (
            {"type": "thread.started", "thread_id": "thread-1"},
            {"type": "turn.started", "turn_id": "turn-1"},
            {"type": "item.started", "item": {
                "id": "call-1", "type": "mcp_tool_call", "server": "google-drive",
                "tool": "get_spreadsheet_range", "arguments": {"range": "A1:C3"},
                "status": "in_progress",
            }},
            {"type": "item.completed", "item": {
                "id": "call-1", "type": "mcp_tool_call", "server": "google-drive",
                "tool": "get_spreadsheet_range", "arguments": {"range": "A1:C3"},
                "result": {"values": [["Item", "Record ID", "Price"], ["Rice", "r-1", 2.5]]},
                "status": "completed",
            }},
            {"type": "item.completed", "item": {
                "id": "message-1", "type": "agent_message", "text": "Read complete."}},
            {"type": "turn.completed", "turn_id": "turn-1"},
        )
    ) + b"\n"

    events = capture.parse_host_stream(raw)
    calls = capture.mcp_tool_ledger(events)

    assert [event["type"] for event in events] == [
        "thread.started", "turn.started", "item.started", "item.completed",
        "item.completed", "turn.completed",
    ]
    assert calls == [{
        "call_id": "call-1",
        "server": "google-drive",
        "tool": "get_spreadsheet_range",
        "arguments": {"range": "A1:C3"},
        "result": {"values": [["Item", "Record ID", "Price"], ["Rice", "r-1", 2.5]]},
        "status": "completed",
        "event_indexes": [2, 3],
    }]


def test_incomplete_or_malformed_host_stream_cannot_be_treated_as_complete():
    capture = load_capture()

    with pytest.raises(ValueError, match="incomplete"):
        capture.parse_host_stream(b'{"type":"thread.started","thread_id":"thread-1"}')
    with pytest.raises(ValueError, match="invalid"):
        capture.parse_host_stream(b'{"type":"thread.started"}\nnot-json\n')


def test_failed_and_unrecognized_calls_remain_in_the_host_stream():
    capture = load_capture()
    raw = (
        b'{"type":"thread.started","thread_id":"thread-1"}\n'
        b'{"type":"item.completed","item":{"id":"call-2","type":"mcp_tool_call",'
        b'"server":"google-drive","tool":"batch_update_spreadsheet",'
        b'"arguments":{"range":"A1"},"error":"denied","status":"failed"}}\n'
        b'{"type":"item.completed","item":{"id":"shell-1","type":"command_execution",'
        b'"command":"cat /tmp/private","status":"completed"}}\n'
    )

    events = capture.parse_host_stream(raw)
    calls = capture.mcp_tool_ledger(events)

    assert len(events) == 3
    assert calls[0]["status"] == "failed"
    assert calls[0]["tool"] == "batch_update_spreadsheet"
    assert events[2]["item"]["type"] == "command_execution"


def test_profile_staging_exposes_only_declared_runtime_files(tmp_path):
    capture = load_capture()
    source = tmp_path / "source"
    package = source / "plugins" / "personal-shopper"
    (package / ".codex-plugin").mkdir(parents=True)
    (package / "skills" / "personal-shopper" / "references").mkdir(parents=True)
    (package / "assets").mkdir()
    (package / "evals" / "shopping").mkdir(parents=True)
    (package / ".codex-plugin" / "plugin.json").write_text('{"name":"personal-shopper"}\n')
    (package / "skills" / "personal-shopper" / "SKILL.md").write_text("---\nname: personal-shopper\n---\n")
    (package / "skills" / "personal-shopper" / "references" / "workflow.md").write_text("runtime")
    (package / "assets" / "icon.svg").write_text("<svg />")
    (package / "evals" / "shopping" / "hidden.json").write_text('{"secret":"hidden"}')
    manifest = {
        "candidate": {
            "packages": {
                "personal-shopper": {
                    "source_root": "plugins/personal-shopper",
                    "files": [".codex-plugin/plugin.json", "assets/**", "skills/**"],
                    "plugin_id": "personal-shopper",
                }
            },
            "profiles": {"shopper-alone": {
                "packages": ["personal-shopper"],
                "provider_plugins": [],
                "provider_apps": [],
            }},
        }
    }

    workspace = tmp_path / "trial" / "workspace"
    result = capture.stage_profile(source, workspace, manifest, "shopper-alone")

    staged = workspace / "plugins" / "personal-shopper"
    assert (staged / "skills" / "personal-shopper" / "SKILL.md").is_file()
    assert (staged / "assets" / "icon.svg").is_file()
    assert not (staged / "evals").exists()
    assert result["packages"] == ["personal-shopper"]
    assert result["files"]
    assert (workspace / ".agents" / "plugins" / "marketplace.json").is_file()
    config = (workspace / ".codex" / "config.toml").read_text()
    assert '[plugins."personal-shopper@shopping-trial"]' in config
    assert "[apps._default]\nenabled = false\ndefault_tools_enabled = false" in config
    assert "shell_tool = false" in config
    assert "unified_exec = false" in config
    assert "[apps." not in config or "[apps._default]" in config


def test_planner_profiles_stage_every_transitive_local_contract(tmp_path):
    capture = load_capture()
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    repo_root = ROOT.parent.parent
    required = (
        "plugins/meal-planner/shared/record-management.md",
        "plugins/meal-planner/shared/handoff-contracts.md",
        "plugins/meal-planner/shared/artifact-formatting.md",
        "plugins/meal-planner/shared/cleanup-migration.md",
    )
    for profile_id in ("planner-fallback", "full-handoff"):
        result = capture.stage_profile(repo_root, tmp_path / profile_id, manifest, profile_id)
        for relative in required:
            assert relative in result["files"]


def test_ownership_profile_stages_work_smarter_local_contract_dependencies(tmp_path):
    capture = load_capture()
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    repo_root = ROOT.parent.parent

    result = capture.stage_profile(
        repo_root, tmp_path / "ownership-profile", manifest, "ownership-integration"
    )

    assert "plugins/work-smarter/shared/handoff-contracts.md" in result["files"]
    assert "plugins/work-smarter/shared/record-audits.md" in result["files"]
    assert not any(path.startswith("plugins/career-coach/") for path in result["files"])
    assert not any(path.startswith("plugins/meal-planner/") for path in result["files"])


def test_staging_rejects_an_unstaged_local_reference_before_creating_workspace(tmp_path):
    capture = load_capture()
    source = tmp_path / "source"
    package = source / "plugins" / "example"
    (package / ".codex-plugin").mkdir(parents=True)
    (package / "skills" / "example").mkdir(parents=True)
    (package / ".codex-plugin" / "plugin.json").write_text('{"name":"example"}\n')
    (package / "skills" / "example" / "SKILL.md").write_text(
        "---\nname: example\n---\n[required contract](references/required.md)\n"
    )
    manifest = {
        "candidate": {
            "packages": {
                "example": {
                    "source_root": "plugins/example",
                    "files": [".codex-plugin/plugin.json", "skills/**"],
                }
            },
            "profiles": {"example": {"packages": ["example"]}},
        }
    }
    workspace = tmp_path / "trial" / "workspace"

    with pytest.raises(ValueError, match="package-local reference"):
        capture.stage_profile(source, workspace, manifest, "example")

    assert not workspace.exists()


def test_staging_rejects_package_reference_escapes(tmp_path):
    capture = load_capture()
    source = tmp_path / "source"
    package = source / "plugins" / "example"
    (package / ".codex-plugin").mkdir(parents=True)
    (package / "skills" / "example").mkdir(parents=True)
    (package / ".codex-plugin" / "plugin.json").write_text('{"name":"example"}\n')
    (package / "skills" / "example" / "SKILL.md").write_text(
        "---\nname: example\n---\n[external](../../../../outside.md)\n"
    )
    (source / "outside.md").write_text("outside the plugin package")
    manifest = {
        "candidate": {
            "packages": {
                "example": {
                    "source_root": "plugins/example",
                    "files": [".codex-plugin/plugin.json", "skills/**"],
                }
            },
            "profiles": {"example": {"packages": ["example"]}},
        }
    }

    with pytest.raises(ValueError, match="escapes its package"):
        capture.stage_profile(source, tmp_path / "trial", manifest, "example")


def test_candidate_identity_uses_local_package_file_declarations(tmp_path):
    capture = load_capture()
    source = tmp_path / "source"
    remember = source / "plugins" / "work-smarter" / "skills" / "remember-me"
    remember.mkdir(parents=True)
    (remember / "SKILL.md").write_text("---\nname: remember-me\n---\nfirst")
    external = source / "provider" / "SKILL.md"
    external.parent.mkdir()
    external.write_text("provider instructions")
    manifest = {
        "candidate": {
            "packages": {
                "work-smarter": {
                    "source_root": "plugins/work-smarter",
                    "files": ["skills/remember-me/**"],
                },
                "google-drive": {
                    "runtime_plugin_id": "google-drive@openai-curated-remote",
                    "files": ["SKILL.md"],
                },
            }
        }
    }

    patterns = capture.candidate_identity_patterns(manifest)
    included = capture._expand_files(source, patterns)
    first = capture.identity_digest(source, patterns)
    assert "plugins/work-smarter/skills/remember-me/SKILL.md" in included
    assert not any(path.startswith("provider/") for path in included)

    (remember / "SKILL.md").write_text("---\nname: remember-me\n---\nsecond")
    assert capture.identity_digest(source, patterns) != first


def test_installed_local_identity_matches_runner_path_convention(tmp_path):
    capture = load_capture()
    source = tmp_path / "source"
    skill = source / "plugins" / "personal-shopper" / "skills" / "personal-shopper" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: personal-shopper\n---\nshopping skill\n", encoding="utf-8")
    manifest = {
        "candidate": {
            "packages": {
                "personal-shopper": {
                    "source_root": "plugins/personal-shopper",
                    "files": ["skills/personal-shopper/**"],
                }
            },
            "profiles": {"shopper-alone": {"packages": ["personal-shopper"]}},
        }
    }
    runner_identity = {
        "personal-shopper/skills/personal-shopper/SKILL.md": hashlib.sha256(
            skill.read_bytes()
        ).hexdigest()
    }

    assert capture.installed_local_files_match(
        {"profile_id": "shopper-alone", "installed_file_sha256": runner_identity},
        manifest,
        source,
    )


@pytest.mark.parametrize("pattern", [None, ""])
def test_candidate_identity_rejects_invalid_file_patterns(pattern):
    capture = load_capture()
    manifest = {
        "candidate": {
            "packages": {
                "example": {"source_root": "plugins/example", "files": [pattern]},
            }
        }
    }

    with pytest.raises(ValueError, match="file pattern is invalid"):
        capture.candidate_identity_patterns(manifest)


def test_profile_rejects_unlisted_plugin_and_provider_tools(tmp_path):
    capture = load_capture()
    source = tmp_path / "source"
    package = source / "plugins" / "personal-shopper"
    (package / ".codex-plugin").mkdir(parents=True)
    (package / ".codex-plugin" / "plugin.json").write_text('{"name":"personal-shopper"}\n')
    manifest = {
        "candidate": {
            "packages": {
                "personal-shopper": {
                    "source_root": "plugins/personal-shopper",
                    "files": [".codex-plugin/plugin.json"],
                    "plugin_id": "personal-shopper",
                }
            },
            "profiles": {"shopper-alone": {
                "packages": ["personal-shopper"],
                "provider_plugins": [],
                "provider_apps": [],
            }},
        }
    }

    with pytest.raises(ValueError, match="unknown or invalid candidate profile"):
        capture.stage_profile(source, tmp_path / "trial", manifest, "not-a-profile")


def test_provider_profiles_enable_only_declared_tools_and_scope_write_approval(tmp_path):
    capture = load_capture()
    source = tmp_path / "source"
    shopper = source / "plugins" / "personal-shopper" / ".codex-plugin"
    provider = source / "provider" / ".codex-plugin"
    shopper.mkdir(parents=True)
    provider.mkdir(parents=True)
    (shopper / "plugin.json").write_text('{"name":"personal-shopper"}\n')
    (provider / "plugin.json").write_text('{"name":"google-drive"}\n')
    (source / "provider" / ".app.json").write_text(
        '{"apps":{"google-drive":{"id":"connector-test"}}}\n'
    )
    manifest = {
        "candidate": {
            "packages": {
                "personal-shopper": {
                    "source_root": "plugins/personal-shopper",
                    "files": [".codex-plugin/plugin.json"],
                    "plugin_id": "personal-shopper",
                },
                "google-drive": {
                    "files": [".codex-plugin/plugin.json", ".app.json"],
                    "plugin_id": "google-drive",
                },
            },
            "profiles": {
                "r25": {"packages": ["personal-shopper", "google-drive"]},
                "native-sheets-preservation": {"packages": ["personal-shopper", "google-drive"]},
            },
            "provider_apps": {"r25": [{
                "plugin": "google-drive",
                "tools": ["get_file_metadata", "get_spreadsheet_metadata", "get_spreadsheet_range"],
            }], "native-sheets-preservation": [{
                "plugin": "google-drive",
                "tools": ["get_file_metadata", "get_spreadsheet_metadata", "get_spreadsheet_range",
                          "get_spreadsheet_cells", "batch_update_spreadsheet"],
                "tool_approval_modes": {"batch_update_spreadsheet": "approve"},
            }]},
        },
    }

    workspace = tmp_path / "trial" / "workspace"
    capture.stage_profile(
        source, workspace, manifest, "r25", package_roots={"google-drive": source / "provider"}
    )

    config = (workspace / ".codex" / "config.toml").read_text()
    assert '[apps."connector-test"]' in config
    assert '[apps."connector-test".tools."get_spreadsheet_metadata"]' in config
    assert '[apps."connector-test".tools."get_spreadsheet_range"]' in config
    assert '[apps."connector-test".tools."get_file_metadata"]' in config
    assert "batch_update_spreadsheet" not in config
    assert "[apps._default]\nenabled = false\ndefault_tools_enabled = false" in config

    native_workspace = tmp_path / "trial" / "native-workspace"
    capture.stage_profile(
        source, native_workspace, manifest, "native-sheets-preservation",
        package_roots={"google-drive": source / "provider"},
    )
    native_config = (native_workspace / ".codex" / "config.toml").read_text()
    assert '[apps."connector-test".tools."batch_update_spreadsheet"]\nenabled = true\napproval_mode = "approve"' in native_config
    assert native_config.count("approval_mode =") == 1
    assert "destructive_enabled = false" in native_config
    assert "open_world_enabled = false" in native_config

    manifest["candidate"]["provider_apps"]["native-sheets-preservation"][0]["tool_approval_modes"] = {
        "unlisted_tool": "approve"
    }
    with pytest.raises(ValueError, match="approval overrides must approve only declared tools"):
        capture.stage_profile(
            source, tmp_path / "trial" / "invalid-native-workspace", manifest,
            "native-sheets-preservation", package_roots={"google-drive": source / "provider"},
        )


def test_runner_environment_is_allowlisted_and_excludes_shopping_secrets(monkeypatch):
    capture = load_capture()
    monkeypatch.setenv("SHOPPING_CANONICAL_GROCERY_LOCATOR", "private-locator")
    monkeypatch.setenv("GOOGLE_ACCESS_TOKEN", "private-token")
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("CODEX_HOME", "/private/codex-home")
    monkeypatch.setenv("SYSTEMROOT", "C:\\Windows")

    child = capture.filtered_environment(os.environ)

    assert child["PATH"] == "/usr/bin"
    assert child["CODEX_HOME"] == "/private/codex-home"
    assert child["SYSTEMROOT"] == "C:\\Windows"
    assert not ({"SHOPPING_CANONICAL_GROCERY_LOCATOR", "GOOGLE_ACCESS_TOKEN"} & child.keys())
    assert set(child) <= capture.SAFE_CHILD_ENV


def test_codex_command_requires_read_only_ephemeral_and_config_isolation():
    capture = load_capture()
    command = capture.build_codex_command("/tmp/candidate", "codex")

    assert command[:2] == ["codex", "exec"]
    assert "--json" in command
    assert "--ephemeral" in command
    assert "--ignore-user-config" not in command
    assert "--sandbox" in command and command[command.index("--sandbox") + 1] == "read-only"
    assert "--disable" in command and command[command.index("--disable") + 1] == "shell_tool"
    assert command[-3:-1] == ["--disable", "apps"]
    assert command[-1] == "-"
    assert "-c" in command and "trust_level=\"trusted\"" in command[command.index("-c") + 1]

    provider_command = capture.build_codex_command("/tmp/provider", "codex", apps_enabled=True)
    assert "apps" not in [provider_command[index + 1] for index, value in enumerate(provider_command[:-1])
                           if value == "--disable"]

    delegated_command = capture.build_codex_command(
        "/tmp/delegated", "codex", apps_enabled=False, multi_agent_enabled=True
    )
    assert "--enable" in delegated_command
    assert delegated_command[delegated_command.index("--enable") + 1] == "multi_agent"
    assert "multi_agent" not in [delegated_command[index + 1]
                                  for index, value in enumerate(delegated_command[:-1])
                                  if value == "--disable"]
    assert delegated_command[-3:-1] == ["--disable", "apps"]
    persisted_delegated = capture.build_codex_command(
        "/tmp/delegated", "codex", apps_enabled=False,
        multi_agent_enabled=True, persist_rollouts=True,
    )
    assert "--ephemeral" not in persisted_delegated
    assert persisted_delegated[persisted_delegated.index("--enable") + 1] == "multi_agent"
    with pytest.raises(ValueError, match="policy"):
        capture.build_codex_command("/tmp/invalid", persist_rollouts=True)


def test_delegation_rollout_capture_keeps_only_bound_parent_and_child(tmp_path):
    capture = load_capture()
    scorer = load_scorer()
    profile_home = tmp_path / "home"
    sessions = profile_home / "sessions" / "2026" / "10" / "30"
    sessions.mkdir(parents=True)
    parent_id, child_id = "parent-thread", "child-thread"
    activity_start = {"type": "event_msg", "payload": {"type": "item_completed",
        "item": {"type": "SubAgentActivity", "id": "activity-start", "kind": "started",
                 "agent_thread_id": child_id}}}
    activity_complete = {"type": "event_msg", "payload": {"type": "item_completed",
        "item": {"type": "SubAgentActivity", "id": "activity-complete", "kind": "completed",
                 "agent_thread_id": child_id}}}
    parent_path = sessions / f"rollout-2026-10-30T04-10-00-{parent_id}.jsonl"
    child_path = sessions / f"rollout-2026-10-30T04-10-01-{child_id}.jsonl"
    unrelated_path = sessions / "rollout-2026-10-30T04-10-02-unrelated.jsonl"
    parent_path.write_text("\n".join(json.dumps(x) for x in (activity_start, activity_complete)) + "\n")
    child_path.write_text('{"type":"session_meta"}\n')
    unrelated_path.write_text('{"type":"session_meta"}\n')
    output_dir = tmp_path / "evidence"
    output_dir.mkdir(mode=0o700)

    metadata = capture.capture_delegation_rollouts(profile_home, parent_id, output_dir)
    host = [{"type": "thread.started", "thread_id": parent_id}]
    result = {"delegation_rollouts": metadata}

    assert metadata["status"] == "captured"
    assert len(metadata["children"]) == 1
    assert not (output_dir / "delegation-rollouts" / "child-unrelated.jsonl").exists()
    assert scorer._delegation_capture(output_dir, result, host)["valid"]
    child_capture = output_dir / metadata["children"][0]["file"]
    child_capture.write_text('{"type":"session_meta","changed":true}\n')
    assert not scorer._delegation_capture(output_dir, result, host)["valid"]


def test_delegation_profile_and_resource_reader_are_limited_to_new_plan(tmp_path):
    runner = load_runner()
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    profile = manifest["candidate"]["profiles"]["full-handoff-delegating"]
    subcases = {item["id"]: item for item in manifest["synthetic_subcases"]}
    runner._validate_delegation_profile("full-handoff-delegating", profile,
                                        subcases["B10-AE12-new-plan"])
    with pytest.raises(ValueError, match="limited"):
        runner._validate_delegation_profile("full-handoff-delegating", profile, None)
    with pytest.raises(ValueError, match="limited"):
        runner._validate_delegation_profile("full-handoff-delegating", profile,
                                            subcases["B10-AE12-existing-plan"])

    profile_home = tmp_path / "profile"
    profile_home.mkdir()
    (profile_home / "config.toml").write_text('approval_policy = "never"\n')
    roots = {}
    identity = {}
    required = subcases["B10-AE12-new-plan"]["required_skill_resources"]
    for qualified in required:
        package, relative = qualified.split("/", 1)
        root = roots.setdefault(package, tmp_path / package)
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{qualified}\n")
        identity[qualified] = hashlib.sha256(path.read_bytes()).hexdigest()
    extra = roots["personal-shopper"] / "skills/personal-shopper/references/unneeded.md"
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("not exposed\n")
    identity["personal-shopper/skills/personal-shopper/references/unneeded.md"] = hashlib.sha256(
        extra.read_bytes()
    ).hexdigest()
    output = tmp_path / "output"
    output.mkdir(mode=0o700)
    reader = runner._register_integration_reader(profile_home, roots, identity, output, required)

    exposed = {f"{package}/{relative}" for package, files in reader["packages"].items() for relative in files}
    assert exposed == set(required)


def test_multi_agent_is_enabled_only_by_explicit_trial_profile(tmp_path):
    capture = load_capture()
    package_details = {"meal-planner": {"plugin_id": "meal-planner"}}
    delegated = capture._profile_config(
        tmp_path, ["meal-planner"], package_details, {"multi_agent": True}
    )
    isolated = capture._profile_config(
        tmp_path, ["meal-planner"], package_details, {"multi_agent": False}
    )

    assert "multi_agent = true" in delegated
    assert "shell_tool = false" in delegated
    assert "unified_exec = false" in delegated
    assert "apps = false" in delegated
    assert "multi_agent = false" in isolated


@pytest.mark.parametrize("executable", ["codex", "codex.exe", "codex.EXE"])
def test_direct_codex_executable_still_requires_isolated_command(executable, tmp_path):
    capture = load_capture()
    with pytest.raises(ValueError, match="fresh read-only isolated profile"):
        capture.run_codex([executable], tmp_path, tmp_path, "test")


def test_version_probe_timeout_marks_capture_incomplete(tmp_path, monkeypatch):
    capture = load_capture()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text("isolated profile\n", encoding="utf-8")
    stream = b'{"type":"thread.started","thread_id":"test"}\n'

    class CompletedSession:
        def __init__(self):
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO(stream)
            self.returncode = 0

        def wait(self, timeout=None):
            return self.returncode

        def poll(self):
            return self.returncode

    monkeypatch.setattr(capture.subprocess, "Popen", lambda *args, **kwargs: CompletedSession())

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs.get("timeout"))

    monkeypatch.setattr(capture.subprocess, "run", timeout)
    command = capture.build_codex_command(workspace, "codex")

    result = capture.run_codex(
        command, workspace, trial_dir, "Use the installed test skill.",
        environ={"CODEX_HOME": str(codex_home), "PATH": "/usr/bin"},
    )

    assert result["host_version"] == ""
    assert result["complete"] is False


def test_successful_host_without_completed_turn_is_incomplete(tmp_path, monkeypatch):
    capture = load_capture()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text("isolated profile\n", encoding="utf-8")

    class CompletedSession:
        def __init__(self):
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO(b'{"type":"thread.started","thread_id":"test"}\n')
            self.returncode = 0

        def wait(self, timeout=None):
            return self.returncode

        def poll(self):
            return self.returncode

    monkeypatch.setattr(capture.subprocess, "Popen", lambda *args, **kwargs: CompletedSession())
    monkeypatch.setattr(capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(
        ["codex", "--version"], 0, "codex-cli test\n", ""
    ))
    command = capture.build_codex_command(workspace, "codex")

    result = capture.run_codex(
        command, workspace, trial_dir, "Use the installed test skill.",
        environ={"CODEX_HOME": str(codex_home), "PATH": "/usr/bin"},
    )

    assert result["reader_complete"] is True
    assert result["lifecycle_complete"] is False
    assert result["complete"] is False


def test_stdout_reader_error_marks_capture_incomplete(tmp_path, monkeypatch):
    capture = load_capture()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text("isolated profile\n", encoding="utf-8")

    class FailingStream:
        def __init__(self):
            self.lines = iter([b'{"type":"thread.started","thread_id":"test"}\n'])

        def readline(self):
            try:
                return next(self.lines)
            except StopIteration as error:
                raise OSError("stream read failed") from error

    class CompletedSession:
        def __init__(self):
            self.stdin = io.BytesIO()
            self.stdout = FailingStream()
            self.returncode = 0

        def wait(self, timeout=None):
            return self.returncode

        def poll(self):
            return self.returncode

    monkeypatch.setattr(capture.subprocess, "Popen", lambda *args, **kwargs: CompletedSession())
    monkeypatch.setattr(capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(
        ["codex", "--version"], 0, "codex-cli test\n", ""
    ))
    command = capture.build_codex_command(workspace, "codex")

    result = capture.run_codex(
        command, workspace, trial_dir, "Use the installed test skill.",
        environ={"CODEX_HOME": str(codex_home), "PATH": "/usr/bin"},
    )

    assert result["reader_complete"] is False
    assert result["reader_error"] == "OSError"
    assert result["complete"] is False


def test_invalid_mcp_ledger_preserves_capture_for_rollout_archival(tmp_path, monkeypatch):
    capture = load_capture()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text("isolated profile\n", encoding="utf-8")
    events = [
        {"type": "thread.started", "thread_id": "parent-thread"},
        {"type": "item.started", "item": {
            "id": "call-1", "type": "mcp_tool_call", "server": "shopping-fixture",
            "tool": "get_meal_plan_index", "arguments": {}, "status": "in_progress",
        }},
        {"type": "item.completed", "item": {
            "id": "call-1", "type": "mcp_tool_call", "server": "shopping-fixture",
            "tool": "save_meal_plan", "arguments": {}, "status": "completed",
        }},
    ]
    stream = b"".join(json.dumps(event).encode() + b"\n" for event in events)

    class CompletedSession:
        def __init__(self):
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO(stream)
            self.returncode = 0

        def wait(self, timeout=None):
            return self.returncode

        def poll(self):
            return self.returncode

    monkeypatch.setattr(capture.subprocess, "Popen", lambda *args, **kwargs: CompletedSession())
    monkeypatch.setattr(
        capture.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="codex 0.164.0\n"),
    )
    command = capture.build_codex_command(workspace, "codex")

    result = capture.run_codex(
        command, workspace, trial_dir, "Use the installed test skill.",
        environ={"CODEX_HOME": str(codex_home), "PATH": "/usr/bin"},
    )

    assert result["complete"] is False
    assert result["ledger_error"] == "MCP call identity changed during host stream"
    assert result["thread_id"] == "parent-thread"
    assert result["event_count"] == len(events)
    assert (trial_dir / "host-events.jsonl").read_bytes() == stream
    assert json.loads((trial_dir / "invocation-capture.json").read_text()) == result


def test_identity_hash_requires_every_declared_pattern(tmp_path):
    capture = load_capture()
    (tmp_path / "present.txt").write_text("candidate")

    hashes = capture.hash_identity(tmp_path, ["present.txt"])

    assert list(hashes) == ["present.txt"]
    with pytest.raises(ValueError, match="required identity pattern"):
        capture.hash_identity(tmp_path, ["missing/**"])


def test_recursive_identity_includes_root_and_nested_files(tmp_path):
    capture = load_capture()
    package = tmp_path / "package"
    (package / "references").mkdir(parents=True)
    (package / "SKILL.md").write_bytes(b"skill")
    (package / "references" / "records.md").write_bytes(b"records")

    assert capture.hash_identity(tmp_path, ["package/**"]) == {
        "package/SKILL.md": hashlib.sha256(b"skill").hexdigest(),
        "package/references/records.md": hashlib.sha256(b"records").hexdigest(),
    }


def test_identity_patterns_ignore_generated_python_bytecode(tmp_path):
    capture = load_capture()
    scripts = tmp_path / "scripts"
    cache = scripts / "__pycache__"
    cache.mkdir(parents=True)
    (scripts / "validate.py").write_text("print('source')\n")
    (scripts / "helper.pyo").write_bytes(b"old bytecode")
    (cache / "validate.cpython-314.pyc").write_bytes(b"generated bytecode")

    assert set(capture._expand_files(tmp_path, ["scripts/**"])) == {"scripts/validate.py"}


def test_skill_discovery_requires_each_frozen_profile_skill_path(tmp_path):
    capture = load_capture()
    root = tmp_path / "plugins" / "cache" / "shopping-trial" / "personal-shopper" / "1.0.0"
    skill = root / "skills" / "personal-shopper" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: personal-shopper\ndescription: Grocery and product shopping.\n---\n", encoding="utf-8")
    payload = [{
        "type": "message",
        "role": "developer",
        "content": [{
            "type": "input_text",
            "text": f"Available skills:\n- r1 = {root / 'skills'}\n"
                    "- personal-shopper:personal-shopper: Grocery shopping.",
        }],
    }]

    result = capture.verify_skill_discovery(
        payload, {"personal-shopper": root}, {"personal-shopper": {"version": "1.0.0"}}
    )

    assert result["candidate_skills"] == ["personal-shopper:personal-shopper"]
    assert len(result["catalog_sha256"]) == 64


def test_skill_discovery_fails_when_candidate_skill_is_missing_from_host_catalog(tmp_path):
    capture = load_capture()
    root = tmp_path / "plugins" / "cache" / "shopping-trial" / "personal-shopper" / "1.0.0"
    skill = root / "skills" / "personal-shopper" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: personal-shopper\ndescription: Shopping.\n---\n", encoding="utf-8")
    payload = [{"type": "message", "role": "developer", "content": [{"text": "No candidate skill."}]}]

    with pytest.raises(ValueError, match="candidate skill is not discoverable"):
        capture.verify_skill_discovery(
            payload, {"personal-shopper": root}, {"personal-shopper": {"version": "1.0.0"}}
        )


def test_skill_discovery_only_requires_the_requested_entrypoints(tmp_path):
    capture = load_capture()
    root = tmp_path / "plugins" / "cache" / "shopping-trial" / "meal-planner" / "1.0.0"
    for name in ("meal-planner", "personal-chef"):
        skill = root / "skills" / name / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(f"---\nname: {name}\ndescription: Test.\n---\n", encoding="utf-8")
    payload = [{
        "type": "message", "role": "developer", "content": [{
            "text": f"Available: {root / 'skills'}\n"
                    "- meal-planner:meal-planner: Meal planning.",
        }],
    }]

    result = capture.verify_skill_discovery(
        payload, {"meal-planner": root}, {"meal-planner": {"version": "1.0.0"}},
        required_skill_ids=["meal-planner:meal-planner"],
    )

    assert result["candidate_skills"] == ["meal-planner:meal-planner"]


def test_live_receipt_resolves_runtime_sheet_id_and_normalizes_host_tab_names():
    builder = load_receipt_builder()
    locator = "https://docs.google.com" + "/spreadsheets/d/" \
        + "Abc_def-12345678901234567890" + "/edit?gid=7"

    assert builder._locator_native_id(locator) == "Abc_def-12345678901234567890"
    assert builder._sheet_name({"sheet_name": "'Store Preferences'"}, "A1:E10") == "Store Preferences"


def test_activation_prompt_selects_skill_without_pasting_its_source():
    capture = load_capture()
    prompt = capture.build_activation_prompt(
        "meal-planner:meal-planner", "Read the supplied synthetic grocery authority.",
        ["personal-shopper:personal-shopper"],
    )

    assert "meal-planner:meal-planner" in prompt
    assert "personal-shopper:personal-shopper" in prompt
    assert "supplied synthetic grocery authority" in prompt
    assert "--- Candidate file:" not in prompt
    assert "SKILL.md" not in prompt


@pytest.mark.parametrize("subcase_id", [None, "B2-AE1"])
def test_trial_runner_leaves_prompt_capture_creation_to_host_runner(monkeypatch, tmp_path, subcase_id):
    runner = load_runner()
    task_file = tmp_path / "task.txt"
    task_file.write_text("Use synthetic grocery data only.", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    profile_home = tmp_path / "codex-home"
    profile_home.mkdir()
    (profile_home / "config.toml").write_text("private isolated profile\n", encoding="utf-8")
    output_dir = tmp_path / "evidence"
    prompt = "Use $personal-shopper:personal-shopper for this synthetic task.\n"
    profile = {
        "packages": ["personal-shopper"],
        "files": {"plugins/personal-shopper/.codex-plugin/plugin.json": "candidate-hash"},
        "provider_apps": [],
    }
    identity = {"personal-shopper/.codex-plugin/plugin.json": "candidate-hash"}
    roots = {"personal-shopper": workspace}
    details = {"personal-shopper": {"plugin_id": "personal-shopper@shopping-trial", "version": "1.0.0"}}
    observed = {}
    discovery = {
        "candidate_skills": ["personal-shopper:personal-shopper"],
        "candidate_skill_path_count": 1,
        "catalog_sha256": "catalog-digest",
    }

    monkeypatch.setattr(runner, "_provider_roots", lambda *args: ({}, {}))
    monkeypatch.setattr(runner, "_global_plugin_inventory", lambda *args: [])
    monkeypatch.setattr(runner, "_make_isolated_home", lambda *args: profile_home)
    def stage_profile(*args, **kwargs):
        config_path = Path(args[1]) / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_bytes = b"[apps._default]\nenabled = false\n"
        config_path.write_bytes(config_bytes)
        profile["config_sha256"] = runner.capture.sha256(config_bytes)
        return profile

    monkeypatch.setattr(runner.capture, "stage_profile", stage_profile)
    monkeypatch.setattr(runner, "_installed_plugins", lambda *args, **kwargs: (roots, details, []))
    monkeypatch.setattr(runner, "_installed_identity", lambda *args, **kwargs: identity)
    monkeypatch.setattr(runner, "_identity_digest", lambda *args, **kwargs: "profile-digest")
    monkeypatch.setattr(runner.capture, "identity_digest", lambda *args, **kwargs: "source-digest")
    monkeypatch.setattr(runner.capture, "verify_skill_discovery", lambda *args, **kwargs: discovery)
    monkeypatch.setattr(runner.capture, "build_activation_prompt", lambda *args: prompt)
    monkeypatch.setattr(runner.capture, "build_codex_command", lambda *args, **kwargs: ["codex", "exec", "-"])

    def register_reader(*args, **kwargs):
        observed["required_resources"] = args[4]
        observed["include_package_references"] = kwargs["include_package_references"]
        return {"packages": {"personal-shopper": {"skills/personal-shopper/SKILL.md": "hash"}}}

    monkeypatch.setattr(runner, "_register_integration_reader", register_reader)

    def debug_prompt_input(command, **kwargs):
        observed["discovery_command"] = command
        observed["discovery_environment"] = kwargs["env"]
        return SimpleNamespace(returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr(runner.subprocess, "run", debug_prompt_input)

    def run_codex(command, trial_workspace, evidence_dir, captured_prompt, **kwargs):
        prompt_path = evidence_dir / "invocation-prompt.txt"
        observed["prompt_existed_before_host_capture"] = prompt_path.exists()
        prompt_path.write_text(captured_prompt, encoding="utf-8")
        os.chmod(prompt_path, 0o600)
        return {"host_version": "0.163.0", "complete": True, "event_count": 2, "tool_call_count": 0}

    monkeypatch.setattr(runner.capture, "run_codex", run_codex)
    result = runner.run_trial("shopper-alone", task_file if subcase_id is None else None,
                              output_dir, subcase_id=subcase_id)

    assert observed["prompt_existed_before_host_capture"] is False
    captured_prompt = (output_dir / "invocation-prompt.txt").read_text(encoding="utf-8")
    if subcase_id is None:
        assert captured_prompt == prompt
        assert "required_resources" not in observed
    else:
        assert observed["required_resources"] == ["personal-shopper/skills/personal-shopper/SKILL.md"]
        assert observed["include_package_references"] is True
        assert "read_installed_skill_file" in captured_prompt
        assert '{"package": "personal-shopper", "relative_path": "skills/personal-shopper/SKILL.md"}' in captured_prompt
    assert result["trial_status"] == "captured"
    assert result["source_candidate_unchanged"] is True
    assert result["suite_identity_unchanged"] is True
    assert result["skill_discovery"] == discovery
    assert observed["discovery_command"] == [
        "codex", "debug", "prompt-input", "Use $personal-shopper:personal-shopper."
    ]
    assert "CODEX_HOME" in observed["discovery_environment"]


def test_trial_runner_rejects_symlinked_private_task_before_resolution(tmp_path):
    runner = load_runner()
    target = tmp_path / "task.txt"
    target.write_text("Use synthetic grocery data only.", encoding="utf-8")
    task_link = tmp_path / "linked-task.txt"
    try:
        task_link.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks are unavailable in this environment: {exc}")

    output_dir = tmp_path / "evidence"
    with pytest.raises(ValueError, match="task input must not be a symlink"):
        runner.run_trial("shopper-alone", task_link, output_dir)

    assert not output_dir.exists()


def test_installed_resource_reader_accepts_only_declared_package_bytes(tmp_path):
    spec = importlib.util.spec_from_file_location("shopping_skill_resources", EVAL / "skill_resources.py")
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    planner = tmp_path / "planner"
    shopper = tmp_path / "shopper"
    (planner / "shared").mkdir(parents=True)
    (shopper / "skills").mkdir(parents=True)
    (planner / "shared" / "handoff.md").write_text("planner contract\n")
    (shopper / "skills" / "SKILL.md").write_text("shopper instructions\n")
    control = {"packages": {
        "meal-planner": {"installed_root": str(planner), "files": {
            "shared/handoff.md": hashlib.sha256(b"planner contract\n").hexdigest()}},
        "personal-shopper": {"installed_root": str(shopper), "files": {
            "skills/SKILL.md": hashlib.sha256(b"shopper instructions\n").hexdigest()}},
    }}
    payload = reader.read_resource(control, {"package": "meal-planner", "relative_path": "shared/handoff.md"})
    assert payload["text"] == "planner contract\n"
    assert payload["package"] == "meal-planner"
    for package, path in (("unknown", "shared/handoff.md"), ("meal-planner", "../shopper/skills/SKILL.md"),
                          ("meal-planner", "shared/undeclared.md")):
        with pytest.raises(ValueError):
            reader.read_resource(control, {"package": package, "relative_path": path})
    (planner / "shared" / "handoff.md").write_text("changed\n")
    with pytest.raises(ValueError, match="changed"):
        reader.read_resource(control, {"package": "meal-planner", "relative_path": "shared/handoff.md"})
