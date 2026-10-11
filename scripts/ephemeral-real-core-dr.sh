#!/usr/bin/env bash
# CI-only live full-stack backup/restore, extending the signed-image core install.
# Never run on customer infrastructure; no production RPO/RTO is established.
set -euo pipefail
umask 077
if [[ "${GITHUB_ACTIONS:-}" != "true" ||
      "${GRC_CORE_DR_EPHEMERAL_ONLY:-NO}" != "YES" ||
      "${GRC_CORE_INSTALL_EPHEMERAL_ONLY:-NO}" != "YES" ]]; then
  echo 'ERROR: disposable opted-in CI-only full-stack DR test.' >&2
  exit 2
fi
if [[ $# -ne 2 ]]; then
  echo 'ERROR: expected installed repository path and signed source SHA.' >&2
  exit 2
fi
INSTALL_REPO="$1"
EXPECTED_SHA="$2"
[[ -d "$INSTALL_REPO/.git" && -s "$INSTALL_REPO/.env" ]]
[[ "$(git -C "$INSTALL_REPO" rev-parse HEAD)" == "$EXPECTED_SHA" ]] || {
  echo 'ERROR: restore source does not match signed commit' >&2
  exit 3
}
cd "$INSTALL_REPO"
[[ -n "${COMPOSE_PROJECT_NAME:-}" ]] || { echo 'ERROR: isolated Compose project is required' >&2; exit 2; }
NAME="ci-core-dr-${GITHUB_RUN_ID:-invalid}-${GITHUB_RUN_ATTEMPT:-1}"
[[ "$NAME" != *invalid* ]] || exit 2
BACKUP="$PWD/backups/$NAME"
COMPOSE=(docker compose --env-file .env -f docker-compose.pilot.yml -f docker-compose.pilot.tls.yml)
BACKUP_QUIESCE=YES
export BACKUP_QUIESCE
# The outer signed-install runner destroys this entire repository, secrets and volumes.
test ! -e "$BACKUP" || { echo 'ERROR: synthetic backup name already exists.' >&2; exit 3; }

s3_marker() {
  local phase="$1"
  "${COMPOSE[@]}" --profile ops run --rm -T ops python - "$phase" <<'PY'
import os, sys, time, hashlib
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
from botocore.exceptions import ClientError
django.setup()
from django.conf import settings
from apps.common.management.commands.pilot_objectstore_archive import s3_client
client=s3_client()
bucket=settings.S3_BUCKET
phase=sys.argv[1]
before='ci-real-core/pre-backup.bin'
after='ci-real-core/post-backup.bin'
payload=b'CI disposable GRC evidence marker - pre-backup\n'
if phase == 'seed':
    for trial in range(30):
        try:
            client.list_buckets()
            break
        except Exception:
            if trial == 29: raise
            time.sleep(2)
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)
    client.put_object(Bucket=bucket, Key=before, Body=payload,
                      ContentType='application/octet-stream',
                      Metadata={'origin':'ci-disposable-real-core'})
elif phase == 'mutate':
    client.put_object(Bucket=bucket,Key=after,Body=b'CI post-backup should disappear')
elif phase == 'prove-denial':
    item=client.get_object(Bucket=bucket,Key=after)
    assert item['Body'].read()==b'CI post-backup should disappear', 'Blocked restore destroyed later evidence'
elif phase == 'verify-restored':
    keys={row['Key'] for row in client.list_objects_v2(Bucket=bucket).get('Contents',[])}
    assert keys=={before}, 'Actual S3 recovered marker key set mismatch'
    item=client.get_object(Bucket=bucket,Key=before)
    assert hashlib.sha256(item['Body'].read()).digest()==hashlib.sha256(payload).digest(), 'Recovered evidence content hash mismatch'
    assert item['Metadata'].get('origin')=='ci-disposable-real-core','Recovered evidence metadata mismatch'
else:
    raise SystemExit('Unsupported DR step')
print('S3 verification PASS: '+phase)
PY
}

db_marker() {
  local phase="$1"
  case "$phase" in
    seed)
      "${COMPOSE[@]}" exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL' >/dev/null
CREATE TABLE ci_real_core_recovery_marker (marker text PRIMARY KEY);
INSERT INTO ci_real_core_recovery_marker(marker) VALUES ('pre-backup');
SQL
      ;;
    mutate)
      "${COMPOSE[@]}" exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL' >/dev/null
