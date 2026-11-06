#!/usr/bin/env python3
"""Select declared backup sources without treating inventory as authority."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


IDENTITY = ("source_provider", "source_container", "source_id")


class ScopeError(ValueError):
    pass


def text(value):
    return isinstance(value, str) and bool(value.strip())


def identity(value, field):
    if not isinstance(value, dict):
        raise ScopeError(f"{field} must be an identity object")
    if any(not text(value.get(name)) for name in IDENTITY):
        raise ScopeError(f"{field} requires {', '.join(IDENTITY)}")
    return {name: value[name] for name in IDENTITY}


def key(value):
    return tuple(value[name] for name in IDENTITY)


def _gap(kind, *, record=None, owner=None, reference=None, state=None):
    result = {"kind": kind}
    if record is not None:
        result["identity"] = record
    if owner is not None:
        result["from"] = owner
    if reference is not None:
        result["reference"] = reference
    if state is not None:
        result["state"] = state
    return result


def _basis_key(item):
    return json.dumps(item, sort_keys=True, separators=(",", ":"))


def select_sources(packet):
    """Return eligible identities and required-source coverage gaps.

    ``canonical_mentions`` contains already-resolved evidence from canonical
    files. This helper does not search a provider, authenticate that evidence,
    infer identity from a filename, or recursively follow supporting files.
    """
    if (
        not isinstance(packet, dict)
        or type(packet.get("schema_version")) is not int
        or packet["schema_version"] != 1
    ):
        raise ScopeError("input requires schema_version 1")

    profile = identity(packet.get("profile"), "profile")
    list_fields = (
        "canonical_records",
        "canonical_mentions",
        "user_designations",
        "excluded",
        "candidates",
    )
    for name in list_fields:
        if not isinstance(packet.get(name), list):
            raise ScopeError(f"{name} must be a list")

    candidates = {}
    for index, value in enumerate(packet["candidates"]):
        record = identity(value, f"candidates[{index}]")
        candidates.setdefault(key(record), record)

    exclusions = {
        key(identity(value, f"excluded[{index}]"))
        for index, value in enumerate(packet["excluded"])
    }
    selected = {}
    gaps = []

    def include(record, basis, *, required_kind, owner=None, reference=None):
        record_key = key(record)
        if record_key in exclusions:
            gaps.append(_gap(
                "excluded-required-record",
                record=record,
                owner=owner,
                reference=reference,
            ))
            return
        if record_key not in candidates:
            gaps.append(_gap(required_kind, record=record, owner=owner, reference=reference))
            return
        entry = selected.setdefault(record_key, {"identity": record, "inclusion_basis": []})
        if basis not in entry["inclusion_basis"]:
            entry["inclusion_basis"].append(basis)

    include(profile, {"kind": "canonical-profile"}, required_kind="profile-outside-inventory")

    canonical = {key(profile): profile}
    for index, value in enumerate(packet["canonical_records"]):
        record = identity(value, f"canonical_records[{index}]")
        if (
            not isinstance(value, dict)
            or not text(value.get("owner"))
            or not text(value.get("evidence_reference"))
        ):
            raise ScopeError(f"canonical_records[{index}] requires owner and evidence_reference")
        canonical.setdefault(key(record), record)
        include(
            record,
            {
                "kind": "canonical-record",
                "owner": value["owner"],
                "reference": value["evidence_reference"],
            },
            required_kind="canonical-record-outside-inventory",
        )

    for index, value in enumerate(packet["user_designations"]):
        if not isinstance(value, dict) or not text(value.get("designation_reference")):
            raise ScopeError(f"user_designations[{index}] requires designation_reference")
        record = identity(value, f"user_designations[{index}]")
        include(
            record,
            {"kind": "user-designation", "reference": value["designation_reference"]},
            required_kind="designated-record-outside-inventory",
            reference=value["designation_reference"],
        )

    grouped_mentions = {}
    valid_states = {"resolved", "ambiguous", "inaccessible", "not-found", "out-of-scope"}
    for index, value in enumerate(packet["canonical_mentions"]):
        if not isinstance(value, dict) or not text(value.get("reference")):
            raise ScopeError(f"canonical_mentions[{index}] requires reference")
        owner = identity(value.get("from"), f"canonical_mentions[{index}].from")
        if key(owner) not in canonical:
            continue
        state = value.get("state")
        if not isinstance(state, str) or state not in valid_states:
            raise ScopeError(f"canonical_mentions[{index}].state is invalid")
        targets_value = value.get("targets")
        if not isinstance(targets_value, list):
            raise ScopeError(f"canonical_mentions[{index}].targets must be a list")
        targets = [
            identity(target, f"canonical_mentions[{index}].targets[{target_index}]")
            for target_index, target in enumerate(targets_value)
        ]
        mention_key = (key(owner), value["reference"])
        grouped_mentions.setdefault(mention_key, []).append(
            {"from": owner, "reference": value["reference"], "state": state, "targets": targets}
        )

    for (owner_key, reference), rows in sorted(grouped_mentions.items()):
        owner = canonical[owner_key]
        states = {row["state"] for row in rows}
        targets = {key(target): target for row in rows for target in row["targets"]}
        if len(states) != 1:
            gaps.append(_gap(
                "conflicting-reference-resolution", owner=owner, reference=reference,
            ))
            continue
        state = next(iter(states))
        if state == "resolved" and len(targets) > 1:
            gaps.append(_gap(
                "conflicting-reference-resolution", owner=owner, reference=reference,
            ))
            continue
        target_list = list(targets.values())
        if state != "resolved":
            gap_kind = {
                "ambiguous": "ambiguous-reference",
                "inaccessible": "inaccessible-reference",
                "not-found": "missing-reference",
                "out-of-scope": "out-of-scope-reference",
            }[state]
            gaps.append(_gap(gap_kind, owner=owner, reference=reference, state=state))
            continue
        if len(target_list) != 1:
            gaps.append(_gap(
                "ambiguous-reference",
                owner=owner,
                reference=reference,
                state="ambiguous",
            ))
            continue
        target = target_list[0]
        include(
            target,
            {"kind": "canonical-mention", "from": owner, "reference": reference},
            required_kind="reference-outside-inventory",
            owner=owner,
            reference=reference,
        )

    result_selected = []
    for record_key in sorted(selected):
        entry = selected[record_key]
        entry["inclusion_basis"].sort(key=_basis_key)
        result_selected.append(entry)

    outside_scope = []
    for record_key in sorted(candidates):
        if record_key in selected:
            continue
        outside_scope.append({
            "identity": candidates[record_key],
            "reason": "excluded" if record_key in exclusions else "no-eligibility-basis",
        })

    gaps.sort(key=_basis_key)
    return {
        "schema_version": 1,
        "complete": not gaps,
        "selected": result_selected,
        "outside_scope": outside_scope,
        "coverage_gaps": gaps,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="run-local source-scope JSON")
    args = parser.parse_args(argv)
    try:
        packet = json.loads(args.input.read_text(encoding="utf-8"))
        result = select_sources(packet)
    except (OSError, json.JSONDecodeError, ScopeError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
