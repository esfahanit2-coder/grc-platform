#!/usr/bin/env python3
"""Live authenticated Chromium checks against isolated, fictionally populated GRC.

This process receives the short-lived JWT over stdin, never CLI argv/files/logs.
Screenshots are marked CI-only synthetic; no human review, login or MFA claim.
"""
from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGES = (
    ("/", "dashboard-populated", "ریسک آزمایشی دسترسی نامجاز"),
    ("/risks", "risks-populated", "ریسک آزمایشی دسترسی نامجاز"),
    ("/controls", "controls-populated", "کنترل نمونه بازبینی دسترسی"),
    ("/evidence", "evidence-populated", "شاهد نمونه صورتجلسه بررسی دسترسی"),
)


def fail(msg: str) -> None:
    raise SystemExit("POPULATED_UAT_FAIL: " + msg)


def verify_viewport(page, width: int, route: str) -> None:
    if page.locator("html").get_attribute("dir") != "rtl":
        fail("RTL missing: " + route)
    dims = page.evaluate("""() => ({
        document: document.documentElement.scrollWidth,
        body: document.body.scrollWidth,
        viewport: innerWidth,
    })""")
    if dims["viewport"] != width or max(dims["document"], dims["body"]) > width + 1:
        fail("Horizontal overflow or wrong viewport: " + route)
    if page.locator(".productSidebar").count() != 1:
        fail("Shared sidebar missing: " + route)
    if page.locator(".productTopbar").count() != 1:
        fail("Shared topbar missing: " + route)


def photo(page, output: Path, label: str, width: int) -> dict[str, object]:
    filename = label + ".png"
    p = output / filename
    page.screenshot(path=str(p), full_page=True, animations="disabled")
    bits = p.read_bytes()
    if len(bits) < 5000 or bits[:8] != b"\x89PNG\r\n\x1a\n":
        fail("Invalid real PNG " + label)
    real_width, _ = struct.unpack(">II", bits[16:24])
    if real_width != width:
        fail(f"{label} real image width {real_width}, expected {width}")
    return {"file": filename, "bytes": len(bits), "viewport_width": width}


def goto(page, url: str, route: str):
    response = page.goto(url + route, wait_until="domcontentloaded", timeout=45000)
    if not response or response.status >= 400:
        fail("HTTP page failure on " + route)
    try:
        page.locator("main h1").first.wait_for(state="visible", timeout=20000)
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        fail("Page or real backend did not settle: " + route)


