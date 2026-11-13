#!/usr/bin/env python3
"""Synthetic provider for isolated coding-preference trials; never use real records."""

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.json"
FIXTURES = ROOT / "fixtures"
SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_fixture(name):
    path = (FIXTURES / name).resolve()
    if path.parent != FIXTURES.resolve() or not path.is_file():
        raise ValueError(f"Invalid coding-preferences fixture: {name}")
    return path.read_text(encoding="utf-8")


def materialize(record):
    result = deepcopy(record)
    if "content_file" in result:
        result["content"] = read_fixture(result.pop("content_file"))
    return result


def load_case(case_id):
    manifest = read_json(MANIFEST)
    for case in manifest["cases"]:
        if case["id"] == case_id:
            return manifest, deepcopy(case)
    raise KeyError(f"Unknown case: {case_id}")


def initialize(root, case_id, candidate, evidence_kind="deterministic-control"):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise FileExistsError("Use a unique empty trial root")

    manifest, case = load_case(case_id)
    initial = {key: materialize(record) for key, record in case["initial"].items()}
    fixture_snapshot = root / "fixtures"
    fixture_snapshot.mkdir()
    for path in sorted(FIXTURES.iterdir()):
        if path.is_file():
            (fixture_snapshot / path.name).write_bytes(path.read_bytes())
    source_hashes = {
        "adapter": file_hash(ROOT / "store.py"),
        "checker": file_hash(ROOT / "check_trial.py"),
        "protocol": file_hash(ROOT / "protocol.md"),
        "manifest": file_hash(MANIFEST),
        "fixtures": {
            path.name: file_hash(path)
            for path in sorted(FIXTURES.iterdir())
            if path.is_file()
        },
    }
    write_json(root / "suite.json", manifest)
    write_json(root / "control.json", case)
    write_json(root / "public.json", case["public"])
    write_json(root / "candidate-hashes.json", candidate.get("files", {}))
    write_json(root / "state.json", initial)
    write_json(root / "receipt.json", {
        "case_id": case_id,
        "case_hash": digest(case),
        "manifest_hash": digest(manifest),
        "scorer_version": manifest["scorer_version"],
        "source_hashes": source_hashes,
        "candidate": candidate,
        "candidate_hash": digest(candidate),
        "evidence_kind": evidence_kind,
    })
    write_json(root / "turns.json", [{
        "session": "session-1",
        "turn": 0,
        "role": "user",
        "content": case["public"]["prompt"],
    }])
    (root / "events.jsonl").touch()
    (root / "runtime.jsonl").touch()


