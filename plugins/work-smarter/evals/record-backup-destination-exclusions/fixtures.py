from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "record-backup" / "scripts"
PROFILE_PATH = "records/configuration/profile.yaml"
PROFILE_IDENTITY = {
    "provider": "synthetic-provider",
    "container": "synthetic-container",
    "id": "synthetic-profile-id",
    "path": "synthetic/profile.yaml",
    "repository_path": PROFILE_PATH,
}
DESTINATION = {"repository": "synthetic/backup", "branch": "main"}
POLICY_CONTEXT = "snapshot-validation"


def load_script(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"synthetic_record_backup_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile_bytes(exclusions: list[str]) -> bytes:
    lines = [
        "schema_version: 1",
        "profile:",
        "  provider: synthetic-provider",
        "  container: synthetic-container",
        "  id: synthetic-profile-id",
        "  path: synthetic/profile.yaml",
        f"  repository_path: {PROFILE_PATH}",
        "destination:",
        "  provider: github",
        "  repository: synthetic/backup",
        "  branch: main",
        "  exclusions:" if exclusions else "  exclusions: []",
    ]
    if exclusions:
        lines.extend(f"    - {json.dumps(path)}" for path in exclusions)
    return ("\n".join(lines) + "\n").encode("utf-8")


def policy_bindings(
    profile: bytes, exclusions: list[str], managed_paths: list[str]
) -> tuple[dict, dict, dict]:
    profile_binding = PROFILE_IDENTITY | {
        "sha256": hashlib.sha256(profile).hexdigest()
    }
    policy = {
        "schema_version": 1,
        "profile": profile_binding,
        "destination": dict(DESTINATION),
        "context": POLICY_CONTEXT,
        "exclusions": list(exclusions),
    }
    expectations = {
        "profile": dict(profile_binding),
        "destination": dict(DESTINATION),
        "context": POLICY_CONTEXT,
        "managed_paths": list(managed_paths),
        "exclusions": list(exclusions),
    }
    capture_policy = policy | {
        "exclusions": [
            path[:-1] if path.endswith("/") else path for path in exclusions
        ]
    }
    return policy, expectations, capture_policy


def write_snapshot(
    root: Path,
    *,
    exclusions: list[str],
    managed_records: dict[str, tuple[str, bytes]],
    protected_files: dict[str, bytes] | None = None,
    profile: bytes | None = None,
) -> dict:
    """Write one synthetic snapshot plus independently managed destination files."""
    root.mkdir(parents=True, exist_ok=True)
    profile = profile if profile is not None else profile_bytes(exclusions)
    content_by_path = {PROFILE_PATH: profile}
    content_by_path.update(
        {path: value[1] for path, value in managed_records.items()}
    )
    if any(not path.startswith("records/") for path in content_by_path):
        raise ValueError("fixture-managed paths must be under records/")

    records = []
    for path, content in content_by_path.items():
        if path == PROFILE_PATH:
            source_id = PROFILE_IDENTITY["id"]
            source_path = PROFILE_IDENTITY["path"]
            classification = "configuration"
        else:
            source_id, _ = managed_records[path]
            source_path = path.removeprefix("records/")
            classification = "current-authority"
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        records.append({
            "repository_path": path,
            "source_provider": PROFILE_IDENTITY["provider"],
            "source_container": PROFILE_IDENTITY["container"],
            "source_id": source_id,
            "source_path": source_path,
            "owner": "synthetic-user",
            "classification": classification,
            "byte_size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })

    managed_paths = [record["repository_path"] for record in records]
    policy, expectations, capture_policy = policy_bindings(
        profile, exclusions, managed_paths
    )
    manifest = {
        "schema_version": 1,
        "operational_layout": 1,
        "profile_repository_path": PROFILE_PATH,
        "capture_policy": capture_policy,
        "records": records,
    }
    manifest_path = root / "backup-index.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    for path, content in (protected_files or {}).items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    load_script("reporting").process(root, write=True)
    return {
        "root": root,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "policy": policy,
        "expectations": expectations,
        "profile_read": {
            "identity": dict(PROFILE_IDENTITY),
            "sha256": hashlib.sha256(profile).hexdigest(),
            "evidence_kind": "synthetic-profile-read",
        },
    }


def git_object_id(kind: str, content: bytes) -> str:
    header = f"{kind} {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def tree_inventory(files: dict[str, bytes]) -> tuple[str, list[dict]]:
    """Build complete SHA-1 Git tree inventory for a synthetic byte mapping."""
    entries: dict[str, dict[str, str]] = {}
    for path, content in files.items():
        parts = Path(path).parts
        for depth in range(1, len(parts)):
            directory = "/".join(parts[:depth])
            entries[directory] = {
                "path": directory,
                "mode": "040000",
                "type": "tree",
                "object_id": "0" * 40,
            }
        entries[path] = {
            "path": path,
            "mode": "100644",
            "type": "blob",
            "object_id": git_object_id("blob", content),
        }

    def children(parent: str):
        values = []
        for path, entry in entries.items():
            if Path(path).parent.as_posix() == parent:
                values.append((Path(path).name, entry))
        return values

    def tree_hash(items):
        ordered = sorted(
            items,
            key=lambda item: item[0].encode("utf-8")
            + (b"/" if item[1]["type"] == "tree" else b""),
        )
        body = bytearray()
        for name, entry in ordered:
            mode = "40000" if entry["mode"] == "040000" else entry["mode"]
            body.extend(mode.encode("ascii") + b" " + name.encode("utf-8") + b"\0")
            body.extend(bytes.fromhex(entry["object_id"]))
        return hashlib.sha1(
            b"tree " + str(len(body)).encode("ascii") + b"\0" + body
        ).hexdigest()

    for path in sorted(entries, key=lambda item: len(Path(item).parts), reverse=True):
        if entries[path]["type"] == "tree":
            entries[path]["object_id"] = tree_hash(children(path))
    inventory = [entries[path] for path in sorted(entries)]
    return tree_hash(children(".")), inventory


def preservation_packet(
    *,
    protected_roots: list[str],
    baseline_files: dict[str, bytes],
    staged_files: dict[str, bytes],
    content_files: dict[str, bytes],
    operational_files: dict[str, bytes],
) -> dict:
    destination = dict(DESTINATION)
    baseline_commit = hashlib.sha1(b"synthetic baseline commit").hexdigest()
    content_commit = hashlib.sha1(b"synthetic content commit").hexdigest()
    operational_commit = hashlib.sha1(b"synthetic operational commit").hexdigest()

    def evidence(files: dict[str, bytes], evidence_id: str) -> dict:
        tree_id, inventory = tree_inventory(files)
        return {"tree_id": tree_id, "inventory": inventory, "evidence_id": evidence_id}

    baseline = evidence(baseline_files, "synthetic-baseline-read")
    staged = evidence(staged_files, "synthetic-stage-check")
    content = evidence(content_files, "synthetic-content-readback")
    operational = evidence(operational_files, "synthetic-operational-readback")
    return {
        "schema_version": 1,
        "destination": destination,
        "protected_roots": list(protected_roots),
        "baseline": baseline | {
            "destination": destination,
            "commit": baseline_commit,
        },
        "staged": staged | {
            "destination": destination,
            "base_commit": baseline_commit,
        },
        "publications": [
            content | {
                "phase": "content",
                "destination": destination,
                "parent_commit": baseline_commit,
                "commit": content_commit,
            },
            operational | {
                "phase": "operational",
                "destination": destination,
                "parent_commit": content_commit,
                "commit": operational_commit,
            },
        ],
    }


def mode_receipt(mode: str, *, complete: bool, records: int, exclusions: list[str]) -> dict:
    status = "verified-no-change" if complete else "incomplete"
    return {
        "schema_version": 1,
        "run_id": f"synthetic-{mode}-run",
        "mode": mode,
        "status": status,
        "started_at": "2026-10-18T10:00:00Z",
        "ended_at": "2026-10-18T10:01:00Z",
        "snapshot_commit": "a" * 40 if complete else None,
        "checks": {
            "local_snapshot": True,
            "remote_snapshot": complete,
        },
        "scope": "synthetic configured roots",
        "exclusions": "synthetic independently managed roots",
        "history_coverage": "synthetic current-state observation",
        "coverage_limits": [] if complete else ["synthetic source coverage is incomplete"],
        "current_state_complete": complete,
        "counts": {"records": records, "bytes": 1, "changed": 0, "deleted": 0},
        "discovery": {
            "listing_calls": 1,
            "content_reads": records,
            "duplicates": 0,
            "pointer_cycles": 0,
            "retries": 0,
        },
        "destination_exclusions": [
            path[:-1] if path.endswith("/") else path for path in exclusions
        ],
        "destination_preservation": {
            "status": "preserved" if complete else "staged_preserved",
            "protected_roots": [
                path[:-1] if path.endswith("/") else path for path in exclusions
            ],
            "baseline_commit": "b" * 40,
            "content_commit": "c" * 40 if complete else None,
            **({"operational_commit": "d" * 40} if complete else {}),
        },
        **({
            "repaired_items": [],
            "unrecoverable_gaps": [],
            "source_access_limits": [],
            "restore_test": "Not repeated by this synthetic fixture; prior user-attested provider exercise is separate.",
        } if mode == "weekly" else {}),
    }


def enumerate_fresh_pages(pages: list[list[tuple[str, str, bytes]]]) -> dict:
    """Capture every synthetic source page without consulting a daily cache."""
    items = []
    events = []
    for page_number, page in enumerate(pages, start=1):
        items.extend(page)
        events.append({
            "operation": "fresh_source_page",
            "page_number": page_number,
            "returned_items": len(page),
            "has_more": page_number < len(pages),
        })
    return {"items": items, "events": events, "complete": bool(pages)}
