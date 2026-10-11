#!/usr/bin/env python3
"""Read-only, secret-safe preflight for application identity in a data restore.

This is intentionally narrower than full deployment configuration validation:
endpoint addresses and storage/database credentials can legitimately differ on a
replacement host. Persistent cryptographic identities must not silently change.
"""
from __future__ import annotations

import argparse
import hmac
import os
import stat
import tempfile
from pathlib import Path

CRITICAL_KEYS = (
    "DJANGO_SECRET_KEY",
    "AUDIT_INTEGRITY_KEY",
    "MFA_ENCRYPTION_KEY",
    "S3_BUCKET",
)
REMEDIATION = (
    "ERROR: restore configuration is incompatible with the backup; no services "
    "or data were changed. Restore the approved original signing/integrity/MFA "
    "keys and S3 bucket identity, or follow a separately reviewed key-migration "
    "procedure. Do not bypass this check."
)


def read_values(path: Path) -> dict[str, str]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("unsafe file type or permissions")
    values: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            record = line.strip()
            if not record or record.startswith("#"):
                continue
            if record.startswith("export "):
                record = record[7:].strip()
            if "=" not in record:
                raise ValueError("invalid configuration syntax")
            key, value = record.split("=", 1)
            key = key.strip()
            if not key or key in values or any(char.isspace() for char in key):
                raise ValueError("invalid or repeated environment key")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            values[key] = value
    return values


def compatible(active: Path, backup: Path) -> bool:
    # Access only in memory, never log, hash, export or persist secret values.
    left = read_values(active)
    right = read_values(backup)
    return all(
        bool(left.get(key)) and bool(right.get(key))
        and hmac.compare_digest(left[key], right[key])
        for key in CRITICAL_KEYS
    )


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="grc-recovery-config-") as directory:
        root = Path(directory)
        active, backup = root / "active.env", root / "backup.env"
        data = {
            "DJANGO_SECRET_KEY": "synthetic-django-key-for-test",
            "AUDIT_INTEGRITY_KEY": "synthetic-audit-key-for-test",
            "MFA_ENCRYPTION_KEY": "synthetic-mfa-key-for-test",
            "S3_BUCKET": "synthetic-evidence-bucket",
            "POSTGRES_PASSWORD": "synthetic-source-password",
            "S3_SECRET_KEY": "synthetic-source-s3-password",
        }

        def write(path: Path, values: dict[str, str]) -> None:
            path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
            path.chmod(0o600)

        write(active, data)
        write(backup, data)
        assert compatible(active, backup)

        # Host-specific database/S3 access credentials may be independently rotated.
        replacement = dict(data, POSTGRES_PASSWORD="new-host-pg", S3_SECRET_KEY="new-host-s3")
        write(active, replacement)
        assert compatible(active, backup)
        for key in CRITICAL_KEYS:
            bad = dict(replacement, **{key: "incorrect-key-or-bucket"})
            write(active, bad)
            assert not compatible(active, backup), key
        for key in CRITICAL_KEYS:
            missing = {k: v for k, v in replacement.items() if k != key}
            write(active, missing)
            assert not compatible(active, backup), key

        write(active, replacement)
        active.chmod(0o644)
        try:
            compatible(active, backup)
        except ValueError:
            pass
        else:
            raise AssertionError("insecure active env accepted")
        active.chmod(0o600)
        link = root / "linked.env"
        link.symlink_to(active)
        try:
            compatible(link, backup)
        except ValueError:
            pass
        else:
            raise AssertionError("symlink active env accepted")
        with active.open("a", encoding="utf-8") as file:
            file.write("S3_BUCKET=duplicate\n")
        try:
            compatible(active, backup)
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate env key accepted")
    print("restore critical configuration compatibility self-test: PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only restore identity compatibility preflight.")
    parser.add_argument("--active", type=Path)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.active is None or args.backup is None:
        parser.error("--active and --backup are required together")
    try:
        valid = compatible(args.active, args.backup)
    except (OSError, UnicodeError, ValueError):
        valid = False
    if not valid:
        print(REMEDIATION)
        return 4
    print("Restore configuration compatibility: PASS (values not disclosed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