class Store:
    """Record every request and simulate faults without enforcing skill policy."""

    def __init__(self, root, session="session-1", allowed_tools=None):
        self.root = Path(root)
        self.session = session
        self.allowed_tools = allowed_tools

    def _append_event(self, request, result, target_id, sequence, committed=False, external_change=False):
        path = self.root / "events.jsonl"
        turns = read_json(self.root / "turns.json")
        turn = max((entry["turn"] for entry in turns if entry["session"] == self.session), default=0)
        event = {
            "sequence": sequence,
            "session": self.session,
            "turn": turn,
            "request": deepcopy(request),
            "result": deepcopy(result),
            "record_id": target_id,
            "committed": bool(committed),
            "external_change": bool(external_change),
        }
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def call(self, request):
        control = read_json(self.root / "control.json")
        public = read_json(self.root / "public.json")
        state = read_json(self.root / "state.json")
        events_path = self.root / "events.jsonl"
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
        op = request.get("op")
        identity = request.get("identity") or {}
        target_id = identity.get("id")
        committed = False
        external_change = False
        result = {"ok": False, "error": "unknown operation or identity"}
        available_tools = self.allowed_tools if self.allowed_tools is not None else public.get("tools", [])
        if op not in available_tools:
            result = {"ok": False, "error": "operation is not available in this case"}
        elif op == "list":
            container = public.get("selected_container")
            records = [
                {key: value for key, value in record.items() if key != "content"}
                for record in state.values()
                if container is not None and record.get("container") == container
            ]
            result = {"ok": True, "records": records}
        elif op == "read":
            record = state.get(target_id)
            exact_identity = record and all(
                identity.get(key) == record.get(key) for key in ("provider", "container", "id")
            )
            fault = control.get("faults", {}).get(f"{target_id}:read")
            after_write = any(event["record_id"] == target_id and event["committed"] for event in events)
            after_fault = control.get("faults", {}).get(f"{target_id}:read-after-write") if after_write else None
            if not exact_identity:
                result = {"ok": False, "error": "unknown or mismatched identity"}
            elif fault == "reject" or after_fault == "reject":
                result = {"ok": False, "error": "synthetic read unavailable"}
            else:
                observed = deepcopy(record)
                result = {"ok": True, "record": observed}
                if after_fault == "mismatch":
                    observed["content"] = "synthetic mismatched readback"
                elif fault == "partial":
                    observed["content"] = "# Coding Preferences\n\n[synthetic read truncated; remaining content unavailable]"
                    result["warning"] = "partial synthetic read"
        elif op == "write":
            record = state.get(target_id)
            exact_identity = record and all(
                identity.get(key) == record.get(key) for key in ("provider", "container", "id")
            )
            fault = control.get("faults", {}).get(f"{target_id}:write")
            if not exact_identity:
                result = {"ok": False, "error": "unknown or mismatched identity"}
            elif record.get("owner") != "user":
                result = {"ok": False, "error": "record is not user-owned"}
            elif fault == "reject":
                result = {"ok": False, "error": "synthetic write unavailable"}
            elif fault == "conflict":
                record["content"] = read_fixture(control["faults"]["external_content_file"])
                record["revision"] = f"{record.get('revision', 'fixture')}-newer"
                write_json(self.root / "state.json", state)
                external_change = True
                result = {"ok": False, "error": "revision conflict; newer content is present"}
            elif request.get("revision") != record.get("revision"):
                result = {"ok": False, "error": "revision conflict"}
            elif not isinstance(request.get("content"), str):
                result = {"ok": False, "error": "content must be a string"}
            else:
                record["content"] = request["content"]
                record["revision"] = f"fixture-rev-{len(events) + 2:03d}"
                committed = True
                write_json(self.root / "state.json", state)
                result = {"ok": True, "revision": record["revision"]}
                if fault == "lost-ack":
                    result = {"ok": False, "error": "acknowledgement lost after commit"}
        elif op == "create":
            new_record = deepcopy(request.get("record", {}))
            target_id = new_record.get("id")
            if not target_id or target_id in state:
                result = {"ok": False, "error": "record id is missing or already exists"}
            elif not all(key in new_record for key in ("provider", "container", "id", "path", "owner", "content")):
                result = {"ok": False, "error": "record is missing required identity or content"}
            elif new_record["provider"] != "fixture" or new_record["owner"] != "user":
                result = {"ok": False, "error": "unsupported synthetic record identity"}
            elif not isinstance(new_record["content"], str):
                result = {"ok": False, "error": "content must be a string"}
            else:
                new_record.setdefault("revision", "fixture-rev-created")
                state[target_id] = new_record
                committed = True
                write_json(self.root / "state.json", state)
                result = {"ok": True, "id": target_id, "revision": new_record["revision"]}

        self._append_event(request, result, target_id, len(events) + 1, committed, external_change)
        return result


def append_turn(root, session, role, text):
    path = Path(root) / "turns.json"
    turns = read_json(path)
    turn = max((entry["turn"] for entry in turns if entry["session"] == session), default=-1) + 1
    turns.append({"session": session, "turn": turn, "role": role, "content": text})
    write_json(path, turns)


def snapshot(root):
    state = read_json(Path(root) / "state.json")
    write_json(Path(root) / "final-state.json", state)
    return state


