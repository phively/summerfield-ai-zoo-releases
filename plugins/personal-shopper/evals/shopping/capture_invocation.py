#!/usr/bin/env python3
"""Capture a real Codex CLI skill invocation and its complete JSONL host stream."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import threading
from typing import Any
from urllib.parse import unquote, urlsplit


SKILL_ID = "personal-shopper:personal-shopper"
MARKETPLACE_NAME = "shopping-trial"
READ_ONLY_CODEX_TOOLS = {
    "shell_tool": False,
    "unified_exec": False,
    "apps": False,
    "plugins": True,
    "skill_search": False,
    "multi_agent": False,
    "memories": False,
    "image_generation": False,
    "view_image": False,
    "sleep_tool": False,
    "computer_use": False,
    "browser_use": False,
    "tool_suggest": False,
    "goals": False,
    "fast_mode": False,
    "ultrafast_mode": False,
    "skip_host_skill_discovery": True,
}
SAFE_CHILD_ENV = {
    "PATH", "CODEX_HOME", "LANG", "LC_ALL", "SSL_CERT_FILE", "HTTPS_PROXY",
    "HTTP_PROXY", "NO_PROXY", "SYSTEMROOT",
}
SENSITIVE_ENV_NAME = re.compile(r"(?:TOKEN|SECRET|PASSWORD|CREDENTIAL|SHOPPING|GOOGLE|SHEETS)", re.I)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_host_stream(raw: bytes) -> list[dict[str, Any]]:
    """Parse complete JSONL records without filtering lifecycle or unknown events."""
    if not raw or not raw.endswith(b"\n"):
        raise ValueError("incomplete host event stream")
    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        try:
            value = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("invalid host event stream") from error
        if not isinstance(value, dict) or not isinstance(value.get("type"), str):
            raise ValueError("invalid host event record")
        events.append(value)
    if not events:
        raise ValueError("empty host event stream")
    return events


def mcp_tool_ledger(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse MCP lifecycle events into calls while retaining every event index."""
    calls: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for index, event in enumerate(events):
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "mcp_tool_call":
            continue
        call_id = item.get("id")
        server = item.get("server")
        tool = item.get("tool") or item.get("name")
        if not all(isinstance(value, str) and value for value in (call_id, server, tool)):
            raise ValueError("invalid MCP tool event")
        arguments = item.get("arguments", item.get("input"))
        if arguments is not None and not isinstance(arguments, (dict, list, str)):
            raise ValueError("invalid MCP tool arguments")
        if call_id not in calls:
            calls[call_id] = {
                "call_id": call_id,
                "server": server,
                "tool": tool,
                "arguments": arguments,
                "result": None,
                "status": "incomplete",
                "event_indexes": [],
            }
            order.append(call_id)
        record = calls[call_id]
        if (record["server"], record["tool"]) != (server, tool):
            raise ValueError("MCP call identity changed during host stream")
        if arguments is not None:
            if record["arguments"] is not None and record["arguments"] != arguments:
                raise ValueError("MCP call arguments changed during host stream")
            record["arguments"] = arguments
        record["event_indexes"].append(index)
        status = item.get("status")
        if status in {"completed", "failed", "cancelled"}:
            record["status"] = status
        elif event.get("type") == "item.completed":
            record["status"] = "completed"
        elif event.get("type") in {"item.failed", "turn.failed", "error"}:
            record["status"] = "failed"
        if "result" in item:
            record["result"] = item["result"]
        elif "output" in item:
            record["result"] = item["output"]
        if "error" in item:
            record["error"] = item["error"]
    return [calls[call_id] for call_id in order]


def _expand_files(root: Path, patterns: list[str]) -> dict[str, Path]:
    root = root.resolve(strict=True)
    files: dict[str, Path] = {}
    for pattern in patterns:
        relative_pattern = PurePosixPath(pattern)
        if relative_pattern.is_absolute() or ".." in relative_pattern.parts:
            raise ValueError("identity patterns must stay inside their root")
        file_pattern = pattern + "/*" if pattern.endswith("/**") else pattern
        matches = [path for path in root.glob(file_pattern)
                   if path.is_file() and "__pycache__" not in path.relative_to(root).parts
                   and path.suffix.lower() not in {".pyc", ".pyo"}]
        if not matches:
            raise ValueError(f"required identity pattern has no files: {pattern}")
        for path in matches:
            if path.is_symlink():
                raise ValueError("identity contains a symlink")
            resolved = path.resolve(strict=True)
            if root not in resolved.parents:
                raise ValueError("identity file escaped its root")
            relative = resolved.relative_to(root).as_posix()
            files[relative] = resolved
    return dict(sorted(files.items()))


