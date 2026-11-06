"""Regression for revoked task-only grants; no provider calls or writes."""
import importlib.util
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "record-backup" / "scripts"
spec = importlib.util.spec_from_file_location("check_permission", SCRIPTS / "check_permission.py")
assert spec is not None and spec.loader is not None
permission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permission)


def test_revoked_task_only_grant_is_denied_without_persistent_grant():
    destination = {"repository": "fixture/private-backup", "branch": "main"}
    identity = {"source_provider": "fixture", "source_container": "container", "source_id": "file"}
    grant = identity | {
        "id": "task-grant", "destination": destination,
        "sensitivity_classes": ["financial"],
        "content_scope": {"mode": "future-versions"},
        "authorized_by": "fixture-user", "authorization_reference": "fixture task approval",
        "granted_at": "2026-10-10T00:00:00Z", "expires_at": None, "revoked": True,
    }
    profile = {
        "schema_version": 1,
        "profile": {"provider": "fixture", "container": "container", "id": "profile", "path": "profile.yaml"},
        "destination": destination,
        "sensitive_backup": {"owner": "fixture-user", "maintainer": "record-backup", "grants": []},
    }
    record = identity | {
        "sha256": "a" * 64, "sensitivity_classes": ["financial"],
        "excluded": False, "credential_material": False,
        "inclusion_basis": [{"kind": "canonical-profile"}],
    }

    result = permission.check_permission(profile, record, destination, "2026-10-30T00:00:00Z", grant)

    assert result == {
        "allowed": False,
        "reason": "grant revoked; canonical reinstatement required",
    }
