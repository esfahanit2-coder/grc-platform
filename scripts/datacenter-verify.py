#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SERVICES = ("postgres", "redis", "objectstore", "backend", "worker", "beat", "frontend", "gateway")


def run(command: list[str], cwd: Path = ROOT, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def add_check(report: dict, name: str, ok: bool, detail: str | None = None) -> None:
    item = {"name": name, "ok": bool(ok)}
    if detail:
        item["detail"] = detail
    report["checks"].append(item)
    if not ok:
        report["ok"] = False


def compose_command(env_file: Path) -> list[str]:
    return [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "-f",
        "docker-compose.pilot.yml",
        "-f",
        "docker-compose.pilot.tls.yml",
    ]


def docker_version_ok(value: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+){1,3}(?:[-+._A-Za-z0-9]*)?", value.strip()))


def compose_v2(value: str) -> bool:
    match = re.search(r"(\d+)(?:\.\d+)+", value)
    return bool(match and int(match.group(1)) >= 2)


def inspect_service(compose: list[str], service: str) -> dict:
    ps = run(compose + ["ps", "-q", service])
    container_id = ps.stdout.strip()
    if ps.returncode != 0 or not container_id:
        return {"service": service, "running": False, "health": "missing"}
    inspected = run(["docker", "inspect", container_id])
    if inspected.returncode != 0:
        return {"service": service, "running": False, "health": "inspect-failed"}
    payload = json.loads(inspected.stdout)[0]
    state = payload.get("State", {})
    health = state.get("Health", {}).get("Status", "not-defined")
    return {
        "service": service,
        "running": bool(state.get("Running")),
        "health": health,
    }


def verify(env_file: Path, release_version: str, include_operational: bool = True) -> dict:
    report = {
        "schema": "grc-datacenter-verification-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "release_version": release_version,
        "ok": True,
        "checks": [],
        "services": [],
        "versions": {},
    }

    validator = run(
        [
            sys.executable,
            "scripts/datacenter-env-validate.py",
            "--env",
            str(env_file),
            "--release-version",
            release_version,
            "--require-tls-files",
        ]
    )
    try:
        config_report = json.loads(validator.stdout)
    except Exception:
        config_report = {"valid": False, "errors": ["validator output unavailable"]}
    report["config"] = config_report
    add_check(report, "config", validator.returncode == 0 and bool(config_report.get("valid")))

    docker_version = run(["docker", "version", "--format", "{{.Server.Version}}"])
    docker_value = docker_version.stdout.strip()
    if docker_version.returncode == 0 and docker_version_ok(docker_value):
        report["versions"]["docker_server"] = docker_value
        add_check(report, "docker-daemon", True)
    else:
        add_check(report, "docker-daemon", False, "Docker Engine server is unavailable")
        return report

    compose_version = run(["docker", "compose", "version", "--short"])
    compose_value = compose_version.stdout.strip()
    if compose_version.returncode == 0 and compose_v2(compose_value):
        report["versions"]["docker_compose"] = compose_value
        add_check(report, "compose-v2", True)
    else:
        add_check(report, "compose-v2", False, "Docker Compose v2 is required")
        return report

    help_result = run(["docker", "compose", "up", "--help"])
    supports_wait = "--wait" in help_result.stdout
    supports_pull = "--pull" in help_result.stdout
    add_check(report, "compose-wait-capability", supports_wait)
    add_check(report, "compose-pull-policy-capability", supports_pull)

    compose = compose_command(env_file)
    rendered = run(compose + ["config"])
    add_check(report, "compose-config", rendered.returncode == 0)
    images = run(compose + ["config", "--images"])
    configured_images = sorted({line.strip() for line in images.stdout.splitlines() if line.strip()})
    if images.returncode != 0 or not configured_images:
        add_check(report, "compose-images", False, "Unable to resolve image references")
    else:
        report["images"] = configured_images
        mutable = [image for image in configured_images if image.endswith(":latest") or ":" not in image.rsplit("/", 1)[-1]]
        add_check(report, "immutable-image-references", not mutable)

        missing_images = []
        for image in configured_images:
            probe = run(["docker", "image", "inspect", image])
            if probe.returncode != 0:
                missing_images.append(image)
        report["missing_images"] = missing_images
        add_check(report, "release-images-preloaded", not missing_images)

    for service in CORE_SERVICES:
        status = inspect_service(compose, service)
        report["services"].append(status)
        healthy = status["running"] and status["health"] not in {"unhealthy", "missing", "inspect-failed"}
        add_check(report, f"service:{service}", healthy, status["health"])

    migrations = run(compose + ["exec", "-T", "backend", "python", "manage.py", "migrate", "--check"])
    add_check(report, "migration-state", migrations.returncode == 0)

    readiness = run(compose + ["exec", "-T", "backend", "python", "manage.py", "pilot_readiness"])
    add_check(report, "application-readiness", readiness.returncode == 0)

    if include_operational:
        operational = run(compose + ["exec", "-T", "backend", "python", "manage.py", "operational_status", "--json"])
        if operational.returncode == 0:
            try:
                report["operational_status"] = json.loads(operational.stdout)
                add_check(report, "operational-status", True)
            except Exception:
                add_check(report, "operational-status", False, "Operational status JSON was invalid")
        else:
            add_check(report, "operational-status", False, "Operational status command failed")

    return report


def self_test() -> None:
    if not docker_version_ok("28.0.1") or docker_version_ok("not-a-version"):
        raise SystemExit("docker version parser self-test failed")
    if not compose_v2("Docker Compose version v2.35.0") or compose_v2("1.29.2"):
        raise SystemExit("compose version parser self-test failed")
    report = {"ok": True, "checks": []}
    add_check(report, "pass", True)
    add_check(report, "fail", False, "bounded detail")
    if report["ok"] is not False or len(report["checks"]) != 2:
        raise SystemExit("check aggregation self-test failed")
    print("datacenter verification self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a running GRC datacenter installation and emit a secret-safe JSON report.")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--release-version", required=False)
    parser.add_argument("--json-out")
    parser.add_argument("--skip-operational", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    env_file = Path(args.env).resolve()
    if not env_file.is_file():
        print("ERROR: environment file is required", file=sys.stderr)
        return 2

    release_version = args.release_version or os.environ.get("GRC_RELEASE_VERSION", "")
    if not release_version:
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            if raw.startswith("GRC_RELEASE_VERSION="):
                release_version = raw.split("=", 1)[1].strip().strip("'\"")
                break
    if not release_version:
        print("ERROR: release version could not be determined", file=sys.stderr)
        return 2

    report = verify(env_file, release_version, include_operational=not args.skip_operational)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.json_out:
        target = Path(args.json_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload + "\n", encoding="utf-8")
        os.chmod(target, 0o600)
    print(payload)
    return 0 if report["ok"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
