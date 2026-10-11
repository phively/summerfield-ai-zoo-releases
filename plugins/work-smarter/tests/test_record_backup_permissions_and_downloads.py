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
    record = identity | {"sha256": "a" * 64, "sensitivity_classes": ["financial"], "excluded": False, "credential_material": False}
    return {"profile": profile, "record": record, "destination": destination, "at": NOW}


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