def hash_identity(root: Path, patterns: list[str]) -> dict[str, str]:
    """Return per-file digests, failing when a required identity glob is empty."""
    return {relative: sha256(path.read_bytes()) for relative, path in _expand_files(root, patterns).items()}


def identity_digest(root: Path, patterns: list[str]) -> str:
    files = _expand_files(root, patterns)
    digest = hashlib.sha256()
    for relative, path in files.items():
        path_bytes = relative.encode("utf-8")
        content = path.read_bytes()
        digest.update(len(path_bytes).to_bytes(4, "big"))
        digest.update(path_bytes)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def candidate_identity_patterns(manifest: dict[str, Any]) -> list[str]:
    candidate = manifest.get("candidate")
    packages = candidate.get("packages") if isinstance(candidate, dict) else None
    if not isinstance(packages, dict) or not packages:
        raise ValueError("candidate package declarations are missing")
    patterns: set[str] = set()
    for name, package in sorted(packages.items()):
        if not isinstance(package, dict):
            raise ValueError("candidate package declaration is invalid")
        source_root = package.get("source_root")
        if source_root is None and package.get("runtime_plugin_id"):
            continue
        if not isinstance(source_root, str) or not source_root:
            raise ValueError(f"local candidate package source is missing: {name}")
        root = PurePosixPath(source_root)
        files = package.get("files")
        if root.is_absolute() or ".." in root.parts or not isinstance(files, list) or not files:
            raise ValueError(f"local candidate package file declarations are invalid: {name}")
        for pattern in files:
            if not isinstance(pattern, str) or not pattern:
                raise ValueError(f"local candidate package file pattern is invalid: {name}")
            relative = PurePosixPath(pattern)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"local candidate package file pattern escapes its root: {name}")
            patterns.add(f"{root.as_posix()}/{relative.as_posix()}")
    if not patterns:
        raise ValueError("candidate has no local production packages")
    return sorted(patterns)


def local_profile_file_hashes(source_root: Path, manifest: dict[str, Any],
                              profile_id: str) -> dict[str, str]:
    source_root = source_root.resolve(strict=True)
    names, packages = _profile_files(manifest, profile_id)
    hashes: dict[str, str] = {}
    for name in names:
        package = packages[name]
        if package.get("runtime_plugin_id") and not package.get("source_root"):
            continue
        package_root_value = package.get("source_root")
        if not isinstance(package_root_value, str) or not package_root_value:
            raise ValueError(f"local candidate package source is missing: {name}")
        package_root = source_root / package_root_value
        for relative, path in _expand_files(package_root, package.get("files", [] )).items():
            hashes[f"{name}/{relative}"] = sha256(path.read_bytes())
    return dict(sorted(hashes.items()))


def installed_local_files_match(result: dict[str, Any], manifest: dict[str, Any],
                                source_root: Path) -> bool:
    profile_id = result.get("profile_id")
    if not isinstance(profile_id, str):
        return False
    try:
        expected = local_profile_file_hashes(source_root, manifest, profile_id)
    except (KeyError, OSError, TypeError, ValueError):
        return False
    installed = result.get("installed_file_sha256")
    if not isinstance(installed, dict):
        return False
    names, packages = _profile_files(manifest, profile_id)
    local_names = [name for name in names if packages[name].get("source_root")]
    prefixes = tuple(f"{name}/" for name in local_names)
    actual = {path: digest for path, digest in installed.items()
              if isinstance(path, str) and path.startswith(prefixes)}
    return actual == expected


def _prompt_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (_prompt_text(item) for item in value)))
    if isinstance(value, dict):
        return "\n".join(filter(None, (_prompt_text(item) for item in value.values())))
    return ""


