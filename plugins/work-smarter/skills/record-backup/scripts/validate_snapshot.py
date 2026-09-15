#!/usr/bin/env python3
"""Validate an offline record-backup staging tree and its backup index."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SnapshotError(ValueError):
    """Raised when a staged snapshot is unsafe or inconsistent."""


def safe_relative_path(value: object, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise SnapshotError(f"{field} must be a non-empty string")
    if "\\" in value:
        raise SnapshotError(f"{field} must use forward slashes")
    parsed = PurePosixPath(value)
    reserved = {"CON", "PRN", "AUX", "NUL"}
    if parsed.is_absolute() or value != parsed.as_posix() or ".." in parsed.parts or "." in parsed.parts:
        raise SnapshotError(f"unsafe {field}: {value}")
    for part in parsed.parts:
        stem = part.split(".", 1)[0].upper()
        if ":" in part or stem in reserved or (
            stem.startswith("COM") and stem[3:].isdigit()
        ) or (
            stem.startswith("LPT") and stem[3:].isdigit()
        ):
            raise SnapshotError(f"unsafe {field}: {value}")
    return Path(*parsed.parts)


def digest(path: Path) -> tuple[int, str]:
    hasher = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            hasher.update(chunk)
    return size, hasher.hexdigest()


def validate(root: Path, manifest_path: Path) -> dict[str, object]:
    if not root.is_dir():
        raise SnapshotError(f"staging root is not a directory: {root}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SnapshotError(f"missing manifest: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"invalid JSON manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise SnapshotError("manifest schema_version must be 1")
    records = manifest.get("records")
    if not isinstance(records, list):
        raise SnapshotError("manifest records must be a list")

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

    actual_files: set[Path] = set()
    for path in root.rglob("*"):
        if not path.is_file() or path.resolve() == manifest_path.resolve():
            continue
        relative = path.relative_to(root)
        if relative.parts[:1] == ("receipts",):
            if len(relative.parts) != 2 or relative.suffix.lower() != ".json":
                raise SnapshotError(
                    "receipt files must be direct JSON files under receipts/: "
                    f"{relative.as_posix()}"
                )
            safe_relative_path(relative.as_posix(), "receipt_path")
            continue
        actual_files.add(relative)
    actual_keys = [path.as_posix().casefold() for path in actual_files]
    if len(actual_keys) != len(set(actual_keys)):
        raise SnapshotError("case-colliding stored file paths")
    if actual_files != expected or set(actual_keys) != expected_keys:
        extras = sorted(path.as_posix() for path in actual_files - expected)
        missing = sorted(path.as_posix() for path in expected - actual_files)
        details = []
        if extras:
            details.append(f"unindexed files: {', '.join(extras)}")
        if missing:
            details.append(f"missing files: {', '.join(missing)}")
        raise SnapshotError("; ".join(details))
    return {
        "record_count": len(records),
        "byte_count": sum(item["byte_size"] for item in summaries),
        "records": summaries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="staging tree containing backup-index.json")
    parser.add_argument("--manifest", type=Path, default=None, help="manifest path (default: ROOT/backup-index.json)")
    args = parser.parse_args(argv)
    manifest = args.manifest or args.root / "backup-index.json"
    try:
        summary = validate(args.root, manifest)
    except (OSError, SnapshotError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "valid", **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
