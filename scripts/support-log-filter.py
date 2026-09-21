#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

SCHEMA = "grc-support-errors-v1"
SAFE_FIELDS = (
    "timestamp",
    "level",
    "logger",
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "error_type",
    "exception_type",
    "task",
    "component",
    "outcome",
)
ERROR_LEVELS = {"ERROR", "CRITICAL"}


def _extract_json(raw: str) -> dict | None:
    start = raw.find("{")
    if start < 0:
        return None
    try:
        payload = json.loads(raw[start:])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def filter_lines(lines, *, limit: int) -> list[dict]:
    rows: list[dict] = []
    for raw in lines:
        payload = _extract_json(raw)
        if not payload or str(payload.get("level", "")).upper() not in ERROR_LEVELS:
            continue
        row = {key: payload[key] for key in SAFE_FIELDS if key in payload}
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def self_test() -> None:
    sample = [
        'backend-1 | {"timestamp":"2026-01-01T00:00:00Z","level":"ERROR","logger":"grc","message":"password=super-secret customer=ACME","error_type":"RuntimeError","path":"/api/v1/x"}\n',
        'worker-1 | {"timestamp":"2026-01-01T00:00:01Z","level":"INFO","logger":"grc","message":"ignore"}\n',
    ]
    rows = filter_lines(sample, limit=20)
    if rows != [{
        "timestamp":"2026-01-01T00:00:00Z",
        "level":"ERROR",
        "logger":"grc",
        "path":"/api/v1/x",
        "error_type":"RuntimeError",
    }]:
        raise RuntimeError(f"unexpected filter result: {rows}")
    rendered = json.dumps(rows)
    if "super-secret" in rendered or "ACME" in rendered or "message" in rendered:
        raise RuntimeError("unsafe message/customer content leaked")


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter structured GRC logs to bounded allowlisted error metadata.")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("support log filter self-test passed")
        return 0
    if args.limit < 1 or args.limit > 1000:
        print("ERROR: --limit must be between 1 and 1000", file=sys.stderr)
        return 2
    rows = filter_lines(sys.stdin, limit=args.limit)
    for row in rows:
        print(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
