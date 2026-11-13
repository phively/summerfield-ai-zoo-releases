#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
from typing import Any


EVAL_ROOT = Path(__file__).resolve().parent
_platform_spec = importlib.util.spec_from_file_location('evaluation_platform_support', EVAL_ROOT.parent / 'platform_support.py')
platform_support = importlib.util.module_from_spec(_platform_spec)
_platform_spec.loader.exec_module(platform_support)
REPO_ROOT = EVAL_ROOT.parents[3]
MANIFEST = json.loads((EVAL_ROOT / "manifest.json").read_text(encoding="utf-8"))
CASE_MAP = {case["id"]: case for case in MANIFEST["cases"] + MANIFEST.get("controls", [])}
MAX_TURN_SECONDS = 240
SESSION_CONTEXT_ENV = (
    "CODEX_SESSION_ID",
    "CODEX_THREAD_ID",
    "CODEX_TOOL_CALL_ID",
    "CODEX_INTERNAL_ORIGINATOR_OVERRIDE",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def isolated_codex_environment() -> tuple[dict[str, str], list[str]]:
    environment = os.environ.copy()
    removed = []
    for key in SESSION_CONTEXT_ENV:
        if key in environment:
            environment.pop(key)
            removed.append(key)
    return environment, removed


def setting_args(server_script: Path, events_path: Path, case_id: str, candidate_id: str, effort: str) -> list[str]:
    fixture_root = EVAL_ROOT / "fixtures"
    server_args = [str(server_script), "serve", str(fixture_root), str(events_path), case_id, candidate_id]
    fixture_tools_enabled = CASE_MAP.get(case_id, {}).get("fixture_tools_enabled", True)
    settings: list[tuple[str, str]] = [
        ("model_reasoning_effort", json.dumps(effort)),
        ("sandbox_mode", '"read-only"'),
        ("service_tier", '"default"'),
        ("web_search", '"disabled"'),
        ("apps._default.enabled", "false"),
        ("mcp_servers.continuity.enabled", json.dumps(fixture_tools_enabled)),
        ("mcp_servers.continuity.required", json.dumps(fixture_tools_enabled)),
        ("mcp_servers.continuity.command", json.dumps(sys.executable)),
        ("mcp_servers.continuity.args", json.dumps(server_args)),
        ("mcp_servers.continuity.cwd", json.dumps(str(EVAL_ROOT))),
        ("mcp_servers.continuity.enabled_tools", json.dumps(["search_sources", "read_source"] if fixture_tools_enabled else [])),
        ("mcp_servers.continuity.default_tools_approval_mode", '"approve"'),
        ("features.apps", "false"),
        ("features.plugins", "false"),
        ("features.shell_tool", "false"),
        ("features.unified_exec", "false"),
        ("features.skill_search", "false"),
        ("features.multi_agent", "false"),
        ("features.memories", "false"),
        ("features.image_generation", "false"),
        ("features.view_image", "false"),
        ("features.sleep_tool", "false"),
        ("features.computer_use", "false"),
        ("features.browser_use", "false"),
        ("features.tool_suggest", "false"),
        ("features.goals", "false"),
        ("features.fast_mode", "false"),
        ("features.ultrafast_mode", "false"),
        ("features.code_mode.enabled", "false"),
        ("features.code_mode.excluded_tool_namespaces", json.dumps(["collaboration", "functions"])),
        ("features.code_mode_host", "true"),
        ("features.web_search", "false"),
        ("features.skip_host_skill_discovery", "true"),
    ]
    return [argument for key, value in settings for argument in ("--config", f"{key}={value}")]


def invoke(command: list[str], prompt: str, cwd: Path, stdout_path: Path, stderr_path: Path) -> tuple[int, str | None, str | None]:
    environment, _ = isolated_codex_environment()
    try:
        with stdout_path.open("wb") as stdout_stream, stderr_path.open("wb") as stderr_stream:
            process = platform_support.start_process(
                command,
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=stdout_stream,
                stderr=stderr_stream,
                env=environment,
            )
            try:
                process.communicate(prompt.encode("utf-8"), timeout=MAX_TURN_SECONDS)
            except subprocess.TimeoutExpired:
                platform_support.terminate_process_group(process)
                return 124, None, None
            except KeyboardInterrupt:
                platform_support.terminate_process_group(process)
                return 130, None, None
            except BaseException:
                platform_support.terminate_process_group(process)
                raise
            finally:
                platform_support.close_process(process)
            return_code = process.returncode
    except OSError as error:
        return 127, None, f"launch_error: {error}"
    thread_id = None
    model = None
    for line in stdout_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            thread_id = event.get("thread_id")
        if event.get("type") in {"session_meta", "session.started", "thread.started"}:
            model = model or event.get("model") or (event.get("metadata") or {}).get("model")
    return return_code, thread_id, model


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cleanup_workspace(record: dict[str, Any]) -> None:
    workspace_value = record.get("workspace")
    if not workspace_value:
        return
    workspace = Path(workspace_value).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if workspace.parent != temp_root or not workspace.name.startswith("rb-continuity-agent-"):
        raise SystemExit("refusing to remove a workspace not created by this runner")
    try:
        shutil.rmtree(workspace)
    except FileNotFoundError:
        pass
    record["workspace"] = None
    record["workspace_cleanup"] = "removed"


def read_events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def observed_tool_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: dict[str, dict[str, Any]] = {}
    for event in events:
        item = event.get("item", {})
        item_type = item.get("type", "")
        if item_type == "mcp_tool_call":
            calls[item.get("id", f"{item.get('server')}:{item.get('tool')}")] = {
                "type": item_type,
                "server": item.get("server"),
                "tool": item.get("tool"),
                "arguments": item.get("arguments"),
                "status": item.get("status"),
                "error": item.get("error"),
            }
        elif "tool_call" in item_type or item_type in {"exec_command", "code_mode_exec", "function_call"}:
            calls[item.get("id", f"unknown:{len(calls)}")] = {
                "type": item_type,
                "name": item.get("name"),
                "server": item.get("server"),
                "tool": item.get("tool"),
                "status": item.get("status"),
                "error": item.get("error"),
            }
    return list(calls.values())


def turn_validation(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    events = read_events(path)
    calls = observed_tool_calls(events)
    unexpected = [
        call for call in calls
        if call.get("type") != "mcp_tool_call"
        or call.get("server") != "continuity"
        or call.get("tool") not in {"search_sources", "read_source"}
    ]
    completed = any(event.get("type") == "turn.completed" for event in events)
    return calls, unexpected, completed


def trial_evidence_error(record: dict[str, Any]) -> str | None:
    turns = record.get("turns")
    thread_id = record.get("thread_id")
    if not isinstance(turns, list) or not turns:
        return "The trial has no recorded turns."
    if not isinstance(thread_id, str) or not thread_id:
        return "The initial turn has no observed thread identity."

    for index, turn in enumerate(turns):
        if turn.get("exit_status") != 0:
            return f"Turn {index + 1} did not exit successfully."
        if turn.get("turn_completed") is not True:
            return f"Turn {index + 1} did not complete."
        if turn.get("unexpected_tool_calls"):
            return f"Turn {index + 1} used an unexpected tool."
        observed_thread_id = turn.get("thread_id") if index == 0 else turn.get("resumed_thread_id")
        if observed_thread_id != thread_id:
            return f"Turn {index + 1} has no matching observed thread identity."
    return None


def controller_turn_error(record: dict[str, Any], case: dict[str, Any], turn_index: int) -> str | None:
    if turn_index < 1 or turn_index > len(case["future_turns"]):
        return "future-turn index is out of range"
    turns = record.get("turns", [])
    recorded_indices = [turn.get("controller_turn_index") for turn in turns[1:]]
    expected_prefix = list(range(1, len(turns)))
    if recorded_indices != expected_prefix:
        return "recorded controller turns are not a complete ordered prefix"
    expected_next = len(turns)
    if turn_index != expected_next:
        return f"future turns must be sent in order; expected controller turn {expected_next}"
    return None


def tool_inventory(payload: Any) -> list[str]:
    inventory: list[str] = []

    def visit(value: Any, namespace: str | None = None) -> None:
        if isinstance(value, dict):
            current_namespace = value.get("name") if value.get("type") == "namespace" else namespace
            if value.get("type") == "namespace":
                for tool in value.get("tools", []):
                    if isinstance(tool, dict) and isinstance(tool.get("name"), str):
                        inventory.append(f"{current_namespace}.{tool['name']}")
            for child in value.values():
                visit(child, current_namespace)
        elif isinstance(value, list):
            for child in value:
                visit(child, namespace)

    visit(payload)
    return sorted(set(inventory))


def model_catalog() -> tuple[list[dict[str, Any]], str | None]:
    environment, _ = isolated_codex_environment()
    try:
        result = subprocess.run(
            ["codex", "--no-daemon", "debug", "models"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return [], f"catalog_unavailable: {type(error).__name__}"
    if result.returncode != 0:
        return [], f"catalog_exit_status_{result.returncode}: {result.stderr[-1000:]}"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        return [], f"catalog_invalid_json: {type(error).__name__}"
    models = []
    for model in payload.get("models", []):
        if not isinstance(model, dict):
            continue
        models.append({
            key: model.get(key)
            for key in ("slug", "display_name", "visibility", "default_reasoning_level")
        })
    return models, None


def model_selection_reason(model: str, catalog: list[dict[str, Any]]) -> str:
    visible = {entry.get("slug") for entry in catalog if entry.get("visibility") == "list"}
    if model == "gpt-6-luna" and model in visible:
        return "gpt-6-luna was visible in this run's Codex CLI model catalog and was selected per the protocol."
    if model in visible:
        return f"{model} was explicitly selected and visible in this run's Codex CLI model catalog."
    return f"{model} was requested but was not visible in this run's Codex CLI model catalog."


def preflight(args: argparse.Namespace) -> int:
    candidate_path = args.candidate.resolve()
    if not candidate_path.is_file():
        raise SystemExit(f"candidate file does not exist: {candidate_path}")
    candidate_bytes = candidate_path.read_bytes()
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-preflight-" + secrets.token_hex(3)
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", run_id) or run_id in {".", ".."}:
        raise SystemExit("run id must be a safe path component")
    output_base = args.output_base.resolve()
    preflight_dir = output_base / run_id / "preflight"
    preflight_dir.mkdir(parents=True, exist_ok=False)
    workspace = Path(tempfile.mkdtemp(prefix="rb-continuity-preflight-"))
    (workspace / "AGENTS.md").write_bytes(candidate_bytes)
    event_path = preflight_dir / "source-events.jsonl"
    configured = setting_args(EVAL_ROOT / "fixture_server.py", event_path, "preflight", "control", args.effort)
    command = ["codex", "--no-daemon", "debug", "prompt-input", *configured]
    environment, removed_context = isolated_codex_environment()
    result: dict[str, Any]
    try:
        process = platform_support.start_process(command, cwd=workspace, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=120)
            status = process.returncode
        except subprocess.TimeoutExpired as timeout:
            drained_stdout, drained_stderr = platform_support.terminate_process_group(process)
            stdout_bytes = drained_stdout if drained_stdout is not None else timeout.stdout or b""
            stderr_bytes = drained_stderr if drained_stderr is not None else timeout.stderr or b""
            status = 124
        except KeyboardInterrupt:
            stdout_bytes, stderr_bytes = platform_support.terminate_process_group(process)
            status = 130
        except BaseException:
            platform_support.terminate_process_group(process)
            raise
        finally:
            platform_support.close_process(process)
        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")
        stdout_digest = digest(stdout_bytes)
        try:
            payload = json.loads(stdout_text)
            exposed = tool_inventory(payload)
            parse_error = None
        except json.JSONDecodeError as error:
            exposed = []
            parse_error = f"invalid_json: {error.__class__.__name__}"
        protocol_events = read_events(event_path)
        expected = {"search_sources", "read_source"}
        advertised = [
            event.get("tool_names", [])
            for event in protocol_events
            if event.get("operation") == "mcp_tools_list"
        ]
        initialized = any(event.get("operation") == "mcp_initialize" for event in protocol_events)
        listed = bool(advertised) and set(advertised[-1]) == expected
        if status == 130:
            catalog, catalog_error = [], "model catalog not queried after interruption"
        else:
            catalog, catalog_error = model_catalog()
        model_visible = {entry.get("slug") for entry in catalog if entry.get("visibility") == "list"}
        model_available = args.model in model_visible
        passed = status == 0 and parse_error is None and initialized and listed and model_available
        reasons = []
        if status != 0:
            reasons.append(f"codex debug prompt-input exited {status}")
        if status == 130:
            reasons.append("Codex CLI prompt-input was interrupted")
        if parse_error:
            reasons.append(parse_error)
        if not initialized:
            reasons.append("Codex did not initialize the configured fixture server")
        if not listed:
            reasons.append("Codex did not retrieve the fixture tool list")
        if not model_available:
            reasons.append(catalog_error or f"requested model {args.model} is not visible in the CLI model catalog")
        result = {
            "status": "passed" if passed else "blocked",
            "reason": None if passed else "; ".join(reasons),
            "command": command,
            "exit_status": status,
            "interrupted": status == 130,
            "stdout_bytes": len(stdout_bytes),
            "stdout_sha256": stdout_digest,
            "stderr": stderr_text[-2000:],
            "parse_error": parse_error,
            "debug_prompt_input_tool_inventory": exposed,
            "debug_prompt_input_inventory_scope": "Codex CLI debug output; behavioral trials additionally retain the tools actually called in each JSONL turn.",
            "session_context_environment_variables_removed": removed_context,
            "fixture_protocol_events": protocol_events,
            "fixture_tools_advertised": advertised[-1] if advertised else [],
            "candidate_source": str(candidate_path),
            "candidate_sha256": digest(candidate_bytes),
            "requested_runner": "codex-cli",
            "cli_version": subprocess.run(["codex", "--version"], capture_output=True, text=True, check=False, env=environment).stdout.strip(),
            "requested_model": args.model,
            "model_catalog": catalog,
            "model_selection_reason": model_selection_reason(args.model, catalog),
            "requested_reasoning_effort": args.effort,
            "requested_speed": "default/standard",
            "sandbox": "read-only",
        }
    except subprocess.TimeoutExpired:
        result = {
            "status": "blocked",
            "reason": "Codex CLI prompt-input fixture route probe exceeded 120 seconds.",
            "exit_status": 124,
            "candidate_sha256": digest(candidate_bytes),
            "requested_runner": "codex-cli",
            "requested_model": args.model,
            "requested_reasoning_effort": args.effort,
            "requested_speed": "default/standard",
        }
    finally:
        shutil.rmtree(workspace)
    write_json(preflight_dir / "preflight.json", result)
    print(json.dumps({
        "status": result["status"],
        "reason": result.get("reason"),
        "fixture_tools_advertised": result.get("fixture_tools_advertised", []),
        "debug_prompt_input_tool_inventory": result.get("debug_prompt_input_tool_inventory", []),
        "record": str(preflight_dir / "preflight.json"),
    }))
    return 0 if result["status"] == "passed" else 3


def assistant_text(path: Path) -> str:
    chunks: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") in {"agent_message", "assistant_message"}:
            text = item.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks)


def common_command(
    model: str,
    effort: str,
    events_path: Path,
    case_id: str,
    candidate_id: str,
    *,
    resume: bool = False,
) -> list[str]:
    server_script = EVAL_ROOT / "fixture_server.py"
    disabled = setting_args(server_script, events_path, case_id, candidate_id, effort)
    subcommand = ["exec", "resume"] if resume else ["exec"]
    return ["codex", "--no-daemon", "--ask-for-approval", "never", "--sandbox", "read-only", *subcommand, *disabled, "--skip-git-repo-check", "--json", "--model", model]


def start_trial(args: argparse.Namespace) -> int:
    if args.case_id not in CASE_MAP:
        raise SystemExit(f"unknown case id: {args.case_id}")
    candidate_path = args.candidate.resolve()
    if not candidate_path.is_file():
        raise SystemExit(f"candidate file does not exist: {candidate_path}")
    candidate_bytes = candidate_path.read_bytes()
    candidate_id = args.candidate_id
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", candidate_id):
        raise SystemExit("candidate id must be a lowercase slug of at most 64 characters")
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", run_id) or run_id in {".", ".."}:
        raise SystemExit("run id must be a safe path component")
    output_base = args.output_base.resolve()
    run_dir = output_base / run_id / candidate_id / args.case_id
    run_dir.mkdir(parents=True, exist_ok=False)
    workspace = Path(tempfile.mkdtemp(prefix="rb-continuity-agent-"))
    (workspace / "AGENTS.md").write_bytes(candidate_bytes)
    event_path = run_dir / "source-events.jsonl"
    event_path.touch(exist_ok=False)
    prompt = CASE_MAP[args.case_id]["initial_turn"]
    (run_dir / "user-turn-1.txt").write_text(prompt + "\n", encoding="utf-8")
    command = common_command(args.model, args.effort, event_path, args.case_id, candidate_id)
    command.extend(["--ignore-user-config", "-C", str(workspace), "-"])
    command_json = ["<prompt via stdin>" if value == "-" else value for value in command]
    catalog, catalog_error = model_catalog()
    environment, removed_context = isolated_codex_environment()
    record: dict[str, Any] = {
        "run_id": run_id,
        "case_id": args.case_id,
        "group_id": CASE_MAP[args.case_id]["group_id"],
        "candidate_id": candidate_id,
        "candidate_source": str(candidate_path),
        "candidate_sha256": digest(candidate_bytes),
        "suite_id": MANIFEST["suite_id"],
        "suite_version": MANIFEST["suite_version"],
        "rubric_id": MANIFEST["rubric_id"],
        "rubric_version": MANIFEST["rubric_version"],
        "fixture_tools_enabled": CASE_MAP[args.case_id].get("fixture_tools_enabled", True),
        "workspace": str(workspace),
        "requested_runner": "codex-cli",
        "cli_version": subprocess.run(["codex", "--version"], capture_output=True, text=True, check=False, env=environment).stdout.strip(),
        "session_context_environment_variables_removed": removed_context,
        "requested_model": args.model,
        "model_catalog": catalog,
        "model_catalog_error": catalog_error,
        "model_selection_reason": model_selection_reason(args.model, catalog),
        "actual_model": "not_exposed",
        "requested_reasoning_effort": args.effort,
        "actual_reasoning_effort": "not_exposed",
        "requested_speed": "default/standard",
        "actual_speed": "not_exposed",
        "sandbox": "read-only",
        "user_config": "ignored on initial thread; feature and app disables repeated on each turn",
        "configured_fixture_tools": ["continuity.search_sources", "continuity.read_source"] if CASE_MAP[args.case_id].get("fixture_tools_enabled", True) else [],
        "command_template": command_json,
        "thread_id": None,
        "turns": [],
    }
    write_json(run_dir / "runtime-settings.json", record)
    status, thread_id, actual_model = invoke(command, prompt, workspace, run_dir / "turn-01.jsonl", run_dir / "turn-01.stderr")
    calls, unexpected_calls, turn_completed = turn_validation(run_dir / "turn-01.jsonl")
    record["actual_model"] = actual_model or "not_exposed"
    record["thread_id"] = thread_id
    record["turns"].append({
        "turn": 1,
        "user_turn_sha256": digest(prompt.encode("utf-8")),
        "exit_status": status,
        "interrupted": status == 130,
        "thread_id": thread_id,
        "turn_completed": turn_completed,
        "observed_tool_calls": calls,
        "unexpected_tool_calls": unexpected_calls,
        "command": command_json,
        "assistant_text_path": "turn-01-assistant.txt",
    })
    (run_dir / "turn-01-assistant.txt").write_text(assistant_text(run_dir / "turn-01.jsonl"), encoding="utf-8")
    write_json(run_dir / "runtime-settings.json", record)
    evidence_error = trial_evidence_error(record)
    valid = evidence_error is None
    record["evidence_status"] = "valid" if valid else "invalid"
    record["evidence_status_reason"] = evidence_error
    if not valid or not CASE_MAP[args.case_id]["future_turns"]:
        cleanup_workspace(record)
    write_json(run_dir / "runtime-settings.json", record)
    print(json.dumps({"run_dir": str(run_dir), "thread_id": thread_id, "exit_status": status, "evidence_status": record["evidence_status"], "workspace_cleanup": record.get("workspace_cleanup", "retained_for_future_turns"), "assistant_output": str(run_dir / "turn-01-assistant.txt")}))
    return 0 if valid else 3


def reply_trial(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    record_path = run_dir / "runtime-settings.json"
    if not record_path.is_file():
        raise SystemExit(f"trial record missing: {record_path}")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    case = CASE_MAP.get(record["case_id"])
    if case is None:
        raise SystemExit("trial case is missing or unknown")
    prior_error = trial_evidence_error(record)
    if record.get("evidence_status") != "valid" or prior_error:
        record["evidence_status"] = "invalid"
        record["evidence_status_reason"] = record.get("evidence_status_reason") or prior_error or "Prior trial evidence is invalid."
        write_json(record_path, record)
        raise SystemExit("prior trial evidence is invalid; start a fresh trial")
    order_error = controller_turn_error(record, case, args.turn_index)
    if order_error:
        raise SystemExit(order_error)
    workspace_value = record.get("workspace")
    if not workspace_value or not Path(workspace_value).is_dir():
        record["evidence_status"] = "invalid"
        record["evidence_status_reason"] = "The candidate workspace required for continuation is missing."
        write_json(record_path, record)
        raise SystemExit("candidate workspace is missing; start a fresh trial")
    prompt = case["future_turns"][args.turn_index - 1]
    next_turn = len(record["turns"]) + 1
    index_path = run_dir / f"user-turn-{next_turn}.txt"
    index_path.write_text(prompt + "\n", encoding="utf-8")
    command = common_command(
        record["requested_model"],
        record["requested_reasoning_effort"],
        run_dir / "source-events.jsonl",
        record["case_id"],
        record["candidate_id"],
        resume=True,
    )
    command.extend(["--ignore-user-config", record["thread_id"], "-"])
    status, resumed_thread_id, actual_model = invoke(command, prompt, Path(workspace_value), run_dir / f"turn-{next_turn:02d}.jsonl", run_dir / f"turn-{next_turn:02d}.stderr")
    calls, unexpected_calls, turn_completed = turn_validation(run_dir / f"turn-{next_turn:02d}.jsonl")
    (run_dir / f"turn-{next_turn:02d}-assistant.txt").write_text(assistant_text(run_dir / f"turn-{next_turn:02d}.jsonl"), encoding="utf-8")
    if actual_model:
        record["actual_model"] = actual_model
    record["turns"].append({
        "turn": next_turn,
        "controller_turn_index": args.turn_index,
        "user_turn_sha256": digest(prompt.encode("utf-8")),
        "exit_status": status,
        "interrupted": status == 130,
        "resumed_thread_id": resumed_thread_id,
        "turn_completed": turn_completed,
        "observed_tool_calls": calls,
        "unexpected_tool_calls": unexpected_calls,
        "command": ["<prompt via stdin>" if value == "-" else value for value in command],
        "assistant_text_path": f"turn-{next_turn:02d}-assistant.txt",
    })
    same_thread = resumed_thread_id is not None and resumed_thread_id == record["thread_id"]
    evidence_error = trial_evidence_error(record)
    valid = evidence_error is None
    record["evidence_status"] = "valid" if valid else "invalid"
    record["evidence_status_reason"] = evidence_error
    if not valid or args.turn_index == len(case["future_turns"]):
        cleanup_workspace(record)
    write_json(record_path, record)
    print(json.dumps({"run_dir": str(run_dir), "thread_id": record["thread_id"], "resumed_thread_id": resumed_thread_id, "exit_status": status, "same_thread": same_thread, "evidence_status": record["evidence_status"], "workspace_cleanup": record.get("workspace_cleanup", "retained_for_future_turns"), "assistant_output": str(run_dir / f"turn-{next_turn:02d}-assistant.txt")}))
    return 0 if valid else 3


def cleanup_trial(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    record_path = run_dir / "runtime-settings.json"
    if not record_path.is_file():
        raise SystemExit(f"trial record missing: {record_path}")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if not record.get("workspace"):
        raise SystemExit("trial workspace is already removed or unavailable")
    cleanup_workspace(record)
    write_json(record_path, record)
    print(json.dumps({"run_dir": str(run_dir), "workspace_cleanup": "removed"}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("preflight")
    check.add_argument("--candidate", type=Path, required=True)
    check.add_argument("--output-base", type=Path, default=REPO_ROOT / "output" / "research-briefing-continuity")
    check.add_argument("--run-id")
    check.add_argument("--model", default="gpt-6-luna")
    check.add_argument("--effort", default="medium")
    check.set_defaults(func=preflight)
    start = subparsers.add_parser("start")
    start.add_argument("--case-id", required=True)
    start.add_argument("--candidate-id", required=True)
    start.add_argument("--candidate", type=Path, required=True)
    start.add_argument("--output-base", type=Path, default=REPO_ROOT / "output" / "research-briefing-continuity")
    start.add_argument("--run-id")
    start.add_argument("--model", default="gpt-6-luna")
    start.add_argument("--effort", default="medium")
    start.set_defaults(func=start_trial)
    reply = subparsers.add_parser("reply")
    reply.add_argument("--run-dir", type=Path, required=True)
    reply.add_argument("--turn-index", type=int, required=True)
    reply.set_defaults(func=reply_trial)
    cleanup = subparsers.add_parser("cleanup")
    cleanup.add_argument("--run-dir", type=Path, required=True)
    cleanup.set_defaults(func=cleanup_trial)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
