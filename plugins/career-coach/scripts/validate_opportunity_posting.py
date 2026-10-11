#!/usr/bin/env python3
"""Check deterministic metadata and GitHub message invariants before posting publication."""

from __future__ import annotations

import argparse
from datetime import date
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


REQUIRED_FIELDS = (
    "Opportunity ID",
    "Employer / role",
    "Source website",
    "Source identity",
    "Captured",
    "Completeness",
    "Storage provider",
    "Canonical path",
    "Canonical link",
    "Content type",
)
OPPORTUNITY_ID = re.compile(r"O-\d{4}-\d{2}-\d{2}-\d{2}")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
FIELD = re.compile(r"^- \*\*(.+?):\*\*\s*(.*)$")
CONTENT_HEADINGS = {
    "full posting text": "## Full Job Posting Text",
    "source-grounded summary": "## Source-grounded Summary",
}


def validate_posting(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0] != "# Captured Opportunity Description":
        errors.append(f"{path.name}: missing captured-opportunity heading")

    content_heading_indexes = [
        index for index, line in enumerate(lines) if line in CONTENT_HEADINGS.values()
    ]
    if len(content_heading_indexes) != 1:
        errors.append(f"{path.name}: expected one posting content heading")
        metadata_lines = lines[1:]
    else:
        metadata_lines = lines[1:content_heading_indexes[0]]

    metadata: dict[str, list[str]] = {}
    for line in metadata_lines:
        match = FIELD.match(line)
        if match:
            metadata.setdefault(match.group(1), []).append(match.group(2).strip())

    for field in REQUIRED_FIELDS:
        values = metadata.get(field, [])
        if len(values) != 1 or not values[0]:
            errors.append(f"{path.name}: expected one non-empty {field} field")

    opportunity_id = metadata.get("Opportunity ID", [""])[0].strip("`")
    if not OPPORTUNITY_ID.fullmatch(opportunity_id):
        errors.append(f"{path.name}: invalid Opportunity ID")
    elif not path.name.startswith(f"{opportunity_id} -- ") or not path.name.endswith(".md"):
        errors.append(f"{path.name}: filename does not match Opportunity ID")

    captured = metadata.get("Captured", [""])[0]
    if captured != "Unknown":
        try:
            if not DATE.fullmatch(captured):
                raise ValueError
            date.fromisoformat(captured)
        except ValueError:
            errors.append(f"{path.name}: Captured must be a valid ISO date or Unknown")

    content_type = metadata.get("Content type", [""])[0].strip("`").lower()
    expected_heading = CONTENT_HEADINGS.get(content_type)
    if expected_heading and len(content_heading_indexes) == 1:
        if lines[content_heading_indexes[0]] != expected_heading:
            errors.append(f"{path.name}: content heading does not match Content type")
        if not "\n".join(lines[content_heading_indexes[0] + 1 :]).strip():
            errors.append(f"{path.name}: posting content is empty")
    elif content_type:
        errors.append(f"{path.name}: unsupported Content type")

    canonical_path = metadata.get("Canonical path", [""])[0].strip("`")
    if canonical_path and Path(canonical_path).name != path.name:
        errors.append(f"{path.name}: Canonical path does not end with this filename")

    provider = metadata.get("Storage provider", [""])[0].strip("`").lower()
    if provider == "github":
        for field in ("Repository", "Branch"):
            values = metadata.get(field, [])
            if len(values) != 1 or not values[0]:
                errors.append(f"{path.name}: GitHub posting requires one {field} field")
        repository = metadata.get("Repository", [""])[0].strip("`").strip("/")
        branch = metadata.get("Branch", [""])[0].strip("`").strip("/")
        link = metadata.get("Canonical link", [""])[0].strip("<>")
        if repository and branch and canonical_path and link:
            parsed = urlsplit(link)
            repo_parts = repository.split("/")
            prefix = repo_parts + ["blob"] + branch.split("/")
            link_parts = parsed.path.lstrip("/").split("/")
            if parsed.netloc.lower() != "github.com" or link_parts[: len(prefix)] != prefix:
                errors.append(f"{path.name}: Canonical link disagrees with Repository or Branch")
            elif unquote("/".join(link_parts[len(prefix) :])) != canonical_path:
                errors.append(f"{path.name}: Canonical link disagrees with Canonical path")

    return errors


def expected_message(operation: str, count: int) -> str:
    if operation == "add":
        return f"Added {count} canonical career-opportunities record(s)"
    if operation == "update":
        return "Updated canonical career-opportunities records"
    raise ValueError(f"unsupported operation: {operation}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("GitHub", "other"), required=True)
    parser.add_argument("--operation", choices=("add", "update"), required=True)
    parser.add_argument("--message", required=True, help="the exact proposed commit message")
    parser.add_argument("--body", default="", help="the exact proposed commit body")
    parser.add_argument("files", nargs="+", type=Path, help="canonical posting files in this commit")
    args = parser.parse_args(argv)

    errors: list[str] = []
    ids: set[str] = set()
    for path in args.files:
        if not path.is_file():
            errors.append(f"{path}: file does not exist")
            continue
        file_errors = validate_posting(path, path.read_text(encoding="utf-8"))
        errors.extend(file_errors)
        if not file_errors:
            match = OPPORTUNITY_ID.match(path.name)
            if match and match.group(0) in ids:
                errors.append(f"{path.name}: duplicate Opportunity ID in commit")
            elif match:
                ids.add(match.group(0))

    if args.provider == "GitHub":
        if args.message != expected_message(args.operation, len(args.files)):
            errors.append("commit message does not match operation and posting-file count")
        if args.body:
            errors.append("GitHub Career Coach record commit body must be empty")

    if errors:
        print("REJECTED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"ACCEPTED: {len(args.files)} canonical posting file(s); metadata and message checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
