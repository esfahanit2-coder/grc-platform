#!/usr/bin/env python3
"""Bounded HTTP load/smoke harness for GRC pilot environments.

This tool measures a specific target environment. Results from GitHub-hosted runners
must not be represented as production capacity or contractual SLO evidence.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ENDPOINTS = [
    "/api/v1/dashboard/management/",
    "/api/v1/risks/?page=1",
    "/api/v1/controls/?page=1",
    "/api/v1/assessments/?page=1",
]


@dataclass(frozen=True)
class Sample:
    scenario: str
    method: str
    duration_ms: float
    status: int | None
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 400 and not self.error


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return round(ordered[index], 3)


def summarize(samples: list[Sample]) -> dict:
    durations = [sample.duration_ms for sample in samples]
    success = sum(1 for sample in samples if sample.ok)
    total = len(samples)
    statuses = Counter(str(sample.status) if sample.status is not None else "transport_error" for sample in samples)
    errors = Counter(sample.error for sample in samples if sample.error)
    return {
        "requests": total,
        "success": success,
        "failed": total - success,
        "error_rate": round((total - success) / total, 6) if total else 0.0,
        "latency_ms": {
            "mean": round(statistics.fmean(durations), 3) if durations else None,
            "p50": percentile(durations, 0.50),
            "p95": percentile(durations, 0.95),
            "max": round(max(durations), 3) if durations else None,
        },
        "status_counts": dict(sorted(statuses.items())),
        "errors": dict(errors.most_common(10)),
    }


def join_url(base_url: str, endpoint: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))


def request_once(*, scenario: str, method: str, url: str, headers: dict[str, str], payload: bytes | None, timeout: float) -> Sample:
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    started = time.perf_counter()
    status = None
    error = ""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        try:
            exc.read()
        except Exception:
            pass
        error = f"http_{status}"
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:180]}"
    duration_ms = (time.perf_counter() - started) * 1000.0
    return Sample(scenario=scenario, method=method, duration_ms=duration_ms, status=status, error=error)


def run_scenario(*, name: str, method: str, url: str, headers: dict[str, str], payload: bytes | None, warmup: int, requests: int, concurrency: int, timeout: float) -> list[Sample]:
    for _ in range(max(0, warmup)):
        request_once(scenario=name, method=method, url=url, headers=headers, payload=payload, timeout=timeout)
    samples: list[Sample] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = [
            executor.submit(
                request_once,
                scenario=name,
                method=method,
                url=url,
                headers=headers,
                payload=payload,
                timeout=timeout,
            )
            for _ in range(max(1, requests))
        ]
        for future in concurrent.futures.as_completed(futures):
            samples.append(future.result())
    return samples


def self_test() -> int:
    assert percentile([10.0, 20.0, 30.0, 40.0], 0.50) == 20.0
    assert percentile([10.0, 20.0, 30.0, 40.0], 0.95) == 40.0
    report = summarize([
        Sample("x", "GET", 10.0, 200),
        Sample("x", "GET", 20.0, 200),
        Sample("x", "GET", 30.0, 500, "http_500"),
    ])
    assert report["requests"] == 3
    assert report["success"] == 2
    assert report["failed"] == 1
    assert report["status_counts"] == {"200": 2, "500": 1}
    print("http-load-smoke self-test: PASS")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Measure bounded GRC HTTP load on an explicitly selected environment.")
    result.add_argument("--base-url", default=os.getenv("GRC_BASE_URL", ""))
    result.add_argument("--tenant-id", default=os.getenv("GRC_TENANT_ID", ""))
    result.add_argument("--access-token", default=os.getenv("GRC_ACCESS_TOKEN", ""), help="Bearer token; prefer GRC_ACCESS_TOKEN environment variable.")
    result.add_argument("--endpoint", action="append", dest="endpoints", help="Repeat to override the default read-only scenarios.")
    result.add_argument("--requests", type=int, default=30, help="Measured requests per scenario.")
    result.add_argument("--concurrency", type=int, default=4)
    result.add_argument("--warmup", type=int, default=2)
    result.add_argument("--timeout", type=float, default=15.0)
    result.add_argument("--label", default=os.getenv("GRC_LOAD_LABEL", "unlabelled-target"))
    result.add_argument("--output", help="Optional JSON output path.")
    result.add_argument("--max-p95-ms", type=float, default=None, help="Optional engineering budget; not a production SLO declaration.")
    result.add_argument("--max-error-rate", type=float, default=None, help="Optional 0..1 engineering budget.")
    result.add_argument("--allow-writes", action="store_true", help="Explicitly allow an additional destructive/write scenario in a disposable tenant.")
    result.add_argument("--write-endpoint", help="POST/PATCH endpoint used only with --allow-writes.")
    result.add_argument("--write-method", choices=["POST", "PATCH"], default="POST")
    result.add_argument("--write-payload-file", help="JSON payload file used only with --allow-writes.")
    result.add_argument("--self-test", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.base_url or not args.tenant_id or not args.access_token:
        raise SystemExit("--base-url, --tenant-id and --access-token (or GRC_* env vars) are required.")
    if args.requests < 1 or args.concurrency < 1 or args.warmup < 0 or args.timeout <= 0:
        raise SystemExit("requests/concurrency must be >=1, warmup >=0 and timeout >0.")
    if args.max_error_rate is not None and not 0 <= args.max_error_rate <= 1:
        raise SystemExit("--max-error-rate must be between 0 and 1.")

    headers = {
        "Authorization": f"Bearer {args.access_token}",
        "X-Tenant-ID": args.tenant_id,
        "Accept": "application/json",
        "User-Agent": "grc-pre-rc-load-smoke/1",
    }
    scenarios: list[tuple[str, str, str, bytes | None]] = []
    for endpoint in args.endpoints or DEFAULT_ENDPOINTS:
        scenarios.append((endpoint, "GET", join_url(args.base_url, endpoint), None))

    if args.allow_writes:
        if not args.write_endpoint or not args.write_payload_file:
            raise SystemExit("--allow-writes requires --write-endpoint and --write-payload-file.")
        payload_path = Path(args.write_payload_file)
        payload = payload_path.read_bytes()
        json.loads(payload.decode("utf-8"))
        write_headers = dict(headers)
        write_headers["Content-Type"] = "application/json"
        scenarios.append((f"WRITE {args.write_endpoint}", args.write_method, join_url(args.base_url, args.write_endpoint), payload))
    elif args.write_endpoint or args.write_payload_file:
        raise SystemExit("Write arguments are ignored unless --allow-writes is explicitly set.")

    started_at = time.time()
    per_scenario: dict[str, dict] = {}
    all_samples: list[Sample] = []
    for name, method, url, payload in scenarios:
        scenario_headers = dict(headers)
        if payload is not None:
            scenario_headers["Content-Type"] = "application/json"
        samples = run_scenario(
            name=name,
            method=method,
            url=url,
            headers=scenario_headers,
            payload=payload,
            warmup=args.warmup,
            requests=args.requests,
            concurrency=args.concurrency,
            timeout=args.timeout,
        )
        all_samples.extend(samples)
        per_scenario[name] = {"method": method, "url_path": urllib.parse.urlparse(url).path, **summarize(samples)}

    overall = summarize(all_samples)
    report = {
        "schema_version": "grc-performance-v1",
        "label": args.label,
        "target": urllib.parse.urlsplit(args.base_url)._replace(query="", fragment="").geturl(),
        "generated_at_unix": round(time.time(), 3),
        "duration_seconds": round(time.time() - started_at, 3),
        "configuration": {
            "requests_per_scenario": args.requests,
            "concurrency": args.concurrency,
            "warmup": args.warmup,
            "timeout_seconds": args.timeout,
            "write_scenario_enabled": bool(args.allow_writes),
        },
        "overall": overall,
        "scenarios": per_scenario,
        "interpretation": "Environment-specific engineering measurement; GitHub-hosted-runner results are not production capacity evidence.",
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")

    failed = False
    if args.max_error_rate is not None and overall["error_rate"] > args.max_error_rate:
        print(f"FAIL: error_rate {overall['error_rate']} > budget {args.max_error_rate}", file=sys.stderr)
        failed = True
    p95 = overall["latency_ms"]["p95"]
    if args.max_p95_ms is not None and p95 is not None and p95 > args.max_p95_ms:
        print(f"FAIL: p95 {p95}ms > budget {args.max_p95_ms}ms", file=sys.stderr)
        failed = True
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
