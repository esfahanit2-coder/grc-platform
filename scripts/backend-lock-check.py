#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "backend/requirements.txt"
LOCK = ROOT / "backend/requirements.lock.txt"
HASH_RE = re.compile(r"^# source-sha256: ([0-9a-f]{64})$")
PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+==[^=<>!~\s]+$")


def source_digest() -> str:
    return hashlib.sha256(SOURCE.read_bytes()).hexdigest()


def validate() -> list[str]:
    errors: list[str] = []
    lines = LOCK.read_text(encoding="utf-8").splitlines()
    expected = None
    pins: list[str] = []
    for raw in lines:
        match = HASH_RE.fullmatch(raw.strip())
        if match:
            if expected is not None:
                errors.append("requirements lock contains multiple source-sha256 headers")
            expected = match.group(1)
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not PIN_RE.fullmatch(line):
            errors.append(f"requirements lock contains a non-exact pin: {line}")
        pins.append(line.lower())
    if expected is None:
        errors.append("requirements lock is missing source-sha256 header")
    elif expected != source_digest():
        errors.append("requirements.txt changed without refreshing requirements.lock.txt")
    if not pins:
        errors.append("requirements lock contains no pinned packages")
    if len(pins) != len(set(pins)):
        errors.append("requirements lock contains duplicate exact pins")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the exact Python server dependency lock.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print("backend requirements lock is synchronized and exact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
