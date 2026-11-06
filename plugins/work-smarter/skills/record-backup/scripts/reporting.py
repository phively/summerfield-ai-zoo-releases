#!/usr/bin/env python3
"""Validate backup receipts and render/check the destination README status block."""

from __future__ import annotations

import argparse
import difflib
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re

START = "<!-- record-backup:start -->"
END = "<!-- record-backup:end -->"
SOURCE_IDENTITY = ("source_provider", "source_container", "source_id")
ADDITION_FIELDS = {
    "identity", "display_reference", "data_types", "inclusion_basis", "approval_ids"
}


def _load_destination_policy():
    path = Path(__file__).with_name("destination_policy.py")
    spec = importlib.util.spec_from_file_location("record_backup_destination_policy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load destination policy helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


destination_policy = _load_destination_policy()


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("receipt timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("receipt timestamp requires a timezone")
    return result


def _identity(value, label):
    if not isinstance(value, dict) or any(
        not isinstance(value.get(field), str) or not value[field].strip()
        for field in SOURCE_IDENTITY
    ):
        raise ValueError(f"{label} requires a complete scoped source identity")
    return {field: value[field] for field in SOURCE_IDENTITY}


def _identity_key(value):
    return tuple(value[field] for field in SOURCE_IDENTITY)


def _display_reference(identity):
    raw = json.dumps([identity[field] for field in SOURCE_IDENTITY], ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    return "record-" + hashlib.sha256(raw).hexdigest()[:16]


def _manifest_identities(manifest, label):
    if not isinstance(manifest, dict) or not isinstance(manifest.get("records"), list):
        raise ValueError(f"{label} manifest requires a records list")
    records = {}
    for index, record in enumerate(manifest["records"]):
        identity = _identity(record, f"{label} manifest records[{index}]")
        if "selection_status" in record and record["selection_status"] != "retained-out-of-scope":
            raise ValueError(f"{label} manifest records[{index}] has invalid selection_status")
        key = _identity_key(identity)
        if key in records:
            raise ValueError(f"{label} manifest contains duplicate scoped identities")
        records[key] = record
    return records


def _addition_basis(basis, label):
    if not isinstance(basis, list) or not basis:
        raise ValueError(f"{label} requires inclusion provenance")
    result = []
    for index, item in enumerate(basis):
        if not isinstance(item, dict):
            raise ValueError(f"{label} inclusion_basis[{index}] must be an object")
        kind = item.get("kind")
        if kind == "canonical-profile" and set(item) == {"kind"}:
            safe = {"kind": kind}
        elif kind == "canonical-record" and set(item) == {"kind", "owner", "reference"}:
            if (not isinstance(item["owner"], str) or not item["owner"].strip()
                    or not isinstance(item["reference"], str) or not item["reference"].strip()):
                raise ValueError(f"{label} canonical-record provenance requires owner and reference")
            safe = {"kind": kind, "owner": item["owner"]}
        elif kind == "canonical-mention" and set(item) == {"kind", "from", "reference"}:
            if not isinstance(item["reference"], str) or not item["reference"].strip():
                raise ValueError(f"{label} canonical mention requires a reference")
            safe = {"kind": kind, "from": _identity(item["from"], f"{label} mention owner")}
        elif kind == "user-designation" and set(item) == {"kind", "reference"}:
            if not isinstance(item["reference"], str) or not item["reference"].strip():
                raise ValueError(f"{label} user designation requires a reference")
            safe = {"kind": kind}
        else:
            raise ValueError(f"{label} has invalid or unsupported inclusion provenance")
        result.append(safe)
    original = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in basis]
    if len(set(original)) != len(original):
        raise ValueError(f"{label} has duplicate inclusion provenance")
    encoded = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in result]
    return [json.loads(item) for item in sorted(set(encoded))]


def validate_personal_data_additions(additions):
    """Validate the closed metadata shape without asserting remote verification."""
    if not isinstance(additions, list):
        raise ValueError("personal_data_additions must be a list")
    seen = set()
    for index, entry in enumerate(additions):
        label = f"personal_data_additions[{index}]"
        if not isinstance(entry, dict) or set(entry) != ADDITION_FIELDS:
            raise ValueError(f"{label} has an invalid closed metadata shape")
        identity = _identity(entry.get("identity"), f"{label}.identity")
        key = _identity_key(identity)
        if key in seen:
            raise ValueError("personal_data_additions contains duplicate scoped identities")
        seen.add(key)
        if entry.get("display_reference") != _display_reference(identity):
            raise ValueError(f"{label} has an invalid neutral display_reference")
        for field in ("data_types", "approval_ids"):
            values = entry.get(field)
            if (not isinstance(values, list) or not values
                    or any(not isinstance(value, str) or not value.strip() for value in values)
                    or len(values) != len(set(values))):
                raise ValueError(f"{label}.{field} must be a nonempty unique string list")
            if field == "data_types" and len({value.strip().casefold() for value in values}) != len(values):
                raise ValueError(f"{label}.data_types must be unique without regard to case")
        basis = entry.get("inclusion_basis")
        if not isinstance(basis, list) or not basis:
            raise ValueError(f"{label}.inclusion_basis must be a nonempty list")
        basis_keys = set()
        for item in basis:
            if not isinstance(item, dict):
                raise ValueError(f"{label}.inclusion_basis entries must be objects")
            kind = item.get("kind")
            if kind == "canonical-profile" and set(item) == {"kind"}:
                pass
            elif kind == "canonical-record" and set(item) == {"kind", "owner"}:
                if not isinstance(item["owner"], str) or not item["owner"].strip():
                    raise ValueError(f"{label} canonical-record owner must be nonempty")
            elif kind == "canonical-mention" and set(item) == {"kind", "from"}:
                _identity(item["from"], f"{label} mention owner")
            elif kind == "user-designation" and set(item) == {"kind"}:
                pass
            else:
                raise ValueError(f"{label} has invalid receipt inclusion provenance")
            encoded = json.dumps(item, sort_keys=True, separators=(",", ":"))
            if encoded in basis_keys:
                raise ValueError(f"{label} has duplicate receipt inclusion provenance")
            basis_keys.add(encoded)
    return additions


def derive_personal_data_additions(prior_snapshot, current_snapshot, included_records,
                                   authorization_results):
    """Derive notices from a verified manifest identity diff and declared gates.

    Callers establish snapshot verification independently. This helper performs
    no provider or GitHub reads and treats unknown prior state as unknown, never
    as an empty baseline.
    """
    if not isinstance(prior_snapshot, dict) or prior_snapshot.get("state") not in {
        "verified", "verified-empty", "unknown"
    }:
        raise ValueError("prior snapshot state must be verified, verified-empty, or unknown")
    if not isinstance(current_snapshot, dict) or current_snapshot.get("state") not in {
        "verified", "staged", "unverified", "failed", "unknown"
    }:
        raise ValueError("current snapshot state is invalid")
    if not isinstance(included_records, list) or not isinstance(authorization_results, list):
        raise ValueError("included_records and authorization_results must be lists")

    if current_snapshot["state"] != "verified":
        return {
            "personal_data_additions": [],
            "coverage_limits": ["Personal-data additions omitted because the current snapshot is not independently verified."],
        }
    commit = current_snapshot.get("snapshot_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise ValueError("verified current snapshot requires a full snapshot commit SHA")
    current = _manifest_identities(current_snapshot.get("manifest"), "current")
    if prior_snapshot["state"] == "verified-empty":
        if not isinstance(prior_snapshot.get("evidence_reference"), str) or not prior_snapshot["evidence_reference"].strip():
            raise ValueError("verified-empty prior state requires an evidence reference")
        prior_keys = set()
    elif prior_snapshot["state"] == "unknown":
        prior_keys = None
    else:
        prior_commit = prior_snapshot.get("snapshot_commit")
        if not isinstance(prior_commit, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", prior_commit):
            raise ValueError("verified prior snapshot requires a full snapshot commit SHA")
        prior = _manifest_identities(prior_snapshot.get("manifest"), "prior")
        prior_keys = set(prior)

    authorizations = {}
    for index, result in enumerate(authorization_results):
        if not isinstance(result, dict) or type(result.get("allowed")) is not bool:
            raise ValueError(f"authorization_results[{index}] requires a boolean allowed result")
        identity = _identity(result.get("identity"), f"authorization_results[{index}]")
        key = _identity_key(identity)
        if key in authorizations:
            raise ValueError("authorization_results contains duplicate scoped identities")
        authorizations[key] = result

    included = {}
    for index, record in enumerate(included_records):
        identity = _identity(record, f"included_records[{index}]")
        key = _identity_key(identity)
        if key in included:
            raise ValueError("included_records contains duplicate scoped identities")
        included[key] = (identity, record)

    additions = []
    unknown_baseline_candidates = 0
    for key in sorted(included):
        identity, record = included[key]
        current_record = current.get(key)
        if current_record is None:
            raise ValueError("included personal record is absent from the verified current manifest")
        if (record.get("selection_status") == "retained-out-of-scope"
                or current_record.get("selection_status") == "retained-out-of-scope"):
            continue
        data_types = record.get("data_types")
        if (not isinstance(data_types, list) or not data_types
                or any(not isinstance(value, str) or not value.strip() for value in data_types)
                or len(data_types) != len(set(data_types))):
            raise ValueError("included personal record requires unique declared data_types")
        basis = _addition_basis(record.get("inclusion_basis"), "included personal record")
        auth = authorizations.get(key)
        if auth is None or auth["allowed"] is not True:
            raise ValueError("included personal record requires a matching successful authorization")
        approval_ids = auth.get("approval_ids")
        if approval_ids is None and isinstance(auth.get("grant_id"), str):
            approval_ids = [auth["grant_id"]]
        if (not isinstance(approval_ids, list) or not approval_ids
                or any(not isinstance(value, str) or not value.strip() for value in approval_ids)
                or len(approval_ids) != len(set(approval_ids))):
            raise ValueError("successful authorization requires actual approval or grant IDs")
        if prior_keys is None:
            unknown_baseline_candidates += 1
            continue
        if key in prior_keys:
            continue
        additions.append({
            "identity": identity,
            "display_reference": _display_reference(identity),
            "data_types": sorted(data_types),
            "inclusion_basis": basis,
            "approval_ids": sorted(approval_ids),
        })

    validate_personal_data_additions(additions)
    limits = []
    if prior_keys is None and unknown_baseline_candidates:
        limits.append("Personal-data additions omitted because prior verified snapshot state is unknown.")
    return {"personal_data_additions": additions, "coverage_limits": limits}


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
    destination_exclusions = value.get("destination_exclusions", [])
    try:
        normalized_exclusions = destination_policy.normalize_exclusions(destination_exclusions)
    except destination_policy.DestinationPolicyError as exc:
        raise ValueError(f"invalid destination_exclusions: {exc}") from exc
    if normalized_exclusions != destination_exclusions:
        raise ValueError("destination_exclusions must use normalized literal paths")
    preservation = value.get("destination_preservation")
    if destination_exclusions:
        required_fields = {"status", "protected_roots", "baseline_commit", "content_commit"}
        allowed_fields = required_fields | {"operational_commit"}
        if not isinstance(preservation, dict) or set(preservation) not in (
            required_fields, allowed_fields
        ):
            raise ValueError("destination exclusions require separate preservation evidence")
        if preservation.get("status") not in {
            "staged_preserved", "content_preserved", "preserved", "unverified", "failed"
        }:
            raise ValueError("invalid destination preservation status")
        try:
            roots = destination_policy.normalize_exclusions(preservation.get("protected_roots"))
        except destination_policy.DestinationPolicyError as exc:
            raise ValueError(f"invalid destination preservation roots: {exc}") from exc
        if roots != destination_exclusions:
            raise ValueError("destination preservation roots differ from configured exclusions")
        for field in ("baseline_commit", "content_commit", "operational_commit"):
            commit = preservation.get(field)
            if commit is not None and (not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit)):
                raise ValueError(f"destination preservation {field} must be a full Git SHA or null")
        expected_commit_fields = {
            "staged_preserved": (True, False, False),
            "content_preserved": (True, True, False),
            "preserved": (True, True, True),
        }.get(preservation["status"])
        if expected_commit_fields and tuple(
            preservation.get(field) is not None
            for field in ("baseline_commit", "content_commit", "operational_commit")
        ) != expected_commit_fields:
            raise ValueError("destination preservation commit evidence does not match its status")
    elif preservation is not None:
        raise ValueError("destination preservation evidence requires configured exclusions")
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
    if verified and destination_exclusions and preservation["status"] not in {
        "content_preserved", "preserved"
    }:
        raise ValueError("verified receipt requires complete destination preservation evidence")
    if (verified and destination_exclusions
            and preservation["content_commit"] != sha):
        raise ValueError(
            "verified receipt requires destination preservation content_commit to match snapshot_commit"
        )
    if verified and value["mode"] == "weekly" and any(
        checks.get(key) is False for key in ("full_latest_restore", "full_older_restore")
    ):
        raise ValueError("verified weekly receipt cannot contain a failed recovery drill")
    if not verified and value["current_state_complete"]:
        raise ValueError("failed/incomplete receipt cannot claim completeness")
    if value["status"] == "verified-no-change" and (value["counts"]["changed"] or value["counts"]["deleted"]):
        raise ValueError("no-change receipt contains changes")
    if "personal_data_additions" in value:
        additions = validate_personal_data_additions(value["personal_data_additions"])
        if additions and (
            value["status"] == "failed" or not sha
            or not checks["local_snapshot"] or not checks["remote_snapshot"]
        ):
            raise ValueError("personal-data additions require independently verified snapshot content")
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
    return _load_receipts(root, legacy_entries(root))


def _load_receipts(root, legacy):
    directory = root / "receipts"
    if directory.is_symlink():
        raise ValueError("receipt directory must not be a symlink")
    result = []
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
        lines += ["| Completed | Result | Records / bytes | Coverage | Preservation | Receipt |", "| --- | --- | --- | --- | --- | --- |"]
        for r in selected:
            coverage = ("Complete current state" if r["current_state_complete"] else "Incomplete current state")
            coverage += "; history: " + r["history_coverage"]
            if r["coverage_limits"]:
                coverage += "; " + "; ".join(r["coverage_limits"])
            if mode == "weekly":
                coverage += "; restore: " + r["restore_test"]
            preservation = r.get("destination_preservation")
            if preservation is None:
                preservation_label = "not configured" if "destination_exclusions" in r else "not recorded"
            else:
                preservation_label = preservation["status"]
            lines.append(f"| {cell(r['ended_at'])} | {r['status']} | {r['counts']['records']} / {r['counts']['bytes']} | {cell(coverage)} | {cell(preservation_label)} | [{r['run_id']}](receipts/{r['run_id']}.json) |")
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
    legacy = legacy_entries(root)
    receipts = _load_receipts(root, legacy)
    path = root / "README.md"
    if path.is_symlink():
        raise ValueError("README must not be a symlink")
    original = path.read_bytes().decode("utf-8") if path.exists() else ""
    base = migrate_readme(original, migration_plan) if migration_plan is not None else original
    updated = update_readme(base, render_block(receipts, len(legacy)))
    if write:
        path.write_bytes(updated.encode("utf-8"))
    elif migration_plan is not None:
        return "".join(difflib.unified_diff(original.splitlines(keepends=True), updated.splitlines(keepends=True), fromfile="README.md (before)", tofile="README.md (proposed)"))
    elif original != updated:
        raise ValueError("README status block is missing or stale; run reporting.py ROOT --write")
    return len(receipts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path)
    parser.add_argument("--write", action="store_true", help="replace only the README status block")
    parser.add_argument("--migration-plan", type=Path, help="preview reviewed legacy-log removals; --write applies them locally")
    parser.add_argument("--derive-additions", type=Path, metavar="INPUT.json",
                        help="derive personal-data additions from verified snapshot and authorization context")
    args = parser.parse_args()
    try:
        if args.derive_additions is not None:
            if args.root is not None or args.write or args.migration_plan is not None:
                parser.error("--derive-additions cannot be combined with ROOT, --write, or --migration-plan")
            packet = json.loads(args.derive_additions.read_text(encoding="utf-8"))
            if not isinstance(packet, dict) or set(packet) != {
                "prior_snapshot", "current_snapshot", "included_records", "authorization_results"
            }:
                raise ValueError("addition input requires prior_snapshot, current_snapshot, included_records, and authorization_results")
            result = derive_personal_data_additions(
                packet["prior_snapshot"], packet["current_snapshot"],
                packet["included_records"], packet["authorization_results"],
            )
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
            return
        if args.root is None:
            parser.error("ROOT is required unless --derive-additions is used")
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
