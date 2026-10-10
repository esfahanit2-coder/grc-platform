#!/usr/bin/env bash
# Synthetic PostgreSQL + SeaweedFS S3 recovery on an isolated GitHub-hosted runner.
# Not a signed offline installation, production recovery, or customer RPO/RTO evidence.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
umask 077

if [[ "${GITHUB_ACTIONS:-}" != "true" || "${GRC_DR_EPHEMERAL_ONLY:-NO}" != "YES" ]]; then
  echo "ERROR: explicitly opted-in ephemeral GitHub Actions runner is required." >&2
  exit 2
fi
if [[ -e .env ]]; then
  echo "ERROR: refusing to overwrite an existing environment." >&2
  exit 2
fi
for command in docker python git; do
  command -v "$command" >/dev/null || { echo "ERROR: missing prerequisite: $command" >&2; exit 2; }
done

export COMPOSE_PROJECT_NAME="grcidr${GITHUB_RUN_ID:-test}${GITHUB_RUN_ATTEMPT:-1}"
NAME="synthetic-dr-${GITHUB_RUN_ID:-test}-${GITHUB_RUN_ATTEMPT:-1}"
BACKUP="$ROOT/backups/$NAME"
VERSION="v-ci-dr-${GITHUB_SHA:0:10}"
COMPOSE=(docker compose --env-file .env -f docker-compose.pilot.yml)
cleanup() {
  local status=$?
  trap - EXIT
  if [[ -f .env ]]; then
    "${COMPOSE[@]}" --profile ops down --volumes --remove-orphans >/dev/null 2>&1 || true
  fi
  rm -f .env
  rm -rf -- "$BACKUP"
  echo "Synthetic DR cleanup; exit=$status"
  exit "$status"
}
trap cleanup EXIT

mkdir -p "$BACKUP"
python scripts/server-pilot-env.py \
  --hostname grc.ci.internal \
  --release-version "$VERSION" \
  --tls-cert /tmp/grc-ci-unused-tls.crt \
  --tls-key /tmp/grc-ci-unused-tls.key \
  --output .env >/dev/null
chmod 600 .env

echo '[1/9] Starting disposable PostgreSQL, Redis and SeaweedFS.'
"${COMPOSE[@]}" up -d --wait postgres redis objectstore
"${COMPOSE[@]}" --profile ops build ops
"${COMPOSE[@]}" --profile ops run --rm -T ops python manage.py migrate --noinput >/dev/null

s3_phase() {
  local phase="$1"
  "${COMPOSE[@]}" --profile ops run --rm -T ops python - "$phase" <<'PY'
import os
import sys
import time
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
from botocore.exceptions import ClientError
django.setup()
from django.conf import settings
from apps.common.management.commands.pilot_objectstore_archive import s3_client

phase = sys.argv[1]
client = s3_client()
bucket = settings.S3_BUCKET
before = 'ci-synthetic/pre-backup.txt'
after = 'ci-synthetic/post-backup.txt'
payload = b'CI synthetic Evidence content - no customer data\n'
if phase == 'seed':
    for attempt in range(30):
        try:
            client.list_buckets()
            break
        except Exception:
            if attempt == 29:
                raise
            time.sleep(2)
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)
    client.put_object(Bucket=bucket, Key=before, Body=payload,
                      ContentType='text/plain', Metadata={'origin': 'synthetic-ci'})
elif phase == 'after':
    client.put_object(Bucket=bucket, Key=after, Body=b'should disappear after restore')
elif phase == 'prove-no-delete':
    body = client.get_object(Bucket=bucket, Key=after)['Body'].read()
    assert body == b'should disappear after restore', 'Corrupt archive deleted existing object'
elif phase == 'verify-restored':
    rows = client.list_objects_v2(Bucket=bucket).get('Contents', [])
    keys = {row['Key'] for row in rows}
    assert keys == {before}, 'Recovered Evidence object names mismatch'
    item = client.get_object(Bucket=bucket, Key=before)
    assert item['Body'].read() == payload, 'Recovered Evidence bytes mismatch'
    assert item['Metadata'].get('origin') == 'synthetic-ci', 'Evidence metadata mismatch'
else:
    raise SystemExit('Unsupported synthetic DR phase')
print(f'S3 phase PASS: {phase}')
PY
}

s3_phase seed
"${COMPOSE[@]}" exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null <<'SQL'
CREATE TABLE ci_synthetic_dr_marker (value text PRIMARY KEY);
INSERT INTO ci_synthetic_dr_marker(value) VALUES ('pre-backup');
SQL

echo '[2/9] Capturing actual PostgreSQL custom dump and S3 archive.'
START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"${COMPOSE[@]}" exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$BACKUP/postgres.dump"
"${COMPOSE[@]}" --profile ops run --rm -T ops python manage.py pilot_objectstore_archive export \
  --archive "/backups/$NAME/objectstore.zip" >/dev/null
