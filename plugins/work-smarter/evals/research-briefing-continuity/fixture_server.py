#!/usr/bin/env python3
"""Read-only MCP source fixture server for Research Briefing continuity trials."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROTOCOL_VERSION = "2025-11-25"


class FixtureServer:
    def __init__(self, fixture_root: Path, event_path: Path, case_id: str, candidate_id: str):
        self.fixture_root = fixture_root.resolve()
        self.event_path = event_path
        self.case_id = case_id
        self.candidate_id = candidate_id
        self.index = json.loads((self.fixture_root / "source-index.json").read_text(encoding="utf-8"))
        self.sources = {item["id"]: item for item in self.index["sources"]}
        existing_events = event_path.read_text(encoding="utf-8").splitlines() if event_path.exists() else []
        self.sequence = json.loads(existing_events[-1]).get("sequence", 0) if existing_events else 0

    def record(self, event: dict[str, Any]) -> None:
        self.sequence += 1
        complete = {
            "sequence": self.sequence,
            "case_id": self.case_id,
            "candidate_id": self.candidate_id,
            **event,
        }
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        with self.event_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(complete, sort_keys=True) + "\n")

    def search(self, query: str) -> dict[str, Any]:
        terms = {part.casefold() for part in query.split() if len(part) > 2}
        matches = []
        for source in self.index["sources"]:
            searchable = " ".join(
                [source["title"], source["authority"], *source["applies_to"], *source["topics"]]
            ).casefold()
            if not terms or any(term in searchable for term in terms):
                matches.append({key: source[key] for key in ("id", "title", "authority", "applies_to", "status")})
        result = {"query": query, "sources": matches}
        self.record({"operation": "search_sources", "query": query, "result": result, "exit_status": 0})
        return result

    def read(self, source_id: str) -> dict[str, Any]:
        source = self.sources.get(source_id)
        if source is None:
            result = {"source_id": source_id, "status": "not_found"}
            self.record({"operation": "read_source", "source_id": source_id, "result": result, "exit_status": 1})
            return result
        if source["status"] == "unavailable":
            result = {
                "source_id": source_id,
                "title": source["title"],
                "status": "unavailable",
                "authority": source["authority"],
                "applies_to": source["applies_to"],
            }
            self.record({"operation": "read_source", "source_id": source_id, "result": result, "exit_status": 1})
            return result

        path = (self.fixture_root / source["path"]).resolve()
        if not path.is_relative_to(self.fixture_root) or not path.is_file():
            result = {"source_id": source_id, "status": "fixture_error"}
            self.record({"operation": "read_source", "source_id": source_id, "result": result, "exit_status": 1})
            return result
        content = path.read_text(encoding="utf-8")
        result = {
            "source_id": source_id,
            "title": source["title"],
            "authority": source["authority"],
            "applies_to": source["applies_to"],
            "status": "read",
            "content": content,
        }
        self.record({
            "operation": "read_source",
            "source_id": source_id,
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "result": {key: value for key, value in result.items() if key != "content"},
            "exit_status": 0,
        })
        return result

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "search_sources":
            query = arguments.get("query")
            if not isinstance(query, str) or not query.strip():
                result = {"error": "query must be a non-empty string"}
                self.record({"operation": name, "arguments": arguments, "result": result, "exit_status": 2})
                return {"isError": True, "content": [{"type": "text", "text": json.dumps(result)}]}
            result = self.search(query)
        elif name == "read_source":
            source_id = arguments.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                result = {"error": "source_id must be a non-empty string"}
                self.record({"operation": name, "arguments": arguments, "result": result, "exit_status": 2})
                return {"isError": True, "content": [{"type": "text", "text": json.dumps(result)}]}
            result = self.read(source_id)
            if result["status"] != "read":
                return {"isError": True, "content": [{"type": "text", "text": json.dumps(result)}]}
        else:
            result = {"error": f"unknown fixture operation: {name}"}
            self.record({"operation": name, "arguments": arguments, "result": result, "exit_status": 2})
            return {"isError": True, "content": [{"type": "text", "text": json.dumps(result)}]}
        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "structuredContent": result,
        }


def tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "search_sources",
            "description": "Search only the synthetic source index for this test case. This does not retrieve source content.",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "A topic, model, version, service, or claim to locate."}},
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": False},
        },
        {
            "name": "read_source",
            "description": "Read exact content from one synthetic source returned by search_sources. No other files or network sources are available.",
            "inputSchema": {
                "type": "object",
                "properties": {"source_id": {"type": "string", "description": "An id returned by search_sources."}},
                "required": ["source_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": False},
        },
    ]


def read_message() -> dict[str, Any] | None:
    line = sys.stdin.buffer.readline()
    if not line:
        return None
    return json.loads(line.decode("utf-8"))


def write_message(message: dict[str, Any]) -> None:
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write(payload + "\n")
    sys.stdout.flush()


def serve(server: FixtureServer) -> int:
    while request := read_message():
        method = request.get("method")
        request_id = request.get("id")
        if method == "notifications/initialized" or request_id is None:
            continue
        if method == "initialize":
            params = request.get("params", {})
            result = {
                "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "research-briefing-continuity-fixtures", "version": "1.0.0"},
            }
            server.record({
                "operation": "mcp_initialize",
                "requested_protocol_version": params.get("protocolVersion"),
                "negotiated_protocol_version": result["protocolVersion"],
                "exit_status": 0,
            })
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            advertised_tools = tools()
            result = {"tools": advertised_tools}
            server.record({
                "operation": "mcp_tools_list",
                "tool_names": [item["name"] for item in advertised_tools],
                "exit_status": 0,
            })
        elif method == "tools/call":
            params = request.get("params", {})
            result = server.call(params.get("name", ""), params.get("arguments", {}))
        else:
            write_message({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}})
            continue
        write_message({"jsonrpc": "2.0", "id": request_id, "result": result})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("serve", choices=["serve"])
    parser.add_argument("fixture_root", type=Path)
    parser.add_argument("event_path", type=Path)
    parser.add_argument("case_id")
    parser.add_argument("candidate_id")
    args = parser.parse_args()
    return serve(FixtureServer(args.fixture_root, args.event_path, args.case_id, args.candidate_id))


if __name__ == "__main__":
    raise SystemExit(main())
