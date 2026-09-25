#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import os
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIBLING_TEMPLATE = Path(__file__).resolve().parent / ".env.pilot.example"
DEFAULT_TEMPLATE = ROOT / ".env.pilot.example"
if not DEFAULT_TEMPLATE.is_file() and SIBLING_TEMPLATE.is_file():
    DEFAULT_TEMPLATE = SIBLING_TEMPLATE

VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$"
)

SECRET_KEYS = {
    "DJANGO_SECRET_KEY",
    "AUDIT_INTEGRITY_KEY",
    "POSTGRES_PASSWORD",
    "OPS_METRICS_TOKEN",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "MFA_ENCRYPTION_KEY",
}


def random_token(bytes_count: int = 32) -> str:
    return secrets.token_urlsafe(bytes_count)


def fernet_key() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")


def validate_hostname(hostname: str) -> str:
    value = hostname.strip().lower().rstrip(".")
    if not HOST_RE.fullmatch(value):
        raise ValueError("hostname must be an explicit DNS/FQDN name such as grc.customer.internal")
    return value


def validate_release_version(version: str) -> str:
    value = version.strip()
    if not VERSION_RE.fullmatch(value) or value in {"local", "latest"}:
        raise ValueError("release version must be immutable and use only letters, numbers, dot, underscore or dash")
    return value


def validate_tls_path(value: str, label: str) -> str:
    if any(ch in value for ch in ("\n", "\r", "\x00")):
        raise ValueError(f"{label} contains an invalid control character")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{label} must be an absolute host path")
    return str(path)


def replace_values(template: str, replacements: dict[str, str]) -> str:
    seen: set[str] = set()
    output: list[str] = []
    for raw in template.splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in raw:
            key = raw.split("=", 1)[0].strip()
            if key in replacements:
                output.append(f"{key}={replacements[key]}")
                seen.add(key)
                continue
        output.append(raw)
    missing = sorted(set(replacements) - seen)
    if missing:
        raise ValueError("template is missing required keys: " + ", ".join(missing))
    return "\n".join(output) + "\n"


def generate(
    template_path: Path,
    output_path: Path,
    hostname: str,
    release_version: str,
    tls_cert: str,
    tls_key: str,
    enable_ai: bool = False,
    force: bool = False,
) -> dict[str, object]:
    hostname = validate_hostname(hostname)
    release_version = validate_release_version(release_version)
    tls_cert = validate_tls_path(tls_cert, "TLS certificate path")
    tls_key = validate_tls_path(tls_key, "TLS private-key path")
    if output_path.is_symlink():
        raise ValueError("output path must not be a symbolic link")
    if output_path.exists() and not force:
        raise FileExistsError(f"output already exists: {output_path}")

    template = template_path.read_text(encoding="utf-8")
    replacements = {
        "APP_ENV": "production",
        "GRC_RELEASE_VERSION": release_version,
        "DJANGO_SECRET_KEY": random_token(64),
        "AUDIT_INTEGRITY_KEY": random_token(48),
        "DJANGO_ALLOWED_HOSTS": hostname,
        "CORS_ALLOWED_ORIGINS": f"https://{hostname}",
        "CSRF_TRUSTED_ORIGINS": f"https://{hostname}",
        "POSTGRES_PASSWORD": random_token(32),
        "OPS_METRICS_TOKEN": random_token(32),
        "S3_ACCESS_KEY": secrets.token_hex(12),
        "S3_SECRET_KEY": random_token(32),
        "MFA_ENCRYPTION_KEY": fernet_key(),
        "AI_ENABLED": "1" if enable_ai else "0",
        "TLS_CERT_PATH": tls_cert,
        "TLS_KEY_PATH": tls_key,
        "NOTIFICATION_EMAIL_ENABLED": "0",
        "APP_BASE_URL": f"https://{hostname}",
    }
    rendered = replace_values(template, replacements)

    for marker in ("replace-with-", "change-me", "changeme", "example-password", "example-secret"):
        for raw in rendered.splitlines():
            if raw.strip().startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            if key.strip() in SECRET_KEYS and marker in value.lower():
                raise ValueError(f"generated secret key remained placeholder-like: {key.strip()}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{output_path.name}.",
            dir=str(output_path.parent),
            text=True,
        )
        temp_path = Path(temp_name)
        os.chmod(temp_path, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, output_path)
        temp_path = None
        os.chmod(output_path, 0o600)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass
    return {
        "schema": "grc-server-pilot-env-generation-v1",
        "output": str(output_path),
        "hostname": hostname,
        "release_version": release_version,
        "ai_enabled": enable_ai,
        "secrets_printed": False,
    }


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="grc-server-env-") as tmp:
        root = Path(tmp)
        output = root / "pilot.env"
        report = generate(
            ROOT / ".env.pilot.example",
            output,
            "grc.customer.internal",
            "v0.9.0-pilot-test",
            "/opt/grc/secrets/tls/server.crt",
            "/opt/grc/secrets/tls/server.key",
        )
        if report["ai_enabled"] is not False:
            raise SystemExit("server env self-test failed: AI must default disabled")
        if oct(output.stat().st_mode & 0o777) != "0o600":
            raise SystemExit("server env self-test failed: output mode is not 0600")
        content = output.read_text(encoding="utf-8")
        if "AI_ENABLED=0" not in content or "GRC_RELEASE_VERSION=v0.9.0-pilot-test" not in content:
            raise SystemExit("server env self-test failed: expected replacements missing")
        symlink_output = root / "symlink.env"
        symlink_target = root / "target.env"
        symlink_target.write_text("do-not-overwrite\n", encoding="utf-8")
        symlink_output.symlink_to(symlink_target)
        try:
            generate(
                ROOT / ".env.pilot.example",
                symlink_output,
                "grc.customer.internal",
                "v0.9.0-pilot-test",
                "/opt/grc/secrets/tls/server.crt",
                "/opt/grc/secrets/tls/server.key",
                force=True,
            )
        except ValueError:
            pass
        else:
            raise SystemExit("server env self-test failed: symlink output was not rejected")
        if symlink_target.read_text(encoding="utf-8") != "do-not-overwrite\n":
            raise SystemExit("server env self-test failed: symlink target was modified")
        validator = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/datacenter-env-validate.py"),
                "--env",
                str(output),
                "--release-version",
                "v0.9.0-pilot-test",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if validator.returncode != 0:
            raise SystemExit("server env self-test failed: generated environment did not pass validator")
        if any(secret in validator.stdout for secret in (report.get("secret", ""),) if secret):
            raise SystemExit("server env self-test failed: validator leaked a secret")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a secret-safe production Pilot .env without printing generated secret values."
    )
    parser.add_argument("--hostname", required=False)
    parser.add_argument("--release-version", required=False)
    parser.add_argument("--output", default="runtime/server-pilot.env")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--tls-cert", default="/opt/grc/secrets/tls/server.crt")
    parser.add_argument("--tls-key", default="/opt/grc/secrets/tls/server.key")
    parser.add_argument("--enable-ai", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("server Pilot env generator self-test passed")
        return 0

    if not args.hostname or not args.release_version:
        parser.error("--hostname and --release-version are required unless --self-test is used")

    try:
        report = generate(
            Path(args.template).resolve(),
            Path(args.output).resolve(),
            args.hostname,
            args.release_version,
            args.tls_cert,
            args.tls_key,
            enable_ai=args.enable_ai,
            force=args.force,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        f"Generated {report['output']} for {report['hostname']} "
        f"release={report['release_version']} ai_enabled={str(report['ai_enabled']).lower()} secrets_printed=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
