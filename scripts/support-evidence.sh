#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
umask 077

OUT="${1:-artifacts/support-evidence-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT"
chmod 700 "$OUT"

COMPOSE=(docker compose --env-file .env -f docker-compose.pilot.yml)
if [[ "${PILOT_TLS:-NO}" == "YES" ]]; then
  COMPOSE+=(-f docker-compose.pilot.tls.yml)
fi

safe_run() {
  local file="$1"
  shift
  if "$@" > "$OUT/$file" 2>&1; then
    printf 'success\n' > "$OUT/$file.status"
  else
    printf 'failed\n' > "$OUT/$file.status"
  fi
}

safe_run_json() {
  local file="$1"
  shift
  if "$@" > "$OUT/$file" 2>/dev/null; then
    printf 'success\n' > "$OUT/$file.status"
  else
    printf 'failed\n' > "$OUT/$file.status"
  fi
}

safe_run docker-version.txt docker version
safe_run compose-version.txt docker compose version
safe_run disk-usage.txt df -h
safe_run service-state.txt "${COMPOSE[@]}" ps
safe_run compose-images.txt "${COMPOSE[@]}" config --images
safe_run source-commit.txt git rev-parse HEAD

PREFLIGHT=(python scripts/datacenter-preflight.py --env-file .env --skip-host --json)
if [[ "${PILOT_TLS:-NO}" == "YES" ]]; then
  PREFLIGHT+=(--tls)
fi
safe_run_json configuration-status.json "${PREFLIGHT[@]}"

python - .env "$OUT/release-version.json" <<'PY'
import json
import re
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
version = None
for raw in env_path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key.strip() == "GRC_RELEASE_VERSION":
        value = value.strip().strip("'\"")
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
            version = value
        break
out_path.write_text(json.dumps({"schema": "grc-support-release-v1", "release_version": version}, sort_keys=True) + "\n", encoding="utf-8")
PY
printf 'success\n' > "$OUT/release-version.json.status"

if BACKEND_ID="$("${COMPOSE[@]}" ps -q backend 2>/dev/null)" && [[ -n "$BACKEND_ID" ]]; then
  safe_run_json readiness.json "${COMPOSE[@]}" exec -T backend python manage.py pilot_readiness --json
  safe_run_json operational-status.json "${COMPOSE[@]}" exec -T backend python manage.py operational_status --json
  safe_run migration-plan.txt "${COMPOSE[@]}" exec -T backend python manage.py showmigrations --plan

  if "${COMPOSE[@]}" logs --no-color --tail 500 backend worker beat gateway 2>/dev/null \
      | python scripts/support-log-filter.py --limit 200 > "$OUT/recent-errors.jsonl"; then
    printf 'success\n' > "$OUT/recent-errors.jsonl.status"
  else
    : > "$OUT/recent-errors.jsonl"
    printf 'failed\n' > "$OUT/recent-errors.jsonl.status"
  fi
else
  printf 'not-running\n' > "$OUT/readiness.json.status"
  printf 'not-running\n' > "$OUT/operational-status.json.status"
  printf 'not-running\n' > "$OUT/migration-plan.txt.status"
  : > "$OUT/recent-errors.jsonl"
  printf 'not-running\n' > "$OUT/recent-errors.jsonl.status"
fi

python - "$OUT" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1])
statuses = {}
for path in sorted(root.glob("*.status")):
    statuses[path.name] = path.read_text(encoding="utf-8").strip()
payload = {
    "schema": "grc-support-evidence-v2",
    "collected_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    "statuses": statuses,
    "recent_error_contract": {
        "source": "bounded structured service logs",
        "maximum_rows": 200,
        "message_field_included": False,
        "allowlisted_metadata_only": True,
    },
    "excluded_by_design": [
        ".env and environment-variable values",
        "TLS private keys and certificate bytes",
        "database dumps and object-store contents",
        "connector credentials/tokens",
        "raw application/service log messages",
        "customer records, evidence payloads and AI prompts/responses",
    ],
}
(root / "evidence-summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
chmod 600 "$OUT"/*

echo "Support evidence collected at: $OUT"
echo "Only bounded allowlisted ERROR/CRITICAL metadata is included; raw log messages are excluded."
