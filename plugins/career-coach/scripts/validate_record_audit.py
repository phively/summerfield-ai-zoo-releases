#!/usr/bin/env python3
"""Validate a staged Career Coach record audit without modifying either state."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


PROTECTED_KINDS = {
    "active_fact",
    "exact_constraint",
    "numeric_rule",
    "provenance",
    "stable_id",
    "pointer",
    "historical_item",
    "authority",
    "evidence_class",
    "uncertainty",
}
EXACT_KINDS = {
    "exact_constraint",
    "numeric_rule",
    "provenance",
    "stable_id",
    "authority",
    "evidence_class",
}
DISPOSABLE_KINDS = {
    "formatting",
    "incorrect",
    "redundant_wording",
    "transient",
    "valueless_duplicate",
}
DISPOSITIONS = {"retained", "moved", "reworded", "updated", "archived", "removed"}


class AuditError(ValueError):
    """Raised when a ledger does not prove a safe staged change."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def markdown_inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(root.rglob("*.md"))
        if path.is_file()
    ]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def _safe_file(root: Path, relative: str) -> Path:
    _require(bool(relative), "Item path must not be empty")
    path = (root / relative).resolve()
    resolved_root = root.resolve()
    _require(path == resolved_root or resolved_root in path.parents, f"Path escapes audit root: {relative}")
    _require(path.is_file(), f"Missing audited file: {relative}")
    return path


def _validate_file_inventory(root: Path, supplied: Any, label: str) -> None:
    _require(isinstance(supplied, list), f"{label}_files must be a list")
    _require(supplied == markdown_inventory(root), f"{label}_files does not match the complete Markdown inventory")


def _index_items(root: Path, supplied: Any, label: str) -> dict[str, dict[str, Any]]:
    _require(isinstance(supplied, list) and supplied, f"{label}_items must be a non-empty list")
    indexed: dict[str, dict[str, Any]] = {}
    stable_ids: set[tuple[str, str]] = set()
    for item in supplied:
        _require(isinstance(item, dict), f"Every {label} item must be an object")
        item_id = item.get("id")
        kind = item.get("kind")
        text = item.get("text")
        relative = item.get("path")
        _require(isinstance(item_id, str) and item_id, f"{label} item has no id")
        _require(item_id not in indexed, f"Duplicate {label} item id: {item_id}")
        _require(kind in PROTECTED_KINDS | DISPOSABLE_KINDS, f"Unknown item kind for {item_id}: {kind}")
        _require(isinstance(text, str) and text, f"{label} item has no text: {item_id}")
        _require(isinstance(relative, str), f"{label} item has no path: {item_id}")
        contents = _safe_file(root, relative).read_text(encoding="utf-8")
        _require(text in contents, f"{label} item text not found in {relative}: {item_id}")
        if kind == "stable_id":
            namespace = item.get("namespace")
            _require(isinstance(namespace, str) and namespace, f"Stable ID has no namespace: {item_id}")
            key = (namespace, text)
            _require(key not in stable_ids, f"Duplicate stable ID in namespace {namespace}: {text}")
            stable_ids.add(key)
        if kind == "pointer":
            target_path = item.get("target_path")
            target_text = item.get("target_text")
            _require(isinstance(target_path, str), f"Pointer has no target_path: {item_id}")
            _require(isinstance(target_text, str) and target_text, f"Pointer has no target_text: {item_id}")
            target = _safe_file(root, target_path).read_text(encoding="utf-8")
            _require(target_text in target, f"Broken pointer target for {item_id}: {target_path}")
        indexed[item_id] = item
    return indexed