INSERT INTO ci_real_core_recovery_marker(marker) VALUES ('post-backup');
SQL
      ;;
    prove-denial)
      local rows
      rows="$("${COMPOSE[@]}" exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT marker FROM ci_real_core_recovery_marker ORDER BY marker"' | tr -d '\r')"
      [[ "$rows" == $'post-backup\npre-backup' ]] || {
        echo 'ERROR: rejected tampered restore changed PostgreSQL.' >&2
        exit 4
      }
      ;;
    verify-restored)
      local rows
      rows="$("${COMPOSE[@]}" exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT marker FROM ci_real_core_recovery_marker ORDER BY marker"' | tr -d '\r')"
      [[ "$rows" == 'pre-backup' ]] || { echo 'ERROR: recovered PostgreSQL marker mismatch.' >&2; exit 4; }
      ;;
    *) echo 'ERROR: unknown DB phase' >&2; exit 2;;
  esac
  echo "PostgreSQL verification PASS: $phase"
}

# Validate the real public operator CLI output without ever printing archived data or keys.
assert_operator_preflight_pass() {
  local report
  report="$(bash scripts/datacenterctl recovery-preflight "$NAME")" || {
    echo 'ERROR: operator recovery preflight rejected a valid signed backup' >&2
    exit 4
  }
  printf '%s\n' "$report" | python -c '
import json,sys
value=json.load(sys.stdin)
assert value["schema"]=="grc-datacenter-recovery-operator-preflight-v1"
assert value["ready_for_operator_review"] is True
assert all(row["ok"] is True for row in value["checks"].values())
assert "backup_name" not in value and "secret" not in value
'
  echo 'Read-only recovery operator preflight PASS: valid archive, critical identity, exact source.'
}

assert_operator_preflight_denied() {
  local key="$1" report
  if report="$(bash scripts/datacenterctl recovery-preflight "$NAME")"; then
    echo "ERROR: operator recovery preflight accepted a corrupted prerequisite: $key" >&2
    exit 4
  fi
  printf '%s\n' "$report" | python -c '
import json,sys
value=json.load(sys.stdin)
key=sys.argv[1]
assert value["ready_for_operator_review"] is False
assert value["checks"][key]["ok"] is False
' "$key"
  echo "Read-only recovery operator preflight correctly refused: $key"
}

echo '[DR 1/8] Seeding synthetic SQL rows and S3 Evidence on the signed installed stack.'
s3_marker seed
db_marker seed
echo '[DR 2/8] Calling the canonical datacenterctl backup with writers quiesced.'
bash scripts/datacenterctl backup "$NAME" >/dev/null
test -s "$BACKUP/postgres.dump" && test -s "$BACKUP/objectstore.zip"
python scripts/datacenter-backup-status.py --restore-preflight "$NAME" >/dev/null
assert_operator_preflight_pass
echo '[DR 3/8] Introducing post-backup mutations in running PostgreSQL and SeaweedFS.'
db_marker mutate
s3_marker mutate
echo '[DR 4/8] Proving mismatched replacement keys are rejected BEFORE destructive restoration.'
CI_ENV_COPY="$(mktemp "$INSTALL_REPO/../${NAME}-pre-key-test-XXXXXXXX.env")"
cp .env "$CI_ENV_COPY"
python - .env <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
data=path.read_text(encoding="utf-8")
rows=data.splitlines(keepends=True)
indices=[index for index, row in enumerate(rows) if row.startswith("MFA_ENCRYPTION_KEY=")]
assert len(indices)==1
rows[indices[0]]="MFA_ENCRYPTION_KEY=ci-intentionally-wrong-recovery-identity" + chr(10)
path.write_text("".join(rows), encoding="utf-8")
PY
assert_operator_preflight_denied critical_config_identity
if CONFIRM_RESTORE=YES bash scripts/datacenterctl restore "$NAME" >/dev/null 2>&1; then
  echo 'ERROR: critical-key mismatch was accepted for destructive restore' >&2
  exit 4
