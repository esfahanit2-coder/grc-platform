#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
umask 077

NAME="${1:-}"
if [[ -z "$NAME" || ! "$NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Usage: CONFIRM_RESTORE=YES $0 <backup-name>" >&2
  exit 2
fi
if [[ "${CONFIRM_RESTORE:-NO}" != "YES" ]]; then
  echo "ERROR: restore is destructive. Set CONFIRM_RESTORE=YES after change approval." >&2
  exit 2
fi

SRC="$ROOT/backups/$NAME"
if [[ ! -d "$SRC" ]]; then
  echo "ERROR: backup directory not found: $SRC" >&2
  exit 2
fi
for required in postgres.dump objectstore.zip schema-manifest.json config.env SHA256SUMS; do
  if [[ ! -s "$SRC/$required" ]]; then
    echo "ERROR: required backup component is missing or empty: $required" >&2
    echo "Legacy backups without schema-manifest.json require an explicitly reviewed legacy restore procedure and are not auto-restored." >&2
    exit 3
  fi
done

(
  cd "$SRC"
  sha256sum -c SHA256SUMS
)

if [[ "${RESTORE_CONFIG:-NO}" == "YES" ]]; then
  if [[ -f .env ]]; then
    install -m 600 .env ".env.pre-restore.$(date -u +%Y%m%dT%H%M%SZ)"
  fi
  install -m 600 "$SRC/config.env" .env
  echo "Restored .env from backup. Review host-specific values before exposing the service."
elif [[ ! -f .env ]]; then
  echo "ERROR: .env is absent. Either create it or set RESTORE_CONFIG=YES." >&2
  exit 2
fi

COMPOSE=(docker compose --env-file .env -f docker-compose.pilot.yml)
if [[ "${PILOT_TLS:-NO}" == "YES" ]]; then
  COMPOSE+=(-f docker-compose.pilot.tls.yml)
fi
LOCAL_AI=0
if [[ "${PILOT_LOCAL_AI:-NO}" == "YES" ]]; then
  COMPOSE+=(--profile local-ai)
  LOCAL_AI=1
fi

START_EPOCH="$(date +%s)"
START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "[1/7] Validating backup schema compatibility before destructive changes..."
"${COMPOSE[@]}" up -d postgres redis objectstore >/dev/null
"${COMPOSE[@]}" --profile ops run --rm ops \
  python manage.py pilot_upgrade_guard restore-check \
  --manifest "/backups/$NAME/schema-manifest.json" \
  --report "/backups/$NAME/restore-compatibility.json"
chmod 600 "$SRC/restore-compatibility.json" 2>/dev/null || true

echo "[2/7] Stopping application writers..."
"${COMPOSE[@]}" stop gateway frontend worker beat backend >/dev/null 2>&1 || true

echo "[3/7] Confirming restore dependencies are running..."
"${COMPOSE[@]}" up -d postgres redis objectstore >/dev/null

echo "[4/7] Restoring PostgreSQL..."
cat "$SRC/postgres.dump" | "${COMPOSE[@]}" exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges'

echo "[5/7] Restoring object storage..."
"${COMPOSE[@]}" --profile ops run --rm ops \
  python manage.py pilot_objectstore_archive restore \
  --archive "/backups/$NAME/objectstore.zip" \
  --replace

echo "[6/7] Starting application services and waiting for candidate migrations/health..."
APP_SERVICES=(backend worker beat frontend gateway)
if [[ "$LOCAL_AI" == "1" ]]; then
  APP_SERVICES+=(ollama)
fi
"${COMPOSE[@]}" up -d --wait "${APP_SERVICES[@]}"

READINESS=(python manage.py pilot_readiness)
if [[ -n "${AI_PROVIDER_ID:-}" ]]; then
  READINESS+=(--ai-provider-id "$AI_PROVIDER_ID")
fi
"${COMPOSE[@]}" exec -T backend "${READINESS[@]}"

END_EPOCH="$(date +%s)"
END_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DURATION="$((END_EPOCH - START_EPOCH))"
cat > "$SRC/restore-observation.json" <<EOF
{
  "backup_name": "$NAME",
  "restore_started_at": "$START_ISO",
  "service_readiness_confirmed_at": "$END_ISO",
  "observed_rto_seconds": $DURATION,
  "rpo_observation": null,
  "schema_compatibility_checked": true,
  "config_restored": "${RESTORE_CONFIG:-NO}",
  "local_ai_smoke_requested": $([[ -n "${AI_PROVIDER_ID:-}" ]] && echo true || echo false),
  "note": "Record RPO from a controlled application marker created before backup and checked after restore."
}
EOF
chmod 600 "$SRC/restore-observation.json"

echo "[7/7] Restore completed and core readiness passed in ${DURATION}s."
echo "Next: verify a controlled application marker, evidence object download, login/CSRF flow, and any local-AI model response required by the drill."
