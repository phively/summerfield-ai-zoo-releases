#!/usr/bin/env python3
"""Run a small, provenance-preserving comparison of instruction candidates.

The caller supplies the requested and actual runtime configuration. The script
does not contain a provider-specific invocation and does not claim Cloud support
for its local command adapter.
"""

from __future__ import annotations

import argparse
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any
import uuid


STATUSES = {"passed", "failed", "blocked", "not_run"}
MAX_CONCURRENCY = 32
MAX_PREVIEW = 20_000
MAX_ARTIFACT_FILES = 100
MAX_ARTIFACT_BYTES = 10_000_000
DEFAULT_COMMAND_OUTPUT_LIMIT_BYTES = 10_000_000
MAX_COMMAND_OUTPUT_LIMIT_BYTES = 50_000_000
PROCESS_TERMINATION_GRACE_SECONDS = 2.0
PROCESS_CONTROLLER_VERSION = "1.3.0"
ADAPTER_SCHEMA_VERSION = "1.4.1"
REPORT_SCHEMA_VERSION = "1.2.0"
EXIT_ACCEPTED = 0
EXIT_REJECTED = 1
EXIT_INVALID = 2
EXIT_INCOMPLETE = 3


class ConfigurationError(ValueError):
    """Raised when supplied comparison inputs cannot safely be used."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def hash_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def exact_bytes(path: Path) -> bytes:
    return path.read_bytes()


def is_link(path: Path) -> bool:
    junction_check = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(junction_check and junction_check())


def reject_links(path: Path) -> None:
    if is_link(path):
        raise ConfigurationError(f"input path must not be a symbolic link or junction: {path}")
    if path.is_dir():
        for child in path.rglob("*"):
            if is_link(child):
                raise ConfigurationError(f"input tree contains a symbolic link or junction: {child}")


def content_hash(path: Path) -> str:
    reject_links(path)
    if path.is_file():
        return hash_bytes(exact_bytes(path))
    if not path.is_dir():
        raise ConfigurationError(f"candidate path does not exist: {path}")
    entries = []
    for child in sorted(path.rglob("*")):
        if child.is_file():
            entries.append({"path": child.relative_to(path).as_posix(), "hash": hash_bytes(exact_bytes(child))})
    return hash_bytes(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hash_bytes(encoded.encode("utf-8"))


def reject_nonfinite_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant is not supported: {value}")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_nonfinite_json_constant)
    except (OSError, ValueError) as exc:
        raise ConfigurationError(f"cannot read JSON input {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"JSON input must be an object: {path}")
    return value


def require(mapping: dict[str, Any], key: str, label: str) -> Any:
    if key not in mapping:
        raise ConfigurationError(f"{label} is missing required field {key!r}")
    return mapping[key]


def require_nonempty_string(mapping: dict[str, Any], key: str, label: str) -> str:
    value = require(mapping, key, label)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{label}.{key} must be a non-empty string")
    return value


def load_suite(path: Path) -> tuple[dict[str, Any], str, dict[str, dict[str, Any]]]:
    suite = read_json(path)
    for key in ("suite_id", "suite_version", "rubric_id", "rubric_version"):
        require_nonempty_string(suite, key, "suite")
    cases = require(suite, "cases", "suite")
    if not isinstance(cases, list) or not cases:
        raise ConfigurationError("suite.cases must be a non-empty list")
    indexed: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ConfigurationError("every suite case must be an object")
        case_id = require_nonempty_string(case, "id", "suite case")
        if case_id in indexed:
            raise ConfigurationError(f"duplicate suite case id: {case_id}")
        checks = case.get("checks")
        if not isinstance(checks, list) or not checks:
            raise ConfigurationError(f"suite case {case_id} must declare non-empty checks")
        for check in checks:
            if not isinstance(check, dict) or check.get("type") not in {"contains", "not_contains"} or not isinstance(check.get("value"), str):
                raise ConfigurationError(f"suite case {case_id} contains an unsupported check")
        for flag in ("required", "critical"):
            if flag in case and not isinstance(case[flag], bool):
                raise ConfigurationError(f"suite case {case_id}.{flag} must be boolean")
        indexed[case_id] = case
    red_green = suite.get("red_green", [])
    if not isinstance(red_green, list):
        raise ConfigurationError("suite.red_green must be a list")
    for pair in red_green:
        if not isinstance(pair, dict):
            raise ConfigurationError("every suite.red_green entry must be an object")
        require_nonempty_string(pair, "criterion_id", "red_green entry")
        require_nonempty_string(pair, "red_candidate_id", "red_green entry")
        require_nonempty_string(pair, "green_candidate_id", "red_green entry")
        pair_cases = pair.get("case_ids")
        if not isinstance(pair_cases, list) or not pair_cases or not set(pair_cases).issubset(indexed):
            raise ConfigurationError("red_green entry case_ids must name suite cases")
    return suite, content_hash(path), indexed


def validate_partition(plan: dict[str, Any], development_case_ids: set[str]) -> dict[str, Any]:
    plan_id = require_nonempty_string(plan, "plan_id", "partition plan")
    scope = require_nonempty_string(plan, "scope", "partition plan")
    scheme = require_nonempty_string(plan, "scheme", "partition plan")
    if scheme != "grouped_development_evaluation":
        raise ConfigurationError("partition plan.scheme must be grouped_development_evaluation")
    grouping_key = require_nonempty_string(plan, "grouping_key", "partition plan")
    assignment = require(plan, "assignment", "partition plan")
    if not isinstance(assignment, dict):
        raise ConfigurationError("partition plan.assignment must be an object")
    for key in ("algorithm", "version"):
        require_nonempty_string(assignment, key, "partition plan.assignment")
    stable_inputs = assignment.get("stable_inputs")
    if stable_inputs is None or (isinstance(stable_inputs, str) and not stable_inputs.strip()) or (isinstance(stable_inputs, (list, dict)) and not stable_inputs):
        raise ConfigurationError("partition plan.assignment.stable_inputs is required")
    if isinstance(stable_inputs, list) and (not all(isinstance(item, str) and item.strip() for item in stable_inputs) or len(stable_inputs) != len(set(stable_inputs))):
        raise ConfigurationError("partition plan.assignment.stable_inputs must contain unique non-empty strings")
    if not isinstance(stable_inputs, (str, list, dict)):
        raise ConfigurationError("partition plan.assignment.stable_inputs must be a string, list, or object")
    requested_fold_count = plan.get("requested_fold_count")
    if requested_fold_count not in {3, 5, 10}:
        raise ConfigurationError("partition plan.requested_fold_count must be 3, 5, or 10")
    requested_holdout_percent = plan.get("requested_holdout_percent")
    if not isinstance(requested_holdout_percent, (int, float)) or isinstance(requested_holdout_percent, bool) or not 0 <= requested_holdout_percent <= 100:
        raise ConfigurationError("partition plan.requested_holdout_percent must be between 0 and 100")
    rounding_rule = require_nonempty_string(plan, "rounding_rule", "partition plan")
    if rounding_rule != "round_half_up":
        raise ConfigurationError("partition plan.rounding_rule must be round_half_up")
    coverage = require(plan, "coverage", "partition plan")
    if not isinstance(coverage, dict):
        raise ConfigurationError("partition plan.coverage must be an object")
    coverage_status = require_nonempty_string(coverage, "status", "partition plan.coverage")
    if coverage_status not in {"sufficient", "insufficient_coverage"}:
        raise ConfigurationError("partition plan.coverage.status must be sufficient or insufficient_coverage")
    coverage_reason = require_nonempty_string(coverage, "reason", "partition plan.coverage")
    exposure_policy = require(plan, "exposure_policy", "partition plan")
    if not isinstance(exposure_policy, dict):
        raise ConfigurationError("partition plan.exposure_policy must be an object")
    require_nonempty_string(exposure_policy, "holdout_content_before_freeze", "partition plan.exposure_policy")
    if not isinstance(exposure_policy.get("exposure_log"), list):
        raise ConfigurationError("partition plan.exposure_policy.exposure_log must be a list")
    declared = plan.get("case_ids")
    if not isinstance(declared, list) or not declared or not all(isinstance(item, str) and item.strip() for item in declared) or len(declared) != len(set(declared)):
        raise ConfigurationError("partition plan.case_ids must contain unique non-empty case IDs")
    all_case_ids = set(declared)

    holdout = plan.get("holdout", {"case_ids": [], "status": "not_requested"})
    if not isinstance(holdout, dict):
        raise ConfigurationError("partition plan.holdout must be an object")
    holdout_ids = holdout.get("case_ids", [])
    if not isinstance(holdout_ids, list) or not all(isinstance(item, str) and item.strip() for item in holdout_ids) or len(holdout_ids) != len(set(holdout_ids)) or not set(holdout_ids).issubset(all_case_ids):
        raise ConfigurationError("partition holdout must contain unique declared case IDs")
    if "case_count" in holdout and holdout["case_count"] != len(holdout_ids):
        raise ConfigurationError("partition holdout has an incorrect case_count")
    holdout_status = require_nonempty_string(holdout, "status", "partition holdout")
    planned_development_case_ids = all_case_ids - set(holdout_ids)
    if planned_development_case_ids != development_case_ids:
        raise ConfigurationError("partition development cases must match the supplied suite; final holdout content must remain outside the suite")
    try:
        requested_holdout_count = int((Decimal(len(all_case_ids)) * Decimal(str(requested_holdout_percent)) / Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError) as exc:
        raise ConfigurationError("partition plan.requested_holdout_percent cannot be rounded") from exc
    if holdout_ids and holdout_status == "not_requested":
        raise ConfigurationError("a non-empty holdout cannot be marked not_requested")
    if not holdout_ids and requested_holdout_percent > 0 and holdout_status != "insufficient_coverage":
        raise ConfigurationError("a missing requested holdout must be marked insufficient_coverage")
    if not holdout_ids and requested_holdout_percent == 0 and holdout_status != "not_requested":
        raise ConfigurationError("an empty zero-percent holdout must be marked not_requested")

    groups = require(plan, "groups", "partition plan")
    if not isinstance(groups, list) or not groups:
        raise ConfigurationError("partition plan.groups must be a non-empty list")
    group_ids: set[str] = set()
    grouped_cases: list[str] = []
    group_by_id: dict[str, dict[str, Any]] = {}
    for group in groups:
        if not isinstance(group, dict):
            raise ConfigurationError("every partition group must be an object")
        group_id = require_nonempty_string(group, "id", "partition group")
        if group_id in group_ids:
            raise ConfigurationError(f"duplicate partition group id: {group_id}")
        group_ids.add(group_id)
        group_case_ids = group.get("case_ids")
        if not isinstance(group_case_ids, list) or not group_case_ids or len(group_case_ids) != len(set(group_case_ids)):
            raise ConfigurationError(f"partition group {group_id} must contain unique case_ids")
        if not set(group_case_ids).issubset(development_case_ids):
            raise ConfigurationError(f"partition group {group_id} contains a holdout or unknown case")
        grouped_cases.extend(group_case_ids)
        group_by_id[group_id] = group
    if set(grouped_cases) != development_case_ids or len(grouped_cases) != len(development_case_ids):
        raise ConfigurationError("partition groups must cover each development case exactly once")

    if holdout_ids:
        holdout_groups = holdout.get("groups")
        if not isinstance(holdout_groups, list) or not holdout_groups:
            raise ConfigurationError("a non-empty holdout must declare whole holdout groups")
        holdout_group_cases: list[str] = []
        holdout_group_ids: set[str] = set()
        for group in holdout_groups:
            if not isinstance(group, dict):
                raise ConfigurationError("every holdout group must be an object")
            holdout_group_id = require_nonempty_string(group, "id", "holdout group")
            if holdout_group_id in group_ids:
                raise ConfigurationError(f"holdout group {holdout_group_id} overlaps a development group")
            if holdout_group_id in holdout_group_ids:
                raise ConfigurationError(f"duplicate holdout group id: {holdout_group_id}")
            holdout_group_ids.add(holdout_group_id)
            group_case_ids = group.get("case_ids")
            if not isinstance(group_case_ids, list) or not group_case_ids or not set(group_case_ids).issubset(set(holdout_ids)):
                raise ConfigurationError("holdout groups must contain only holdout cases")
            holdout_group_cases.extend(group_case_ids)
        if set(holdout_group_cases) != set(holdout_ids) or len(holdout_group_cases) != len(set(holdout_group_cases)):
            raise ConfigurationError("holdout groups must cover each holdout case exactly once")
    exposure_log = exposure_policy["exposure_log"]
    required_exposure_fields = {"case_or_group_ids", "actor", "role", "timestamp", "reason", "exposure_type"}
    holdout_group_id_set = {group["id"] for group in holdout.get("groups", []) if isinstance(group, dict) and isinstance(group.get("id"), str)}
    for entry in exposure_log:
        if not isinstance(entry, dict) or not required_exposure_fields.issubset(entry):
            raise ConfigurationError("each exposure log entry must declare case/group IDs, actor, role, timestamp, reason, and exposure type")
        ids = entry["case_or_group_ids"]
        if not isinstance(ids, list) or not ids or not all(isinstance(item, str) and item.strip() for item in ids):
            raise ConfigurationError("exposure log case_or_group_ids must be a non-empty string list")
        if not set(ids).issubset(set(holdout_ids) | holdout_group_id_set):
            raise ConfigurationError("exposure log may reference only holdout cases or groups")
        for key in required_exposure_fields - {"case_or_group_ids"}:
            if not isinstance(entry[key], str) or not entry[key].strip():
                raise ConfigurationError(f"exposure log {key} must be a non-empty string")

    folds = require(plan, "folds", "partition plan")
    if not isinstance(folds, list) or not folds:
        raise ConfigurationError("partition plan.folds must be a non-empty list")
    fold_ids: set[str] = set()
    fold_cases: list[str] = []
    for fold in folds:
        if not isinstance(fold, dict):
            raise ConfigurationError("every partition fold must be an object")
        fold_id = require_nonempty_string(fold, "id", "partition fold")
        if fold_id in fold_ids:
            raise ConfigurationError(f"duplicate partition fold id: {fold_id}")
        fold_ids.add(fold_id)
        fold_group_ids = fold.get("group_ids")
        fold_case_ids = fold.get("case_ids")
        if not isinstance(fold_group_ids, list) or not fold_group_ids or len(fold_group_ids) != len(set(fold_group_ids)):
            raise ConfigurationError(f"partition fold {fold_id} must contain unique group_ids")
        if not isinstance(fold_case_ids, list):
            raise ConfigurationError(f"partition fold {fold_id} must contain case_ids")
        if not set(fold_group_ids).issubset(group_ids):
            raise ConfigurationError(f"partition fold {fold_id} contains an unknown group")
        expected = [case for group_id in fold_group_ids for case in group_by_id[group_id]["case_ids"]]
        if fold_case_ids != expected or len(fold_case_ids) != len(set(fold_case_ids)):
            raise ConfigurationError(f"partition fold {fold_id} case_ids do not match its whole groups")
        if "case_count" in fold and fold["case_count"] != len(fold_case_ids):
            raise ConfigurationError(f"partition fold {fold_id} has an incorrect case_count")
        training_group_ids = fold.get("training_group_ids")
        if not isinstance(training_group_ids, list) or len(training_group_ids) != len(set(training_group_ids)):
            raise ConfigurationError(f"partition fold {fold_id} must declare unique training_group_ids")
        if set(training_group_ids) != group_ids - set(fold_group_ids):
            raise ConfigurationError(f"partition fold {fold_id} training_group_ids must be the complement of validation groups")
        fold_cases.extend(fold_case_ids)
    if set(fold_cases) != development_case_ids or len(fold_cases) != len(development_case_ids):
        raise ConfigurationError("development folds must cover each development case exactly once")
    actual_fold_count = len(folds)
    if coverage_status == "sufficient" and actual_fold_count != requested_fold_count:
        raise ConfigurationError("a sufficient partition must use its requested fold count")
    if coverage_status == "sufficient" and len(holdout_ids) != requested_holdout_count:
        raise ConfigurationError("a sufficient partition must use its rounded requested holdout count")
    if coverage_status == "sufficient" and any(not fold.get("training_group_ids") for fold in folds):
        raise ConfigurationError("a sufficient partition must provide training groups for every fold")
    if coverage_status == "insufficient_coverage" and not coverage_reason:
        raise ConfigurationError("insufficient coverage must explain the limitation")

    return {
        "plan_id": plan_id,
        "scope": scope,
        "scheme": scheme,
        "grouping_key": grouping_key,
        "assignment": assignment,
        "requested_fold_count": requested_fold_count,
        "requested_holdout_percent": requested_holdout_percent,
        "requested_holdout_case_count": requested_holdout_count,
        "rounding_rule": rounding_rule,
        "coverage": {"status": coverage_status, "reason": coverage_reason},
        "exposure_policy": exposure_policy,
        "case_count": len(all_case_ids),
        "fold_count": actual_fold_count,
        "groups": groups,
        "folds": folds,
        "development_case_ids": sorted(development_case_ids),
        "holdout_case_ids": sorted(holdout_ids),
        "holdout_groups": holdout.get("groups", []),
        "holdout_case_count": len(holdout_ids),
        "plan_content_hash": json_hash(plan),
    }


def package_text(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    chunks = []
    for child in sorted(path.rglob("*")):
        if child.is_file() and child.suffix.lower() in {".md", ".markdown", ".txt", ".json", ".yaml", ".yml"}:
            chunks.append(f"--- {child.relative_to(path).as_posix()} ---\n{child.read_text(encoding='utf-8')}\n")
    return "\n".join(chunks)


def parse_candidates(values: list[str]) -> list[dict[str, Any]]:
    if len(values) < 2:
        raise ConfigurationError("at least two candidates are required for a comparison")
    candidates = []
    seen: set[str] = set()
    for value in values:
        candidate_id, separator, raw_path = value.partition("=")
        if not separator or not candidate_id.strip() or not raw_path.strip():
            raise ConfigurationError("each candidate must use ID=PATH syntax")
        if candidate_id in seen:
            raise ConfigurationError(f"duplicate candidate id: {candidate_id}")
        path = Path(raw_path).resolve()
        if not path.is_file() and not path.is_dir():
            raise ConfigurationError(f"candidate path does not exist: {path}")
        seen.add(candidate_id)
        candidates.append({"id": candidate_id, "path": str(path), "source_kind": "directory" if path.is_dir() else "file", "content_hash": content_hash(path), "content": package_text(path)})
    return candidates


def validate_relative_pattern(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{label} must be a non-empty relative path or glob")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ConfigurationError(f"{label} must stay within the trial directory")
    return path.as_posix()


def validate_config(config: dict[str, Any], adapter: str, base_dir: Path | None = None, allow_pending_smoke: bool = False) -> dict[str, Any]:
    base_dir = (base_dir or Path.cwd()).resolve()
    required = ("requested_runner", "requested_model", "requested_reasoning_effort", "actual_runner", "actual_model", "actual_reasoning_effort", "substitution_reason", "requested_environment_identity", "actual_environment_identity", "permissions_profile")
    for key in required:
        require_nonempty_string(config, key, "configuration")
    selection = require(config, "model_selection", "configuration")
    if not isinstance(selection, dict):
        raise ConfigurationError("configuration.model_selection must be an object")
    for key in ("policy", "basis", "reason"):
        require_nonempty_string(selection, key, "configuration.model_selection")
    authorization = require(config, "authorization", "configuration")
    if not isinstance(authorization, dict) or not isinstance(authorization.get("run"), bool) or not isinstance(authorization.get("output"), bool):
        raise ConfigurationError("configuration.authorization must declare boolean run and output fields")
    concurrency = config.get("concurrency")
    if not isinstance(concurrency, int) or isinstance(concurrency, bool) or not 1 <= concurrency <= MAX_CONCURRENCY:
        raise ConfigurationError(f"configuration.concurrency must be an integer from 1 to {MAX_CONCURRENCY}")
    smoke = require(config, "smoke_test", "configuration")
    if not isinstance(smoke, dict):
        raise ConfigurationError("configuration.smoke_test must be an object")
    smoke_status = smoke.get("status")
    if allow_pending_smoke and smoke_status == "pending":
        if smoke.get("output_inspected") is not False or smoke.get("permissions_verified") is not False:
            raise ConfigurationError("pending configuration.smoke_test must explicitly mark output and permissions as unverified")
    elif smoke_status != "passed" or smoke.get("output_inspected") is not True or smoke.get("permissions_verified") is not True:
        raise ConfigurationError("configuration.smoke_test must record a passed, inspected trial with verified permissions")
    require_nonempty_string(smoke, "trial_id", "configuration.smoke_test")
    require_nonempty_string(smoke, "artifact_path", "configuration.smoke_test")
    smoke = dict(smoke)
    smoke_artifact_path = Path(smoke["artifact_path"])
    if not smoke_artifact_path.is_absolute():
        smoke_artifact_path = base_dir / smoke_artifact_path
    smoke["artifact_path"] = str(smoke_artifact_path.resolve())
    if smoke_status == "passed" or not allow_pending_smoke:
        require_nonempty_string(smoke, "output_hash", "configuration.smoke_test")
        require_nonempty_string(smoke, "execution_fingerprint", "configuration.smoke_test")
    command_argv = config.get("command_argv")
    if adapter == "command":
        if not isinstance(command_argv, list) or not command_argv or not all(isinstance(item, str) and item for item in command_argv):
            raise ConfigurationError("command adapter requires a non-empty command_argv string list")
        timeout = config.get("command_timeout_seconds", 120)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 600:
            raise ConfigurationError("command_timeout_seconds must be a finite number greater than 0 and no greater than 600")
    elif command_argv is not None:
        raise ConfigurationError("command_argv is only valid with the command adapter")
    output_limit = config.get("command_output_limit_bytes", DEFAULT_COMMAND_OUTPUT_LIMIT_BYTES)
    if not isinstance(output_limit, int) or isinstance(output_limit, bool) or not 1 <= output_limit <= MAX_COMMAND_OUTPUT_LIMIT_BYTES:
        raise ConfigurationError(f"command_output_limit_bytes must be an integer from 1 to {MAX_COMMAND_OUTPUT_LIMIT_BYTES}")
    artifact_paths = config.get("artifact_paths", [])
    if not isinstance(artifact_paths, list):
        raise ConfigurationError("configuration.artifact_paths must be a list")
    artifact_paths = [validate_relative_pattern(value, "configuration.artifact_paths entry") for value in artifact_paths]
    raw_dependencies = config.get("command_dependencies", [])
    if not isinstance(raw_dependencies, list):
        raise ConfigurationError("configuration.command_dependencies must be a list")
    dependencies = []
    for value in raw_dependencies:
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError("configuration.command_dependencies entries must be non-empty strings")
        path = Path(value)
        if not path.is_absolute():
            path = base_dir / path
        path = path.resolve()
        if not path.is_file() and not path.is_dir():
            raise ConfigurationError(f"configuration.command_dependencies path does not exist: {path}")
        dependencies.append({"path": str(path), "content_hash": content_hash(path)})
    target_id = require_nonempty_string(config, "target_package_id", "configuration")
    target_hash = require_nonempty_string(config, "target_content_hash", "configuration")
    target_path = config.get("target_package_path")
    if target_path is not None:
        target_path_value = Path(target_path)
        if not target_path_value.is_absolute():
            target_path_value = base_dir / target_path_value
        target_path = str(target_path_value.resolve())
        if not Path(target_path).is_file() and not Path(target_path).is_dir():
            raise ConfigurationError(f"configuration.target_package_path does not exist: {target_path}")
        if content_hash(Path(target_path)) != target_hash:
            raise ConfigurationError("target_content_hash does not match target_package_path")
    return {
        "requested": {"runner": config["requested_runner"], "model": config["requested_model"], "reasoning_effort": config["requested_reasoning_effort"]},
        "actual": {"runner": config["actual_runner"], "model": config["actual_model"], "reasoning_effort": config["actual_reasoning_effort"]},
        "model_selection": selection,
        "substitution_reason": config["substitution_reason"],
        "requested_environment_identity": config["requested_environment_identity"],
        "actual_environment_identity": config["actual_environment_identity"],
        "environment_identity": config["actual_environment_identity"],
        "permissions_profile": config["permissions_profile"],
        "authorization": authorization,
        "concurrency": concurrency,
        "smoke_test": smoke,
        "target_package": {"id": target_id, "content_hash": target_hash, "hash_verified": target_path is not None},
        "target_package_path": target_path,
        "command_timeout_seconds": config.get("command_timeout_seconds", 120),
        "command_output_limit_bytes": output_limit,
        "command_argv": command_argv,
        "command_hash": json_hash(command_argv) if command_argv is not None else None,
        "artifact_paths": artifact_paths,
        "command_dependencies": dependencies,
        "adapter_schema_version": ADAPTER_SCHEMA_VERSION,
        "process_controller_version": PROCESS_CONTROLLER_VERSION,
    }


def execution_fingerprint(adapter: str, candidates: list[dict[str, Any]], suite_meta: dict[str, Any], partition: dict[str, Any], config: dict[str, Any]) -> str:
    payload = {
        "adapter": adapter,
        "candidate_hashes": sorted((candidate["id"], candidate["content_hash"]) for candidate in candidates),
        "suite": {key: suite_meta[key] for key in ("suite_id", "suite_version", "content_hash", "rubric_id", "rubric_version")},
        "partition_hash": partition["plan_content_hash"],
        "requested": config["requested"],
        "actual": config["actual"],
        "requested_environment_identity": config["requested_environment_identity"],
        "actual_environment_identity": config["actual_environment_identity"],
        "permissions_profile": config["permissions_profile"],
        "authorization": config["authorization"],
        "concurrency": config["concurrency"],
        "command_timeout_seconds": config["command_timeout_seconds"],
        "command_output_limit_bytes": config["command_output_limit_bytes"],
        "command_hash": config["command_hash"],
        "command_dependencies": config["command_dependencies"],
        "artifact_paths": config["artifact_paths"],
        "adapter_schema_version": config["adapter_schema_version"],
        "process_controller_version": config["process_controller_version"],
        "target_package": config["target_package"],
    }
    return json_hash(payload)


def validate_smoke(config: dict[str, Any], fingerprint: str) -> None:
    smoke_path = Path(config["smoke_test"]["artifact_path"]).resolve()
    try:
        if not smoke_path.is_file():
            raise ConfigurationError(f"smoke artifact does not exist: {smoke_path}")
        if not exact_bytes(smoke_path):
            raise ConfigurationError("smoke artifact is empty")
        if content_hash(smoke_path) != config["smoke_test"]["output_hash"]:
            raise ConfigurationError("smoke artifact hash does not match smoke_test.output_hash")
    except OSError as exc:
        raise ConfigurationError(f"smoke artifact could not be inspected: {exc}") from exc
    if config["smoke_test"]["execution_fingerprint"] != fingerprint:
        raise ConfigurationError("smoke artifact is not bound to the current execution fingerprint")


def validate_red_green(suite: dict[str, Any], candidate_ids: set[str], case_ids: set[str]) -> list[dict[str, Any]]:
    pairs = suite.get("red_green", [])
    for pair in pairs:
        if pair["red_candidate_id"] not in candidate_ids or pair["green_candidate_id"] not in candidate_ids:
            raise ConfigurationError(f"red_green criterion {pair['criterion_id']} references an unknown candidate")
        if pair["red_candidate_id"] == pair["green_candidate_id"] or not set(pair["case_ids"]).issubset(case_ids):
            raise ConfigurationError(f"red_green criterion {pair['criterion_id']} has invalid candidate or case boundary")
    return pairs


def safe_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip(".") or "item"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{normalized[:80]}-{digest}"


def snapshot_candidate(candidate: dict[str, Any], destination: Path) -> Path:
    source = Path(candidate["path"])
    target = destination / safe_name(candidate["id"])
    if source.is_dir():
        shutil.copytree(source, target, symlinks=True)
        snapshot = target
    else:
        target.mkdir(parents=True)
        snapshot = target / source.name
        shutil.copy2(source, snapshot)
    if content_hash(snapshot) != candidate["content_hash"]:
        raise ConfigurationError(f"candidate snapshot hash changed for {candidate['id']}")
    return snapshot


def check_candidate_text(content: str, case: dict[str, Any]) -> tuple[str, list[dict[str, Any]], str | None]:
    evidence = []
    for check in case["checks"]:
        value = check["value"]
        passed = value in content if check["type"] == "contains" else value not in content
        evidence.append({"type": check["type"], "value": value, "passed": passed})
    if all(item["passed"] for item in evidence):
        return "passed", evidence, None
    return "failed", evidence, "one or more declared checks failed"


def trial_identity(run_id: str, candidate_id: str, case_id: str) -> str:
    payload = json.dumps([run_id, candidate_id, case_id], ensure_ascii=False, separators=(",", ":"))
    return "trial-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def base_result(candidate: dict[str, Any], case: dict[str, Any], config: dict[str, Any], suite_meta: dict[str, Any], adapter: str, output_reference: str, run_id: str) -> dict[str, Any]:
    return {
        "trial_id": trial_identity(run_id, candidate["id"], case["id"]),
        "case_id": case["id"],
        "candidate_id": candidate["id"],
        "candidate_content_hash": candidate["content_hash"],
        "target_content_hash": config["target_package"]["content_hash"],
        "suite_id": suite_meta["suite_id"],
        "suite_version": suite_meta["suite_version"],
        "suite_content_hash": suite_meta["content_hash"],
        "rubric_id": suite_meta["rubric_id"],
        "rubric_version": suite_meta["rubric_version"],
        "requested_runner": config["requested"]["runner"],
        "actual_runner": config["actual"]["runner"],
        "requested_model": config["requested"]["model"],
        "actual_model": config["actual"]["model"],
        "requested_reasoning_effort": config["requested"]["reasoning_effort"],
        "actual_reasoning_effort": config["actual"]["reasoning_effort"],
        "requested_environment_identity": config["requested_environment_identity"],
        "actual_environment_identity": config["actual_environment_identity"],
        "environment_identity": config["environment_identity"],
        "adapter": adapter,
        "command_hash": config["command_hash"],
        "substitution_reason": config["substitution_reason"],
        "permissions_profile": config["permissions_profile"],
        "concurrency": config["concurrency"],
        "command_timeout_seconds": config["command_timeout_seconds"],
        "command_output_limit_bytes": config["command_output_limit_bytes"],
        "process_controller_version": config["process_controller_version"],
        "started_at": utc_now(),
        "loaded_references": [],
        "output_reference": output_reference,
    }


def finish_result(base: dict[str, Any], status: str, evidence: list[dict[str, Any]], failure: str | None, artifacts: dict[str, Any] | None = None, *, evidence_valid: bool = True) -> dict[str, Any]:
    result = dict(base)
    result.update({"finished_at": utc_now(), "status": status, "evidence_valid": evidence_valid, "observed_evidence": evidence, "failure_reason": failure})
    if artifacts is not None:
        result["attempt_artifacts"] = artifacts
    return result


def output_artifact(data: bytes, path: Path) -> dict[str, Any]:
    path.write_bytes(data)
    decoded = data.decode("utf-8", errors="replace")
    return {"path": str(path), "hash": hash_bytes(data), "size": len(data), "preview": decoded[-MAX_PREVIEW:]}


def within_directory(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def paths_overlap(first: Path, second: Path) -> bool:
    first = first.resolve()
    second = second.resolve()
    return first == second or within_directory(first, second) or within_directory(second, first)


def validate_output_paths(output_path: Path, attempts_path: Path, artifacts_dir: Path, protected_paths: list[Path]) -> None:
    generated = (output_path, attempts_path, artifacts_dir)
    for index, first in enumerate(generated):
        for second in generated[index + 1:]:
            if paths_overlap(first, second):
                raise ConfigurationError(f"generated output paths overlap: {first} and {second}")
    for generated_path in generated:
        for protected_path in protected_paths:
            if paths_overlap(generated_path, protected_path):
                raise ConfigurationError(f"generated output path overlaps protected input: {generated_path} and {protected_path}")


def copy_trial_candidate(snapshot: Path, destination: Path, expected_hash: str) -> Path:
    candidate_root = destination / "candidate"
    if snapshot.is_dir():
        shutil.copytree(snapshot, candidate_root, symlinks=True)
        target = candidate_root
    else:
        candidate_root.mkdir()
        target = candidate_root / snapshot.name
        shutil.copy2(snapshot, target)
    if content_hash(target) != expected_hash:
        raise ConfigurationError("candidate trial copy failed hash verification")
    return target


def collect_trial_artifacts(trial_dir: Path, attempt_dir: Path, patterns: list[str]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    total_bytes = 0
    seen: set[Path] = set()
    collection_errors: list[str] = []
    destination_root = attempt_dir / "files"
    for pattern in patterns:
        pattern_satisfied = False
        try:
            matches = trial_dir.glob(pattern)
        except (OSError, ValueError) as exc:
            collection_errors.append(f"{pattern}: invalid pattern: {exc}")
            continue
        for source in matches:
            if not source.is_file():
                continue
            resolved = source.resolve()
            if not within_directory(resolved, trial_dir):
                collection_errors.append(f"{pattern}: matched path escapes trial directory")
                continue
            if resolved in seen:
                pattern_satisfied = True
                continue
            seen.add(resolved)
            try:
                size = source.stat().st_size
            except OSError as exc:
                collection_errors.append(f"{source}: could not inspect artifact: {exc}")
                continue
            if len(files) >= MAX_ARTIFACT_FILES or total_bytes + size > MAX_ARTIFACT_BYTES:
                collection_errors.append("artifact collection limit exceeded")
                break
            relative = source.relative_to(trial_dir)
            destination = destination_root / relative
            try:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                file_hash = content_hash(source)
            except (OSError, ConfigurationError) as exc:
                collection_errors.append(f"{relative.as_posix()}: could not retain artifact: {exc}")
                continue
            files.append({"path": str(destination), "relative_path": relative.as_posix(), "size": size, "hash": file_hash})
            total_bytes += size
            pattern_satisfied = True
        if not pattern_satisfied:
            collection_errors.append(f"{pattern}: no retained artifact matched the declared pattern")
    return {"files": files, "total_bytes": total_bytes, "collection_errors": collection_errors}


class BoundedCapture:
    """Drain one command stream while retaining only a bounded prefix."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.data = bytearray()
        self.total_bytes = 0
        self.exceeded = threading.Event()
        self.finished = threading.Event()
        self.read_error: str | None = None

    def read(self, stream: Any) -> None:
        try:
            while True:
                chunk = stream.read(64 * 1024)
                if not chunk:
                    return
                self.total_bytes += len(chunk)
                if len(self.data) < self.limit:
                    self.data.extend(chunk[: self.limit - len(self.data)])
                if self.total_bytes > self.limit:
                    self.exceeded.set()
        except (OSError, ValueError) as exc:
            self.read_error = str(exc)
        finally:
            self.finished.set()