def verify_skill_discovery(prompt_input: Any, package_roots: dict[str, Path],
                           package_details: dict[str, dict[str, Any]],
                           required_skill_ids: list[str] | None = None) -> dict[str, Any]:
    """Verify requested skill IDs from the isolated candidate packages."""
    messages = prompt_input if isinstance(prompt_input, list) else [prompt_input]
    developer_text = "\n".join(
        _prompt_text(message.get("content"))
        for message in messages
        if isinstance(message, dict) and message.get("role") == "developer"
    )
    if not developer_text:
        raise ValueError("Codex skill catalog is unavailable")

    required = set(required_skill_ids) if required_skill_ids is not None else None
    discovered: list[str] = []
    for package_name, root in sorted(package_roots.items()):
        version = package_details.get(package_name, {}).get("version")
        if not isinstance(version, str) or not version:
            raise ValueError("installed candidate version is unavailable for skill discovery")
        root = root.resolve(strict=True)
        skill_files = sorted(root.glob("skills/**/SKILL.md"))
        if not skill_files:
            raise ValueError("installed candidate package has no skills to discover")
        for skill_file in skill_files:
            if skill_file.is_symlink() or root not in skill_file.resolve(strict=True).parents:
                raise ValueError("installed skill path is unsafe")
            contents = skill_file.read_text(encoding="utf-8")
            frontmatter = re.match(r"\A---\s*\n(.*?)\n---(?:\s|$)", contents, re.S)
            match = re.search(r"(?m)^name:\s*[\"']?([a-z0-9-]+)[\"']?\s*$",
                              frontmatter.group(1) if frontmatter else "")
            if not match:
                raise ValueError("installed candidate skill identity is invalid")
            skill_id = f"{package_name}:{match.group(1)}"
            entry_count = len(re.findall(
                rf"(?m)^\s*[-*]\s*{re.escape(skill_id)}\s*:", developer_text
            ))
            if entry_count > 1:
                raise ValueError("candidate skill identity is ambiguous in the host catalog")
            if entry_count == 0:
                if required is None or skill_id in required:
                    raise ValueError("candidate skill is not discoverable from the installed package")
                continue
            if skill_id in discovered:
                raise ValueError("candidate skill identity is duplicated in the host catalog")
            discovered.append(skill_id)

    if required is not None and not required.issubset(discovered):
        raise ValueError("requested candidate skill is not discoverable from the installed package")

    return {
        "candidate_skills": sorted(discovered),
        "candidate_skill_path_count": len(discovered),
        "catalog_sha256": sha256(developer_text.encode("utf-8")),
    }


def _profile_files(manifest: dict[str, Any], profile_id: str) -> tuple[list[str], dict[str, Any]]:
    candidate = manifest.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("candidate manifest is missing")
    profile = candidate.get("profiles", {}).get(profile_id)
    packages = candidate.get("packages")
    if not isinstance(profile, dict) or not isinstance(packages, dict):
        raise ValueError("unknown or invalid candidate profile")
    names = profile.get("packages")
    if not isinstance(names, list) or not names or len(names) != len(set(names)):
        raise ValueError("candidate profile must name unique packages")
    return names, packages


_MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]*)\)")
_MARKDOWN_FENCE = re.compile(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$")


def _validate_package_local_links(package_root: Path, files: dict[str, Path]) -> None:
    package_root = package_root.resolve(strict=True)
    included = set(files)
    for relative, source in files.items():
        if source.suffix.lower() != ".md":
            continue
        text = _MARKDOWN_FENCE.sub("", source.read_text(encoding="utf-8"))
        for match in _MARKDOWN_LINK.finditer(text):
            destination = match.group(1).strip()
            if destination.startswith("<") and ">" in destination:
                destination = destination[1:destination.index(">")]
            else:
                destination = destination.split(None, 1)[0] if destination else ""
            if not destination or destination.startswith("#") or urlsplit(destination).scheme:
                continue
            path_text = destination.split("#", 1)[0].split("?", 1)[0]
            if not path_text:
                path_text = relative
            if "\\" in path_text or PurePosixPath(path_text).is_absolute():
                raise ValueError(f"package-local reference escapes its package: {relative}")
            lexical = Path(os.path.abspath(source.parent / unquote(path_text)))
            try:
                expected_relative = lexical.relative_to(package_root).as_posix()
            except ValueError as error:
                raise ValueError(f"package-local reference escapes its package: {relative}") from error
            cursor = lexical
            while cursor != package_root:
                if cursor.is_symlink():
                    raise ValueError(f"package-local reference uses a symlink: {relative}")
                cursor = cursor.parent
            resolved = lexical.resolve(strict=False)
            if package_root not in resolved.parents or not resolved.is_file():
                raise ValueError(f"package-local reference target is missing: {relative}")
            resolved_relative = resolved.relative_to(package_root).as_posix()
            if expected_relative != resolved_relative or resolved_relative not in included:
                raise ValueError(f"package-local reference is not declared: {relative}")


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _profile_config(workspace: Path, packages: list[str], package_details: dict[str, Any],
                    profile: dict[str, Any]) -> str:
    multi_agent_enabled = profile.get("multi_agent", False)
    if not isinstance(multi_agent_enabled, bool):
        raise ValueError("profile multi-agent policy must be boolean")
    provider_apps = profile.get("provider_apps", [])
    if not isinstance(provider_apps, list):
        raise ValueError("profile provider app policy must be a list")
    enabled_apps: dict[str, dict[str, Any]] = {}
    for policy in provider_apps:
        if not isinstance(policy, dict) or set(policy) not in (
                {"plugin", "tools"}, {"plugin", "tools", "tool_approval_modes"}):
            raise ValueError("invalid provider app policy")
        plugin = policy["plugin"]
        tools = policy["tools"]
        if plugin not in packages or not isinstance(tools, list) or not tools \
                or any(not isinstance(tool, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", tool)
                       for tool in tools) or len(tools) != len(set(tools)):
            raise ValueError("provider app tools must be explicit and belong to a staged package")
        approval_modes = policy.get("tool_approval_modes", {})
        if not isinstance(approval_modes, dict) or any(
                not isinstance(tool, str) or tool not in tools or mode != "approve"
                for tool, mode in approval_modes.items()):
            raise ValueError("provider app approval overrides must approve only declared tools")
        app_path = workspace / "plugins" / plugin / ".app.json"
        try:
            app_manifest = json.loads(app_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("provider package is missing its app manifest") from error
        apps = app_manifest.get("apps")
        if not isinstance(apps, dict) or not apps:
            raise ValueError("provider package has no declared app")
        if len(apps) != 1:
            raise ValueError("provider package must declare exactly one app for an isolated profile")
        app_record = next(iter(apps.values()))
        app_id = app_record.get("id") if isinstance(app_record, dict) else None
        if not isinstance(app_id, str) or not app_id or app_id in enabled_apps:
            raise ValueError("provider app identity is missing or duplicated")
        enabled_apps[app_id] = {"tools": tools, "tool_approval_modes": approval_modes}

    lines = ["[features]"]
    feature_values = dict(READ_ONLY_CODEX_TOOLS)
    feature_values["apps"] = bool(enabled_apps)
    feature_values["multi_agent"] = multi_agent_enabled
    lines.extend(f"{name} = {'true' if enabled else 'false'}" for name, enabled in feature_values.items())
    lines.extend(("", "[apps._default]", "enabled = false", "default_tools_enabled = false", ""))
    for package in packages:
        plugin_id = package_details[package].get("plugin_id", package)
        lines.extend((f"[plugins.{_toml_string(plugin_id + '@' + MARKETPLACE_NAME)}]", "enabled = true", ""))
    for app_id, app_policy in sorted(enabled_apps.items()):
        quoted_app = _toml_string(app_id)
        lines.extend((f"[apps.{quoted_app}]", "enabled = true", "default_tools_enabled = false", "destructive_enabled = false", "open_world_enabled = false", ""))
        for tool in sorted(app_policy["tools"]):
            lines.extend((f"[apps.{quoted_app}.tools.{_toml_string(tool)}]", "enabled = true"))
            approval_mode = app_policy["tool_approval_modes"].get(tool)
            if approval_mode is not None:
                lines.append(f"approval_mode = {_toml_string(approval_mode)}")
            lines.append("")
    return "\n".join(lines)


def resolve_installed_plugin_root(plugin_id: str, codex_home: Path | None = None,
                                 executable: str = "codex") -> tuple[Path, dict[str, Any]]:
    """Resolve a provider plugin from the installed CLI inventory and verify its cache manifest."""
    try:
        inventory = subprocess.run(
            [executable, "plugin", "list", "--json"], capture_output=True, text=True,
            check=True, env=filtered_environment(dict(os.environ)), timeout=30,
        )
        payload = json.loads(inventory.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        raise ValueError("Codex plugin inventory is unavailable") from error
    plugins = payload.get("installed") if isinstance(payload, dict) else None
    match = next((item for item in plugins or [] if isinstance(item, dict)
                  and item.get("pluginId") == plugin_id and item.get("installed") is True
                  and item.get("enabled") is True), None)
    if match is None:
        raise ValueError("required provider plugin is not installed and enabled")
    home = codex_home or Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    root = home / "plugins" / "cache" / str(match.get("marketplaceName")) \
        / str(match.get("name")) / str(match.get("version"))
    try:
        plugin_manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("installed provider plugin cache is incomplete") from error
    if plugin_manifest.get("name") != match.get("name") or plugin_manifest.get("version") != match.get("version"):
        raise ValueError("installed provider plugin cache identity does not match CLI inventory")
    return root.resolve(strict=True), match


def stage_profile(source_root: Path, workspace: Path, manifest: dict[str, Any], profile_id: str,
                  package_roots: dict[str, Path] | None = None) -> dict[str, Any]:
    """Stage only declared production files into a clean candidate workspace."""
    source_root = source_root.resolve(strict=True)
    workspace = workspace.resolve()
    if source_root == workspace or source_root in workspace.parents:
        raise ValueError("candidate workspace must be outside the source checkout")
    current = workspace
    while current != current.parent:
        if (current / "AGENTS.md").is_file():
            raise ValueError("candidate workspace inherits repository instructions")
        current = current.parent
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError("candidate workspace must be new or empty")
    names, packages = _profile_files(manifest, profile_id)
    profile = manifest["candidate"]["profiles"][profile_id]
    profile = dict(profile)
    provider_apps_by_profile = manifest["candidate"].get("provider_apps", {})
    if not isinstance(provider_apps_by_profile, dict):
        raise ValueError("candidate provider app policy must be a mapping")
    profile["provider_apps"] = provider_apps_by_profile.get(profile_id, [])
    package_roots = package_roots or {}
    provider_plugins = [name for name in names if packages[name].get("runtime_plugin_id")]
    prepared: dict[str, tuple[dict[str, Any], dict[str, Path]]] = {}
    for name in names:
        package = packages.get(name)
        if not isinstance(package, dict):
            raise ValueError("candidate profile references an unknown package")
        package_root = package_roots.get(name)
        if package_root is None and isinstance(package.get("source_root"), str):
            package_root = source_root / package["source_root"]
        if package_root is None:
            raise ValueError("candidate package source is unavailable")
        package_root = package_root.resolve(strict=True)
        source_files = _expand_files(package_root, package.get("files", []))
        if package.get("source_root"):
            _validate_package_local_links(package_root, source_files)
        prepared[name] = package, source_files
    workspace.mkdir(parents=True, exist_ok=True)
    os.chmod(workspace, 0o700)
    staged: dict[str, str] = {}
    marketplace_plugins = []
    for name in names:
        package, source_files = prepared[name]
        destination_root = workspace / "plugins" / name
        for relative, source in source_files.items():
            destination = destination_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            staged[f"plugins/{name}/{relative}"] = sha256(destination.read_bytes())
        manifest_path = destination_root / ".codex-plugin" / "plugin.json"
        if not manifest_path.is_file():
            raise ValueError("candidate package is missing its Codex plugin manifest")
        try:
            staged_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("candidate package has an invalid Codex plugin manifest") from error
        if staged_manifest.get("name") != name:
            raise ValueError("candidate package name does not match its Codex plugin manifest")
        runtime_id = package.get("runtime_plugin_id")
        if runtime_id and package.get("version") and staged_manifest.get("version") != package.get("version"):
            raise ValueError("provider plugin package version changed during profile staging")
        marketplace_plugins.append({
            "name": name,
            "source": {"source": "local", "path": f"./plugins/{name}"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        })
    marketplace = {"name": MARKETPLACE_NAME, "plugins": marketplace_plugins}
    marketplace_path = workspace / ".agents" / "plugins" / "marketplace.json"
    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    marketplace_path.write_text(json.dumps(marketplace, indent=2) + "\n", encoding="utf-8")
    config_path = workspace / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_text = _profile_config(workspace, names, packages, profile)
    config_path.write_text(config_text, encoding="utf-8")
    agent_profiles = {
        "schema_version": 1,
        "profile": profile_id,
        "skill_paths": [str((workspace / "plugins" / name / "skills").resolve())
                        for name in names if (workspace / "plugins" / name / "skills").is_dir()],
    }
    (workspace / ".agents" / "skill-profile.json").write_text(
        json.dumps(agent_profiles, indent=2) + "\n", encoding="utf-8")
    return {
        "profile": profile_id,
        "packages": names,
        "provider_plugins": provider_plugins,
        "provider_apps": profile.get("provider_apps", []),
        "files": staged,
        "marketplace_sha256": sha256(marketplace_path.read_bytes()),
        "config_sha256": sha256(config_path.read_bytes()),
        "profile_sha256": identity_digest(workspace, ["plugins/**"]),
        "source_packages": {name: str(package_roots[name]) for name in sorted(package_roots)
                            if name in names},
    }


def filtered_environment(environ: dict[str, str], allowlist: set[str] | None = None) -> dict[str, str]:
    """Pass only runtime essentials to the host; private shopping inputs stay controller-side."""
    allowed = SAFE_CHILD_ENV if allowlist is None else allowlist
    if any(name in allowed and SENSITIVE_ENV_NAME.search(name) for name in allowed):
        raise ValueError("host environment allowlist contains a sensitive variable name")
    return {name: value for name, value in environ.items() if name in allowed}


def build_codex_command(workspace: str | Path, executable: str = "codex", *,
                        apps_enabled: bool = False, multi_agent_enabled: bool = False,
                        persist_rollouts: bool = False) -> list[str]:
    """Build a fresh CLI invocation with global config and filesystem tools disabled."""
    if not isinstance(multi_agent_enabled, bool) or not isinstance(persist_rollouts, bool) \
            or persist_rollouts and not multi_agent_enabled:
        raise ValueError("delegation and rollout persistence policy is invalid")
    workspace_path = str(Path(workspace).resolve())
    trust_override = f"projects.{_toml_string(workspace_path)}.trust_level=\"trusted\""
    command = [
        executable, "exec", "--json",
        "--skip-git-repo-check", "--strict-config", "--sandbox", "read-only",
        "--cd", workspace_path, "-c", trust_override,
        "--disable", "shell_tool", "--disable", "unified_exec",
        "--disable", "computer_use",
        "--disable", "browser_use", "--disable", "image_generation",
        "--disable", "view_image", "--disable", "sleep_tool",
        "--disable", "memories", "--disable", "goals", "--disable", "tool_suggest",
        "-",
    ]
    if not persist_rollouts:
        command.insert(3, "--ephemeral")
    if multi_agent_enabled:
        command[-1:-1] = ["--enable", "multi_agent"]
    else:
        command[-1:-1] = ["--disable", "multi_agent"]
    if not apps_enabled:
        # App integrations can be injected by the host even when project config
        # disables them. Repeat the deny at the CLI boundary for synthetic runs.
        command[-1:-1] = ["--disable", "apps"]
    return command


def build_activation_prompt(skill_id: str, task: str, additional_skill_ids: list[str] | None = None) -> str:
    """Select installed skills by identity; never concatenate their source text."""
    if not isinstance(skill_id, str) or not re.fullmatch(r"[a-z0-9-]+:[a-z0-9-]+", skill_id):
        raise ValueError("invalid qualified skill identity")
    additional_skill_ids = additional_skill_ids or []
    if not isinstance(additional_skill_ids, list) \
            or any(not isinstance(value, str) or not re.fullmatch(r"[a-z0-9-]+:[a-z0-9-]+", value)
                   or value == skill_id for value in additional_skill_ids):
        raise ValueError("invalid additional qualified skill identity")
    if len(additional_skill_ids) != len(set(additional_skill_ids)):
        raise ValueError("invalid additional qualified skill identity")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("trial task must not be empty")
    selected = [skill_id, *additional_skill_ids]
    selection = ", ".join(f"${value}" for value in selected)
    return f"Use {selection} for this task. Follow their installed instructions and use only tools available in this trial profile.\n\n{task.strip()}\n"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stream_stdout(stream, raw_path: Path, timestamps_path: Path, reader_state: dict[str, Any]) -> None:
    try:
        with raw_path.open("wb") as raw_file, timestamps_path.open("w", encoding="utf-8") as time_file:
            os.chmod(raw_path, 0o600)
            os.chmod(timestamps_path, 0o600)
            line_number = 0
            for line in iter(stream.readline, b""):
                raw_file.write(line)
                raw_file.flush()
                time_file.write(json.dumps({"line": line_number, "observed_at": _utc_now()}) + "\n")
                time_file.flush()
                line_number += 1
        reader_state["complete"] = True
    except Exception as error:
        reader_state["error"] = type(error).__name__


def run_codex(command: list[str], workspace: Path, trial_dir: Path, prompt: str,
              timeout_seconds: int = 900, environ: dict[str, str] | None = None,
              multi_agent_enabled: bool = False, persist_rollouts: bool = False) -> dict[str, Any]:
    """Run a fresh JSONL Codex session and retain stdout/stderr even on interruption."""
    if not isinstance(multi_agent_enabled, bool) or not isinstance(persist_rollouts, bool) \
            or persist_rollouts and not multi_agent_enabled:
        raise ValueError("delegation and rollout persistence policy is invalid")
    if not command or Path(command[0]).name.lower() not in {"codex", "codex.exe"}:
        raise ValueError("host command must launch Codex CLI directly")
    if "exec" not in command or "--json" not in command \
            or (("--ephemeral" in command) == persist_rollouts) \
            or "--sandbox" not in command \
            or command[command.index("--sandbox") + 1] != "read-only" \
            or "--disable" not in command or "shell_tool" not in command or "unified_exec" not in command \
            or "--cd" not in command or "-c" not in command \
            or command[-1] != "-":
        raise ValueError("host command must enforce a fresh read-only isolated profile with stdin prompt input")
    disabled_values = [command[index + 1] for index, value in enumerate(command[:-1]) if value == "--disable"]
    enabled_values = [command[index + 1] for index, value in enumerate(command[:-1]) if value == "--enable"]
    if multi_agent_enabled:
        if "multi_agent" in disabled_values or enabled_values.count("multi_agent") != 1:
            raise ValueError("host command multi-agent policy does not match trial profile")
    elif disabled_values.count("multi_agent") != 1 or "multi_agent" in enabled_values:
        raise ValueError("host command multi-agent policy does not match trial profile")
    if any("http" in argument.lower() for argument in command):
        raise ValueError("host command must not contain runtime locators or URLs")
    workspace = workspace.resolve(strict=True)
    trial_dir = trial_dir.resolve(strict=True)
    raw_path = trial_dir / "host-events.jsonl"
    timestamps_path = trial_dir / "host-event-times.jsonl"
    stderr_path = trial_dir / "host-stderr.log"
    prompt_path = trial_dir / "invocation-prompt.txt"
    for path in (raw_path, timestamps_path, stderr_path, prompt_path):
        if path.exists():
            raise ValueError("trial evidence files already exist")
    prompt_bytes = prompt.encode("utf-8")
    prompt_path.write_bytes(prompt_bytes)
    os.chmod(prompt_path, 0o600)
    started_at = _utc_now()
    if environ is None or not environ.get("CODEX_HOME"):
        raise ValueError("host invocation requires a task-isolated CODEX_HOME")
    child_env = filtered_environment(dict(environ))
    if not (Path(child_env["CODEX_HOME"]) / "config.toml").is_file():
        raise ValueError("isolated Codex profile is not configured")
    with stderr_path.open("wb") as stderr_file:
        os.chmod(stderr_path, 0o600)
        process = subprocess.Popen(
            command,
            cwd=workspace,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            close_fds=True,
            env=child_env,
        )
        assert process.stdin is not None and process.stdout is not None
        reader_state: dict[str, Any] = {"complete": False, "error": None}
        reader = threading.Thread(
            target=_stream_stdout,
            args=(process.stdout, raw_path, timestamps_path, reader_state),
            daemon=True,
        )
        reader.start()
        try:
            process.stdin.write(prompt_bytes)
            process.stdin.close()
            process.wait(timeout=timeout_seconds)
        except (BrokenPipeError, subprocess.TimeoutExpired, KeyboardInterrupt):
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
        finally:
            reader.join(timeout=10)
            if process.poll() is None:
                process.kill()
                process.wait()
                reader.join(timeout=10)
    raw = raw_path.read_bytes() if raw_path.exists() else b""
    try:
        parsed_events = parse_host_stream(raw)
        capture_valid = True
    except ValueError:
        parsed_events = []
        capture_valid = False
    try:
        version_probe = subprocess.run(
            command[:1] + ["--version"], capture_output=True, text=True,
            check=False, env=child_env, timeout=10,
        )
        host_version = version_probe.stdout.strip()
        version_probe_succeeded = version_probe.returncode == 0
    except (OSError, subprocess.SubprocessError):
        host_version = ""
        version_probe_succeeded = False
    lifecycle_complete = bool(
        parsed_events
        and parsed_events[0].get("type") == "thread.started"
        and parsed_events[-1].get("type") == "turn.completed"
    )
    reader_complete = not reader.is_alive() and reader_state.get("complete") is True
    capture_complete = bool(
        capture_valid and reader_complete and process.returncode == 0 and version_probe_succeeded
    )
    complete = capture_complete and lifecycle_complete
    tool_calls = []
    ledger_error = None
    if capture_complete:
        try:
            tool_calls = mcp_tool_ledger(parsed_events)
        except ValueError as error:
            # Keep the raw capture and thread identity so the trial runner can
            # archive delegated rollouts for diagnosis before marking it blocked.
            complete = False
            ledger_error = str(error)
    result = {
        "host": "codex-cli",
        "host_version": host_version,
        "started_at": started_at,
        "completed_at": _utc_now(),
        "return_code": process.returncode,
        "complete": complete,
        "lifecycle_complete": lifecycle_complete,
        "reader_complete": reader_complete,
        "reader_error": reader_state.get("error"),
        "event_count": len(parsed_events),
        "thread_id": parsed_events[0].get("thread_id") if parsed_events else None,
        "tool_call_count": len(tool_calls),
        "tool_calls": tool_calls,
        "ledger_error": ledger_error,
        "trace_sha256": sha256(raw),
        "prompt_sha256": sha256(prompt_bytes),
        "raw_trace_path": raw_path.name,
        "timestamps_path": timestamps_path.name,
        "stderr_path": stderr_path.name,
    }
    metadata_path = trial_dir / "invocation-capture.json"
    metadata_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.chmod(metadata_path, 0o600)
    return result


def capture_delegation_rollouts(profile_home: Path, parent_thread_id: str | None,
                                trial_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "codex-delegation-rollouts/v1",
        "status": "incomplete",
        "parent_thread_id": parent_thread_id,
        "children": [],
    }
    try:
        if not isinstance(parent_thread_id, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,128}", parent_thread_id):
            raise ValueError
        sessions = profile_home / "sessions"
        candidates = [path for path in sessions.rglob("rollout-*.jsonl")
                      if path.stem == f"rollout-{parent_thread_id}"
                      or path.stem.endswith(f"-{parent_thread_id}")] if sessions.is_dir() else []
        if len(candidates) != 1:
            raise ValueError
        parent_path = candidates[0]
        if parent_path.is_symlink() or profile_home.resolve(strict=True) not in parent_path.resolve(strict=True).parents:
            raise ValueError
        parent_events = _read_rollout(parent_path)
        child_ids = _subagent_thread_ids(parent_events)
        if not child_ids:
            raise ValueError
        child_paths: dict[str, Path] = {}
        for child_id in sorted(child_ids):
            if child_id == parent_thread_id:
                raise ValueError
            matches = [path for path in sessions.rglob("rollout-*.jsonl")
                       if path.stem == f"rollout-{child_id}"
                       or path.stem.endswith(f"-{child_id}")]
            if len(matches) != 1:
                raise ValueError
            if matches[0].is_symlink() or profile_home.resolve(strict=True) not in matches[0].resolve(strict=True).parents:
                raise ValueError
            child_paths[child_id] = matches[0]
            _read_rollout(matches[0])
        evidence = trial_dir / "delegation-rollouts"
        evidence.mkdir(mode=0o700)
        os.chmod(evidence, 0o700)
        copied: list[dict[str, str]] = []
        for name, source, thread_id in [("parent.jsonl", parent_path, parent_thread_id),
                                        *[(f"child-{thread_id}.jsonl", path, thread_id)
                                          for thread_id, path in child_paths.items()]]:
            raw = source.read_bytes()
            if not raw.endswith(b"\n"):
                raise ValueError
            destination = evidence / name
            destination.write_bytes(raw)
            os.chmod(destination, 0o600)
            copied.append({"file": f"delegation-rollouts/{name}", "thread_id": thread_id,
                           "sha256": sha256(raw)})
        result.update({"status": "captured", "parent_file": copied[0]["file"],
                       "parent_sha256": copied[0]["sha256"], "children": copied[1:]})
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        result["status"] = "incomplete"
    metadata = trial_dir / "delegation-rollouts.json"
    metadata.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.chmod(metadata, 0o600)
    return result


def _read_rollout(path: Path, expected_sha256: str | None = None) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("rollout path is invalid")
    raw = path.read_bytes()
    if expected_sha256 is not None and sha256(raw) != expected_sha256:
        raise ValueError("rollout digest mismatch")
    return parse_host_stream(raw)


def _subagent_thread_ids(events: list[dict[str, Any]]) -> set[str]:
    found: set[str] = set()
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        item = payload.get("item")
        if isinstance(item, dict) and item.get("type") == "SubAgentActivity":
            child_id = item.get("agent_thread_id") or item.get("child_thread_id")
            if not isinstance(child_id, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,128}", child_id):
                raise ValueError("subagent rollout has no valid child thread identity")
            found.add(child_id)
    return found
