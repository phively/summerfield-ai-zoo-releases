#!/usr/bin/env python3
"""Check a sensitive-record grant from a fresh, parsed canonical profile; no writes."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re

IDENTITY = ("source_provider", "source_container", "source_id")
FORBIDDEN = {"authentication-material", "credentials", "passwords", "tokens", "recovery-codes", "private-keys"}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def instant(value):
    if not isinstance(value, str):
        raise ValueError("authorization time must be an ISO-8601 string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("authorization time requires a timezone")
    return result


def classes(value):
    if not isinstance(value, list) or not value or any(not text(item) for item in value) or len(set(value)) != len(value):
        raise ValueError("sensitivity_classes must be a nonempty unique string list")
    return set(value)


def validate_grant(grant):
    if not isinstance(grant, dict):
        raise ValueError("grant must be an object")
    for field in (*IDENTITY, "id", "authorized_by", "authorization_reference"):
        if not text(grant.get(field)):
            raise ValueError(f"grant requires {field}")
    destination = grant.get("destination")
    if not isinstance(destination, dict) or any(not text(destination.get(key)) for key in ("repository", "branch")):
        raise ValueError("grant requires an exact destination")
    granted = instant(grant.get("granted_at"))
    if "expires_at" not in grant or (grant["expires_at"] is not None and instant(grant["expires_at"]) <= granted):
        raise ValueError("grant requires an explicit null or later expires_at")
    if type(grant.get("revoked")) is not bool:
        raise ValueError("grant requires revoked boolean")
    if {item.strip().casefold() for item in classes(grant.get("sensitivity_classes"))} & FORBIDDEN:
        raise ValueError("authentication material cannot be granted")
    scope = grant.get("content_scope")
    if not isinstance(scope, dict) or scope.get("mode") not in {"exact-sha256", "future-versions"}:
        raise ValueError("grant requires exact-sha256 or future-versions scope")
    if scope["mode"] == "exact-sha256" and (not isinstance(scope.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", scope["sha256"])):
        raise ValueError("exact grant requires sha256")
    return grant


def check_permission(profile, record, destination, at, task_grant=None):
    """A decision over declared metadata, not proof of consent or secret scanning."""
    def denied(reason):
        return {"allowed": False, "reason": reason}

    try:
        now = instant(at)
        if not isinstance(profile, dict) or type(profile.get("schema_version")) is not int or profile["schema_version"] != 1:
            return denied("canonical profile unavailable or invalid")
        identity = profile.get("profile")
        if not isinstance(identity, dict) or any(not text(identity.get(k)) for k in ("provider", "container", "id", "path")):
            return denied("canonical profile identity unavailable")
        if not isinstance(destination, dict) or any(not text(destination.get(k)) for k in ("repository", "branch")):
            return denied("destination unavailable")
        if not isinstance(profile.get("destination"), dict) or any(profile["destination"].get(k) != destination[k] for k in ("repository", "branch")):
            return denied("destination differs from canonical profile")
        policy = profile.get("sensitive_backup")
        if not isinstance(policy, dict) or not text(policy.get("owner")) or not text(policy.get("maintainer")):
            return denied("sensitive backup owner or maintainer unavailable")
        if not isinstance(record, dict) or any(not text(record.get(k)) for k in IDENTITY):
            return denied("record identity unavailable")
        if record.get("excluded") is not False or record.get("credential_material") is not False:
            return denied("exclusion or credential classification unresolved or prohibited")
        sensitivities = classes(record.get("sensitivity_classes"))
        if {item.strip().casefold() for item in sensitivities} & FORBIDDEN:
            return denied("authentication material prohibited")
        if not isinstance(record.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
            return denied("exact record hash unavailable")
        grants = policy.get("grants")
        if not isinstance(grants, list):
            return denied("canonical grant list unavailable")
        for grant in grants:
            validate_grant(grant)
        ids = [grant["id"] for grant in grants]
        if len(set(ids)) != len(ids):
            return denied("duplicate grant IDs")
        matches = [grant for grant in grants if all(grant[k] == record[k] for k in IDENTITY)
                   and all(grant["destination"][k] == destination[k] for k in ("repository", "branch"))]
        if any(grant["revoked"] for grant in matches):
            return denied("grant revoked; canonical reinstatement required")
        if task_grant is not None:
            matches = [validate_grant(task_grant)]
        if len(matches) != 1:
            return denied("missing or ambiguous grant")
        grant = matches[0]
        if grant["authorized_by"] != policy["owner"]:
            return denied("grant author differs from authorization owner")
        if grant["revoked"] or any(grant[k] != record[k] for k in IDENTITY) or any(grant["destination"][k] != destination[k] for k in ("repository", "branch")):
            return denied("grant does not authorize this record and destination")
        if now < instant(grant["granted_at"]) or (grant["expires_at"] is not None and now >= instant(grant["expires_at"])):
            return denied("grant not yet effective or expired")
        if not sensitivities <= classes(grant["sensitivity_classes"]):
            return denied("sensitivity exceeds grant")
        scope = grant["content_scope"]
        if scope["mode"] == "exact-sha256" and scope["sha256"] != record["sha256"]:
            return denied("content exceeds exact-version grant")
        return {"allowed": True, "grant_id": grant["id"], "authorization_scope": "task-only" if task_grant is not None else "persistent"}
    except (ValueError, TypeError, KeyError) as exc:
        return denied(str(exc))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="run-local JSON: profile, record, destination, at, optional task_grant")
    args = parser.parse_args()
    try:
        packet = json.loads(args.input.read_text(encoding="utf-8"))
        result = check_permission(packet.get("profile"), packet.get("record"), packet.get("destination"), packet.get("at"), packet.get("task_grant"))
    except (OSError, ValueError, AttributeError) as exc:
        result = {"allowed": False, "reason": str(exc)}
    print(json.dumps(result))
    return 0 if result["allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