_ACTIVE_CONTROLLERS: set["ProcessTreeController"] = set()
_ACTIVE_CONTROLLERS_LOCK = threading.Lock()
_STOP_REQUESTED = threading.Event()


def _create_windows_job(process: subprocess.Popen[bytes]) -> Any:
    """Create and attach a kill-on-close Job Object to a suspended process."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
        )]

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, wintypes.INT, wintypes.LPVOID, wintypes.DWORD]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
    limits = ExtendedLimitInformation()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        error = ctypes.get_last_error()
        kernel32.CloseHandle(job)
        raise OSError(error, "SetInformationJobObject failed")
    if not kernel32.AssignProcessToJobObject(job, wintypes.HANDLE(process._handle)):
        error = ctypes.get_last_error()
        kernel32.CloseHandle(job)
        raise OSError(error, "AssignProcessToJobObject failed")
    return (kernel32, job)


def _resume_windows_process(process: subprocess.Popen[bytes]) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    class ThreadEntry32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD),
            ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", wintypes.LONG),
            ("tpDeltaPri", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
        ]

    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(ThreadEntry32)]
    kernel32.Thread32First.restype = wintypes.BOOL
    kernel32.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(ThreadEntry32)]
    kernel32.Thread32Next.restype = wintypes.BOOL
    kernel32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenThread.restype = wintypes.HANDLE
    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
    if not snapshot or snapshot == wintypes.HANDLE(-1).value:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot failed")
    thread_handle = None
    try:
        entry = ThreadEntry32()
        entry.dwSize = ctypes.sizeof(ThreadEntry32)
        found = kernel32.Thread32First(snapshot, ctypes.byref(entry))
        while found:
            if entry.th32OwnerProcessID == process.pid:
                thread_handle = kernel32.OpenThread(0x0002, False, entry.th32ThreadID)  # THREAD_SUSPEND_RESUME
                if thread_handle:
                    break
            found = kernel32.Thread32Next(snapshot, ctypes.byref(entry))
        if not thread_handle:
            raise OSError(ctypes.get_last_error(), "OpenThread failed")
        if kernel32.ResumeThread(thread_handle) == 0xFFFFFFFF:
            raise OSError(ctypes.get_last_error(), "ResumeThread failed")
    finally:
        if thread_handle:
            kernel32.CloseHandle(thread_handle)
        kernel32.CloseHandle(snapshot)


class ProcessTreeController:
    """Run one command with bounded output and whole-tree cleanup."""

    def __init__(self, argv: list[str], cwd: Path, output_limit: int) -> None:
        self.argv = argv
        self.cwd = cwd
        self.output_limit = output_limit
        self.process: subprocess.Popen[bytes] | None = None
        self.job: Any = None
        self.stdout_capture = BoundedCapture(output_limit)
        self.stderr_capture = BoundedCapture(output_limit)
        self.stop_requested = threading.Event()
        self.termination_reason: str | None = None
        self.termination_method: str | None = None
        self.containment_method: str | None = None
        self.containment_established = False
        self.tree_termination_verified = False
        self.tree_cleanup_verified = False
        self.elapsed_seconds = 0.0
        self._readers: list[threading.Thread] = []
        self._termination_attempted = False

    def _abort_start(self) -> None:
        if self.process is None:
            return
        try:
            self.process.kill()
        except OSError:
            pass
        try:
            self.process.wait(timeout=PROCESS_TERMINATION_GRACE_SECONDS)
        except (OSError, subprocess.TimeoutExpired):
            pass
        for stream in (self.process.stdout, self.process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass

    def start(self) -> None:
        kwargs: dict[str, Any] = {"cwd": self.cwd, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
        if os.name == "nt":
            kwargs["creationflags"] = (
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | 0x00000004  # CREATE_SUSPENDED
            )
        else:
            kwargs["start_new_session"] = True
        self.process = subprocess.Popen(self.argv, **kwargs)
        try:
            if os.name == "nt":
                self.job = _create_windows_job(self.process)
                _resume_windows_process(self.process)
                self.containment_method = "windows_job"
            else:
                self.containment_method = "process_group"
            self.containment_established = True
        except OSError as exc:
            self.tree_termination_verified = False
            self._abort_start()
            raise OSError(f"whole-process-tree containment could not be established: {exc}") from exc
        self._readers = [
            threading.Thread(target=self.stdout_capture.read, args=(self.process.stdout,), daemon=True),
            threading.Thread(target=self.stderr_capture.read, args=(self.process.stderr,), daemon=True),
        ]
        for reader in self._readers:
            reader.start()

    def request_stop(self, reason: str = "interrupted") -> None:
        self.stop_requested.set()
        self.termination_reason = reason
        if self.process is not None:
            self._terminate_tree(force=True)

    def _close_job(self) -> bool:
        if self.job is None:
            return True
        kernel32, handle = self.job
        closed = bool(kernel32.CloseHandle(handle))
        self.job = None
        return closed

    def _terminate_tree(self, force: bool) -> None:
        process = self.process
        if process is None or not self.containment_established:
            self.tree_termination_verified = False
            return
        if self._termination_attempted:
            return
        self._termination_attempted = True
        if os.name == "nt":
            self.termination_method = "windows_job_close"
            self.tree_termination_verified = self._close_job()
            if process.poll() is None:
                try:
                    process.kill()
                except OSError:
                    pass
        else:
            self.termination_method = "process_group"
            try:
                os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
                self.tree_termination_verified = True
            except ProcessLookupError:
                self.tree_termination_verified = True
            except OSError:
                self.tree_termination_verified = False
            if process.poll() is None:
                try:
                    process.kill()
                except OSError:
                    pass

    def _join_readers(self, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        for reader in self._readers:
            reader.join(max(0.0, deadline - time.monotonic()))
        return all(not reader.is_alive() for reader in self._readers)

    def _close_streams(self) -> None:
        if any(reader.is_alive() for reader in self._readers):
            return
        for stream in (self.process.stdout if self.process else None, self.process.stderr if self.process else None):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass

    def _result(self, started: float, readers_finished: bool) -> dict[str, Any]:
        process_finished = self.process is not None and self.process.poll() is not None
        self.tree_cleanup_verified = bool(process_finished and readers_finished and self.containment_established and self.tree_termination_verified)
        self.elapsed_seconds = time.monotonic() - started
        return {
            "returncode": self.process.returncode if self.process is not None else None,
            "stdout": bytes(self.stdout_capture.data),
            "stderr": bytes(self.stderr_capture.data),
            "stdout_total_bytes": self.stdout_capture.total_bytes,
            "stderr_total_bytes": self.stderr_capture.total_bytes,
            "output_truncated": self.stdout_capture.exceeded.is_set() or self.stderr_capture.exceeded.is_set(),
            "termination_reason": self.termination_reason,
            "termination_method": self.termination_method,
            "containment_method": self.containment_method,
            "tree_cleanup_verified": self.tree_cleanup_verified,
            "reader_errors": [error for error in (self.stdout_capture.read_error, self.stderr_capture.read_error) if error],
            "elapsed_seconds": self.elapsed_seconds,
        }

    def run(self, timeout: float) -> dict[str, Any]:
        started = time.monotonic()
        readers_finished = False
        try:
            self.start()
            reason = None
            while self.process is not None and self.process.poll() is None:
                if self.stop_requested.is_set():
                    reason = self.termination_reason or "interrupted"
                    break
                if self.stdout_capture.exceeded.is_set() or self.stderr_capture.exceeded.is_set():
                    reason = "command_output_limit"
                    break
                if time.monotonic() - started >= timeout:
                    reason = "command_timeout"
                    break
                time.sleep(0.01)
            if reason is not None:
                self.termination_reason = reason
            # Closing the containment boundary also cleans up descendants that
            # outlive a normally exiting parent.
            self._terminate_tree(force=True)
            if self.stdout_capture.exceeded.is_set() or self.stderr_capture.exceeded.is_set():
                self.termination_reason = self.termination_reason or "command_output_limit"
            readers_finished = self._join_readers(PROCESS_TERMINATION_GRACE_SECONDS)
            if self.stdout_capture.exceeded.is_set() or self.stderr_capture.exceeded.is_set():
                self.termination_reason = self.termination_reason or "command_output_limit"
            if not readers_finished:
                self.termination_reason = self.termination_reason or "output_pipe_cleanup_timeout"
                self._terminate_tree(force=True)
                readers_finished = self._join_readers(PROCESS_TERMINATION_GRACE_SECONDS)
            if self.process is not None:
                try:
                    self.process.wait(timeout=PROCESS_TERMINATION_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    self._terminate_tree(force=True)
                    try:
                        self.process.wait(timeout=PROCESS_TERMINATION_GRACE_SECONDS)
                    except subprocess.TimeoutExpired:
                        pass
            return self._result(started, readers_finished)
        except BaseException:
            self.termination_reason = self.termination_reason or "controller_exception"
            self._terminate_tree(force=True)
            readers_finished = self._join_readers(PROCESS_TERMINATION_GRACE_SECONDS)
            if self.process is not None and self.process.poll() is None:
                try:
                    self.process.kill()
                    self.process.wait(timeout=PROCESS_TERMINATION_GRACE_SECONDS)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            raise
        finally:
            self._close_streams()
            if self.job is not None:
                self._close_job()


def register_controller(controller: ProcessTreeController) -> None:
    with _ACTIVE_CONTROLLERS_LOCK:
        _ACTIVE_CONTROLLERS.add(controller)
        stopped = _STOP_REQUESTED.is_set()
    if stopped:
        controller.request_stop()


def unregister_controller(controller: ProcessTreeController) -> None:
    with _ACTIVE_CONTROLLERS_LOCK:
        _ACTIVE_CONTROLLERS.discard(controller)


def stop_active_controllers() -> None:
    _STOP_REQUESTED.set()
    with _ACTIVE_CONTROLLERS_LOCK:
        active = list(_ACTIVE_CONTROLLERS)
    for controller in active:
        controller.request_stop()


def reset_stop_request() -> None:
    _STOP_REQUESTED.clear()


def stop_requested() -> bool:
    return _STOP_REQUESTED.is_set()


def execute_trial(candidate: dict[str, Any], case: dict[str, Any], snapshot: Path, config: dict[str, Any], suite_meta: dict[str, Any], adapter: str, output_reference: str, artifacts_dir: Path, run_id: str) -> dict[str, Any]:
    base = base_result(candidate, case, config, suite_meta, adapter, output_reference, run_id)
    if stop_requested():
        return interrupted_result(candidate, case, config, suite_meta, adapter, output_reference, run_id, "interrupted before trial started")
    if adapter == "deterministic":
        status, evidence, failure = check_candidate_text(candidate["content"], case)
        return finish_result(base, status, evidence, failure)

    trial_dir = Path(tempfile.mkdtemp(prefix=safe_name(base["trial_id"]) + "-"))
    attempt_dir = artifacts_dir / safe_name(base["trial_id"])
    attempt_dir.mkdir(parents=True, exist_ok=False)
    trial_candidate = copy_trial_candidate(snapshot, trial_dir, candidate["content_hash"])
    public_case = {key: value for key, value in case.items() if key not in {"checks", "required", "critical"}}
    public_suite = {"suite_id": suite_meta["suite_id"], "suite_version": suite_meta["suite_version"], "cases": [public_case]}
    suite_path = trial_dir / "suite.json"
    suite_path.write_text(json.dumps(public_suite, indent=2) + "\n", encoding="utf-8")
    substitutions = {"candidate": str(trial_candidate), "candidate_id": candidate["id"], "suite": str(suite_path), "case_id": case["id"], "trial_dir": str(trial_dir)}

    def make_artifacts(returncode: int | None, stdout: bytes = b"", stderr: bytes = b"", command: dict[str, Any] | None = None) -> dict[str, Any]:
        command = command or {
            "stdout_total_bytes": len(stdout),
            "stderr_total_bytes": len(stderr),
            "output_truncated": False,
            "termination_reason": None,
            "termination_method": None,
            "containment_method": None,
            "tree_cleanup_verified": False,
            "elapsed_seconds": None,
            "reader_errors": [],
        }
        try:
            candidate_after_hash = content_hash(trial_candidate)
        except (OSError, ConfigurationError) as exc:
            candidate_after_hash = None
            candidate_hash_error = str(exc)
        else:
            candidate_hash_error = None
        return {
            "returncode": returncode,
            "candidate_before_hash": candidate["content_hash"],
            "candidate_after_hash": candidate_after_hash,
            "candidate_modified": candidate_after_hash not in {None, candidate["content_hash"]},
            "candidate_hash_error": candidate_hash_error,
            "stdout": output_artifact(stdout, attempt_dir / "stdout.bin"),
            "stderr": output_artifact(stderr, attempt_dir / "stderr.bin"),
            "stdout_total_bytes": command["stdout_total_bytes"],
            "stderr_total_bytes": command["stderr_total_bytes"],
            "output_truncated": command["output_truncated"],
            "termination_reason": command["termination_reason"],
            "termination_method": command["termination_method"],
            "containment_method": command["containment_method"],
            "tree_cleanup_verified": command["tree_cleanup_verified"],
            "elapsed_seconds": command["elapsed_seconds"],
            "reader_errors": command["reader_errors"],
            "files": collect_trial_artifacts(trial_dir, attempt_dir, config["artifact_paths"]),
        }

    try:
        argv = [item.format(**substitutions) for item in config["command_argv"]]
        controller = ProcessTreeController(argv, trial_dir, config["command_output_limit_bytes"])
        register_controller(controller)
        try:
            if stop_requested():
                return interrupted_result(candidate, case, config, suite_meta, adapter, output_reference, run_id, "interrupted before trial started")
            command = controller.run(config["command_timeout_seconds"])
        finally:
            unregister_controller(controller)
        stdout = command["stdout"]
        stderr = command["stderr"]
        artifacts = make_artifacts(command["returncode"], stdout, stderr, command)
        if artifacts["candidate_hash_error"] or artifacts["candidate_modified"]:
            return finish_result(
                base,
                "failed",
                [{"type": "candidate_integrity", "passed": False, "before_hash": artifacts["candidate_before_hash"], "after_hash": artifacts["candidate_after_hash"], "hash_error": artifacts["candidate_hash_error"]}],
                "candidate snapshot was modified or could not be verified after execution",
                artifacts,
                evidence_valid=False,
            )
        if not command["tree_cleanup_verified"]:
            return finish_result(base, "failed", [{"type": "process_cleanup", "passed": False, "termination_reason": command["termination_reason"]}], "process-tree cleanup could not be verified", artifacts, evidence_valid=False)
        if command["reader_errors"]:
            return finish_result(base, "failed", [{"type": "command_output_read", "passed": False, "errors": command["reader_errors"]}], "command output could not be read completely", artifacts, evidence_valid=False)
        if command["termination_reason"]:
            return finish_result(base, "failed", [{"type": command["termination_reason"], "passed": False, "elapsed_seconds": command["elapsed_seconds"]}], f"command ended because of {command['termination_reason']}", artifacts, evidence_valid=False)
        if command["returncode"] != 0:
            return finish_result(base, "failed", [{"type": "command_returncode", "value": command["returncode"], "passed": False}], f"command exited with return code {command['returncode']}", artifacts, evidence_valid=False)
        if artifacts["files"]["collection_errors"]:
            return finish_result(base, "failed", [{"type": "artifact_collection", "passed": False, "errors": artifacts["files"]["collection_errors"]}], "declared trial artifacts could not be collected", artifacts, evidence_valid=False)
        text = stdout.decode("utf-8", errors="replace")
        if not text.strip():
            return finish_result(base, "failed", [{"type": "command_output", "passed": False}], "command produced no stdout", artifacts, evidence_valid=False)
        status, evidence, failure = check_candidate_text(text, case)
        return finish_result(base, status, evidence, failure, artifacts)
    except (OSError, KeyError, ValueError) as exc:
        artifacts = make_artifacts(None)
        if artifacts["candidate_hash_error"] or artifacts["candidate_modified"]:
            return finish_result(base, "failed", [{"type": "candidate_integrity", "passed": False, "before_hash": artifacts["candidate_before_hash"], "after_hash": artifacts["candidate_after_hash"], "hash_error": artifacts["candidate_hash_error"]}], "candidate snapshot was modified or could not be verified after execution", artifacts, evidence_valid=False)
        return finish_result(base, "failed", [{"type": "command_execution", "passed": False}], f"command could not execute: {exc}", artifacts, evidence_valid=False)
    finally:
        shutil.rmtree(trial_dir, ignore_errors=True)


def interrupted_result(candidate: dict[str, Any], case: dict[str, Any], config: dict[str, Any], suite_meta: dict[str, Any], adapter: str, output_reference: str, run_id: str, reason: str) -> dict[str, Any]:
    return finish_result(base_result(candidate, case, config, suite_meta, adapter, output_reference, run_id), "not_run", [], reason, evidence_valid=False)


def append_attempt(handle: Any, result: dict[str, Any]) -> None:
    handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    handle.flush()


def recommend(results: list[dict[str, Any]], candidates: list[dict[str, Any]], cases: dict[str, dict[str, Any]], status: str, red_green_results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    scores = {}
    for candidate in candidates:
        own = [result for result in results if result["candidate_id"] == candidate["id"]]
        failed_required = [result["case_id"] for result in own if cases[result["case_id"]].get("required", True) and result["status"] != "passed"]
        failed_critical = [result["case_id"] for result in own if cases[result["case_id"]].get("critical", False) and result["status"] != "passed"]
        passed = sum(result["status"] == "passed" for result in own)
        scores[candidate["id"]] = {"passed": passed, "total": len(own), "pass_rate": passed / len(own) if own else 0.0, "failed_required_case_ids": failed_required, "failed_critical_case_ids": failed_critical, "eligible": not failed_required and not failed_critical}
    limitations = ["Deterministic checks provide structural evidence only; they do not establish live model quality or Cloud compatibility.", "Clarity and maintenance still require named human review."]
    if status != "complete":
        recommendation_status = "blocked" if status == "blocked" else "incomplete"
        return {"status": recommendation_status, "selected_candidate_id": None, "scores": scores, "rationale": "The comparison did not complete.", "limitations": limitations}
    if red_green_results and any(item["status"] != "demonstrated" for item in red_green_results):
        return {"status": "red_green_not_demonstrated", "selected_candidate_id": None, "scores": scores, "rationale": "A declared red/green criterion lacks complete observed red failure and green success evidence.", "limitations": limitations}
    eligible = [candidate_id for candidate_id, score in scores.items() if score["eligible"]]
    if not eligible:
        return {"status": "no_eligible_candidate", "selected_candidate_id": None, "scores": scores, "rationale": "Every candidate failed a required or critical criterion.", "limitations": limitations}
    best = max(scores[candidate_id]["pass_rate"] for candidate_id in eligible)
    leaders = [candidate_id for candidate_id in eligible if scores[candidate_id]["pass_rate"] == best]
    if len(leaders) != 1:
        return {"status": "manual_review_required", "selected_candidate_id": None, "scores": scores, "rationale": "The eligible candidates are tied; behavior, clarity, and maintenance require review.", "limitations": limitations}
    selected = leaders[0]
    return {"status": "selected", "selected_candidate_id": selected, "scores": scores, "rationale": "The selected candidate passed all required and critical criteria and has the highest eligible pass rate; confirm clarity and maintenance before adoption.", "limitations": limitations}


def evaluate_red_green(pairs: list[dict[str, Any]], results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(result["candidate_id"], result["case_id"]): result for result in results}

    def classify(result: dict[str, Any] | None) -> str:
        if result is None or result["status"] in {"blocked", "not_run"}:
            return "not_evaluated"
        if result.get("evidence_valid") is not True:
            return "invalid_evidence"
        evidence = result.get("observed_evidence", [])
        if not evidence or any(item.get("type") not in {"contains", "not_contains"} or not isinstance(item.get("passed"), bool) for item in evidence):
            return "invalid_evidence"
        if result["status"] == "passed" and all(item["passed"] for item in evidence):
            return "valid_pass"
        if result["status"] == "failed" and any(not item["passed"] for item in evidence):
            return "valid_fail"
        return "invalid_evidence"

    def case_details(results_for_candidate: list[tuple[str, dict[str, Any] | None, str]]) -> list[dict[str, Any]]:
        return [
            {
                "case_id": pair_case_id,
                "classification": classification,
                "status": result["status"] if result else "not_run",
                "observed_evidence": result.get("observed_evidence", []) if result else [],
                "failure_reason": result.get("failure_reason") if result else "result missing",
            }
            for pair_case_id, result, classification in results_for_candidate
        ]

    evaluated = []
    for pair in pairs:
        red_results = [by_key.get((pair["red_candidate_id"], case_id)) for case_id in pair["case_ids"]]
        green_results = [by_key.get((pair["green_candidate_id"], case_id)) for case_id in pair["case_ids"]]
        red_classifications = [classify(result) for result in red_results]
        green_classifications = [classify(result) for result in green_results]
        all_classifications = red_classifications + green_classifications
        if "not_evaluated" in all_classifications:
            criterion_status = "not_evaluated"
        elif "invalid_evidence" in all_classifications:
            criterion_status = "invalid_evidence"
        elif all(classification == "valid_pass" for classification in green_classifications) and any(classification == "valid_fail" for classification in red_classifications):
            criterion_status = "demonstrated"
        elif all(classification == "valid_pass" for classification in red_classifications):
            criterion_status = "red_not_observed"
        else:
            criterion_status = "green_failed"
        evaluated.append({
            "criterion_id": pair["criterion_id"],
            "red_candidate_id": pair["red_candidate_id"],
            "green_candidate_id": pair["green_candidate_id"],
            "case_ids": pair["case_ids"],
            "status": criterion_status,
            "red_cases": case_details([(case_id, result, classification) for case_id, result, classification in zip(pair["case_ids"], red_results, red_classifications)]),
            "green_cases": case_details([(case_id, result, classification) for case_id, result, classification in zip(pair["case_ids"], green_results, green_classifications)]),
        })
    return evaluated


def report_summary(status: str, results: list[dict[str, Any]], recommendation: dict[str, Any]) -> str:
    counts = {name: sum(result["status"] == name for result in results) for name in STATUSES}
    selected = recommendation.get("selected_candidate_id") or "none"
    return f"Comparison {status}: {len(results)} trial result(s); " + ", ".join(f"{key}={counts[key]}" for key in sorted(counts)) + f"; selected={selected}."


def reserve_output(output_path: Path, attempts_path: Path, artifacts_dir: Path) -> tuple[Any, Any]:
    output_handle = None
    attempt_handle = None
    output_created = False
    attempts_created = False
    artifacts_created = False
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="wb", dir=output_path.parent, prefix=".comparison-write-", delete=True) as probe:
            probe.write(b"preflight")
            probe.flush()
        output_handle = output_path.open("x", encoding="utf-8")
        output_created = True
        attempt_handle = attempts_path.open("x", encoding="utf-8")
        attempts_created = True
        artifacts_dir.mkdir()
        artifacts_created = True
        return output_handle, attempt_handle
    except (OSError, FileExistsError) as exc:
        if output_handle is not None:
            output_handle.close()
        if attempt_handle is not None:
            attempt_handle.close()
        if artifacts_created:
            try:
                artifacts_dir.rmdir()
            except OSError:
                pass
        if attempts_created:
            try:
                attempts_path.unlink()
            except OSError:
                pass
        if output_created:
            try:
                output_path.unlink()
            except OSError:
                pass
        raise ConfigurationError(f"output destination or evidence path is unavailable: {exc}") from exc


def write_report(output_handle: Any, report: dict[str, Any]) -> None:
    try:
        output_handle.seek(0)
        output_handle.truncate()
        json.dump(report, output_handle, indent=2, ensure_ascii=False)
        output_handle.write("\n")
        output_handle.flush()
    except OSError as exc:
        raise ConfigurationError(f"could not write comparison report: {exc}") from exc


def run_comparison(args: argparse.Namespace) -> dict[str, Any]:
    suite_path = Path(args.suite).resolve()
    partition_path = Path(args.partition_plan).resolve()
    config_path = Path(args.config).resolve()
    suite, suite_hash, cases = load_suite(suite_path)
    partition = validate_partition(read_json(partition_path), set(cases))
    candidates = parse_candidates(args.candidate)
    raw_config = read_json(config_path)
    config = validate_config(raw_config, args.adapter, config_path.parent, allow_pending_smoke=args.preflight)
    output_path = Path(args.output).resolve()
    if not args.preflight and not config["authorization"]["output"]:
        raise ConfigurationError("output authorization is false; refusing to create a report")
    input_paths = [suite_path, partition_path, config_path, *(Path(candidate["path"]).resolve() for candidate in candidates), Path(config["smoke_test"]["artifact_path"]).resolve()]
    if config["target_package_path"]:
        input_paths.append(Path(config["target_package_path"]).resolve())
    run_id = args.run_id or "run-" + uuid.uuid4().hex[:12]
    attempts_path = output_path.with_suffix(output_path.suffix + ".attempts.jsonl")
    artifacts_dir = output_path.parent / (output_path.stem + ".attempts")
    protected_paths = input_paths + [Path(dependency["path"]).resolve() for dependency in config["command_dependencies"]]
    validate_output_paths(output_path, attempts_path, artifacts_dir, protected_paths)
    suite_meta = {"suite_id": suite["suite_id"], "suite_version": suite["suite_version"], "rubric_id": suite["rubric_id"], "rubric_version": suite["rubric_version"], "content_hash": suite_hash}
    fingerprint = execution_fingerprint(args.adapter, candidates, suite_meta, partition, config)
    red_green = validate_red_green(suite, {candidate["id"] for candidate in candidates}, set(cases))
    if args.preflight:
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "artifact_kind": "candidate_comparison_preflight",
            "execution_fingerprint": fingerprint,
            "target_package": config["target_package"],
            "suite_id": suite["suite_id"],
            "suite_version": suite["suite_version"],
            "suite_content_hash": suite_hash,
            "rubric_id": suite["rubric_id"],
            "rubric_version": suite["rubric_version"],
            "partition": partition,
            "candidates": [{key: value for key, value in candidate.items() if key != "content"} for candidate in candidates],
            "configuration": {key: value for key, value in config.items() if key not in {"command_argv", "target_package_path"}},
            "smoke_requirements": {
                "status": "passed",
                "output_inspected": True,
                "permissions_verified": True,
                "execution_fingerprint": fingerprint,
            },
        }
    validate_smoke(config, fingerprint)
    attempt_handle = None
    output_handle = None
    results: list[dict[str, Any]] = []
    status = "complete"
    run_cases = [cases[case_id] for case_id in partition["development_case_ids"]]
    with tempfile.TemporaryDirectory(prefix="candidate-snapshots-") as snapshot_root:
        snapshots = {candidate["id"]: snapshot_candidate(candidate, Path(snapshot_root)) for candidate in candidates}
        output_handle, attempt_handle = reserve_output(output_path, attempts_path, artifacts_dir)
        try:
            if config["authorization"]["run"]:
                reset_stop_request()
                executor = ThreadPoolExecutor(max_workers=config["concurrency"], thread_name_prefix="candidate-trial")
                future_map: dict[Future[dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]] = {
                    executor.submit(execute_trial, candidate, case, snapshots[candidate["id"]], config, suite_meta, args.adapter, str(output_path), artifacts_dir, run_id): (candidate, case)
                    for candidate in candidates for case in run_cases
                }
                seen: set[Future[dict[str, Any]]] = set()
                try:
                    for future in as_completed(future_map):
                        candidate, case = future_map[future]
                        seen.add(future)
                        try:
                            result = future.result()
                        except Exception as exc:
                            result = finish_result(base_result(candidate, case, config, suite_meta, args.adapter, str(output_path), run_id), "failed", [{"type": "unexpected_exception", "passed": False}], f"trial raised an unexpected error: {exc}", evidence_valid=False)
                        results.append(result)
                        append_attempt(attempt_handle, result)
                except KeyboardInterrupt:
                    status = "incomplete"
                    stop_active_controllers()
                    for future in future_map:
                        if future in seen:
                            continue
                        future.cancel()
                    for future in future_map:
                        if future in seen or future.cancelled():
                            if future.cancelled() and future not in seen:
                                candidate, case = future_map[future]
                                result = interrupted_result(candidate, case, config, suite_meta, args.adapter, str(output_path), run_id, "interrupted before trial started")
                                results.append(result)
                                append_attempt(attempt_handle, result)
                            continue
                        candidate, case = future_map[future]
                        try:
                            result = future.result()
                        except Exception as exc:
                            result = finish_result(base_result(candidate, case, config, suite_meta, args.adapter, str(output_path), run_id), "failed", [{"type": "unexpected_exception", "passed": False}], f"trial raised an unexpected error after interruption: {exc}", evidence_valid=False)
                        results.append(result)
                        append_attempt(attempt_handle, result)
                finally:
                    executor.shutdown(wait=True, cancel_futures=True)
                    reset_stop_request()
                expected = len(candidates) * len(run_cases)
                if len(results) != expected or any(result["status"] in {"blocked", "not_run"} or result.get("evidence_valid") is not True for result in results):
                    status = "incomplete"
            else:
                status = "blocked"

            results.sort(key=lambda item: (item["candidate_id"], item["case_id"]))
            red_green_results = evaluate_red_green(red_green, results)
            recommendation = recommend(results, candidates, cases, status, red_green_results)
            report = {
                "schema_version": REPORT_SCHEMA_VERSION,
                "artifact_kind": "candidate_comparison_report",
                "run_id": run_id,
                "status": status,
                "output_destination": str(output_path),
                "attempts_log": str(attempts_path) if attempts_path.exists() else None,
                "attempt_artifacts_directory": str(artifacts_dir) if artifacts_dir.exists() else None,
                "execution_fingerprint": fingerprint,
                "target_package": config["target_package"],
                "suite_id": suite["suite_id"],
                "suite_version": suite["suite_version"],
                "suite_content_hash": suite_hash,
                "rubric_id": suite["rubric_id"],
                "rubric_version": suite["rubric_version"],
                "red_green": red_green,
                "red_green_results": red_green_results,
                "partition": partition,
                "configuration": {key: value for key, value in config.items() if key not in {"command_argv", "target_package_path"}},
                "results": results,
                "recommendation": recommendation,
            }
            report["candidates"] = [{key: value for key, value in candidate.items() if key != "content"} for candidate in candidates]
            report["summary"] = report_summary(status, results, recommendation)
            write_report(output_handle, report)
            return report
        finally:
            if attempt_handle is not None:
                attempt_handle.close()
            if output_handle is not None:
                output_handle.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="append", required=True, help="candidate identity and file or package path: ID=PATH")
    parser.add_argument("--suite", required=True, help="canonical JSON suite path")
    parser.add_argument("--partition-plan", required=True, help="canonical JSON development/holdout partition path")
    parser.add_argument("--config", required=True, help="JSON runtime and authorization configuration path")
    parser.add_argument("--output", required=True, help="new JSON report destination; existing files are never overwritten")
    parser.add_argument("--adapter", choices=("deterministic", "command"), default="deterministic")
    parser.add_argument("--run-id", help="stable caller-supplied run identifier")
    parser.add_argument("--preflight", action="store_true", help="validate inputs and print the execution fingerprint without running trials or writing output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run_comparison(args)
    except ConfigurationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_INVALID
    if args.preflight:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return EXIT_ACCEPTED
    print(report["summary"])
    if report["status"] != "complete":
        return EXIT_INCOMPLETE
    if report["recommendation"]["status"] != "selected":
        return EXIT_REJECTED
    return EXIT_ACCEPTED


if __name__ == "__main__":
    raise SystemExit(main())
