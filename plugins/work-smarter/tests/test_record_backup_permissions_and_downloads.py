"""Focused grant matching and exact remote-payload handling; no live writes."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "record-backup" / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


permission = load("check_permission")
download = load("verify_download")
NOW = "2026-10-11T12:00:00-05:00"


def packet():
    destination = {"repository": "fixture/private-backup", "branch": "main"}
    identity = {"source_provider": "fixture", "source_container": "container", "source_id": "sensitive-file"}
    grant = identity | {"id": "grant-1", "destination": destination.copy(), "sensitivity_classes": ["financial"],
                        "content_scope": {"mode": "exact-sha256", "sha256": "a" * 64},
                        "authorized_by": "fixture-user", "authorization_reference": "fixture approval 1",
                        "granted_at": "2026-10-10T12:00:00-05:00", "expires_at": None, "revoked": False}
    profile = {"schema_version": 1, "profile": {"provider": "fixture", "container": "container", "id": "profile-id", "path": "/profile.yaml"},
               "destination": destination.copy(), "sensitive_backup": {"owner": "fixture-user", "maintainer": "record-owner", "grants": [grant]}}
    record = identity | {
        "sha256": "a" * 64,
        "sensitivity_classes": ["financial"],
        "excluded": False,
        "credential_material": False,
        "inclusion_basis": [{
            "kind": "canonical-record",
            "owner": "remember-me",
            "reference": "synthetic-index",
        }],
    }
    return {"profile": profile, "record": record, "destination": destination, "at": NOW}


def data_type_approval(data_type="salary", sensitivity_classes=None):
    return {
        "id": f"type-{data_type}",
        "data_type": data_type,
        "sensitivity_classes": sensitivity_classes or ["financial"],
        "source_provider": "fixture",
        "source_container": "container",
        "destination": {"repository": "fixture/private-backup", "branch": "main"},
        "authorized_by": "fixture-user",
        "authorization_reference": f"fixture {data_type} approval",
        "granted_at": "2026-10-10T12:00:00-05:00",
        "expires_at": None,
        "revoked": False,
    }


def category_packet(data_types=("salary",), sensitivity_classes=("financial",)):
    request = packet()
    request["profile"]["sensitive_backup"]["grants"] = []
    request["profile"]["sensitive_backup"]["approved_data_types"] = [
        data_type_approval()
    ]
    request["record"]["source_id"] = "new-sensitive-file"
    request["record"]["data_types"] = list(data_types)
    request["record"]["sensitivity_classes"] = list(sensitivity_classes)
    return request


def test_exact_and_future_grants_use_current_profile_without_mutation():
    request = packet()
    before = copy.deepcopy(request)
    assert permission.check_permission(**request)["allowed"]
    assert request == before
    request["record"]["sha256"] = "b" * 64
    assert not permission.check_permission(**request)["allowed"]
    request["profile"]["sensitive_backup"]["grants"][0]["content_scope"] = {"mode": "future-versions"}
    assert permission.check_permission(**request)["allowed"]
    request["record"]["sensitivity_classes"].append("medical")
    assert not permission.check_permission(**request)["allowed"]


@pytest.mark.parametrize("change", ["missing", "revoked", "expired", "not-effective", "new-identity", "destination", "excluded", "credentials", "unknown-class", "wrong-author", "ambiguous"])
def test_missing_or_inapplicable_permission_denies_publication(change):
    request = packet()
    policy = request["profile"]["sensitive_backup"]
    grant = policy["grants"][0]
    if change == "missing":
        policy["grants"] = []
    elif change == "revoked":
        grant["revoked"] = True
    elif change == "expired":
        grant["expires_at"] = NOW
    elif change == "not-effective":
        grant["granted_at"] = "2026-10-12T12:00:00-05:00"
    elif change == "new-identity":
        request["record"]["source_id"] = "other-file"
    elif change == "destination":
        request["destination"]["branch"] = "other"
    elif change == "excluded":
        request["record"]["excluded"] = True
    elif change == "credentials":
        request["record"]["credential_material"] = True
    elif change == "unknown-class":
        request["record"].pop("sensitivity_classes")
    elif change == "wrong-author":
        grant["authorized_by"] = "different-user"
    else:
        policy["grants"].append(copy.deepcopy(grant) | {"id": "grant-2"})
    assert not permission.check_permission(**request)["allowed"]


def test_task_only_permission_is_not_persisted_and_cannot_override_revocation():
    request = packet()
    grant = request["profile"]["sensitive_backup"]["grants"].pop()
    result = permission.check_permission(**request, task_grant=grant)
    assert result == {"allowed": True, "grant_id": "grant-1", "authorization_scope": "task-only"}
    assert request["profile"]["sensitive_backup"]["grants"] == []
    request["profile"]["sensitive_backup"]["grants"] = [grant | {"revoked": True}]
    assert not permission.check_permission(**request, task_grant=grant)["allowed"]


def test_unavailable_or_partial_profile_does_not_reuse_old_grants():
    request = packet()
    request["profile"] = None
    assert not permission.check_permission(**request)["allowed"]
    request = packet()
    request["profile"]["sensitive_backup"].pop("maintainer")
    assert not permission.check_permission(**request)["allowed"]


def test_authentication_classes_are_prohibited_even_with_a_matching_grant():
    request = packet()
    request["record"]["sensitivity_classes"] = ["tokens"]
    request["profile"]["sensitive_backup"]["grants"][0]["sensitivity_classes"] = ["tokens"]
    assert not permission.check_permission(**request)["allowed"]


def test_approved_data_type_covers_new_id_and_later_versions_without_mutation():
    request = category_packet()
    before = copy.deepcopy(request)

    first = permission.check_permission(**request)
    request["record"]["source_id"] = "another-salary-file"
    request["record"]["sha256"] = "b" * 64
    later = permission.check_permission(**request)

    assert first == {
        "allowed": True,
        "approval_ids": ["type-salary"],
        "authorization_scope": "approved-data-types",
    }
    assert later["allowed"]
    assert later["approval_ids"] == ["type-salary"]
    assert request["profile"]["sensitive_backup"]["approved_data_types"] == before[
        "profile"]["sensitive_backup"]["approved_data_types"]


@pytest.mark.parametrize(
    "first_record",
    [
        None,
        {
            "source_provider": "fixture",
            "source_container": "container",
            "source_id": "first-salary-file",
            "reference": "renamed-first-file.md",
        },
        {
            "source_provider": "fixture",
            "source_container": "container",
            "source_id": "unavailable-first-file",
            "reference": "inaccessible-first-file",
        },
    ],
)
def test_first_approved_file_provenance_is_optional_and_not_a_match_restriction(first_record):
    request = category_packet()
    approval = request["profile"]["sensitive_backup"]["approved_data_types"][0]
    if first_record is not None:
        approval["first_approved_record"] = first_record

    result = permission.check_permission(**request)

    assert result["allowed"]
    assert result["approval_ids"] == ["type-salary"]


def test_disjoint_data_type_approvals_cover_mixed_records_and_missing_type_denies():
    request = category_packet(("salary", "medical"), ("financial", "health"))
    request["profile"]["sensitive_backup"]["approved_data_types"].append(
        data_type_approval("medical", ["health"])
    )

    result = permission.check_permission(**request)
    assert result["allowed"]
    assert result["approval_ids"] == ["type-medical", "type-salary"]

    request["profile"]["sensitive_backup"]["approved_data_types"].pop()
    denied = permission.check_permission(**request)
    assert not denied["allowed"]
    assert "medical" in denied["reason"]

    request = category_packet(("salary",), ("financial", "health"))
    denied = permission.check_permission(**request)
    assert not denied["allowed"]
    assert "health" in denied["reason"]


def test_record_and_type_revocation_and_exact_record_restriction_block_category_fallback():
    request = category_packet()
    exact = packet()["profile"]["sensitive_backup"]["grants"][0]
    exact.update({
        "source_provider": request["record"]["source_provider"],
        "source_container": request["record"]["source_container"],
        "source_id": request["record"]["source_id"],
        "content_scope": {"mode": "exact-sha256", "sha256": "c" * 64},
    })
    request["profile"]["sensitive_backup"]["grants"] = [exact]
    restricted = permission.check_permission(**request)
    assert not restricted["allowed"]
    assert "exact-version" in restricted["reason"]

    exact["revoked"] = True
    assert "revoked" in permission.check_permission(**request)["reason"]
    request["task_grant"] = exact | {"revoked": False}
    assert "revoked" in permission.check_permission(**request)["reason"]

    request = category_packet()
    approval = request["profile"]["sensitive_backup"]["approved_data_types"][0]
    approval["revoked"] = True
    task = packet()["profile"]["sensitive_backup"]["grants"][0]
    task.update({
        "source_provider": request["record"]["source_provider"],
        "source_container": request["record"]["source_container"],
        "source_id": request["record"]["source_id"],
    })
    denied = permission.check_permission(**request, task_grant=task)
    assert not denied["allowed"]
    assert "data-type approval revoked" in denied["reason"]


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("wrong-owner", "author differs"),
        ("wrong-provider", "no effective approval"),
        ("wrong-container", "no effective approval"),
        ("wrong-repository", "no effective approval"),
        ("wrong-branch", "no effective approval"),
        ("not-effective", "no effective approval"),
        ("expired", "no effective approval"),
        ("duplicate-id", "duplicate grant or approval IDs"),
        ("duplicate-type", "multiple effective approvals"),
    ],
)
def test_inapplicable_or_conflicting_data_type_approvals_deny(change, reason):
    request = category_packet()
    approvals = request["profile"]["sensitive_backup"]["approved_data_types"]
    if change == "wrong-owner":
        approvals[0]["authorized_by"] = "different-user"
    elif change == "wrong-provider":
        approvals[0]["source_provider"] = "another-provider"
    elif change == "wrong-container":
        approvals[0]["source_container"] = "another-container"
    elif change == "wrong-repository":
        approvals[0]["destination"]["repository"] = "other/backup"
    elif change == "wrong-branch":
        approvals[0]["destination"]["branch"] = "other"
    elif change == "not-effective":
        approvals[0]["granted_at"] = "2026-10-12T12:00:00-05:00"
    elif change == "expired":
        approvals[0]["expires_at"] = NOW
    elif change == "duplicate-id":
        approvals.append(copy.deepcopy(approvals[0]))
    else:
        approvals.append(data_type_approval() | {"id": "type-salary-copy"})

    denied = permission.check_permission(**request)
    assert not denied["allowed"]
    assert reason in denied["reason"]


def test_credentials_and_missing_classification_or_inclusion_evidence_deny_category_permission():
    request = category_packet()
    request["record"]["credential_material"] = True
    assert not permission.check_permission(**request)["allowed"]

    request = category_packet()
    request["record"].pop("data_types")
    denied = permission.check_permission(**request)
    assert not denied["allowed"]
    assert "data types unavailable" in denied["reason"]

    request = category_packet()
    request["record"].pop("inclusion_basis")
    denied = permission.check_permission(**request)
    assert not denied["allowed"]
    assert "eligibility evidence unavailable" in denied["reason"]

    request = category_packet()
    request["record"].pop("sensitivity_classes")
    denied = permission.check_permission(**request)
    assert not denied["allowed"]
    assert "sensitivity_classes" in denied["reason"]

    request = category_packet()
    request["record"].pop("excluded")
    assert "exclusion or credential classification" in permission.check_permission(**request)["reason"]

    request = category_packet()
    request["record"]["source_container"] = ""
    assert "record identity unavailable" in permission.check_permission(**request)["reason"]


def test_category_only_profile_can_omit_legacy_grants_and_expired_unrelated_type_does_not_veto():
    request = category_packet()
    request["profile"]["sensitive_backup"].pop("grants")
    request["record"]["data_types"] = ["medical"]
    request["record"]["sensitivity_classes"] = ["health"]
    unrelated = data_type_approval("salary", ["financial"])
    unrelated["expires_at"] = "2026-10-11T12:00:00-05:00"
    request["profile"]["sensitive_backup"]["approved_data_types"] = [
        unrelated,
        data_type_approval("medical", ["health"]),
    ]

    result = permission.check_permission(**request)

    assert result["allowed"]
    assert result["approval_ids"] == ["type-medical"]


@pytest.mark.parametrize("encoding", ["raw", "base64"])
def test_binary_payload_is_preserved_exactly(encoding):
    data = bytes(range(256)) * 4
    payload = data if encoding == "raw" else b"\n".join(base64.b64encode(data)[i:i + 60] for i in range(0, len(base64.b64encode(data)), 60))
    assert download.verified_bytes(payload, encoding, len(data), hashlib.sha256(data).hexdigest()) == data


@pytest.mark.parametrize("payload,encoding", [(b"", "raw"), (b"truncated", "raw"), (b"@@@", "base64"), (b"AA==", "base64")])
def test_missing_truncated_and_invalid_downloads_cannot_verify(payload, encoding):
    with pytest.raises(ValueError):
        download.verified_bytes(payload, encoding, 256, hashlib.sha256(bytes(range(256))).hexdigest())


def test_permission_cli_denial_and_download_output_never_overwrite(tmp_path):
    request = packet()
    request["profile"]["sensitive_backup"]["grants"] = []
    input_path = tmp_path / "request.json"
    input_path.write_text(json.dumps(request))
    result = subprocess.run([sys.executable, str(SCRIPTS / "check_permission.py"), str(input_path)], capture_output=True, text=True)
    assert result.returncode == 1 and not json.loads(result.stdout)["allowed"]

    request = category_packet()
    input_path.write_text(json.dumps(request))
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_permission.py"), str(input_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["approval_ids"] == ["type-salary"]

    data = b"\x00\xff binary\r\n"
    payload, output = tmp_path / "payload.b64", tmp_path / "recovered.bin"
    payload.write_bytes(base64.b64encode(data))
    command = [sys.executable, str(SCRIPTS / "verify_download.py"), str(payload), "--encoding", "base64",
               "--byte-size", str(len(data)), "--sha256", hashlib.sha256(data).hexdigest(), "--output", str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert output.read_bytes() == data
    output.write_bytes(b"keep existing scratch")
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 1 and output.read_bytes() == b"keep existing scratch"
