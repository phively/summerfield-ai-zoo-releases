#!/usr/bin/env python3
"""Validate a disposable, profile-bound destination exclusion packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Sequence


PACKET_VERSION = 1
POLICY_CONTEXT = "snapshot-validation"
MAX_EXCLUSIONS = 64
MAX_EXCLUSION_LENGTH = 512
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PROFILE_FIELDS = ("provider", "container", "id", "path", "repository_path", "sha256")


class DestinationPolicyError(ValueError):
    pass


def safe_relative_path(value: object, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise DestinationPolicyError(f"{field} must be a non-empty string")
    if "\\" in value:
        raise DestinationPolicyError(f"{field} must use forward slashes")
    parsed = PurePosixPath(value)
    reserved = {"CON", "PRN", "AUX", "NUL"}
    if (
        parsed.is_absolute()
        or value != parsed.as_posix()
        or not parsed.parts
        or ".." in parsed.parts
        or "." in parsed.parts
    ):
        raise DestinationPolicyError(f"unsafe {field}: {value}")
    for part in parsed.parts:
        stem = part.split(".", 1)[0].upper()
        if ":" in part or stem in reserved or (
            stem.startswith("COM") and stem[3:].isdigit()
        ) or (
            stem.startswith("LPT") and stem[3:].isdigit()
        ):
            raise DestinationPolicyError(f"unsafe {field}: {value}")
    return Path(*parsed.parts)


def normalize_exclusions(value: object) -> list[str]:
    """Normalize one optional trailing slash and reject ambiguous rule sets."""
    if not isinstance(value, list) or len(value) > MAX_EXCLUSIONS:
        raise DestinationPolicyError(
            f"exclusions must be a list of at most {MAX_EXCLUSIONS} directory paths"
        )
    normalized: list[str] = []
    component_sets: list[tuple[str, ...]] = []
    for number, raw in enumerate(value, start=1):
        if not isinstance(raw, str) or len(raw) > MAX_EXCLUSION_LENGTH:
            raise DestinationPolicyError(
                f"exclusion {number} must be a string no longer than {MAX_EXCLUSION_LENGTH} characters"
            )
        path_value = raw[:-1] if raw.endswith("/") else raw
        path = safe_relative_path(path_value, f"exclusion {number}")
        if any(character in path_value for character in "*?[]{}"):
            raise DestinationPolicyError(f"exclusion {number} must be a literal directory path")
        components = tuple(part.casefold() for part in path.parts)
        for previous in component_sets:
            if paths_overlap(previous, components):
                raise DestinationPolicyError("duplicate, nested, or case-colliding exclusions")
        normalized.append(path.as_posix())
        component_sets.append(components)
    return normalized


def _require_text(value: object, field: str, limit: int = 2048) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise DestinationPolicyError(f"{field} must be non-empty text no longer than {limit} characters")
    return value


def _profile(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != set(PROFILE_FIELDS):
        raise DestinationPolicyError(f"{field} must contain exactly {', '.join(PROFILE_FIELDS)}")
    result = {
        key: _require_text(value[key], f"{field}.{key}")
        for key in PROFILE_FIELDS
        if key != "sha256"
    }
    sha256 = value["sha256"]
    if not isinstance(sha256, str) or not SHA256.fullmatch(sha256):
        raise DestinationPolicyError(f"{field}.sha256 must be lowercase hexadecimal")
    result["sha256"] = sha256
    safe_relative_path(result["repository_path"], f"{field}.repository_path")
    return result


def _destination(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"repository", "branch"}:
        raise DestinationPolicyError(f"{field} must contain exactly repository and branch")
    return {
        key: _require_text(value[key], f"{field}.{key}", limit=512)
        for key in ("repository", "branch")
    }


def _record_paths(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise DestinationPolicyError(f"{field} must be a list")
    result: list[str] = []
    keys: set[str] = set()
    for number, item in enumerate(value, start=1):
        path = safe_relative_path(item, f"{field} item {number}")
        if path.parts[:1] != ("records",):
            raise DestinationPolicyError(f"{field} items must be under records/")
        key = path.as_posix().casefold()
        if key in keys:
            raise DestinationPolicyError(f"{field} contains duplicate or case-colliding paths")
        keys.add(key)
        result.append(path.as_posix())
    return result


def paths_overlap(left: Sequence[str], right: Sequence[str]) -> bool:
    left_folded = tuple(part.casefold() for part in left)
    right_folded = tuple(part.casefold() for part in right)
    size = min(len(left_folded), len(right_folded))
    return left_folded[:size] == right_folded[:size]


def validate_policy(
    packet: object,
    expectations: object,
    *,
    profile_bytes: bytes,
    indexed_profile_path: str,
    proposed_managed_paths: Sequence[str],
    manifest_relative_path: str,
) -> dict[str, object]:
    """Check a policy packet against independent expectations and staged bytes.

    The expectation packet must come from separately evidenced fresh profile and
    destination reads. This function binds those values; it cannot prove their
    freshness, faithful YAML extraction, user consent, or publication authority.
    """
    if not isinstance(packet, dict) or set(packet) != {
        "schema_version", "profile", "destination", "context", "exclusions"
    }:
        raise DestinationPolicyError("policy packet has an invalid shape")
    if type(packet.get("schema_version")) is not int or packet["schema_version"] != PACKET_VERSION:
        raise DestinationPolicyError("unsupported destination policy packet version")
    if not isinstance(expectations, dict) or set(expectations) != {
        "profile", "destination", "context", "managed_paths", "exclusions"
    }:
        raise DestinationPolicyError("policy expectations have an invalid shape")

    packet_profile = _profile(packet["profile"], "policy.profile")
    expected_profile = _profile(expectations["profile"], "expectations.profile")
    if packet_profile != expected_profile:
        raise DestinationPolicyError("policy profile differs from independent expectations")
    packet_destination = _destination(packet["destination"], "policy.destination")
    expected_destination = _destination(expectations["destination"], "expectations.destination")
    if packet_destination != expected_destination:
        raise DestinationPolicyError("policy destination differs from independent expectations")
    if packet.get("context") != POLICY_CONTEXT or expectations.get("context") != POLICY_CONTEXT:
        raise DestinationPolicyError("policy context must be snapshot-validation")

    normalized = normalize_exclusions(packet["exclusions"])
    expected_exclusions = normalize_exclusions(expectations["exclusions"])
    if sorted(normalized) != sorted(expected_exclusions):
        raise DestinationPolicyError(
            "policy exclusions differ from independent expectations"
        )

    if not isinstance(profile_bytes, bytes):
        raise DestinationPolicyError("staged profile bytes are unavailable")
    staged_hash = hashlib.sha256(profile_bytes).hexdigest()
    if staged_hash != packet_profile["sha256"]:
        raise DestinationPolicyError("staged profile bytes differ from the bound profile hash")
    indexed = safe_relative_path(indexed_profile_path, "indexed_profile_path").as_posix()
    if indexed != packet_profile["repository_path"]:
        raise DestinationPolicyError("indexed profile path differs from the bound profile")

    expected_paths = _record_paths(expectations["managed_paths"], "expectations.managed_paths")
    proposed_paths = _record_paths(list(proposed_managed_paths), "proposed_managed_paths")
    expected_keys = {path.casefold() for path in expected_paths}
    if any(path.casefold() not in expected_keys for path in proposed_paths):
        raise DestinationPolicyError("independent managed paths omit a proposed manifest record")

    manifest_path = safe_relative_path(manifest_relative_path, "manifest_relative_path").as_posix()
    protected_roots = ("records", "receipts", ".git")
    protected_files = ("README.md", "backup-index.json", manifest_path)
    protected_paths = [packet_profile["repository_path"], *protected_roots, *protected_files]
    for exclusion in normalized:
        exclusion_parts = tuple(exclusion.split("/"))
        for protected in protected_paths:
            protected_parts = tuple(protected.split("/"))
            if paths_overlap(exclusion_parts, protected_parts):
                raise DestinationPolicyError(
                    f"exclusion overlaps managed or operational path: {exclusion}"
                )

    return {
        "schema_version": PACKET_VERSION,
        "profile": packet_profile,
        "destination": packet_destination,
        "context": POLICY_CONTEXT,
        "exclusions": normalized,
    }


def _load_json(path: Path, field: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    except FileNotFoundError as exc:
        raise DestinationPolicyError(f"missing {field}: {path}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DestinationPolicyError(f"invalid {field}: {exc}") from exc


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON containing policy, expectations, and staged bindings")
    args = parser.parse_args(argv)
    try:
        value = _load_json(args.input, "input packet")
        if not isinstance(value, dict) or set(value) != {
            "policy", "expectations", "profile_file", "indexed_profile_path",
            "proposed_managed_paths", "manifest_relative_path",
        }:
            raise DestinationPolicyError("input packet has an invalid shape")
        profile_file = Path(value["profile_file"])
        profile_bytes = profile_file.read_bytes()
        result = validate_policy(
            value["policy"],
            value["expectations"],
            profile_bytes=profile_bytes,
            indexed_profile_path=value["indexed_profile_path"],
            proposed_managed_paths=value["proposed_managed_paths"],
            manifest_relative_path=value["manifest_relative_path"],
        )
    except (OSError, DestinationPolicyError, ValueError, TypeError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "valid", "capture_policy": result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
