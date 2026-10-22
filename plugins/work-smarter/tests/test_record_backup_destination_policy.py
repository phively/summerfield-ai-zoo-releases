"""Synthetic controls for user-configured destination exclusions."""
import hashlib
import importlib.util
import json
import copy
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "record-backup" / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


validator = load("validate_snapshot")
reporting = load("reporting")
preservation = load("check_destination_preservation")


PROFILE = {
    "provider": "synthetic-provider",
    "container": "synthetic-container",
    "id": "synthetic-profile-id",
    "path": "synthetic/profile.yaml",
    "repository_path": "records/configuration/profile.yaml",
}
DESTINATION = {"repository": "synthetic/backup", "branch": "main"}
PROFILE_BYTES = b"schema_version: 1\n"
RECORD_PATH = "records/topics/current.md"
PROFILE_SHA256 = hashlib.sha256(PROFILE_BYTES).hexdigest()


def record(path: str, data: bytes, *, source_id: str) -> dict[str, object]:
    return {
        "repository_path": path,
        "source_provider": "synthetic-provider",
        "source_container": "synthetic-container",
        "source_id": source_id,
        "source_path": PROFILE["path"] if path == PROFILE["repository_path"] else path,
        "owner": "synthetic",
        "classification": "configuration" if path == PROFILE["repository_path"] else "current-authority",
        "byte_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def make_snapshot(root: Path, exclusions: list[str] | None = None) -> tuple[dict, dict, dict]:
    profile = root / PROFILE["repository_path"]
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_bytes(PROFILE_BYTES)
    record_path = root / RECORD_PATH
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_bytes = b"# Synthetic current topic\n"
    record_path.write_bytes(record_bytes)

    policy = None
    expectations = None
    metadata = None
    if exclusions is not None:
        packet_exclusions = list(exclusions)
        normalized = [value[:-1] if value.endswith("/") else value for value in packet_exclusions]
        policy = {
            "schema_version": 1,
            "profile": PROFILE | {"sha256": PROFILE_SHA256},
            "destination": DESTINATION,
            "context": "snapshot-validation",
            "exclusions": packet_exclusions,
        }
        expectations = {
            "profile": PROFILE | {"sha256": PROFILE_SHA256},
            "destination": DESTINATION,
            "context": "snapshot-validation",
            "managed_paths": [PROFILE["repository_path"], RECORD_PATH],
            "exclusions": packet_exclusions,
        }
        metadata = policy | {"exclusions": normalized}

    manifest = {
        "schema_version": 1,
        "operational_layout": 1,
        "profile_repository_path": PROFILE["repository_path"],
        "records": [
            record(PROFILE["repository_path"], PROFILE_BYTES, source_id=PROFILE["id"]),
            record(RECORD_PATH, record_bytes, source_id="synthetic-topic-id"),
        ],
    }
    if metadata is not None:
        manifest["capture_policy"] = metadata
    manifest_path = root / "backup-index.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    reporting.process(root, write=True)
    return {"root": root, "manifest_path": manifest_path, "manifest": manifest}, policy, expectations


def validate(snapshot, policy=None, expectations=None):
    return validator.validate(
        snapshot["root"],
        snapshot["manifest_path"],
        destination_policy=policy,
        policy_expectations=expectations,
    )


def test_configured_directory_is_exempt_but_prefix_neighbor_is_not(tmp_path):
    snapshot, policy, expectations = make_snapshot(tmp_path, ["managed/archive/"])
    excluded = tmp_path / "managed" / "archive" / "independently-owned.dat"
    excluded.parent.mkdir(parents=True)
    excluded.write_bytes(b"leave this file alone")
    neighbor = tmp_path / "managed" / "archive-old" / "unexpected.dat"
    neighbor.parent.mkdir(parents=True)
    neighbor.write_bytes(b"still outside the configured root")

    with pytest.raises(validator.SnapshotError, match="unindexed files: managed/archive-old/unexpected.dat"):
        validate(snapshot, policy, expectations)

    neighbor.unlink()
    result = validate(snapshot, policy, expectations)
    assert result["record_count"] == 2
    assert excluded.read_bytes() == b"leave this file alone"


def test_missing_exclusion_directory_is_allowed_and_file_root_is_rejected(tmp_path):
    snapshot, policy, expectations = make_snapshot(tmp_path, ["not-created-yet"])
    assert validate(snapshot, policy, expectations)["record_count"] == 2

    snapshot, policy, expectations = make_snapshot(tmp_path / "file-root", ["independent-root"])
    (tmp_path / "file-root" / "independent-root").write_bytes(b"a file is not a directory")
    with pytest.raises(validator.SnapshotError, match="exclusion root is not a directory"):
        validate(snapshot, policy, expectations)


def test_missing_or_empty_policy_keeps_strict_extra_file_check(tmp_path):
    snapshot, _, _ = make_snapshot(tmp_path)
    (tmp_path / "independent" / "data.bin").parent.mkdir(parents=True)
    (tmp_path / "independent" / "data.bin").write_bytes(b"independent")
    with pytest.raises(validator.SnapshotError, match="unindexed files"):
        validate(snapshot)

    snapshot, policy, expectations = make_snapshot(tmp_path / "empty-policy", [])
    (tmp_path / "empty-policy" / "independent").mkdir()
    (tmp_path / "empty-policy" / "independent" / "data.bin").write_bytes(b"independent")
    with pytest.raises(validator.SnapshotError, match="unindexed files"):
        validate(snapshot, policy, expectations)


@pytest.mark.parametrize("exclusion", [
    "",
    "/absolute",
    "../outside",
    "one/../two",
    "one//two",
    "one\\two",
    "C:/outside",
    "wild*card",
    ".",
    "records/",
    "records/topics/current.md/",
    "receipts/",
    "README.md/",
    "backup-index.json/",
    ".git/",
])
def test_unsafe_or_operationally_overlapping_policy_fails_closed(tmp_path, exclusion):
    snapshot, policy, expectations = make_snapshot(tmp_path, [exclusion])
    with pytest.raises(validator.SnapshotError):
        validate(snapshot, policy, expectations)


@pytest.mark.parametrize("exclusions", [
    ["archive", "archive"],
    ["archive", "archive/nested"],
    ["Archive", "archive"],
])
def test_duplicate_nested_and_case_colliding_rules_fail_closed(tmp_path, exclusions):
    snapshot, policy, expectations = make_snapshot(tmp_path, exclusions)
    with pytest.raises(validator.SnapshotError, match="duplicate, nested, or case-colliding"):
        validate(snapshot, policy, expectations)


def test_policy_must_match_profile_hash_destination_and_capture_metadata(tmp_path):
    snapshot, policy, expectations = make_snapshot(tmp_path, ["separately-managed"])
    independent = tmp_path / "separately-managed" / "file.bin"
    independent.parent.mkdir()
    independent.write_bytes(b"separate")

    wrong_destination = dict(policy, destination={"repository": "other/backup", "branch": "main"})
    with pytest.raises(validator.SnapshotError):
        validate(snapshot, wrong_destination, expectations)

    wrong_profile_hash = dict(policy, profile=policy["profile"] | {"sha256": "0" * 64})
    with pytest.raises(validator.SnapshotError):
        validate(snapshot, wrong_profile_hash, expectations)

    snapshot["manifest"]["capture_policy"]["destination"] = {"repository": "other/backup", "branch": "main"}
    snapshot["manifest_path"].write_text(json.dumps(snapshot["manifest"]), encoding="utf-8")
    with pytest.raises(validator.SnapshotError):
        validate(snapshot, policy, expectations)


def test_packet_exclusions_must_match_independently_extracted_profile_roots(tmp_path):
    snapshot, policy, expectations = make_snapshot(tmp_path, ["configured-area"])
    expectations["exclusions"] = ["different-area"]

    with pytest.raises(
        validator.SnapshotError,
        match="policy exclusions differ from independent expectations",
    ):
        validate(snapshot, policy, expectations)


def test_exclusion_cannot_hide_managed_corruption_or_unexpected_files_elsewhere(tmp_path):
    snapshot, policy, expectations = make_snapshot(tmp_path, ["independent-area"])
    excluded = tmp_path / "independent-area" / "file.bin"
    excluded.parent.mkdir()
    excluded.write_bytes(b"separate")
    unexpected = tmp_path / "other-area" / "extra.bin"
    unexpected.parent.mkdir()
    unexpected.write_bytes(b"extra")
    with pytest.raises(validator.SnapshotError, match="unindexed files"):
        validate(snapshot, policy, expectations)

    unexpected.unlink()
    (tmp_path / RECORD_PATH).write_bytes(b"corrupt")
    with pytest.raises(validator.SnapshotError, match="content mismatch"):
        validate(snapshot, policy, expectations)

    (tmp_path / RECORD_PATH).unlink()
    with pytest.raises(validator.SnapshotError, match="missing stored record"):
        validate(snapshot, policy, expectations)


def test_symlink_inside_excluded_directory_is_rejected(tmp_path):
    snapshot, policy, expectations = make_snapshot(tmp_path, ["independent-area"])
    excluded = tmp_path / "independent-area"
    excluded.mkdir()
    target = tmp_path / "outside.bin"
    target.write_bytes(b"outside")
    (excluded / "link.bin").symlink_to(target)

    with pytest.raises(validator.SnapshotError, match="symlinks are not supported"):
        validate(snapshot, policy, expectations)


def test_symlink_ancestor_of_excluded_directory_is_rejected(tmp_path):
    snapshot, policy, expectations = make_snapshot(tmp_path, ["linked-area/subdir"])
    target = tmp_path / "safe-target"
    (target / "subdir").mkdir(parents=True)
    (tmp_path / "linked-area").symlink_to(target, target_is_directory=True)

    with pytest.raises(validator.SnapshotError, match="symlinks are not supported"):
        validate(snapshot, policy, expectations)


def test_case_collision_inside_excluded_directory_is_rejected(tmp_path):
    snapshot, policy, expectations = make_snapshot(tmp_path, ["independent-area"])
    excluded = tmp_path / "independent-area"
    excluded.mkdir()
    (excluded / "item.bin").write_bytes(b"lower")
    (excluded / "ITEM.bin").write_bytes(b"upper")

    with pytest.raises(validator.SnapshotError, match="case-colliding stored paths"):
        validate(snapshot, policy, expectations)


def test_case_collision_between_directories_is_rejected_even_with_different_files(tmp_path):
    snapshot, policy, expectations = make_snapshot(tmp_path, ["independent-area"])
    lower = tmp_path / "independent-area" / "nested"
    upper = tmp_path / "independent-area" / "NESTED"
    lower.mkdir(parents=True)
    upper.mkdir(parents=True)
    (lower / "one.bin").write_bytes(b"lower")
    (upper / "two.bin").write_bytes(b"upper")

    with pytest.raises(validator.SnapshotError, match="case-colliding stored paths"):
        validate(snapshot, policy, expectations)


def _refresh_tree_inventory(inventory, algorithm="sha1"):
    children_by_parent = {}
    for entry in inventory:
        path = Path(entry["path"])
        children_by_parent.setdefault(path.parent.as_posix(), []).append((path.name, entry))

    def tree_hash(children):
        ordered = sorted(
            children,
            key=lambda item: item[0].encode("utf-8") + (b"/" if item[1]["type"] == "tree" else b""),
        )
        body = bytearray()
        for name, entry in ordered:
            mode = "40000" if entry["mode"] == "040000" else entry["mode"]
            body.extend(mode.encode("ascii") + b" " + name.encode("utf-8") + b"\0")
            body.extend(bytes.fromhex(entry["object_id"]))
        header = b"tree " + str(len(body)).encode("ascii") + b"\0"
        return hashlib.new(algorithm, header + body).hexdigest()

    tree_entries = sorted(
        (entry for entry in inventory if entry["type"] == "tree"),
        key=lambda entry: len(Path(entry["path"]).parts),
        reverse=True,
    )
    for entry in tree_entries:
        entry["object_id"] = tree_hash(children_by_parent.get(entry["path"], []))
    return tree_hash(children_by_parent.get(".", []))


def _preservation_packet(*, algorithm="sha1"):
    destination = {"repository": "synthetic/backup", "branch": "main"}
    object_id_length = 40 if algorithm == "sha1" else 64

    def object_id(char):
        return char * object_id_length

    baseline_commit = object_id("1")
    content_commit = object_id("2")
    entries = [
        {"path": "separately-managed", "mode": "040000", "type": "tree", "object_id": object_id("a")},
        {"path": "separately-managed/jobs", "mode": "040000", "type": "tree", "object_id": object_id("b")},
        {"path": "separately-managed/jobs/posting.md", "mode": "100644", "type": "blob", "object_id": object_id("c")},
        {"path": "README.md", "mode": "100644", "type": "blob", "object_id": object_id("d")},
    ]
    tree_id = _refresh_tree_inventory(entries, algorithm)
    return {
        "schema_version": 1,
        "destination": destination,
        "protected_roots": ["separately-managed/jobs/"],
        "baseline": {
            "destination": destination, "commit": baseline_commit, "tree_id": tree_id,
            "evidence_id": "base-tree-read", "inventory": copy.deepcopy(entries),
        },
        "staged": {
            "destination": destination, "base_commit": baseline_commit, "tree_id": tree_id,
            "evidence_id": "staged-tree-read", "inventory": copy.deepcopy(entries),
        },
        "publications": [
            {
                "phase": "content", "destination": destination,
                "parent_commit": baseline_commit, "commit": content_commit,
                "tree_id": tree_id, "evidence_id": "content-tree-read", "inventory": copy.deepcopy(entries),
            },
            {
                "phase": "operational", "destination": destination,
                "parent_commit": content_commit, "commit": object_id("3"),
                "tree_id": tree_id, "evidence_id": "operational-tree-read", "inventory": copy.deepcopy(entries),
            },
        ],
    }


def test_protected_destination_is_compared_through_both_publication_phases():
    result = preservation.check_preservation(_preservation_packet())

    assert result["status"] == "preserved"
    assert result["checked_phases"] == ["staging", "content", "operational"]
    assert result["protected_roots"] == ["separately-managed/jobs"]


def test_tree_inventory_supports_sha256_repositories():
    assert preservation.check_preservation(_preservation_packet(algorithm="sha256"))["status"] == "preserved"


def test_git_tree_hash_matches_a_known_git_object_id():
    children = [
        ("separately-managed", {"mode": "040000", "type": "tree", "object_id": "a" * 40}),
        ("README.md", {"mode": "100644", "type": "blob", "object_id": "d" * 40}),
    ]

    assert preservation._git_tree_hash(children, "sha1") == "9c3617cadfc223d16d12cce766a8b2dba8171a9e"


def test_incomplete_inventory_cannot_certify_an_omitted_existing_protected_root():
    packet = _preservation_packet()
    root = "separately-managed/jobs"
    evidence = [packet["baseline"], packet["staged"], *packet["publications"]]
    for phase in evidence:
        phase["inventory"] = [
            entry for entry in phase["inventory"]
            if entry["path"] != root and not entry["path"].startswith(root + "/")
        ]

    with pytest.raises(preservation.PreservationError, match="inventory is incomplete or inconsistent"):
        preservation.check_preservation(packet)


@pytest.mark.parametrize("phase", ["baseline", "staged", "content", "operational"])
def test_each_tree_inventory_must_match_its_declared_tree_id(phase):
    packet = _preservation_packet()
    evidence = {
        "baseline": packet["baseline"],
        "staged": packet["staged"],
        "content": packet["publications"][0],
        "operational": packet["publications"][1],
    }[phase]
    root = "separately-managed/jobs"
    evidence["inventory"] = [
        entry for entry in evidence["inventory"]
        if entry["path"] != root and not entry["path"].startswith(root + "/")
    ]

    with pytest.raises(preservation.PreservationError, match="inventory is incomplete or inconsistent"):
        preservation.check_preservation(packet)


def test_inventory_rejects_nul_in_git_path_components():
    packet = _preservation_packet()
    evidence = [packet["baseline"], packet["staged"], *packet["publications"]]
    for phase in evidence:
        phase["inventory"].append({
            "path": "untracked\0suffix",
            "mode": "100644",
            "type": "blob",
            "object_id": "f" * 40,
        })
        phase["tree_id"] = _refresh_tree_inventory(phase["inventory"])

    with pytest.raises(preservation.PreservationError, match="safe repository-relative path"):
        preservation.check_preservation(packet)


def test_content_readback_alone_does_not_claim_full_preservation():
    packet = _preservation_packet()
    packet["publications"] = packet["publications"][:1]

    result = preservation.check_preservation(packet)

    assert result["status"] == "content_preserved"
    assert "operational" not in result["checked_phases"]


def test_unchanged_destination_can_be_read_back_without_creating_commits():
    packet = _preservation_packet()
    base_tree = packet["baseline"]["tree_id"]
    for publication in packet["publications"]:
        publication["commit"] = packet["baseline"]["commit"]
        publication["parent_commit"] = packet["baseline"]["commit"]
        publication["tree_id"] = base_tree

    assert preservation.check_preservation(packet)["status"] == "preserved"


@pytest.mark.parametrize("mode,kind", [
    ("040000", "blob"), ("040000", "commit"),
    ("100644", "tree"), ("100644", "commit"),
    ("100755", "tree"), ("100755", "commit"),
    ("120000", "tree"), ("120000", "commit"),
    ("160000", "blob"), ("160000", "tree"),
])
def test_inventory_rejects_invalid_git_mode_type_pairs(mode, kind):
    packet = _preservation_packet()
    inventories = [packet["baseline"], packet["staged"], *packet["publications"]]
    for phase in inventories:
        phase["inventory"][-2].update(mode=mode, type=kind)

    with pytest.raises(preservation.PreservationError, match="invalid Git mode/type pair"):
        preservation.check_preservation(packet)


@pytest.mark.parametrize("phase", ["staged", "content", "operational"])
@pytest.mark.parametrize("change", ["add", "remove", "overwrite", "mode", "type"])
def test_protected_tree_changes_fail_even_when_managed_snapshot_is_valid(phase, change):
    packet = _preservation_packet()
    if phase == "staged":
        evidence = packet["staged"]
    else:
        evidence = next(item for item in packet["publications"] if item["phase"] == phase)
    inventory = evidence["inventory"]

    file_entry = inventory[-2]
    if change == "add":
        inventory.append({"path": "separately-managed/jobs/new.md", "mode": "100644", "type": "blob", "object_id": "8" * 40})
    elif change == "remove":
        inventory.remove(file_entry)
    elif change == "overwrite":
        file_entry["object_id"] = "8" * 40
    elif change == "mode":
        file_entry["mode"] = "100755"
    else:
        file_entry.update(mode="160000", type="commit")
    evidence["tree_id"] = _refresh_tree_inventory(inventory)

    with pytest.raises(preservation.PreservationError, match="protected destination changed"):
        preservation.check_preservation(packet)


def test_adding_files_beneath_a_previously_absent_protected_root_fails():
    packet = _preservation_packet()
    root = "separately-managed/jobs"
    packet["baseline"]["inventory"] = [
        entry for entry in packet["baseline"]["inventory"]
        if entry["path"] != root and not entry["path"].startswith(root + "/")
    ]
    packet["baseline"]["tree_id"] = _refresh_tree_inventory(packet["baseline"]["inventory"])

    with pytest.raises(preservation.PreservationError, match="protected destination changed at staging"):
        preservation.check_preservation(packet)


def test_stale_or_unavailable_independent_publication_evidence_cannot_verify_preservation():
    packet = _preservation_packet()
    packet["staged"]["base_commit"] = "4" * 40
    with pytest.raises(preservation.PreservationError, match="stale or different baseline"):
        preservation.check_preservation(packet)

    packet = _preservation_packet()
    packet["publications"] = []
    assert preservation.check_preservation(packet)["status"] == "staged_preserved"


def test_destination_binding_and_commit_chain_are_required():
    packet = _preservation_packet()
    packet["publications"][1]["destination"] = {"repository": "elsewhere/backup", "branch": "main"}
    with pytest.raises(preservation.PreservationError, match="different destination"):
        preservation.check_preservation(packet)

    packet = _preservation_packet()
    packet["publications"][1]["parent_commit"] = "4" * 40
    with pytest.raises(preservation.PreservationError, match="does not extend"):
        preservation.check_preservation(packet)


def test_concurrent_base_update_requires_refetch_and_a_fresh_staged_inventory():
    packet = _preservation_packet()
    packet["baseline"]["commit"] = "4" * 40
    with pytest.raises(preservation.PreservationError, match="stale or different baseline"):
        preservation.check_preservation(packet)

    packet["staged"]["base_commit"] = "4" * 40
    packet["baseline"]["inventory"][-2]["object_id"] = "9" * 40
    packet["baseline"]["tree_id"] = _refresh_tree_inventory(packet["baseline"]["inventory"])
    packet["staged"]["inventory"][-2]["object_id"] = "9" * 40
    packet["staged"]["tree_id"] = _refresh_tree_inventory(packet["staged"]["inventory"])
    packet["publications"][0]["parent_commit"] = "4" * 40
    for publication in packet["publications"]:
        publication["inventory"][-2]["object_id"] = "9" * 40
        publication["tree_id"] = _refresh_tree_inventory(publication["inventory"])
    assert preservation.check_preservation(packet)["status"] == "preserved"


def test_operational_publication_cannot_change_protected_content():
    packet = _preservation_packet()
    packet["publications"][1]["inventory"][-2]["object_id"] = "8" * 40
    packet["publications"][1]["tree_id"] = _refresh_tree_inventory(packet["publications"][1]["inventory"])

    with pytest.raises(preservation.PreservationError, match="protected destination changed at operational"):
        preservation.check_preservation(packet)


def _run_preservation_cli(input_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "check_destination_preservation.py"), str(input_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_preservation_cli_accepts_valid_packet_and_prints_json(tmp_path):
    input_path = tmp_path / "preservation.json"
    input_path.write_text(json.dumps(_preservation_packet()), encoding="utf-8")

    completed = _run_preservation_cli(input_path)

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    result = json.loads(completed.stdout)
    assert result["status"] == "preserved"
    assert result["checked_phases"] == ["staging", "content", "operational"]
    assert result["protected_roots"] == ["separately-managed/jobs"]


def test_preservation_cli_rejects_malformed_json_with_nonzero_exit(tmp_path):
    input_path = tmp_path / "preservation.json"
    input_path.write_text("{malformed json", encoding="utf-8")

    completed = _run_preservation_cli(input_path)

    assert completed.returncode != 0
    error = json.loads(completed.stderr)
    assert error["status"] == "failed"
    assert "invalid preservation input" in error["reason"]


def test_preservation_cli_rejects_invalid_packet_with_nonzero_exit(tmp_path):
    packet = _preservation_packet()
    packet["schema_version"] = 2
    input_path = tmp_path / "preservation.json"
    input_path.write_text(json.dumps(packet), encoding="utf-8")

    completed = _run_preservation_cli(input_path)

    assert completed.returncode != 0
    error = json.loads(completed.stderr)
    assert error["status"] == "failed"
    assert "unsupported preservation packet version" in error["reason"]
