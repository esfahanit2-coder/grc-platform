#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


PLACEHOLDER_MARKERS = (
    "replace-with-",
    "change-me",
    "changeme",
    "example-password",
    "example-secret",
)
REQUIRED_KEYS = (
    "APP_ENV",
    "GRC_RELEASE_VERSION",
    "DJANGO_SECRET_KEY",
    "AUDIT_INTEGRITY_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "CORS_ALLOWED_ORIGINS",
    "CSRF_TRUSTED_ORIGINS",
    "POSTGRES_PASSWORD",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "OPS_METRICS_TOKEN",
    "S3_ENDPOINT_URL",
    "S3_BUCKET",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "MFA_ENCRYPTION_KEY",
    "TLS_CERT_PATH",
    "TLS_KEY_PATH",
)


def parse_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"line {number} is not KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or any(ch.isspace() for ch in key):
            raise ValueError(f"line {number} has an invalid key")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result[key] = value
    return result


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def https_origin(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def validate(path: Path, expected_release: str | None = None, require_tls_files: bool = False) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        env = parse_env(path)
    except Exception as exc:
        return {
            "schema": "grc-datacenter-config-validation-v1",
            "valid": False,
            "errors": [f"environment file cannot be parsed: {type(exc).__name__}"],
            "warnings": [],
        }

    missing = [key for key in REQUIRED_KEYS if not env.get(key, "").strip()]
    if missing:
        errors.append("required keys missing or empty: " + ", ".join(sorted(missing)))

    if env.get("APP_ENV") != "production":
        errors.append("APP_ENV must be production")
    if truthy(env.get("DJANGO_DEBUG")):
        errors.append("DJANGO_DEBUG must be disabled")
    for key in ("AUTH_COOKIE_MODE", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "SECURE_SSL_REDIRECT"):
        if not truthy(env.get(key)):
            errors.append(f"{key} must be enabled")
    if not truthy(env.get("EVIDENCE_REQUIRE_CLEAN_DOWNLOAD")):
        errors.append("EVIDENCE_REQUIRE_CLEAN_DOWNLOAD must be enabled")

    release = env.get("GRC_RELEASE_VERSION", "").strip()
    if release in {"", "local", "latest"} or placeholder(release):
        errors.append("GRC_RELEASE_VERSION must identify an immutable release")
    if expected_release and release != expected_release:
        errors.append("GRC_RELEASE_VERSION does not match the signed/selected release")

    for key, minimum in (
        ("DJANGO_SECRET_KEY", 50),
        ("AUDIT_INTEGRITY_KEY", 32),
        ("POSTGRES_PASSWORD", 16),
        ("OPS_METRICS_TOKEN", 32),
        ("S3_ACCESS_KEY", 12),
        ("S3_SECRET_KEY", 24),
    ):
        value = env.get(key, "")
        if placeholder(value) or len(value) < minimum:
            errors.append(f"{key} is missing, placeholder-like, or shorter than the production minimum")

    mfa_key = env.get("MFA_ENCRYPTION_KEY", "")
    if placeholder(mfa_key):
        errors.append("MFA_ENCRYPTION_KEY must be a dedicated Fernet key")
    else:
        try:
            decoded = base64.urlsafe_b64decode(mfa_key.encode("ascii"))
            if len(decoded) != 32:
                raise ValueError("wrong length")
        except Exception:
            errors.append("MFA_ENCRYPTION_KEY must be a valid 32-byte urlsafe-base64 Fernet key")

    hosts = split_csv(env.get("DJANGO_ALLOWED_HOSTS", ""))
    if not hosts or "*" in hosts:
        errors.append("DJANGO_ALLOWED_HOSTS must be explicit and must not contain *")
    if any(host.endswith(".example.internal") or host == "grc.example.internal" for host in hosts):
        errors.append("DJANGO_ALLOWED_HOSTS still contains the example hostname")

    for key in ("CORS_ALLOWED_ORIGINS", "CSRF_TRUSTED_ORIGINS"):
        origins = split_csv(env.get(key, ""))
        if not origins or any(not https_origin(origin) for origin in origins):
            errors.append(f"{key} must contain only explicit https origins")

    endpoint = env.get("S3_ENDPOINT_URL", "")
    parsed_endpoint = urlparse(endpoint)
    if parsed_endpoint.scheme not in {"http", "https"} or not parsed_endpoint.hostname:
        errors.append("S3_ENDPOINT_URL must be an explicit http(s) endpoint")
    if truthy(env.get("S3_USE_SSL")) and parsed_endpoint.scheme != "https":
        errors.append("S3_USE_SSL requires an https S3_ENDPOINT_URL")
    if parsed_endpoint.scheme == "http" and parsed_endpoint.hostname not in {"objectstore", "127.0.0.1", "localhost"}:
        warnings.append("S3 endpoint is HTTP outside the bundled private objectstore name; verify network isolation")

    if truthy(env.get("NOTIFICATION_EMAIL_ENABLED")):
        if not env.get("EMAIL_HOST", "").strip():
            errors.append("EMAIL_HOST is required when notification email is enabled")
        if not env.get("DEFAULT_FROM_EMAIL", "").strip() or "@" not in env.get("DEFAULT_FROM_EMAIL", ""):
            errors.append("DEFAULT_FROM_EMAIL must be configured when notification email is enabled")
        if not https_origin(env.get("APP_BASE_URL", "")):
            errors.append("APP_BASE_URL must be an explicit https URL when notification email is enabled")
        if truthy(env.get("EMAIL_USE_TLS")) and truthy(env.get("EMAIL_USE_SSL")):
            errors.append("EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled")
        if env.get("EMAIL_HOST_USER", "").strip() and placeholder(env.get("EMAIL_HOST_PASSWORD", "")):
            errors.append("EMAIL_HOST_PASSWORD is required when EMAIL_HOST_USER is configured")

    if require_tls_files:
        for key in ("TLS_CERT_PATH", "TLS_KEY_PATH"):
            configured = env.get(key, "").strip()
            candidate = Path(configured)
            if not candidate.is_absolute():
                candidate = (path.parent / candidate).resolve()
            if not candidate.is_file():
                errors.append(f"{key} does not point to an existing file")
        key_path = Path(env.get("TLS_KEY_PATH", ""))
        if not key_path.is_absolute():
            key_path = (path.parent / key_path).resolve()
        if key_path.is_file():
            mode = stat.S_IMODE(key_path.stat().st_mode)
            if mode & 0o077:
                errors.append("TLS private key permissions must not grant group/other access")

    return {
        "schema": "grc-datacenter-config-validation-v1",
        "valid": not errors,
        "release_version": release or None,
        "checks": {
            "production_mode": env.get("APP_ENV") == "production",
            "secure_cookies": all(truthy(env.get(k)) for k in ("SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE")),
            "tls_paths_checked": require_tls_files,
            "evidence_download_fail_closed": truthy(env.get("EVIDENCE_REQUIRE_CLEAN_DOWNLOAD")),
            "smtp_enabled": truthy(env.get("NOTIFICATION_EMAIL_ENABLED")),
        },
        "errors": errors,
        "warnings": warnings,
    }


def self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fernet = base64.urlsafe_b64encode(b"x" * 32).decode("ascii")
        sample = {
            "APP_ENV": "production",
            "GRC_RELEASE_VERSION": "v1.2.3",
            "DJANGO_SECRET_KEY": "s" * 60,
            "AUDIT_INTEGRITY_KEY": "a" * 40,
            "DJANGO_DEBUG": "0",
            "DJANGO_ALLOWED_HOSTS": "grc.customer.internal",
            "CORS_ALLOWED_ORIGINS": "https://grc.customer.internal",
            "CSRF_TRUSTED_ORIGINS": "https://grc.customer.internal",
            "POSTGRES_PASSWORD": "p" * 24,
            "REDIS_URL": "redis://redis:6379/0",
            "CELERY_BROKER_URL": "redis://redis:6379/1",
            "CELERY_RESULT_BACKEND": "redis://redis:6379/2",
            "OPS_METRICS_TOKEN": "m" * 40,
            "S3_ENDPOINT_URL": "http://objectstore:8333",
            "S3_BUCKET": "grc-evidence",
            "S3_ACCESS_KEY": "k" * 16,
            "S3_SECRET_KEY": "z" * 32,
            "S3_USE_SSL": "0",
            "MFA_ENCRYPTION_KEY": fernet,
            "AUTH_COOKIE_MODE": "1",
            "SESSION_COOKIE_SECURE": "1",
            "CSRF_COOKIE_SECURE": "1",
            "SECURE_SSL_REDIRECT": "1",
            "EVIDENCE_REQUIRE_CLEAN_DOWNLOAD": "1",
            "TLS_CERT_PATH": "./server.crt",
            "TLS_KEY_PATH": "./server.key",
            "NOTIFICATION_EMAIL_ENABLED": "0",
        }
        env_file = root / ".env"
        env_file.write_text("\n".join(f"{k}={v}" for k, v in sample.items()) + "\n", encoding="utf-8")
        result = validate(env_file, expected_release="v1.2.3")
        if not result["valid"]:
            raise SystemExit("self-test valid fixture failed")
        env_file.write_text(env_file.read_text(encoding="utf-8").replace("s" * 60, "replace-with-secret"), encoding="utf-8")
        result = validate(env_file, expected_release="v1.2.3")
        if result["valid"] or any("replace-with-secret" in item for item in result["errors"]):
            raise SystemExit("self-test placeholder/redaction contract failed")
    print("datacenter env validator self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate production datacenter environment without printing secret values.")
    parser.add_argument("--env", default=".env", help="Environment file to validate.")
    parser.add_argument("--release-version", help="Expected immutable release version.")
    parser.add_argument("--require-tls-files", action="store_true", help="Require certificate/key files and safe private-key permissions.")
    parser.add_argument("--json-out", help="Optional machine-readable output path.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    path = Path(args.env).resolve()
    if not path.is_file():
        print("ERROR: environment file does not exist", file=sys.stderr)
        return 2
    result = validate(path, args.release_version, args.require_tls_files)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.json_out:
        target = Path(args.json_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload + "\n", encoding="utf-8")
        os.chmod(target, 0o600)
    print(payload)
    return 0 if result["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
