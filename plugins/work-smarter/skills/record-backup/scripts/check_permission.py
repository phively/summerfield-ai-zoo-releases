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


def data_types(value):
    if not isinstance(value, list) or not value or any(not text(item) for item in value):
        raise ValueError("data_types must be a nonempty unique string list")
    normalized = [item.strip().casefold() for item in value]
    if len(set(normalized)) != len(normalized):
        raise ValueError("data_types must be a nonempty unique string list")
    return set(normalized)


def validate_inclusion_basis(value):
    if not isinstance(value, list) or not value:
        raise ValueError("record eligibility evidence unavailable")
    valid_kinds = {"canonical-profile", "canonical-record", "canonical-mention", "user-designation"}
    for entry in value:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("kind"), str)
            or entry["kind"] not in valid_kinds
        ):
            raise ValueError("record eligibility evidence is invalid")
        kind = entry["kind"]
        if kind == "canonical-record" and not all(text(entry.get(k)) for k in ("owner", "reference")):
            raise ValueError("canonical-record eligibility evidence requires owner and reference")
        if kind == "canonical-mention":
            owner = entry.get("from")
            if not isinstance(owner, dict) or any(not text(owner.get(k)) for k in IDENTITY):
                raise ValueError("canonical-mention eligibility evidence requires source identity")
            if not text(entry.get("reference")):
                raise ValueError("canonical-mention eligibility evidence requires reference")
        if kind == "user-designation" and not text(entry.get("reference")):
            raise ValueError("user-designation eligibility evidence requires reference")


