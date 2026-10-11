#!/usr/bin/env python3
"""Check exact, user-authorized reuse of a manual GitHub raw-download check."""
import argparse
from datetime import date
import json
from pathlib import Path
import re


def eligible(entry, record, destination, remote_blob_id, at):
    if not all(isinstance(value, dict) for value in (entry, record, destination)):
        return False
    if entry.get("reuse_policy") != "until-identity-version-or-content-changes" or entry.get("revoked") is not False:
        return False
    if entry.get("basis") != "user-reported-github-raw-download":
        return False
    for field in ("id", "verified_by", "evidence_reference"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            return False
    try:
        if date.fromisoformat(entry["verified_on"]) > date.fromisoformat(at):
            return False
    except (KeyError, TypeError, ValueError):
        return False
    if entry.get("destination") != destination or set(destination) != {"repository", "branch"}:
        return False
    if any(not isinstance(value, str) or not value for value in destination.values()):
        return False
    for field in ("source_provider", "source_container", "source_id", "repository_path", "sha256"):
        if not isinstance(entry.get(field), str) or not entry[field] or entry[field] != record.get(field):
            return False
    if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
        return False
    if type(entry.get("byte_size")) is not int or type(record.get("byte_size")) is not int:
        return False
    if entry["byte_size"] < 0 or entry["byte_size"] != record["byte_size"]:
        return False
    if ("source_version" in entry) != ("source_version" in record):
        return False
    if type(entry.get("source_version")) is not type(record.get("source_version")) or entry.get("source_version") != record.get("source_version"):
        return False
    blob = entry.get("remote_blob_id")
    return isinstance(blob, str) and bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", blob)) and blob == remote_blob_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    try:
        packet = json.loads(args.packet.read_text(encoding="utf-8"))
        result = eligible(packet.get("entry"), packet.get("record"), packet.get("destination"),
                          packet.get("remote_blob_id"), packet.get("at"))
    except (OSError, ValueError, AttributeError):
        result = False
    print(json.dumps({"manual_verification_reusable": result}))
    raise SystemExit(0 if result else 1)


if __name__ == "__main__":
    main()
