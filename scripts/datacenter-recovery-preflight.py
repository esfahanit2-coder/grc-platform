#!/usr/bin/env python3
"""Non-destructive customer-operator recovery preflight; no Docker needed.

A healthy report is NOT authorization for restore and NOT proof of RPO/RTO,
media provenance, independent-host readiness or customer UAT.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "grc-datacenter-recovery-operator-preflight-v1"
BACKUP_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def import_script(file_name: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "scripts" / file_name)
    if spec is None or spec.loader is None:
        raise RuntimeError("operator validation module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compile_report(
    *, integrity: bool, identity: bool, source_match: bool, archive_reason: str
) -> dict:
    ready = integrity and identity and source_match
    safe_reasons = {
        "validated_before_destructive_restore",
        "invalid_backup_name_or_directory",
        "backup_metadata_or_files_invalid",
        "backup_not_release_consistent",
        "backup_format_unsupported",
        "backup_release_identity_mismatch",
        "postgres_custom_dump_header_invalid",
        "backup_checksum_mismatch",
        "objectstore_archive_invalid",
    }
    return {
        "schema": SCHEMA,
        "ready_for_operator_review": bool(ready),
        "checks": {
            "backup_integrity": {
                "ok": bool(integrity),
                "reason": archive_reason if archive_reason in safe_reasons else "backup_unavailable_or_invalid",
            },
            "critical_config_identity": {
                "ok": bool(identity),
                "reason": "compatible" if identity else "critical_identity_mismatch_or_unavailable",
            },
            "exact_source_commit": {
                "ok": bool(source_match),
                "reason": "matches" if source_match else "checkout_missing_or_release_mismatch",
            },
        },
        "boundary": (
            "Read-only local gate only; neither authorizes destructive restore nor proves "
            "customer media custody, encrypted offsite transport, full signed-release "
            "attestation, customer PKI, physical host separation, RPO/RTO or UAT."
        ),
    }


def inspect(root: Path, name: str) -> dict:
    integrity = identity = source_match = False
    archive_reason = "invalid_backup_name_or_directory"
    if not BACKUP_NAME.fullmatch(name):
        return compile_report(
            integrity=False, identity=False, source_match=False,
            archive_reason=archive_reason,
        )
    backups = root / "backups"
    selected = backups / name
    try:
        checks = import_script("datacenter-backup-status.py", "grc_backup_status")
        result = checks.check_restore(backups, name)
        integrity = result.get("healthy") is True
        archive_reason = result.get("reason", "backup_unavailable_or_invalid")
    except (OSError, UnicodeError, ValueError, RuntimeError, KeyError):
        pass
    if integrity:
        try:
            crypto = import_script(
                "datacenter-restore-config-check.py", "grc_restore_crypto"
            )
            identity = crypto.compatible(root / ".env", selected / "config.env")
        except (OSError, UnicodeError, ValueError, RuntimeError):
            identity = False
        try:
            manifest = json.loads((selected / "backup-manifest.json").read_text(encoding="utf-8"))
            source = manifest.get("source_commit")
            git = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=15, check=False,
            )
            source_match = (
                isinstance(source, str)
                and re.fullmatch(r"[0-9a-f]{40}", source) is not None
                and git.returncode == 0
                and git.stdout.strip() == source
            )
        except (OSError, UnicodeError, ValueError, subprocess.TimeoutExpired):
            source_match = False
    return compile_report(
        integrity=integrity, identity=identity, source_match=source_match,
        archive_reason=archive_reason,
    )


def self_test() -> None:
    good = compile_report(
        integrity=True, identity=True, source_match=True,
        archive_reason="validated_before_destructive_restore",
    )
    assert good["ready_for_operator_review"] is True
    assert all(item["ok"] for item in good["checks"].values())
    for key in ("integrity", "identity", "source_match"):
        arguments = {"integrity": True, "identity": True, "source_match": True}
        arguments[key] = False
        failed = compile_report(**arguments, archive_reason="backup_checksum_mismatch")
        assert failed["ready_for_operator_review"] is False
        assert any(not item["ok"] for item in failed["checks"].values())
    assert inspect(ROOT, "../unsafe")["ready_for_operator_review"] is False
    assert inspect(ROOT, "")["ready_for_operator_review"] is False
    unsafe = compile_report(
        integrity=False, identity=False, source_match=False,
        archive_reason="secret=my-sensitive-content",
    )
    assert "my-sensitive-content" not in json.dumps(unsafe)
    assert not any(x in json.dumps(good) for x in ("secret=", "password="))
    print("datacenter recovery operator preflight self-test: PASS")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only local recovery integrity, app identity and Git SHA check."
    )
    parser.add_argument("backup_name", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.backup_name:
        parser.error("a single backup name is required")
    report = inspect(ROOT, args.backup_name)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
    return 0 if report["ready_for_operator_review"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
