#!/usr/bin/env python3
"""Validate an offline record-backup staging tree and its backup index."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path


SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SnapshotError(ValueError):
    """Raised when a staged snapshot is unsafe or inconsistent."""


def _load_destination_policy():
    path = Path(__file__).with_name("destination_policy.py")
    spec = importlib.util.spec_from_file_location("record_backup_destination_policy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load destination policy helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


destination_policy_helper = _load_destination_policy()


def safe_relative_path(value: object, field: str) -> Path:
    try:
        return destination_policy_helper.safe_relative_path(value, field)
    except destination_policy_helper.DestinationPolicyError as exc:
        raise SnapshotError(str(exc)) from exc


def digest(path: Path) -> tuple[int, str]:
    hasher = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            hasher.update(chunk)
    return size, hasher.hexdigest()


def _read_json(path: Path, field: str) -> object:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=destination_policy_helper.unique_object,
        )
    except FileNotFoundError as exc:
        raise SnapshotError(f"missing {field}: {path}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise SnapshotError(f"invalid {field}: {exc}") from exc


def _tree_paths(root: Path):
    def onerror(error: OSError) -> None:
        raise SnapshotError(f"could not inspect destination tree: {error}") from error

    try:
        for directory, directories, files in os.walk(
            root, topdown=True, followlinks=False, onerror=onerror
        ):
            current = Path(directory)
            for name in list(directories):
                path = current / name
                if path.is_symlink():
                    raise SnapshotError(f"symlinks are not supported: {path.relative_to(root)}")
                if not path.is_dir():
                    raise SnapshotError(f"unsupported destination entry: {path.relative_to(root)}")
                yield path
            for name in files:
                path = current / name
                if path.is_symlink():
                    raise SnapshotError(f"symlinks are not supported: {path.relative_to(root)}")
                if not path.is_file():
                    raise SnapshotError(f"unsupported destination entry: {path.relative_to(root)}")
                yield path
    except OSError as exc:
        raise SnapshotError(f"could not inspect destination tree: {exc}") from exc


def validate(
    root: Path,
    manifest_path: Path,
    *,
    destination_policy: object | None = None,
    policy_expectations: object | None = None,
) -> dict[str, object]:
    if root.is_symlink() or not root.is_dir():
        raise SnapshotError(f"staging root is not a directory: {root}")
    try:
        manifest = _read_json(manifest_path, "manifest")
    except OSError as exc:
        raise SnapshotError(f"could not read manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise SnapshotError("manifest schema_version must be 1")
    records = manifest.get("records")
    if not isinstance(records, list):
        raise SnapshotError("manifest records must be a list")
    operational = "operational_layout" in manifest
    if operational and (type(manifest["operational_layout"]) is not int or manifest["operational_layout"] != 1):
        raise SnapshotError("unsupported operational_layout")
    if operational:
        profile_path = manifest.get("profile_repository_path")
        safe_relative_path(profile_path, "profile_repository_path")
        profiles = [r for r in records if isinstance(r, dict) and r.get("repository_path") == profile_path]
        if len(profiles) != 1 or profiles[0].get("classification") != "configuration":
            raise SnapshotError("operational layout requires one indexed configuration profile")
        if Path(profile_path).suffix.lower() not in {".yaml", ".yml"}:
            raise SnapshotError("configuration profile must retain its YAML extension")
    if destination_policy is None and policy_expectations is not None:
        raise SnapshotError("policy expectations require a destination policy packet")
    if destination_policy is not None and policy_expectations is None:
        raise SnapshotError("destination policy packet requires independent expectations")

    expected: set[Path] = set()
    expected_keys: set[str] = set()
    source_identities: set[tuple[str, str, str]] = set()
    summaries: list[dict[str, object]] = []
    required = (
        "repository_path", "source_provider", "source_container", "source_id",
        "source_path", "owner", "classification", "byte_size", "sha256",
    )
    for number, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise SnapshotError(f"record {number} is not an object")
        missing = [field for field in required if field not in record]
        if missing:
            raise SnapshotError(f"record {number} missing: {', '.join(missing)}")
        relative = safe_relative_path(record["repository_path"], "repository_path")
        if relative.parts[:1] != ("records",):
            raise SnapshotError("repository_path must be under records/")
        if relative == Path("backup-index.json"):
            raise SnapshotError("records may not contain the manifest")
        relative_key = relative.as_posix().casefold()
        if relative in expected or relative_key in expected_keys:
            raise SnapshotError(f"duplicate repository_path: {relative.as_posix()}")
        expected.add(relative)
        expected_keys.add(relative_key)
        source_provider = record["source_provider"]
        source_container = record["source_container"]
        source_id = record["source_id"]
        if not isinstance(source_provider, str) or not source_provider:
            raise SnapshotError(f"record {number} source_provider must be non-empty")
        if not isinstance(source_container, str) or not source_container:
            raise SnapshotError(f"record {number} source_container must be non-empty")
        if not isinstance(source_id, str) or not source_id:
            raise SnapshotError(f"record {number} source_id must be non-empty")
        source_identity = (source_provider, source_container, source_id)
        if source_identity in source_identities:
            raise SnapshotError(
                "duplicate source identity: "
                f"({source_provider}, {source_container}, {source_id})"
            )
        source_identities.add(source_identity)
        if not isinstance(record["byte_size"], int) or record["byte_size"] < 0:
            raise SnapshotError(f"record {number} byte_size must be a non-negative integer")
        sha256 = record["sha256"]
        if not isinstance(sha256, str) or not SHA256.fullmatch(sha256):
            raise SnapshotError(f"record {number} sha256 must be lowercase hexadecimal")
        path = root / relative
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError as exc:
            raise SnapshotError(f"stored record escapes staging root: {relative.as_posix()}") from exc
        if not path.is_file() or path.is_symlink():
            raise SnapshotError(f"missing stored record: {relative.as_posix()}")
        size, actual = digest(path)
        if size != record["byte_size"] or actual != sha256:
            raise SnapshotError(f"content mismatch: {relative.as_posix()}")
        summaries.append({"path": relative.as_posix(), "byte_size": size, "sha256": actual})

    normalized_exclusions: list[tuple[str, ...]] = []
    if destination_policy is not None:
        if not operational:
            raise SnapshotError("destination policy requires an indexed operational profile")
        profile_repository_path = manifest["profile_repository_path"]
        profile_records = [record for record in records if record["repository_path"] == profile_repository_path]
        if len(profile_records) != 1:
            raise SnapshotError("destination policy requires one indexed profile record")
        profile_record = profile_records[0]
        try:
            helper_profile = policy_expectations.get("profile") if isinstance(policy_expectations, dict) else None
            if not isinstance(helper_profile, dict):
                raise destination_policy_helper.DestinationPolicyError("expectations.profile must be an object")
            identity_fields = {
                "provider": "source_provider",
                "container": "source_container",
                "id": "source_id",
                "path": "source_path",
                "repository_path": "repository_path",
            }
            if any(profile_record.get(record_field) != helper_profile.get(profile_field)
                   for profile_field, record_field in identity_fields.items()):
                raise destination_policy_helper.DestinationPolicyError(
                    "indexed profile record identity differs from independent expectations"
                )
            profile_bytes = (root / Path(profile_repository_path)).read_bytes()
            try:
                manifest_relative_path = manifest_path.resolve().relative_to(root.resolve()).as_posix()
            except ValueError:
                manifest_relative_path = "backup-index.json"
            capture_policy = destination_policy_helper.validate_policy(
                destination_policy,
                policy_expectations,
                profile_bytes=profile_bytes,
                indexed_profile_path=profile_repository_path,
                proposed_managed_paths=[record["repository_path"] for record in records],
                manifest_relative_path=manifest_relative_path,
            )
        except (destination_policy_helper.DestinationPolicyError, OSError, AttributeError, TypeError) as exc:
            raise SnapshotError(f"invalid destination policy: {exc}") from exc
        if manifest.get("capture_policy") != capture_policy:
            raise SnapshotError("manifest capture_policy differs from the validated destination policy")
        normalized_exclusions = [tuple(path.split("/")) for path in capture_policy["exclusions"]]
        for components in normalized_exclusions:
            exclusion_path = root.joinpath(*components)
            try:
                resolved = exclusion_path.resolve()
                resolved.relative_to(root.resolve())
            except (OSError, ValueError) as exc:
                raise SnapshotError(
                    f"exclusion path escapes staging root: {'/'.join(components)}"
                ) from exc
            if exclusion_path.is_symlink():
                raise SnapshotError(f"symlinks are not supported: {'/'.join(components)}")
            if exclusion_path.exists() and not exclusion_path.is_dir():
                raise SnapshotError(f"exclusion root is not a directory: {'/'.join(components)}")

    actual_files: set[Path] = set()
    actual_paths_by_key: dict[str, str] = {}
    try:
        manifest_resolved = manifest_path.resolve()
    except OSError as exc:
        raise SnapshotError(f"could not resolve manifest path: {exc}") from exc
    for path in _tree_paths(root):
        relative = path.relative_to(root)
        relative_value = relative.as_posix()
        relative_key = relative_value.casefold()
        previous = actual_paths_by_key.setdefault(relative_key, relative_value)
        if previous != relative_value:
            raise SnapshotError("case-colliding stored paths")
        try:
            path.resolve().relative_to(root.resolve())
        except (OSError, ValueError) as exc:
            raise SnapshotError(f"stored path escapes staging root: {relative_value}") from exc
        if path.is_dir():
            continue
        if not path.is_file() or path.resolve() == manifest_resolved:
            continue
        if relative == Path("README.md"):
            continue
        if relative.parts[:1] == ("receipts",):
            if len(relative.parts) != 2 or relative.suffix.lower() != ".json":
                raise SnapshotError(
                    "receipt files must be direct JSON files under receipts/: "
                    f"{relative.as_posix()}"
                )
            safe_relative_path(relative.as_posix(), "receipt_path")
            continue
        actual_files.add(relative)
    coverage_files = {
        path for path in actual_files
        if not any(path.parts[:len(exclusion)] == exclusion for exclusion in normalized_exclusions)
    }
    coverage_keys = {path.as_posix().casefold() for path in coverage_files}
    if coverage_files != expected or coverage_keys != expected_keys:
        extras = sorted(path.as_posix() for path in coverage_files - expected)
        missing = sorted(path.as_posix() for path in expected - actual_files)
        details = []
        if extras:
            details.append(f"unindexed files: {', '.join(extras)}")
        if missing:
            details.append(f"missing files: {', '.join(missing)}")
        raise SnapshotError("; ".join(details))
    if operational or (root / "README.md").exists() or "legacy_receipts" in manifest:
        spec = importlib.util.spec_from_file_location("backup_reporting", Path(__file__).with_name("reporting.py"))
        reporting = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reporting)
        try:
            reporting.process(root)
        except (ValueError, OSError) as exc:
            raise SnapshotError(f"invalid operational files: {exc}") from exc
    return {
        "record_count": len(records),
        "byte_count": sum(item["byte_size"] for item in summaries),
        "records": summaries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="staging tree containing backup-index.json")
    parser.add_argument("--manifest", type=Path, default=None, help="manifest path (default: ROOT/backup-index.json)")
    parser.add_argument("--destination-policy", type=Path, default=None, help="disposable JSON policy packet")
    parser.add_argument("--policy-expectations", type=Path, default=None, help="independent profile, destination, and managed-path bindings")
    args = parser.parse_args(argv)
    manifest = args.manifest or args.root / "backup-index.json"
    try:
        if (args.destination_policy is None) != (args.policy_expectations is None):
            raise SnapshotError("--destination-policy and --policy-expectations must be supplied together")
        packet = _read_json(args.destination_policy, "destination policy packet") if args.destination_policy else None
        expectations = _read_json(args.policy_expectations, "policy expectations") if args.policy_expectations else None
        summary = validate(
            args.root,
            manifest,
            destination_policy=packet,
            policy_expectations=expectations,
        )
    except (OSError, SnapshotError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "valid", **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
