#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
umask 077

if [[ ! -f .env ]]; then
  echo "ERROR: .env is required. Copy and harden .env.pilot.example first." >&2
  exit 2
fi

NAME="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
if [[ ! "$NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "ERROR: backup name may contain only letters, numbers, dot, underscore and dash." >&2
  exit 2
fi

DEST="$ROOT/backups/$NAME"
if [[ -e "$DEST" ]]; then
  echo "ERROR: backup destination already exists: $DEST" >&2
  exit 2
fi
mkdir -p "$DEST"
chmod 700 "$ROOT/backups" "$DEST" 2>/dev/null || true

COMPOSE=(docker compose --env-file .env -f docker-compose.pilot.yml)
START_EPOCH="$(date +%s)"
START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SOURCE_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
RELEASE_ID="${GRC_RELEASE_VERSION:-$SOURCE_COMMIT}"

echo "[1/6] Checking required services..."
"${COMPOSE[@]}" up -d postgres redis objectstore backend >/dev/null
READY=0
for _ in $(seq 1 12); do
  if "${COMPOSE[@]}" exec -T backend python manage.py pilot_readiness >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 5
done
if [[ "$READY" != "1" ]]; then
  echo "ERROR: pilot readiness did not pass before backup." >&2
  "${COMPOSE[@]}" exec -T backend python manage.py pilot_readiness || true
  exit 3
fi

echo "[2/6] Backing up PostgreSQL..."
"${COMPOSE[@]}" exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DEST/postgres.dump"

if [[ ! -s "$DEST/postgres.dump" ]]; then
  echo "ERROR: PostgreSQL backup is empty." >&2
  exit 3
fi

echo "[3/6] Backing up S3-compatible object storage..."
"${COMPOSE[@]}" --profile ops run --rm ops \
  python manage.py pilot_objectstore_archive export \
  --archive "/backups/$NAME/objectstore.zip"

if [[ ! -s "$DEST/objectstore.zip" ]]; then
  echo "ERROR: object-storage backup is empty." >&2
  exit 3
fi

echo "[4/6] Capturing schema compatibility, configuration and image manifest..."
"${COMPOSE[@]}" --profile ops run --rm ops \
  python manage.py pilot_upgrade_guard snapshot \
  --output "/backups/$NAME/schema-manifest.json" \
  --release-id "$RELEASE_ID" \
  --source-commit "$SOURCE_COMMIT"

if [[ ! -s "$DEST/schema-manifest.json" ]]; then
  echo "ERROR: schema compatibility manifest is missing or empty." >&2
  exit 3
fi

install -m 600 .env "$DEST/config.env"
install -m 600 docker-compose.pilot.yml "$DEST/docker-compose.pilot.yml"
if [[ -f docker-compose.pilot.tls.yml ]]; then
  install -m 600 docker-compose.pilot.tls.yml "$DEST/docker-compose.pilot.tls.yml"
fi
"${COMPOSE[@]}" config --images | sort -u > "$DEST/images.txt"
printf '%s\n' "$SOURCE_COMMIT" > "$DEST/source-commit.txt"
printf '%s\n' "$RELEASE_ID" > "$DEST/release-id.txt"

echo "[5/6] Writing integrity manifest and observation metadata..."
(
  cd "$DEST"
  sha256sum \
    postgres.dump \
    objectstore.zip \
    schema-manifest.json \
    config.env \
    docker-compose.pilot.yml \
    images.txt \
    source-commit.txt \
    release-id.txt > SHA256SUMS
  if [[ -f docker-compose.pilot.tls.yml ]]; then
    sha256sum docker-compose.pilot.tls.yml >> SHA256SUMS
  fi
)

END_EPOCH="$(date +%s)"
END_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DURATION="$((END_EPOCH - START_EPOCH))"
cat > "$DEST/backup-observation.json" <<EOF
{
  "backup_name": "$NAME",
  "release_id": "$RELEASE_ID",
  "source_commit": "$SOURCE_COMMIT",
  "schema_manifest": "schema-manifest.json",
  "started_at": "$START_ISO",
  "completed_at": "$END_ISO",
  "duration_seconds": $DURATION,
  "contains_secret_bearing_config": true,
  "tls_private_key_included": false,
  "rpo_observation": null,
  "note": "Measure RPO with a controlled application marker during the restore drill; do not infer it from backup duration."
}
EOF
chmod 600 "$DEST"/*

echo "[6/6] Backup complete: $DEST"
echo "IMPORTANT: this directory contains config secrets. Store it only on approved encrypted backup media."
