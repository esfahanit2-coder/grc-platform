#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCHEMA = "grc-datacenter-verification-v1"
REQUIRED_SERVICES = ("postgres", "redis", "objectstore", "backend", "worker", "beat", "frontend", "gateway")


def run(args: list[str], *, timeout: int = 30) -> tuple[int, str, str]:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def check(name: str, ok: bool, *, detail: object | None = None) -> dict[str, object]:
    row: dict[str, object] = {"name": name, "status": "pass" if ok else "fail"}
    if detail is not None:
        row["detail"] = detail
    return row


def compose_args(env_file: Path, tls: bool) -> list[str]:
    args = ["docker", "compose", "--env-file", str(env_file), "-f", "docker-compose.pilot.yml"]
    if tls:
        args += ["-f", "docker-compose.pilot.tls.yml"]
    return args


def request_json(url: str, *, cafile: str | None, timeout: int = 10) -> tuple[bool, object]:
    context = ssl.create_default_context(cafile=cafile) if url.lower().startswith("https://") else None
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=context) as response:
            body = response.read(65536)
            payload = json.loads(body.decode("utf-8")) if body else {}
            return 200 <= response.status < 300, payload
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return False, {"error_type": type(exc).__name__}


def parse_json_output(text: str) -> object:
    text = text.strip()
    if not text:
        return None
    return json.loads(text.splitlines()[-1])


def build_report(*, env_file: Path, base_url: str, tls: bool, ca_cert: str | None) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    preflight = [sys.executable, "scripts/datacenter-preflight.py", "--env-file", str(env_file), "--json"]
    if tls:
        preflight.append("--tls")
    rc, out, _ = run(preflight)
    try:
        preflight_payload = json.loads(out)
    except json.JSONDecodeError:
        preflight_payload = {"status": "fail", "error_type": "InvalidPreflightOutput"}
    checks.append(check("host_and_configuration_preflight", rc == 0 and preflight_payload.get("status") == "pass", detail={"status": preflight_payload.get("status")}))

    compose = compose_args(env_file, tls)
    rc, running, _ = run(compose + ["ps", "--status", "running", "--services"])
    running_set = {line.strip() for line in running.splitlines() if line.strip()} if rc == 0 else set()
    missing_services = sorted(set(REQUIRED_SERVICES) - running_set)
    checks.append(check("required_services_running", rc == 0 and not missing_services, detail={"missing": missing_services}))

    rc, readiness, _ = run(compose + ["exec", "-T", "backend", "python", "manage.py", "pilot_readiness", "--json"], timeout=45)
    try:
        readiness_payload = parse_json_output(readiness) or {}
    except json.JSONDecodeError:
        readiness_payload = {"status": "fail", "error_type": "InvalidReadinessOutput"}
    checks.append(check("backend_dependency_readiness", rc == 0 and readiness_payload.get("status") != "fail", detail={"status": readiness_payload.get("status")}))

    rc, migrations, _ = run(compose + ["exec", "-T", "backend", "python", "manage.py", "showmigrations", "--plan"], timeout=45)
    pending = [line for line in migrations.splitlines() if "[ ]" in line]
    checks.append(check("migration_state", rc == 0 and not pending, detail={"pending_count": len(pending)}))

    live_ok, live_payload = request_json(base_url.rstrip("/") + "/api/v1/health/live", cafile=ca_cert)
    ready_ok, ready_payload = request_json(base_url.rstrip("/") + "/api/v1/health/ready", cafile=ca_cert)
    checks.append(check("api_live", live_ok, detail={"response": live_payload if live_ok else {"error_type": (live_payload or {}).get("error_type")}}))
    checks.append(check("api_ready", ready_ok, detail={"response": ready_payload if ready_ok else {"error_type": (ready_payload or {}).get("error_type")}}))

    rc, operational, _ = run(compose + ["exec", "-T", "backend", "python", "manage.py", "operational_status", "--json"], timeout=45)
    try:
        ops_payload = parse_json_output(operational) or {}
    except json.JSONDecodeError:
        ops_payload = {"overall_status": "invalid", "error_type": "InvalidOperationalStatus"}
    async_component = (ops_payload.get("components") or {}).get("async_pipeline") or {}
    checks.append(check("worker_beat_pipeline", rc == 0 and async_component.get("status") == "ok", detail={"status": async_component.get("status"), "age_seconds": async_component.get("age_seconds")}))

    failed = [item for item in checks if item["status"] == "fail"]
    return {"schema": SCHEMA, "status": "fail" if failed else "pass", "checks": checks}


def self_test() -> None:
    rows = [check("a", True), check("b", False, detail={"error_type": "Example"})]
    report = {"schema": SCHEMA, "status": "fail" if any(x["status"] == "fail" for x in rows) else "pass", "checks": rows}
    rendered = json.dumps(report)
    if report["status"] != "fail" or "Example" not in rendered:
        raise RuntimeError("verification report self-test failed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run machine-readable post-install verification for a GRC datacenter deployment.")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--base-url", required=False, default=os.getenv("GRC_VERIFY_BASE_URL", ""))
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--ca-cert", default=os.getenv("GRC_VERIFY_CA_CERT", "") or None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("datacenter verification self-test passed")
        return 0
    if not args.base_url:
        print("ERROR: --base-url or GRC_VERIFY_BASE_URL is required", file=sys.stderr)
        return 2
    report = build_report(env_file=Path(args.env_file).resolve(), base_url=args.base_url, tls=args.tls, ca_cert=args.ca_cert)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        for row in report["checks"]:
            print(f"{row['status'].upper():5} {row['name']}")
        print(f"RESULT: {report['status']}")
    return 0 if report["status"] == "pass" else 3


if __name__ == "__main__":
    raise SystemExit(main())