def validate_data_type_approval(approval):
    if not isinstance(approval, dict):
        raise ValueError("data-type approval must be an object")
    fields = (*IDENTITY[:2], "id", "data_type", "authorized_by", "authorization_reference")
    if any(not text(approval.get(field)) for field in fields):
        raise ValueError("data-type approval requires identity, type, and provenance")
    destination = approval.get("destination")
    if not isinstance(destination, dict) or any(
        not text(destination.get(key)) for key in ("repository", "branch")
    ):
        raise ValueError("data-type approval requires an exact destination")
    granted = instant(approval.get("granted_at"))
    if "expires_at" not in approval or (
        approval["expires_at"] is not None and instant(approval["expires_at"]) <= granted
    ):
        raise ValueError("data-type approval requires an explicit null or later expires_at")
    if type(approval.get("revoked")) is not bool:
        raise ValueError("data-type approval requires revoked boolean")
    if {item.strip().casefold() for item in classes(approval.get("sensitivity_classes"))} & FORBIDDEN:
        raise ValueError("authentication material cannot be granted")
    first = approval.get("first_approved_record")
    if first is not None:
        if not isinstance(first, dict) or any(not text(first.get(key)) for key in IDENTITY):
            raise ValueError("first_approved_record requires a scoped record identity")
        if not text(first.get("reference")):
            raise ValueError("first_approved_record requires a reference")
    return approval


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

    def grant_result(grant, authorization_scope, *, task_only=False):
        if grant["authorized_by"] != policy["owner"]:
            return denied("grant author differs from authorization owner")
        if task_only:
            if grant["revoked"]:
                return denied("grant revoked; canonical reinstatement required")
            if any(grant[k] != record[k] for k in IDENTITY) or any(
                grant["destination"][k] != destination[k] for k in ("repository", "branch")
            ):
                return denied("grant does not authorize this record and destination")
        if now < instant(grant["granted_at"]) or (
            grant["expires_at"] is not None and now >= instant(grant["expires_at"])
        ):
            return denied("grant not yet effective or expired")
        if not sensitivities <= classes(grant["sensitivity_classes"]):
            return denied("sensitivity exceeds grant")
        scope = grant["content_scope"]
        if scope["mode"] == "exact-sha256" and scope["sha256"] != record["sha256"]:
            return denied("content exceeds exact-version grant")
        return {
            "allowed": True,
            "grant_id": grant["id"],
            "authorization_scope": authorization_scope,
        }

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
        validate_inclusion_basis(record.get("inclusion_basis"))
        if record.get("excluded") is not False or record.get("credential_material") is not False:
            return denied("exclusion or credential classification unresolved or prohibited")
        sensitivities = classes(record.get("sensitivity_classes"))
        if {item.strip().casefold() for item in sensitivities} & FORBIDDEN:
            return denied("authentication material prohibited")
        if not isinstance(record.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
            return denied("exact record hash unavailable")
        required_types = data_types(record["data_types"]) if "data_types" in record else None
        if "grants" not in policy:
            if "approved_data_types" not in policy:
                return denied("canonical grant list unavailable")
            grants = []
        else:
            grants = policy["grants"]
        if not isinstance(grants, list):
            return denied("canonical grant list unavailable")
        approvals = policy.get("approved_data_types", [])
        if not isinstance(approvals, list):
            return denied("data-type approval list unavailable or invalid")
        for grant in grants:
            validate_grant(grant)
        for approval in approvals:
            validate_data_type_approval(approval)
        ids = [grant["id"] for grant in grants] + [approval["id"] for approval in approvals]
        if len(set(ids)) != len(ids):
            return denied("duplicate grant or approval IDs")
        matches = [grant for grant in grants if all(grant[k] == record[k] for k in IDENTITY)
                   and all(grant["destination"][k] == destination[k] for k in ("repository", "branch"))]
        if any(grant["revoked"] for grant in matches):
            return denied("grant revoked; canonical reinstatement required")

        scoped_approvals = []
        if required_types is not None:
            scoped_approvals = [
                approval for approval in approvals
                if approval["data_type"].strip().casefold() in required_types
                and all(approval[key] == record[key] for key in IDENTITY[:2])
                and all(approval["destination"][key] == destination[key]
                        for key in ("repository", "branch"))
            ]
            if any(approval["revoked"] for approval in scoped_approvals):
                return denied("data-type approval revoked; canonical reinstatement required")

        if task_grant is not None:
            grant = validate_grant(task_grant)
            return grant_result(grant, "task-only", task_only=True)

        if len(matches) > 1:
            return denied("missing or ambiguous grant")
        if matches:
            return grant_result(matches[0], "persistent")

        if not approvals:
            return denied("missing or ambiguous grant")
        if required_types is None:
            return denied("data types unavailable for category approval")

        applicable = [
            approval for approval in scoped_approvals
            if now >= instant(approval["granted_at"])
            and (approval["expires_at"] is None or now < instant(approval["expires_at"]))
        ]
        if any(approval["authorized_by"] != policy["owner"] for approval in applicable):
            return denied("data-type approval author differs from authorization owner")
        by_type = {}
        for approval in applicable:
            data_type = approval["data_type"].strip().casefold()
            by_type.setdefault(data_type, []).append(approval)
        duplicates = sorted(data_type for data_type, entries in by_type.items() if len(entries) > 1)
        if duplicates:
            return denied(f"multiple effective approvals for data type: {', '.join(duplicates)}")
        missing_types = sorted(required_types - by_type.keys())
        if missing_types:
            return denied(f"no effective approval for data type: {', '.join(missing_types)}")
        approved_classes = set()
        used_ids = []
        for data_type in sorted(required_types):
            approval = by_type[data_type][0]
            approved_classes.update(classes(approval["sensitivity_classes"]))
            used_ids.append(approval["id"])
        uncovered_classes = sorted(sensitivities - approved_classes)
        if uncovered_classes:
            return denied(f"sensitivity exceeds data-type approvals: {', '.join(uncovered_classes)}")
        return {
            "allowed": True,
            "approval_ids": sorted(used_ids),
            "authorization_scope": "approved-data-types",
        }
    except (ValueError, TypeError, KeyError) as exc:
        return denied(str(exc))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        type=Path,
        help="run-local JSON: profile, eligible record, destination, at, optional task_grant",
    )
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
