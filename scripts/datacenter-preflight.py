#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA = "grc-datacenter-preflight-v1"
RELEASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PLACEHOLDER_MARKERS = ("replace-with-", "change-me", "unsafe-dev-key")
REQUIRED_KEYS = {
    "APP_ENV",
    "GRC_RELEASE_VERSION",
    "DJANGO_SECRET_KEY",
    "AUDIT_INTEGRITY_KEY",
    "POSTGRES_PASSWORD",
    "OPS_METRICS_TOKEN",
    "S3_ENDPOINT_URL",
    "S3_BUCKET",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "MFA_ENCRYPTION_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "CSRF_TRUSTED_ORIGINS",
}
HOST_COMMANDS = ("docker", "git", "openssl", "python", "tar", "gzip", "sha256sum")


class PreflightError(RuntimeError):
    pass


def _run(*args: str) -> tuple[int, str]:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=10)
    return proc.returncode, (proc.stdout or proc.stderr).strip()


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise PreflightError(f"invalid env syntax at line {lineno}")
        name, value = line.split("=", 1)
        name = name.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise PreflightError(f"invalid env variable name at line {lineno}")
        if name in values:
            raise PreflightError(f"duplicate env variable: {name}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[name] = value
    return values


def _check(name: str, ok: bool, *, severity: str = "error", detail: str | None = None) -> dict[str, object]:
    row: dict[str, object] = {"name": name, "status": "pass" if ok else severity}
    if detail:
        row["detail"] = detail
    return row


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _fernet_shape_valid(value: str) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii"))
    except Exception:
        return False
    return len(decoded) == 32


def inspect_env(path: Path, *, tls: bool) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    if not path.is_file():
        return [_check("env_file", False, detail="production env file is missing")]
    mode = stat.S_IMODE(path.stat().st_mode)
    checks.append(_check("env_permissions", mode & 0o077 == 0, detail=f"mode={oct(mode)}; expected no group/world permissions"))
    try:
        env = _parse_env(path)
    except PreflightError as exc:
        return checks + [_check("env_syntax", False, detail=str(exc))]
    checks.append(_check("env_syntax", True))
    missing = sorted(key for key in REQUIRED_KEYS if not env.get(key, "").strip())
    checks.append(_check("required_env", not missing, detail=("missing=" + ",".join(missing)) if missing else "required variables present"))
    placeholders = sorted(
        key for key, value in env.items()
        if any(marker in value.lower() for marker in PLACEHOLDER_MARKERS)
    )
    checks.append(_check("placeholder_values", not placeholders, detail=("placeholder keys=" + ",".join(placeholders)) if placeholders else "none"))
    checks.append(_check("app_env", env.get("APP_ENV") == "production", detail="APP_ENV must be production"))
    version = env.get("GRC_RELEASE_VERSION", "")
    checks.append(_check("release_version", bool(RELEASE_RE.fullmatch(version)) and version != "local", detail="release version must be exact and non-local"))
    checks.append(_check("django_secret_length", len(env.get("DJANGO_SECRET_KEY", "")) >= 50, detail="minimum 50 characters"))
    checks.append(_check("audit_key_length", len(env.get("AUDIT_INTEGRITY_KEY", "")) >= 32, detail="minimum 32 characters"))
    checks.append(_check("mfa_fernet_key", _fernet_shape_valid(env.get("MFA_ENCRYPTION_KEY", "")), detail="must decode to 32 bytes"))
    checks.append(_check("secure_cookies", _is_truthy(env.get("SESSION_COOKIE_SECURE", "")) and _is_truthy(env.get("CSRF_COOKIE_SECURE", ""))))
    checks.append(_check("ssl_redirect", _is_truthy(env.get("SECURE_SSL_REDIRECT", ""))))
    smtp_enabled = _is_truthy(env.get("NOTIFICATION_EMAIL_ENABLED", "0"))
    if smtp_enabled:
        smtp_required = [key for key in ("EMAIL_HOST", "DEFAULT_FROM_EMAIL", "APP_BASE_URL") if not env.get(key, "").strip()]
        checks.append(_check("smtp_required", not smtp_required, detail=("missing=" + ",".join(smtp_required)) if smtp_required else "present"))
        tls_enabled = _is_truthy(env.get("EMAIL_USE_TLS", "0"))
        ssl_enabled = _is_truthy(env.get("EMAIL_USE_SSL", "0"))
        checks.append(_check("smtp_transport_mode", not (tls_enabled and ssl_enabled), detail="EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled"))
    else:
        checks.append(_check("smtp_disabled_or_valid", True))
    if tls:
        cert = Path(env.get("TLS_CERT_PATH", ""))
        key = Path(env.get("TLS_KEY_PATH", ""))
        checks.append(_check("tls_paths", cert.is_file() and key.is_file(), detail="configured TLS certificate/key must exist"))
        if cert.is_file() and shutil.which("openssl"):
            rc, _ = _run("openssl", "x509", "-in", str(cert), "-noout", "-checkend", "0")
            checks.append(_check("tls_certificate_valid", rc == 0, detail="certificate must parse and not be expired"))
        if key.is_file() and shutil.which("openssl"):
            rc, _ = _run("openssl", "pkey", "-in", str(key), "-noout", "-check")
            checks.append(_check("tls_private_key_valid", rc == 0, detail="private key must parse"))
        if cert.is_file() and key.is_file() and shutil.which("openssl"):
            cert_rc, cert_pub = _run("openssl", "x509", "-in", str(cert), "-pubkey", "-noout")
            key_rc, key_pub = _run("openssl", "pkey", "-in", str(key), "-pubout")
            checks.append(_check("tls_keypair_match", cert_rc == 0 and key_rc == 0 and cert_pub == key_pub, detail="certificate public key must match private key"))
    return checks


def inspect_host() -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    for command in HOST_COMMANDS:
        checks.append(_check(f"command:{command}", shutil.which(command) is not None))
    if shutil.which("docker"):
        rc, out = _run("docker", "version", "--format", "{{.Server.Version}}")
        checks.append(_check("docker_engine", rc == 0 and bool(out), detail=out if rc == 0 else "Docker daemon unavailable"))
        rc, out = _run("docker", "compose", "version", "--short")
        checks.append(_check("docker_compose_v2", rc == 0 and bool(out), detail=out if rc == 0 else "Docker Compose v2 unavailable"))
    return checks


def build_report(env_file: Path, *, tls: bool, skip_host: bool) -> dict[str, object]:
    checks = inspect_env(env_file, tls=tls)
    if not skip_host:
        checks = inspect_host() + checks
    failed = [row for row in checks if row["status"] == "error"]
    warnings = [row for row in checks if row["status"] == "warning"]
    return {
        "schema": SCHEMA,
        "status": "fail" if failed else ("warning" if warnings else "pass"),
        "checks": checks,
    }


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="grc-preflight-") as tmp:
        root = Path(tmp)
        env = root / ".env"
        key = base64.urlsafe_b64encode(b"x" * 32).decode("ascii")
        env.write_text(
            "\n".join(
                [
                    "APP_ENV=production",
                    "GRC_RELEASE_VERSION=v1.2.3",
                    "DJANGO_SECRET_KEY=" + "x" * 60,
                    "AUDIT_INTEGRITY_KEY=" + "y" * 40,
                    "POSTGRES_PASSWORD=strong",
                    "OPS_METRICS_TOKEN=metrics",
                    "S3_ENDPOINT_URL=http://objectstore:8333",
                    "S3_BUCKET=grc",
                    "S3_ACCESS_KEY=access",
                    "S3_SECRET_KEY=secret-value",
                    "MFA_ENCRYPTION_KEY=" + key,
                    "DJANGO_ALLOWED_HOSTS=grc.internal",
                    "CSRF_TRUSTED_ORIGINS=https://grc.internal",
                    "SESSION_COOKIE_SECURE=1",
                    "CSRF_COOKIE_SECURE=1",
                    "SECURE_SSL_REDIRECT=1",
                    "NOTIFICATION_EMAIL_ENABLED=0",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env.chmod(0o600)
        good = build_report(env, tls=False, skip_host=True)
        if good["status"] != "pass":
            raise PreflightError(f"valid self-test environment failed: {good}")
        env.write_text(env.read_text() + "EMAIL_HOST_PASSWORD=replace-with-password\n", encoding="utf-8")
        bad = build_report(env, tls=False, skip_host=True)
        if bad["status"] != "fail":
            raise PreflightError("placeholder self-test did not fail closed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GRC datacenter host and production configuration without printing secret values.")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--tls", action="store_true", help="Require configured TLS certificate/key paths to exist and parse.")
    parser.add_argument("--skip-host", action="store_true", help="Skip host command checks (primarily for CI/self-contained validation).")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            print("datacenter preflight self-test passed")
            return 0
        report = build_report(Path(args.env_file).resolve(), tls=args.tls, skip_host=args.skip_host)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            for row in report["checks"]:
                print(f"{str(row['status']).upper():7} {row['name']}: {row.get('detail', '')}".rstrip())
            print(f"RESULT: {report['status']}")
        return 0 if report["status"] != "fail" else 2
    except (OSError, PreflightError, subprocess.SubprocessError) as exc:
        if args.json:
            print(json.dumps({"schema": SCHEMA, "status": "fail", "error_type": type(exc).__name__}, sort_keys=True))
        else:
            print(f"ERROR: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
