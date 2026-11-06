"""Synthetic selection, permission, snapshot, and receipt flows.

All identities, bytes, approvals, and verification claims are development
fixtures. This module does not access providers, GitHub, or personal records.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[2]
SCRIPTS = PLUGIN / "skills" / "record-backup" / "scripts"
NOW = "2026-10-30T12:00:00Z"
DESTINATION = {"repository": "fixture/private-backup", "branch": "main"}


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scope = load_script("check_source_scope")
permission = load_script("check_permission")
reporting = load_script("reporting")
snapshot_validator = load_script("validate_snapshot")


def identity(source_id):
    return {"source_provider": "fixture", "source_container": "personal", "source_id": source_id}


def source_packet():
    profile = identity("profile")
    canonical = identity("current-authority")
    salary = identity("salary-file")
    designated = identity("designated-reference")
    unrelated = identity("xfinity-neighbor")
    frozen = identity("old-root-mirror")
    return {
        "schema_version": 1,
        "profile": profile,
        "canonical_records": [{
            **canonical, "owner": "remember-me", "evidence_reference": "fixture-index-entry",
        }],
        "canonical_mentions": [{
            "from": canonical, "reference": "salary-file.md", "state": "resolved", "targets": [salary],
        }],
        "user_designations": [{
            **designated, "designation_reference": "fixture-user-designation",
        }],
        "excluded": [],
        "candidates": [profile, canonical, salary, designated, unrelated, frozen],
    }


def approval_profile():
    return {
        "schema_version": 1,
        "profile": {
            "provider": "fixture", "container": "personal", "id": "profile", "path": "profile.yaml",
        },
        "destination": dict(DESTINATION),
        "sensitive_backup": {
            "owner": "fixture-user", "maintainer": "record-backup",
            "grants": [],
            "approved_data_types": [{
                "id": "salary-approval-1", "data_type": "salary",
                "source_provider": "fixture", "source_container": "personal",
                "destination": dict(DESTINATION), "sensitivity_classes": ["financial"],
                "authorized_by": "fixture-user", "authorization_reference": "fixture-approved-type",
                "granted_at": "2026-10-01T00:00:00Z", "expires_at": None, "revoked": False,
            }],
        },
    }


def run_synthetic_flow(mode, root):
    if mode not in {"daily", "manual", "weekly"}:
        raise ValueError("mode must be daily, manual, or weekly")
    selected = scope.select_sources(source_packet())
    selected_by_id = {item["identity"]["source_id"]: item for item in selected["selected"]}
    if "xfinity-neighbor" in selected_by_id:
        raise AssertionError("unreferenced same-topic neighbor entered selected scope")

    staged_rows = []
    for source_id, item in sorted(selected_by_id.items()):
        data = f"synthetic fixture bytes for {source_id}\n".encode()
        staged_rows.append((item["identity"], item["inclusion_basis"], data, None, 1))
    # The old mirror stays in the indexed snapshot without being selected or read.
    frozen_bytes = b"frozen synthetic bytes\n"
    prior_mirror = identity("old-root-mirror") | {
        "repository_path": "records/old-root-mirror.md",
        "source_path": "fixture/old-root-mirror.md", "source_version": 7,
        "owner": "fixture", "classification": "supporting",
        "byte_size": len(frozen_bytes), "sha256": hashlib.sha256(frozen_bytes).hexdigest(),
    }
    staged_rows.append((identity("old-root-mirror"), [], frozen_bytes,
                        "retained-out-of-scope", 7))

    included = selected_by_id["salary-file"]
    salary_bytes = next(row[2] for row in staged_rows if row[0]["source_id"] == "salary-file")
    permission_record = included["identity"] | {
        "sha256": hashlib.sha256(salary_bytes).hexdigest(),
        "sensitivity_classes": ["financial"], "excluded": False,
        "credential_material": False, "data_types": ["salary"],
        "inclusion_basis": included["inclusion_basis"],
    }
    permission_checked_ids = []
    profile = approval_profile()

    def check_selected_permission(record):
        permission_checked_ids.append(record["source_id"])
        return permission.check_permission(profile, record, DESTINATION, NOW)

    allowed = check_selected_permission(permission_record)
    if not allowed.get("allowed"):
        raise AssertionError(f"synthetic salary approval was denied: {allowed}")
    allowed = allowed | {"identity": included["identity"]}

    root = Path(root)
    records = []
    for item, _, data, selection_status, version in staged_rows:
        source_id = item["source_id"]
        repository_path = f"records/{source_id}.md"
        path = root / repository_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        record = item | {
            "repository_path": repository_path, "source_path": f"fixture/{source_id}.md",
            "owner": "fixture", "classification": "supporting",
            "source_version": version, "byte_size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        }
        if selection_status:
            record["selection_status"] = selection_status
        records.append(record)
    manifest = {"schema_version": 1, "records": records}
    manifest_path = root / "backup-index.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    snapshot_validator.validate(root, manifest_path)
    remote_operations = ["stub_remote_tree_read"]
    stub_remote_tree = {
        item["repository_path"]: (root / item["repository_path"]).read_bytes()
        for item in records
    }
    remote_operations.append("manifest_size_and_sha256_check")
    for item in records:
        remote_bytes = stub_remote_tree[item["repository_path"]]
        if len(remote_bytes) != item["byte_size"] or hashlib.sha256(remote_bytes).hexdigest() != item["sha256"]:
            raise AssertionError("synthetic stub readback differs from the manifest")

    selected_salary = included["identity"] | {
        "data_types": ["salary"], "inclusion_basis": included["inclusion_basis"],
    }
    additions = reporting.derive_personal_data_additions(
        {"state": "verified", "snapshot_commit": "a" * 40,
         "manifest": {"records": [prior_mirror]}},
        {"state": "verified", "snapshot_commit": "b" * 40, "manifest": manifest},
        [selected_salary], [allowed],
    )
    receipt = {
        "schema_version": 1, "run_id": f"fixture-{mode}", "mode": mode,
        "status": "verified", "started_at": "2026-10-30T11:00:00Z", "ended_at": NOW,
        "snapshot_commit": "b" * 40,
        "checks": {"local_snapshot": True, "remote_snapshot": True},
        "scope": "synthetic selected records", "exclusions": "none",
        "history_coverage": "synthetic fixture only", "coverage_limits": additions["coverage_limits"],
        "current_state_complete": True,
        "counts": {"records": len(records), "bytes": sum(item["byte_size"] for item in records),
                   "changed": 1, "deleted": 0},
        "discovery": {"listing_calls": 1, "content_reads": len(selected["selected"]),
                      "duplicates": 0, "pointer_cycles": 0, "retries": 0},
        **({"personal_data_additions": additions["personal_data_additions"]}
           if additions["personal_data_additions"] else {}),
    }
    if mode == "weekly":
        receipt.update(repaired_items=[], unrecoverable_gaps=[], source_access_limits=[],
                       restore_test="Synthetic manifest hash validation only.")
    reporting.validate_receipt(receipt, receipt["run_id"])
    return {
        "mode": mode,
        "selected_ids": sorted(selected_by_id),
        "outside_scope_ids": sorted(item["identity"]["source_id"] for item in selected["outside_scope"]),
        "permission_checked_ids": permission_checked_ids,
        "snapshot_record_count": len(records),
        "prior_mirror": prior_mirror,
        "retained_mirror": next(item for item in records if item["source_id"] == "old-root-mirror"),
        "receipt": receipt,
        "remote_operations": remote_operations,
        "remote_verification": "synthetic stub readback passed; GitHub was not contacted",
    }