def main() -> int:
    if not (os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("GRC_BROWSER_VISUAL_EPHEMERAL_ONLY") == "YES"
            and os.environ.get("GRC_BROWSER_POPULATED_EPHEMERAL_ONLY") == "YES"):
        fail("No explicit three-condition disposable CI permission.")
    if len(sys.argv) != 3:
        fail("usage: ... <installed-source> <outside-repo-output>")

    install = Path(sys.argv[1]).resolve(strict=True)
    output = Path(sys.argv[2]).resolve()
    if output.exists() and any(output.iterdir()):
        fail("Refusing nonempty output.")
    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o700)
    credential = json.loads(sys.stdin.read())
    if set(credential) != {"access", "tenant"} or not all(credential.values()):
        fail("Invalid ephemeral browser token input.")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if not run_id.isdecimal():
        fail("Missing GitHub run id.")

    # Source live installed tenant seed: no database mock, no standard imports,
    # no credentials or customer identifiers displayed in logs/artifacts.
    seed = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "ephemeral-browser-populate.py"), str(install)],
        capture_output=True, text=True, timeout=85, check=False,
    )
    if seed.returncode != 0:
        fail("Backend synthetic-tenant seeding rejected or incomplete.")

    base = "https://grc.ci.internal"
    snapshots: list[dict[str, object]] = []
    checks: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-proxy-server"])
        try:
            for viewport, width, height, mobile in (
                ("desktop", 1440, 900, False),
                ("mobile", 390, 844, True),
            ):
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    is_mobile=mobile, has_touch=mobile,
                    device_scale_factor=1,
                    ignore_https_errors=True, locale="fa-IR",
                )
                context.add_init_script(
                    "sessionStorage.setItem('grc_access_token', "
                    + json.dumps(credential["access"])
                    + ");sessionStorage.setItem('grc_tenant_id', "
                    + json.dumps(credential["tenant"]) + ");"
                )
                page = context.new_page()
                unexpected: list[str] = []
                page.on("pageerror", lambda _: unexpected.append("JavaScript"))
                page.on("response", lambda res: unexpected.append("HTTP5xx")
                        if res.status >= 500 and res.url.startswith(base) else None)

                # Preserve an auditable trace of real populated GETs, not merely
                # screenshot success while the API quietly returned 403/empty.
                for route, name, item in PAGES:
                    goto(page, base, route)
                    try:
                        page.get_by_text(item, exact=False).first.wait_for(state="visible", timeout=14000)
                    except Exception:
                        fail(f"Expected scoped synthetic fixture NOT visible at {viewport}:{route}")
                    verify_viewport(page, width, route)
                    snap = photo(page, output, viewport + "-" + name, width)
                    snapshots.append({"viewport": viewport, "route": route, **snap})
                if unexpected:
                    fail(viewport + ": unexpected JS/HTTP 5xx in live fixture pages")

                if viewport == "desktop":
                    # Actual user-like form creation, without selected fallback,
                    # unapproved control remains DRAFT and visible after POST.
                    goto(page, base, "/controls")
                    page.get_by_role("button", name="+ ایجاد کنترل").click()
                    form = page.locator('form[aria-label="ایجاد پیش‌نویس کنترل"]')
                    form.wait_for(state="visible", timeout=10000)
                    if form.locator('input[required]').count() < 2:
                        fail("Required control field validation missing.")
                    if form.evaluate("(f) => f.checkValidity()"):
                        fail("An empty control form may be submitted.")
                    form.locator('input[placeholder="CTRL-IAM-001"]').fill("ci-ctrl-ui-created")
                    form.locator('input[placeholder="عنوان کنترل را وارد کنید"]').fill("کنترل ساختگی ثبت‌شده با مرورگر")
                    form.get_by_role("button", name="ثبت پیش‌نویس").click()
                    try:
                        page.get_by_text("کنترل ساختگی ثبت‌شده با مرورگر").first.wait_for(
                            state="visible", timeout=20000,
                        )
                    except Exception:
                        fail("Control created via real form did not appear in API-backed table.")
                    checks.append("real_control_creation_draft_visible")

                    goto(page, base, "/risks")
                    page.get_by_role("button", name="+ ریسک جدید").click()
                    rf = page.locator("form.settingsForm").first
                    rf.wait_for(state="visible", timeout=10000)
                    if rf.locator("select").count() < 3:
                        fail("Risk deliberate owner selection form incomplete.")
                    # Assert the owner is NOT silently chosen (admin is only
                    # permitted OPTION, never preselected on user's behalf).
                    if rf.locator("select").nth(2).input_value() != "":
                        fail("Risk owner was preselected without human interaction.")
                    rf.locator('input[placeholder="RISK-001"]').fill("CI-RISK-UI-002")
                    rf.locator('input[placeholder="عنوان روشن و قابل پیگیری"]').fill("ریسک ساختگی ثبت‌شده با مرورگر")
                    rf.locator("select").nth(2).select_option(index=1)
                    rf.get_by_role("button", name="ثبت ریسک", exact=True).click()
                    try:
                        page.get_by_text("ریسک ساختگی ثبت‌شده با مرورگر").first.wait_for(
                            state="visible", timeout=20000,
                        )
                    except Exception:
                        fail("Risk created by explicit-owner UI form not visible.")
                    checks.append("real_risk_creation_explicit_owner_visible")

                if viewport == "mobile":
                    # Functional mobile open/navigation/close, not only screenshot.
                    goto(page, base, "/risks")
                    toggle = page.get_by_role("button", name="باز کردن منوی اصلی")
                    toggle.click()
                    sidebar = page.locator(".productSidebar")
                    if not sidebar.is_visible():
                        fail("Mobile sidebar fails to open.")
                    sidebar.locator('a.productNavLink[href="/controls"]').click()
                    page.wait_for_url(base + "/controls", timeout=14000)
                    if sidebar.is_visible():
                        fail("Mobile sidebar fails to close after route navigation.")
                    verify_viewport(page, width, "/controls")
                    checks.append("real_mobile_navigation_open_change_close")

                if unexpected:
                    fail("Real API/browser errors during interaction: " + viewport)
                context.close()
        finally:
            browser.close()

    if len(snapshots) != 8 or len(checks) != 3:
        fail("Missing populated live screenshots or interactive checks.")
    manifest = {
        "schema": "grc-ci-populated-browser-ux-v1",
        "source_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=install, text=True, timeout=10,
        ).strip(),
        "run_id": run_id,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "fictional_only": True,
        "human_approved": False,
        "customer_data_or_licensed_content": False,
        "login_mfa_tested": False,
        "scanned_commercial_release_tested": False,
        "checks": checks,
        "screenshots": snapshots,
    }
    (output / "POPULATED_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("CI-only real populated browser journeys PASS: 8 PNGs, 3 interactive checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