fi
cp "$CI_ENV_COPY" .env
rm -f "$CI_ENV_COPY"
db_marker prove-denial
s3_marker prove-denial
echo '[DR 4/8] Proving a corrupted backup is refused BEFORE database or Evidence deletion.'
ORIGINAL="$(mktemp "$INSTALL_REPO/../${NAME}-original-objectstore-XXXXXXXX.zip")"
chmod 600 "$ORIGINAL"
cp "$BACKUP/objectstore.zip" "$ORIGINAL"
# A checksum mismatch must stop the destructive recovery script before any service changes.
printf '\nci-deliberately-tampered\n' >> "$BACKUP/objectstore.zip"
assert_operator_preflight_denied backup_integrity
if python scripts/datacenter-backup-status.py --restore-preflight "$NAME" >/dev/null 2>&1; then
  echo 'ERROR: mandatory corrupt archive preflight unexpectedly passed' >&2
  exit 4
fi
if CONFIRM_RESTORE=YES bash scripts/datacenterctl restore "$NAME" >/dev/null 2>&1; then
  echo 'ERROR: production restore accepted a tampered backup' >&2
  exit 4
fi
db_marker prove-denial
s3_marker prove-denial
# Keep the canonical backup intact for the next phase, and revalidate after repair.
cp "$ORIGINAL" "$BACKUP/objectstore.zip"
rm -f "$ORIGINAL"
python scripts/datacenter-backup-status.py --restore-preflight "$NAME" >/dev/null
assert_operator_preflight_pass
echo '[DR 5/8] Executing the actual destructive datacenterctl restore, including full stack restart.'
CONFIRM_RESTORE=YES bash scripts/datacenterctl restore "$NAME" >/dev/null
echo '[DR 6/8] Verifying pre-backup SQL/Evidence markers, bytes and metadata; later mutations absent.'
db_marker verify-restored
s3_marker verify-restored
echo '[DR 7/8] Checking post-recovery production-shaped TLS readiness and signed image identities.'
bash scripts/datacenterctl verify > /dev/null
python scripts/datacenter-backup-status.py --restore-preflight "$NAME" >/dev/null
python - "$BACKUP/restore-observation.json" "$EXPECTED_SHA" <<'PY'
import json,sys
from pathlib import Path
report=json.loads(Path(sys.argv[1]).read_text())
assert report.get('backup_source_commit')==sys.argv[2]
assert report.get('restore_checkout_commit')==sys.argv[2]
assert report.get('rpo_observation') is None, 'CI must not claim measured customer RPO'
assert isinstance(report.get('observed_rto_seconds'),int)
print('Synthetic restore observation recorded; not customer recovery RTO/RPO.')
PY
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo '### Real signed-core full-stack synthetic recovery: PASS'
    echo '- Actual datacenterctl backup (quiesced) + restore (destructive) ran after signed offline install.'
    echo '- PostgreSQL data, S3 byte hash and object metadata restored; post-snapshot changes absent.'
    echo '- Backup tamper rejected before data replacement; running markers preserved.'
    echo '- Running backend, frontend, gateway, worker, beat and dependencies re-verified over test TLS.'
    echo '- NOT independent off-host DR, customer RPO/RTO, real air-gap, approved release or production UAT.'
  } >> "$GITHUB_STEP_SUMMARY"
fi
echo '[DR 8/8] Full real-core synthetic recovery PASS. Runner cleanup follows.'