[[ -s "$BACKUP/postgres.dump" && -s "$BACKUP/objectstore.zip" ]]

# Metadata describes this explicitly synthetic CI snapshot; it is not field evidence.
install -m 600 .env "$BACKUP/config.env"
install -m 600 docker-compose.pilot.yml "$BACKUP/docker-compose.pilot.yml"
"${COMPOSE[@]}" config --images | sort -u > "$BACKUP/images.txt"
SOURCE_SHA="$(git rev-parse HEAD)"
printf '%s\n' "$SOURCE_SHA" > "$BACKUP/source-commit.txt"
PG_NUM="$("${COMPOSE[@]}" exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SHOW server_version_num"' | tr -d '\r[:space:]')"
COMPLETED_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python - "$BACKUP" "$NAME" "$SOURCE_SHA" "$VERSION" "$START_ISO" "$COMPLETED_ISO" "$PG_NUM" <<'PY'
import json
import sys
from pathlib import Path
root, name, sha, version, start, completed, pg = sys.argv[1:]
folder = Path(root)
manifest = {
    'schema': 'grc-backup-manifest-v1', 'backup_name': name,
    'created_at': start, 'source_commit': sha, 'release_version': version,
    'postgres': {'server_version_num': int(pg), 'major': int(pg)//10000,
                 'dump_format': 'custom'},
    'objectstore_archive_schema': 1, 'release_consistent_quiesce': True,
    'components': ['postgres.dump', 'objectstore.zip', 'config.env',
                   'docker-compose.pilot.yml', 'images.txt', 'source-commit.txt'],
}
observation = {
    'backup_name': name, 'started_at': start, 'completed_at': completed,
    'contains_secret_bearing_config': True, 'tls_private_key_included': False,
    'release_consistent_quiesce': True,
}
(folder / 'backup-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
(folder / 'backup-observation.json').write_text(json.dumps(observation), encoding='utf-8')
PY
(
  cd "$BACKUP"
  sha256sum postgres.dump objectstore.zip config.env docker-compose.pilot.yml images.txt source-commit.txt backup-manifest.json > SHA256SUMS
)
echo '[3/9] Testing production non-destructive restore preflight.'
python scripts/datacenter-backup-status.py --restore-preflight "$NAME" >/dev/null

s3_phase after
"${COMPOSE[@]}" exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null <<'SQL'
INSERT INTO ci_synthetic_dr_marker(value) VALUES ('post-backup');
SQL

echo '[4/9] Testing corrupt ZIP fails before deletion against actual SeaweedFS.'
python - "$BACKUP/objectstore.zip" "$BACKUP/invalid.zip" <<'PY'
from pathlib import Path
import sys, zipfile
source, destination = (Path(x) for x in sys.argv[1:])
with zipfile.ZipFile(source, 'r') as archive:
    entries = [(n, archive.read(n)) for n in archive.namelist()]
with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for name, value in entries:
        archive.writestr(name, b'CI deliberately corrupted content' if name.startswith('objects/') else value)
PY
if "${COMPOSE[@]}" --profile ops run --rm -T ops python manage.py pilot_objectstore_archive restore \
     --archive "/backups/$NAME/invalid.zip" --replace >/dev/null 2>&1; then
  echo 'ERROR: corrupt archive was accepted for restore.' >&2
  exit 4
fi
s3_phase prove-no-delete

echo '[5/9] Restoring actual PostgreSQL data.'
"${COMPOSE[@]}" exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges' < "$BACKUP/postgres.dump" >/dev/null
DB_MARKERS="$("${COMPOSE[@]}" exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT value FROM ci_synthetic_dr_marker ORDER BY value"' | tr -d '\r')"
[[ "$DB_MARKERS" == 'pre-backup' ]] || { echo 'ERROR: recovered PostgreSQL marker mismatch.' >&2; exit 4; }

echo '[6/9] Restoring actual S3 objects and verifying bytes/metadata.'
"${COMPOSE[@]}" --profile ops run --rm -T ops python manage.py pilot_objectstore_archive restore \
  --archive "/backups/$NAME/objectstore.zip" --replace >/dev/null
s3_phase verify-restored

echo '[7/9] Validating original backup after round-trip.'
python scripts/datacenter-backup-status.py --restore-preflight "$NAME" >/dev/null
echo '[8/9] Recording synthetic-only CI result.'
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo '### Synthetic PostgreSQL + S3 recovery: PASS'
    echo '- Real PostgreSQL dump/restore and real SeaweedFS archive recovery tested.'
    echo '- Post-backup markers absent; pre-backup records, Evidence bytes and metadata retained.'
    echo '- Corrupt S3 archive rejected before deleting existing objects.'
    echo '- NOT signed offline installation, customer UAT, independent security review or RPO/RTO proof.'
  } >> "$GITHUB_STEP_SUMMARY"
fi
echo '[9/9] Synthetic DR passed; deleting test volumes and temporary secrets.'
