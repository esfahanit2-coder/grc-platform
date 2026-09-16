#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
umask 077

PREVIOUS_BACKEND_IMAGE="${PREVIOUS_BACKEND_IMAGE:-}"
CANDIDATE_BACKEND_IMAGE="${CANDIDATE_BACKEND_IMAGE:-}"
ROLLBACK_STRATEGY="${ROLLBACK_STRATEGY:-reversible}"
PREVIOUS_RELEASE_ID="${PREVIOUS_RELEASE_ID:-$PREVIOUS_BACKEND_IMAGE}"
CANDIDATE_RELEASE_ID="${CANDIDATE_RELEASE_ID:-$CANDIDATE_BACKEND_IMAGE}"
PREVIOUS_SOURCE_COMMIT="${PREVIOUS_SOURCE_COMMIT:-unknown}"
CANDIDATE_SOURCE_COMMIT="${CANDIDATE_SOURCE_COMMIT:-unknown}"
REPORT_PATH="${UPGRADE_REHEARSAL_REPORT:-$ROOT/runtime/upgrade-rehearsal.json}"

if [[ -z "$PREVIOUS_BACKEND_IMAGE" || -z "$CANDIDATE_BACKEND_IMAGE" ]]; then
  echo "ERROR: PREVIOUS_BACKEND_IMAGE and CANDIDATE_BACKEND_IMAGE are required." >&2
  exit 2
fi
if [[ "$PREVIOUS_BACKEND_IMAGE" =~ :latest$ || "$CANDIDATE_BACKEND_IMAGE" =~ :latest$ ]]; then
  echo "ERROR: mutable :latest image tags are not valid upgrade rehearsal inputs." >&2
  exit 2
fi
if [[ "$ROLLBACK_STRATEGY" != "reversible" && "$ROLLBACK_STRATEGY" != "restore" ]]; then
  echo "ERROR: ROLLBACK_STRATEGY must be reversible or restore." >&2
  exit 2
fi

mkdir -p "$(dirname "$REPORT_PATH")"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/grc-upgrade-rehearsal.XXXXXX")"
NETWORK="grc-upgrade-rehearsal-$$"
POSTGRES_CONTAINER="grc-upgrade-postgres-$$"
POSTGRES_DB="grc_upgrade"
POSTGRES_USER="grc"
POSTGRES_PASSWORD="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
DJANGO_SECRET_KEY="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(64))
PY
)"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_EPOCH="$(date +%s)"

