"""Read frozen Markdown resources from a CLI-installed candidate; no provider access."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


SERVER = "shopping-skill-resources"
TOOL = "read_installed_skill_file"


def read_resource(control: dict, arguments: dict) -> dict:
    if not isinstance(arguments, dict) or set(arguments) not in ({"relative_path"}, {"package", "relative_path"}):
        raise ValueError("invalid resource arguments")
    package = arguments.get("package")
    if package is None:
        root_path, files = control["installed_skill_root"], control["files"]
    else:
        packages = control.get("packages", {})
        if not isinstance(package, str) or package not in packages:
            raise ValueError("resource package is not allowed")
        root_path, files = packages[package]["installed_root"], packages[package]["files"]
    relative = arguments["relative_path"]
    if not isinstance(relative, str) or "\\" in relative:
        raise ValueError("invalid resource path")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts or str(parts) != relative \
            or not relative.endswith(".md") or relative not in files:
        raise ValueError("resource outside installed allowlist")
    root = Path(root_path).resolve(strict=True)
    path = root / relative
    if any(item.is_symlink() for item in (path, *path.parents)) \
            or root not in path.resolve(strict=True).parents:
        raise ValueError("unsafe installed resource")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != files[relative]:
        raise ValueError("installed resource changed")
    text = raw.decode("utf-8")
    if text.encode("utf-8") != raw:
        raise ValueError("resource encoding mismatch")
    payload = {"relative_path": relative, "sha256": digest, "text": text}
    if package is not None:
        payload["package"] = package
    return payload


def serve(control_path: Path) -> None:
    control = json.loads(control_path.read_text(encoding="utf-8"))
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        response = {"jsonrpc": "2.0", "id": request["id"]}
        method, params = request.get("method"), request.get("params", {})
        if method == "initialize":
            result = {"protocolVersion": params["protocolVersion"], "capabilities": {"tools": {}},
                      "serverInfo": {"name": SERVER, "version": "1.0.0"}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            multi_package = "packages" in control
            properties = {"relative_path": {"type": "string"}}
            if multi_package:
                properties["package"] = {"type": "string", "enum": list(control["packages"])}
            result = {"tools": [{"name": TOOL, "description":
                "Read exact frozen Markdown bytes from an installed candidate package. "
                "Read the skill instructions and linked contracts by their declared paths. "
                "This is a local package reader, never spreadsheet evidence.",
                "inputSchema": {"type": "object", "properties": properties,
                                "required": ["package", "relative_path"] if multi_package else ["relative_path"], "additionalProperties": False},
                "annotations": {"readOnlyHint": True, "openWorldHint": False}}]}
        elif method == "tools/call":
            try:
                if params.get("name") != TOOL:
                    raise ValueError("unknown installed resource tool")
                payload = read_resource(control, params.get("arguments"))
                result = {"content": [{"type": "text", "text": json.dumps(payload)}],
                          "structuredContent": payload, "isError": False}
            except (ValueError, OSError, KeyError, UnicodeError):
                result = {"content": [{"type": "text", "text": "Installed resource unavailable or changed"}],
                          "isError": True}
        else:
            response["error"] = {"code": -32601, "message": "Unsupported resource method"}
            result = None
        if result is not None:
            response["result"] = result
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    serve(Path(sys.argv[1]))
