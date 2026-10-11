#!/usr/bin/env bash
# Disposable second-install/independent-volume recovery test using signed real images.
# SAME hosted runner/Docker daemon: never describe this as independent physical host UAT.
set -euo pipefail
umask 077
if [[ "${GITHUB_ACTIONS:-}" != "true" ||
      "${GRC_CORE_INSTALL_EPHEMERAL_ONLY:-NO}" != "YES" ||
      "${GRC_CORE_DR_EPHEMERAL_ONLY:-NO}" != "YES" ||
      "${GRC_CORE_REPLACEMENT_EPHEMERAL_ONLY:-NO}" != "YES" ]]; then
  echo 'ERROR: explicitly opted-in disposable GitHub Actions only.' >&2
  exit 2
fi
if [[ $# -ne 6 ]]; then
  echo 'Usage: ephemeral-replacement-core-dr.sh <source-repository> <signed-tar> <trusted-key> <new-install-root> <recovery-env> <expected-SHA>' >&2
  exit 2
fi
SOURCE="$1"
SIGNED="$2"
TRUSTED="$3"
TARGET="$4"
RECOVERY_ENV="$5"
SHA="$6"
SOURCE_PROJECT="${COMPOSE_PROJECT_NAME:-}"
[[ -n "$SOURCE_PROJECT" && -d "$SOURCE/.git" && -s "$SOURCE/.env" ]] || exit 3
[[ "$(git -C "$SOURCE" rev-parse HEAD)" == "$SHA" ]] || exit 3
[[ ! -e "$TARGET" && -s "$SIGNED" && -s "$TRUSTED" && -s "$RECOVERY_ENV" ]] || exit 3
NAME="ci-core-dr-${GITHUB_RUN_ID:-invalid}-${GITHUB_RUN_ATTEMPT:-1}"
[[ "$NAME" != *invalid* ]] || exit 3
[[ -d "$SOURCE/backups/$NAME" ]] || exit 3
NEW_PROJECT="grcreplacement${GITHUB_RUN_ID:-invalid}${GITHUB_RUN_ATTEMPT:-1}"
[[ "$NEW_PROJECT" != "$SOURCE_PROJECT" ]] || exit 3
CUSTODY="$(mktemp -d "$(dirname "$TARGET")/disposable-custody.XXXXXXXX")"
chmod 700 "$CUSTODY"
cleanup() {
  local status=$?
  trap - EXIT
  if [[ -s "$TARGET/repository/.env" ]]; then
    (export COMPOSE_PROJECT_NAME="$NEW_PROJECT"; cd "$TARGET/repository";
      docker compose --env-file .env -f docker-compose.pilot.yml -f docker-compose.pilot.tls.yml \
        --profile ops down --volumes --remove-orphans >/dev/null 2>&1) || true
  fi
  rm -rf -- "$CUSTODY"
  echo "Disposable replacement recovery cleanup: status=$status"
  exit "$status"
}
trap cleanup EXIT

echo '[REPL 1/7] Staging synthetic backup in separate private custody.'
(cd "$SOURCE" && python scripts/datacenter-backup-status.py --restore-preflight "$NAME" >/dev/null)
cp -a "$SOURCE/backups/$NAME" "$CUSTODY/$NAME"
[[ -s "$CUSTODY/$NAME/postgres.dump" && -s "$CUSTODY/$NAME/objectstore.zip" ]]
echo '[REPL 2/7] Removing ALL original running services and volumes.'
(
  cd "$SOURCE"
  docker compose --env-file .env -f docker-compose.pilot.yml -f docker-compose.pilot.tls.yml \
    --profile ops down --volumes --remove-orphans >/dev/null
)
for role in postgres_pilot_data redis_pilot_data objectstore_pilot_data; do
  if docker volume inspect "${SOURCE_PROJECT}_$role" >/dev/null 2>&1; then
    echo 'ERROR: old source volume survived destructive teardown' >&2
    exit 4
  fi
done
echo '[REPL 3/7] Independently installing the SAME signed source on a new root.'
OFFLINE_INSTALL_START=NO bash "$SOURCE/scripts/offline-release-apply.sh" install \
  "$SIGNED" "$TRUSTED" "$TARGET" "$RECOVERY_ENV" >/dev/null
[[ "$(git -C "$TARGET/repository" rev-parse HEAD)" == "$SHA" ]]
[[ -d "$TARGET/repository/backups" && -w "$TARGET/repository/backups" ]]
cp -a "$CUSTODY/$NAME" "$TARGET/repository/backups/$NAME"
(
  cd "$TARGET/repository"
  python scripts/datacenter-backup-status.py --restore-preflight "$NAME" >/dev/null
  bash scripts/datacenterctl recovery-preflight "$NAME" | python -c '
import json,sys
result=json.load(sys.stdin)
assert result["ready_for_operator_review"] is True
assert all(check["ok"] for check in result["checks"].values())
'
  echo "Signed replacement checkout read-only operator preflight PASS."
)
echo '[REPL 4/7] Requiring clean, previously nonexistent target volumes.'
for role in postgres_pilot_data redis_pilot_data objectstore_pilot_data; do
  if docker volume inspect "${NEW_PROJECT}_$role" >/dev/null 2>&1; then
    echo 'ERROR: replacement volume unexpectedly existed before recovery' >&2
    exit 4
  fi
done
echo '[REPL 5/7] Restoring through the official operator tool on fresh volumes.'
(
  export COMPOSE_PROJECT_NAME="$NEW_PROJECT"
  export RESTORE_INITIALIZE_MISSING_BUCKET=YES
  export DATACENTER_LOCAL_AI=NO
  cd "$TARGET/repository"
  CONFIRM_RESTORE=YES bash scripts/datacenterctl restore "$NAME" >/dev/null
)
echo '[REPL 6/7] Verifying independent SQL/S3 markers and TLS readiness.'
(
  export COMPOSE_PROJECT_NAME="$NEW_PROJECT"
  cd "$TARGET/repository"
  COMPOSE=(docker compose --env-file .env -f docker-compose.pilot.yml -f docker-compose.pilot.tls.yml)
  rows="$("${COMPOSE[@]}" exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT marker FROM ci_real_core_recovery_marker ORDER BY marker"' | tr -d '\r')"
  [[ "$rows" == "pre-backup" ]] || { echo 'ERROR: replacement SQL marker mismatch' >&2; exit 4; }
  "${COMPOSE[@]}" --profile ops run --rm -T ops python - <<'PY'
import hashlib, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
from apps.common.management.commands.pilot_objectstore_archive import s3_client
client=s3_client()
bucket=settings.S3_BUCKET
name='ci-real-core/pre-backup.bin'
response=client.list_objects_v2(Bucket=bucket)
assert {v['Key'] for v in response.get('Contents', [])} == {name}, 'Unexpected recovered object keys'
item=client.get_object(Bucket=bucket,Key=name)
expected=b'CI disposable GRC evidence marker - pre-backup\n'
assert hashlib.sha256(item['Body'].read()).digest() == hashlib.sha256(expected).digest(), 'Recovered evidence SHA mismatch'
assert item['Metadata'].get('origin') == 'ci-disposable-real-core', 'Evidence metadata mismatch'
print('Fresh-volume Evidence recovery verified')
PY
  bash scripts/datacenterctl verify >/dev/null
  python scripts/datacenter-backup-status.py --restore-preflight "$NAME" >/dev/null
)
[[ "$(git -C "$TARGET/repository" rev-parse HEAD)" == "$SHA" ]]
echo '[REPL 7/7] Disposable replacement-volume recovery PASS.'
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo '### Separate install root and fresh Docker-volume restore: PASS (CI-only)'
    echo '- Source stack destroyed including database, Redis and objectstore volumes before recovery.'
    echo '- Exact signed release installed to different checkout/root with different Compose project.'
    echo '- Actual production restore against fresh volumes, explicit missing-bucket initialization and real data verified.'
    echo '- NOT a separate physical machine, disconnected network, encrypted offsite backup, PKI/UAT or measured customer RPO/RTO.'
  } >> "$GITHUB_STEP_SUMMARY"
fi
