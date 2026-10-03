#!/usr/bin/env python3
"""Enforce a narrow, time-bounded exception for an unfixed dev-only npm advisory.

Production dependencies are audited separately with:
    npm audit --omit=dev --audit-level=high

This script evaluates the full npm audit JSON and permits only the known
unfixed braces advisory GHSA-vfj7-8cjw-p6xm through 2026-11-03. Any other
HIGH/CRITICAL advisory fails the build. The exception must be revisited after
expiry and is not a security-acceptance artifact.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ALLOWED_ADVISORY = "GHSA-vfj7-8cjw-p6xm"
EXPIRES_ON = dt.date(2026, 11, 3)
BLOCKING = {"high", "critical"}
GHSA_RE = re.compile(r"GHSA-[0-9a-z-]+", re.IGNORECASE)


def _root_advisories(name: str, vulnerabilities: dict, seen: set[str] | None = None) -> set[str]:
    seen = set() if seen is None else set(seen)
    if name in seen:
        return set()
    seen.add(name)
    item = vulnerabilities.get(name) or {}
    roots: set[str] = set()
    for via in item.get("via") or []:
        if isinstance(via, str):
            roots.update(_root_advisories(via, vulnerabilities, seen))
            continue
        if not isinstance(via, dict):
            continue
        severity = str(via.get("severity") or "").lower()
        if severity not in BLOCKING:
            continue
        haystack = " ".join(
            str(via.get(key) or "") for key in ("url", "title", "name", "source")
        )
        match = GHSA_RE.search(haystack)
        roots.add(match.group(0).upper() if match else f"UNKNOWN:{haystack[:120]}")
    return roots


def evaluate(data: dict, *, today: dt.date | None = None) -> tuple[bool, list[str]]:
    today = today or dt.datetime.now(dt.timezone.utc).date()
    vulnerabilities = data.get("vulnerabilities") or {}
    blocking = []
    for name, item in sorted(vulnerabilities.items()):
        severity = str((item or {}).get("severity") or "").lower()
        if severity not in BLOCKING:
            continue
        roots = _root_advisories(name, vulnerabilities)
        blocking.append((name, severity, roots))

    if not blocking:
        return True, ["No HIGH/CRITICAL vulnerabilities are present in the full npm audit."]

    messages: list[str] = []
    disallowed = []
    for name, severity, roots in blocking:
        if roots == {ALLOWED_ADVISORY.upper()} and severity == "high":
            messages.append(
                f"Temporary dev-only exception: {name} severity={severity} root={ALLOWED_ADVISORY}"
            )
        else:
            disallowed.append((name, severity, sorted(roots)))
            messages.append(
                f"BLOCKED: {name} severity={severity} roots={','.join(sorted(roots)) or 'unknown'}"
            )

    if disallowed:
        return False, messages

    if today > EXPIRES_ON:
        messages.append(
            f"BLOCKED: exception for {ALLOWED_ADVISORY} expired on {EXPIRES_ON.isoformat()}."
        )
        return False, messages

    messages.append(
        f"Exception for {ALLOWED_ADVISORY} expires on {EXPIRES_ON.isoformat()}; "
        "production npm audit must pass separately."
    )
    return True, messages


def self_test() -> None:
    allowed = {
        "vulnerabilities": {
            "braces": {
                "severity": "high",
                "via": [
                    {
                        "severity": "high",
                        "url": "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm",
                        "title": "braces recursion",
                    }
                ],
            },
            "micromatch": {"severity": "high", "via": ["braces"]},
        }
    }
    ok, _ = evaluate(allowed, today=dt.date(2026, 10, 3))
    assert ok

    expired, _ = evaluate(allowed, today=dt.date(2026, 11, 4))
    assert not expired

    critical = {
        "vulnerabilities": {
            "next": {
                "severity": "critical",
                "via": [
                    {
                        "severity": "critical",
                        "url": "https://github.com/advisories/GHSA-vcvr-r3jv-pc5j",
                    }
                ],
            }
        }
    }
    ok, _ = evaluate(critical, today=dt.date(2026, 10, 3))
    assert not ok

    unknown = {
        "vulnerabilities": {
            "other": {
                "severity": "high",
                "via": [{"severity": "high", "title": "unknown vulnerability"}],
            }
        }
    }
    ok, _ = evaluate(unknown, today=dt.date(2026, 10, 3))
    assert not ok
    print("frontend-audit-check self-test: PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audit_json", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if not args.audit_json:
        parser.error("audit_json is required unless --self-test is used")

    path = Path(args.audit_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    ok, messages = evaluate(data)
    for message in messages:
        print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
