#!/usr/bin/env python3
"""Compare protected destination inventories across a backup run."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
MODE_TYPES = {
    "040000": "tree",
    "100644": "blob",
    "100755": "blob",
    "120000": "blob",
    "160000": "commit",
}
MODES = set(MODE_TYPES)
KINDS = set(MODE_TYPES.values())


def _load_policy_helper():
    path = Path(__file__).with_name("destination_policy.py")
    spec = importlib.util.spec_from_file_location("record_backup_destination_policy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load destination policy helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy_helper = _load_policy_helper()


class PreservationError(ValueError):
    pass


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PreservationError(f"{field} must be non-empty text")
    return value


def _path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise PreservationError(f"{field} must be a safe repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix() or any(part in {"", ".", ".."} for part in path.parts):
        raise PreservationError(f"{field} must be a safe repository-relative path")
    return path.as_posix()


def _commit(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise PreservationError(f"{field} must be a full lowercase Git object ID")
    return value


def _destination(value: object, expected: dict[str, str], field: str) -> None:
    if not isinstance(value, dict) or set(value) != {"repository", "branch"}:
        raise PreservationError(f"{field}.destination must contain repository and branch")
    if value != expected:
        raise PreservationError(f"{field} is bound to a different destination")


def _inventory(value: object, field: str) -> dict[str, dict[str, str]]:
    if not isinstance(value, list):
        raise PreservationError(f"{field}.inventory must be a list")
    result: dict[str, dict[str, str]] = {}
    folded_spelling: dict[str, str] = {}
    for number, entry in enumerate(value, start=1):
        label = f"{field}.inventory[{number}]"
        if not isinstance(entry, dict) or set(entry) != {"path", "mode", "type", "object_id"}:
            raise PreservationError(f"{label} must contain path, mode, type, and object_id")
        path = _path(entry["path"], f"{label}.path")
        mode = entry["mode"]
        kind = entry["type"]
        object_id = entry["object_id"]
        if mode not in MODES or kind not in KINDS or not isinstance(object_id, str) or not SHA.fullmatch(object_id):
            raise PreservationError(f"{label} has an invalid Git mode, type, or object ID")
        if MODE_TYPES.get(mode) != kind:
            raise PreservationError(f"{label} has an invalid Git mode/type pair")
        if path in result:
            raise PreservationError(f"{field}.inventory has duplicate or case-colliding paths")
        parts = PurePosixPath(path).parts
        for depth in range(1, len(parts) + 1):
            prefix = "/".join(parts[:depth])
            prefix_key = prefix.casefold()
            previous = folded_spelling.setdefault(prefix_key, prefix)
            if previous != prefix:
                message = (
                    "duplicate or case-colliding paths" if depth == len(parts)
                    else "case-colliding directory paths"
                )
                raise PreservationError(f"{field}.inventory has {message}")
        result[path] = {"mode": mode, "type": kind, "object_id": object_id}
    for path in result:
        parent = PurePosixPath(path).parent
        while parent.as_posix() != ".":
            parent_entry = result.get(parent.as_posix())
            if parent_entry is None or parent_entry["type"] != "tree":
                raise PreservationError(f"{field}.inventory is missing a parent tree for {path}")
            parent = parent.parent
    return result


def _git_tree_hash(children: list[tuple[str, dict[str, str]]], algorithm: str) -> str:
    ordered = sorted(
        children,
        key=lambda item: item[0].encode("utf-8") + (b"/" if item[1]["type"] == "tree" else b""),
    )
    body = bytearray()
    for name, entry in ordered:
        mode = "40000" if entry["mode"] == "040000" else entry["mode"]
        body.extend(mode.encode("ascii"))
        body.extend(b" ")
        body.extend(name.encode("utf-8"))
        body.extend(b"\0")
        body.extend(bytes.fromhex(entry["object_id"]))
    header = b"tree " + str(len(body)).encode("ascii") + b"\0"
    return hashlib.new(algorithm, header + body).hexdigest()


def _check_tree_inventory(
    inventory: dict[str, dict[str, str]], tree_id: str, field: str
) -> None:
    algorithm = {40: "sha1", 64: "sha256"}[len(tree_id)]
    if any(len(entry["object_id"]) != len(tree_id) for entry in inventory.values()):
        raise PreservationError(f"{field}.inventory object IDs do not match {field}.tree_id format")

    children_by_parent: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for path, entry in inventory.items():
        parsed = PurePosixPath(path)
        children_by_parent.setdefault(parsed.parent.as_posix(), []).append((parsed.name, entry))

    tree_paths = sorted(
        (path for path, entry in inventory.items() if entry["type"] == "tree"),
        key=lambda path: len(PurePosixPath(path).parts),
        reverse=True,
    )
    for path in tree_paths:
        actual = _git_tree_hash(children_by_parent.get(path, []), algorithm)
        if actual != inventory[path]["object_id"]:
            raise PreservationError(
                f"{field}.inventory is incomplete or inconsistent with {field}.tree_id at {path}"
            )

    actual_root = _git_tree_hash(children_by_parent.get(".", []), algorithm)
    if actual_root != tree_id:
        raise PreservationError(f"{field}.inventory is incomplete or inconsistent with {field}.tree_id")


def _protected_view(inventory: dict[str, dict[str, str]], roots: list[str]) -> dict[str, dict[str, str]]:
    return {
        path: value
        for path, value in inventory.items()
        if any(path == root or path.startswith(root + "/") for root in roots)
    }


def _check_protected_roots(inventory: dict[str, dict[str, str]], roots: list[str], field: str) -> None:
    for root in roots:
        entry = inventory.get(root)
        if entry is not None and entry["type"] != "tree":
            raise PreservationError(f"{field} protected root is not a directory: {root}")


def _compare(expected: dict[str, dict[str, str]], actual: dict[str, dict[str, str]], label: str) -> None:
    if expected == actual:
        return
    missing = sorted(set(expected) - set(actual))
    added = sorted(set(actual) - set(expected))
    changed = sorted(path for path in set(expected) & set(actual) if expected[path] != actual[path])
    details = []
    if missing:
        details.append("removed: " + ", ".join(missing))
    if added:
        details.append("added: " + ", ".join(added))
    if changed:
        details.append("changed: " + ", ".join(changed))
    raise PreservationError(f"protected destination changed at {label} ({'; '.join(details)})")


def check_preservation(packet: object) -> dict[str, Any]:
    """Validate and compare independently collected Git tree inventories.

    This checks evidence consistency and equality. It cannot authenticate that
    inventories came from independent provider reads; callers must retain those
    reads and bind their repository, ref, commit and tree identities here.
    """
    if not isinstance(packet, dict) or set(packet) != {
        "schema_version", "destination", "protected_roots", "baseline", "staged", "publications"
    }:
        raise PreservationError("preservation packet has an invalid shape")
    if type(packet.get("schema_version")) is not int or packet["schema_version"] != 1:
        raise PreservationError("unsupported preservation packet version")
    destination = packet["destination"]
    if not isinstance(destination, dict) or set(destination) != {"repository", "branch"}:
        raise PreservationError("destination must contain repository and branch")
    destination = {key: _text(destination[key], f"destination.{key}") for key in ("repository", "branch")}

    raw_roots = packet["protected_roots"]
    if not isinstance(raw_roots, list) or not raw_roots:
        raise PreservationError("protected_roots must be a non-empty list")
    try:
        roots = policy_helper.normalize_exclusions(raw_roots)
    except policy_helper.DestinationPolicyError as exc:
        raise PreservationError(f"invalid protected roots: {exc}") from exc
    for root in roots:
        path = PurePosixPath(root)
        if any(
            policy_helper.paths_overlap(path.parts, PurePosixPath(protected).parts)
            for protected in ("records", "receipts", ".git", "README.md", "backup-index.json")
        ):
            raise PreservationError(f"protected root overlaps an operational path: {root}")

    baseline = packet["baseline"]
    staged = packet["staged"]
    if not isinstance(baseline, dict) or set(baseline) != {
        "destination", "commit", "tree_id", "evidence_id", "inventory"
    }:
        raise PreservationError("baseline evidence has an invalid shape")
    _destination(baseline["destination"], destination, "baseline")
    base_commit = _commit(baseline["commit"], "baseline.commit")
    base_tree = _commit(baseline["tree_id"], "baseline.tree_id")
    _text(baseline["evidence_id"], "baseline.evidence_id")
    base_inventory = _inventory(baseline["inventory"], "baseline")
    _check_tree_inventory(base_inventory, base_tree, "baseline")
    _check_protected_roots(base_inventory, roots, "baseline")
    protected_base = _protected_view(base_inventory, roots)

    if not isinstance(staged, dict) or set(staged) != {
        "destination", "base_commit", "tree_id", "evidence_id", "inventory"
    }:
        raise PreservationError("staged evidence has an invalid shape")
    _destination(staged["destination"], destination, "staged")
    if _commit(staged["base_commit"], "staged.base_commit") != base_commit:
        raise PreservationError("staged evidence uses a stale or different baseline")
    staged_tree = _commit(staged["tree_id"], "staged.tree_id")
    _text(staged["evidence_id"], "staged.evidence_id")
    staged_inventory = _inventory(staged["inventory"], "staged")
    _check_tree_inventory(staged_inventory, staged_tree, "staged")
    _check_protected_roots(staged_inventory, roots, "staged")
    _compare(protected_base, _protected_view(staged_inventory, roots), "staging")

    publications = packet["publications"]
    if not isinstance(publications, list):
        raise PreservationError("publications must be a list")
    phases = [item.get("phase") if isinstance(item, dict) else None for item in publications]
    if phases not in ([], ["content"], ["content", "operational"]):
        raise PreservationError("publication evidence must include content before optional operational readback")
    previous_commit = base_commit
    previous_tree = baseline["tree_id"]
    for number, publication in enumerate(publications, start=1):
        field = f"publications[{number}]"
        if not isinstance(publication, dict) or set(publication) != {
            "phase", "destination", "parent_commit", "commit", "tree_id", "evidence_id", "inventory"
        }:
            raise PreservationError(f"{field} evidence has an invalid shape")
        phase = _text(publication["phase"], f"{field}.phase")
        if phase not in {"content", "operational"}:
            raise PreservationError(f"{field}.phase must be content or operational")
        _destination(publication["destination"], destination, field)
        if _commit(publication["parent_commit"], f"{field}.parent_commit") != previous_commit:
            raise PreservationError(f"{field} does not extend the independently checked destination head")
        current_commit = _commit(publication["commit"], f"{field}.commit")
        current_tree = _commit(publication["tree_id"], f"{field}.tree_id")
        if current_commit == previous_commit and current_tree != previous_tree:
            raise PreservationError(f"{field} changes the tree without advancing the destination commit")
        _text(publication["evidence_id"], f"{field}.evidence_id")
        inventory = _inventory(publication["inventory"], field)
        _check_tree_inventory(inventory, current_tree, field)
        _check_protected_roots(inventory, roots, field)
        _compare(protected_base, _protected_view(inventory, roots), phase)
        previous_commit = current_commit
        previous_tree = current_tree

    checked_phases = ["staging", *phases]
    status = (
        "preserved" if phases == ["content", "operational"]
        else "content_preserved" if phases == ["content"]
        else "staged_preserved"
    )

    return {
        "status": status,
        "destination": destination,
        "baseline_commit": base_commit,
        "protected_roots": roots,
        "checked_phases": checked_phases,
        "publication_commit": previous_commit,
        "limitations": ["inventory equality does not authenticate evidence provenance"],
    }


def _load_packet(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=policy_helper.unique_object)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise PreservationError(f"invalid preservation input: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON packet containing pinned inventory evidence")
    args = parser.parse_args(argv)
    try:
        result = check_preservation(_load_packet(Path(args.input)))
    except (PreservationError, TypeError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
