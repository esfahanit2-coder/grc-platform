#!/usr/bin/env python3
"""CI-only real-browser GRC screenshots from the disposable installed core.

No mocked backend API, licensed standard content, customer data, human UAT,
commercial release signing or login/MFA verification is claimed.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROUTES = (
    ("/", "dashboard", "داشبورد"),
    ("/risks", "risks", "Risk"),
    ("/controls", "controls", "کنترل"),
    ("/evidence", "evidence", "Evidence"),
    ("/soa", "soa-draft", "SoA"),
    ("/admin/operations", "operations", "عملیات"),
)

BACKEND_MINT = r"""
import json, os
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from apps.tenancy.models import Tenant, TenantMembership
user = get_user_model().objects.get(username=os.environ["GRC_VISUAL_USER"])
tenant = Tenant.objects.get(code=os.environ["GRC_VISUAL_TENANT"], status="active")
assert TenantMembership.objects.filter(tenant=tenant, user=user, is_active=True).exists()
token = AccessToken.for_user(user)
print("GRC_EPHEMERAL_BROWSER_AUTH=" + json.dumps({"access": str(token), "tenant": str(tenant.pk)}))
"""


def die(message: str) -> None:
    raise SystemExit("BROWSER_UAT_FAIL: " + message)


def get_synthetic_token(install: Path) -> dict[str, str]:
    command = [
        "docker", "compose", "--env-file", ".env",
        "-f", "docker-compose.pilot.yml",
        "-f", "docker-compose.pilot.tls.yml",
        "exec", "-T",
        "-e", "GRC_VISUAL_USER=ci-installed-admin",
        "-e", "GRC_VISUAL_TENANT=ci-installed-" + os.environ["GITHUB_RUN_ID"],
        "backend", "python", "manage.py", "shell", "-c", BACKEND_MINT,
    ]
    result = subprocess.run(command, cwd=install, capture_output=True, text=True, timeout=35, check=False)
    if result.returncode != 0:
        # Never echo stderr/stdout here: secrets may be accidentally included.
        die("Could not create ephemeral backend-only visual test token.")
    marker = "GRC_EPHEMERAL_BROWSER_AUTH="
    matching = [line[len(marker):] for line in result.stdout.splitlines() if line.startswith(marker)]
    if len(matching) != 1:
        die("Did not obtain exactly one disposable test token.")
    payload = json.loads(matching[0])
    assert set(payload) == {"access", "tenant"}
    assert payload["access"] and payload["tenant"]
    return payload


def main() -> int:
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GRC_BROWSER_VISUAL_EPHEMERAL_ONLY") != "YES"):
        die("Browser capture is only allowed on explicitly opted-in disposable GitHub CI.")
    if len(sys.argv) != 3:
        die("usage: ephemeral-browser-rtl.py <installed-repository> <outside-repo-artifact-dir>")

    install = Path(sys.argv[1]).resolve(strict=True)
    output = Path(sys.argv[2]).resolve()
    if output == install or install in output.parents:
        die("Evidence directory must be outside installed repository.")
    if output.exists() and any(output.iterdir()):
        die("Refusing to reuse a nonempty screenshot directory.")
    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o700)

    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=install, text=True, timeout=10
    ).strip()
    if not re.fullmatch("[0-9a-f]{40}", sha):
        die("Unable to determine exact installed commit.")
    token = get_synthetic_token(install)
    base = "https://grc.ci.internal"
    results: list[dict[str, object]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-proxy-server"])
        try:
            for name, width, height, mobile in (
                ("desktop", 1440, 900, False),
                ("mobile", 390, 844, True),
            ):
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                    is_mobile=mobile,
                    has_touch=mobile,
                    ignore_https_errors=True,
                    locale="fa-IR",
                )
                # One-run test JWT issued in already-bootstrapped *actual*
                # backend container; this deliberately does NOT test MFA/login.
                # It is never logged or placed in artifacts.
                context.add_init_script(
                    "sessionStorage.setItem('grc_access_token', "
                    + json.dumps(token["access"])
                    + ");sessionStorage.setItem('grc_tenant_id', "
                    + json.dumps(token["tenant"])
                    + ");"
                )
                page = context.new_page()
                for route, label, expected in ROUTES:
                    console_errors: list[str] = []
                    server_failures: list[str] = []
                    page.on("pageerror", lambda error: console_errors.append(type(error).__name__))
                    page.on(
                        "response",
                        lambda response: server_failures.append(str(response.status))
                        if response.status >= 500 and response.url.startswith(base) else None,
                    )
                    response = page.goto(base + route, wait_until="domcontentloaded", timeout=45000)
                    if not response or response.status >= 400:
                        die(f"{name}:{route} returned missing/error HTML.")
                    try:
                        page.locator("main h1").first.wait_for(state="visible", timeout=25000)
                        page.wait_for_load_state("networkidle", timeout=25000)
                    except Exception:
                        die(f"{name}:{route} did not render a stable heading and API-loaded view.")
                    title = page.locator("main h1").first.inner_text(timeout=7000)
                    if expected.lower() not in title.lower():
                        die(f"{name}:{route} unexpected heading (expected route domain).")
                    # Strong RTL invariant on real page: no left-to-right shell.
                    if page.locator("html").get_attribute("dir") != "rtl":
                        die(f"{name}:{route} HTML document is not RTL.")
                    if console_errors or server_failures:
                        die(f"{name}:{route} experienced Javascript or HTTP 5xx errors.")
                    filename = f"{name}-{label}.png"
                    screenshot = output / filename
                    page.screenshot(path=str(screenshot), full_page=True, animations="disabled")
                    if screenshot.stat().st_size < 5000:
                        die(f"{name}:{route} screenshot too small.")
                    results.append({
                        "viewport": name,
                        "route": route,
                        "heading": title,
                        "file": filename,
                        "bytes": screenshot.stat().st_size,
                    })
                context.close()
        finally:
            browser.close()
    if len(results) != len(ROUTES) * 2:
        die("Incomplete real-browser screenshot set.")
    manifest = {
        "schema": "grc-ci-browser-rtl-v1",
        "source_sha": sha,
        "run_id": os.environ["GITHUB_RUN_ID"],
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "real_django_next_postgres_tls": True,
        "data_type": "newly bootstrapped synthetic tenant, no customer data",
        "authentication": "backend-minted CI-only JWT injected into browser; login/MFA NOT tested",
        "visual_approval": False,
        "production_release_or_host_verified": False,
        "full_design_parity": False,
        "images": results,
    }
    (output / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"CI real-browser RTL screenshots PASS: {len(results)} views (synthetic tenant only).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
