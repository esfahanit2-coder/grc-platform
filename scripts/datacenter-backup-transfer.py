#!/usr/bin/env python3
"""Optional age-encrypted custody transfer for an already validated GRC backup.

No new encryption primitives are implemented here: age performs authenticated
recipient encryption. The decryption identity must stay with the customer.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = frozenset({
    "postgres.dump", "objectstore.zip", "config.env",
    "docker-compose.pilot.yml", "images.txt", "source-commit.txt",
    "backup-manifest.json", "backup-observation.json", "SHA256SUMS",
    "docker-compose.pilot.tls.yml",
})
REQUIRED_FILES = FILES - {"docker-compose.pilot.tls.yml"}
SCHEMA = "grc-encrypted-backup-custody-v1"


def backup_status():
    spec = importlib.util.spec_from_file_location(
        "grc_backup_status", ROOT / "scripts/datacenter-backup-status.py"
    )
    if spec is None or spec.loader is None:
        raise ValueError("backup integrity validator unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def private_regular(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
        return stat.S_ISREG(mode) and not (stat.S_IMODE(mode) & 0o077)
    except OSError:
        return False


def valid_backup(root: Path, name: str) -> None:
    status = backup_status()
    if not status.NAME_RE.fullmatch(name):
        raise ValueError("invalid backup identifier")
    if status.check_restore(root / "backups", name).get("healthy") is not True:
        raise ValueError("backup is incomplete or failed integrity preflight")


def export_encrypted(root: Path, name: str, recipient: Path, output: Path) -> None:
    valid_backup(root, name)
    folder = root / "backups" / name
    if not recipient.is_file() or recipient.is_symlink():
        raise ValueError("recipient file must be an approved regular public-key file")
    if output.suffix != ".age" or not output.parent.is_dir() or output.exists() or output.is_symlink():
        raise ValueError("encrypted destination is invalid or already exists")
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("encrypted custody artifact must be outside the checkout")
    files = sorted(p for p in folder.iterdir() if p.name in FILES)
    if not REQUIRED_FILES.issubset({p.name for p in files}):
        raise ValueError("required backup entries missing")
    if any(not private_regular(p) for p in files):
        raise ValueError("backup files must be regular and mode 0600/owner-only")

    fd, temp_name = tempfile.mkstemp(prefix=".grc-encrypted-", suffix=".partial", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as ciphertext:
            proc = subprocess.Popen(
                ["age", "-R", str(recipient)],
                stdin=subprocess.PIPE, stdout=ciphertext, stderr=subprocess.DEVNULL,
            )
            try:
                assert proc.stdin is not None
                with tarfile.open(mode="w|", fileobj=proc.stdin, format=tarfile.PAX_FORMAT) as archive:
                    for path in files:
                        raw_fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                        with os.fdopen(raw_fd, "rb") as source:
                            file_stat = os.fstat(source.fileno())
                            if not stat.S_ISREG(file_stat.st_mode) or stat.S_IMODE(file_stat.st_mode) & 0o077:
                                raise ValueError("backup file changed or became unsafe")
                            entry = tarfile.TarInfo(f"{name}/{path.name}")
                            entry.size = file_stat.st_size
                            entry.mode = 0o600
                            entry.uid = entry.gid = entry.mtime = 0
                            archive.addfile(entry, fileobj=source)
                proc.stdin.close()
                if proc.wait() != 0:
                    raise ValueError("age failed to encrypt approved backup")
            except BaseException:
                proc.kill()
                proc.wait()
                raise
            ciphertext.flush()
            os.fsync(ciphertext.fileno())
        if os.stat(temp_name).st_size < 32:
            raise ValueError("encrypted output is empty")
        # Exclusive hard link prevents clobbering an existing custody artifact.
        os.link(temp_name, output)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def import_encrypted(root: Path, name: str, encrypted: Path, identity: Path) -> None:
    status = backup_status()
    if not status.NAME_RE.fullmatch(name):
        raise ValueError("invalid backup identifier")
    if not private_regular(identity):
        raise ValueError("identity file must be private and a regular file")
    if not encrypted.is_file() or encrypted.is_symlink() or encrypted.suffix != ".age":
        raise ValueError("input must be a regular encrypted envelope")
    base = root / "backups"
    if not status.safe_directory(base) or stat.S_IMODE(base.lstat().st_mode) & 0o077:
        raise ValueError("backup root is missing or not private")
    destination = base / name
    if destination.exists() or destination.is_symlink():
        raise ValueError("backup destination already exists")

    with tempfile.TemporaryDirectory(prefix=".grc-custody-stage-", dir=base) as temporary:
        staging = Path(temporary)
        selected = staging / name
        selected.mkdir(mode=0o700)
        proc = subprocess.Popen(
            ["age", "-d", "-i", str(identity), str(encrypted)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        names: set[str] = set()
        try:
            assert proc.stdout is not None
            with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
                for member in archive:
                    pieces = member.name.split("/")
                    if (
                        len(pieces) != 2 or pieces[0] != name or pieces[1] not in FILES
                        or not member.isfile() or pieces[1] in names
                        or member.size < 1 or member.size > 2 * 1024**4
                    ):
                        raise ValueError("unexpected or unsafe encrypted archive member")
                    names.add(pieces[1])
                    if member.size + 64 * 1024 * 1024 > shutil.disk_usage(staging).free:
                        raise ValueError("insufficient protected recovery storage")
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise ValueError("encrypted member cannot be read")
                    filename = selected / pieces[1]
                    fd = os.open(
                        filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                        0o600,
                    )
                    with os.fdopen(fd, "wb") as output:
                        shutil.copyfileobj(stream, output, length=1024 * 1024)
                        output.flush()
                        os.fsync(output.fileno())
            proc.stdout.close()
            if proc.wait() != 0:
                raise ValueError("envelope authentication or decryption failed")
        except BaseException:
            proc.kill()
            proc.wait()
            raise

        if not REQUIRED_FILES.issubset(names):
            raise ValueError("encrypted custody envelope lacks mandatory backup content")
        if status.check_restore(staging, name).get("healthy") is not True:
            raise ValueError("decrypted backup failed mandatory integrity validation")
        if destination.exists() or destination.is_symlink():
            raise ValueError("another backup already occupies the selected name")
        os.rename(selected, destination)


def synthetic_fixture(root: Path, name: str) -> None:
    folder = root / "backups" / name
    folder.mkdir(parents=True, mode=0o700)
    (root / "backups").chmod(0o700)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(seconds=10)).isoformat()
    end = (now - timedelta(seconds=1)).isoformat()
    sha = "a" * 40
    values: dict[str, bytes] = {
        "postgres.dump": b"PGDMP" + b"synthetic fixture (not actual SQL)",
        "config.env": b"DJANGO_SECRET_KEY=synthetic-only\n",
        "docker-compose.pilot.yml": b"services: {}\n",
        "images.txt": b"synthetic-only\n",
        "source-commit.txt": (sha + "\n").encode(),
        "backup-manifest.json": json.dumps({
            "schema": "grc-backup-manifest-v1", "backup_name": name,
            "created_at": start, "source_commit": sha, "release_version": "ci",
            "postgres": {"dump_format": "custom", "major": 18, "server_version_num": 180000},
            "release_consistent_quiesce": True, "objectstore_archive_schema": 1,
        }).encode(),
        "backup-observation.json": json.dumps({
            "backup_name": name, "completed_at": end,
            "contains_secret_bearing_config": True,
            "release_consistent_quiesce": True,
        }).encode(),
    }
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", json.dumps({
            "schema_version": 1, "object_count": 0, "objects": [],
        }))
    values["objectstore.zip"] = zipped.getvalue()
    hashes = []
    for filename, data in sorted(values.items()):
        path = folder / filename
        path.write_bytes(data)
        path.chmod(0o600)
        if filename != "backup-observation.json":
            hashes.append(f"{hashlib.sha256(data).hexdigest()}  {filename}\n")
    catalog = folder / "SHA256SUMS"
    catalog.write_text("".join(hashes), encoding="ascii")
    catalog.chmod(0o600)
    valid_backup(root, name)


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="grc-age-transfer-test-") as raw:
        sandbox = Path(raw)
        source = sandbox / "source"
        source.mkdir()
        name = "ci-private-datacenter-backup"
        synthetic_fixture(source, name)
        secret = sandbox / "age-identity.txt"
        recipient = sandbox / "recipients.txt"
        with secret.open("w", encoding="utf-8") as output:
            result = subprocess.run(["age-keygen"], stdout=output, stderr=subprocess.DEVNULL, check=False)
        assert result.returncode == 0
        secret.chmod(0o600)
        public = subprocess.run(["age-keygen", "-y", str(secret)], capture_output=True, check=True, text=True)
        recipient.write_text(public.stdout, encoding="utf-8")
        cipher = sandbox / "sealed.age"
        export_encrypted(source, name, recipient, cipher)
        assert cipher.stat().st_size > 64
        restored = sandbox / "recovered"
        (restored / "backups").mkdir(parents=True, mode=0o700)
        import_encrypted(restored, name, cipher, secret)
        valid_backup(restored, name)
        for key in REQUIRED_FILES:
            assert (source / "backups" / name / key).read_bytes() == (restored / "backups" / name / key).read_bytes()
        try:
            export_encrypted(source, name, recipient, cipher)
        except ValueError:
            pass
        else:
            raise AssertionError("existing encrypted custody file was overwritten")
        try:
            import_encrypted(restored, name, cipher, secret)
        except ValueError:
            pass
        else:
            raise AssertionError("existing recovered backup was overwritten")

        broken = sandbox / "tampered.age"
        broken.write_bytes(cipher.read_bytes()[:-16])
        empty = sandbox / "tampered-target"
        (empty / "backups").mkdir(parents=True, mode=0o700)
        try:
            import_encrypted(empty, name, broken, secret)
        except (ValueError, tarfile.TarError, OSError, EOFError):
            pass
        else:
            raise AssertionError("tampered age envelope accepted")
        assert not (empty / "backups" / name).exists()
        assert not list((empty / "backups").glob(".grc-custody-stage-*"))

        unsafe = sandbox / "unsafe.age"
        proc = subprocess.Popen(["age", "-R", str(recipient)], stdin=subprocess.PIPE, stdout=unsafe.open("wb"), stderr=subprocess.DEVNULL)
        try:
            assert proc.stdin is not None
            with tarfile.open(fileobj=proc.stdin, mode="w|") as archive:
                member = tarfile.TarInfo(f"{name}/../../escape")
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc/passwd"
                archive.addfile(member)
            proc.stdin.close()
            assert proc.wait() == 0
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        try:
            import_encrypted(empty, name, unsafe, secret)
        except (ValueError, tarfile.TarError, OSError):
            pass
        else:
            raise AssertionError("unsafe tar member accepted")
        assert not (empty / "backups" / name).exists()
    print("Encrypted age custody transfer: full synthetic roundtrip and refusal tests PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description="age-encrypted, secret-safe offline backup custody transport.")
    subs = parser.add_subparsers(dest="action", required=True)
    export = subs.add_parser("export", help="Encrypt one integrity-checked backup to a new external .age file.")
    export.add_argument("backup_name")
    export.add_argument("recipient_file", type=Path)
    export.add_argument("output", type=Path)
    restore = subs.add_parser("import", help="Decrypt into an absent backup directory, validate before publishing.")
    restore.add_argument("backup_name")
    restore.add_argument("encrypted_file", type=Path)
    restore.add_argument("identity_file", type=Path)
    subs.add_parser("self-test", help="Real ephemeral age roundtrip; requires age and age-keygen.")
    args = parser.parse_args()
    try:
        if args.action == "export":
            export_encrypted(ROOT, args.backup_name, args.recipient_file, args.output)
        elif args.action == "import":
            import_encrypted(ROOT, args.backup_name, args.encrypted_file, args.identity_file)
        else:
            self_test()
    except (OSError, ValueError, RuntimeError, tarfile.TarError, EOFError, subprocess.SubprocessError):
        print("ERROR: encrypted custody operation refused; verify source, key custody, media and storage.", file=sys.stderr)
        return 4
    if args.action != "self-test":
        print(json.dumps({"schema": SCHEMA, "action": args.action, "status": "ok",
                          "verified_backup": True, "customer_media_custody_proven": False},
                         sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
