#!/usr/bin/env python3
"""Check independently downloaded raw/base64 bytes against expected size and SHA-256."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re


def verified_bytes(payload, encoding, byte_size, sha256):
    if not isinstance(payload, bytes):
        raise ValueError("download payload must be bytes")
    if type(byte_size) is not int or byte_size < 0:
        raise ValueError("expected byte_size must be a nonnegative integer")
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError("expected sha256 must be lowercase hexadecimal")
    if encoding == "base64":
        try:
            data = base64.b64decode(b"".join(payload.split()), validate=True)
        except binascii.Error as exc:
            raise ValueError("invalid base64 download") from exc
    elif encoding == "raw":
        data = payload
    else:
        raise ValueError("unsupported download encoding")
    if len(data) != byte_size or hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError("download size or SHA-256 mismatch")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path)
    parser.add_argument("--encoding", choices=("raw", "base64"), default="raw")
    parser.add_argument("--byte-size", type=int, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, help="new isolated scratch file; existing files are never overwritten")
    args = parser.parse_args()
    try:
        if args.payload.is_symlink():
            raise ValueError("download payload must not be a symlink")
        data = verified_bytes(args.payload.read_bytes(), args.encoding, args.byte_size, args.sha256)
        if args.output:
            with args.output.open("xb") as handle:
                handle.write(data)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"FAIL {exc}\n")
    print(json.dumps({"status": "bytes-match", "byte_size": len(data), "sha256": hashlib.sha256(data).hexdigest()}))


if __name__ == "__main__":
    main()
