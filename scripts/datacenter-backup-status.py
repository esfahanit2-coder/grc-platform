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
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REQUIRED = frozenset({
    "postgres.dump", "objectstore.zip", "config.env",
    "docker-compose.pilot.yml", "images.txt", "source-commit.txt",
    "backup-manifest.json",
})
ALLOWED = REQUIRED | {"docker-compose.pilot.tls.yml"}
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
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


def check_restore(backups_dir: Path, name: str, *,
                  now: datetime | None = None) -> dict:
    """Pre-destructive guard for a named backup, irrespective of backup age.

    The result never discloses a backup name/path, archive object names or data.
    """
    now = now or datetime.now(timezone.utc)
    report = {
        "schema": "grc-restore-preflight-v1", "healthy": False,
        "checked_hashes": True, "validated_object_archive": False,
        "release_consistent": None, "reason": "invalid_backup_name_or_directory",
    }
    if not NAME_RE.fullmatch(name) or not safe_directory(backups_dir):
        return report
    selected = backups_dir / name
    probe = backup_probe(selected, now)
    if probe is None:
        report["reason"] = "backup_metadata_or_files_invalid"
        return report
    if not probe["release_consistent"]:
        report["reason"] = "backup_not_release_consistent"
        return report
    report["release_consistent"] = True
    manifest = read_json(selected / "backup-manifest.json")
    pg = manifest.get("postgres") if manifest else None
    if (
        not isinstance(pg, dict) or isinstance(pg.get("major"), bool)
        or not isinstance(pg.get("major"), int) or not 1 <= pg["major"] <= 99
        or manifest.get("objectstore_archive_schema") != 1
    ):
        report["reason"] = "backup_format_unsupported"
        return report
    try:
        source_path = selected / "source-commit.txt"
        if source_path.stat().st_size > 100 or (
            source_path.read_text(encoding="ascii").strip()
            != manifest["source_commit"]
        ):
            report["reason"] = "backup_release_identity_mismatch"
            return report
        with (selected / "postgres.dump").open("rb") as stream:
            if stream.read(5) != b"PGDMP":
                report["reason"] = "postgres_custom_dump_header_invalid"
                return report
    except (OSError, UnicodeError, KeyError):
        report["reason"] = "backup_release_identity_mismatch"
        return report

    catalog = integrity_catalog(selected)
    if catalog is None or not hash_matches(selected, catalog):
        report["reason"] = "backup_checksum_mismatch"
        return report

    # Validate the manifest and every ZIP member *before* a restore script can
    # delete/replace the target object-storage contents.
    try:
        with zipfile.ZipFile(selected / "objectstore.zip") as archive:
            members = archive.infolist()
            if len(members) > 1000000:
                raise ValueError("too many archive members")
            files = {row.filename: row for row in members}
            if len(files) != len(members) or "manifest.json" not in files:
                raise ValueError("ambiguous ZIP member")
            index = files["manifest.json"]
            if index.file_size > 32 * 1024 * 1024:
                raise ValueError("unbounded archive manifest")
            manifest_bytes = archive.read(index)
            archive_manifest = json.loads(manifest_bytes)
            if (
                not isinstance(archive_manifest, dict)
                or archive_manifest.get("schema_version") != 1
                or not isinstance(archive_manifest.get("objects"), list)
                or archive_manifest.get("object_count") != len(archive_manifest["objects"])
                or isinstance(archive_manifest["object_count"], bool)
            ):
                raise ValueError("invalid archive schema")
            rows = archive_manifest["objects"]
            if len(files) != len(rows) + 1:
                raise ValueError("unexpected archive members")
            for index, row in enumerate(rows):
                if not isinstance(row, dict):
                    raise ValueError("malformed object entry")
                member_name = f"objects/{index:08d}.bin"
                expected_size = row.get("size")
                expected_digest = row.get("sha256")
                if (
                    row.get("archive_name") != member_name
                    or not isinstance(row.get("key"), str) or not row["key"]
                    or isinstance(expected_size, bool) or not isinstance(expected_size, int)
                    or expected_size < 0 or member_name not in files
                    or files[member_name].file_size != expected_size
                    or not isinstance(expected_digest, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", expected_digest)
                ):
                    raise ValueError("invalid archived object contract")
                digest = hashlib.sha256()
                with archive.open(member_name) as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                if digest.hexdigest() != expected_digest:
                    raise ValueError("inner object checksum mismatch")
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, KeyError, TypeError, EOFError):
        report["reason"] = "objectstore_archive_invalid"
        return report
    report["validated_object_archive"] = True
    report["healthy"] = True
    report["reason"] = "validated_before_destructive_restore"
    return report


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
        # Recovery-specific fixture: custom-format PG header plus the real
        # S3-archive manifest contract. Age is deliberately unrestricted.
        observation["release_consistent_quiesce"] = True
        (backup / "backup-observation.json").write_text(json.dumps(observation), encoding="utf-8")
        manifest["postgres"]["major"] = 18
        manifest["objectstore_archive_schema"] = 1
        (backup / "backup-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (backup / "source-commit.txt").write_text("a" * 40 + "\n", encoding="ascii")
        (backup / "postgres.dump").write_bytes(b"PGDMPtest archive header")
        def make_zip(*, bad_digest: bool = False):
            with zipfile.ZipFile(backup / "objectstore.zip", "w") as archive:
                payload = b"sample evidence"
                archive.writestr("objects/00000000.bin", payload)
                archive.writestr("manifest.json", json.dumps({
                    "schema_version": 1, "object_count": 1,
                    "objects": [{"key": "evidence/test", "archive_name": "objects/00000000.bin",
                                 "size": len(payload),
                                 "sha256": "0" * 64 if bad_digest else hashlib.sha256(payload).hexdigest()}],
                }))
            rewrite_catalog()
        make_zip()
        assert check_restore(root, backup.name, now=now)["healthy"]
        assert check_restore(root, backup.name, now=now + timedelta(days=500))["healthy"]
        for unsafe in ("..", ".", "../other", ".hidden", "name/child", ""):
            assert not check_restore(root, unsafe, now=now)["healthy"]
        make_zip(bad_digest=True)
        assert check_restore(root, backup.name, now=now)["reason"] == "objectstore_archive_invalid"
        make_zip()
        (backup / "postgres.dump").write_bytes(b"invalid")
        rewrite_catalog()
        assert check_restore(root, backup.name, now=now)["reason"] == "postgres_custom_dump_header_invalid"
        (backup / "postgres.dump").write_bytes(b"PGDMPtest archive header")
        rewrite_catalog()
        (backup / "source-commit.txt").write_text("f" * 40, encoding="ascii")
        rewrite_catalog()
        assert check_restore(root, backup.name, now=now)["reason"] == "backup_release_identity_mismatch"
        (backup / "source-commit.txt").write_text("a" * 40 + "\n", encoding="ascii")
        rewrite_catalog()
        (backup / "objectstore.zip").unlink()
        (backup / "objectstore.zip").symlink_to(backup / "postgres.dump")
        assert check_restore(root, backup.name, now=now)["reason"] == "backup_metadata_or_files_invalid"
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
    parser.add_argument("--restore-preflight", metavar="BACKUP_NAME", help="Validate selected older backup, complete checksums and object archive before destructive restore.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not 1 <= args.max_age_hours <= 24 * 365:
        parser.error("--max-age-hours must be between 1 and 8760")
    if args.restore_preflight is not None:
        outcome = check_restore(Path(args.backups_dir), args.restore_preflight)
    else:
        outcome = check(
            Path(args.backups_dir), max_age_hours=args.max_age_hours,
            verify_hashes=args.verify_hashes,
        )
    print(json.dumps(outcome, indent=2, sort_keys=True))
    return 0 if outcome["healthy"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
