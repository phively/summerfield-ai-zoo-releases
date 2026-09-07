#!/usr/bin/env python3
"""Check a UTF-8 instruction artifact against target and hard character limits."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence


DEFAULT_LIMIT = 8000
DEFAULT_TARGET = 7600


def count_characters(path: Path) -> int:
    """Count Unicode code points exactly as stored, including line endings."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return len(handle.read())


def classify(count: int, target: int, limit: int) -> str:
    if count > limit:
        return "OVER_LIMIT"
    if count > target:
        return "WITHIN_LIMIT_ABOVE_TARGET"
    return "WITHIN_TARGET"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="UTF-8 instruction artifact to check")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="hard character limit")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET, help="preferred working target")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit < 1 or args.target < 1:
        raise SystemExit("limit and target must be positive")
    if args.target > args.limit:
        raise SystemExit("target cannot exceed limit")

    count = count_characters(args.path)
    status = classify(count, args.target, args.limit)
    print(f"{status}: {count} characters (target {args.target}, limit {args.limit})")
    return 1 if count > args.limit else 0


if __name__ == "__main__":
    raise SystemExit(main())