cleanup() {
  docker rm -f "$POSTGRES_CONTAINER" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

docker network create "$NETWORK" >/dev/null
docker run -d --name "$POSTGRES_CONTAINER" --network "$NETWORK" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  pgvector/pgvector:0.8.6-pg18-trixie >/dev/null

READY=0
for _ in $(seq 1 30); do
  if docker exec "$POSTGRES_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
done
if [[ "$READY" != "1" ]]; then
  echo "ERROR: disposable PostgreSQL did not become ready." >&2
  exit 3
fi

APP_ENV_ARGS=(
  --network "$NETWORK"
  -e APP_ENV=development
  -e DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY"
  -e POSTGRES_DB="$POSTGRES_DB"
  -e POSTGRES_USER="$POSTGRES_USER"
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD"
  -e POSTGRES_HOST="$POSTGRES_CONTAINER"
  -e POSTGRES_PORT=5432
)

run_previous() {
  docker run --rm "${APP_ENV_ARGS[@]}" "$PREVIOUS_BACKEND_IMAGE" "$@"
}

run_candidate() {
  docker run --rm "${APP_ENV_ARGS[@]}" \
    -v "$WORKDIR:/rehearsal" \
    "$CANDIDATE_BACKEND_IMAGE" "$@"
}

echo "[1/8] Migrating disposable database with previous image..."
run_previous python manage.py migrate --noinput

echo "[2/8] Capturing previous schema baseline with candidate guard..."
run_candidate python manage.py pilot_upgrade_guard snapshot \
  --allow-pending \
  --output /rehearsal/baseline-schema.json \
  --release-id "$PREVIOUS_RELEASE_ID" \
  --source-commit "$PREVIOUS_SOURCE_COMMIT"

echo "[3/8] Creating and verifying baseline database dump..."
docker exec "$POSTGRES_CONTAINER" pg_dump \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$WORKDIR/baseline.dump"
if [[ ! -s "$WORKDIR/baseline.dump" ]]; then
  echo "ERROR: baseline database dump is empty." >&2
  exit 3
fi
cat "$WORKDIR/baseline.dump" | docker exec -i "$POSTGRES_CONTAINER" pg_restore --list >/dev/null

PREFLIGHT=(
  python manage.py pilot_upgrade_guard preflight
  --baseline /rehearsal/baseline-schema.json
  --rollback-strategy "$ROLLBACK_STRATEGY"
  --release-id "$CANDIDATE_RELEASE_ID"
  --source-commit "$CANDIDATE_SOURCE_COMMIT"
  --report /rehearsal/preflight.json
)
if [[ "$ROLLBACK_STRATEGY" == "restore" ]]; then
  PREFLIGHT+=(--backup-verified)
fi

echo "[4/8] Running fail-closed candidate upgrade preflight..."
run_candidate "${PREFLIGHT[@]}"

echo "[5/8] Applying candidate migrations and Django checks..."
run_candidate python manage.py migrate --noinput
run_candidate python manage.py check
run_candidate python manage.py pilot_upgrade_guard snapshot \
  --output /rehearsal/candidate-schema-first-pass.json \
  --release-id "$CANDIDATE_RELEASE_ID" \
  --source-commit "$CANDIDATE_SOURCE_COMMIT"

echo "[6/8] Exercising selected rollback strategy..."
if [[ "$ROLLBACK_STRATEGY" == "reversible" ]]; then
  run_candidate python manage.py pilot_upgrade_guard rollback \
    --baseline /rehearsal/baseline-schema.json \
    --confirm ROLLBACK_SCHEMA \
    --report /rehearsal/rollback.json
else
  echo "Restoring verified baseline dump because schema rollback strategy is restore."
  cat "$WORKDIR/baseline.dump" | docker exec -i "$POSTGRES_CONTAINER" pg_restore \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --clean --if-exists --no-owner --no-privileges
fi

# Whether rollback used reverse migrations or backup restore, the database must now
# exactly match the captured previous schema before a second forward pass.
run_candidate python manage.py pilot_upgrade_guard preflight \
  --baseline /rehearsal/baseline-schema.json \
  --rollback-strategy "$ROLLBACK_STRATEGY" \
  $([[ "$ROLLBACK_STRATEGY" == "restore" ]] && printf '%s' '--backup-verified') \
  --release-id "$CANDIDATE_RELEASE_ID" \
  --source-commit "$CANDIDATE_SOURCE_COMMIT" \
  --report /rehearsal/preflight-after-rollback.json

echo "[7/8] Reapplying candidate migrations to prove repeatability..."
run_candidate python manage.py migrate --noinput
run_candidate python manage.py check
run_candidate python manage.py pilot_upgrade_guard snapshot \
  --output /rehearsal/candidate-schema-final.json \
  --release-id "$CANDIDATE_RELEASE_ID" \
  --source-commit "$CANDIDATE_SOURCE_COMMIT"

COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DURATION="$(( $(date +%s) - START_EPOCH ))"
python3 - "$WORKDIR" "$REPORT_PATH" <<'PY'
import json
import os
import pathlib
import sys

work = pathlib.Path(sys.argv[1])
report_path = pathlib.Path(sys.argv[2])
preflight = json.loads((work / "preflight.json").read_text(encoding="utf-8"))
final_schema = json.loads((work / "candidate-schema-final.json").read_text(encoding="utf-8"))
report = {
    "schema_version": "grc-upgrade-rehearsal-v1",
    "previous_image": os.environ["PREVIOUS_BACKEND_IMAGE"],
    "candidate_image": os.environ["CANDIDATE_BACKEND_IMAGE"],
    "previous_release_id": os.environ.get("PREVIOUS_RELEASE_ID", "unknown"),
    "candidate_release_id": os.environ.get("CANDIDATE_RELEASE_ID", "unknown"),
    "previous_source_commit": os.environ.get("PREVIOUS_SOURCE_COMMIT", "unknown"),
    "candidate_source_commit": os.environ.get("CANDIDATE_SOURCE_COMMIT", "unknown"),
    "rollback_strategy": os.environ.get("ROLLBACK_STRATEGY", "reversible"),
    "started_at": os.environ["STARTED_AT"],
    "completed_at": os.environ["COMPLETED_AT"],
    "duration_seconds": int(os.environ["DURATION"]),
    "pending_migrations_at_preflight": preflight["pending_migrations"],
    "irreversible_operations": preflight["irreversible_operations"],
    "final_migration_state_hash": final_schema["migration_state_hash"],
    "forward_migration_repeated_after_rollback": True,
    "result": "pass",
}
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
try:
    os.chmod(report_path, 0o600)
except OSError:
    pass
PY

echo "[8/8] Upgrade rehearsal PASS: $REPORT_PATH"
