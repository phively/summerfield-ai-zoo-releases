#!/usr/bin/env python3
"""Run a fresh, isolated Codex invocation of a staged shopping skill profile."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

import capture_invocation as capture
import private_evidence
import store as fixture_store


EVAL_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = EVAL_ROOT.parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[1]
MANIFEST_PATH = EVAL_ROOT / "manifest.json"


def _write_private(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    os.chmod(path, 0o600)


def _private_trial_dir(path: Path) -> Path:
    path = path.expanduser().absolute()
    resolved_path = path.resolve()
    repo_root = REPO_ROOT.resolve()
    if repo_root in resolved_path.parents or resolved_path == repo_root:
        try:
            result = subprocess.run(
                ["git", "check-ignore", "--quiet", str(resolved_path)], cwd=REPO_ROOT,
                check=False, capture_output=True,
            )
        except OSError as error:
            raise ValueError("cannot verify private trial artifact directory") from error
        if result.returncode != 0:
            raise ValueError("trial artifacts inside the repository must be git-ignored")
    if path.exists():
        raise ValueError("trial artifact directory must be new")
    return private_evidence.ensure_private_directory(path, require_new=True)


def _provider_roots(manifest: dict, profile_id: str, codex_home: Path) -> tuple[dict[str, Path], dict[str, dict]]:
    profiles = manifest["candidate"]["profiles"]
    packages = manifest["candidate"]["packages"]
    roots: dict[str, Path] = {}
    installed: dict[str, dict] = {}
    for package_name in profiles[profile_id]["packages"]:
        package = packages[package_name]
        selector = package.get("runtime_plugin_id")
        if selector:
            root, details = capture.resolve_installed_plugin_root(selector, codex_home=codex_home)
            roots[package_name] = root
            installed[package_name] = {
                "plugin_id": selector,
                "name": details["name"],
                "version": details["version"],
                "marketplace": details["marketplaceName"],
                "files": capture.hash_identity(root, package["files"]),
            }
    return roots, installed


def _profile_command(command: list[str], workspace: Path, environment: dict[str, str],
                     timeout_seconds: int = 90) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=workspace, env=environment, capture_output=True,
                          text=True, timeout=timeout_seconds, check=False)


def _global_plugin_inventory(executable: str) -> list[dict]:
    environment = capture.filtered_environment(dict(os.environ))
    result = subprocess.run([executable, "plugin", "list", "--json"], cwd=REPO_ROOT,
                            env=environment, capture_output=True, text=True,
                            check=False, timeout=60)
    if result.returncode != 0:
        raise ValueError("global plugin inventory is unavailable for isolation")
    try:
        plugins = json.loads(result.stdout).get("installed", [])
    except json.JSONDecodeError as error:
        raise ValueError("global plugin inventory is invalid") from error
    return [item for item in plugins if isinstance(item, dict) and item.get("installed") is True]


def _suppress_other_plugins(profile_home: Path, package_names: list[str],
                            global_plugins: list[dict]) -> list[str]:
    selected_ids = {f"{name}@{capture.MARKETPLACE_NAME}" for name in package_names}
    config_path = profile_home / "config.toml"
    config_text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    existing_ids = set(re.findall(r'^\[plugins\."([^\"]+)"\]', config_text, re.M))
    suppressed = []
    lines = []
    for plugin in global_plugins:
        plugin_id = plugin.get("pluginId")
        if not isinstance(plugin_id, str) or plugin_id in selected_ids or plugin_id in existing_ids:
            continue
        lines.extend((f"[plugins.{json.dumps(plugin_id)}]", "enabled = false", ""))
        suppressed.append(plugin_id)
    if lines:
        with config_path.open("a", encoding="utf-8") as config_file:
            config_file.write("\n" + "\n".join(lines))
        os.chmod(config_path, 0o600)
    return suppressed


def _installed_plugins(profile_home: Path, workspace: Path, environment: dict[str, str],
                       package_names: list[str], output_dir: Path,
                       global_plugins: list[dict],
                       executable: str = "codex") -> tuple[dict[str, Path], dict[str, dict], list[str]]:
    setup_log = output_dir / "isolated-profile-setup.log"
    commands = [[executable, "plugin", "marketplace", "add", str(workspace), "--json"]]
    commands.extend([executable, "plugin", "add", name, "--marketplace", capture.MARKETPLACE_NAME, "--json"]
                    for name in package_names)
    with setup_log.open("wb") as log:
        os.chmod(setup_log, 0o600)
        for command in commands:
            completed = _profile_command(command, workspace, environment)
            log.write(json.dumps({"command": command[1:4], "return_code": completed.returncode}).encode() + b"\n")
            log.write(completed.stdout.encode(errors="replace"))
            log.write(completed.stderr.encode(errors="replace"))
            log.flush()
            if completed.returncode != 0:
                raise ValueError("isolated local marketplace installation failed")
    suppressed = _suppress_other_plugins(profile_home, package_names, global_plugins)
    inventory_result = _profile_command([executable, "plugin", "list", "--json"], workspace, environment)
    if inventory_result.returncode != 0:
        raise ValueError("isolated plugin inventory is unavailable")
    try:
        inventory = json.loads(inventory_result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("isolated plugin inventory is invalid") from error
    selected = {item.get("name"): item for item in inventory.get("installed", [])
                if isinstance(item, dict) and item.get("installed") is True
                and item.get("marketplaceName") == capture.MARKETPLACE_NAME
                and item.get("enabled") is True}
    if set(selected) != set(package_names):
        raise ValueError("isolated Codex profile exposed an unexpected installed plugin set: "
                         + ", ".join(sorted(selected)))
    roots: dict[str, Path] = {}
    details: dict[str, dict] = {}
    for name in package_names:
        item = selected[name]
        cache_root = profile_home / "plugins" / "cache" / capture.MARKETPLACE_NAME / name / str(item["version"])
        if not cache_root.is_dir():
            raise ValueError("isolated installed plugin bytes are unavailable")
        roots[name] = cache_root.resolve(strict=True)
        details[name] = {"plugin_id": item["pluginId"], "version": item["version"]}
    return roots, details, suppressed


def _installed_identity(roots: dict[str, Path], manifest: dict) -> dict[str, str]:
    packages = manifest["candidate"]["packages"]
    identity: dict[str, str] = {}
    for name, root in sorted(roots.items()):
        files = capture.hash_identity(root, packages[name]["files"])
        for relative, digest in files.items():
            identity[f"{name}/{relative}"] = digest
    return identity


def _discover_candidate_skills(skill_id: str, workspace: Path, environment: dict[str, str],
                               roots: dict[str, Path], package_details: dict[str, dict],
                               executable: str, required_skill_ids: list[str] | None = None) -> dict:
    prompt = f"Use ${skill_id}."
    try:
        completed = subprocess.run(
            [executable, "debug", "prompt-input", prompt], cwd=workspace,
            env=capture.filtered_environment(environment), capture_output=True, text=True,
            timeout=60, check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("Codex skill discovery preflight could not run") from error
    if completed.returncode != 0:
        raise ValueError("Codex skill discovery preflight failed")
    try:
        prompt_input = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("Codex skill discovery output is invalid") from error
    discovery = capture.verify_skill_discovery(
        prompt_input, roots, package_details,
        required_skill_ids=required_skill_ids or [skill_id],
    )
    if skill_id not in discovery["candidate_skills"]:
        raise ValueError("requested candidate skill is not discoverable in the isolated profile")
    return discovery


def _identity_digest(files: dict[str, str]) -> str:
    import hashlib
    digest = hashlib.sha256()
    for relative, content_hash in sorted(files.items()):
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(bytes.fromhex(content_hash))
    return digest.hexdigest()


def _make_isolated_home() -> Path:
    profile_home = Path(tempfile.mkdtemp(prefix="personal-shopper-codex-home-")).resolve()
    os.chmod(profile_home, 0o700)
    config_path = profile_home / "config.toml"
    config_path.write_text("approval_policy = \"never\"\nsandbox_mode = \"read-only\"\n", encoding="utf-8")
    os.chmod(config_path, 0o600)
    return profile_home


def _link_existing_cli_auth(profile_home: Path, source_home: Path) -> None:
    source = source_home / "auth.json"
    if not private_evidence.private_file(source):
        raise ValueError("a private existing CLI auth cache is required")
    (profile_home / "auth.json").symlink_to(source.resolve(strict=True))
    with (profile_home / "config.toml").open("a", encoding="utf-8") as config:
        config.write('cli_auth_credentials_store = "file"\n')


def _register_fixture_server(profile_home: Path, fixture_root: Path) -> dict[str, str]:
    """Register only the local synthetic MCP server in a fresh private CLI profile."""
    config_path = profile_home / "config.toml"
    config = config_path.read_text(encoding="utf-8")
    if "[mcp_servers" in config:
        raise ValueError("isolated Codex profile already contains MCP servers")
    command = sys.executable
    args = [str(EVAL_ROOT / "store.py"), "serve", str(fixture_root.resolve(strict=True))]
    encoded_args = ", ".join(capture._toml_string(value) for value in args)
    with config_path.open("a", encoding="utf-8") as stream:
        stream.write(
            "\n[mcp_servers.\"shopping-fixture\"]\n"
            f"command = {capture._toml_string(command)}\n"
            f"args = [{encoded_args}]\n"
            "startup_timeout_sec = 20\n"
            "tool_timeout_sec = 60\n"
            "default_tools_approval_mode = \"approve\"\n"
        )
    os.chmod(config_path, 0o600)
    return {"name": "shopping-fixture", "tool_count_source": "subcase allowlist"}


def _validate_delegation_profile(profile_id: str, profile_spec: dict, subcase: dict | None) -> None:
    multi_agent = profile_spec.get("multi_agent", False)
    persist_rollouts = profile_spec.get("persist_rollouts", False)
    is_new_plan = isinstance(subcase, dict) and subcase.get("id") == "B10-AE12-new-plan"
    if (multi_agent or persist_rollouts) and (profile_id != "full-handoff-delegating" or not is_new_plan):
        raise ValueError("delegation capture is limited to B10-AE12-new-plan")
    if is_new_plan and (multi_agent is not True or persist_rollouts is not True):
        raise ValueError("B10-AE12-new-plan requires persisted restricted delegation capture")


def _register_skill_resource_reader(profile_home: Path, control_path: Path) -> None:
    args = [str(EVAL_ROOT / "skill_resources.py"), str(control_path)]
    with (profile_home / "config.toml").open("a", encoding="utf-8") as stream:
        stream.write('\n[mcp_servers."shopping-skill-resources"]\n'
                     f"command = {capture._toml_string(sys.executable)}\n"
                     f"args = {json.dumps(args)}\n"
                     'startup_timeout_sec = 20\ntool_timeout_sec = 20\n')


def _register_skill_reader(profile_home: Path, installed_root: Path, identity: dict,
                           output_dir: Path) -> dict:
    prefix = "personal-shopper/skills/personal-shopper/"
    control = {"installed_skill_root": str(installed_root / "skills/personal-shopper"),
               "files": {key[len(prefix):]: digest for key, digest in identity.items()
                         if key.startswith(prefix) and key.endswith(".md")}}
    control_path = output_dir / "skill-resource-config.json"
    _write_private(control_path, json.dumps(control).encode() + b"\n")
    _register_skill_resource_reader(profile_home, control_path)
    return {"server": "shopping-skill-resources", "tool": "read_installed_skill_file",
            "files": control["files"]}


def _register_integration_reader(profile_home: Path, installed_roots: dict[str, Path],
                                 identity: dict, output_dir: Path,
                                 required_resources: list[str], *,
                                 include_package_references: bool = False) -> dict:
    packages = {}
    if not isinstance(required_resources, list) or not required_resources \
            or any(not isinstance(path, str) or path.count("/") < 2 for path in required_resources) \
            or len(required_resources) != len(set(required_resources)):
        raise ValueError("required installed skill resource list is invalid")
    resources = set(required_resources)
    if include_package_references:
        names = {path.split("/", 1)[0] for path in required_resources}
        resources.update(path for path in identity if path.endswith(".md")
                         and any(path.startswith(f"{name}/skills/") for name in names))
    for qualified_path in sorted(resources):
        name, relative = qualified_path.split("/", 1)
        root = installed_roots.get(name)
        digest = identity.get(qualified_path)
        if root is None or not relative.endswith(".md") or not isinstance(digest, str):
            raise ValueError("required installed skill resource is not part of the profile")
        packages.setdefault(name, {"installed_root": str(root), "files": {}})["files"][relative] = digest
    control_path = output_dir / "skill-resource-config.json"
    _write_private(control_path, json.dumps({"packages": packages}).encode() + b"\n")
    _register_skill_resource_reader(profile_home, control_path)
    return {"server": "shopping-skill-resources", "tool": "read_installed_skill_file",
            "packages": {name: package["files"] for name, package in packages.items()},
            "config_sha256": capture.sha256(control_path.read_bytes())}


def run_trial(profile_id: str, task_file: Path | None, output_dir: Path, *, subcase_id: str | None = None,
              timeout_seconds: int = 900, executable: str = "codex",
              use_existing_cli_auth: bool = False) -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    profiles = manifest["candidate"]["profiles"]
    if profile_id not in profiles:
        raise ValueError("unknown shopping trial profile")
    profile_spec = profiles[profile_id]
    provider_app_policies = manifest["candidate"].get("provider_apps", {}).get(profile_id, [])
    if use_existing_cli_auth and provider_app_policies:
        raise ValueError("existing CLI auth cannot be used with provider apps")
    multi_agent_enabled = profile_spec.get("multi_agent", False)
    persist_rollouts = profile_spec.get("persist_rollouts", False)
    if not isinstance(multi_agent_enabled, bool) or not isinstance(persist_rollouts, bool) \
            or persist_rollouts and (not multi_agent_enabled or profile_id != "full-handoff-delegating"):
        raise ValueError("trial profile delegation capture policy is invalid")
    activation_skill = profile_spec.get("activation_skill", manifest["candidate"]["skill"])
    subcase = None
    if subcase_id:
        if task_file is not None:
            raise ValueError("provide either a fixture subcase or a private task file")
        subcase = next((item for item in manifest.get("synthetic_subcases", [])
                        if item.get("id") == subcase_id), None)
        if not isinstance(subcase, dict) or subcase.get("profile") != profile_id:
            raise ValueError("unknown fixture subcase or mismatched isolated profile")
        additional_skills = subcase.get("additional_skills", [])
        if not isinstance(additional_skills, list) or any(not isinstance(skill, str) for skill in additional_skills) \
                or len(additional_skills) != len(set(additional_skills)):
            raise ValueError("trial additional skill identities are invalid")
        task = fixture_store.render_task(
            subcase["fixture_id"], context_keys=subcase.get("context_keys"),
            request_override=subcase.get("task"),
        )
    else:
        additional_skills = []
        if task_file is None:
            raise ValueError("a private task file or fixture subcase is required")
        if task_file.is_symlink():
            raise ValueError("task input must not be a symlink")
        task_file = task_file.resolve(strict=True)
        task = task_file.read_text(encoding="utf-8")
    _validate_delegation_profile(profile_id, profile_spec, subcase)
    if not task.strip():
        raise ValueError("task input must not be empty")

    candidate_patterns = capture.candidate_identity_patterns(manifest)
    candidate_before = capture.identity_digest(REPO_ROOT, candidate_patterns)
    suite_before = capture.identity_digest(REPO_ROOT, manifest["suite_identity_files"])

    output_dir = _private_trial_dir(output_dir)
    fixture_root = None
    fixture_before_hash = None
    fixture_runtime = None
    if subcase:
        fixture_root = output_dir / "fixture-store"
        fixture_store.initialize(
            fixture_root, subcase["fixture_id"], subcase["tools"], faults=subcase.get("faults", {})
        )
        fixture_before_hash = fixture_store._json_hash(fixture_store._read(fixture_root / "state.json"))
        fixture_runtime = {
            "case_id": subcase["fixture_id"],
            "subcase_id": subcase["id"],
            "allowed_tools": subcase["tools"],
            "permitted_operations": subcase["permitted_operations"],
        }
    source_codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()
    package_roots, external_packages = _provider_roots(manifest, profile_id, source_codex_home)
    global_plugins = _global_plugin_inventory(executable)
    workspace = Path(tempfile.mkdtemp(prefix=f"personal-shopper-{profile_id}-")).resolve()
    profile_home = _make_isolated_home()
    try:
        if use_existing_cli_auth:
            _link_existing_cli_auth(profile_home, source_codex_home)
        os.chmod(workspace, 0o700)
        profile = capture.stage_profile(REPO_ROOT, workspace, manifest, profile_id,
                                        package_roots=package_roots)
        runtime_config = (workspace / ".codex" / "config.toml").read_bytes()
        _write_private(output_dir / "runtime-config.toml", runtime_config)
        child_env = capture.filtered_environment(dict(os.environ))
        child_env["CODEX_HOME"] = str(profile_home)
        package_names = list(profile["packages"])
        installed_roots, installed_details, suppressed_plugins = _installed_plugins(
            profile_home, workspace, child_env, package_names, output_dir,
            global_plugins, executable=executable
        )
        if fixture_root is not None:
            fixture_runtime.update(_register_fixture_server(profile_home, fixture_root))
        staged_identity = {
            f"{name}/{relative.removeprefix(f'plugins/{name}/')}": digest
            for relative, digest in profile["files"].items() for name in package_names
            if relative.startswith(f"plugins/{name}/")
        }
        installed_before = _installed_identity(installed_roots, manifest)
        if staged_identity != installed_before:
            raise ValueError("isolated plugin cache differs from the frozen candidate packages")
        skill_reader = None
        if profile_id == "native-sheets-preservation":
            skill_reader = _register_skill_reader(
                profile_home, installed_roots["personal-shopper"], installed_before, output_dir)
        elif subcase and (subcase.get("required_skill_resources") or profile_id == "shopper-alone"):
            required = subcase.get("required_skill_resources") or [
                "personal-shopper/skills/personal-shopper/SKILL.md"]
            skill_reader = _register_integration_reader(
                profile_home, installed_roots, installed_before, output_dir, required,
                include_package_references=profile_id == "shopper-alone")
            available = {f"{name}/{path}" for name, files in skill_reader["packages"].items() for path in files}
            if not set(required) <= available:
                raise ValueError("required installed skill resources are not available")
        codex_home_config_hash = None
        if persist_rollouts:
            codex_home_config = (profile_home / "config.toml").read_bytes()
            _write_private(output_dir / "isolated-codex-home-config.toml", codex_home_config)
            codex_home_config_hash = capture.sha256(codex_home_config)
        profile_before = _identity_digest(installed_before)
        discovery = _discover_candidate_skills(
            activation_skill, workspace, child_env,
            installed_roots, installed_details, executable,
            required_skill_ids=[activation_skill, *additional_skills],
        )
        if set(additional_skills) - set(discovery["candidate_skills"]):
            raise ValueError("additional trial skill is not discoverable in the isolated profile")
        prompt = capture.build_activation_prompt(activation_skill, task, additional_skills)
        if skill_reader and "packages" in skill_reader:
            prompt += ("\nUse shopping-skill-resources.read_installed_skill_file to read the installed "
                       "skill instructions and linked handoff contracts for the applicable packages. "
                       "Pass the package name and package-relative path. This reader has no provider access. "
                       "Use these exact argument pairs for the required resources: "
                       + json.dumps([{"package": path.split("/", 1)[0],
                                      "relative_path": path.split("/", 1)[1]} for path in required]) + ".\n")
        elif skill_reader:
            prompt += ("\nThe selected candidate is installed in this CLI profile. Load its SKILL.md "
                       "and required linked references using shopping-skill-resources.read_installed_skill_file. "
                       "Use this installed package, not another remotely installed version. "
                       "The resource tool reads the actual installed files and has no provider access.\n")
        if subcase and subcase["id"] == "B10-AE12-new-plan":
            prompt += (
                "Before delegating, read the caller's installed Meal Planner skill and grocery integration contract. "
                "Construct the complete grocery-handoff/v1 request packet from the approved context, including the "
                "finalized recipe packet and exact versions, proposed plan identity, workbook identity, answered "
                "shopping facts, consent, authorization and unresolved questions. Use these exact top-level packet "
                "keys: protocol, request_id, recipe_ids, recipe_versions, plan_identity, workbook_identity, "
                "recipe_packet, approval, confirmed_pantry, region, currency, shopping_date, budget, preferred_stores, "
                "check_pantry, required_constraints, shopping_record_write_authorization, unresolved_questions. "
                "Emit that packet as one assistant "
                "message immediately before spawning the independently installed Personal Shopper child. The child "
                "must read each listed installed Personal Shopper resource for its role through the allowlisted "
                "resource reader before workbook work. These include its grocery workflow, receiver, record, "
                "store-preference, and pricing instructions. The child may use only the synthetic fixture's "
                "read-only get_spreadsheet_metadata and get_spreadsheet_range tools when needed, and must use the "
                "exact supplied synthetic workbook identity. The child must not call any other fixture tool, write "
                "the grocery workbook, record the grocery result, or save/read meal plans. Return the child's exact "
                "terminal JSON result unchanged as the top-level returned_grocery_result object; do not wrap or "
                "rewrite its v1 fields. Only the parent may check plan IDs, "
                "record the returned grocery result, and save/read back the plan after that return.\n"
            )
        command = capture.build_codex_command(
            workspace, executable=executable, apps_enabled=bool(profile["provider_apps"]),
            multi_agent_enabled=multi_agent_enabled, persist_rollouts=persist_rollouts,
        )
        capture_started = capture._utc_now()
        result = capture.run_codex(
            command, workspace, output_dir, prompt, timeout_seconds=timeout_seconds, environ=child_env,
            multi_agent_enabled=multi_agent_enabled, persist_rollouts=persist_rollouts,
        )
        if persist_rollouts:
            result["delegation_rollouts"] = capture.capture_delegation_rollouts(
                profile_home, result.get("thread_id"), output_dir)
        if fixture_root is not None:
            final_fixture_state = fixture_store.snapshot(fixture_root)
            fixture_after_hash = fixture_store._json_hash(final_fixture_state)
            fixture_events = [line for line in (fixture_root / "events.jsonl").read_text().splitlines() if line]
            fixture_runtime.update({
                "event_count": len(fixture_events),
                "state_sha256_before": fixture_before_hash,
                "state_sha256_after": fixture_after_hash,
                "state_changed": fixture_before_hash != fixture_after_hash,
            })
            result["fixture"] = fixture_runtime
        installed_after = _installed_identity(installed_roots, manifest)
        profile_after = _identity_digest(installed_after)
        candidate_after = capture.identity_digest(REPO_ROOT, candidate_patterns)
        suite_after = capture.identity_digest(REPO_ROOT, manifest["suite_identity_files"])
        result["source_candidate_sha256_before"] = candidate_before
        result["source_candidate_sha256_after"] = candidate_after
        result["source_candidate_unchanged"] = candidate_before == candidate_after
        result["candidate_profile_sha256_before"] = profile_before
        result["candidate_profile_sha256_after"] = profile_after
        result["candidate_profile_unchanged"] = profile_before == profile_after
        result["candidate_profile_sha256"] = profile_before
        result["suite_sha256_before"] = suite_before
        result["suite_sha256_after"] = suite_after
        result["suite_identity_unchanged"] = suite_before == suite_after
        result["profile_id"] = profile_id
        result["candidate_packages"] = profile["packages"]
        result["installed_plugins"] = installed_details
        result["skill_discovery"] = discovery
        result["suppressed_global_plugins"] = suppressed_plugins
        result["installed_file_sha256"] = installed_before
        result["external_packages"] = external_packages
        result["runtime_workspace"] = str(workspace)
        result["capture_started_at"] = capture_started
        result["source_candidate_sha256"] = candidate_before
        result["run_id"] = output_dir.name or uuid.uuid4().hex
        result["skill_id"] = activation_skill
        result["candidate_skill_id"] = manifest["candidate"]["skill"]
        result["requested_skill_ids"] = [activation_skill, *additional_skills]
        result["activation_prompt_hash"] = capture.sha256(prompt.encode("utf-8"))
        if persist_rollouts:
            result["isolated_codex_home_config_sha256"] = codex_home_config_hash
        result["trial_status"] = "captured" if result["complete"] \
            and result["source_candidate_unchanged"] and result["candidate_profile_unchanged"] \
            and result["suite_identity_unchanged"] else "blocked"
        _write_private(output_dir / "runtime-profile.json", json.dumps(profile, indent=2).encode() + b"\n")
        _write_private(output_dir / "runtime-settings.json", json.dumps({
            "host_version": result["host_version"],
            "profile_id": profile_id,
            "candidate_profile_sha256": profile_before,
            "candidate_profile_unchanged": result["candidate_profile_unchanged"],
            "source_candidate_sha256": candidate_before,
            "source_candidate_unchanged": result["source_candidate_unchanged"],
            "suite_sha256": suite_before,
            "suite_identity_unchanged": result["suite_identity_unchanged"],
            "command": command,
            "child_environment_names": sorted(child_env),
            "sandbox": "read-only",
            "fresh_session": True,
            "isolated_codex_home": True,
            "existing_cli_auth_link": use_existing_cli_auth,
            "global_user_profile_unchanged": True,
            "provider_apps": profile["provider_apps"],
            "multi_agent_enabled": multi_agent_enabled,
            "persist_rollouts": persist_rollouts,
            "runtime_config_sha256": profile["config_sha256"],
            "isolated_codex_home_config_sha256": codex_home_config_hash,
            "installed_plugins": installed_details,
            "skill_discovery": discovery,
            "skill_resource_reader": skill_reader,
            "fixture": fixture_runtime,
            "suppressed_global_plugins": suppressed_plugins,
            "external_packages": external_packages,
            "capture_started_at": capture_started,
            "capture_completed_at": capture._utc_now(),
        }, indent=2).encode() + b"\n")
        _write_private(output_dir / "trial-result.json", json.dumps(result, indent=2).encode() + b"\n")
        return result
    except Exception as error:
        _write_private(output_dir / "blocked-reason.json", json.dumps({
            "error_type": type(error).__name__,
            "error": str(error),
            "observed_at": capture._utc_now(),
        }, indent=2).encode() + b"\n")
        raise
    finally:
        shutil.rmtree(profile_home, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, choices=sorted(json.loads(MANIFEST_PATH.read_text())["candidate"]["profiles"]))
    task_source = parser.add_mutually_exclusive_group(required=True)
    task_source.add_argument("--task-file", type=Path, help="private task input, never passed in argv to Codex")
    task_source.add_argument("--subcase", choices=sorted(
        item["id"] for item in json.loads(MANIFEST_PATH.read_text()).get("synthetic_subcases", [])
    ), help="run one controller-selected synthetic acceptance subcase")
    parser.add_argument("--output-dir", required=True, type=Path, help="new private evidence directory")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--codex", default=shutil.which("codex") or "codex")
    parser.add_argument("--use-existing-cli-auth", action="store_true",
                        help="link the private existing CLI auth cache for profiles without provider apps; never copy it to evidence")
    args = parser.parse_args(argv)
    try:
        result = run_trial(args.profile, args.task_file, args.output_dir, subcase_id=args.subcase,
                           timeout_seconds=args.timeout_seconds, executable=args.codex,
                           use_existing_cli_auth=args.use_existing_cli_auth)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        message = re.sub(r"https?://\S+", "[private-url]", str(error), flags=re.I)
        message = re.sub(r"(?i)(?:native_id|spreadsheet_id|file_id)[^\s]{0,12}[A-Za-z0-9_-]{40,}",
                         "[private-resource]", message)
        print(json.dumps({"status": "blocked", "error_type": type(error).__name__, "error": message}))
        return 2
    print(json.dumps({
        "status": result["trial_status"],
        "profile": result["profile_id"],
        "host_version": result["host_version"],
        "complete": result["complete"],
        "event_count": result["event_count"],
        "tool_call_count": result["tool_call_count"],
        "candidate_profile_unchanged": result["candidate_profile_unchanged"],
        "evidence_dir": str(args.output_dir.resolve()),
    }, sort_keys=True))
    return 0 if result["trial_status"] == "captured" else 2


if __name__ == "__main__":
    sys.exit(main())
