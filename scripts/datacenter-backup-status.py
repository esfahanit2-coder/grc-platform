#!/usr/bin/env python3
"""Read-only backup freshness and optional checksum probe; never print customer data.

Freshness and checksums do NOT establish that a backup is restorable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REQUIRED = frozenset({
    "postgres.dump", "objectstore.zip", "config.env",
    "docker-compose.pilot.yml", "images.txt", "source-commit.txt",
    "backup-manifest.json",
})
ALLOWED = REQUIRED | {"docker-compose.pilot.tls.yml"}
NAME_RE = re.compile(r"[A-Za-z0-9._-]+\Z")
HASH_LINE_RE = re.compile(r"([a-fA-F0-9]{64})  (.+)\Z")
SHA_RE = re.compile(r"[a-fA-F0-9]{40}\Z")
SCHEMA = "grc-backup-freshness-v1"


def utc_time(value: object) -> datetime | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def regular_file(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and info.st_size > 0


def safe_directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except OSError:
        return False


def read_json(path: Path) -> dict | None:
    if not regular_file(path):
        return None
    try:
        if path.stat().st_size > 64 * 1024:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def integrity_catalog(directory: Path) -> dict[str, str] | None:
    path = directory / "SHA256SUMS"
    if not regular_file(path):
        return None
    try:
        if path.stat().st_size > 16 * 1024:
            return None
        rows = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError):
        return None
    checks: dict[str, str] = {}
    for line in rows:
        match = HASH_LINE_RE.fullmatch(line)
        if not match:
            return None
        sha, name = match.groups()
        # Disallow path traversal, symlinks, unknown names and duplicate entries.
        if name not in ALLOWED or name in checks or not regular_file(directory / name):
            return None
        checks[name] = sha.lower()
    if not REQUIRED.issubset(checks) or len(checks) not in {len(REQUIRED), len(ALLOWED)}:
        return None
    return checks


def hash_matches(directory: Path, catalog: dict[str, str]) -> bool:
    for name, expected in catalog.items():
        digest = hashlib.sha256()
        try:
            with (directory / name).open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
        except OSError:
            return False
        if digest.hexdigest() != expected:
            return False
    return True


def backup_probe(path: Path, now: datetime) -> dict | None:
    if not safe_directory(path) or not NAME_RE.fullmatch(path.name):
        return None
    manifest = read_json(path / "backup-manifest.json")
    observation = read_json(path / "backup-observation.json")
    if not manifest or not observation:
        return None
    if manifest.get("schema") != "grc-backup-manifest-v1":
        return None
    if manifest.get("backup_name") != path.name or observation.get("backup_name") != path.name:
        return None
    if not SHA_RE.fullmatch(str(manifest.get("source_commit", ""))):
        return None
    postgres = manifest.get("postgres")
    if not isinstance(postgres, dict) or postgres.get("dump_format") != "custom":
        return None
    if observation.get("contains_secret_bearing_config") is not True:
        return None
    if manifest.get("release_consistent_quiesce") is not observation.get("release_consistent_quiesce"):
        return None
    created = utc_time(manifest.get("created_at"))
    finished = utc_time(observation.get("completed_at"))
    if not created or not finished or created > finished or finished > now + timedelta(minutes=5):
        return None
    if (finished - created).total_seconds() > 7 * 86400:
        return None
    if not all(regular_file(path / name) for name in REQUIRED):
        return None
    if integrity_catalog(path) is None:
        return None
    age = max(0, (now - finished).total_seconds() / 3600)
    return {
        "name": path.name, "age_hours": age,
        "completed_at": finished.isoformat(),
        "release_consistent": manifest["release_consistent_quiesce"],
    }


def check(backups_dir: Path, *, max_age_hours: float = 26,
          verify_hashes: bool = False, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    result = {
        "schema": SCHEMA, "healthy": False, "max_age_hours": max_age_hours,
        "checked_hashes": verify_hashes, "latest_age_hours": None,
        "latest_completed_at": None, "release_consistent": None,
        "reason": "no_valid_backup",
    }
    if not safe_directory(backups_dir):
        result["reason"] = "backup_directory_missing_or_unsafe"
        return result
    try:
        entries = list(backups_dir.iterdir())
    except OSError:
        result["reason"] = "backup_directory_unreadable"
        return result
    if len(entries) > 20000:
        result["reason"] = "backup_directory_too_large"
        return result
    valid = []
    for path in entries:
        if not NAME_RE.fullmatch(path.name) or not safe_directory(path):
            continue
        probe = backup_probe(path, now)
        if probe is not None:
            valid.append(probe)
    if not valid:
        return result
    latest = max(valid, key=lambda row: row["completed_at"])
    result.update(
        latest_age_hours=round(latest["age_hours"], 2),
        latest_completed_at=latest["completed_at"],
        release_consistent=latest["release_consistent"],
    )
    # Expensive SHA scan touches only latest eligible backup. The catalog is
    # unsigned: SHA detects accidental damage but cannot prove authenticity.
    if verify_hashes:
        directory = backups_dir / latest["name"]
        catalog = integrity_catalog(directory)
        if catalog is None or not hash_matches(directory, catalog):
            result["reason"] = "backup_checksum_mismatch"
            return result
    if latest["age_hours"] > max_age_hours:
        result["reason"] = "backup_stale"
    elif not latest["release_consistent"]:
        result["reason"] = "latest_backup_not_release_consistent"
    else:
        result["reason"] = "fresh_metadata_and_files"
        result["healthy"] = True
    return result


def self_test() -> None:
    now = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        assert check(root, now=now)["reason"] == "no_valid_backup"
        backup = root / "20261010T100000Z"
        backup.mkdir()
        for name in REQUIRED - {"backup-manifest.json"}:
            (backup / name).write_bytes(b"sample")
        manifest = {
            "schema": "grc-backup-manifest-v1", "backup_name": backup.name,
            "source_commit": "a" * 40, "created_at": "2026-10-10T10:00:00Z",
            "postgres": {"dump_format": "custom"}, "release_consistent_quiesce": True,
        }
        (backup / "backup-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        observation = {
            "backup_name": backup.name, "completed_at": "2026-10-10T10:15:00Z",
            "contains_secret_bearing_config": True, "release_consistent_quiesce": True,
        }
        (backup / "backup-observation.json").write_text(json.dumps(observation), encoding="utf-8")

        def rewrite_catalog():
            (backup / "SHA256SUMS").write_text("".join(
                f"{hashlib.sha256((backup / name).read_bytes()).hexdigest()}  {name}\n"
                for name in sorted(REQUIRED)
            ), encoding="ascii")

        rewrite_catalog()
        assert check(root, now=now, verify_hashes=True)["healthy"]
        assert check(root, now=now + timedelta(days=3))["reason"] == "backup_stale"
        # Never round monitoring thresholds before deciding if a backup is stale.
        assert check(root, now=now + timedelta(hours=26, seconds=1))["reason"] == "backup_stale"
        (backup / "postgres.dump").write_bytes(b"modified")
        assert check(root, now=now)["healthy"]  # Metadata alone cannot detect damaged bytes.
        assert check(root, now=now, verify_hashes=True)["reason"] == "backup_checksum_mismatch"
        (backup / "postgres.dump").write_bytes(b"sample")
        rewrite_catalog()
        (backup / "config.env").unlink()
        (backup / "config.env").symlink_to(backup / "postgres.dump")
        assert check(root, now=now)["reason"] == "no_valid_backup"
        (backup / "config.env").unlink()
        (backup / "config.env").write_bytes(b"sample")
        (backup / "SHA256SUMS").write_text("../../secrets\n", encoding="ascii")
        assert check(root, now=now)["reason"] == "no_valid_backup"
        rewrite_catalog()
        observation["completed_at"] = "2026-10-12T10:15:00Z"
        (backup / "backup-observation.json").write_text(json.dumps(observation), encoding="utf-8")
        assert check(root, now=now)["reason"] == "no_valid_backup"
        observation["completed_at"] = "2026-10-10T10:15:00Z"
        observation["release_consistent_quiesce"] = False
        (backup / "backup-observation.json").write_text(json.dumps(observation), encoding="utf-8")
        assert check(root, now=now)["reason"] == "no_valid_backup"
    print("datacenter backup freshness and integrity probe self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Secret-safe read-only backup freshness; does not prove recoverability",
    )
    parser.add_argument(
        "--backups-dir", default=str(Path(__file__).resolve().parents[1] / "backups"),
    )
    parser.add_argument("--max-age-hours", type=float, default=26)
    parser.add_argument("--verify-hashes", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not 1 <= args.max_age_hours <= 24 * 365:
        parser.error("--max-age-hours must be between 1 and 8760")
    outcome = check(
        Path(args.backups_dir), max_age_hours=args.max_age_hours,
        verify_hashes=args.verify_hashes,
    )
    print(json.dumps(outcome, indent=2, sort_keys=True))
    return 0 if outcome["healthy"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