def validate_audit(before_root: Path, after_root: Path, ledger: dict[str, Any]) -> None:
    """Validate complete inventories, protected meanings, identities, and relationships."""
    _require(ledger.get("schema_version") == 1, "Unsupported schema_version")
    for review in ("current_state_review", "history_reconstruction_review", "cross_authority_review"):
        _require(ledger.get(review) == "passed", f"Audit lacks passed {review}")
    _validate_file_inventory(before_root, ledger.get("before_files"), "before")
    _validate_file_inventory(after_root, ledger.get("after_files"), "after")
    before = _index_items(before_root, ledger.get("before_items"), "before")
    after = _index_items(after_root, ledger.get("after_items"), "after")

    decisions = ledger.get("decisions")
    _require(isinstance(decisions, list), "decisions must be a list")
    by_before: dict[str, dict[str, Any]] = {}
    referenced_after: set[str] = set()
    for decision in decisions:
        _require(isinstance(decision, dict), "Every decision must be an object")
        before_id = decision.get("before_id")
        disposition = decision.get("disposition")
        after_ids = decision.get("after_ids")
        _require(before_id in before, f"Decision refers to unknown before item: {before_id}")
        _require(before_id not in by_before, f"Multiple decisions for before item: {before_id}")
        _require(disposition in DISPOSITIONS, f"Invalid disposition for {before_id}: {disposition}")
        _require(isinstance(after_ids, list), f"after_ids must be a list for {before_id}")
        _require(all(item_id in after for item_id in after_ids), f"Unknown after item for {before_id}")
        by_before[before_id] = decision
        referenced_after.update(after_ids)

        source = before[before_id]
        targets = [after[item_id] for item_id in after_ids]
        justification = decision.get("justification")
        if disposition in {"retained", "moved"}:
            _require(targets, f"{disposition} item has no target: {before_id}")
            _require(
                any(target["kind"] == source["kind"] and target["text"] == source["text"] for target in targets),
                f"{disposition} item changed kind or text: {before_id}",
            )
        elif disposition == "reworded":
            _require(source["kind"] not in EXACT_KINDS, f"Exact item cannot be reworded: {before_id}")
            _require(targets, f"Reworded item has no target: {before_id}")
            _require(decision.get("semantic_review") == "passed", f"Reworded item lacks semantic review: {before_id}")
            _require(isinstance(justification, str) and justification, f"Reworded item lacks justification: {before_id}")
        elif disposition == "updated":
            _require(targets, f"Updated item has no target: {before_id}")
            _require(decision.get("authorized") is True, f"Updated item lacks authorization: {before_id}")
            _require(isinstance(justification, str) and justification, f"Updated item lacks justification: {before_id}")
        elif disposition == "archived":
            _require(targets, f"Archived item has no target: {before_id}")
            _require(
                any(target["kind"] == "historical_item" and target["text"] == source["text"] for target in targets),
                f"Archived item was not preserved exactly in history: {before_id}",
            )
        elif disposition == "removed":
            _require(source["kind"] in DISPOSABLE_KINDS, f"Protected item cannot be removed: {before_id}")
            _require(not targets, f"Removed item still has targets: {before_id}")
            _require(isinstance(justification, str) and justification, f"Removed item lacks justification: {before_id}")

    _require(set(by_before) == set(before), "Every before item must have exactly one decision")
    new_after = ledger.get("new_after_ids", [])
    _require(isinstance(new_after, list), "new_after_ids must be a list")
    _require(len(new_after) == len(set(new_after)), "new_after_ids contains duplicates")
    _require(all(item_id in after for item_id in new_after), "new_after_ids contains an unknown item")
    _require(referenced_after.isdisjoint(new_after), "An after item cannot be both derived and new")
    _require(referenced_after | set(new_after) == set(after), "Every after item must have an origin or be authorized new")
    if new_after:
        justification = ledger.get("new_items_justification")
        _require(isinstance(justification, str) and justification, "New items require a justification")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before_root", type=Path)
    parser.add_argument("after_root", type=Path)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args(argv)
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    validate_audit(args.before_root, args.after_root, ledger)
    print("PASS Career Coach audit: inventories, ledger, identities, pointers, and reviews validated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, json.JSONDecodeError, OSError) as exc:
        print(f"FAIL Career Coach audit: {exc}", file=sys.stderr)
        raise SystemExit(1)
