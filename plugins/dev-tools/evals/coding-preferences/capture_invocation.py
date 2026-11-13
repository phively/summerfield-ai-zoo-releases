#!/usr/bin/env python3
"""Run one isolated trial session and bind its prompt, candidate, and trace."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path, PurePosixPath


PREAMBLE = (
    "You are executing the frozen Coding Preferences skill candidate for one task. "
    "Follow the included skill and its references. The only available external authority "
    "is the explicitly selected synthetic fixture provider; use only MCP tools declared "
    "for this case. Do not use or claim any other source."
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def contained_path(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Path must stay inside the trial: {relative}")
    result = (Path(root) / Path(*path.parts)).resolve()
    if Path(root).resolve() not in result.parents:
        raise ValueError(f"Path must stay inside the trial: {relative}")
    return result


def validate_workspace(workspace):
    workspace = Path(workspace).resolve()
    if workspace == REPOSITORY_ROOT or REPOSITORY_ROOT in workspace.parents:
        raise ValueError("The candidate workspace must be outside the repository")
    current = workspace
    while True:
        if (current / "AGENTS.md").is_file():
            raise ValueError("The candidate workspace inherits AGENTS.md instructions")
        if current == current.parent:
            break
        current = current.parent
    return workspace


def candidate_prompt(candidate_root, candidate_hashes, task, execution_date):
    sections = [PREAMBLE, "--- Trial date ---", (
        f"The actual current date for audit verification in this trial is {execution_date}. "
        "Keep it distinct from any update or effective date specified by the task."
    )]
    for relative in sorted(candidate_hashes):
        path = contained_path(candidate_root, relative)
        content = path.read_text(encoding="utf-8")
        sections.extend((f"--- Candidate file: {relative} ---", content.rstrip("\n")))
    sections.extend(("--- Public task ---", task))
    return "\n\n".join(sections) + "\n"


def validate_command(command, workspace, trial):
    if not command or Path(command[0]).name not in {"codex", "codex.exe"}:
        raise ValueError("The command must launch the Codex CLI directly")
    if command.count("exec") != 1 or command.count("--json") != 1 or command[-1] != "-":
        raise ValueError("Use codex exec --json with stdin as the only prompt source")
    if command.count("-") != 1:
        raise ValueError("The command must contain exactly one stdin prompt marker")
    if command.count("--cd") != 1 or command.count("--output-last-message") != 1:
        raise ValueError("The command must set --cd and --output-last-message exactly once")
    try:
        cd_index = command.index("--cd")
        output_index = command.index("--output-last-message")
    except ValueError as error:
        raise ValueError("The command must set --cd and --output-last-message") from error
    if cd_index + 1 >= len(command) or output_index + 1 >= len(command):
        raise ValueError("The command must provide values for --cd and --output-last-message")
    if Path(command[cd_index + 1]).resolve() != Path(workspace).resolve():
        raise ValueError("The Codex workspace must match the captured candidate workspace")
    output_path = Path(command[output_index + 1])
    if not output_path.is_absolute():
        output_path = Path(workspace) / output_path
    if Path(trial).resolve() not in output_path.resolve().parents:
        raise ValueError("The final-message output must stay inside the trial")


def snapshot_candidate(workspace, trial, candidate_hashes):
    workspace = Path(workspace).resolve()
    snapshot = Path(trial) / "candidate-workspace"
    actual = {}
    for relative in sorted(candidate_hashes):
        source = contained_path(workspace, relative)
        if not source.is_file():
            raise ValueError(f"Missing candidate workspace file: {relative}")
        content = source.read_bytes()
        actual[relative] = sha256(content)
        destination = contained_path(snapshot, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != content:
            raise ValueError("Candidate workspace changed during the trial")
        destination.write_bytes(content)
    if actual != candidate_hashes:
        raise ValueError("Candidate workspace bytes do not match candidate-hashes.json")
    return actual


def append_capture(trial, entry, runtime_bytes, candidate_hashes):
    capture_path = Path(trial) / "invocation-capture.json"
    capture = read_json(capture_path) if capture_path.exists() else {"version": 1, "sessions": []}
    if capture.get("version") != 1:
        raise ValueError("Unsupported invocation capture version")
    if any(item.get("id") == entry["id"] for item in capture["sessions"]):
        raise ValueError(f"Session already captured: {entry['id']}")
    capture["candidate_workspace_hashes"] = candidate_hashes
    capture["sessions"].append(entry)
    capture["runtime_sha256"] = sha256(runtime_bytes)
    for item in capture["sessions"]:
        item["runtime_sha256"] = capture["runtime_sha256"]
    capture_path.write_text(json.dumps(capture, indent=2) + "\n", encoding="utf-8")


def run(trial, workspace, session_id, execution_date, command):
    trial = Path(trial).resolve()
    workspace = validate_workspace(workspace)
    if not trial.is_dir() or not workspace.is_dir():
        raise ValueError("Trial and candidate workspace must already exist")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", session_id):
        raise ValueError("Session ID must be a simple filename-safe identifier")
    command = list(command)
    if date.fromisoformat(execution_date).isoformat() != execution_date:
        raise ValueError("Execution date must use YYYY-MM-DD")
    validate_command(command, workspace, trial)
    candidate_hashes = read_json(trial / "candidate-hashes.json")
    public = read_json(trial / "public.json")
    session = next((item for item in public.get("sessions", []) if item.get("id") == session_id), None)
    if public.get("sessions") and session is None:
        raise ValueError(f"Unknown public session: {session_id}")
    task = session.get("prompt") if session else public.get("prompt")
    if not isinstance(task, str) or not task:
        raise ValueError("The public task prompt is missing")
    candidate_workspace_hashes = snapshot_candidate(workspace, trial, candidate_hashes)
    prompt = candidate_prompt(trial / "candidate-workspace", candidate_hashes, task, execution_date)
    prompt_bytes = prompt.encode("utf-8")
    inputs = trial / "agent-inputs"
    inputs.mkdir(exist_ok=True)
    prompt_path = inputs / f"{session_id}.txt"
    if prompt_path.exists():
        raise ValueError(f"Session input already captured: {session_id}")
    prompt_path.write_bytes(prompt_bytes)

    runtime_path = trial / "runtime.jsonl"
    before = runtime_path.read_bytes()
    if before and not before.endswith(b"\n"):
        raise ValueError("The previous runtime stream must end at a JSONL boundary")
    result = subprocess.run(command, cwd=workspace, input=prompt_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    snapshot_candidate(workspace, trial, candidate_hashes)
    with runtime_path.open("ab") as stream:
        stream.write(result.stdout)
    runtime_bytes = runtime_path.read_bytes()
    stderr_dir = trial / "session-streams"
    stderr_dir.mkdir(exist_ok=True)
    (stderr_dir / f"{session_id}.stderr").write_bytes(result.stderr)
    entry = {
        "id": session_id,
        "prompt_path": prompt_path.relative_to(trial).as_posix(),
        "prompt_sha256": sha256(prompt_bytes),
        "task_sha256": sha256(task.encode("utf-8")),
        "workspace": str(workspace),
        "command": command,
        "exit_code": result.returncode,
        "stderr_path": (stderr_dir / f"{session_id}.stderr").relative_to(trial).as_posix(),
        "stderr_sha256": sha256(result.stderr),
        "runtime_start": len(before),
        "runtime_end": len(runtime_bytes),
        "runtime_segment_sha256": sha256(result.stdout),
    }
    append_capture(trial, entry, runtime_bytes, candidate_workspace_hashes)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial", type=Path)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--execution-date", required=True)
    raw_args = sys.argv[1:]
    if "--" not in raw_args:
        parser.error("separate the Codex command with --")
    separator = raw_args.index("--")
    args = parser.parse_args(raw_args[:separator])
    command = raw_args[separator + 1:]
    if not command:
        parser.error("provide the Codex command after --")
    try:
        return run(args.trial, args.workspace, args.session, args.execution_date, command)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"capture_invocation: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