TOOL_DETAILS = {
    "list": ("List metadata for records in the selected container. This does not return record content.", {}, []),
    "read": (
        "Read one record by its exact provider, container, and id. Returns identity, revision, and content.",
        {"identity": {"type": "object", "properties": {
            key: {"type": "string"} for key in ("provider", "container", "id")
        }, "required": ["provider", "container", "id"]}},
        ["identity"],
    ),
    "write": (
        "Write the complete content of one existing record. Supply its exact identity and current revision. A conflict or lost acknowledgement requires a fresh read before any retry.",
        {
            "identity": {"type": "object", "properties": {
                key: {"type": "string"} for key in ("provider", "container", "id")
            }, "required": ["provider", "container", "id"]},
            "revision": {"type": "string"},
            "content": {"type": "string"},
        },
        ["identity", "revision", "content"],
    ),
    "create": (
        "Create one user-owned record at an explicitly selected destination.",
        {"record": {"type": "object", "properties": {
            "provider": {"type": "string"}, "container": {"type": "string"}, "id": {"type": "string"},
            "path": {"type": "string"}, "owner": {"type": "string"}, "content": {"type": "string"},
            "revision": {"type": "string"},
        }, "required": ["provider", "container", "id", "path", "owner", "content"]}},
        ["record"],
    ),
}
TOOL_ANNOTATIONS = {
    "list": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    "read": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    "write": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
    "create": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
}


def serve(root, session, allowed_tools=None):
    public = read_json(Path(root) / "public.json")
    active_tools = allowed_tools if allowed_tools is not None else public.get("tools", [])
    if not set(active_tools) <= set(public.get("tools", [])):
        raise ValueError("Session tools must be a subset of the declared case operations")
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method = request.get("method")
        params = request.get("params", {})
        response = {"jsonrpc": "2.0", "id": request["id"]}
        if method == "initialize":
            requested = params.get("protocolVersion")
            response["result"] = {
                "protocolVersion": requested if requested in SUPPORTED_PROTOCOLS else "2025-11-25",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "coding-preferences-synthetic-store", "version": "1.0.0"},
            }
        elif method == "ping":
            response["result"] = {}
        elif method == "tools/list":
            tools = []
            for name in active_tools:
                description, properties, required = TOOL_DETAILS[name]
                tools.append({
                    "name": name,
                    "description": description,
                    "annotations": TOOL_ANNOTATIONS[name],
                    "inputSchema": {"type": "object", "properties": properties, "required": required},
                })
            response["result"] = {"tools": tools}
        elif method == "tools/call" and params.get("name") in active_tools:
            result = Store(root, session, active_tools).call({**params.get("arguments", {}), "op": params["name"]})
            response["result"] = {"content": [{"type": "text", "text": json.dumps(result)}], "isError": not result["ok"]}
        else:
            response["error"] = {"code": -32601, "message": "Unknown fixture method or unavailable synthetic operation"}
        print(json.dumps(response), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "call", "snapshot", "serve", "turn"])
    parser.add_argument("root", type=Path)
    parser.add_argument("--case")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--evidence-kind", default="deterministic-control")
    parser.add_argument("--request", help="one JSON tool request")
    parser.add_argument("--session", default="session-1")
    parser.add_argument("--tools", nargs="*", help="session-specific subset of declared tools")
    parser.add_argument("--role", choices=["user", "assistant"])
    parser.add_argument("--text")
    args = parser.parse_args()
    if args.action == "init":
        initialize(args.root, args.case, read_json(args.candidate), args.evidence_kind)
    elif args.action == "call":
        print(json.dumps(Store(args.root, args.session).call(json.loads(args.request))))
    elif args.action == "serve":
        serve(args.root, args.session, args.tools)
    elif args.action == "snapshot":
        print(json.dumps(snapshot(args.root)))
    elif args.action == "turn":
        if args.role is None or args.text is None:
            parser.error("turn requires --role and --text")
        append_turn(args.root, args.session, args.role, args.text)


if __name__ == "__main__":
    main()
