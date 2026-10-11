#!/usr/bin/env python3
"""Validate backup receipts and render/check the destination README status block."""

from __future__ import annotations

import argparse
import difflib
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

START = "<!-- record-backup:start -->"
END = "<!-- record-backup:end -->"


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("receipt timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("receipt timestamp requires a timezone")
    return result


def validate_receipt(value, stem, *, discovery_keys=None):
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("receipt schema_version must be 1")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", stem) or value.get("run_id") != stem:
        raise ValueError("receipt run_id must match its safe filename")
    if value.get("mode") not in {"daily", "weekly", "manual", "restore"}:
        raise ValueError("invalid receipt mode")
    if value.get("status") not in {"verified", "verified-no-change", "incomplete", "failed"}:
        raise ValueError("invalid receipt status")
    if timestamp(value.get("ended_at")) < timestamp(value.get("started_at")):
        raise ValueError("receipt ends before it starts")
    for field in ("scope", "exclusions", "history_coverage"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f"receipt requires {field}")
    lists = ["coverage_limits"]
    if value["mode"] == "weekly":
        lists += ["repaired_items", "unrecoverable_gaps", "source_access_limits"]
        if not isinstance(value.get("restore_test"), str) or not value["restore_test"].strip():
            raise ValueError("weekly receipt requires restore_test")
    for field in lists:
        if not isinstance(value.get(field), list) or any(not isinstance(item, str) for item in value[field]):
            raise ValueError(f"receipt requires string list {field}")
    for field, keys in (("counts", ("records", "bytes", "changed", "deleted")),
                        ("discovery", discovery_keys if discovery_keys is not None else
                         ("listing_calls", "content_reads", "duplicates", "pointer_cycles", "retries"))):
        obj = value.get(field)
        if not isinstance(obj, dict) or any(type(obj.get(key)) is not int or obj[key] < 0 for key in keys):
            raise ValueError(f"receipt requires nonnegative integer {field}")
    checks = value.get("checks")
    if not isinstance(checks, dict) or not {"local_snapshot", "remote_snapshot"} <= checks.keys() or any(type(v) is not bool for v in checks.values()):
        raise ValueError("receipt requires boolean snapshot checks")
    sha = value.get("snapshot_commit")
    if "snapshot_commit" not in value or (sha is not None and (not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha))):
        raise ValueError("receipt requires full snapshot SHA or null")
    published = value.get("published_content_commit")
    if "published_content_commit" in value and (not isinstance(published, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", published)):
        raise ValueError("published_content_commit requires a full Git SHA")
    if bool(sha) != checks["remote_snapshot"]:
        raise ValueError("snapshot SHA and remote verification must agree")
    if type(value.get("current_state_complete")) is not bool:
        raise ValueError("receipt requires current_state_complete")
    verified = value["status"] in {"verified", "verified-no-change"}
    if verified and (not sha or not all(checks[k] for k in ("local_snapshot", "remote_snapshot")) or not value["current_state_complete"]):
        raise ValueError("verified receipt requires complete, checked snapshot")
    if verified and value["mode"] == "weekly" and any(
        checks.get(key) is False for key in ("full_latest_restore", "full_older_restore")
    ):
        raise ValueError("verified weekly receipt cannot contain a failed recovery drill")
    if not verified and value["current_state_complete"]:
        raise ValueError("failed/incomplete receipt cannot claim completeness")
    if value["status"] == "verified-no-change" and (value["counts"]["changed"] or value["counts"]["deleted"]):
        raise ValueError("no-change receipt contains changes")
    return value


def legacy_entries(root):
    """Read the explicit historical-byte allowlist; never infer it from failures."""
    index = root / "backup-index.json"
    if index.is_symlink():
        raise ValueError("backup index must not be a symlink")
    manifest = json.loads(index.read_text(encoding="utf-8")) if index.exists() else {}
    if not isinstance(manifest, dict):
        raise ValueError("backup index must be an object")
    entries = manifest.get("legacy_receipts", [])
    if not isinstance(entries, list):
        raise ValueError("legacy_receipts must be a list")
    result = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("legacy receipt entry must be an object")
        path = entry.get("repository_path")
        if not isinstance(path, str) or not re.fullmatch(r"receipts/[A-Za-z0-9][A-Za-z0-9_-]*\.json", path):
            raise ValueError("legacy receipt requires a direct safe receipt path")
        key = path.casefold()
        if key in result:
            raise ValueError("duplicate legacy receipt path")
        if type(entry.get("byte_size")) is not int or entry["byte_size"] < 0:
            raise ValueError("legacy receipt requires byte_size")
        if not isinstance(entry.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError("legacy receipt requires sha256")
        if not isinstance(entry.get("provenance"), str) or not entry["provenance"].strip():
            raise ValueError("legacy receipt requires reviewed provenance")
        result[key] = entry
    return result


def validate_legacy_receipt(value, stem):
    """Recognize inspected historical formats without translating their claims."""
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("unsupported legacy receipt schema")
    mode = value.get("mode")
    if mode == "daily-missed-recovery":
        # The inspected historical variant may use its original discovery counters.
        discovery = value.get("discovery")
        keys = ("listing_pages", "inventory_items", "configured_records", "stable_rechecks", "pointer_cycles") if (
            isinstance(discovery, dict) and "listing_pages" in discovery
        ) else None
        validate_receipt(value | {"mode": "daily"}, stem, discovery_keys=keys)
        return
    prefix = {"daily-sync": "daily-", "weekly-reconciliation": "weekly-"}.get(mode)
    if prefix is None or "status" in value or stem != prefix + str(value.get("run_id")):
        raise ValueError("unknown incompatible receipt; modern receipts cannot be exempted")
    if value.get("result") not in {"verified", "verified-no-change", "incomplete", "failed"}:
        raise ValueError("invalid historical result")
    if timestamp(value.get("ended_at")) < timestamp(value.get("started_at")):
        raise ValueError("legacy receipt ends before it starts")
    for field in ("source", "destination", "checks"):
        if not isinstance(value.get(field), dict) or not value[field]:
            raise ValueError(f"legacy receipt requires {field}")
    for field in (("reconciliation", "coverage") if mode == "daily-sync" else ("restore_test", "history_coverage")):
        if not value.get(field):
            raise ValueError(f"legacy receipt requires {field}")


def load_receipts(root):
    directory = root / "receipts"
    if directory.is_symlink():
        raise ValueError("receipt directory must not be a symlink")
    result = []
    legacy = legacy_entries(root)
    seen = set()
    if directory.exists():
        for path in sorted(directory.iterdir()):
            if path.is_symlink() or not path.is_file() or path.suffix != ".json":
                raise ValueError("receipts must be direct regular JSON files")
            raw = path.read_bytes()
            value = json.loads(raw.decode("utf-8"))
            key = f"receipts/{path.name}".casefold()
            if key in seen:
                raise ValueError("case-colliding receipt paths")
            seen.add(key)
            if key in legacy:
                entry = legacy[key]
                if f"receipts/{path.name}" != entry["repository_path"] or len(raw) != entry["byte_size"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                    raise ValueError("legacy receipt bytes differ from reviewed evidence")
                validate_legacy_receipt(value, path.stem)
            else:
                result.append(validate_receipt(value, path.stem))
    if legacy.keys() - seen:
        raise ValueError("missing reviewed legacy receipts")
    return sorted(result, key=lambda r: (timestamp(r["ended_at"]), r["run_id"]), reverse=True)


def cell(value):
    # Escape Markdown/HTML so source metadata cannot inject links or table rows.
    text = " ".join(str(value).split())
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([\\|`*_[\]])", r"\\\1", text)


def render_block(receipts, legacy_count=0):
    lines = [START, "## Backup status", ""]
    if legacy_count:
        lines += [f"{legacy_count} reviewed historical receipts retained unchanged; excluded from current results.", ""]
    for mode, limit, title in (("weekly", 1, "Latest weekly result"), ("daily", 7, "Latest daily results")):
        lines += [f"### {title}", ""]
        selected = [r for r in receipts if r["mode"] == mode][:limit]
        if not selected:
            lines += [f"No {mode} results recorded.", ""]
            continue
        lines += ["| Completed | Result | Records / bytes | Coverage | Receipt |", "| --- | --- | --- | --- | --- |"]
        for r in selected:
            coverage = ("Complete current state" if r["current_state_complete"] else "Incomplete current state")
            coverage += "; history: " + r["history_coverage"]
            if r["coverage_limits"]:
                coverage += "; " + "; ".join(r["coverage_limits"])
            if mode == "weekly":
                coverage += "; restore: " + r["restore_test"]
            lines.append(f"| {cell(r['ended_at'])} | {r['status']} | {r['counts']['records']} / {r['counts']['bytes']} | {cell(coverage)} | [{r['run_id']}](receipts/{r['run_id']}.json) |")
        lines.append("")
    return "\n".join(lines + [END])


def update_readme(original, block):
    if START not in original and END not in original:
        return original + ("\n\n" if original else "") + block + "\n"
    if original.count(START) != 1 or original.count(END) != 1 or original.index(START) > original.index(END):
        raise ValueError("README has ambiguous status markers")
    start, end = original.index(START), original.index(END) + len(END)
    return original[:start] + block + original[end:]


def migrate_readme(original, plan):
    """Remove only reviewed byte ranges from an exact README, outside its block."""
    raw = original.encode("utf-8")
    if not isinstance(plan, dict) or plan.get("readme_sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("README differs from reviewed migration source")
    ranges = plan.get("remove_ranges")
    if not isinstance(ranges, list) or not ranges:
        raise ValueError("migration requires explicit remove_ranges")
    # Validate markers even before changing any text.
    update_readme(original, render_block([]))
    block_start = raw.find(START.encode())
    block_end = raw.find(END.encode()) + len(END.encode()) if block_start >= 0 else -1
    previous = 0
    pieces = []
    for item in ranges:
        if not isinstance(item, dict):
            raise ValueError("migration range must be an object")
        start, end = item.get("start"), item.get("end")
        if type(start) is not int or type(end) is not int or not previous <= start < end <= len(raw):
            raise ValueError("migration ranges must be ordered, nonoverlapping byte offsets")
        removed = raw[start:end]
        if (start and raw[start - 1] != 10) or (end < len(raw) and raw[end - 1] != 10):
            raise ValueError("migration ranges must follow line boundaries")
        if block_start >= 0 and start < block_end and end > block_start:
            raise ValueError("migration must not remove the generated status block")
        if hashlib.sha256(removed).hexdigest() != item.get("sha256"):
            raise ValueError("migration range differs from reviewed bytes")
        if not re.match(rb"## (?:Verified structural cutover|(?:Weekly reconciliation|Daily sync(?: retry)?|Missed daily sync) [^\r\n]+)(?:\r?\n)", removed):
            raise ValueError("migration range must start with a reviewed legacy log heading")
        pieces.append(raw[previous:start])
        previous = end
    pieces.append(raw[previous:])
    return b"".join(pieces).decode("utf-8")


def process(root, write=False, migration_plan=None):
    receipts = load_receipts(root)
    path = root / "README.md"
    if path.is_symlink():
        raise ValueError("README must not be a symlink")
    original = path.read_bytes().decode("utf-8") if path.exists() else ""
    base = migrate_readme(original, migration_plan) if migration_plan is not None else original
    updated = update_readme(base, render_block(receipts, len(legacy_entries(root))))
    if write:
        path.write_bytes(updated.encode("utf-8"))
    elif migration_plan is not None:
        return "".join(difflib.unified_diff(original.splitlines(keepends=True), updated.splitlines(keepends=True), fromfile="README.md (before)", tofile="README.md (proposed)"))
    elif original != updated:
        raise ValueError("README status block is missing or stale; run reporting.py ROOT --write")
    return len(receipts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--write", action="store_true", help="replace only the README status block")
    parser.add_argument("--migration-plan", type=Path, help="preview reviewed legacy-log removals; --write applies them locally")
    args = parser.parse_args()
    try:
        plan = json.loads(args.migration_plan.read_text(encoding="utf-8")) if args.migration_plan else None
        count = process(args.root, args.write, plan)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"FAIL {exc}\n")
    if args.migration_plan and not args.write:
        print(count, end="")
    else:
        print(json.dumps({"status": "valid", "receipts": count}))


if __name__ == "__main__":
    main()
